"""Private per-repository Node and Python tooling. No global writes by installer.

Only host-level language/runtime CLIs are prerequisites. npm/pip may maintain user
caches but packages/executables are installed under <repo>/.exelia-tools.
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path


def node_bin(root: Path, name: str) -> Path:
    return root / '.exelia-tools/node/node_modules/.bin' / name


def python_bin(root: Path, name: str) -> Path:
    base = root / '.exelia-tools/python'
    return base / ('Scripts' if sys.platform == 'win32' else 'bin') / name


def install_node(root: Path, package: str, *, timeout: int = 600) -> subprocess.CompletedProcess:
    base = root / '.exelia-tools/node'
    base.mkdir(parents=True, exist_ok=True)
    # This npm prefix is PRIVATE to the repository; --save-exact retains both
    # dependencies when adding the second package, unlike --no-save.
    if not (base / 'package.json').exists():
        (base / 'package.json').write_text(json.dumps({
            'name':'exelia-project-tools','version':'1.0.0','private':True,
            'description':'Local development tools only', 'devDependencies':{}
        },indent=2)+'\n')
    env=os.environ.copy()
    env['npm_config_cache']=str(root/'.exelia-tools/npm-cache')
    return subprocess.run(['npm','install','--prefix',str(base),'--save-dev','--save-exact',
                           '--no-audit','--no-fund','--ignore-scripts',package],
                          cwd=root,capture_output=True,text=True,stdin=subprocess.DEVNULL,
                          check=False,timeout=timeout,env=env)


def install_python(root: Path, package: str, *, timeout: int = 600) -> subprocess.CompletedProcess:
    base=root/'.exelia-tools/python'
    interpreter=python_bin(root,'python')
    if not interpreter.is_file():
        result=subprocess.run([sys.executable,'-m','venv',str(base)],cwd=root,
                              capture_output=True,text=True,stdin=subprocess.DEVNULL,
                              check=False,timeout=100)
        if result.returncode:
            return result
    env=os.environ.copy()
    env['PIP_CACHE_DIR']=str(root/'.exelia-tools/pip-cache')
    return subprocess.run([str(interpreter),'-m','pip','install','--disable-pip-version-check',
                           '--no-input',package],cwd=root,capture_output=True,text=True,
                          stdin=subprocess.DEVNULL,check=False,timeout=timeout,env=env)
