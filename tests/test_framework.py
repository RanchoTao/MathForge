"""Adversarial tests use newly generated synthetic fixtures, never research records."""
import concurrent.futures
import copy
from datetime import date, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from mathforge import engine
from mathforge.workspace import initialize
from mathforge.queue import AuditQueue
from mathforge import certificates, lean

LOCAL = Path.cwd()/'reports/local'
LOCAL.mkdir(parents=True, exist_ok=True)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=LOCAL)
        self.root = initialize(Path(self.tmp.name)/'workspace')
    def tearDown(self): self.tmp.cleanup()
    def request(self, target='BLOCKED'):
        return dict(problem_id='MF-0000', **{'from':'OPEN_STATUS_UNVERIFIED','to':target},
                    actor='critic', reason='Synthetic adversarial fixture only.', evidence=[])
    def card(self): return engine.read_jsonl(self.root/'atlas/atlas.jsonl')[0]
    def save_card(self, card):
        (self.root/'atlas/atlas.jsonl').write_text(engine.canonical(card)+'\n',encoding='utf-8')

class IntegrityTests(Fixture):
    def test_seed_has_no_verified_scientific_claim(self):
        data=engine.load_repository(self.root)
        self.assertEqual(len(data['problems']),1)
        self.assertFalse(data['policy']['research_execution_enabled'])
        self.assertEqual(self.card()['audit']['novelty'],'unknown')
    def test_unknown_schema_field_rejected(self):
        c=self.card();c['unsupported_claim']=True;self.save_card(c)
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_duplicate_alias_rejected(self):
        c=self.card();c['aliases']=[c['name'].upper()];self.save_card(c)
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_broken_evidence_rejected(self):
        c=self.card();c['sources']['primary']=['SRC-NONE'];self.save_card(c)
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_state_transition_appended_and_genesis_unchanged(self):
        before=(self.root/'atlas/atlas.jsonl').read_bytes()
        event=engine.append_transition(self.root,self.request())
        self.assertEqual(engine.load_repository(self.root)['states']['MF-0000'],'BLOCKED')
        self.assertEqual(before,(self.root/'atlas/atlas.jsonl').read_bytes())
        self.assertEqual(event['hash'],engine.digest({k:v for k,v in event.items() if k!='hash'}))
    def test_unreviewed_open_status_denied(self):
        with self.assertRaises(engine.IntegrityError):engine.append_transition(self.root,self.request('VERIFIED_OPEN'))
        self.assertFalse((self.root/'orchestration/events.jsonl').exists())
    def test_all_research_promotions_denied(self):
        for state in ['PROOF_ATTEMPT','FORMALIZATION','PROVED','SENTINEL_RUNNING']:
            with self.subTest(state=state), self.assertRaises(engine.IntegrityError):engine.append_transition(self.root,self.request(state))
    def test_policy_cannot_enable_execution(self):
        p=self.root/'orchestration/policy.json';o=engine.read_json(p);o['research_execution_enabled']=True;p.write_text(json.dumps(o))
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_policy_cannot_expand_targets(self):
        p=self.root/'orchestration/policy.json';o=engine.read_json(p);o['allowed_targets'].append('PROVED');p.write_text(json.dumps(o))
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_writer_lock_not_stolen(self):
        p=self.root/'orchestration/.writer.lock';p.write_text('synthetic-other-writer')
        with self.assertRaises(engine.IntegrityError):engine.append_transition(self.root,self.request())
        self.assertEqual(p.read_text(),'synthetic-other-writer')
    def test_torn_journal_rejected(self):
        p=self.root/'orchestration/events.jsonl';p.write_text('{"partial":')
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_rehashed_invalid_event_rejected(self):
        event=engine.append_transition(self.root,self.request());event['problem_id']='MF-9999'
        event['hash']=engine.digest({k:v for k,v in event.items() if k!='hash'})
        (self.root/'orchestration/events.jsonl').write_text(engine.canonical(event)+'\n')
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)
    def test_stale_writer_rejected(self):
        engine.append_transition(self.root,self.request())
        with self.assertRaises(engine.IntegrityError):engine.append_transition(self.root,self.request())
    def test_replay_block_remains(self):
        d=engine.load_repository(self.root)
        self.assertEqual(engine.replay_blocks('MF-0000',d['negatives']),['NEG-DEMO-PHASE0'])
    def test_initializer_never_overwrites(self):
        before=(self.root/'atlas/atlas.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):initialize(self.root)
        self.assertEqual(before,(self.root/'atlas/atlas.jsonl').read_bytes())

class QueueTests(Fixture):
    def test_duplicate_admission_is_idempotent(self):
        q=AuditQueue(self.root);a=q.enqueue('validate');b=q.enqueue('validate')
        self.assertEqual(a,b);self.assertEqual(len(q.status()),1)
    def test_only_audits_execute(self):
        q=AuditQueue(self.root)
        for action in ['research','proof','shell','publish']:
            with self.assertRaises(engine.IntegrityError):q.enqueue(action)
    def test_export_stays_in_evidence_root(self):
        q=AuditQueue(self.root)
        with self.assertRaises(engine.IntegrityError):q.enqueue('export',{'output':'../outside.jsonl'})
    def test_durable_claim_not_duplicated(self):
        q=AuditQueue(self.root);q.enqueue('validate')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:AuditQueue(self.root).run_one(),range(2)))
        self.assertEqual(sum(x is not None for x in results),1)
        self.assertEqual(q.status()[0]['state'],'DONE')
    def test_drift_retained_as_failure(self):
        q=AuditQueue(self.root);q.enqueue('validate')
        c=self.card();c['informal_statement']='Changed synthetic input';self.save_card(c)
        result=q.run_one();self.assertEqual(result['state'],'FAILED')
        self.assertTrue((self.root/q.status()[0]['receipt']).is_file())
    def test_interrupted_work_is_not_automatically_replayed(self):
        q=AuditQueue(self.root);job=q.enqueue('validate')
        with q.connect() as db:db.execute("UPDATE jobs SET state='RUNNING' WHERE id=?",(job,))
        self.assertFalse(q.recover_interrupted(job)['replayed'])
        self.assertIsNone(q.run_one());self.assertEqual(q.enqueue('validate'),job)
    def test_evidence_chain_tampering_rejected(self):
        q=AuditQueue(self.root);q.enqueue('validate')
        with q.connect() as db:db.execute("UPDATE events SET kind='changed'")
        with self.assertRaises(engine.IntegrityError):q.run_one()
    def test_export_existing_file_not_overwritten(self):
        q=AuditQueue(self.root);p=self.root/'reports/local/exists.jsonl';p.write_text('keep')
        q.enqueue('export',{'output':'reports/local/exists.jsonl'})
        self.assertEqual(q.run_one()['state'],'FAILED');self.assertEqual(p.read_text(),'keep')

