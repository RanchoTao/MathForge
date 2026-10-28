"""Contract fixtures only. No real research admission or original workspace is changed."""
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import uuid
from unittest.mock import patch

from mathforge import engine
from mathforge.gateway import server
from mathforge.source_audit import SourceAuditQueue, BoundaryError, history_snapshot
from mathforge.source_audit_worker import finite_frequency_table, deny_external
from mathforge.workspace import initialize

ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'reports/local';LOCAL.mkdir(parents=True,exist_ok=True)
SECRET='contract-test-only-receipt-secret-not-a-production-key'
TOKEN='contract-test-only-gateway-token-not-a-production-key'


class SourceAudits(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=LOCAL)
        self.root=initialize(Path(self.tmp.name)/'workspace')
        shutil.copytree(ROOT/'sources/conjmap-fin2',self.root/'sources/conjmap-fin2')
        self.card=engine.read_json(self.root/'sources/conjmap-fin2/ADMISSION.json')
        self.card['history_clearance']['snapshot_sha256']=history_snapshot(self.root)
        (self.root/'sources/conjmap-fin2/ADMISSION.json').write_text(json.dumps(self.card),encoding='utf8')
        self.queue=SourceAuditQueue(self.root,'reports/local/fixture',SECRET,commit='f'*40)
        self.request=dict(api_version='v2',conjmap_task_id=str(uuid.uuid4()),problem_id=self.card['problem_id'],
                          objective='Contract fixture only; never a genuine research result.',admission_id=self.card['admission_id'],
                          budget=dict(wall_seconds=5,max_tasks=1,network=False),context=dict(problem_id=self.card['problem_id'],
                          statement=self.card['statement'],formal_statement=self.card['formal_statement'],source_binding=self.card['source_binding']))
        self.key='contract-test-only-idempotency-key'
    def tearDown(self):self.tmp.cleanup()
    def enqueue(self):return self.queue.enqueue(self.request,self.key)['engine_task_id']

    def test_semantic_finite_bound_and_empty_family(self):
        result=finite_frequency_table()
        self.assertEqual(result['families_examined'],16)
        self.assertEqual(result['applicable_families'],13)
        self.assertTrue(result['rows'][0]['applicable'])
        self.assertFalse(result['rows'][1]['applicable'])
        self.assertTrue(result['encodings_agree'])
        self.assertFalse(result['proof_kernel_verified'])

    def test_network_and_child_execution_denied(self):
        for event in ['socket.connect','socket.__new__','subprocess.Popen','os.system','os.exec']:
            with self.assertRaises(PermissionError):deny_external(event,())

    def test_admission_source_variant_and_budget_fail_closed(self):
        for change in [dict(admission_id='unknown'),dict(budget=dict(wall_seconds=61,max_tasks=1,network=False)),dict(budget=dict(wall_seconds=1,max_tasks=1,network=True)),dict(problem_id='cm-000001')]:
            with self.subTest(change=change),self.assertRaises(BoundaryError):self.queue.enqueue({**self.request,**change},self.key)
        bad=copy.deepcopy(self.request);bad['context']['formal_statement']='different variant'
        with self.assertRaises(BoundaryError):self.queue.enqueue(bad,self.key)
        with self.queue.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],0)

    def test_idempotency_and_terminal_evidence(self):
        uid=self.enqueue()
        self.assertEqual(self.enqueue(),uid)
        with self.assertRaises(BoundaryError):self.queue.enqueue({**self.request,'objective':'Changed fixture objective'},self.key)
        self.queue.cancel(uid)
        self.assertEqual(self.queue.result(uid)['status'],'cancelled')
        with self.assertRaises(BoundaryError):self.queue.change(uid,'running')

    def test_one_lifetime_task_even_new_idempotency_key(self):
        self.enqueue()
        with self.assertRaises(BoundaryError):self.queue.enqueue(self.request,self.key+'-new')

    def test_mode_cannot_relabel_persisted_contract_run(self):
        self.enqueue()
        with self.assertRaisesRegex(BoundaryError,'mode is immutable'):
            SourceAuditQueue(self.root,'reports/local/fixture',SECRET,mode='REAL_RUN',commit='f'*40,legacy_root=self.root)

    def test_real_reservation_is_engine_root_scoped_without_execution(self):
        # REAL_RUN boundary fixture reserves a slot, never calls run or launches a worker.
        one=SourceAuditQueue(self.root,'reports/local/real-boundary-one',SECRET,mode='REAL_RUN',commit='f'*40,legacy_root=self.root)
        one.enqueue(self.request,self.key)
        two=SourceAuditQueue(self.root,'reports/local/real-boundary-two',SECRET,mode='REAL_RUN',commit='f'*40,legacy_root=self.root)
        with self.assertRaisesRegex(BoundaryError,'engine-root'):
            two.enqueue(self.request,self.key+'-another')

    def test_historical_registry_drift_rejects_before_execution(self):
        one=SourceAuditQueue(self.root,'reports/local/real-boundary',SECRET,mode='REAL_RUN',commit='f'*40,legacy_root=self.root)
        p=self.root/'negative_knowledge/new.json';p.write_text('{}')
        with self.assertRaisesRegex(BoundaryError,'historical registry changed'):one.enqueue(self.request,self.key)

    def test_receipt_freezes_original_provenance_and_binds_attempts(self):
        uid=self.enqueue();self.queue.cancel(uid)
        other=SourceAuditQueue(self.root,'reports/local/fixture',SECRET,commit='a'*40)
        row=other.result(uid);payload=json.loads(row['receipt']['payload'])
        self.assertEqual(payload['engine_commit'],'f'*40)
        self.assertEqual(payload['attempts'],row['attempts'])
        self.assertEqual(row['execution_mode'],'CONTRACT_TEST')
        signature=hmac.new(SECRET.encode(),row['receipt']['payload'].encode(),hashlib.sha256).hexdigest()
        self.assertEqual(row['receipt']['signature'],'sha256='+signature)

    def test_restart_code_commit_drift_rejects_queued_worker(self):
        uid=self.enqueue()
        other=SourceAuditQueue(self.root,'reports/local/fixture',SECRET,commit='a'*40)
        result=other.run(uid)
        self.assertEqual(result['status'],'rejected')
        self.assertFalse((other.folder/'runs'/uid).exists())

    def test_recovery_refuses_live_controller_and_retains_state(self):
        uid=self.enqueue();self.queue.change(uid,'running')
        with self.assertRaisesRegex(BoundaryError,'live controller'):self.queue.recover(uid)
        with self.queue.connect() as db:db.execute('UPDATE jobs SET controller_pid=NULL WHERE id=?',(uid,))
        self.assertEqual(self.queue.recover(uid)['status'],'interrupted')
        self.assertEqual(self.queue.run(uid)['status'],'interrupted')

    def test_cancel_and_recover_read_current_state_under_transaction(self):
        uid=self.enqueue();self.queue.change(uid,'running')
        original=self.queue.row
        def stale_row(*args,**kwargs):
            row=original(*args,**kwargs)
            # Simulated stale pre-start snapshot must not drive either operation.
            return {**row,'state':'queued','controller_pid':None,'worker_pid':None}
        with patch.object(self.queue,'row',side_effect=stale_row):
            self.queue.cancel(uid)
            with self.assertRaisesRegex(BoundaryError,'live controller'):self.queue.recover(uid)
        current=original(uid)
        self.assertEqual(current['state'],'running')
        self.assertEqual(current['cancel'],1)

    def test_setup_failure_is_finalized_without_overwriting_existing_files(self):
        uid=self.enqueue();folder=self.queue.folder/'runs'/uid;folder.mkdir(parents=True)
        (folder/'preserve.txt').write_text('existing evidence')
        self.assertEqual(self.queue.run(uid)['status'],'failed')
        self.assertEqual((folder/'preserve.txt').read_text(),'existing evidence')

    @unittest.skipUnless(os.name=='nt','Windows budget adapter fails closed on other platforms')
    def test_actual_trusted_worker_contract_fixture_not_real_run(self):
        uid=self.enqueue();result=self.queue.run(uid)
        self.assertEqual(result['status'],'completed',result)
        self.assertEqual(result['execution_mode'],'CONTRACT_TEST')
        receipt=json.loads(result['receipt']['payload'])
        self.assertGreater(receipt['resources']['peak_job_bytes'],0)
        self.assertLess(receipt['resources']['wall_seconds'],5)
        data=json.loads(self.queue.artifact(uid,'RESULT.json'))
        self.assertEqual(data['execution_mode'],'CONTRACT_TEST')
        self.assertEqual(data['families_examined'],16)
        with self.assertRaises(BoundaryError):self.queue.artifact(uid,'../ADMISSION.json')
        with (self.queue.folder/'runs'/uid/'RESULT.json').open('a') as f:f.write('x')
        with self.assertRaisesRegex(BoundaryError,'integrity'):self.queue.artifact(uid,'RESULT.json')

    def test_authenticated_http_lookup_and_no_browser_origin(self):
        uid=self.enqueue();self.queue.cancel(uid)
        http=server(self.queue,TOKEN);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{http.server_port}/v2/research-tasks'
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+'/'+uid)
            self.assertEqual(caught.exception.code,401)
            request=urllib.request.Request(base+'/by-key/'+self.key,headers={'Authorization':'Bearer '+TOKEN})
            with urllib.request.urlopen(request) as response:self.assertEqual(json.load(response)['engine_task_id'],uid)
            request.add_header('Origin','https://example.com')
            with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code,403)
        finally:http.shutdown();http.server_close();http.audit_pool.shutdown();thread.join()


if __name__=='__main__':unittest.main()
