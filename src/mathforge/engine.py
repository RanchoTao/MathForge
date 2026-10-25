# Adapted foundational engine; historical research validators intentionally excluded.
"""Offline integrity and state-journal CLI. Does not execute mathematical research."""


from __future__ import annotations


import argparse


import copy


import hashlib


import json


import os


from pathlib import Path


import sys


import unicodedata


import uuid


from functools import lru_cache


from datetime import date, datetime, timezone


from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path.cwd()


class IntegrityError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    raw = path.read_bytes()
    require(not raw or raw.endswith(b'\n'), f'{path}: incomplete final record; preserve and recover explicitly')
    return [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


@lru_cache(maxsize=64)
def schema_validator(text):
    spec = json.loads(text)
    Draft202012Validator.check_schema(spec)
    return Draft202012Validator(spec, format_checker=FormatChecker())


def validate_schema(root, kind, record):
    text = (root / 'schemas' / f'{kind}.schema.json').read_text(encoding='utf-8')
    errors = sorted(schema_validator(text).iter_errors(record), key=lambda e: str(e.path))
    if errors:
        raise IntegrityError(f'{kind}: {errors[0].json_path}: {errors[0].message}')


def keyed(records, field):
    result = {}
    for row in records:
        require(row[field] not in result, f'duplicate {field}: {row[field]}')
        result[row[field]] = row
    return result


def evidence_refs(node):
    if isinstance(node, dict):
        if 'source_id' in node:
            yield node['source_id']
        for value in node.values():
            yield from evidence_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from evidence_refs(value)


def check_evidence(node, sources):
    for sid in evidence_refs(node):
        require(sid in sources, f'unknown source: {sid}')


def check_open_evidence(evidence, sources, when, max_age, problem_id, statement):
    supported = False
    for item in evidence:
        if item['supports'] != 'open_status':
            continue
        source = sources[item['source_id']]
        age = (when - date.fromisoformat(source['retrieved_on'])).days
        binding = source.get('status_bindings', {}).get(problem_id)
        if source['kind'] == 'official_problem_list' and source['access'] == 'full_text' and 0 <= age <= max_age and binding is not None and binding['statement_sha256'] == digest(statement) and binding['locator'] == item['locator']:
            supported = True
    require(supported, 'VERIFIED_OPEN requires fresh full-text official-list evidence in Phase 0')


STATUS_VALUES = {'OPEN_STATUS_UNVERIFIED', 'VERIFIED_OPEN', 'PARTIALLY_SOLVED', 'KNOWN_RESULT', 'FALSIFIED'}

# A status value above the default must already be justified by the workflow state
# recorded in the same card. OPEN_STATUS_UNVERIFIED is the default; VERIFIED_OPEN is
# checked separately because it also carries evidence and a binding.
STATUS_STATES = {
    'KNOWN_RESULT': {'COLLISION_FOUND', 'KNOWN_RESULT_REDISCOVERED', 'PROVED'},
    'PARTIALLY_SOLVED': {'PARTIALLY_SOLVED', 'PARTIAL_PROGRESS'},
    'FALSIFIED': {'FALSIFIED'},
}


def project_status(card, events):
    """Derive the current open-status projection from the card plus the event log.

    The atlas record is a genesis snapshot and is never rewritten, so a promotion
    recorded as an event never appears in ``card['status']``. Anything that reads or
    exports the claimed status must use this projection, not the raw field.
    """
    status = copy.deepcopy(card['status'])
    audit = copy.deepcopy(card['audit'])
    for event in events:
        if event['problem_id'] != card['problem_id']:
            continue
        if event['to'] == 'VERIFIED_OPEN':
            status.update(value='VERIFIED_OPEN', last_verified=event['at'][:10],
                          confidence='source_supported',
                          evidence=[item for item in event['evidence'] if item['supports'] == 'open_status'])
            audit['open_status'] = 'verified'
        elif status['value'] == 'VERIFIED_OPEN':
            status.update(value='OPEN_STATUS_UNVERIFIED', confidence='unknown')
            audit['open_status'] = 'unverified'
    return status, audit


def check_edge(before, after, transitions):
    require(before in transitions and after in transitions[before], f'illegal transition: {before} -> {after}')


def load_repository(root=ROOT, today=None):
    root = Path(root)
    today = today or date.today()
    policy = read_json(root / 'orchestration/policy.json')
    require(policy['phase'] == 0 and policy['research_execution_enabled'] is False and policy['proof_acceptance_enabled'] is False, 'Phase 0 policy cannot enable research')
    require(set(policy['allowed_targets']) <= {'MAPPED','OPEN_STATUS_UNVERIFIED','VERIFIED_OPEN','COLLISION_FOUND','BLOCKED','ABANDONED'}, 'policy targets exceed the hard-coded Phase 0 boundary')
    transitions = read_json(root / 'orchestration/transitions.json')
    cards = read_jsonl(root / 'atlas/atlas.jsonl')
    require(bool(cards), 'atlas is missing or empty')
    sources_list = read_json(root / 'knowledge/sources/catalog.json')
    fields_list = read_json(root / 'atlas/fields/taxonomy.json')
    negatives_list = [read_json(p) for p in sorted((root / 'negative_knowledge').rglob('*.json'))]
    candidates = read_json(root / 'research/candidates/shortlist.json')
    definitions = keyed(read_json(root / 'knowledge/definitions/catalog.json'), 'definition_id')
    for kind, rows in [('problem', cards), ('source', sources_list), ('field', fields_list), ('negative', negatives_list), ('candidate', candidates)]:
        for row in rows:
            validate_schema(root, kind, row)
    problems = keyed(cards, 'problem_id')
    sources = keyed(sources_list, 'source_id')
    fields = keyed(fields_list, 'field_id')
    negatives = keyed(negatives_list, 'negative_id')
    keyed(candidates, 'candidate_id')
    for source in sources.values():
        require(date.fromisoformat(source['retrieved_on']) <= today, 'source retrieval is in the future')
        require(datetime.fromisoformat(source['provenance']['recorded_at']).date() <= today, 'source provenance is in the future')
    visiting, visited = set(), set()

    def visit(fid):
        require(fid in fields, f'unknown field: {fid}')
        require(fid not in visiting, f'cyclic field taxonomy: {fid}')
        if fid in visited:
            return
        visiting.add(fid)
        for parent in fields[fid]['parents']:
            visit(parent)
        for related in fields[fid]['related_fields']:
            require(related in fields, f'unknown related field: {related}')
        visiting.remove(fid)
        visited.add(fid)
    for fid in fields:
        visit(fid)
    names = {}
    for card in cards:
        pid = card['problem_id']
        for name in [card['name'], *card['aliases']]:
            token = normalize(name)
            require(token and token not in names, f'duplicate name or alias: {name}')
            names[token] = pid
        for fid in card['field'] + card['subfields']:
            require(fid in fields, f'unknown field: {fid}')
        for sid in sum(card['sources'].values(), []):
            require(sid in sources, f'unknown source: {sid}')
        if card['origin']['first_known_source'] is not None:
            require(card['origin']['first_known_source'] in sources, 'unknown origin source')
        check_evidence(card, sources)
        for rel, ids in card['dependency_graph'].items():
            for target in ids:
                require(target in (definitions if rel == 'prerequisites' else problems), f'broken {rel}: {target}')
                require(target != pid, 'self-referential problem edge')
        for nid in card['negative_knowledge_links'] + card['known_counterexamples'] + card['known_barriers']:
            require(nid in negatives, f'unknown negative knowledge: {nid}')
            require(pid in negatives[nid]['problem_ids'], f'negative artifact {nid} does not apply to {pid}')
        before = 'UNMAPPED'
        previous_time = None
        for event in card['research_history']:
            require(event['from'] == before, f'{pid}: noncontiguous history')
            check_edge(before, event['to'], transitions)
            instant = datetime.fromisoformat(event['at'])
            require(instant.date() <= today, 'history is in the future')
            require(previous_time is None or instant >= previous_time, 'history timestamps decrease')
            if event['to'] == 'VERIFIED_OPEN':
                check_open_evidence(event['evidence'], sources, instant.date(), policy['open_evidence_max_age_days'],pid,card['canonical_statement'])
            require(event['to'] in policy['allowed_targets'], 'genesis contains Phase 0 forbidden state')
            previous_time = instant
            before = event['to']
        require(before == card['research_state'], f'{pid}: history/state mismatch')
        status = card['status']
        require(status['value'] in STATUS_VALUES, 'unknown status value')
        if status['value'] == 'VERIFIED_OPEN':
            require(card['research_state'] == 'VERIFIED_OPEN', 'card claims VERIFIED_OPEN that the workflow has not reached')
            require(status['last_verified'] is not None and card['audit']['open_status'] == 'verified' and status['confidence'] == 'source_supported', 'missing status provenance')
            require(date.fromisoformat(status['last_verified']) <= today, 'status verification is in the future')
            check_open_evidence(status['evidence'], sources, date.fromisoformat(status['last_verified']), policy['open_evidence_max_age_days'],pid,card['canonical_statement'])
        else:
            require(card['audit']['open_status'] == 'unverified', 'inconsistent open-status audit')
            justified = STATUS_STATES.get(status['value'])
            if justified is not None:
                require(card['research_state'] in justified, f'status {status["value"]} is not supported by workflow state {card["research_state"]}')
    for negative in negatives_list:
        check_evidence(negative, sources)
        for pid in negative['problem_ids']:
            require(pid in problems, f'negative references nonexistent problem: {pid}')
        if negative['supersedes'] is not None:
            require(negative['supersedes'] in negatives and negative['supersedes'] != negative['negative_id'], 'invalid superseded negative ID')
        if negative['kind'] == 'false_conjecture':
            path = (root / negative['details']['exact_code_path']).resolve()
            require(path.is_relative_to(root.resolve()) and path.is_file(), 'invalid counterexample code path')
            require(hashlib.sha256(path.read_bytes()).hexdigest() == negative['details']['code_sha256'], 'counterexample code hash mismatch')
    for candidate in candidates:
        require(candidate['problem_id'] in problems, 'candidate references nonexistent problem')
        require(candidate['exact_question'] == problems[candidate['problem_id']]['canonical_statement'], 'shortlist scope differs from card')
        for sid in candidate['literature']:
            require(sid in sources, 'candidate has broken literature reference')
    for kind, folder, id_key in [('conjecture','conjectures','conjecture_id'),('theorem','theorems','theorem_id')]:
        records = [read_json(p) for p in sorted((root / 'atlas' / folder).glob('*.json'))]
        for record in records:
            validate_schema(root, kind, record)
            require(record['problem_id'] in problems, f'{kind}: nonexistent problem')
            check_evidence(record, sources)
        keyed(records, id_key)
    events = read_jsonl(root / 'orchestration/events.jsonl')
    states = {pid: card['research_state'] for pid, card in problems.items()}
    previous_hash = None
    ids = set()
    previous_at = None
    for event in events:
        validate_schema(root, 'event', event)
        require(event['event_id'] not in ids, 'duplicate event ID')
        ids.add(event['event_id'])
        require(event['problem_id'] in problems, 'event references nonexistent problem')
        require(event['previous_hash'] == previous_hash, 'event hash chain broken')
        payload = {k:v for k,v in event.items() if k != 'hash'}
        require(digest(payload) == event['hash'], 'event hash mismatch')
        require(event['from'] == states[event['problem_id']], 'event source state mismatch')
        check_transition(root, event, sources, policy, transitions, negatives, today,problems)
        instant = datetime.fromisoformat(event['at'])
        genesis_time = datetime.fromisoformat(problems[event['problem_id']]['research_history'][-1]['at'])
        require(instant >= genesis_time and (previous_at is None or instant >= previous_at), 'event chronology invalid')
        previous_at = instant
        states[event['problem_id']] = event['to']
        previous_hash = event['hash']
    projected = {pid: project_status(card, events) for pid, card in problems.items()}
    stale = [pid for pid, (status, _) in projected.items()
             if status['value'] == 'VERIFIED_OPEN' and (today - date.fromisoformat(status['last_verified'])).days > policy['open_evidence_max_age_days']]
    return dict(problems=problems, sources=sources, fields=fields, negatives=negatives, candidates=candidates, events=events, states=states, policy=policy, transitions=transitions, projected_status=projected, stale_open_status=stale)


def replay_blocks(pid, negatives):
    return [n['negative_id'] for n in negatives.values() if pid in n['problem_ids'] and n['kind'] == 'replay_prohibition']


def check_transition(root, event, sources, policy, transitions, negatives, today,problems):
    check_edge(event['from'], event['to'], transitions)
    # Hard coded boundary also protects against an edited allowed_targets list.
    allowed = {'MAPPED','OPEN_STATUS_UNVERIFIED','VERIFIED_OPEN','COLLISION_FOUND','BLOCKED','ABANDONED'}
    require(event['to'] in allowed and event['to'] in policy['allowed_targets'], 'Phase 0 forbids research/proof state transitions')
    require(event['actor'] in policy['enabled_roles'], 'role is disabled in Phase 0')
    check_evidence(event, sources)
    when = datetime.fromisoformat(event['at']).date()
    require(when <= today, 'event is in the future')
    if event['to'] == 'VERIFIED_OPEN':
        check_open_evidence(event['evidence'], sources, when, policy['open_evidence_max_age_days'],event['problem_id'],problems[event['problem_id']]['canonical_statement'])
    if event['to'] == 'COLLISION_FOUND':
        require(any(e['supports'] == 'known_result' and sources[e['source_id']]['kind'] == 'published_paper' and sources[e['source_id']]['access'] == 'full_text' for e in event['evidence']), 'collision requires a full-text published source; proof claims are insufficient')


def append_transition(root, request, today=None):
    """Single writer lock + one append. Torn writes cause fail-closed recovery, not repair."""
    root = Path(root)
    today = today or date.today()
    require(set(request) == {'problem_id','from','to','actor','reason','evidence'}, 'request needs exactly problem_id/from/to/actor/reason/evidence')
    lock = root / 'orchestration/.writer.lock'
    fd = None
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        data = load_repository(root, today)
        pid = request['problem_id']
        require(pid in data['problems'], 'unknown problem')
        require(request['from'] == data['states'][pid], 'stale expected state; reload before proposing')
        event = {**request,'event_id':str(uuid.uuid4()),'at':datetime.now(timezone.utc).isoformat(),'previous_hash':data['events'][-1]['hash'] if data['events'] else None}
        event['hash'] = digest(event)
        validate_schema(root,'event',event)
        check_transition(root,event,data['sources'],data['policy'],data['transitions'],data['negatives'],today,data['problems'])
        # New promotion must use current evidence, even if an attacker supplies historical data.
        if event['to']=='VERIFIED_OPEN':
            check_open_evidence(event['evidence'],data['sources'],today,data['policy']['open_evidence_max_age_days'],pid,data['problems'][pid]['canonical_statement'])
        previous_at = datetime.fromisoformat(data['events'][-1]['at']) if data['events'] else datetime.fromisoformat(data['problems'][pid]['research_history'][-1]['at'])
        require(datetime.fromisoformat(event['at']) >= previous_at, 'clock moved backwards')
        with (root / 'orchestration/events.jsonl').open('ab') as stream:
            stream.write((canonical(event)+'\n').encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        return event
    except FileExistsError as exc:
        raise IntegrityError('writer lock exists; inspect owner and journal before recovery') from exc
    finally:
        if fd is not None:
            os.close(fd)
            lock.unlink()


def export_cards(data):
    require(not data['stale_open_status'], 'open-status evidence expired; audit before exporting as current')
    cards = copy.deepcopy(data['problems'])
    for event in data['events']:
        card = cards[event['problem_id']]
        card['research_state'] = event['to']
        card['research_history'].append({k:event[k] for k in ['from','to','at','actor','reason','evidence']})
    # Overlay the projected open status: the raw card field is the genesis snapshot only.
    for pid, card in cards.items():
        card['status'], card['audit'] = copy.deepcopy(data['projected_status'][pid])
    return list(cards.values())