class LeanInterfaceTests(Fixture):
    def task(self):
        return dict(natural_language='Synthetic adapter smoke only: True.',imports=['Init'],
                    targets=[dict(name='Smoke',type='True',proof=dict(kind='exact',term='True.intro'))])
    def test_executable_certificates_rejected(self):
        for term in ['by run_tac IO.println "spoof"','sorry','axiom','by_elab','unsafe']:
            with self.subTest(term=term), self.assertRaises(ValueError):certificates.pure_term(term)
    def test_unknown_certificate_rejected(self):
        with self.assertRaises(ValueError):certificates.proof({'kind':'shell','command':'anything'})
    def test_missing_tool_is_hold_not_success(self):
        r=lean.check(self.task(),self.root/'reports/local/missing',workspace=self.root,lean=self.root/'absent',reviewed_policy={})
        self.assertFalse(r['scoped_kernel_checked']);self.assertEqual(r['status'],'HOLD')
    def test_arbitrary_source_import_denied(self):
        t=self.task();t['imports']=['Unreviewed']
        r=lean.check(t,self.root/'reports/local/denied',workspace=self.root,lean=self.root/'absent',reviewed_policy={})
        self.assertEqual(r['status'],'HOLD');self.assertFalse(r['stages'])
    def test_receipt_path_escape_denied(self):
        with self.assertRaises(ValueError):lean.check(self.task(),self.root/'outside',workspace=self.root,lean='absent',reviewed_policy={})
    @unittest.skipUnless(os.environ.get('MATHFORGE_TEST_LEAN') and os.name=='nt','real Lean is an explicit optional integration test')
    def test_real_kernel_true_and_wrong_type(self):
        exe=os.environ['MATHFORGE_TEST_LEAN'];policy=lean.pin_toolchain(exe)
        good=lean.check(self.task(),self.root/'reports/local/true',workspace=self.root,lean=exe,reviewed_policy=policy,timeout=90)
        self.assertTrue(good['scoped_kernel_checked'],good)
        self.assertFalse(good['workflow_proof_acceptance'])
        bad=self.task();bad['targets'][0]['type']='False'
        fail=lean.check(bad,self.root/'reports/local/false',workspace=self.root,lean=exe,reviewed_policy=policy)
        self.assertEqual(fail['status'],'HOLD');self.assertFalse(fail['scoped_kernel_checked'])

