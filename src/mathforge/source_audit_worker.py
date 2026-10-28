"""Trusted finite frequency calibration. No client-supplied code or network access.

This computes a finite table, not an accepted proof of the general conjecture.
"""
import hashlib
import json
from pathlib import Path
import sys
import time


def finite_frequency_table():
    rows = []
    # A ground subset is a two-bit mask; a family is a four-bit mask.
    for family in range(16):
        members = [x for x in range(4) if family & (1 << x)]
        closed = all((x | y) in members for x in members for y in members)
        excluded = members == [0]  # exactly {empty}; the empty family stays included
        frequencies = [sum(bool(x & (1 << i)) for x in members) for i in range(2)]
        witnesses = [i for i in range(2) if 2 * frequencies[i] >= len(members)]
        # Independent representation: construct actual sets and their unions.
        sets = [frozenset(i for i in range(2) if x & (1 << i)) for x in members]
        set_closed = all(x.union(y) in sets for x in sets for y in sets)
        set_witnesses = [i for i in range(2) if 2 * sum(i in x for x in sets) >= len(sets)]
        if closed != set_closed or witnesses != set_witnesses:
            raise ValueError('independent encodings disagree')
        if closed and not excluded and not witnesses:
            raise ValueError('finite counterexample found; retain table and review source mapping')
        rows.append(dict(family_mask=family, members=members, union_closed=closed,
                         excluded_singleton_empty=excluded, frequencies=frequencies,
                         witnesses=witnesses, applicable=closed and not excluded))
    return dict(ground_size=2, families_examined=16, rows=rows,
                applicable_families=sum(r['applicable'] for r in rows),
                all_applicable_have_witness=True, encodings_agree=True,
                scientific_status='unverified', proof_kernel_verified=False,
                scope='Only families of subsets of Fin 2. No general conjecture conclusion.')


def deny_external(event, args):
    if event.startswith(('socket.', 'subprocess.', 'os.system', 'os.exec', 'os.spawn')):
        raise PermissionError('network and child execution are prohibited in this trusted worker')


def main():
    # The controller assigns its Job Object before releasing this handshake.
    if sys.stdin.readline().strip() != 'START':
        return 2
    sys.addaudithook(deny_external)
    start = time.perf_counter()
    folder = Path(sys.argv[1])
    request = json.loads((folder / 'INPUT.json').read_text(encoding='utf8'))
    source = (folder / 'SOURCE.lean').read_bytes()
    if hashlib.sha256(source).hexdigest() != request['source_sha256']:
        raise ValueError('worker source binding mismatch')
    text = source.decode('utf8')
    if request['formal_statement'] not in text or request['variant_signature'] not in text:
        raise ValueError('formal declaration binding mismatch')
    if not all(s in text for s in request['required_source_fragments']):
        raise ValueError('source hypothesis context mismatch')
    print(json.dumps(dict(event='source_binding_checked', sha256=request['source_sha256']), sort_keys=True), flush=True)
    result = finite_frequency_table()
    result.update(source_sha256=request['source_sha256'], statement_sha256=request['statement_sha256'],
                  source_context_checked=True, wall_seconds=time.perf_counter()-start,
                  cpu_seconds=time.process_time(), execution_mode=request['execution_mode'])
    with (folder / 'RESULT.json').open('x', encoding='utf8', newline='\n') as output:
        json.dump(result, output, sort_keys=True, indent=2)
    print(json.dumps(dict(event='finite_calibration_finished', families=16,
                         applicable=result['applicable_families'], scientific_status='unverified'), sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
