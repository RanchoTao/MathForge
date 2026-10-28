"""Engine-owned, separately admitted source/finite audit queue.

Does not extend Phase 0 proof/novelty state permissions or the legacy audit queue.
Reuses its SQLite transaction, event hashing, output boundaries and Windows budget.
"""
from datetime import datetime, timezone
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

from . import engine
from .certificates import dump, sha
from .queue import AuditQueue, evidence_path

TERMINAL = {'completed', 'failed', 'rejected', 'interrupted', 'cancelled', 'blocked'}
ADMISSION = 'cm-v04-union-closed-fin2-v1'


def now():
    return datetime.now(timezone.utc).isoformat()


def history_snapshot(root):
    """Read-only replay inputs, matching the original controller's bounded registry."""
    root=Path(root).resolve()
    paths=sorted((root/'negative_knowledge').rglob('*.json'))
    paths+=sorted((root/'research/phase2a').glob('*REPLAY*'))
    paths+=[root/'research/phase2a/NEGATIVE_KNOWLEDGE.jsonl']
    paths+=sorted((root/'research').glob('phase2*/MF-*/RESEARCH_EVENTS.jsonl'))
    values={p.relative_to(root).as_posix():sha(p) for p in paths if p.is_file()}
    if not values:raise BoundaryError(503,'historical replay registry missing')
    return engine.digest(values)


def process_active(pid):
    if not pid:return False
    if os.name!='nt':return Path(f'/proc/{pid}').exists()
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return False
        raise BoundaryError(409,'cannot establish controller liveness; recovery held')
    try:
        code=wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle,ctypes.byref(code)):
            raise BoundaryError(409,'cannot establish worker liveness')
        return code.value==259
    finally:kernel.CloseHandle(handle)


class BoundaryError(ValueError):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


