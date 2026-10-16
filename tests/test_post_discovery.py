"""Starter integrity stays independent of the destination application's selected stack."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PostDiscoveryTests(unittest.TestCase):
    def test_configuration_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name in ('exelia', 'scripts', 'tests', 'docs', 'installer', '.codex'):
                shutil.copytree(ROOT/name, root/name, ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tasks').mkdir()
            (root/'tasks/STATE.json').write_text(json.dumps({'documentation_approved': False}))
            (root/'tasks/backlog.json').write_text(json.dumps({'tasks': []}))
            for frontend, backend, security in ((None, None, False), ('React', None, False),
                                                (None, 'FastAPI', False), ('React', 'FastAPI', False),
                                                ('React', 'FastAPI', True)):
                with self.subTest(frontend=frontend, backend=backend, security=security):
                    config = {'stack': {'frontend': frontend, 'backend': backend},
                              'conversation_language': 'en', 'application_ui_languages': ['en-US'],
                              'capabilities': {'security_review': security}}
                    (root/'project.config.json').write_text(json.dumps(config))
                    result = subprocess.run([sys.executable, '-m', 'unittest',
                        'test_exelia_automation.CapabilityTests.test_core_only_before_discovery',
                        'test_starter.StarterTests.test_docs_gate_fails_before_discovery',
                        'test_starter.StarterTests.test_app_gate_fails_without_approval',
                        'test_starter.StarterTests.test_state_command_rejects_stage_before_approval'],
                        cwd=root/'tests', env={**__import__('os').environ, 'PYTHONPATH':str(root)},
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    plan = subprocess.run([sys.executable, '-m', 'exelia', 'capabilities', 'plan'],
                                          cwd=root, capture_output=True, text=True)
                    self.assertEqual(plan.returncode, 0, plan.stderr)
                    names = {x['name'] for x in json.loads(plan.stdout)['selected']}
                    self.assertEqual('frontend-design' in names, frontend is not None)
                    self.assertEqual('fastapi' in names, backend is not None)
                    self.assertEqual('differential-review' in names, security)
