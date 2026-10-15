"""Shared, dependency-free file and policy operations."""
from __future__ import annotations
import contextlib
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TASK_ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,47}$')


def load(path: Path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else default


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(prefix='.' + path.name + '-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(*arguments: str, cwd: Path = ROOT, check=True):
    result = subprocess.run(['git', *arguments], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode:
        raise RuntimeError('git ' + ' '.join(arguments) + ': ' + result.stderr.strip()[:700])
    return result


def approved(root: Path):
    state = load(root / 'tasks/STATE.json', {})
    if not state.get('documentation_approved'):
        raise RuntimeError('Project specification requires one explicit human approval before implementation.')


def valid_task(task_id: str):
    if not TASK_ID.fullmatch(task_id):
        raise ValueError('Task ID must begin with a letter and contain only letters, digits, _ or - (max 48 chars).')
    return task_id


def root_repo(root: Path):
    result = git('rev-parse', '--show-toplevel', cwd=root)
    if Path(result.stdout.strip()).resolve() != root.resolve():
        raise RuntimeError('Use a standalone Git repository, not a nested directory.')


def all_tasks(root: Path):
    return load(root / 'tasks/backlog.json', {'tasks': []})['tasks']


def named_task(root: Path, task_id: str):
    valid_task(task_id)
    match = [item for item in all_tasks(root) if item['id'] == task_id]
    if not match:
        raise ValueError('Unknown task ID: ' + task_id)
    return match[0]


def dump(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))
