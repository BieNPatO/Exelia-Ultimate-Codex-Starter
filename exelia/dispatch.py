"""Deterministic bounded task dispatch; Codex agents execute packets in separate worktrees."""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
from . import models, worktrees
from .common import ROOT, approved, all_tasks, save, utc


def packet(root: Path, task: dict, workspace: str):
    owner = task.get('owner', 'implementation')
    stage = 'qa' if 'qa' in owner.lower() else 'review' if 'review' in owner.lower() else 'implementation'
    policy = models.recommend(root, stage=stage)
    return {'task_id': task['id'], 'role_requested': owner, 'workspace': workspace,
            'scope': task.get('scope'), 'acceptance': task.get('acceptance'), 'dependencies': task.get('dependencies', []),
            'model_recommendation': policy, 'execution_status': 'NOT_STARTED',
            'instructions': ('Use the Codex custom role if supported. Work only within the assigned worktree. '
                             'Check task scope and quality gates, commit locally, report evidence and return for independent review. '
                             'No push, deployment, host changes or secret access.')}


def dispatch(root: Path = ROOT, *, limit: int = 3, prepare=False):
    if prepare:
        approved(root)
    selection = worktrees.schedule(root, limit=limit)
    by_id = {task['id']: task for task in all_tasks(root)}
    made = []
    # Preserve MAIN working tree until all worktrees are safely created.
    for task_id in selection['ready']:
        if prepare:
            location = worktrees.create(root, task_id)
            made.append(task_id)
            target = location['path']
        else:
            target = str(worktrees.workspace(root, task_id).relative_to(root))
        selection.setdefault('packets', []).append(packet(root, by_id[task_id], target))
    if prepare:
        for task_id in made:
            result = subprocess.run([sys.executable, str(root / 'scripts/task-ledger.py'), 'start', task_id],
                                    cwd=root, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError('Workspace prepared but task start failed; inspect worktrees registry: '+result.stderr[-500:])
        report = {'generated_at': utc(), 'packets': selection['packets'],
                  'note': 'Worktrees prepared, tasks marked in_progress; native Codex subagents NOT launched by this CLI. '
                          'Use the coordinator to delegate packets; commit ledger updates locally.'}
        save(root / '.exelia/dispatch/last.json', report)
        selection['prepared'] = made
        selection['packets_path'] = '.exelia/dispatch/last.json'
    return selection
