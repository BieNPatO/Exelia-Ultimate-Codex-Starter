"""Safe local Git worktrees for approved, independent tasks. Never pushes or deletes work."""
from __future__ import annotations
from pathlib import Path
import datetime
import subprocess
import re
from .common import ROOT, all_tasks, approved, git, load, named_task, root_repo, save, utc, valid_task
from .security import is_sensitive_path


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
        parse_scopes(scope, root=root)
        if any(overlaps(scope, other, root=root) for other in busy):
            continue
        chosen.append(t)
        busy.append(scope)
        if len(chosen) >= limit:
            break
    return {'ready': [t['id'] for t in chosen], 'deferred': [t['id'] for t in candidates if t not in chosen],
            'active': [t['id'] for t in tasks if t['status'] in ('in_progress', 'ready_for_review')]}


def parse_scopes(text: str, *, root: Path | None = None):
    scopes = []
    for path in [p.strip() for p in text.split(',') if p.strip()] or ['*']:
        if path == '*':
            scopes.append(path)
            continue
        if Path(path).is_absolute() or path.startswith('~') or '..' in Path(path).parts or not re.fullmatch(r'[A-Za-z0-9._/-]+', path):
            raise ValueError('Invalid task scope: use repository-relative directories, no traversal or glob patterns.')
        normalized = Path(path).as_posix()
        if root is not None:
            try:
                normalized = (root / normalized).resolve().relative_to(root.resolve()).as_posix()
            except (ValueError, OSError, RuntimeError) as exc:
                raise ValueError('Task scope resolves outside the project or contains an invalid symlink.') from exc
        scopes.append('*' if normalized == '.' else normalized)
    return scopes


def overlaps(left: str, right: str, *, root: Path | None = None):
    def paths(text):
        # Conservatively serialize case aliases even on case-sensitive hosts for portable task ownership.
        return [p.casefold() for p in parse_scopes(text, root=root)]
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
    canonical_scopes = parse_scopes(task.get('scope', '*'), root=root)
    if any(overlaps(task.get('scope', '*'), t.get('scope', '*'), root=root) for t in other_active):
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
                                'scope': task.get('scope', '*'), 'canonical_scopes': canonical_scopes, 'status': 'prepared'}
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


