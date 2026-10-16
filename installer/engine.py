"""Plan/apply/verify/recovery engine. External installs require an explicit apply phase.

Only project-owned configuration changes are automatically reversible. Host
prerequisites are detected, never installed. Project-private npm/venv installs
are reproducible but are not automatically deleted by config rollback.
"""
from __future__ import annotations
import contextlib, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from .probe import inspect, command
from .processes import run_group, timeout_budget
from .localtools import node_bin, python_bin, install_node, install_python
from exelia.security import redact

SKIP = {'ready', 'already_available'}


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def read_json(path: Path, default: dict | None = None) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(default or {})


def project_path_guard(root: Path, path: Path):
    """Reject redirected writable paths, including symlinks in any project ancestor."""
    try:
        parts = path.relative_to(root).parts
    except ValueError as error:
        raise RuntimeError('Installer writable path escapes project') from error
    if '..' in parts:
        raise RuntimeError('Installer path traversal is forbidden')
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink() or not current.resolve().is_relative_to(root):
            raise RuntimeError('Installer writable paths must remain inside the project without symlinks')


def runtime_guard(root: Path, path: Path):
    """Refuse redirected installer state before reads, writes or stale-lock removal."""
    if not path.is_relative_to(root / '.exelia-install'):
        raise RuntimeError('Installer runtime path escapes project state')
    project_path_guard(root, path)


