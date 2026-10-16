"""Process-boundary visual QA regressions; synthetic runners, no real browser claim."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VisualProcessTests(unittest.TestCase):
    def fixture(self, root, runner='exit 0\n'):
        shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
        for filename, value in {
            'project.config.json': {'stack': {'frontend': 'React'}},
            'tasks/STATE.json': {'documentation_approved': True},
            'app/package.json': {},
            'app/node_modules/@playwright/test/package.json': {},
        }.items():
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        for filename in ('app/playwright.config.ts', 'app/tests/e2e/smoke.spec.ts'):
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('// synthetic fixture\n')
        binary = root / 'app/node_modules/.bin/playwright'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\n' + runner)
        binary.chmod(0o755)
        return binary

    def invoke(self, root):
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        return subprocess.run([sys.executable, '-m', 'exelia', 'visual', 'run'], cwd=root,
                              env=env, capture_output=True, text=True)

    def test_runner_success_and_failure_actual_cli(self):
        for status in (0, 7, 130):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self.fixture(root, f'exit {status}\n')
                result = self.invoke(root)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                record = json.loads((root / '.exelia/visual/last-run.json').read_text())
                self.assertEqual(record['exit_code'], status)
                self.assertEqual(record['status'], 'PASS' if status == 0 else 'FAIL')

    def test_missing_runner_configuration_and_browser_fail_actual_cli(self):
        for missing in ('runner', 'config', 'browser', 'invalid-config', 'signal'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                binary = self.fixture(root)
                if missing == 'runner':
                    binary.unlink()
                elif missing == 'config':
                    (root / 'app/playwright.config.ts').unlink()
                else:
                    script = {'browser': 'echo "browser executable missing" >&2\nexit 1\n',
                              'invalid-config': 'echo "invalid configuration" >&2\nexit 1\n',
                              'signal': 'kill -TERM $$\n'}[missing]
                    binary.write_text('#!/bin/sh\n' + script)
                result = self.invoke(root)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mobile_descriptor_uses_installed_chromium(self):
        from exelia.visual import PLAYWRIGHT_CONFIG
        self.assertIn("devices['Pixel 7']", PLAYWRIGHT_CONFIG)
        self.assertNotIn("devices['iPhone 13']", PLAYWRIGHT_CONFIG)
