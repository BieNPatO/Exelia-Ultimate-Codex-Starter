"""Private per-repository Node and Python tooling. No global writes by installer.

Only host-level language/runtime CLIs are prerequisites. npm/pip may maintain user
caches but packages/executables are installed under <repo>/.exelia-tools.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path


def node_bin(root: Path, name: str) -> Path:
    return root / '.exelia-tools/node/node_modules/.bin' / name


def python_bin(root: Path, name: str) -> Path:
    base = root / '.exelia-tools/python'
    return base / ('Scripts' if sys.platform == 'win32' else 'bin') / name


def _managed_directory(root: Path, directory: Path, *, venv: bool = False) -> None:
    """Reject redirected writable paths before installers can modify local tool state."""
    root = root.resolve()
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Project-local managed directory cannot be a symlink')
    if not directory.exists():
        return
    for entry in directory.rglob('*'):
        if not entry.is_symlink():
            continue
        # venv uses read-only links to the host interpreter; its libraries/cache stay local.
        interpreter = (venv and entry.parent == directory / ('Scripts' if sys.platform == 'win32' else 'bin')
                       and re.fullmatch(r'(?:python(?:\d+(?:\.\d+)?)?(?:\.exe)?|𝜋thon)', entry.name)
                       and entry.resolve() == Path(sys.executable).resolve())
        if interpreter:
            continue
        contained_lib64 = venv and entry.name == 'lib64' and entry.parent == directory and entry.resolve() == directory / 'lib'
        if not entry.resolve().is_relative_to(directory) or (entry.parent == directory and not contained_lib64):
            raise ValueError('Project-local managed content contains an unsafe symlink')


def local_executable(root: Path, name: str) -> Path | None:
    """Allow npm executable links only when their resolved content remains project-local."""
    root = root.resolve()
    if name in ('skills', 'playwright-cli', 'impeccable'):
        candidate = node_bin(root, name)
        base = root / '.exelia-tools/node'
    elif name in ('uv', 'ruff'):
        candidate = python_bin(root, name)
        base = root / '.exelia-tools/python'
    else:
        raise ValueError('Unsupported local tool')
    current = root
    for part in candidate.parent.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            return None
    if not candidate.is_file() or not candidate.resolve().is_relative_to(base) or not os.access(candidate, os.X_OK):
        return None
    return candidate


def install_node(root: Path, package: str, *, timeout: int = 600) -> subprocess.CompletedProcess:
    if not re.fullmatch(r'(?:@[a-z0-9_.-]+/)?[a-z0-9_.-]+@\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?', package):
        raise ValueError('Node tool installation requires an exact package version')
    root = root.resolve()
    base = root / '.exelia-tools/node'
    _managed_directory(root, base)
    _managed_directory(root, root / '.exelia-tools/npm-cache')
    base.mkdir(parents=True, exist_ok=True)
    profile = 'web' if package != 'skills@1.7.2' else 'core'
    existing = base / 'package.json'
    if existing.exists():
        installed = json.loads(existing.read_text())
        managed = json.loads((root / 'manifests/tool-dependencies/web/package.json').read_text())['devDependencies']
        if installed.get('dependencies') or set(installed.get('devDependencies', {})) - set(managed):
            raise ValueError('Unmanaged dependencies in installer-owned tools prefix; preserve and review them')
        if '@playwright/cli' in installed.get('devDependencies', {}):
            profile = 'web'
    source = root / 'manifests/tool-dependencies' / profile
    manifest = json.loads((source / 'package.json').read_text())
    name, version = package.rsplit('@', 1)
    if manifest['devDependencies'].get(name) != version:
        raise ValueError('Requested Node tool does not match reviewed dependency lock')
    for filename in ('package.json', 'package-lock.json'):
        # Replace the inode so a pre-existing hardlink cannot modify a file outside the prefix.
        with tempfile.NamedTemporaryFile(dir=base, delete=False) as temporary:
            temporary.write((source / filename).read_bytes())
        os.replace(temporary.name, base / filename)
    env = os.environ.copy()
    env['npm_config_cache'] = str(root / '.exelia-tools/npm-cache')
    return subprocess.run(['npm', 'ci', '--include=dev', '--global=false',
                           '--cache', str(root / '.exelia-tools/npm-cache'),
                           '--no-audit', '--no-fund', '--ignore-scripts'],
                          cwd=base.resolve(), capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          check=False, timeout=timeout, env=env)



def install_python(root: Path, package: str, *, timeout: int = 600) -> subprocess.CompletedProcess:
    if not re.fullmatch(r'(uv|ruff)==\d+\.\d+\.\d+', package):
        raise ValueError('Python tool requires a reviewed exact version')
    root = root.resolve()
    name = package.split('==')[0]
    requirements = root / 'manifests/tool-dependencies' / ('requirements-' + name + '.txt')
    declarations = [line.split()[0] for line in requirements.read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith(('#', '--'))] if requirements.is_file() else []
    if declarations != [package]:
        raise ValueError('Requested Python tool does not match reviewed hash lock')
    base=root/'.exelia-tools/python'
    _managed_directory(root, base, venv=True)
    _managed_directory(root, root / '.exelia-tools/pip-cache')
    interpreter=python_bin(root,'python')
    if not interpreter.is_file():
        result=subprocess.run([sys.executable,'-m','venv',str(base)],cwd=root,
                              capture_output=True,text=True,stdin=subprocess.DEVNULL,
                              check=False,timeout=100)
        if result.returncode:
            return result
    _managed_directory(root, base, venv=True)
    _managed_directory(root, root / '.exelia-tools/pip-cache')
    env=os.environ.copy()
    env['PIP_CONFIG_FILE'] = os.devnull
    return subprocess.run([str(interpreter),'-m','pip','--isolated','install','--disable-pip-version-check',
                           '--no-user','--prefix',str(base),'--cache-dir',str(root/'.exelia-tools/pip-cache'),
                           '--no-input','--require-hashes','-r',str(requirements)],cwd=root,capture_output=True,text=True,
                          stdin=subprocess.DEVNULL,check=False,timeout=timeout,env=env)


if __name__ == '__main__':
    binary = local_executable(Path(sys.argv[1]), sys.argv[2])
    if binary is None:
        print('Project-local tool missing or redirected outside its managed prefix', file=sys.stderr)
        sys.exit(3)
    print(binary)
