"""Best-effort dependency and integration checks; no credential exposure."""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tomllib
from pathlib import Path
from typing import Any
from .platforms import detect
from .localtools import node_bin, python_bin, local_executable

VERSION = re.compile(r'(?<![\w.])v?(\d+(?:\.\d+){0,3})(?![\d.])')


def command(args: list[str], timeout: int = 9, cwd: Path | None = None) -> dict:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL, check=False)
        combined = (result.stdout + '\n' + result.stderr).strip()
        return {'ok':result.returncode == 0,'code':result.returncode,'output':combined[:2000]}
    except (OSError, subprocess.TimeoutExpired) as ex:
        return {'ok':False,'code':None,'output':type(ex).__name__}


def version(text: str) -> str | None:
    m = VERSION.search(text)
    return m.group(1) if m else None


def compatible(found: str | None, minimum: str | None) -> bool:
    if not found:
        return minimum is None
    if not minimum:
        return True
    def parts(v): return tuple(int(x) for x in v.split('.'))
    return parts(found) >= parts(minimum)


def tool_info(tool: dict, root: Path) -> dict:
    binary = tool['binary']
    mode=tool.get('install')
    if mode=='bundled-python-lib':
        vendor=root/'installer/_vendor'
        required=('rich','markdown_it','mdurl','pygments')
        present=all((vendor/package/'__init__.py').is_file() for package in required)
        return {'status':'ready' if present else 'missing','path':str(vendor) if present else None,
                'version':'15.0.0' if present else None,
                'detail':'bundled Rich UI · available offline from first launch' if present else 'bundled UI missing; plain fallback'}
    if mode=='local-python-lib':
        interp=python_bin(root,'python')
        if not interp.is_file():
            return {'status':'missing','path':None,'version':None,'detail':'project-local Python venv missing'}
        res=command([str(interp),'-c',
            'import rich, importlib.metadata; print(importlib.metadata.version("rich"))'])
        return {'status':'ready' if res['ok'] else 'missing','path':str(interp),
                'version':version(res['output']) if res['ok'] else None,
                'detail':'Rich present in project venv' if res['ok'] else 'Rich missing in project venv'}
    if mode=='local-npm':
        candidate=local_executable(root,binary)
        path=str(candidate) if candidate else None
    elif mode=='local-python':
        candidate=local_executable(root,binary)
        path=str(candidate) if candidate else None
    else:
        path = sys.executable if tool['id']=='python' else shutil.which(binary)
    if not path:
        return {'status':'missing','path':None,'version':None,'detail':'project-local tool not installed' if mode in ('local-npm','local-python') else 'host prerequisite not in PATH'}
    if binary == 'python3':
        result = command([path,'--version'])
    elif binary == 'docker':
        result = command([path,'--version'])
    else:
        result = command([path, '--version'])
    v = version(result['output'])
    if not result['ok']:
        status = 'broken'
    elif not compatible(v,tool.get('minimum')):
        status = 'incompatible'
    else:
        status = 'ready'
    return {'status':status,'path':path,'version':v,'detail':result['output'][:140]}


def scan_skill(name: str, root: Path, home: Path) -> dict:
    """Strict local scope: a global skill NEVER satisfies a project requirement."""
    projects = [root/'.agents/skills'/name, root/'.codex/skills'/name]
    globals_ = [home/'.agents/skills'/name, home/'.codex/skills'/name]
    def valid(folder):
        try:
            if folder.is_symlink() or (folder/'SKILL.md').is_symlink():return False
            content=(folder/'SKILL.md').read_text(encoding='utf-8')
            return (content.startswith('---\n') and '\nname:' in content[:700]
                    and '\ndescription:' in content[:900])
        except (OSError, UnicodeError): return False
    found=[str(folder) for folder in projects if folder.resolve().is_relative_to(root.resolve()) and valid(folder)]
    existing_global=any(valid(folder) for folder in globals_)
    if found:
        return {'status':'ready','locations':found,'detail':'project-local SKILL.md verified',
                'global_also_present':existing_global}
    detail='global copy exists, project copy required' if existing_global else 'no project-local SKILL.md'
    return {'status':'missing','locations':[],'detail':detail,'global_also_present':existing_global}


def other_skills(root: Path, home: Path, expected: set[str]) -> list[str]:
    """Inventory additional skills without loading their untrusted instructions."""
    found=set()
    for folder in (root/'.agents/skills',root/'.codex/skills'):
        if not folder.is_dir():continue
        for skill in folder.iterdir():
            if skill.name not in expected and (skill/'SKILL.md').is_file():
                found.add(skill.name)
    return sorted(found)


def codex_plugins() -> dict:
    """Do not inspect or mutate user-level plugins in strict project-local mode."""
    return {'status':'not_applicable','names':[],'marketplace_present':False,
            'detail':'Only local Ponytail skill is used; no user-level plugin install or detection'}


def mcp_servers(root: Path) -> dict:
    """Report ONLY MCP servers configured in this trusted project.

    Codex may load additional user-global MCP servers, but we deliberately
    neither count nor modify them in the local installation plan.
    """
    names=set()
    cfg=root/'.codex/config.toml'
    try:
        data=tomllib.loads(cfg.read_text(encoding='utf-8'))
        names.update(data.get('mcp_servers',{}))
    except (ValueError,OSError):pass
    return {'configured_names':sorted(names),
            'verification':'project configuration only; auth and connectivity unverified'}


def inspect(root: Path, manifest: dict, home: Path | None = None) -> dict:
    home=home or Path.home()
    tools={t['id']:tool_info(t,root) for t in manifest['tools']}
    skills={s['name']:scan_skill(s['name'],root,home) for s in manifest['skills']}
    plugins=codex_plugins()
    mcp=mcp_servers(root)
    extras=other_skills(root,home,{s['name'] for s in manifest['skills']} |
                        {'premium-motion','project-delivery','python-backend-engineering'})
    daemon={'status':'missing','detail':'Docker CLI unavailable'}
    if tools['docker']['status']=='ready':
        d=command(['docker','info','--format','{{.ServerVersion}}'],timeout=7)
        daemon={'status':'ready' if d['ok'] else 'not-running', 'detail':d['output'][:120]}
    git={ 'inside_repo':False, 'repo_root':None,'identity':False,'clean':None }
    r=command(['git','rev-parse','--show-toplevel'],cwd=root)
    if r['ok']:
        path=Path(r['output'].splitlines()[0]).resolve()
        git['inside_repo']=True
        git['repo_root']=str(path)
        git['own_repo']=(path==root.resolve())
        st=command(['git','status','--porcelain'],cwd=root)
        git['clean']=(not st['output']) if st['ok'] else None
    n=command(['git','config','user.name'],cwd=root)
    e=command(['git','config','user.email'],cwd=root)
    git['identity']=bool(n['ok'] and n['output'] and e['ok'] and e['output'])
    return {'platform':detect(),'tools':tools,'skills':skills,'additional_installed_skills':extras,'plugins':plugins,'mcp':mcp,'docker_daemon':daemon,'git':git}
