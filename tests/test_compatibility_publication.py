"""Actual publication CLI checks for source inventories and strict ZIP contents."""
import hashlib
import importlib.util
import os
from pathlib import Path
import py_compile
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PublicationCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'export'
        self.root.mkdir()
        (self.root / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/check-publication.py', self.root / 'scripts/check-publication.py')
        (self.root / 'exelia').mkdir()
        shutil.copy2(ROOT / 'exelia/security.py', self.root / 'exelia/security.py')
        (self.root / 'exelia/__init__.py').write_text('')
        for name in ('LICENSE', 'SECURITY.md', 'CONTRIBUTING.md', '.gitignore',
                     'README.md', 'docs/GITHUB_SETUP.md'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Synthetic publication fixture\n')
        (self.root / 'example.py').write_text('VALUE = 42\n')
        self.inventory()

    def inventory(self):
        paths = sorted(p for p in self.root.rglob('*') if p.is_file() and p.name != 'MANIFEST.sha256')
        (self.root / 'MANIFEST.sha256').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(self.root).as_posix() + '\n'
            for p in paths))

    def scan(self, *args):
        return subprocess.run([sys.executable, 'scripts/check-publication.py', *map(str, args)],
                              cwd=self.root, capture_output=True, text=True,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def archive(self):
        archive = Path(self.temporary.name) / 'release.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for path in self.root.rglob('*'):
                if path.is_file():
                    output.write(path, path.relative_to(self.root).as_posix())
        return archive

    def test_clean_export_and_clean_archive(self):
        for result in (self.scan(), self.scan('--archive', self.archive())):
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_post_test_export_ignores_only_valid_unlisted_bytecode(self):
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_archive_rejects_generated_cache_even_if_export_accepts_it(self):
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        result = self.scan('--archive', self.archive())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runtime', result.stdout)

    def test_inventoried_cache_is_forbidden(self):
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        self.inventory()
        result = self.scan()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('runtime', result.stdout)

    def test_unlisted_sensitive_file_in_cache_is_rejected(self):
        cache = self.root / '__pycache__'
        cache.mkdir()
        (cache / '.env').write_text('fixture=synthetic\n')
        self.assertNotEqual(self.scan().returncode, 0)

    def test_unlisted_invalid_or_source_less_bytecode_is_rejected(self):
        for name in ('example', 'unknown'):
            with self.subTest(name=name):
                path = self.root / '__pycache__' / (name + '.cpython-311.pyc')
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'not Python bytecode')
                self.assertNotEqual(self.scan().returncode, 0)
                path.unlink()

    @unittest.skipIf(os.name == 'nt', 'symlink fixture requires Unix permissions')
    def test_symlink_in_cache_is_rejected(self):
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        bytecode = Path(importlib.util.cache_from_source(str(self.root / 'example.py')))
        data = bytecode.read_bytes()
        bytecode.unlink()
        outside = Path(self.temporary.name) / 'outside.pyc'
        outside.write_bytes(data)
        bytecode.symlink_to(outside)
        self.assertNotEqual(self.scan().returncode, 0)

    def test_inventory_tampering_or_missing_file_is_rejected(self):
        (self.root / 'example.py').write_text('VALUE = 43\n')
        self.assertNotEqual(self.scan().returncode, 0)
        (self.root / 'example.py').unlink()
        self.assertNotEqual(self.scan().returncode, 0)

    def test_archive_rejects_symlink_traversal_and_sensitive_members(self):
        for name, mode in (('../escape.py', stat.S_IFREG), ('nested/.env', stat.S_IFREG),
                           ('link.py', stat.S_IFLNK)):
            with self.subTest(name=name):
                archive = self.archive()
                with zipfile.ZipFile(archive, 'a') as output:
                    member = zipfile.ZipInfo(name)
                    member.create_system = 3
                    member.external_attr = (mode | 0o644) << 16
                    output.writestr(member, 'synthetic fixture')
                self.assertNotEqual(self.scan('--archive', archive).returncode, 0)

    def test_compiled_synthetic_secret_fixture_is_incidental(self):
        source = self.root / 'example.py'
        # Split source markers remain scanner-safe but compile into a synthetic token.
        source.write_text("VALUE = 'gh' + 'p_' + 'q' * 36\n")
        self.inventory()
        py_compile.compile(str(source), doraise=True)
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.scan('--archive', self.archive()).returncode, 0)

    def test_bytecode_cannot_hide_secret_markers(self):
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        bytecode = Path(importlib.util.cache_from_source(str(self.root / 'example.py')))
        token = 'gh' + 'p_' + 'z' * 36
        with bytecode.open('ab') as output:
            output.write(token.encode())
        result = self.scan()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(token, result.stdout + result.stderr)

    def test_archive_member_secret_and_corruption_are_rejected(self):
        archive = self.archive()
        token = 'gh' + 'p_' + 'y' * 36
        with zipfile.ZipFile(archive, 'a') as output:
            output.writestr('notes.txt', token)
        result = self.scan('--archive', archive)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(token, result.stdout + result.stderr)
        archive.write_bytes(b'not a ZIP')
        self.assertNotEqual(self.scan('--archive', archive).returncode, 0)

    def test_no_inventory_retains_strict_export_rules(self):
        (self.root / 'MANIFEST.sha256').unlink()
        py_compile.compile(str(self.root / 'example.py'), doraise=True)
        self.assertNotEqual(self.scan().returncode, 0)


if __name__ == '__main__':
    unittest.main()
