"""Human-friendly and machine-readable Exelia Ultimate Full Installer CLI."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .ui import UI
from . import __version__
from .engine import Session, atomic_json, baseline_commit, configure_git, plan_actions, read_json, utc, validate_post_install
from .probe import inspect, command

ROOT=Path(__file__).resolve().parent.parent
MANIFEST=ROOT/'manifests/components.json'

def args_parse(argv=None):
    ap=argparse.ArgumentParser(description='Exelia Ultimate Installer 2.0 — safe, repeatable, project-local setup.')
    group=ap.add_mutually_exclusive_group()
    group.add_argument('--check',action='store_true',help='Read-only discovery of current environment')
    group.add_argument('--plan',action='store_true',help='Read-only plan (default when no action is set)')
    group.add_argument('--apply',action='store_true',help='Install missing components after reviewing the plan')
    group.add_argument('--resume',action='store_true',help='Recheck interrupted setup and execute missing steps')
    group.add_argument('--repair',action='store_true',help='Recheck and attempt only missing/broken components')
    group.add_argument('--verify',action='store_true',help='Read-only post-install verification')
    group.add_argument('--rollback',action='store_true',help='Restore installer-touched local config, preserving user changes')
    group.add_argument('--report',action='store_true',help='Print last installation report and state')
    group.add_argument('--ui-demo',action='store_true',help='Preview the REAL bundled Rich UI without any changes')
    ap.add_argument('--yes',action='store_true',help='Apply approved plan without additional prompt (not an unsafe sandbox override)')
    ap.add_argument('--allow-system-changes',action='store_true',help='DEPRECATED: global host installation is disabled; this flag is rejected')
    ap.add_argument('--include-optional',action='store_true',help='Also plan optional CLI tools')
    ap.add_argument('--git-name',type=str,help='Local Git author name (not saved in report)')
    ap.add_argument('--git-email',type=str,help='Local Git author email (not saved in report)')
    ap.add_argument('--json',action='store_true',help='Machine-readable stdout JSON only')
    ap.add_argument('--quiet',action='store_true')
    ap.add_argument('--verbose',action='store_true')
    return ap.parse_args(argv)


def safe_view(findings: dict) -> dict:
    """Strip private absolute paths from machine-readable reports."""
    out=json.loads(json.dumps(findings))
    for t in out['tools'].values():t.pop('path',None)
    for s in out['skills'].values():
        s['locations']=['project' if '/.agents/skills/' in x and x.startswith(str(ROOT)) else
                        'existing-user-or-project' for x in s.get('locations',[])]
    out['git'].pop('repo_root',None)
    out['platform'].pop('shell',None)
    return out


def emit(ui: UI, payload: dict):
    if ui.json:print(json.dumps(payload,indent=2,ensure_ascii=False))


def main(argv=None):
    args=args_parse(argv)
    ui=UI(ROOT,__version__,json_mode=args.json,quiet=args.quiet)
    ui.verbose=args.verbose
    if args.ui_demo:
        ui.demo()
        return 0
    if args.allow_system_changes:
        print('ERROR: Exelia 2.1.1 is project-local only. --allow-system-changes is disabled. Install host prerequisites yourself.',file=sys.stderr)
        return 2
    manifest=read_json(MANIFEST)
    if not manifest:
        print('ERROR: missing manifests/components.json',file=sys.stderr);return 2
    session=Session(ROOT)
    if args.report:
        report=read_json(session.state_dir/'report.json')
        payload={'mode':'report','report':report,'journal':session.journal}
        if args.json:emit(ui,payload)
        else:
            ui.header('Previous installation summary')
            ui.say(json.dumps({'report':report,'steps':session.journal.get('steps',{})},indent=2,ensure_ascii=False))
        return 0
    if args.rollback:
        try:
            with session.locked():
                notes=session.restore()
        except RuntimeError as e:
            print('ERROR: '+str(e),file=sys.stderr);return 3
        payload={'mode':'rollback','notes':notes,'warning':'User/global installs and Git history were not reverted'}
        if args.json:emit(ui,payload)
        else:
            ui.header('Safe local configuration rollback')
            for note in notes:ui.say('  '+note)
            ui.say('  Global installs, Git history and service state remain intact; see docs/installer/ROLLBACK.md')
        return 0
    findings=inspect(ROOT,manifest)
    action='apply' if args.apply or args.resume or args.repair or (not any((args.check,args.plan,args.verify,args.rollback,args.report)) and sys.stdin.isatty() and not args.json) else 'verify' if args.verify else 'check' if args.check else 'plan'
    if action!='apply':
        actions=plan_actions(ROOT,manifest,findings,optional=args.include_optional,system_changes=args.allow_system_changes)
        checks=validate_post_install(ROOT,manifest,findings) if action=='verify' else []
        payload={'mode':action,'version':__version__,'discovery':safe_view(findings),
                 'plan':actions if action=='plan' else [],'checks':checks}
        if args.json:emit(ui,payload)
        else:
            ui.header('Environment diagnostics' if action=='check' else 'Installation plan' if action=='plan' else 'Verification')
            ui.dashboard(findings,manifest,mode=action)
            if action=='plan':ui.plan(actions)
            if checks:
                ui.section('QUALITY CHECKS')
                for check in checks:ui.status(check['name'],check['status'],check['detail'])
                from exelia.capabilities import resolve
                required={v['name'] for v in resolve(ROOT)['selected']}
                missing=[s['name'] for s in manifest['skills'] if s['name'] in required and findings['skills'][s['name']]['status']!='ready']
                if missing: ui.note('Missing project skills: '+', '.join(missing)+'. To continue: ./install.sh --resume',kind='warning')
        ui.flush()
        from exelia.capabilities import resolve
        if action=='verify' and (any(c['status']=='fail' for c in checks) or
                                 any(v['name'] in {x['name'] for x in resolve(ROOT)['selected']} and findings['skills'][v['name']]['status']!='ready' for v in manifest['skills'])):
            return 1
        return 0
    ui.header('Environment preparation — review / apply')
    if not findings['platform']['supported']:
        ui.say('Unsupported native platform. Windows should use WSL2; see docs/installer/PLATFORMS.md.',important=True)
        return 2
    if findings['git'].get('inside_repo') and not findings['git'].get('own_repo'):
        ui.say('STOP: folder belongs to a parent Git repository. Use an independent project directory.',important=True)
        return 2
    actions=plan_actions(ROOT,manifest,findings,optional=args.include_optional,system_changes=args.allow_system_changes)
    ui.dashboard(findings,manifest,mode='apply')
    ui.plan(actions)
    if not args.yes:
        if not sys.stdin.isatty():
            ui.say('No terminal for confirmation. Re-run with --apply --yes after reviewing --plan.',important=True)
            return 2
        answer=input('\nApply this plan and initialize local Git? [y/N] ').strip().lower()
        if answer not in ('y','yes'):
            ui.say('Cancelled. Nothing changed.')
            return 0
    if args.git_name or args.git_email:
        if not(args.git_name and args.git_email):
            ui.say('Both --git-name and --git-email are required for local Git override.',important=True)
            return 2
    try:
        with session.locked():
            session.journal['attempts'].append({'at':utc(),'mode':'resume' if args.resume else 'repair' if args.repair else 'apply'})
            session.persist()
            failure=False
            # Tools must be installed before skills, plugins and MCP so dependencies
            # can be re-discovered in the same run (first-time Codex installation).
            ordered=[a for a in actions if a['kind'] in ('local-npm','local-python')]
            def perform(candidate, ordinal, total):
                nonlocal failure
                if candidate.get('blocked'):
                    if ui.verbose:ui.status(candidate['name'],'manual',candidate['reason'])
                    return
                with ui.step(candidate['name'], ordinal, total):
                    outcome=session.run_step(candidate)
                status=outcome['status']
                if status=='passed' and candidate['kind'] in ('local-npm','local-python'):
                    from .probe import tool_info
                    tool=next(t for t in manifest['tools'] if t['id']==candidate['name'])
                    if tool_info(tool,ROOT)['status']!='ready':
                        status='failed';outcome['status']='failed'
                        outcome['reason']='Installer returned success but project-local executable is absent or incompatible'
                        session.journal['steps'][candidate['id']]=outcome;session.persist()
                if status=='passed' and candidate['kind'] in ('skill','skill-playwright'):
                    from .probe import scan_skill
                    if scan_skill(candidate['name'],ROOT,Path.home())['status']!='ready':
                        status='failed'
                        outcome['status']='failed'
                        outcome['reason']='Command succeeded but SKILL.md not found'
                        session.journal['steps'][candidate['id']]=outcome
                        session.persist()
                if ui.verbose or status != 'passed':
                    ui.status(candidate['name'],'ready' if status=='passed' else 'failed',outcome.get('reason',''))
                if status=='failed' and candidate.get('id') in session.journal['steps']:
                    logpath=session.journal['steps'][candidate['id']].get('log')
                    if logpath and ui.verbose:
                        path=ROOT/logpath
                        if path.exists():ui.say('  Log tail: '+path.read_text(errors='replace')[-850:])
                if status!='passed':failure=True
            attempted=set()
            with ui.batch('Local tools',len(ordered)):
                for i,a in enumerate(ordered,1):
                    if not a.get('blocked'):attempted.add(a['id'])
                    perform(a,i,len(ordered))
            # Re-scan when a package manager has just made npm/codex available.
            # A missing npm at discovery time must not permanently block Codex.
            newstate=inspect(ROOT,manifest)
            second=plan_actions(ROOT,manifest,newstate,
                        optional=args.include_optional,system_changes=args.allow_system_changes)
            second_tools=[a for a in second if a['kind'] in ('local-npm','local-python')
                          and a['id'] not in attempted and not a.get('blocked')]
            with ui.batch('Additional local tools',len(second_tools)):
                for i,a in enumerate(second_tools,1):
                    attempted.add(a['id'])
                    perform(a,i,len(second_tools))
            ui.enable_rich()
            ui.section('GIT · REPOSITORY ONLY')
            current_git=inspect(ROOT,manifest)['git']
            if (not current_git['identity'] and not args.git_name and not args.git_email
                    and sys.stdin.isatty() and not args.yes):
                ui.say('  No Git author identity detected. Configure it for this project only:')
                args.git_name=input('  Git author name: ').strip() or None
                args.git_email=input('  Git author email: ').strip() or None
                if not(args.git_name and args.git_email):
                    args.git_name=None;args.git_email=None
                    ui.say('  Skipped Git identity; baseline commit will remain blocked.')
            messages=configure_git(ROOT,session,args.git_name,args.git_email)
            for m in messages:ui.say('  '+m)
            if any(m.startswith('BLOCKED:') for m in messages):return 2
            refreshed=inspect(ROOT,manifest)
            remaining=plan_actions(ROOT,manifest,refreshed,
                    optional=args.include_optional,system_changes=args.allow_system_changes)
            other=[a for a in remaining if a['kind'] not in ('local-npm','local-python')]
            with ui.batch('Project skills',len(other)):
                for i,a in enumerate(other,1):perform(a,i,len(other))
            ui.section('QUALITY GATES')
            updated=inspect(ROOT,manifest)
            checks=validate_post_install(ROOT,manifest,updated)
            for c in checks:
                if ui.verbose or c['status'] not in ('pass','passed'):
                    ui.status(c['name'],c['status'],c['detail'])
            core_ok=all(updated['tools'][t]['status']=='ready' for t in ('git','python','node','npm','npx','codex'))
            if core_ok:
                baseline=baseline_commit(ROOT)
            else:
                baseline={'status':'blocked','reason':'required tools are missing or incompatible'}
            ui.status('Initial Git checkpoint',baseline['status'],baseline['reason'])
            from exelia.capabilities import resolve
            required={item['name'] for item in resolve(ROOT)['selected']}
            missing_required=[item['name'] for item in manifest['skills']
                              if item['name'] in required and updated['skills'][item['name']]['status']!='ready']
            report={
                'schema_version':1,'version':__version__,'created_at':utc(),
                'platform':updated['platform'],'tool_status':{k:v['status'] for k,v in updated['tools'].items()},
                'skills':{k:v['status'] for k,v in updated['skills'].items()},
                'selected_skills':sorted(required),
                'ponytail_project_skill_present':updated['skills']['ponytail']['status']=='ready',
                'mcp_configured':updated['mcp']['configured_names'],
                'quality_checks':checks,'git_checkpoint':baseline,
                'missing_skills':missing_required,
                'manual_actions':[a['name'] for a in actions if a.get('blocked')],
                'outcome':'partial' if failure or missing_required or not core_ok or baseline['status'] in ('failed','blocked') or any(c['status']=='fail' for c in checks) else 'completed_with_manual_checks',
                'security_note':'Only repository-local packages/skills are installed. Host tools are prerequisites; MCP authentication may require user action.'}
            atomic_json(session.state_dir/'report.json',report)
            session.journal['last_report']=report['outcome']
            session.persist()
            ui.section('RESULT · ACTIONABLE SUMMARY')
            ui.summary(report, core_ok=core_ok)
            ui.flush()
            emit(ui,{'mode':'apply','report':report})
            return 0 if not failure and not missing_required and core_ok and baseline['status'] in ('passed','skipped') else 1
    except RuntimeError as e:
        print('INSTALLATION HALTED: '+str(e),file=sys.stderr)
        return 3

if __name__=='__main__':sys.exit(main())
