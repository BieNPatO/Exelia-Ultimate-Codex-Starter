#!/usr/bin/env python3
"""Validate a checkpoint's exact paths before any index mutation."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exelia.security import is_sensitive_path, secret_markers


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def paths(*args):
    return {p.decode() for p in git(*args).split(b'\0') if p}


def main():
    args = sys.argv[1:]
    staged = paths('diff', '--cached', '--name-only', '-z', '--no-renames')
    if args == ['--staged']:
        selected = staged
    elif args == ['--initial']:
        if subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            raise ValueError('--initial requires a repository without commits')
        manifest = ROOT / 'MANIFEST.sha256'
        if not manifest.is_file():
            raise ValueError('Initial checkpoint requires MANIFEST.sha256 source inventory')
        selected = {line.split('  ', 1)[1] for line in manifest.read_text().splitlines() if '  ' in line}
        selected.add('MANIFEST.sha256')
        unknown = (paths('ls-files', '--others', '--exclude-standard', '-z') | staged) - selected
        if unknown:
            raise ValueError('Unlisted initial source files; review source inventory first: ' + ', '.join(sorted(unknown)))
        selected = {p for p in selected if (ROOT / p).is_file()}
    else:
        if not args or any(a.startswith('-') for a in args):
            raise ValueError('Supply exact file paths, --staged, or --initial')
        selected = set(args)
    if staged - selected:
        raise ValueError('Unrelated staged paths; existing index preserved')
    for path in selected:
        file = ROOT / path
        if Path(path).is_absolute() or '..' in Path(path).parts or file.resolve().is_relative_to(ROOT) is False:
            raise ValueError('Unsafe checkpoint path')
        if file.is_dir() or file.is_symlink():
            raise ValueError('Supply regular file paths, not directories or symlinks')
        if is_sensitive_path(path):
            raise ValueError('Possible credential filename; checkpoint refused')
        if args == ['--staged']:
            # Check the index, not a potentially different working-tree version.
            result = subprocess.run(['git', 'show', ':' + path], cwd=ROOT, capture_output=True)
            if result.returncode: continue  # staged deletion
            data = result.stdout
        else:
            data = file.read_bytes() if file.is_file() else b''
        if len(data) > 10 * 1024 * 1024:
            raise ValueError('Checkpoint file exceeds 10 MiB')
        if secret_markers(data.decode('utf-8', errors='replace')):
            raise ValueError('Possible credential content; checkpoint refused')
    if args == ['--staged'] and selected:
        dirty = paths('diff', '--name-only', '-z', '--no-renames', '--', *sorted(selected))
        if dirty:
            raise ValueError('Staged files have unstaged changes; QA would check different content')
    if args != ['--staged'] and selected:
        # Literal pathspecs prevent wildcard or magic path arguments from expanding scope.
        subprocess.run(['git', '--literal-pathspecs', 'add', '--', *sorted(selected)], cwd=ROOT, check=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('CHECKPOINT REFUSED: ' + str(error), file=sys.stderr)
        sys.exit(6)
