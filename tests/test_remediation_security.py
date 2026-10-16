"""Synthetic-only regressions for installer logs and release hygiene."""
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from installer.engine import Session

ROOT = Path(__file__).resolve().parents[1]


class SecurityRemediationTests(unittest.TestCase):
    def test_installer_redacts_authentication_output_and_restricts_logs(self):
        samples = [
            ('Authorization: Bearer ' + 'synthetic_bearer', 'synthetic_bearer'),
            ('{"token": "synthetic quoted token"}', 'synthetic quoted token'),
            ("password='synthetic password with spaces'", 'synthetic password with spaces'),
            ('export OPENAI_API_KEY="synthetic_environment"', 'synthetic_environment'),
            ('AWS_SECRET_ACCESS_KEY=synthetic_cloud', 'synthetic_cloud'),
            ('https://user:synthetic_url_password@example.invalid', 'synthetic_url_password'),
            ('gh' + 'p_' + 'a' * 36, 'a' * 36),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = '\n'.join(row[0] for row in samples)
            result = subprocess.CompletedProcess([sys.executable], 0, output, '')
            with patch('installer.engine.subprocess.run', return_value=result):
                record = Session(root).run_step({'id': 'redaction', 'kind': 'fixture',
                                               'command': [sys.executable]})
            log = root / record['log']
            text = log.read_text()
            for _, marker in samples:
                self.assertNotIn(marker, text)
            self.assertEqual(stat.S_IMODE(log.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(log.parent.stat().st_mode), 0o700)

    def test_redaction_suppresses_entire_auth_bearing_output(self):
        from exelia.security import redact
        samples = (
            'PASSWORD="synthetic-first\nsynthetic-second\nsynthetic-third"\n',
            '--token synthetic_cli_token\n',
            '--password synthetic_cli_password\n',
            '--api-key synthetic_cli_key\n',
            'ssh://user:synthetic_uri_password@example.invalid\n',
            'postgresql://user:synthetic_uri_password@example.invalid/db\n',
        )
        for output in samples:
            with self.subTest(output_kind=output.split()[0][:12]):
                self.assertEqual(redact('benign prefix\n' + output + 'benign suffix\n'),
                                 '[REDACTED sensitive output]\n')
        benign = 'Dependency installed successfully\n2 packages checked\n'
        self.assertEqual(redact(benign), benign)

    def test_log_directory_cannot_redirect_output_outside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'repo'
            root.mkdir()
            outside = Path(directory) / 'outside'
            outside.mkdir()
            (root / '.exelia-install').mkdir()
            (root / '.exelia-install/logs').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                Session(root).run_step({'id': 'guard', 'kind': 'fixture',
                                       'command': [sys.executable]})
            self.assertEqual(list(outside.iterdir()), [])

    def test_installer_state_root_symlink_cannot_write_outside_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'repo'
            root.mkdir()
            outside = Path(directory) / 'outside'
            outside.mkdir()
            marker = outside / 'marker'
            marker.write_text('untouched')
            (root / '.exelia-install').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                with Session(root).locked():
                    pass
            self.assertEqual(marker.read_text(), 'untouched')
            self.assertEqual(sorted(path.name for path in outside.iterdir()), ['marker'])

    def test_installer_runtime_children_cannot_redirect_writes(self):
        for child, operation in (
            ('journal.json', lambda session: session.persist()),
            ('backups', lambda session: session.backup('config.txt')),
            ('lock/pid', lambda session: session.locked().__enter__()),
        ):
            with self.subTest(child=child), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'repo'
                root.mkdir()
                outside = Path(directory) / 'outside'
                outside.mkdir()
                marker = outside / 'marker'
                marker.write_text('untouched')
                (root / 'config.txt').write_text('synthetic config')
                session = Session(root)
                path = root / '.exelia-install' / child
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(outside if child == 'backups' else marker,
                                target_is_directory=child == 'backups')
                with self.assertRaises(RuntimeError):
                    operation(session)
                self.assertEqual(marker.read_text(), 'untouched')
                self.assertEqual(sorted(item.name for item in outside.iterdir()), ['marker'])

    def test_skill_install_rejects_redirected_ancestor_directories(self):
        for folder in ('.agents', '.codex'):
            with self.subTest(folder=folder), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'repo'
                root.mkdir()
                outside = Path(directory) / 'outside'
                outside.mkdir()
                (root / folder).symlink_to(outside, target_is_directory=True)
                with patch('installer.engine.subprocess.run') as runner:
                    with self.assertRaises(RuntimeError):
                        Session(root).run_step({'id': 'skill-synthetic', 'kind': 'skill',
                                               'name': 'synthetic', 'command': [sys.executable]})
                    runner.assert_not_called()
                self.assertEqual(list(outside.iterdir()), [])

    def test_capability_hashing_rejects_redirected_skill_ancestors(self):
        from exelia.capabilities import resolve
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'repo'
            root.mkdir()
            outside = Path(directory) / 'outside'
            skill = outside / 'systematic-debugging/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text('synthetic external skill must never be read')
            (root / '.agents').mkdir()
            (root / '.agents/skills').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                resolve(root)

    def test_rejected_tool_configuration_records_failed_step_without_raw_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = Session(root)
            with patch('installer.engine.install_node',
                       side_effect=ValueError('synthetic sensitive configuration detail')):
                record = session.run_step({'id': 'local-npm-fixture', 'kind': 'local-npm',
                                           'name': 'fixture', 'package': 'fixture@1.0.0',
                                           'command': [sys.executable]})
            self.assertEqual(record['status'], 'failed')
            self.assertEqual(record['reason'], 'tool configuration rejected')
            self.assertEqual(session.journal['steps']['local-npm-fixture']['status'], 'failed')
            journal = session.journal_file.read_text()
            self.assertNotIn('synthetic sensitive configuration detail', journal)

    def test_nested_sensitive_names_and_explicit_examples(self):
        from exelia.security import is_sensitive_path
        for path in ('.env', '.env.local', 'api/src/.env', 'api/.env.production',
                     'nested/id_rsa', 'api/auth.json', 'deep/service-account-dev.json',
                     'nested/key.pem', 'api/.npmrc', 'api/.aws/credentials'):
            with self.subTest(path=path):
                self.assertTrue(is_sensitive_path(path))
        for path in ('api/.env.example', 'api/.env.local.example', 'api/.env.sample',
                     'docs/credentials.json.example', 'api/config.json', 'monkey.py'):
            with self.subTest(path=path):
                self.assertFalse(is_sensitive_path(path))

    def test_publication_detects_current_and_deleted_synthetic_token_without_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'exelia', root / 'exelia', ignore=shutil.ignore_patterns('__pycache__'))
            (root / 'scripts').mkdir()
            shutil.copy2(ROOT / 'scripts/check-publication.py', root / 'scripts/check-publication.py')
            for name in ('LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', '.gitignore',
                         'README.md', 'docs/GITHUB_SETUP.md'):
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('Fixture\n')
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            git('init', '-q')
            git('config', 'user.name', 'Synthetic Review')
            git('config', 'user.email', 'synthetic@example.invalid')
            token = 'github_' + 'pat_' + 'S' * 70
            (root / 'fixture.txt').write_text(token)
            git('add', '.')
            git('commit', '-qm', 'fixture baseline')
            def scan():
                return subprocess.run([sys.executable, 'scripts/check-publication.py'], cwd=root,
                                      text=True, capture_output=True)
            current = scan()
            self.assertNotEqual(current.returncode, 0)
            self.assertNotIn(token, current.stdout + current.stderr)
            (root / 'fixture.txt').write_text('removed synthetic token\n')
            git('add', 'fixture.txt')
            git('commit', '-qm', 'remove fixture marker')
            historical = scan()
            self.assertNotEqual(historical.returncode, 0)
            self.assertIn('history', historical.stdout.lower())
            self.assertNotIn(token, historical.stdout + historical.stderr)

    def test_history_checks_every_path_for_shared_blob_content(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('publication_history_fixture',
                                                     ROOT / 'scripts/check-publication.py')
        scanner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scanner)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)
            git('init', '-q')
            git('config', 'user.name', 'Synthetic Review')
            git('config', 'user.email', 'synthetic@example.invalid')
            content = '{"fixture": "synthetic non-pattern data"}\n'
            (root / 'notes.json').write_text(content)
            git('add', 'notes.json')
            git('commit', '-qm', 'ordinary shared blob')
            (root / 'credentials.json').write_text(content)
            git('add', 'credentials.json')
            git('commit', '-qm', 'same blob under credential filename')
            (root / 'credentials.json').unlink()
            git('add', 'credentials.json')
            git('commit', '-qm', 'remove credential filename')
            problems = []
            with patch.object(scanner, 'ROOT', root):
                scanner.scan_history(problems)
            self.assertTrue(any('history credential filename: credentials.json' in error
                                for error in problems), problems)

    def test_markers_cover_common_token_formats(self):
        from exelia.security import secret_markers
        for token in ('gh' + 'p_' + 'a' * 36, 'github_' + 'pat_' + 'b' * 70,
                      'gl' + 'pat-' + 'c' * 24, 'sk-' + 'proj-' + 'd' * 40,
                      'AK' + 'IA' + 'A' * 16, 'npm_' + 'e' * 36,
                      'xox' + 'b-' + '1' * 12 + '-' + '2' * 12 + '-' + 'f' * 24):
            self.assertTrue(secret_markers(token))


if __name__ == '__main__':
    unittest.main()