def atomic_json(path: Path, value: dict):
    state = next((parent for parent in (path, *path.parents) if parent.name == '.exelia-install'), None)
    if state is not None:
        runtime_guard(state.parent, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle=tempfile.NamedTemporaryFile('w',encoding='utf-8', dir=path.parent,delete=False)
    try:
        with handle as f:
            json.dump(value,f,indent=2,ensure_ascii=False)
            f.write('\n')
        os.replace(handle.name,path)
    finally:
        if os.path.exists(handle.name):os.unlink(handle.name)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_actions(root: Path, manifest: dict, findings: dict, *, optional: bool=False,
                 system_changes: bool=False) -> list[dict]:
    """No host-level installer actions. Every executable action is project-scoped."""
    actions=[]
    tools=findings['tools']
    from exelia.capabilities import resolve
    required = {item["name"] for item in resolve(root, include_qa=optional)["selected"]}
    missing_skills=[s for s in manifest['skills'] if s['name'] in required and findings['skills'][s['name']]['status']!='ready']
    requires_cli=any(s.get('installer','skills-cli')=='skills-cli' for s in missing_skills)
    for t in manifest['tools']:
        info=tools[t['id']]
        if info['status']=='ready':continue
        if t['category']=='optional' and not optional:continue
        if t['id']=='playwright-cli' and 'playwright-cli' not in required:continue
        if t['id'] in ('uv','ruff') and not (read_json(root/'project.config.json').get('stack') or {}).get('backend'):continue
        if t['id']=='skills-cli' and not requires_cli:continue
        if t['id']=='impeccable-cli' and not any(sk['name']=='impeccable' for sk in missing_skills):continue
        method=t.get('install','host-manual')
        if method=='local-npm':
            cmd=['npm','ci','--include=dev','--global=false','--cache','../npm-cache',
                 '--no-audit','--no-fund','--ignore-scripts']
            actions.append({'id':'local-npm-'+t['id'],'kind':'local-npm','name':t['id'],
                 'reason':info['detail'],'command':cmd,'package':t['package'],
                 'working_directory':'.exelia-tools/node',
                 'scope':'project','blocked':False})
        elif method in ('local-python','local-python-lib'):
            actions.append({'id':'local-python-'+t['id'],'kind':'local-python','name':t['id'],
                'reason':info['detail'],
                'command':['.exelia-tools/python/bin/python','-m','pip','--isolated','install','--no-user',
                           '--prefix','.exelia-tools/python','--cache-dir','.exelia-tools/pip-cache','--require-hashes',
                           '-r','manifests/tool-dependencies/requirements-'+t['id']+'.txt'],
                'package':t['package'],'scope':'project','blocked':False})
        else:
            actions.append({'id':'host-prereq-'+t['id'],'kind':'manual','name':t['id'],
                'reason':'HOST PREREQUISITE: '+info['detail']+'; not installed or changed by Exelia',
                'command':None,'scope':'host','blocked':True})
    if findings['docker_daemon']['status']!='ready':
        actions.append({'id':'host-docker-daemon','kind':'manual','name':'Docker daemon',
                        'reason':findings['docker_daemon']['detail'],'command':None,
                        'scope':'host','blocked':True})
    for skill in missing_skills:
        name=skill['name']
        kind=skill.get('installer','skills-cli')
        if kind=='impeccable':
            actions.append({'id':'skill-'+name,'kind':'manual','name':name,
               'reason':'Interactive upstream installer: select Codex + PROJECT (never global)',
               'command':['./scripts/local-tool.sh','impeccable','install'],
               'scope':'project','blocked':True})
        elif kind=='playwright-cli':
            actions.append({'id':'skill-'+name,'kind':'skill-playwright','name':name,
               'reason':'Install skill into project .agents/skills (without -g)',
               'command':['./scripts/local-tool.sh','playwright-cli','install','--skills=agents'],
               'scope':'project','blocked':False})
        else:
            actions.append({'id':'skill-'+name,'kind':'skill','name':name,'source':skill['source'],
               'reason':'Project skill required (global copies are not used)',
               'command':['./scripts/local-tool.sh','skills','add',
                          'https://github.com/'+skill['source']+'/tree/'+skill['commit'] if skill.get('commit') else skill['source'],'--skill',name,
                          '-a','codex','-y','--copy'],
               'scope':'project','blocked':False})
    # OpenAI Docs and Context7 are declared in trusted project config; never
    # run ctx7 setup --codex because its default writes user-global state.
    configured=set(findings['mcp']['configured_names'])
    for item in manifest['mcp']:
        if item['name'] not in configured:
            actions.append({'id':'mcp-'+item['name'],'kind':'manual','name':item['name'],
              'reason':'Missing project-scoped MCP configuration. Inspect .codex/config.toml.',
              'command':None,'scope':'project','blocked':True})
    assert len({a['id'] for a in actions})==len(actions)
    return actions


class Session:
    def __init__(self, root: Path):
        self.root=root.resolve()
        self.state_dir=self.root/'.exelia-install'
        self.journal_file=self.state_dir/'journal.json'
        self.lock_dir=self.state_dir/'lock'
        runtime_guard(self.root, self.journal_file)
        self.journal=read_json(self.journal_file, {'version':2,'attempts':[],'steps':{},'backups':[]})
        self.logs_dir=self.state_dir/'logs'

    @contextlib.contextmanager
    def locked(self):
        runtime_guard(self.root, self.lock_dir / 'pid')
        self.state_dir.mkdir(exist_ok=True)
        try:
            self.lock_dir.mkdir()
        except FileExistsError:
            pid_file=self.lock_dir/'pid'
            try: pid=int(pid_file.read_text())
            except (ValueError, OSError): pid=0
            alive=False
            if pid>0:
                try: os.kill(pid,0);alive=True
                except ProcessLookupError:pass
                except PermissionError:alive=True
            if alive:
                raise RuntimeError(f'Another installer process is active (PID {pid}).')
            # Removal of stale locks is explicit and safe only if process is not alive.
            shutil.rmtree(self.lock_dir)
            self.lock_dir.mkdir()
        (self.lock_dir/'pid').write_text(str(os.getpid()))
        try:
            yield
        finally:
            runtime_guard(self.root, self.lock_dir)
            shutil.rmtree(self.lock_dir,ignore_errors=True)

    def persist(self):
        atomic_json(self.journal_file,self.journal)

    def backup(self, relative: str) -> dict:
        # Snapshots only project-owned files, never follow links outside workspace.
        target=(self.root/relative)
        if not target.resolve().is_relative_to(self.root):
            raise RuntimeError('Backup path escapes project')
        if not target.is_file():
            entry={'path':relative,'existed':False,'before':None,'after':None}
        else:
            original=target.read_bytes()
            bname=str(len(self.journal['backups'])+1)+'-'+sha(relative.encode())[:10]
            folder=self.state_dir/'backups'
            runtime_guard(self.root, folder / bname)
            folder.mkdir(parents=True,exist_ok=True)
            (folder/bname).write_bytes(original)
            entry={'path':relative,'existed':True,'stored':bname,
                   'before':sha(original),'after':None}
        self.journal['backups'].append(entry)
        self.persist()
        return entry

    def backup_complete(self, entry: dict):
        target=self.root/entry['path']
        entry['after']=sha(target.read_bytes()) if target.exists() else None
        self.persist()

    def restore(self) -> list[str]:
        runtime_guard(self.root, self.journal_file)
        lines=[]
        for entry in reversed(self.journal.get('backups',[])):
            target=self.root/entry['path']
            if not target.resolve().is_relative_to(self.root):
                lines.append('SKIP outside project '+entry['path']); continue
            # Do not overwrite any user modifications after installer touched the file.
            current=sha(target.read_bytes()) if target.is_file() else None
            if current!=entry.get('after'):
                lines.append('SKIP changed since install: '+entry['path']);continue
            if entry['existed']:
                target.parent.mkdir(parents=True,exist_ok=True)
                source = self.state_dir/'backups'/entry['stored']
                runtime_guard(self.root, source)
                shutil.copyfile(source,target)
                lines.append('RESTORED '+entry['path'])
            elif target.exists():
                if target.is_file(): target.unlink();lines.append('REMOVED installer-created '+entry['path'])
        self.journal['rollback_at']=utc()
        self.journal['rollback_notes']=lines
        self.persist()
        return lines

    def run_step(self, action: dict) -> dict:
        runtime_guard(self.root, self.logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.logs_dir.chmod(0o700)
        if action.get('kind') in ('skill', 'skill-playwright'):
            for folder in ('.agents/skills', '.codex/skills'):
                project_path_guard(self.root, self.root / folder / action['name'])
        step=action['id']
        cmd=action.get('command')
        if not cmd or action.get('blocked'):
            return {'status':'manual','at':utc(),'reason':action['reason']}
        if action['kind'] in ('local-npm','local-python'):
            pass
        elif action['kind']=='skill' and not node_bin(self.root,'skills').is_file():
            return {'status':'blocked','at':utc(),'reason':'Project-local skills CLI not installed'}
        elif action['kind']=='skill-playwright' and not node_bin(self.root,'playwright-cli').is_file():
            return {'status':'blocked','at':utc(),'reason':'Project-local Playwright CLI not installed'}
        elif cmd[0].startswith('./') and not (self.root/cmd[0]).exists():
            return {'status':'blocked','at':utc(),'reason':'Project-local tool launcher missing'}
        elif not cmd[0].startswith('./') and not shutil.which(cmd[0]):
            return {'status':'blocked','at':utc(),'reason':f'{cmd[0]} not in PATH'}
        logfile=self.logs_dir/(re.sub('[^a-z0-9_-]','_',step)+'.log')
        self.journal['steps'][step]={'status':'running','at':utc(),'kind':action['kind']}
        self.persist()
        # Avoid capturing raw logs into JSON; local logs may contain sensitive output.
        timeout=600 if action['kind'] in ('skill','skill-playwright','local-npm','local-python') else 90
        try:
            env=os.environ.copy()
            env['CI']='1'
            env['DISABLE_TELEMETRY']='1'
            if action['kind']=='local-npm':
                result=install_node(self.root,action['package'],timeout=timeout)
            elif action['kind']=='local-python':
                result=install_python(self.root,action['package'],timeout=timeout)
            else:
                result=subprocess.run(cmd,cwd=self.root, capture_output=True, text=True,
                                      stdin=subprocess.DEVNULL, timeout=timeout, check=False,env=env)
            output=result.stdout+'\n'+result.stderr
            # Safeguard: never write plaintext auth/token output to persistent logs.
            clean=redact(output)
            # Atomic replacement avoids following an existing symlink or modifying a hardlink.
            handle=tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.logs_dir, delete=False)
            try:
                with handle:
                    os.fchmod(handle.fileno(), 0o600)
                    handle.write(clean[-16000:])
                os.replace(handle.name, logfile)
            finally:
                if os.path.exists(handle.name):
                    os.unlink(handle.name)
            status='passed' if result.returncode==0 else 'failed'
            record={'status':status,'at':utc(),'exit_code':result.returncode,
                    'log':str(logfile.relative_to(self.root))}
        except subprocess.TimeoutExpired:
            record={'status':'failed','at':utc(),'reason':'command timeout'}
        except ValueError:
            record={'status':'failed','at':utc(),'reason':'tool configuration rejected'}
        except OSError as e:
            record={'status':'failed','at':utc(),'reason':type(e).__name__}
        self.journal['steps'][step]=record
        self.persist()
        return record


def configure_git(root: Path, session: Session, name: str | None, email: str | None) -> list[str]:
    lines=[]
    def git(*args): return command(['git',*args],cwd=root)
    if not shutil.which('git'):
        return ['Git not yet installed; cannot initialize.']
    repository=git('rev-parse','--show-toplevel')
    if repository['ok']:
        if Path(repository['output'].splitlines()[0]).resolve()!=root.resolve():
            return ['BLOCKED: directory is inside a parent Git repository. Use a standalone project folder.']
    else:
        r=git('init','-b','main')
        if not r['ok']:
            r=git('init')
        if not r['ok']:
            return ['FAIL: git init: '+r['output'][:160]]
        session.journal['created_git_repo']=True
        session.persist()
        lines.append('Initialized local Git repository')
    if name or email:
        cfg=root/'.git/config'
        b=session.backup('.git/config')
        if name:
            r=git('config','--local','user.name',name)
            if not r['ok']:lines.append('Could not configure Git user.name')
        if email:
            r=git('config','--local','user.email',email)
            if not r['ok']:lines.append('Could not configure Git user.email')
        session.backup_complete(b)
        lines.append('Git identity configured locally; global Git config untouched')
    return lines


def baseline_commit(root: Path) -> dict:
    # Local baseline only in new clean starter repository, never in an existing working repository.
    if not (root/'.git').exists():return {'status':'skipped','reason':'no Git repository'}
    r=command(['git','rev-parse','HEAD'],cwd=root)
    if r['ok']:return {'status':'skipped','reason':'repository already has commits'}
    v=command([sys.executable,str(root/'scripts/validate-starter.py')],cwd=root,timeout=20)
    if not v['ok']:return {'status':'blocked','reason':'starter structural audit failed'}
    name=command(['git','config','user.name'],cwd=root)
    email=command(['git','config','user.email'],cwd=root)
    if not name['ok'] or not name['output'] or not email['ok'] or not email['output']:
        return {'status':'blocked','reason':'Git user.name or user.email missing; configure locally'}
    # Existing git-checkpoint.sh checks for secrets, file sizes and quality gate.
    try:
        budget = timeout_budget('EXELIA_CHECKPOINT_TIMEOUT', 900)
        r=run_group(['bash','scripts/git-checkpoint.sh','--starter',
             'chore: initialize Exelia Ultimate Starter v2','--initial'],cwd=root,timeout=budget)
        return {'status':'passed' if r.returncode==0 else 'failed',
                'reason':'QA-gated local commit created' if r.returncode==0
                 else (r.stdout+'\n'+r.stderr)[-3500:]}
    except subprocess.TimeoutExpired:
        return {'status':'failed','reason':f'Git baseline checkpoint timed out after {budget}s; process group terminated; resume to retry'}
    except ValueError as error:
        return {'status':'failed','reason':str(error)}


def validate_post_install(root: Path, manifest: dict, findings: dict) -> list[dict]:
    checks=[]
    def add(name,status,detail):checks.append({'name':name,'status':status,'detail':detail})
    st=command([sys.executable,str(root/'scripts/validate-starter.py')],cwd=root,timeout=30)
    add('Starter configuration','pass' if st['ok'] else 'fail',st['output'][-280:])
    for required in ('git','python','node','npm','npx','codex'):
        tool=findings['tools'][required]
        add('Tool '+required,'pass' if tool['status']=='ready' else 'fail',tool['detail'])
    add('Docker/OrbStack runtime','pass' if findings['docker_daemon']['status']=='ready' else 'warning',
        findings['docker_daemon']['detail'])
    from exelia.capabilities import resolve
    required={item['name'] for item in resolve(root)['selected']}
    skillmissing=[n for n,v in findings['skills'].items() if n in required and v['status']!='ready']
    add('Skills registry','pass' if not skillmissing else 'warning',
        'All selected core/project skills present' if not skillmissing else 'Selected missing: '+', '.join(skillmissing))
    ponytail=findings['skills'].get('ponytail',{})
    add('Ponytail project skill','pass' if ponytail.get('status')=='ready' else 'warning',
        'Project-local SKILL.md detected; AGENTS.md activates coding guidance; no global Ponytail plugin or trust required.')
    add('OpenAI Docs MCP','warning' if 'openaiDeveloperDocs' in findings['mcp']['configured_names'] else 'fail',
        'Project MCP configured, live connectivity remains unverified')
    add('Context7 MCP','warning', 'Project MCP configured; OAuth/live connection unverified' if 'context7' in findings['mcp']['configured_names'] else 'Missing project MCP configuration')
    add('Agent role files','pass' if len(list((root/'.codex/agents').glob('*.toml')))==12 else 'fail',
        'Expected twelve role files')
    add('Codex live multiagent execution','not_tested','Requires authenticated Codex on target device')
    add('Ponytail plugin hooks','not_applicable','Not part of Exelia local skill mode; no global hook trust required')
    add('Exelia SessionStart hook','pass' if (root/'.codex/hooks.json').is_file() else 'warning',
        'Separate project-state hook; review its script before granting trust')
    return checks
