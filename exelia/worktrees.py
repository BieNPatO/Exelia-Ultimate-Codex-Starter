"""Safe local Git worktrees for approved, independent tasks. Never pushes or deletes work."""
from __future__ import annotations
from pathlib import Path
import subprocess
import re
from .common import ROOT, all_tasks, approved, git, load, named_task, root_repo, save, utc, valid_task


def workspace(root: Path, task_id: str):
    return root / '.exelia' / 'worktrees' / valid_task(task_id)


def schedule(root: Path = ROOT, limit: int = 3):
    if limit < 1 or limit > 4:
        raise ValueError('Parallel task limit must be between 1 and 4.')
    tasks = all_tasks(root)
    by_id = {t['id']: t for t in tasks}
    candidates = []
    for t in tasks:
        if t['status'] != 'todo':
            continue
        if any(by_id.get(d, {}).get('status') != 'done' for d in t.get('dependencies', [])):
            continue
        candidates.append(t)
    # A scope is a real ownership boundary. '*' overlaps everything; nested paths overlap.
    busy = [t.get('scope', '*') for t in tasks if t['status'] in ('in_progress', 'ready_for_review')]
    chosen = []
    for t in candidates:
        scope = t.get('scope') or '*'
        if any(overlaps(scope, other) for other in busy):
            continue
        chosen.append(t)
        busy.append(scope)
        if len(chosen) >= limit:
            break
    return {'ready': [t['id'] for t in chosen], 'deferred': [t['id'] for t in candidates if t not in chosen],
            'active': [t['id'] for t in tasks if t['status'] in ('in_progress', 'ready_for_review')]}


def parse_scopes(text: str):
    scopes = [p.strip().strip('/') for p in text.split(',') if p.strip()] or ['*']
    for path in scopes:
        if path != '*' and (path.startswith('~') or '..' in Path(path).parts or not re.fullmatch(r'[A-Za-z0-9._/-]+', path)):
            raise ValueError('Invalid task scope: use repository-relative directories, no traversal or glob patterns.')
    return scopes


def overlaps(left: str, right: str):
    def paths(text):
        return parse_scopes(text)
    for a in paths(left):
        for b in paths(right):
            if a == '*' or b == '*' or a == b or a.startswith(b + '/') or b.startswith(a + '/'):
                return True
    return False


def create(root: Path, task_id: str):
    approved(root)
    root_repo(root)
    task = named_task(root, task_id)
    if task['status'] not in ('todo', 'in_progress'):
        raise RuntimeError('Only todo/in_progress tasks may receive worktrees.')
    if any(next((t for t in all_tasks(root) if t['id'] == dep), {}).get('status') != 'done' for dep in task.get('dependencies', [])):
        raise RuntimeError('Dependencies must be completed before preparing a worktree.')
    other_active = [t for t in all_tasks(root) if t['id'] != task_id and t['status'] in ('in_progress', 'ready_for_review')]
    if any(overlaps(task.get('scope', '*'), t.get('scope', '*')) for t in other_active):
        raise RuntimeError('File ownership overlaps another active task. Schedule sequentially.')
    if git('status', '--porcelain', cwd=root).stdout.strip():
        raise RuntimeError('Main working tree must be clean before creating a task worktree.')
    path = workspace(root, task_id)
    if path.exists():
        raise RuntimeError('Task workspace already exists; inspect before retrying: ' + str(path))
    branch = 'exelia/' + task_id
    if git('branch', '--list', branch, cwd=root).stdout.strip():
        raise RuntimeError('Branch already exists; refusing to reassign it: ' + branch)
    path.parent.mkdir(parents=True, exist_ok=True)
    git('worktree', 'add', '-b', branch, str(path), 'HEAD', cwd=root)
    registry = root / '.exelia' / 'worktrees.json'
    value = load(registry, {'schema_version': 1, 'items': {}})
    value['items'][task_id] = {'branch': branch, 'path': str(path.relative_to(root)),
                                'prepared_at': utc(), 'base_commit': git('rev-parse', 'HEAD', cwd=root).stdout.strip(),
                                'scope': task.get('scope', '*'), 'status': 'prepared'}
    save(registry, value)
    return value['items'][task_id]


def inspect(root: Path = ROOT):
    root_repo(root)
    data = load(root / '.exelia/worktrees.json', {'items': {}})['items']
    for item in data.values():
        location = root / item['path']
        item['exists'] = location.is_dir()
        if location.is_dir():
            item['dirty'] = bool(git('status', '--porcelain', cwd=location).stdout.strip())
    return data


def integrate(root: Path, task_id: str, *, confirm: bool = False):
    approved(root)
    root_repo(root)
    task = named_task(root, task_id)
    if task['status'] != 'ready_for_review':
        raise RuntimeError('Task must be ready_for_review with independent review before integration.')
    registry_path = root / '.exelia/worktrees.json'
    items = load(registry_path, {'items': {}})['items']
    if task_id not in items:
        raise RuntimeError('No registered worktree for this task.')
    entry = items[task_id]
    location = root / entry['path']
    if not location.is_dir():
        raise RuntimeError('Worktree missing; no changes applied.')
    if git('status', '--porcelain', cwd=root).stdout.strip() or git('status', '--porcelain', cwd=location).stdout.strip():
        raise RuntimeError('Main and task worktrees must both be clean and committed.')
    branch = entry['branch']
    diff = git('diff', '--check', f'HEAD...{branch}', cwd=root, check=False)
    if diff.returncode:
        raise RuntimeError('Branch contains whitespace errors or invalid diff; fix before merging.')
    changed = [x.strip() for x in git('diff', '--name-only', f'HEAD...{branch}', cwd=root).stdout.splitlines() if x.strip()]
    scopes = parse_scopes(task.get('scope', '*'))
    for filename in changed:
        if filename == '.env' or filename.startswith('.env.') and not filename.endswith('.example') or \
           filename.endswith(('.pem','.p12','.pfx','.key')) or filename.endswith('/credentials.json'):
            raise RuntimeError('Refusing to integrate possible secret file: ' + filename)
        if '*' not in scopes and not any(filename == p or filename.startswith(p + '/') for p in scopes):
            raise RuntimeError('Task changed files outside its assigned scope: ' + filename)
    base = git('merge-base', 'HEAD', branch, cwd=root).stdout.strip()
    status = {'task': task_id, 'branch': branch, 'base': base, 'main': git('rev-parse','HEAD',cwd=root).stdout.strip(),
              'branch_head': git('rev-parse', branch,cwd=root).stdout.strip(), 'whitespace': diff.returncode == 0}
    if not confirm:
        status['action'] = 'read-only dry run; merge requires --confirm and QA'
        return status
    qa = subprocess.run(['bash', 'scripts/quality-gate.sh', '--app'], cwd=location, capture_output=True, text=True)
    if qa.returncode:
        raise RuntimeError('Branch QA failed; refusing merge: ' + (qa.stdout + qa.stderr)[-1100:])
    result = git('merge', '--no-ff', '--no-edit', branch, cwd=root, check=False)
    if result.returncode:
        raise RuntimeError('Merge failed or conflicted; inspect Git status and resolve manually. No automatic reset: ' + result.stderr[-700:])
    entry['status'] = 'integrated'
    entry['integrated_at'] = utc()
    save(registry_path, {'schema_version': 1, 'items': items})
    status['action'] = 'merge completed; final main quality gate still required'
    return status