class SourceAuditQueue(AuditQueue):
    def __init__(self, root, journal, secret, *, mode='CONTRACT_TEST', commit=None, legacy_root=None):
        self.root = Path(root).resolve()
        self.folder = evidence_path(self.root, journal)
        self.path = self.folder / 'source-audits.sqlite3'
        self.folder.mkdir(parents=True, exist_ok=True)
        if mode not in {'REAL_RUN', 'CONTRACT_TEST'} or len(secret) < 32:
            raise BoundaryError(503, 'explicit execution mode and strong receipt secret required')
        self.mode, self.secret = mode, secret
        self.legacy_root=Path(legacy_root).resolve() if legacy_root else None
        if mode=='REAL_RUN' and self.legacy_root is None:
            raise BoundaryError(503,'REAL_RUN requires explicit read-only historical registry binding')
        self.commit = commit or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        self.code = {p.name: sha(p) for p in [Path(__file__), Path(__file__).with_name('source_audit_worker.py'), Path(__file__).with_name('windows_budget.py'),Path(__file__).with_name('gateway.py')]}
        self.provenance=dict(execution_mode=mode,engine_commit=self.commit,code_sha256=self.code)
        self.registry = self.root / 'sources/conjmap-fin2/ADMISSION.json'
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS jobs(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE, logical_key TEXT UNIQUE,
                request TEXT, admission TEXT, state TEXT, created TEXT, updated TEXT, cancel INTEGER DEFAULT 0,
                resources TEXT, artifacts TEXT, outcome TEXT, workspace_binding TEXT, provenance TEXT,
                controller_pid INTEGER, worker_pid INTEGER);
                CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                job TEXT, kind TEXT, at TEXT, previous_hash TEXT, hash TEXT);''')
            for row in db.execute('SELECT provenance FROM jobs'):
                if json.loads(row['provenance'])['execution_mode']!=mode:
                    raise BoundaryError(409,'journal execution mode is immutable')
        self.real_ledger=evidence_path(self.root,'reports/local/source-audit-real-ledger.sqlite3')
        if mode=='REAL_RUN':
            import sqlite3
            with closing(sqlite3.connect(self.real_ledger)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS claims(admission TEXT PRIMARY KEY,job TEXT,journal TEXT,created TEXT)')
                db.commit()

    def check_chain(self):
        with self.connect() as db:
            prev = None
            for row in db.execute('SELECT * FROM events ORDER BY sequence'):
                value = {k: row[k] for k in ['job', 'kind', 'at', 'previous_hash']}
                if row['previous_hash'] != prev or engine.digest(value) != row['hash']:
                    raise BoundaryError(503, 'audit chain corrupted; preserve evidence')
                prev = row['hash']

    def admission(self, request):
        if request.get('admission_id') != ADMISSION:
            raise BoundaryError(422, 'no engine-owned admission for this request')
        card = engine.read_json(self.registry)
        expected = {'api_version', 'conjmap_task_id', 'problem_id', 'objective', 'budget', 'context', 'admission_id'}
        if set(request) != expected or request['api_version'] != 'v2':
            raise BoundaryError(422, 'unsupported transport fields')
        try:
            uuid.UUID(request['conjmap_task_id'])
        except (ValueError, TypeError, AttributeError):
            raise BoundaryError(422, 'invalid ConjMap identity') from None
        budget = request['budget']
        if (set(budget) != {'wall_seconds', 'max_tasks', 'network'} or
                type(budget['wall_seconds']) is not int or not 1 <= budget['wall_seconds'] <= 60 or
                type(budget['max_tasks']) is not int or budget['max_tasks'] != 1 or budget['network'] is not False):
            raise BoundaryError(422, 'budget outside the explicit one-task/no-network cap')
        if not isinstance(request['objective'],str) or not 5<=len(request['objective'])<=2000:
            raise BoundaryError(422,'bounded objective required')
        if (card['admission_id'] != ADMISSION or card['decision'] != 'ADMITTED_KNOWN_FINITE_CALIBRATION' or
                card['task_type'] != 'union_closed_fin2_frequency' or
                card['history_clearance']['decision'] != 'DISTINCT_TARGET_NO_REPLAY' or
                not card['reviews'] or request['problem_id'] != card['problem_id']):
            raise BoundaryError(422, 'scientific admission missing, mismatched or held')
        if self.mode=='REAL_RUN' and history_snapshot(self.legacy_root)!=card['history_clearance']['snapshot_sha256']:
            raise BoundaryError(422,'historical registry changed since scoped replay review; new audit required')
        context = request['context']
        if (context.get('problem_id') != card['problem_id'] or context.get('statement') != card['statement'] or
                context.get('formal_statement') != card['formal_statement'] or
                context.get('source_binding') != card['source_binding']):
            raise BoundaryError(422, 'original statement, variant or exact source binding mismatch')
        if hashlib.sha256(card['statement'].encode()).hexdigest() != card['source_binding']['statement_sha256']:
            raise BoundaryError(422, 'statement digest mismatch')
        source = self.registry.parent / 'SOURCE.lean'
        if sha(source) != card['source_binding']['sha256']:
            raise BoundaryError(422, 'admission source drift')
        text = source.read_text(encoding='utf8')
        if not all(s in text for s in [card['formal_statement'], card['variant_signature'], *card['required_source_fragments']]):
            raise BoundaryError(422, 'source hypothesis/declaration drift')
        data = engine.load_repository(self.root)
        # Bootstrap proof/research permissions remain false. This separate allowlist only
        # permits the source-bound known-result calibration, not novelty/proof states.
        if engine.replay_blocks(card['problem_id'], data['negatives']):
            raise BoundaryError(422, 'engine replay prohibition applies')
        return card

    def enqueue(self, request, key):
        self.check_chain()
        if not re.fullmatch('[A-Za-z0-9-]{16,100}', key):
            raise BoundaryError(400, 'valid idempotency key required')
        card = self.admission(request)
        bound = self.binding()
        stamp = now()
        with self.connect() as db:
            if self.mode=='REAL_RUN':db.execute('ATTACH DATABASE ? AS real_ledger',(str(self.real_ledger),))
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM jobs WHERE logical_key=?', (key,)).fetchone()
            if old:
                if engine.canonical(request) != old['request']:
                    raise BoundaryError(409, 'idempotency payload conflict')
                db.commit()
                return self.result(old['id'])
            if db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] >= 1:
                raise BoundaryError(429, 'one lifetime task cap; no new key or automatic replay')
            uid = 'mf-audit-' + uuid.uuid4().hex
            if self.mode=='REAL_RUN':
                if db.execute('SELECT COUNT(*) FROM real_ledger.claims WHERE admission=?',(ADMISSION,)).fetchone()[0]:
                    raise BoundaryError(429,'engine-root REAL_RUN admission already reserved; journal changes do not grant replay')
                db.execute('INSERT INTO real_ledger.claims VALUES(?,?,?,?)',(ADMISSION,uid,str(self.path.relative_to(self.root)),stamp))
            resources = dict(wall_seconds=0, cpu_seconds=0, peak_job_bytes=0)
            db.execute('INSERT INTO jobs(id,logical_key,request,admission,state,created,updated,resources,artifacts,outcome,workspace_binding,provenance) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (uid,key,engine.canonical(request),engine.canonical(card),'queued',stamp,stamp,engine.canonical(resources),'[]','Awaiting admitted worker',bound,engine.canonical(self.provenance)))
            self.event(db, uid, 'queued')
            db.commit()
        self.snapshot(uid)
        return self.result(uid)

    def row(self, uid=None, *, key=None):
        self.check_chain()
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE ' + ('logical_key=?' if key is not None else 'id=?'), (key if key is not None else uid,)).fetchone()
        if row is None:
            raise BoundaryError(404, 'unknown engine task; no resubmission occurred')
        return dict(row)

    def result(self, uid):
        row = self.row(uid)
        request, card = json.loads(row['request']), json.loads(row['admission'])
        provenance=json.loads(row['provenance'])
        attempts = []
        if row['state'] in TERMINAL:
            attempts = [dict(kind='partial_result' if row['state']=='completed' else 'failed_route', result=row['outcome'],
                             verification_status='unverified',artifact_urls=[])]
        payload = dict(protocol='mathforge-conjmap-receipt-v1', engine_task_id=uid,
                       conjmap_task_id=request['conjmap_task_id'], problem_id=card['problem_id'],
                       admission_id=card['admission_id'], execution_mode=provenance['execution_mode'], status=row['state'],
                       source_sha256=card['source_binding']['sha256'], statement_sha256=card['source_binding']['statement_sha256'],
                       admission_sha256=engine.digest(card), engine_commit=provenance['engine_commit'],
                       worker_sha256=provenance['code_sha256']['source_audit_worker.py'], artifact_index=json.loads(row['artifacts']),
                       resources=json.loads(row['resources']), scientific_status='unverified', recorded_at=row['updated'],attempts=attempts)
        raw = engine.canonical(payload)
        return dict(engine='mathforge',is_mock=False,engine_task_id=uid,status=row['state'],attempts=attempts,
                    execution_mode=provenance['execution_mode'],receipt=dict(payload=raw,signature='sha256='+hmac.new(self.secret.encode(),raw.encode(),hashlib.sha256).hexdigest()))

    def snapshot(self, uid):
        folder = self.folder / 'receipts' / uid
        folder.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            sequence = db.execute('SELECT MAX(sequence) FROM events WHERE job=?',(uid,)).fetchone()[0]
        dump(folder / f'{sequence:06}.json', self.result(uid))

    def change(self, uid, state, *, resources=None, artifacts=None, outcome=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM jobs WHERE id=?',(uid,)).fetchone()
            allowed = {'queued':{'running','cancelled','rejected','interrupted'},'running':TERMINAL}
            if row is None or state not in allowed.get(row['state'],set()):
                raise BoundaryError(409, 'illegal or terminal state transition')
            db.execute('UPDATE jobs SET state=?,updated=?,resources=?,artifacts=?,outcome=? WHERE id=?',
                       (state,now(),engine.canonical(resources or json.loads(row['resources'])),engine.canonical(artifacts if artifacts is not None else json.loads(row['artifacts'])),outcome or row['outcome'],uid))
            if state=='running':db.execute('UPDATE jobs SET controller_pid=? WHERE id=?',(os.getpid(),uid))
            self.event(db,uid,state)
            db.commit()
        self.snapshot(uid)

    def cancel(self, uid):
        self.check_chain();terminal=False
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE id=?',(uid,)).fetchone()
            if row is None:raise BoundaryError(404,'unknown task')
            if row['state']=='queued':
                db.execute('UPDATE jobs SET state=?,updated=?,outcome=? WHERE id=?',('cancelled',now(),'Cancelled before worker admission; no computation launched',uid))
                self.event(db,uid,'cancelled');terminal=True
            elif row['state']=='running':
                db.execute('UPDATE jobs SET cancel=1 WHERE id=? AND state=?',(uid,'running'))
                self.event(db,uid,'cancellation_requested')
            db.commit()
        if terminal:self.snapshot(uid)
        return self.result(uid)

    def recover(self, uid):
        # Operator-only CLI; never replay an uncertain/previously running computation.
        self.check_chain()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE id=?',(uid,)).fetchone()
            if row is None or row['state'] not in {'queued','running'}:
                raise BoundaryError(409,'only unsettled tasks can be interrupted')
            if process_active(row['controller_pid']) or process_active(row['worker_pid']):
                raise BoundaryError(409,'live controller or worker; recovery must not race execution')
            db.execute('UPDATE jobs SET state=?,updated=?,outcome=? WHERE id=?',('interrupted',now(),'Operator reconciled interrupted controller; no worker replay',uid))
            self.event(db,uid,'interrupted');db.commit()
        self.snapshot(uid)
        return self.result(uid)

    def artifact(self, uid, name):
        row=self.row(uid)
        entry=next((a for a in json.loads(row['artifacts']) if a['name']==name),None)
        if entry is None or not re.fullmatch('[A-Za-z0-9_.-]{1,80}',name):
            raise BoundaryError(404,'artifact not in signed evidence index')
        file=self.folder/'runs'/uid/name
        raw=file.read_bytes()
        if len(raw)>1048576 or len(raw)!=entry['bytes'] or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise BoundaryError(503,'artifact integrity mismatch')
        return raw

    def run(self, uid):
        row=self.row(uid)
        if row['state']!='queued': return self.result(uid)
        try:
            request=json.loads(row['request'])
            card=self.admission(request)
            if row['workspace_binding']!=self.binding() or engine.canonical(card)!=row['admission'] or row['provenance']!=engine.canonical(self.provenance) or any(sha(Path(__file__).with_name(n))!=h for n,h in self.code.items()):
                raise BoundaryError(422,'workspace, code or admission drift; no worker launched')
        except (ValueError,OSError) as error:
            self.change(uid,'rejected',outcome=str(error));return self.result(uid)
        self.change(uid,'running')
        folder=self.folder/'runs'/uid
        start=time.monotonic();process=None;state='failed';cpu=0;peak=0;created=False;watchdog=None
        expired=threading.Event();stopped_at=[];monitor=None
        try:
            folder.mkdir(parents=True,exist_ok=False);created=True
            dump(folder/'INPUT.json',dict(source_sha256=card['source_binding']['sha256'],statement_sha256=card['source_binding']['statement_sha256'],
                                         formal_statement=card['formal_statement'],variant_signature=card['variant_signature'],required_source_fragments=card['required_source_fragments'],execution_mode=self.mode))
            with (folder/'SOURCE.lean').open('xb') as out:out.write((self.registry.parent/'SOURCE.lean').read_bytes())
            from .windows_budget import WindowsMemoryJob
            with (folder/'stdout.txt').open('x',encoding='utf8') as stdout, (folder/'stderr.txt').open('x',encoding='utf8') as stderr, WindowsMemoryJob(256*1024**2) as job:
                env={k:os.environ[k] for k in ['SystemRoot','WINDIR','TEMP','TMP'] if k in os.environ}
                env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
                process=subprocess.Popen([sys.executable,'-I',str(Path(__file__).with_name('source_audit_worker.py')),str(folder)],stdin=subprocess.PIPE,
                                         stdout=stdout,stderr=stderr,cwd=folder,env=env,creationflags=0x08000000)
                job.assign(process.pid)
                def observe_exit():
                    process.wait();stopped_at.append(time.monotonic())
                monitor=threading.Thread(target=observe_exit,daemon=True);monitor.start()
                def timeout():
                    expired.set()
                    try:
                        if process.poll() is None:process.kill()
                    except OSError:pass
                watchdog=threading.Timer(max(.001,request['budget']['wall_seconds']-(time.monotonic()-start)),timeout)
                watchdog.daemon=True;watchdog.start()
                with self.connect() as db:db.execute('UPDATE jobs SET worker_pid=? WHERE id=?',(process.pid,uid))
                state='completed'
                if expired.is_set() or time.monotonic()-start>=request['budget']['wall_seconds']:
                    timeout()
                else:
                    process.stdin.write(b'START\n')
                process.stdin.close()
                while process.poll() is None:
                    if self.row(uid)['cancel']:
                        state='cancelled';process.kill();break
                    time.sleep(.01)
                process.wait(timeout=2)
                watchdog.cancel()
                if expired.is_set():state='interrupted'
                if state=='completed' and process.returncode!=0:state='failed'
                usage=job.usage();cpu=usage['cpu_seconds'];peak=usage['peak_job_bytes']
            if state=='completed':
                result=engine.read_json(folder/'RESULT.json')
                if result['execution_mode']!=self.mode or not result['encodings_agree'] or result['families_examined']!=16:
                    raise ValueError('worker result scope/encoding mismatch')
                outcome=f"Actual MathForge finite calibration: examined 16 families of P(Fin 2); {result['applicable_families']} applicable union-closed families each have a half-frequency witness. Source binding checked; no general proof, kernel verification or status promotion."
            else:outcome='Worker '+state+'; retain actual logs, do not retry or claim a mathematical result'
        except Exception as error:
            state='interrupted' if expired.is_set() else 'failed';outcome=type(error).__name__+': '+str(error)
        finally:
            if watchdog:watchdog.cancel()
            if process is not None and process.poll() is None:process.kill();process.wait()
            if monitor:monitor.join(timeout=2)
        resources=dict(wall_seconds=(stopped_at[0] if stopped_at else time.monotonic())-start,cpu_seconds=cpu,peak_job_bytes=peak,
                       controller_elapsed_seconds=time.monotonic()-start)
        if created:dump(folder/'EXECUTION.json',dict(engine_commit=self.commit,code_sha256=self.code,python=sys.version.split()[0],
                                         pid=process.pid if process else None,exit_code=process.returncode if process else None,
                                         resources=resources,memory_cap_bytes=256*1024**2,network='trusted-worker audit hook denies socket and child execution',
                                         mode=self.mode,proof_acceptance_enabled=False,novelty='KNOWN_CALIBRATION_NOT_A_DISCOVERY'))
        artifacts=[dict(name=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(folder.iterdir()) if p.is_file()] if created else []
        self.change(uid,state,resources=resources,artifacts=artifacts,outcome=outcome)
        return self.result(uid)
