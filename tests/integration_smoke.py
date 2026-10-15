#!/usr/bin/env python3
"""Offline full installation against fake host tools. Tests real repo-local paths.

Never downloads dependencies, never touches user directories, never invokes
host-level package installation. Verifies the real quality-gated Git baseline.
"""
import json,os,pathlib,shutil,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]

def write_bin(p,body):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'+body+'\n')
    p.chmod(0o755)

def run(cmd,cwd,env,timeout=210):
    return subprocess.run(cmd,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)

def main():
  with tempfile.TemporaryDirectory(prefix='exelia_local_scope_') as td:
    base=pathlib.Path(td);repo=base/'new-project'
    shutil.copytree(ROOT,repo,ignore=shutil.ignore_patterns('__pycache__','.exelia-install','.git','*.pyc','MANIFEST.sha256','.exelia-tools'))
    fake=base/'bin';fake.mkdir();log=base/'executed.txt'
    flag=base/'ponytail-global-command-was-called'
    write_bin(fake/'codex',r'''
case "${1:-}" in
 --version) echo 'codex-cli 0.162.1';;
 plugin) touch "$EXELIA_GLOBAL_PLUGIN_FLAG";exit 4;;
 mcp) echo 'openaiDeveloperDocs configured';;
 *) echo 'Codex';;
esac
''')
    write_bin(fake/'npm',r'''
if [[ "${1:-}" == --version ]];then echo '11.2.0';exit 0;fi
printf 'npm %s\n' "$*" >> "$EXELIA_MOCK_LOG"
[[ "${1:-}" == install ]] || exit 6
prefix='';pkg='';next=0
for x in "$@";do
 if [[ $next == 1 ]];then prefix="$x";next=0;continue;fi
 if [[ "$x" == --prefix ]];then next=1;continue;fi
 if [[ "$x" != -* && "$x" != install && "$x" != "$prefix" ]];then pkg="$x";fi
done
[[ "$prefix" == "$PWD/.exelia-tools/node" ]] || { echo "nonlocal npm prefix: $prefix" >&2;exit 7; }
mkdir -p "$prefix/node_modules/.bin"
case "$pkg" in
 skills) name=skills;;
 @playwright/cli) name=playwright-cli;;
 impeccable) name=impeccable;;
 *) echo "Unknown package $pkg" >&2;exit 8;;
esac
if [[ "$name" == skills ]];then
 cat > "$prefix/node_modules/.bin/skills" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --version ]];then echo 1.1.0;exit 0;fi
name='';next=0
for a in "$@";do
 if [[ $next == 1 ]];then name="$a";next=0;fi
 [[ "$a" == --skill ]] && next=1
done
[[ -n "$name" ]] || exit 5
mkdir -p ".agents/skills/$name"
printf -- '---\nname: %s\ndescription: Test local skill.\n---\n' "$name" > ".agents/skills/$name/SKILL.md"
printf 'skills %s\n' "$*" >> "$EXELIA_MOCK_LOG"
SCRIPT
elif [[ "$name" == playwright-cli ]];then
 cat > "$prefix/node_modules/.bin/playwright-cli" <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == --version ]];then echo 0.1.0;exit 0;fi
printf 'playwright-cli %s\n' "$*" >> "$EXELIA_MOCK_LOG"
mkdir -p .agents/skills/playwright-cli
printf -- '---\nname: playwright-cli\ndescription: Local browser testing.\n---\n' > .agents/skills/playwright-cli/SKILL.md
SCRIPT
else
 cat > "$prefix/node_modules/.bin/impeccable" <<'SCRIPT'
#!/usr/bin/env bash
if [[ "${1:-}" == --version ]];then echo 1.0.0;exit 0;fi
exit 2
SCRIPT
fi
chmod +x "$prefix/node_modules/.bin/$name"
''')
    write_bin(fake/'npx',r'''if [[ "${1:-}" == --version ]];then echo 11.2.0;else echo 'No npx installer allowed' >&2;exit 8;fi''')
    write_bin(fake/'docker',r'''
if [[ "${1:-}" == --version ]];then echo 'Docker version 29.4.0';elif [[ "${1:-}" == info ]];then echo '29.4.0';elif [[ "${1:-}" == context ]];then echo 'orbstack';else exit 2;fi
''')
    # Python tools already locally present in the mock to prevent real pip downloads.
    for tool in ('uv','ruff'):
        write_bin(repo/'.exelia-tools/python/bin'/tool,f"if [[ \"${{1:-}}\" == --version ]];then echo '{tool} 0.9.0';else exit 2;fi")
    # Bundled Rich needs no pip; emulate the existing Python tool environment.
    write_bin(repo/'.exelia-tools/python/bin/python',r"""
if [[ "${1:-}" == '-c' ]];then echo 14.0.0;exit 0;fi
exit 4
""")
    # Impeccable installer is interactive and correctly deferred; simulate an
    # already installed PROJECT skill, not a global one.
    s=repo/'.agents/skills/impeccable/SKILL.md';s.parent.mkdir(parents=True,exist_ok=True)
    s.write_text('---\nname: impeccable\ndescription: UI finishing.\n---\n')
    home=base/'home';home.mkdir()
    env=os.environ.copy();env['PATH']=str(fake)+os.pathsep+env['PATH']
    env['HOME']=str(home)
    env['EXELIA_GLOBAL_PLUGIN_FLAG']=str(flag)
    env['EXELIA_MOCK_LOG']=str(log)
    env['PYTHONDONTWRITEBYTECODE']='1'
    p=run(['bash','install.sh','--plan','--json'],repo,env)
    assert p.returncode==0,p.stderr
    obj=json.loads(p.stdout)
    assert all(x['scope']=='project' for x in obj['plan'] if not x['blocked'])
    assert not (repo/'.git').exists()
    assert not (repo/'.exelia-install').exists()
    p=run(['bash','install.sh','--apply','--yes','--git-name','Exelia Test','--git-email','test@exelia.invalid'],repo,env)
    if p.returncode:
        report_path=repo/'.exelia-install/report.json'
        if report_path.exists():
            report=json.loads(report_path.read_text())
            print('CHECKPOINT_DIAGNOSIS:',report.get('git_checkpoint'))
        d=run(['git','diff','--cached','--check'],repo,env)
        print('STAGED_DIFF_CHECK:',d.returncode,d.stdout[-1700:],d.stderr)
        raise AssertionError(p.stdout[-5000:]+p.stderr)
    assert (repo/'.agents/skills/ponytail/SKILL.md').exists()
    assert not (repo/'.agents/skills/frontend-design/SKILL.md').exists(), 'Web skill should be selected only after discovery'
    assert not (repo/'.agents/skills/playwright-cli/SKILL.md').exists(), 'Browser skill should be opt-in'
    assert (repo/'.exelia-tools/node/node_modules/.bin/skills').exists()
    assert not flag.exists(),'GLOBAL Codex plugin command called'
    assert not any(x.startswith('npm install --global') for x in log.read_text().splitlines())
    assert not (home/'.agents/skills').exists(), 'Created unwanted user-level skills'
    head=run(['git','log','-1','--format=%s'],repo,env)
    assert head.returncode==0 and 'initialize Exelia Ultimate Starter' in head.stdout,head.stderr
    assert run(['git','status','--porcelain'],repo,env).stdout.strip()=='', 'Working tree not clean'
    before=log.read_text()
    second=run(['bash','install.sh','--resume','--yes'],repo,env)
    assert second.returncode==0,(second.stdout[-1800:]+second.stderr)
    assert before==log.read_text(),'Repeat install executed npm/skills again'
    ver=run(['bash','install.sh','--verify','--json'],repo,env)
    assert ver.returncode==0,ver.stderr
    assert json.loads(ver.stdout)['mode']=='verify'
    # Real two-phase selection: adding an approved Next.js/FastAPI stack should
    # install only newly relevant capabilities without host/global mutation.
    project=json.loads((repo/'project.config.json').read_text())
    project['stack']={'frontend':'Next.js','backend':'FastAPI','database':'Postgres'}
    project['capabilities']={'visual_qa':True,'security_review':True}
    (repo/'project.config.json').write_text(json.dumps(project,indent=2)+'\n')
    state=json.loads((repo/'tasks/STATE.json').read_text())
    state['documentation_approved']=True  # offline simulation only
    (repo/'tasks/STATE.json').write_text(json.dumps(state,indent=2)+'\n')
    plan=run(['bash','install.sh','--plan','--json'],repo,env)
    assert plan.returncode==0,plan.stderr
    plan_json=json.loads(plan.stdout)
    ids={x['id'] for x in plan_json['plan']}
    assert 'skill-frontend-design' in ids and 'skill-fastapi' in ids
    assert 'skill-playwright-cli' in ids and 'skill-differential-review' in ids
    assert not any(x['scope']=='host' and not x['blocked'] for x in plan_json['plan'])
    print('PASS: approved stack produces a project-only plan for frontend, FastAPI, browser and security tools')
    print('PASS: project-local tools, all skills including Ponytail, and Git initial commit')
    print('PASS: no global npm/skills/plugins, no host modifications, idempotent resume')
    print('PASS: all downloads mocked; no network or credentials used')

if __name__=='__main__':main()
