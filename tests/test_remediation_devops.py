"""Regression checks for checkpoint scope and reproducible local tools."""
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from installer.localtools import install_node, install_python

ROOT = pathlib.Path(__file__).resolve().parents[1]

class CheckpointTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'scripts').mkdir()
        for name in ('git-checkpoint.sh', 'checkpoint.py'):
            source = ROOT / 'scripts' / name
            if source.exists(): shutil.copy(source, root / 'scripts' / name)
        (root / 'exelia').mkdir()
        for name in ('__init__.py', 'security.py'):
            shutil.copy(ROOT / 'exelia' / name, root / 'exelia' / name)
        (root / 'scripts/quality-gate.sh').write_text('#!/bin/sh\nexit 0\n')
        (root / 'scripts/quality-gate.sh').chmod(0o755)
        for args in (('init', '-q'), ('config', 'user.name', 'Fixture'), ('config', 'user.email', 'fixture@example.invalid')):
            subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
        (root / 'owned.txt').write_text('base\n')
        subprocess.run(['git', 'add', 'owned.txt'], cwd=root, check=True)
        subprocess.run(['git', 'commit', '-qm', 'chore: fixture'], cwd=root, check=True)

    def run_checkpoint(self, root, *scope):
        return subprocess.run(['bash', 'scripts/git-checkpoint.sh', '--starter', 'fix: scoped change', *scope], cwd=root, capture_output=True, text=True)

    def test_requires_explicit_scope_and_does_not_stage(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'owned.txt').write_text('changed\n')
            result = self.run_checkpoint(root)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=root), b'')

    def test_only_selected_file_committed(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'owned.txt').write_text('changed\n')
            (root / 'unrelated.txt').write_text('user work\n')
            result = self.run_checkpoint(root, 'owned.txt')
            self.assertEqual(result.returncode, 0, result.stderr)
            names = subprocess.check_output(['git', 'show', '--format=', '--name-only', 'HEAD'], cwd=root, text=True)
            self.assertEqual(names.strip(), 'owned.txt')
            self.assertEqual((root / 'unrelated.txt').read_text(), 'user work\n')

    def test_rejects_unrelated_index_without_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'owned.txt').write_text('changed\n')
            (root / 'unrelated.txt').write_text('user work\n')
            subprocess.run(['git', 'add', 'unrelated.txt'], cwd=root, check=True)
            before = subprocess.check_output(['git', 'diff', '--cached'], cwd=root)
            result = self.run_checkpoint(root, 'owned.txt')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(subprocess.check_output(['git', 'diff', '--cached'], cwd=root), before)

    def test_sensitive_nested_file_rejected_before_staging(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'api').mkdir(); (root / 'api/.env').write_text('SYNTHETIC=value\n')
            result = self.run_checkpoint(root, 'api/.env')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=root), b'')

    def test_gate_cannot_stage_unrelated_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'owned.txt').write_text('changed\n')
            (root / 'user.txt').write_text('keep\n')
            (root / 'scripts/quality-gate.sh').write_text('#!/bin/sh\ngit add user.txt\n')
            before = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root)
            result = self.run_checkpoint(root, 'owned.txt')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root), before)

    def test_staged_content_must_match_tested_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            (root / 'owned.txt').write_text('staged\n')
            subprocess.run(['git', 'add', 'owned.txt'], cwd=root, check=True)
            (root / 'owned.txt').write_text('different\n')
            result = self.run_checkpoint(root, '--staged')
            self.assertNotEqual(result.returncode, 0)

    def test_initial_manifest_rejects_unlisted_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d); self.fixture(root)
            # A new orphan repository retains files but has no initial source manifest.
            subprocess.run(['git', 'checkout', '--orphan', 'fresh'], cwd=root, capture_output=True, check=True)
            result = self.run_checkpoint(root, '--initial')
            self.assertNotEqual(result.returncode, 0)