def validate_review(root: Path, task: dict, commit: str):
    """Validate a procedural attestation; this cannot authenticate the human or agent identity."""
    review = task.get('review') or {}
    if not isinstance(review, dict):
        raise RuntimeError('Review evidence must be a structured attestation.')
    reviewer = review.get('reviewer')
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.strip().casefold() == str(task.get('owner', '')).strip().casefold():
        raise RuntimeError('Independent reviewer identifier is required and must differ from the task owner.')
    if review.get('result') != 'PASS' or review.get('outstanding_findings') != []:
        raise RuntimeError('Review must PASS with no outstanding findings.')
    if review.get('commit') != commit:
        raise RuntimeError('Review is missing or stale: exact task branch commit must be reviewed.')
    try:
        timestamp = datetime.datetime.fromisoformat(review['timestamp'])
        if timestamp.tzinfo is None or timestamp > datetime.datetime.now(datetime.timezone.utc):
            raise ValueError('Review timestamp must include timezone and must not be in the future.')
        evidence = Path(review['evidence'])
        if evidence.is_absolute() or '..' in evidence.parts or not (root / evidence).resolve().is_relative_to(root.resolve()) or not (root / evidence).is_file():
            raise ValueError('Review evidence must be an existing repository-relative file.')
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError('Valid review timestamp and local evidence file are required.') from exc


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
    expected = workspace(root, task_id)
    if entry.get('path') != expected.relative_to(root).as_posix() or entry.get('branch') != 'exelia/' + task_id:
        raise RuntimeError('Worktree registry must identify the registered task workspace and branch.')
    location = root / entry['path']
    if location.resolve() != root.resolve() / expected.relative_to(root) or not location.resolve().is_relative_to(root.resolve()):
        raise RuntimeError('Registered task workspace cannot redirect through a symlink.')
    if not location.is_dir():
        raise RuntimeError('Worktree missing; no changes applied.')
    if git('status', '--porcelain', cwd=root).stdout.strip() or git('status', '--porcelain', cwd=location).stdout.strip():
        raise RuntimeError('Main and task worktrees must both be clean and committed.')
    branch = entry['branch']
    branch_head = git('rev-parse', branch, cwd=root).stdout.strip()
    main_head = git('rev-parse', 'HEAD', cwd=root).stdout.strip()
    if git('rev-parse', 'HEAD', cwd=location).stdout.strip() != branch_head:
        raise RuntimeError('Task worktree HEAD must match the exact reviewed branch commit before QA.')
    validate_review(root, task, branch_head)
    scopes = entry.get('canonical_scopes')
    if not scopes:
        raise RuntimeError('Frozen scope ownership is missing; inspect and prepare a new reviewed worktree.')
    if parse_scopes(task.get('scope', '*'), root=root) != scopes or parse_scopes(entry['scope'], root=root) != scopes or parse_scopes(entry['scope'], root=location) != scopes:
        raise RuntimeError('Task scope ownership changed or was rebound by a symlink after preparation.')
    lexical_scopes = parse_scopes(entry['scope']) + scopes
    diff = git('diff', '--check', f'{main_head}...{branch_head}', cwd=root, check=False)
    if diff.returncode:
        raise RuntimeError('Branch contains whitespace errors or invalid diff; fix before merging.')
    changed = [x for x in git('diff', '--no-renames', '--name-only', '-z', f'{main_head}...{branch_head}', cwd=root).stdout.split('\0') if x]
    for filename in changed:
        if is_sensitive_path(filename):
            raise RuntimeError('Refusing to integrate possible secret file: ' + filename)
        if '*' not in lexical_scopes and not any(filename == p or filename.startswith(p + '/') for p in lexical_scopes):
            raise RuntimeError('Task changed a file outside its assigned lexical scope: ' + filename)
        try:
            canonical = (location / filename).resolve().relative_to(location.resolve()).as_posix()
        except (ValueError, OSError, RuntimeError) as exc:
            raise RuntimeError('Changed path resolves outside its task worktree: ' + filename) from exc
        if '*' not in scopes and not any(canonical == p or canonical.startswith(p + '/') for p in scopes):
            raise RuntimeError('Task changed files outside its assigned scope: ' + filename)
    base = git('merge-base', main_head, branch_head, cwd=root).stdout.strip()
    status = {'task': task_id, 'branch': branch, 'base': base, 'main': main_head,
              'branch_head': branch_head, 'whitespace': diff.returncode == 0}
    if not confirm:
        status['action'] = 'read-only dry run; merge requires --confirm and QA'
        return status
    qa = subprocess.run(['bash', 'scripts/quality-gate.sh', '--app'], cwd=location, capture_output=True, text=True)
    if qa.returncode:
        raise RuntimeError('Branch QA failed; refusing merge: ' + (qa.stdout + qa.stderr)[-1100:])
    if git('rev-parse', branch, cwd=root).stdout.strip() != branch_head or git('rev-parse', 'HEAD', cwd=location).stdout.strip() != branch_head or git('rev-parse', 'HEAD', cwd=root).stdout.strip() != main_head:
        raise RuntimeError('Git commit changed during QA; review and run integration again.')
    if git('status', '--porcelain', cwd=root).stdout.strip() or git('status', '--porcelain', cwd=location).stdout.strip():
        raise RuntimeError('QA changed a working tree; commit and review changes before integration.')
    result = git('merge', '--no-ff', '--no-edit', branch_head, cwd=root, check=False)
    if result.returncode:
        raise RuntimeError('Merge failed or conflicted; inspect Git status and resolve manually. No automatic reset: ' + result.stderr[-700:])
    entry['status'] = 'integrated'
    entry['integrated_at'] = utc()
    save(registry_path, {'schema_version': 1, 'items': items})
    status['action'] = 'merge completed; final main quality gate still required'
    return status