class StatusProjectionTests(Fixture):
    """The claimed open status must never outrun the workflow that justifies it."""

    def add_open_source(self, source_id='SRC-PROBE', locator='https://example.invalid/probe'):
        retrieved = date.today().isoformat()
        path = self.root/'knowledge/sources/catalog.json'
        rows = engine.read_json(path)
        rows.append(dict(source_id=source_id, title='Synthetic probe source', authors=['fixture'],
                         url=locator, kind='official_problem_list', access='full_text',
                         retrieved_on=retrieved, publication_year=None, version=None,
                         provenance=dict(actor='fixture', recorded_at=retrieved+'T00:00:00+00:00',
                                         method='synthetic probe', limitations='not a real source'),
                         status_bindings={'MF-0000': dict(
                             statement_sha256=engine.digest(self.card()['canonical_statement']),
                             locator=locator)}))
        path.write_text(json.dumps(rows, indent=2))
        return dict(source_id=source_id, locator=locator, supports='open_status', note='synthetic probe')

    def promote(self, evidence):
        return engine.append_transition(self.root, dict(problem_id='MF-0000',
            **{'from':'OPEN_STATUS_UNVERIFIED','to':'VERIFIED_OPEN'},
            actor='critic', reason='Synthetic projection fixture.', evidence=[evidence]))

    def test_card_status_cannot_outrun_workflow_state(self):
        c=self.card();c['status']['value']='KNOWN_RESULT';self.save_card(c)
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)

    def test_partially_solved_status_needs_matching_state(self):
        c=self.card();c['status']['value']='PARTIALLY_SOLVED';self.save_card(c)
        with self.assertRaises(engine.IntegrityError):engine.load_repository(self.root)

    def test_card_verified_open_needs_matching_state(self):
        c=self.card()
        c['status'].update(value='VERIFIED_OPEN',last_verified=str(date.today()),confidence='source_supported')
        c['audit']['open_status']='verified';self.save_card(c)
        with self.assertRaisesRegex(engine.IntegrityError,'has not reached'):engine.load_repository(self.root)

    def test_promotion_is_projected_into_the_export(self):
        self.promote(self.add_open_source())
        data=engine.load_repository(self.root)
        card=engine.export_cards(data)[0]
        self.assertEqual(card['research_state'],'VERIFIED_OPEN')
        self.assertEqual(card['status']['value'],'VERIFIED_OPEN')
        self.assertEqual(card['status']['last_verified'],date.today().isoformat())
        self.assertEqual(card['status']['confidence'],'source_supported')
        self.assertEqual(card['audit']['open_status'],'verified')
        self.assertEqual(card['status']['evidence'][0]['source_id'],'SRC-PROBE')
        self.assertEqual(data['stale_open_status'],[])

    def test_projected_promotion_expires_and_blocks_export(self):
        self.promote(self.add_open_source())
        data=engine.load_repository(self.root,today=date.today()+timedelta(days=200))
        self.assertEqual(data['stale_open_status'],['MF-0000'])
        with self.assertRaises(engine.IntegrityError):engine.export_cards(data)

    def test_projection_downgrades_after_leaving_verified_open(self):
        self.promote(self.add_open_source())
        engine.append_transition(self.root, dict(problem_id='MF-0000',
            **{'from':'VERIFIED_OPEN','to':'BLOCKED'},
            actor='critic', reason='Synthetic downgrade fixture.', evidence=[]))
        data=engine.load_repository(self.root)
        card=engine.export_cards(data)[0]
        self.assertEqual(card['research_state'],'BLOCKED')
        self.assertEqual(card['status']['value'],'OPEN_STATUS_UNVERIFIED')
        self.assertEqual(card['audit']['open_status'],'unverified')
        self.assertEqual(data['stale_open_status'],[])


class ManifestTests(unittest.TestCase):
    """Recorded distribution hashes are a gate, not a one-off audit."""

    def test_tracked_tree_matches_the_manifest(self):
        root=Path(__file__).resolve().parents[1]
        if not (root/'.git').exists(): self.skipTest('source checkout required')
        result=subprocess.run([sys.executable,str(root/'scripts/verify_manifest.py'),'--root',str(root)],
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