class DependencyTests(unittest.TestCase):
    def test_npm_requires_exact_version(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
            with self.assertRaises(ValueError): install_node(pathlib.Path(d), 'skills')
            run.assert_not_called()

    def test_npm_uses_resolver_lock_and_local_ci(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
            root = pathlib.Path(d)
            shutil.copytree(ROOT / 'manifests/tool-dependencies', root / 'manifests/tool-dependencies')
            install_node(root, 'skills@1.7.2')
            command = run.call_args.args[0]
            self.assertEqual(command[:2], ['npm', 'ci'])
            self.assertIn('--ignore-scripts', command)
            self.assertEqual(run.call_args.kwargs['cwd'], (root / '.exelia-tools/node').resolve())
            self.assertEqual(json.loads((root / '.exelia-tools/node/package-lock.json').read_text()),
                             json.loads((root / 'manifests/tool-dependencies/core/package-lock.json').read_text()))

    def test_unknown_private_tool_dependency_is_preserved(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
            root = pathlib.Path(d)
            shutil.copytree(ROOT / 'manifests/tool-dependencies', root / 'manifests/tool-dependencies')
            base = root / '.exelia-tools/node'; base.mkdir(parents=True)
            original = '{"devDependencies":{"user-tool":"1.0.0"}}'
            (base / 'package.json').write_text(original)
            with self.assertRaisesRegex(ValueError, 'Unmanaged'):
                install_node(root, 'skills@1.7.2')
            self.assertEqual((base / 'package.json').read_text(), original)
            run.assert_not_called()

    def test_manifest_sources_and_actions_are_immutable(self):
        manifest = json.loads((ROOT / 'manifests/components.json').read_text())
        for skill in manifest['skills']:
            if skill.get('installer', 'skills-cli') == 'skills-cli':
                self.assertRegex(skill['commit'], r'^[0-9a-f]{40}$')
        workflow = (ROOT / '.github/workflows/starter-ci.yml').read_text()
        for line in workflow.splitlines():
            if 'uses:' in line:
                self.assertRegex(line, r'@[0-9a-f]{40}(?: |$)')
        self.assertIn('fetch-depth: 0', workflow)

    def test_python_pin_requires_exact_requirement_token(self):
        with tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
            root = pathlib.Path(d)
            base = root / 'manifests/tool-dependencies'; base.mkdir(parents=True)
            (base / 'requirements-uv.txt').write_text('# lock\nuv==0.13.10 \\\n    --hash=sha256:fixture\n')
            with self.assertRaisesRegex(ValueError, 'reviewed hash lock'):
                install_python(root, 'uv==0.13.1')
            run.assert_not_called()

class ToolContainmentTests(unittest.TestCase):
    def fixture(self, root):
        shutil.copytree(ROOT / 'manifests/tool-dependencies', root / 'manifests/tool-dependencies')

    def test_node_rejects_redirected_writable_paths_without_outside_write(self):
        for relative in ('.exelia-tools', '.exelia-tools/node', '.exelia-tools/npm-cache',
                         '.exelia-tools/node/package.json', '.exelia-tools/node/package-lock.json'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
                root = pathlib.Path(d) / 'repo'; root.mkdir(); self.fixture(root)
                outside = pathlib.Path(d) / 'outside'; outside.mkdir()
                marker = outside / 'marker'; marker.write_text('preserve\n')
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(marker if target.name.endswith('.json') else outside)
                with self.assertRaisesRegex(ValueError, 'local|symlink|managed'):
                    install_node(root, 'skills@1.7.2')
                self.assertEqual(marker.read_text(), 'preserve\n')
                self.assertEqual({p.name for p in outside.iterdir()}, {'marker'})
                run.assert_not_called()

    def test_python_rejects_redirected_writable_paths_before_subprocess(self):
        for relative in ('.exelia-tools', '.exelia-tools/python', '.exelia-tools/pip-cache',
                         '.exelia-tools/python/lib/python3.14/site-packages'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
                root = pathlib.Path(d) / 'repo'; root.mkdir(); self.fixture(root)
                outside = pathlib.Path(d) / 'outside'; outside.mkdir()
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); target.symlink_to(outside)
                with self.assertRaisesRegex(ValueError, 'local|symlink|managed'):
                    install_python(root, 'ruff==0.17.1')
                self.assertEqual(list(outside.iterdir()), [])
                run.assert_not_called()

    def test_probe_and_launcher_reject_external_tool_symlink(self):
        from installer.probe import tool_info
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / 'repo'; root.mkdir()
            shutil.copytree(ROOT / 'installer', root / 'installer', ignore=shutil.ignore_patterns('__pycache__'))
            (root / 'scripts').mkdir(); shutil.copy(ROOT / 'scripts/local-tool.sh', root / 'scripts/local-tool.sh')
            outside = pathlib.Path(d) / 'outside'; outside.mkdir()
            marker = outside / 'executed'
            executable = outside / 'global-tool'
            executable.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\necho 1.0.0\n'); executable.chmod(0o755)
            for name, mode, prefix in (('skills', 'local-npm', 'node/node_modules/.bin'), ('ruff', 'local-python', 'python/bin')):
                target = root / '.exelia-tools' / prefix / name; target.parent.mkdir(parents=True, exist_ok=True); target.symlink_to(executable)
                info = tool_info({'binary': name, 'id': name, 'install': mode}, root)
                self.assertNotEqual(info['status'], 'ready')
                result = subprocess.run(['bash', 'scripts/local-tool.sh', name, '--version'], cwd=root, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(marker.exists())

    def test_standard_venv_interpreter_symlink_is_allowed(self):
        import sys
        with tempfile.TemporaryDirectory() as d, patch('installer.localtools.subprocess.run') as run:
            root = pathlib.Path(d); self.fixture(root)
            interpreter = root / '.exelia-tools/python/bin/python'; interpreter.parent.mkdir(parents=True)
            interpreter.symlink_to(pathlib.Path(sys.executable).resolve())
            (interpreter.parent / '𝜋thon').symlink_to('python')
            base = root / '.exelia-tools/python'
            (base / 'lib').mkdir()
            (base / 'lib64').symlink_to('lib', target_is_directory=True)
            install_python(root, 'ruff==0.17.1')
            self.assertEqual(run.call_args.args[0][1:5], ['-m', 'pip', '--isolated', 'install'])

    def test_probe_accepts_confined_npm_bin_symlink(self):
        from installer.probe import tool_info
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            base = root / '.exelia-tools/node/node_modules'
            target = base / 'skills/cli'; target.parent.mkdir(parents=True)
            target.write_text('#!/bin/sh\necho 1.7.2\n'); target.chmod(0o755)
            binary = base / '.bin/skills'; binary.parent.mkdir(); binary.symlink_to('../skills/cli')
            self.assertEqual(tool_info({'binary': 'skills', 'id': 'skills', 'install': 'local-npm'}, root)['status'], 'ready')

    def test_project_skill_parent_symlink_cannot_satisfy_readiness(self):
        from installer.probe import scan_skill
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / 'repo'; root.mkdir()
            outside = pathlib.Path(d) / 'outside'; (outside / 'test').mkdir(parents=True)
            (outside / 'test/SKILL.md').write_text('---\nname: test\ndescription: fixture\n---\n')
            (root / '.agents').mkdir(); (root / '.agents/skills').symlink_to(outside)
            self.assertEqual(scan_skill('test', root, pathlib.Path(d) / 'home')['status'], 'missing')

    def test_pip_real_process_ignores_external_target_environment(self):
        import hashlib
        import os
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / 'repo'; root.mkdir()
            outside = pathlib.Path(d) / 'outside'; outside.mkdir()
            wheels = root / 'wheels'; wheels.mkdir()
            wheel = wheels / 'ruff-0.17.1-py3-none-any.whl'
            with zipfile.ZipFile(wheel, 'w') as archive:
                archive.writestr('ruff_fixture.py', '# Synthetic local-only install fixture\n')
                archive.writestr('ruff-0.17.1.dist-info/METADATA', 'Metadata-Version: 2.1\nName: ruff\nVersion: 0.17.1\n')
                archive.writestr('ruff-0.17.1.dist-info/WHEEL', 'Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
                archive.writestr('ruff-0.17.1.dist-info/RECORD', '')
            manifests = root / 'manifests/tool-dependencies'; manifests.mkdir(parents=True)
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
            (manifests / 'requirements-ruff.txt').write_text('--no-index\n--find-links ' + str(wheels) + '\nruff==0.17.1 --hash=sha256:' + digest + '\n')
            with patch.dict(os.environ, {'PIP_TARGET': str(outside), 'PIP_USER': '1'}):
                result = install_python(root, 'ruff==0.17.1')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertTrue(list((root / '.exelia-tools/python').rglob('ruff_fixture.py')))
