#!/usr/bin/env python3
"""Offline tracked-source and reachable-history hygiene; no credential values printed."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import marshal
import os
import re
import stat
import zipfile
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


def exported_files(allow_bytecode=False):
    """Inspect export artifacts too, without descending into private runtime trees."""
    files = []
    for directory, dirs, names in os.walk(ROOT, followlinks=False):
        base = Path(directory).relative_to(ROOT)
        for name in list(dirs):
            path = base / name
            if (name in DIRECTORIES and not (allow_bytecode and name == '__pycache__')) or (ROOT / path).is_symlink():
                files.append(path)
                dirs.remove(name)
        files.extend(base / name for name in names)
    return files


def export_inventory(problems):
    """Inventory is provenance metadata, not permission to include private files."""
    manifest = ROOT / 'MANIFEST.sha256'
    if not manifest.exists():
        return None
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > MAX_BYTES:
        problems.append('invalid source inventory')
        return {}
    inventory = {}
    try:
        lines = manifest.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError):
        problems.append('unreadable source inventory')
        return {}
    for line in lines:
        match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
        if not match:
            problems.append('invalid source inventory entry')
            continue
        digest, name = match.groups()
        path = Path(name)
        if (not path.parts or path.is_absolute() or '..' in path.parts or '\\' in name
                or ':' in path.parts[0]
                or name != path.as_posix() or name in inventory):
            problems.append('unsafe or duplicate source inventory entry')
            continue
        inventory[name] = digest
    return inventory


def generated_bytecode(path, inventory):
    """Only current-interpreter cache files for inventoried sources may be incidental."""
    if inventory is None or path.as_posix() in inventory or path.parent.name != '__pycache__':
        return False
    match = re.fullmatch(r'(.+)\.' + re.escape(sys.implementation.cache_tag)
                         + r'(?:\.opt-([012]))?\.pyc', path.name)
    if not match:
        return False
    source = path.parent.parent / (match[1] + '.py')
    full = ROOT / path
    if (private_path(source) or source.as_posix() not in inventory or full.is_symlink() or not full.is_file()
            or not full.resolve().is_relative_to(ROOT) or full.stat().st_size > MAX_BYTES):
        return False
    data = full.read_bytes()
    if (len(data) < 16 or data[:4] != importlib.util.MAGIC_NUMBER
            or int.from_bytes(data[4:8], 'little') not in (0, 1, 3)):
        return False
    source_file = ROOT / source
    if source_file.is_symlink() or not source_file.is_file() or source_file.stat().st_size > MAX_BYTES:
        return False
    source_bytes = source_file.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != inventory[source.as_posix()]:
        return False
    try:
        # Compile trusted source; never unmarshal or execute the incidental cache.
        lexical_source = Path(__file__).absolute().parents[1] / source
        filenames = {str(source_file), str(lexical_source)}
        if sys.platform == 'darwin' and str(source_file).startswith('/private/'):
            filenames.add(str(source_file)[len('/private'):])
        for filename in filenames:
            expected = compile(source_bytes, filename, 'exec', dont_inherit=True,
                               optimize=int(match[2] or 0))
            # CPython's pyc writer retains another reference while marshaling code.
            retained = (expected,)
            if data[16:] == marshal.dumps(retained[0]):
                return True
        return False
    except (SyntaxError, ValueError):
        return False


def scan_archive(archive, problems):
    """Scan the actual distribution members, never ignore generated runtime files."""
    names = set()
    regular_names = set()
    count = 0
    try:
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                count += 1
                name = member.filename.rstrip('/') if member.is_dir() else member.filename
                path = Path(name)
                if (not path.parts or path.is_absolute() or '..' in path.parts or '\\' in name
                        or ':' in path.parts[0] or name != path.as_posix() or name in names):
                    problems.append('unsafe or duplicate archive path')
                    continue
                names.add(name)
                reason = private_path(path)
                if reason:
                    problems.append(reason + ': ' + name)
                    continue
                mode = stat.S_IFMT(member.external_attr >> 16)
                if (mode not in (0, stat.S_IFREG, stat.S_IFDIR)
                        or (mode != 0 and (mode == stat.S_IFDIR) != member.is_dir())):
                    problems.append('unreviewed archive file type: ' + name)
                    continue
                if member.is_dir():
                    continue
                regular_names.add(name)
                if member.file_size > MAX_BYTES:
                    problems.append('oversized unscanned archive file: ' + name)
                    continue
                for marker in secret_markers(package.read(member).decode('utf-8', errors='replace')):
                    problems.append(marker + ' marker: ' + name)
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError):
        problems.append('archive inspection failed')
    for needed in ('LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', '.gitignore', 'README.md', 'docs/GITHUB_SETUP.md'):
        if needed not in regular_names:
            problems.append('missing publication file: ' + needed)
    return count


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


def check(archive=None):
    problems = []
    if archive is not None:
        count = scan_archive(archive, problems)
        return report(problems, count, 0, False)
    repository = git('rev-parse', '--show-toplevel')
    own_git = repository.returncode == 0 and Path(os.fsdecode(repository.stdout).strip()).resolve() == ROOT
    command = git('ls-files', '-z') if own_git else None
    if own_git and command.returncode:
        problems.append('tracked source enumeration failed')
    inventory = None if own_git else export_inventory(problems)
    files = [Path(os.fsdecode(row)) for row in command.stdout.split(b'\0') if row] if command and command.returncode == 0 and command.stdout else exported_files(allow_bytecode=inventory is not None)
    if inventory is not None:
        files = sorted(set(files) | {Path(name) for name in inventory})
    for path in files:
        if path.is_absolute() or '..' in path.parts:
            problems.append('unsafe tracked path: ' + str(path))
            continue
        reason = private_path(path)
        if reason:
            if not generated_bytecode(path, inventory):
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
        content = full.read_bytes()
        if inventory is not None and path.as_posix() in inventory:
            if hashlib.sha256(content).hexdigest() != inventory[path.as_posix()]:
                problems.append('source inventory hash mismatch: ' + str(path))
        for marker in secret_markers(content.decode('utf-8', errors='replace')):
            problems.append(marker + ' marker: ' + str(path))
    history_count = scan_history(problems) if own_git else 0
    for needed in ('LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', '.gitignore', 'README.md', 'docs/GITHUB_SETUP.md'):
        if not (ROOT / needed).is_file():
            problems.append('missing publication file: ' + needed)
    return report(problems, len(files), history_count, own_git)


def report(problems, file_count, history_count, own_git):
    print('PUBLICATION AUDIT:', 'PASS' if not problems else 'FAIL')
    print(f'Inspected {file_count} release paths and {history_count} reachable history blobs.')
    print('History:', 'reachable local refs only' if own_git else 'NOT_APPLICABLE (source export has no Git history)')
    print('Dedicated secret scanner: NOT_TESTED. Heuristic patterns cannot certify absence of secrets or license compliance.')
    for error in problems:
        print(' -', error)
    return 1 if problems else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Strictly inspect every member of a release ZIP')
    sys.exit(check(parser.parse_args().archive))
