"""Verify (or rebuild) the distributed file manifest against the tracked tree.

CURRENT_FILE_MANIFEST.json records the bytes actually shipped for the current
commit. It is a gate, not a one-off audit: CI runs this script so that a later
edit cannot silently leave the recorded hashes behind.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'CURRENT_FILE_MANIFEST.json'
DEFAULT_SCOPE = ('Distributed file snapshot, excluding this manifest itself. Verify against the '
                 'accepted commit in the delivery report, not an advancing branch name.')


def tracked(root):
    try:
        output = subprocess.run(['git', 'ls-files', '-z'], cwd=root, check=True,
                                capture_output=True).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'cannot list tracked files (a git checkout is required): {error}')
    return sorted(name for name in output.decode('utf-8').split('\0') if name)


def snapshot(root):
    entries = []
    for name in tracked(root):
        if name == MANIFEST:
            continue
        payload = (root / name).read_bytes()
        entries.append(dict(path=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
    return entries


def compare(recorded, current):
    by_path = {row['path']: row for row in recorded}
    current_paths = {row['path'] for row in current}
    problems = []
    for row in current:
        old = by_path.get(row['path'])
        if old is None:
            problems.append(f"added:    {row['path']}")
        elif old.get('sha256') != row['sha256'] or old.get('bytes') != row['bytes']:
            problems.append(f"changed:  {row['path']}")
    for name in sorted(set(by_path) - current_paths):
        problems.append(f'removed:  {name}')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--rebuild', action='store_true', help='rewrite the manifest instead of checking it')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    path = root / MANIFEST
    current = snapshot(root)
    if args.rebuild:
        scope = DEFAULT_SCOPE
        if path.exists():
            scope = json.loads(path.read_text(encoding='utf-8')).get('scope', DEFAULT_SCOPE)
        path.write_text(json.dumps(dict(scope=scope, files=current), indent=2) + '\n', encoding='utf-8')
        print(f'rebuilt {MANIFEST}: {len(current)} entries')
        return 0
    if not path.exists():
        print(f'{MANIFEST} is missing; run this script with --rebuild')
        return 1
    problems = compare(json.loads(path.read_text(encoding='utf-8'))['files'], current)
    if problems:
        print(f'{MANIFEST} does not match the tracked tree ({len(problems)} of {len(current)} entries):')
        for line in problems:
            print(' ', line)
        print('run `python scripts/verify_manifest.py --rebuild` and commit the result')
        return 1
    print(f'PASS: {len(current)} tracked files match {MANIFEST}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
