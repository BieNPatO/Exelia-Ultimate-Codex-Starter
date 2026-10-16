"""Offline regression evidence for scope, capability, dispatch and ledger safety."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from exelia import capabilities, dispatch, worktrees
from exelia.common import save, utc

ROOT = Path(__file__).resolve().parents[1]


def fixture(root, tasks=None):
    save(root / 'tasks/backlog.json', {'tasks': tasks or []})
    save(root / 'tasks/STATE.json', {'documentation_approved': True})
    save(root / 'project.config.json', {'conversation_language': 'en', 'stack': {}})


def script(root, name, *args):
    (root / 'scripts').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
    return subprocess.run([sys.executable, str(root / 'scripts' / name), *args],
                          cwd=root, capture_output=True, text=True)


class ScopeRegressionTests(unittest.TestCase):
    def test_alias_parent_and_case_conflicts(self):
        for alias in ('api/./src', 'api//src', 'API/src', 'api/src/child'):
            with self.subTest(alias=alias):
                self.assertTrue(worktrees.overlaps('api/src', alias))

    def test_unsafe_paths_rejected(self):
        for scope in ('/api/src', '../api', 'api/../src', '~user/api'):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                worktrees.parse_scopes(scope)

    def test_symlink_alias_and_escape(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d)
            (root / 'api/src').mkdir(parents=True)
            (root / 'alias').symlink_to(root / 'api', target_is_directory=True)
            (root / 'escape').symlink_to(outside, target_is_directory=True)
            self.assertTrue(worktrees.overlaps('api/src', 'alias/src', root=root))
            with self.assertRaises(ValueError):
                worktrees.parse_scopes('escape/data', root=root)

    def test_scheduler_uses_canonical_scope(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture(root, [{'id': 'A', 'status': 'todo', 'scope': 'api/src'},
                           {'id': 'B', 'status': 'todo', 'scope': 'api/./src'}])
            self.assertEqual(worktrees.schedule(root)['ready'], ['A'])


class CapabilityRegressionTests(unittest.TestCase):
    def make_skills(self, root, names):
        for name in names:
            p = root / '.agents/skills' / name / 'SKILL.md'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('synthetic test skill')

    def test_stack_selection_missing_skills_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture(root)
            self.make_skills(root, capabilities.CORE)
            capabilities.freeze(root)
            save(root / 'project.config.json', {'stack': {'frontend': 'React'}})
            self.assertEqual(capabilities.audit(root)['status'], 'DRIFT')

    def test_explicit_optional_selectors_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture(root)
            self.make_skills(root, (*capabilities.CORE, *capabilities.SECURITY))
            capabilities.freeze(root, include_security=True)
            self.assertEqual(capabilities.audit(root)['status'], 'PASS')

    def test_source_revision_change_is_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture(root)
            self.make_skills(root, capabilities.CORE)
            save(root / 'manifests/components.json', {'skills': [{'name': 'ponytail', 'source': 'sample/repo', 'commit': 'a' * 40}]})
            capabilities.freeze(root)
            save(root / 'manifests/components.json', {'skills': [{'name': 'ponytail', 'source': 'sample/repo', 'commit': 'b' * 40}]})
            self.assertEqual(capabilities.audit(root)['status'], 'DRIFT')


class DispatchRegressionTests(unittest.TestCase):
    def test_empty_and_blocked_prepare_are_noops(self):
        for tasks in ([], [{'id': 'A', 'status': 'blocked', 'scope': 'api'}],
                      [{'id': 'B', 'status': 'todo', 'scope': 'api', 'dependencies': ['MISSING']}]):
            with self.subTest(tasks=tasks), tempfile.TemporaryDirectory() as d:
                root = Path(d); fixture(root, tasks)
                result = dispatch.dispatch(root, prepare=True)
                self.assertEqual(result['packets'], [])
                self.assertEqual(result['prepared'], [])
                self.assertFalse((root / '.exelia').exists())


class LedgerRegressionTests(unittest.TestCase):
    def test_resume_blocked_preserves_history_requires_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture(root, [{'id': 'A', 'owner': 'backend', 'status': 'blocked', 'evidence': [{'text': 'original block'}]}])
            rejected = script(root, 'task-ledger.py', 'resume', 'A', '--evidence', '')
            self.assertNotEqual(rejected.returncode, 0)
            resumed = script(root, 'task-ledger.py', 'resume', 'A', '--evidence', 'Dependency recovered')
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            task = json.loads((root / 'tasks/backlog.json').read_text())['tasks'][0]
            self.assertEqual(task['status'], 'todo')
            self.assertEqual(task['evidence'][0]['text'], 'original block')
            self.assertEqual(task['history'][-1]['from'], 'blocked')
            self.assertNotEqual(script(root, 'task-ledger.py', 'resume', 'A', '--evidence', 'again').returncode, 0)

    def test_language_tags_are_separate_and_subset_validated(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); fixture(root)
            result = script(root, 'project-state.py', 'ui-language', 'pl,en,en-US,zh-Hant,es-419')
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((root / 'project.config.json').read_text())
            self.assertEqual(config['conversation_language'], 'en')
            self.assertIn('zh-Hant', config['application_ui_languages'])
            for tag in ('en_US', 'en--US', '-en', 'en-', 'x', 'en-u'):
                self.assertNotEqual(script(root, 'project-state.py', 'ui-language', tag).returncode, 0)


class ReviewRegressionTests(unittest.TestCase):
    def test_sequential_main_review_allows_only_committed_review_metadata(self):
        from test_exelia_automation import repository
        for source_change in ('none', 'changed', 'reverted'):
            with self.subTest(source_change=source_change), tempfile.TemporaryDirectory() as d:
                root = Path(d); repository(root, approved=True, status='ready_for_review')
                shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
                shutil.copyfile(ROOT / 'scripts/task-ledger.py', root / 'scripts/task-ledger.py')
                (root / '.gitignore').write_text('.exelia/\n__pycache__/\n')
                (root / 'source.txt').write_text('Reviewed source\n')
                subprocess.run(['git', 'add', 'exelia', 'scripts', '.gitignore', 'source.txt'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: reviewed implementation'], cwd=root, check=True)
                reviewed = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
                evidence = root / 'docs/reviews/TASK-1.md'; evidence.parent.mkdir(parents=True); evidence.write_text('Independent synthetic review\n')
                invalid = script(root, 'task-ledger.py', 'attest-review', 'TASK-1', '--reviewer', 'independent-qa',
                                 '--commit', reviewed, '--result', 'PASS', '--evidence', 'source.txt')
                self.assertNotEqual(invalid.returncode, 0)
                self.assertIn('Sequential review evidence', invalid.stderr)
                attested = script(root, 'task-ledger.py', 'attest-review', 'TASK-1', '--reviewer', 'independent-qa',
                                  '--commit', reviewed, '--result', 'PASS', '--evidence', 'docs/reviews/TASK-1.md')
                self.assertEqual(attested.returncode, 0, attested.stderr)
                subprocess.run(['git', 'add', 'tasks/backlog.json', 'docs/reviews/TASK-1.md'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: review metadata'], cwd=root, check=True)
                if source_change != 'none':
                    (root / 'source.txt').write_text('Unreviewed source\n')
                    subprocess.run(['git', 'add', 'source.txt'], cwd=root, check=True)
                    subprocess.run(['git', 'commit', '-qm', 'test: unreviewed source change'], cwd=root, check=True)
                    if source_change == 'reverted':
                        (root / 'source.txt').write_text('Reviewed source\n')
                        subprocess.run(['git', 'add', 'source.txt'], cwd=root, check=True)
                        subprocess.run(['git', 'commit', '-qm', 'test: reverted unreviewed change'], cwd=root, check=True)
                result = script(root, 'task-ledger.py', 'complete', 'TASK-1', '--evidence', 'Actual sequential QA fixture')
                task = json.loads((root / 'tasks/backlog.json').read_text())['tasks'][0]
                if source_change != 'none':
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(task['status'], 'ready_for_review')
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(task['status'], 'done')

    def test_complete_checks_stable_integrated_main_through_actual_qa(self):
        from test_exelia_automation import repository
        for mutation in ('none', 'dirty', 'commit'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root = Path(d); repository(root, approved=True)
                shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
                shutil.copyfile(ROOT / 'scripts/task-ledger.py', root / 'scripts/task-ledger.py')
                (root / '.gitignore').write_text('.exelia/\n__pycache__/\n')
                gate = '#!/bin/sh\nset -e\n'
                if mutation != 'none':
                    gate += 'echo unreviewed >> api/src/feature.txt\n'
                if mutation == 'commit':
                    gate += 'git add api/src/feature.txt\ngit commit -qm "test: changed during QA"\n'
                (root / 'scripts/quality-gate.sh').write_text(gate + 'exit 0\n')
                subprocess.run(['git', 'add', 'exelia', 'scripts', '.gitignore'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: completion fixture'], cwd=root, check=True)
                entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
                feature = working / 'api/src/feature.txt'; feature.parent.mkdir(parents=True); feature.write_text('reviewed\n')
                subprocess.run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: task'], cwd=working, check=True)
                data = json.loads((root / 'tasks/backlog.json').read_text())
                task = data['tasks'][0]; task['status'] = 'ready_for_review'
                task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'timestamp': utc(),
                                  'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                                  'evidence': 'review.md', 'outstanding_findings': []}
                (root / 'review.md').write_text('Synthetic independent review')
                save(root / 'tasks/backlog.json', data)
                subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: review'], cwd=root, check=True)
                subprocess.run(['git', 'merge', '--no-ff', '--no-edit', entry['branch']], cwd=root, check=True, capture_output=True)
                result = script(root, 'task-ledger.py', 'complete', 'TASK-1', '--evidence', 'Actual fixture QA')
                task = json.loads((root / 'tasks/backlog.json').read_text())['tasks'][0]
                if mutation == 'none':
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(task['status'], 'done')
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('changed during completion QA', result.stderr)
                    self.assertEqual(task['status'], 'ready_for_review')

    def test_complete_cannot_run_main_qa_for_unintegrated_task_branch(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); repository(root, approved=True)
            shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copyfile(ROOT / 'scripts/task-ledger.py', root / 'scripts/task-ledger.py')
            (root / 'scripts/quality-gate.sh').write_text('#!/bin/sh\nif test -f api/src/broken.txt; then exit 42; fi\nexit 0\n')
            subprocess.run(['git', 'add', 'exelia', 'scripts'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: QA fixture'], cwd=root, check=True)
            entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
            broken = working / 'api/src/broken.txt'; broken.parent.mkdir(parents=True); broken.write_text('Broken task fixture\n')
            subprocess.run(['git', 'add', 'api/src/broken.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: broken task'], cwd=working, check=True)
            data = json.loads((root / 'tasks/backlog.json').read_text())
            task = data['tasks'][0]; task['status'] = 'ready_for_review'
            task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'timestamp': utc(),
                              'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                              'evidence': 'review.md', 'outstanding_findings': []}
            (root / 'review.md').write_text('Synthetic attestation for negative fixture')
            save(root / 'tasks/backlog.json', data)
            subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: record review'], cwd=root, check=True)
            self.assertEqual(subprocess.run(['bash', 'scripts/quality-gate.sh'], cwd=root).returncode, 0)
            self.assertEqual(subprocess.run(['bash', 'scripts/quality-gate.sh'], cwd=working).returncode, 42)
            result = script(root, 'task-ledger.py', 'complete', 'TASK-1', '--evidence', 'Actual negative fixture')
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('integrated', result.stderr)
            self.assertEqual(json.loads((root / 'tasks/backlog.json').read_text())['tasks'][0]['status'], 'ready_for_review')

    def test_renames_check_deleted_source_scope_and_sensitive_name(self):
        from test_exelia_automation import repository
        for source in ('other/critical.txt', 'api/src/.env'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as d:
                root = Path(d); repository(root, approved=True)
                old = root / source; old.parent.mkdir(parents=True); old.write_text('Synthetic rename fixture\n')
                subprocess.run(['git', 'add', source], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: existing source'], cwd=root, check=True)
                entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
                (working / 'api/src').mkdir(parents=True, exist_ok=True)
                subprocess.run(['git', 'mv', source, 'api/src/critical.txt'], cwd=working, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: rename source'], cwd=working, check=True)
                data = json.loads((root / 'tasks/backlog.json').read_text())
                task = data['tasks'][0]; task['status'] = 'ready_for_review'
                task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'timestamp': utc(),
                                  'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                                  'evidence': 'review.md', 'outstanding_findings': []}
                (root / 'review.md').write_text('Synthetic independent review')
                save(root / 'tasks/backlog.json', data)
                subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: recorded review'], cwd=root, check=True)
                with self.assertRaisesRegex(RuntimeError, 'outside|secret'):
                    worktrees.integrate(root, 'TASK-1', confirm=True)
                self.assertTrue(old.exists())
                self.assertFalse((root / 'api/src/critical.txt').exists())

    def test_registry_cannot_redirect_workspace_or_branch(self):
        from test_exelia_automation import repository
        for field, value in (('path', '../another'), ('branch', 'main')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as d:
                root = Path(d); repository(root, approved=True)
                worktrees.create(root, 'TASK-1')
                data = json.loads((root / 'tasks/backlog.json').read_text())
                data['tasks'][0]['status'] = 'ready_for_review'
                save(root / 'tasks/backlog.json', data)
                subprocess.run(['git', 'add', 'tasks/backlog.json'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: ready for review'], cwd=root, check=True)
                registry = json.loads((root / '.exelia/worktrees.json').read_text())
                registry['items']['TASK-1'][field] = value
                save(root / '.exelia/worktrees.json', registry)
                with self.assertRaisesRegex(RuntimeError, 'registered|registry|workspace'):
                    worktrees.integrate(root, 'TASK-1')

    def test_outside_scope_symlink_cannot_borrow_inside_target_ownership(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); repository(root, approved=True)
            entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
            target = working / 'api/src/target.txt'; target.parent.mkdir(parents=True); target.write_text('Owned fixture\n')
            (working / 'outside-link').symlink_to('api/src/target.txt')
            subprocess.run(['git', 'add', 'api/src/target.txt', 'outside-link'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: outside symlink'], cwd=working, check=True)
            data = json.loads((root / 'tasks/backlog.json').read_text())
            task = data['tasks'][0]; task['status'] = 'ready_for_review'
            task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'timestamp': utc(),
                              'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                              'evidence': 'review.md', 'outstanding_findings': []}
            (root / 'review.md').write_text('Synthetic independent review')
            save(root / 'tasks/backlog.json', data)
            subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: review'], cwd=root, check=True)
            with self.assertRaisesRegex(RuntimeError, 'scope|ownership'):
                worktrees.integrate(root, 'TASK-1', confirm=True)
            self.assertFalse((root / 'outside-link').exists())

    def test_branch_change_during_qa_requires_new_review(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); repository(root, approved=True)
            entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
            feature = working / 'api/src/feature.txt'; feature.parent.mkdir(parents=True)
            feature.write_text('reviewed\n')
            subprocess.run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: reviewed task'], cwd=working, check=True)
            data = json.loads((root / 'tasks/backlog.json').read_text())
            task = data['tasks'][0]; task['status'] = 'ready_for_review'
            task['review'] = {'reviewer': 'independent-qa', 'result': 'PASS', 'timestamp': utc(),
                              'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                              'evidence': 'review.md', 'outstanding_findings': []}
            (root / 'review.md').write_text('Synthetic independent review')
            save(root / 'tasks/backlog.json', data)
            subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: recorded review'], cwd=root, check=True)
            original_run = subprocess.run

            def run_with_qa_change(arguments, **kwargs):
                result = original_run(arguments, **kwargs)
                if arguments[:2] == ['bash', 'scripts/quality-gate.sh']:
                    feature.write_text('unreviewed change during QA\n')
                    original_run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
                    original_run(['git', 'commit', '-qm', 'test: QA changed task'], cwd=working, check=True)
                return result

            with patch('exelia.worktrees.subprocess.run', side_effect=run_with_qa_change):
                with self.assertRaisesRegex(RuntimeError, 'changed during QA'):
                    worktrees.integrate(root, 'TASK-1', confirm=True)
            self.assertFalse((root / 'api/src/feature.txt').exists())

    def test_integration_filename_guards_and_portable_names(self):
        from test_exelia_automation import repository
        for name, allowed in (('api/src/hello world żółć.txt', True), ('api/src/.env', False),
                              ('api/src/private.key', False), ('api/src/.env.example', True)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d); repository(root, approved=True)
                entry = worktrees.create(root, 'TASK-1'); working = root / entry['path']
                file = working / name; file.parent.mkdir(parents=True); file.write_text('synthetic fixture\n')
                subprocess.run(['git', 'add', name], cwd=working, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: filename'], cwd=working, check=True)
                data = json.loads((root / 'tasks/backlog.json').read_text())
                task = data['tasks'][0]; task['status'] = 'ready_for_review'
                task['review'] = {'reviewer': 'qa-reviewer', 'result': 'PASS', 'timestamp': utc(),
                                  'commit': subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip(),
                                  'evidence': 'review.md', 'outstanding_findings': []}
                (root / 'review.md').write_text('Synthetic independent review')
                save(root / 'tasks/backlog.json', data)
                subprocess.run(['git', 'add', 'tasks/backlog.json', 'review.md'], cwd=root, check=True)
                subprocess.run(['git', 'commit', '-qm', 'test: reviewed'], cwd=root, check=True)
                if allowed:
                    self.assertIn('read-only', worktrees.integrate(root, 'TASK-1')['action'])
                else:
                    with self.assertRaisesRegex(RuntimeError, 'secret file'):
                        worktrees.integrate(root, 'TASK-1')

    def test_actual_attestation_and_stale_review_integration(self):
        from test_exelia_automation import repository
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            repository(root, approved=True)
            entry = worktrees.create(root, 'TASK-1')
            working = root / entry['path']
            (working / 'api/src').mkdir(parents=True)
            feature = working / 'api/src/feature.txt'
            feature.write_text('first\n')
            subprocess.run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: task feature'], cwd=working, check=True)
            data = json.loads((root / 'tasks/backlog.json').read_text())
            data['tasks'][0]['status'] = 'ready_for_review'
            save(root / 'tasks/backlog.json', data)
            (root / 'review.md').write_text('Fixture independent review')
            shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
            commit = subprocess.run(['git', 'rev-parse', entry['branch']], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
            result = script(root, 'task-ledger.py', 'attest-review', 'TASK-1', '--reviewer', 'qa-reviewer',
                            '--commit', commit, '--result', 'PASS', '--evidence', 'review.md')
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: review record'], cwd=root, check=True)
            worktrees.integrate(root, 'TASK-1')
            feature.write_text('changed after review\n')
            subprocess.run(['git', 'add', 'api/src/feature.txt'], cwd=working, check=True)
            subprocess.run(['git', 'commit', '-qm', 'test: stale review'], cwd=working, check=True)
            before = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True).stdout
            with self.assertRaisesRegex(RuntimeError, 'stale'):
                worktrees.integrate(root, 'TASK-1', confirm=True)
            completion = script(root, 'task-ledger.py', 'complete', 'TASK-1', '--evidence', 'QA fixture')
            self.assertEqual(completion.returncode, 2, completion.stderr)
            self.assertIn('stale', completion.stderr)
            after = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True).stdout
            self.assertEqual(before, after)
            self.assertFalse((root / 'api/src/feature.txt').exists())

    def test_review_requires_independence_exact_commit_and_existing_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            task = {'owner': 'implementer'}
            for review in ({}, {'reviewer': 'implementer', 'result': 'PASS', 'commit': 'a' * 40,
                                'timestamp': utc(), 'evidence': 'review.md', 'outstanding_findings': []}):
                task['review'] = review
                with self.assertRaises(RuntimeError):
                    worktrees.validate_review(root, task, 'a' * 40)
            (root / 'review.md').write_text('Independent synthetic review')
            good = {'reviewer': 'reviewer', 'result': 'PASS', 'commit': 'a' * 40,
                    'timestamp': utc(), 'evidence': 'review.md', 'outstanding_findings': []}
            task['review'] = good
            worktrees.validate_review(root, task, 'a' * 40)
            for field, value in (('commit', 'b' * 40), ('result', 'FAIL'), ('timestamp', 'invalid'),
                                 ('evidence', '../outside.md'), ('outstanding_findings', ['unfixed'])):
                with self.subTest(field=field), self.assertRaises(RuntimeError):
                    worktrees.validate_review(root, {'owner': 'implementer', 'review': {**good, field: value}}, 'a' * 40)


if __name__ == '__main__':
    unittest.main()
