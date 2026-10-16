"""Python interpreter links are read-only exceptions to writable-prefix confinement."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from installer.localtools import _managed_directory

ROOT = Path(__file__).resolve().parents[1]


class VenvCompatibilityTests(unittest.TestCase):
    def test_trusted_base_interpreter_link_is_allowed(self):
        for executable_name in ('python', 'python3', 'python3.11', 'python3.14', '𝜋thon'):
            with self.subTest(name=executable_name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                base = root / '.exelia-tools/python'
                (base / 'bin').mkdir(parents=True)
                trusted = root / 'base-python'; trusted.write_text('synthetic interpreter')
                external = root / 'external-python'; external.write_text('synthetic venv copy')
                (base / 'bin' / executable_name).symlink_to(trusted)
                with patch('installer.localtools.sys.executable', str(external)), patch(
                        'installer.localtools.sys._base_executable', str(trusted), create=True):
                    _managed_directory(root, base, venv=True)

    def test_unknown_interpreter_is_not_trusted_by_pyvenv_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            base = root / '.exelia-tools/python'
            (base / 'bin').mkdir(parents=True)
            foreign = root / 'foreign-python'; foreign.write_text('synthetic foreign interpreter')
            (base / 'bin/python').symlink_to(foreign)
            (base / 'pyvenv.cfg').write_text('home = ' + str(foreign.parent) + '\nexecutable = ' + str(foreign) + '\n')
            with self.assertRaisesRegex(ValueError, 'unsafe symlink'):
                _managed_directory(root, base, venv=True)

    def test_interpreter_exception_cannot_redirect_writable_paths(self):
        for relative in ('bin', 'lib', 'lib64', 'lib/python3.11/site-packages', 'include',
                         'bin/ruff', 'pyvenv.cfg'):
            with self.subTest(path=relative), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                base = root / '.exelia-tools/python'; base.mkdir(parents=True)
                outside = root / 'outside'; outside.mkdir()
                link = base / relative; link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'unsafe symlink'):
                    _managed_directory(root, base, venv=True)
                self.assertEqual(list(outside.iterdir()), [])

    def test_real_offline_install_from_system_and_external_venvs(self):
        base_interpreter = str(Path(getattr(sys, '_base_executable', sys.executable)).resolve())
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve()
            interpreters = [('system', base_interpreter)]
            for mode in ('copies', 'symlinks'):
                external = workspace / ('external-' + mode)
                creation = subprocess.run([base_interpreter, '-m', 'venv', '--without-pip', '--' + mode,
                                           str(external)], capture_output=True, text=True, timeout=90)
                self.assertEqual(creation.returncode, 0, creation.stderr)
                interpreters.append((mode, str(external / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))))
            for mode, executable in interpreters:
                with self.subTest(interpreter=mode):
                    root = workspace / ('repo-' + mode); root.mkdir()
                    outside = workspace / ('outside-' + mode); outside.mkdir()
                    self.make_wheel(root)
                    environment = os.environ.copy()
                    environment.update({'PIP_TARGET': str(outside), 'PIP_PREFIX': str(outside),
                                        'PIP_USER': '1', 'PIP_CACHE_DIR': str(outside),
                                        'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1'})
                    if mode != 'system':
                        environment['VIRTUAL_ENV'] = str(Path(executable).parent.parent)
                        environment['PATH'] = str(Path(executable).parent) + os.pathsep + environment.get('PATH', '')
                    program = '''import json, pathlib, sys
from installer.localtools import install_python
root = pathlib.Path(sys.argv[1])
for attempt in range(2):
    result = install_python(root, 'ruff==0.17.1')
    assert result.returncode == 0, result.stderr
print(json.dumps({'executable': sys.executable, 'base': sys._base_executable, 'attempts': 2}))
'''
                    result = subprocess.run([executable, '-c', program, str(root)], cwd=ROOT,
                                            env=environment, capture_output=True, text=True, timeout=180)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)['attempts'], 2)
                    self.assertTrue(list((root / '.exelia-tools/python').rglob('ruff_fixture.py')))
                    self.assertEqual(list(outside.iterdir()), [])

    @staticmethod
    def make_wheel(root):
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


if __name__ == '__main__':
    unittest.main()
