#!/usr/bin/env python3
"""Offline tracked-source and reachable-history hygiene; no credential values printed."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from exelia.security import is_sensitive_path, secret_markers

DIRECTORIES = {'.exelia', '.exelia-install', '.exelia-tools', 'node_modules', '__pycache__',
               '.git', '.venv', 'venv', '.cache', '.pytest_cache', '.ruff_cache',
               'playwright-report', 'test-results'}
BUNDLED_SKILLS = {'premium-motion', 'project-delivery', 'python-backend-engineering'}
MAX_BYTES = 10_000_000


def private_path(path):
    if any(part in DIRECTORIES for part in path.parts):
        return 'private runtime path'
    if is_sensitive_path(path):
        return 'credential filename'
    parts = path.parts
    if len(parts) >= 3 and parts[:2] == ('.agents', 'skills') and parts[2] not in BUNDLED_SKILLS:
        return 'downloaded external skill'
    if path.suffix.lower() in {'.log', '.pyc', '.pyo'} or path.name in {'.DS_Store', '.coverage'}:
        return 'private runtime file'
    return None


def git(*args, data=None):
    return subprocess.run(['git', *args], cwd=ROOT, input=data, capture_output=True)


def exported_files():
    """Inspect export artifacts too, without descending into private runtime trees."""
    files = []
    for directory, dirs, names in os.walk(ROOT, followlinks=False):
        base = Path(directory).relative_to(ROOT)
        for name in list(dirs):
            path = base / name
            if name in DIRECTORIES or (ROOT / path).is_symlink():
                files.append(path)
                dirs.remove(name)
        files.extend(base / name for name in names)
    return files


def scan_history(problems):
    trees = git('log', '--all', '--format=%T')
    if trees.returncode:
        problems.append('history enumeration failed')
        return 0
    objects = {}
    checked_paths = set()
    # Blob deduplication loses filename aliases; inspect each historical tree first.
    for tree in sorted(set(trees.stdout.splitlines())):
        entries = git('ls-tree', '-r', '-z', tree.decode('ascii'))
        if entries.returncode:
            problems.append('history tree inspection failed: ' + tree.decode('ascii')[:12])
            continue
        for row in entries.stdout.split(b'\0'):
            if not row:
                continue
            metadata, raw_path = row.split(b'\t', 1)
            _, kind, raw_oid = metadata.split()
            if kind != b'blob':
                continue
            oid = raw_oid.decode('ascii')
            path = os.fsdecode(raw_path)
            if path not in checked_paths:
                checked_paths.add(path)
                reason = private_path(Path(path))
                if reason:
                    problems.append(f'history {reason}: {path} ({oid[:12]})')
            if not private_path(Path(path)):
                objects.setdefault(oid, path)
    if not objects:
        return 0
    metadata = git('cat-file', '--batch-check', data=('\n'.join(objects) + '\n').encode())
    if metadata.returncode:
        problems.append('history object inspection failed')
        return 0
    blobs = []
    for row in metadata.stdout.splitlines():
        oid, kind, size = row.decode('ascii').split()
        if kind != 'blob':
            continue
        reason = private_path(Path(objects[oid]))
        if reason:
            problems.append(f'history {reason}: {objects[oid]} ({oid[:12]})')
            continue
        if int(size) > MAX_BYTES:
            problems.append(f'oversized unscanned history blob: {oid[:12]}')
            continue
        blobs.append(oid)
    # Batch avoids one process per historical file; values remain in memory only.
    payload = git('cat-file', '--batch', data=('\n'.join(blobs) + '\n').encode()) if blobs else None
    if payload is not None and payload.returncode:
        problems.append('history content scan failed')
        return 0
    offset = 0
    for oid in blobs:
        end = payload.stdout.index(b'\n', offset)
        size = int(payload.stdout[offset:end].split()[2])
        content = payload.stdout[end + 1:end + 1 + size]
        offset = end + 1 + size + 1
        for marker in secret_markers(content.decode('utf-8', errors='replace')):
            problems.append(f'history {marker} marker: {objects[oid]} ({oid[:12]})')
    return len(blobs)


def check():
    problems = []
    repository = git('rev-parse', '--show-toplevel')
    own_git = repository.returncode == 0 and Path(os.fsdecode(repository.stdout).strip()).resolve() == ROOT
    command = git('ls-files', '-z') if own_git else None
    if own_git and command.returncode:
        problems.append('tracked source enumeration failed')
    files = [Path(os.fsdecode(row)) for row in command.stdout.split(b'\0') if row] if command and command.returncode == 0 and command.stdout else exported_files()
    for path in files:
        if path.is_absolute() or '..' in path.parts:
            problems.append('unsafe tracked path: ' + str(path))
            continue
        reason = private_path(path)
        if reason:
            problems.append(reason + ': ' + str(path))
            continue
        full = ROOT / path
        if full.is_symlink() or not full.resolve().is_relative_to(ROOT):
            problems.append('unreviewed symlink: ' + str(path))
            continue
        if not full.is_file():
            problems.append('missing release file: ' + str(path))
            continue
        if full.stat().st_size > MAX_BYTES:
            problems.append('oversized unscanned release file: ' + str(path))
            continue
        for marker in secret_markers(full.read_bytes().decode('utf-8', errors='replace')):
            problems.append(marker + ' marker: ' + str(path))
    history_count = scan_history(problems) if own_git else 0
    for needed in ('LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', '.gitignore', 'README.md', 'docs/GITHUB_SETUP.md'):
        if not (ROOT / needed).is_file():
            problems.append('missing publication file: ' + needed)
    print('PUBLICATION AUDIT:', 'PASS' if not problems else 'FAIL')
    print(f'Inspected {len(files)} release paths and {history_count} reachable history blobs.')
    print('History:', 'reachable local refs only' if own_git else 'NOT_APPLICABLE (source export has no Git history)')
    print('Dedicated secret scanner: NOT_TESTED. Heuristic patterns cannot certify absence of secrets or license compliance.')
    for error in problems:
        print(' -', error)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(check())
