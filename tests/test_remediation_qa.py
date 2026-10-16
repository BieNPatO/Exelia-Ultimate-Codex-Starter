"""Independent QA regressions using disposable repositories and real CLI processes."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from exelia import worktrees
from exelia.common import save, utc

ROOT = Path(__file__).resolve().parents[1]


class IndependentQATests(unittest.TestCase):
    def test_integration_rejects_worktree_checked_out_at_another_commit(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, approved=True)
            entry = worktrees.create(root, 'TASK-1')
            working = root / entry['path']
            (working / 'api/src').mkdir(parents=True)
            (working / 'api/src/feature.txt').write_text('Reviewed branch feature\n')
            subprocess.run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: reviewed branch feature'], cwd=working, check=True)
            commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=working, check=True,
                                    capture_output=True, text=True).stdout.strip()
            data = json.loads((root / 'tasks/backlog.json').read_text())
            task = data['tasks'][0]
            task['status'] = 'ready_for_review'
            task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'commit': commit,
                              'timestamp': utc(), 'evidence': 'review.md', 'outstanding_findings': []}
            save(root / 'tasks/backlog.json', data)
            (root / 'review.md').write_text('Synthetic branch-specific review.\n')
            subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: review fixture'], cwd=root, check=True)
            subprocess.run(['git', 'checkout', '-q', '--detach', entry['base_commit']], cwd=working, check=True)
            with self.assertRaisesRegex(RuntimeError, 'commit|HEAD|branch|checkout'):
                worktrees.integrate(root, 'TASK-1', confirm=True)
            self.assertFalse((root / 'api/src/feature.txt').exists())

    def test_task_cannot_rebind_owned_scope_using_a_new_symlink(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository(root, approved=True)
            entry = worktrees.create(root, 'TASK-1')
            working = root / entry['path']
            (working / 'docs').mkdir()
            (working / 'docs/outside.txt').write_text('Outside the assigned api/src scope\n')
            (working / 'api').mkdir()
            (working / 'api/src').symlink_to('../docs', target_is_directory=True)
            subprocess.run(['git', 'add', 'api/src', 'docs/outside.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: scope symlink fixture'], cwd=working, check=True)
            commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=working, check=True,
                                    capture_output=True, text=True).stdout.strip()
            data = json.loads((root / 'tasks/backlog.json').read_text())
            task = data['tasks'][0]
            task['status'] = 'ready_for_review'
            task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'commit': commit,
                              'timestamp': utc(), 'evidence': 'review.md', 'outstanding_findings': []}
            save(root / 'tasks/backlog.json', data)
            (root / 'review.md').write_text('Synthetic attestation for scope validation test.\n')
            subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: review fixture'], cwd=root, check=True)
            with self.assertRaisesRegex(RuntimeError, 'scope|symlink|ownership'):
                worktrees.integrate(root, 'TASK-1')
            self.assertFalse((root / 'docs/outside.txt').exists())

    def test_empty_dispatch_prepare_actual_cli_is_successful_noop(self):
        for tasks in ([], [{'id': 'BLOCKED', 'owner': 'qa', 'status': 'blocked', 'scope': 'api'}]):
            with self.subTest(tasks=tasks), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
                save(root / 'tasks/STATE.json', {'documentation_approved': True})
                save(root / 'tasks/backlog.json', {'tasks': tasks})
                result = subprocess.run([sys.executable, '-m', 'exelia', 'dispatch', 'prepare'],
                                        cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                record = json.loads(result.stdout)
                self.assertEqual(record['prepared'], [])
                self.assertEqual(record['packets'], [])
                self.assertFalse((root / '.exelia').exists())


if __name__ == '__main__':
    unittest.main()
