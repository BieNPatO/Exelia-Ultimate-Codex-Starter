"""Offline host-version and real checkpoint deadline regression tests."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from installer.engine import baseline_commit
from installer.probe import tool_info

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('integration_fixture', ROOT / 'tests/integration_smoke.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class NodeFixtureTests(unittest.TestCase):
    def test_offline_fixture_shadows_host_node_and_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / 'bin'; fake.mkdir()
            fixture.write_node_fixture(fake)
            host = root / 'host'; host.mkdir()
            fixture.write_bin(host / 'node', 'echo HOST_NODE_MUST_NOT_RUN >&2; exit 88')
            env = os.environ.copy()
            env['PATH'] = str(fake) + os.pathsep + str(host) + os.pathsep + env['PATH']
            tool = {'id': 'node', 'binary': 'node', 'minimum': '22.20.0'}
            for version, expected in (('22.20.0', 'ready'), ('24.0.0', 'ready'), ('22.16.0', 'incompatible')):
                with self.subTest(version=version), patch.dict(os.environ, {**env, 'EXELIA_MOCK_NODE_VERSION': version}):
                    info = tool_info(tool, root)
                    self.assertEqual(info['status'], expected, info)
                    self.assertEqual(Path(info['path']), fake / 'node')

    def test_real_installer_cli_simulates_compliant_and_rejected_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('installer', 'exelia', 'manifests'):
                shutil.copytree(ROOT / folder, root / folder, ignore=shutil.ignore_patterns('__pycache__'))
            fake = root / 'bin'; fake.mkdir(); fixture.write_node_fixture(fake)
            env = os.environ.copy()
            env['PATH'] = str(fake) + os.pathsep + env['PATH']
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            for version, expected in (('22.20.0', 'ready'), ('22.16.0', 'incompatible')):
                with self.subTest(version=version):
                    env['EXELIA_MOCK_NODE_VERSION'] = version
                    result = subprocess.run([sys.executable, '-m', 'installer', '--plan', '--json'],
                                            cwd=root, env=env, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    self.assertEqual(data['discovery']['tools']['node']['status'], expected)
                    if expected == 'incompatible':
                        rejected = subprocess.run([sys.executable, '-m', 'installer', '--verify', '--json'],
                                                  cwd=root, env=env, capture_output=True, text=True, timeout=30)
                        self.assertNotEqual(rejected.returncode, 0)
                        checks = json.loads(rejected.stdout)['checks']
                        self.assertEqual(next(item['status'] for item in checks if item['name'] == 'Tool node'), 'fail')
                    self.assertFalse((root / '.exelia-install').exists())


class CheckpointDeadlineTests(unittest.TestCase):
    def fixture(self, root, gate='exit 0\n'):
        (root / 'scripts').mkdir()
        (root / 'exelia').mkdir()
        for name in ('git-checkpoint.sh', 'checkpoint.py'):
            shutil.copy2(ROOT / 'scripts' / name, root / 'scripts' / name)
        for name in ('__init__.py', 'security.py'):
            shutil.copy2(ROOT / 'exelia' / name, root / 'exelia' / name)
        (root / 'scripts/validate-starter.py').write_text('raise SystemExit(0)\n')
        self.gate(root, gate)
        for args in (('init', '-q'), ('config', 'user.name', 'Synthetic Fixture'),
                     ('config', 'user.email', 'fixture@example.invalid')):
            subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)

    def gate(self, root, code):
        path = root / 'scripts/quality-gate.sh'
        path.write_text('#!/bin/sh\nset -eu\n' + code)
        path.chmod(0o755)
        files = sorted(p for p in root.rglob('*') if p.is_file() and '.git' not in p.parts and p.name != 'MANIFEST.sha256')
        (root / 'MANIFEST.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(root).as_posix() + '\n' for p in files))

    def head_exists(self, root):
        return subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=root, capture_output=True).returncode == 0

    def test_timeout_kills_gate_descendants_and_resume_rechecks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, '(sleep 2; touch late-descendant) &\nsleep 3\n')
            with patch.dict(os.environ, {'EXELIA_CHECKPOINT_TIMEOUT': '1', 'PYTHONDONTWRITEBYTECODE': '1'}):
                result = baseline_commit(root)
            self.assertEqual(result['status'], 'failed', result)
            self.assertIn('timed out', result['reason'])
            self.assertFalse(self.head_exists(root))
            time.sleep(2.2)
            self.assertFalse((root / 'late-descendant').exists(), 'A timed-out child survived')
            self.assertFalse(self.head_exists(root), 'Timed-out gate created a late commit')
            self.gate(root, 'exit 0\n')
            with patch.dict(os.environ, {'EXELIA_CHECKPOINT_TIMEOUT': '10', 'PYTHONDONTWRITEBYTECODE': '1'}):
                resumed = baseline_commit(root)
            self.assertEqual(resumed['status'], 'passed', resumed)
            self.assertTrue(self.head_exists(root))

    def test_sigterm_installer_parent_cannot_create_a_late_commit_and_can_resume(self):
        import signal
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'repo'; root.mkdir()
            self.fixture(root)
            (root / '.gitignore').write_text('.exelia-install/\n')
            self.gate(root, 'touch ../gate-ready\nsleep 3\n')
            code = ("from pathlib import Path; from installer.engine import Session, baseline_commit; "
                    "root = Path(" + repr(str(root)) + "); session = Session(root); "
                    "exec('with session.locked():\\n print(baseline_commit(root))')")
            env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'EXELIA_CHECKPOINT_TIMEOUT': '15'}
            process = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 10
                while not (base / 'gate-ready').exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((base / 'gate-ready').exists())
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=8)
                self.assertNotEqual(process.returncode, 0)
                time.sleep(3.2)
                self.assertFalse(self.head_exists(root), 'Terminated installer left a checkpoint running')
                self.assertFalse((root / '.exelia-install/lock').exists())
                self.gate(root, 'exit 0\n')
                from installer.engine import Session
                with Session(root).locked(), patch.dict(os.environ, {'PYTHONDONTWRITEBYTECODE': '1'}):
                    resumed = baseline_commit(root)
                self.assertEqual(resumed['status'], 'passed', resumed)
                self.assertTrue(self.head_exists(root))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_slow_gate_with_configured_budget_can_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root, 'sleep 1\n')
            with patch.dict(os.environ, {'EXELIA_CHECKPOINT_TIMEOUT': '5', 'PYTHONDONTWRITEBYTECODE': '1'}):
                result = baseline_commit(root)
            self.assertEqual(result['status'], 'passed', result)
            self.assertTrue(self.head_exists(root))

    def test_invalid_deadlines_fail_before_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.fixture(root)
            for value in ('0', '-1', '7201', 'nan', '1.5', ''):
                with self.subTest(value=value), patch.dict(os.environ, {'EXELIA_CHECKPOINT_TIMEOUT': value}):
                    result = baseline_commit(root)
                    self.assertEqual(result['status'], 'failed', result)
                    self.assertIn('EXELIA_CHECKPOINT_TIMEOUT', result['reason'])
                    self.assertFalse(self.head_exists(root))

    def test_deadline_default_and_bounds(self):
        from installer.processes import timeout_budget
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(timeout_budget('EXELIA_CHECKPOINT_TIMEOUT', 900), 900)
        for value in ('1', '7200'):
            with patch.dict(os.environ, {'EXELIA_CHECKPOINT_TIMEOUT': value}):
                self.assertEqual(timeout_budget('EXELIA_CHECKPOINT_TIMEOUT', 900), int(value))


class ProcessInterruptionTests(unittest.TestCase):
    def test_interrupt_reaps_gate_child_before_returning(self):
        import signal
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = ("from installer.processes import run_group; import sys; "
                    "run_group([sys.executable, '-c', \"from pathlib import Path; import time; "
                    "Path('ready').write_text('1'); time.sleep(2); Path('late').write_text('bad')\"], "
                    "cwd=" + repr(str(root)) + ", timeout=20)")
            process = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 10
                while not (root / 'ready').exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue((root / 'ready').exists())
                process.send_signal(signal.SIGINT)
                process.communicate(timeout=5)
                self.assertNotEqual(process.returncode, 0)
                time.sleep(2.1)
                self.assertFalse((root / 'late').exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()

    def test_outer_smoke_timeout_cleans_nested_checkpoint_group(self):
        from installer.processes import run_group
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = ("from installer.processes import run_group; import sys; "
                    "run_group([sys.executable, '-c', \"from pathlib import Path; import time; "
                    "Path('ready').write_text('1'); time.sleep(5); Path('late').write_text('bad')\"], "
                    "cwd=" + repr(str(root)) + ", timeout=20)")
            with self.assertRaises(subprocess.TimeoutExpired):
                run_group([sys.executable, '-c', code], cwd=ROOT, timeout=3, interrupt_first=True)
            self.assertTrue((root / 'ready').exists())
            time.sleep(5.1)
            self.assertFalse((root / 'late').exists())

    def test_detached_child_cannot_hold_cleanup_pipes_open(self):
        import signal
        from installer.processes import run_group
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pid_file = root / 'detached-pid'
            code = ("import subprocess, sys, time; from pathlib import Path; "
                    "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], start_new_session=True); "
                    "Path(" + repr(str(pid_file)) + ").write_text(str(child.pid)); time.sleep(20)")
            started = time.monotonic()
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    run_group([sys.executable, '-c', code], cwd=root, timeout=1)
                self.assertTrue(pid_file.exists(), 'Detached child fixture never started')
                self.assertLess(time.monotonic() - started, 10)
            finally:
                if pid_file.exists():
                    try:
                        os.kill(int(pid_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_sigterm_handler_is_restored_after_success_and_timeout(self):
        import signal
        from installer.processes import run_group
        previous = signal.getsignal(signal.SIGTERM)

        def original_handler(_signum, _frame):
            raise AssertionError('Restored handler must not execute in this test')

        signal.signal(signal.SIGTERM, original_handler)
        try:
            result = run_group([sys.executable, '-c', 'pass'], cwd=ROOT, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIs(signal.getsignal(signal.SIGTERM), original_handler)
            with self.assertRaises(subprocess.TimeoutExpired):
                run_group([sys.executable, '-c', 'import time; time.sleep(10)'], cwd=ROOT, timeout=1)
            self.assertIs(signal.getsignal(signal.SIGTERM), original_handler)
        finally:
            signal.signal(signal.SIGTERM, previous)

    def test_worker_thread_supervision_is_rejected_before_spawn(self):
        import threading
        from installer.processes import run_group
        errors = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def worker():
                try:
                    run_group([sys.executable, '-c', "from pathlib import Path; Path('unsafe-start').touch()"],
                              cwd=root, timeout=10)
                except RuntimeError as error:
                    errors.append(str(error))

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertIn('main thread', errors[0])
            self.assertFalse((root / 'unsafe-start').exists())
