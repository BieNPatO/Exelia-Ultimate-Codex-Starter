"""Offline interruption and retry evidence with real synthetic subprocess failures."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from installer.engine import Session


class InstallerRecoveryTests(unittest.TestCase):
    def action(self, code):
        return {'id': 'synthetic-download', 'kind': 'fixture',
                'command': [sys.executable, '-c', code], 'blocked': False, 'reason': 'Offline test'}

    def test_failed_network_step_is_not_passed_and_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = Session(root)
            with session.locked():
                failed = session.run_step(self.action("import sys; print('ENOTFOUND synthetic.invalid'); sys.exit(9)"))
            self.assertEqual(failed['status'], 'failed')
            self.assertEqual(failed['exit_code'], 9)
            resumed = Session(root)
            self.assertEqual(resumed.journal['steps']['synthetic-download']['status'], 'failed')
            with resumed.locked():
                passed = resumed.run_step(self.action("print('Synthetic local retry completed')"))
            self.assertEqual(passed['status'], 'passed')
            self.assertEqual(passed['exit_code'], 0)
            self.assertFalse((root/'.exelia-install/lock').exists())

    def test_interrupted_running_journal_and_stale_lock_can_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = Session(root)
            with session.locked():
                session.journal['steps']['synthetic-download'] = {'status': 'running', 'at': 'synthetic-interruption'}
                session.persist()
            # A dead-PID lock represents the previous process stopping before cleanup.
            lock = root/'.exelia-install/lock'
            lock.mkdir()
            (lock/'pid').write_text('0')
            resumed = Session(root)
            self.assertEqual(resumed.journal['steps']['synthetic-download']['status'], 'running')
            with resumed.locked():
                result = resumed.run_step(self.action("print('Resumed locally')"))
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(json.loads((root/'.exelia-install/journal.json').read_text())['steps']['synthetic-download']['status'], 'passed')

    def test_timeout_is_recorded_without_raw_authentication_output(self):
        from unittest.mock import patch
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = Session(root)
            with session.locked(), patch('installer.engine.subprocess.run', side_effect=subprocess.TimeoutExpired('synthetic', 1, output=b'never persist this raw output')):
                result = session.run_step(self.action('pass'))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['reason'], 'command timeout')
            self.assertNotIn('never persist', (root/'.exelia-install/journal.json').read_text())
