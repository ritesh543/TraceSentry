#!/usr/bin/env python3
"""Verify SHA-256 manifest, reporting missing, tampered, or unexpected files."""
from pathlib import Path
import hashlib
import sys

root = Path(__file__).resolve().parents[1]
manifest = root / 'verification' / 'MANIFEST.sha256'
if not manifest.is_file():
    print('ERROR: missing MANIFEST.sha256', file=sys.stderr)
    sys.exit(1)
lines = [line.strip() for line in manifest.read_text().splitlines() if line.strip()]
seen = set()
failed = False
for item in lines:
    sha, sep, name = item.partition('  ')
    if not sep or len(sha) != 64 or name in seen:
        print('BAD MANIFEST ENTRY:', item)
        failed = True
        continue
    seen.add(name)
    fp = root / name
    if not fp.is_file():
        print('MISSING:', name)
        failed = True
        continue
    actual = hashlib.sha256(fp.read_bytes()).hexdigest()
    if actual != sha:
        print('MISMATCH:', name)
        failed = True
untracked = []
for fp in sorted(root.rglob('*')):
    if fp.is_file() and not any(x in fp.parts for x in ('__pycache__','.pytest_cache','.git')):
        name = fp.relative_to(root).as_posix()
        if name != 'verification/MANIFEST.sha256' and name not in seen:
            untracked.append(name)
if untracked:
    print('UNTRACKED FILES:', ', '.join(untracked))
    failed = True
if failed:
    sys.exit(1)
print('PASS: SHA-256 manifest verified:', len(seen), 'files.')
