"""Exelia Ultimate terminal experience.

Rich and its pure-Python dependencies ship WITH this repository under
installer/_vendor. Rendering starts before any dependency installation.
Plain/JSON/noninteractive modes remain available without global packages.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sys

STATES = {
    'ready': ('●', 'green', '32', 'READY'),
    'pass': ('●', 'green', '32', 'PASS'),
    'passed': ('●', 'green', '32', 'PASSED'),
    'configured': ('◆', 'cyan', '36', 'CONFIGURED'),
    'missing': ('○', 'yellow', '33', 'MISSING'),
    'warning': ('!', 'yellow', '33', 'WARNING'),
    'manual': ('!', 'yellow', '33', 'ACTION'),
    'blocked': ('×', 'red', '31', 'BLOCKED'),
    'incompatible': ('×', 'red', '31', 'INCOMPATIBLE'),
    'broken': ('×', 'red', '31', 'BROKEN'),
    'failed': ('×', 'red', '31', 'FAILED'),
    'fail': ('×', 'red', '31', 'FAIL'),
    'skipped': ('−', 'dim', '2', 'SKIPPED'),
    'unknown': ('?', 'dim', '2', 'UNKNOWN'),
    'not-running': ('!', 'yellow', '33', 'STOPPED'),
    'not_tested': ('?', 'dim', '2', 'NOT TESTED'),
    'not_applicable': ('−', 'dim', '2', 'N/A'),
}

THEME = {
    'accent': 'bright_cyan',
    'title': 'bold bright_white',
    'good': 'green',
    'muted': 'grey62',
    'edge': 'steel_blue',
    'warning': 'yellow',
}


class UI:
    def __init__(self, root: Path, version: str, *, json_mode=False, quiet=False, color=True):
        self.root = root
        self.version = version
        self.json = json_mode
        self.quiet = quiet
        self.verbose = False
        self.color = bool(color and sys.stdout.isatty() and 'NO_COLOR' not in os.environ)
        self.width = max(48, min(112, shutil.get_terminal_size((100, 24)).columns - 2))
        self.rich_console = None
        self._rows = []
        self._progress = None
        self._progress_id = None
        self._current_group = ''
        self._steps_done = 0
        self.enable_rich()

    def enable_rich(self):
        """Load bundled Rich ONLY; never fall back to a global installation."""
        if self.json or self.quiet or self.rich_console is not None:
            return
        vendor = self.root / 'installer' / '_vendor'
        if not (vendor / 'rich' / '__init__.py').is_file():
            return
        try:
            if str(vendor) not in sys.path:
                sys.path.insert(0, str(vendor))
            import rich
            if not Path(rich.__file__).resolve().is_relative_to(vendor.resolve()):
                return
            from rich.console import Console
            self.rich_console = Console(force_terminal=self.color, no_color=not self.color,
                                        width=self.width, highlight=False, soft_wrap=False)
        except (ImportError, OSError, ValueError):
            self.rich_console = None

    @property
    def renderer(self):
        return 'Rich · bundled / project-local' if self.rich_console else 'Plain · fallback'

    def paint(self, content, color='2'):
        return f'\033[{color}m{content}\033[0m' if self.color else str(content)

    def _direct(self, content=''):
        if self.json or self.quiet:
            return
        if self.rich_console:
            self.rich_console.print(str(content), markup=False, highlight=False)
        else:
            print(content, flush=True)

    def say(self, content='', *, important=False):
        self.flush()
        if important and self.quiet:
            print(content, file=sys.stderr, flush=True)
        else:
            self._direct(content)

    def header(self, title):
        self.flush()
        if self.json or self.quiet:
            return
        if self.rich_console:
            from rich import box
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
            grid = Table.grid(expand=True, padding=(0, 1))
            grid.add_column(ratio=3)
            grid.add_column(justify='right', ratio=1)
            grid.add_row(Text('◆  EXELIA  /  ULTIMATE', style='bold bright_cyan'),
                         Text('v' + self.version, style='bold white'))
            grid.add_row(Text(title, style='bold white'), Text('PROJECT SCOPE', style='cyan'))
            grid.add_row(Text('Autonomous development workspace', style='grey62'),
                         Text('NO GLOBAL INSTALLS', style='grey62'))
            self.rich_console.print(Panel(grid, border_style=THEME['edge'], box=box.ROUNDED,
                                          padding=(1, 2)))
            self.rich_console.print('')
        else:
            self._direct('\n' + self.paint('◆  EXELIA ULTIMATE', '1;96') + '   v' + self.version)
            self._direct(self.paint(title, '1'))
            self._direct('Project-local setup; no global installs')
            self._direct('─'*self.width)

    def section(self, title):
        self.flush()
        if self.json or self.quiet:
            return
        if self.rich_console:
            from rich.rule import Rule
            self.rich_console.print(Rule(' ' + str(title).upper() + ' ', style='steel_blue', align='left'))
        else:
            self._direct('\n' + self.paint('▸  ' + str(title).upper(), '1;94'))

    def status(self, label, state, detail=''):
        if self.json or self.quiet:
            return
        sym, color, ansi, word = STATES.get(state, ('•', 'dim', '2', str(state).upper()))
        self._rows.append((str(label), str(detail).replace('\n', ' ').strip(), sym, color, ansi, word))

    def flush(self):
        if not self._rows:
            return
        rows, self._rows = self._rows, []
        if self.json or self.quiet:
            return
        if self.rich_console:
            from rich import box
            from rich.table import Table
            from rich.text import Text
            table = Table(box=box.SIMPLE, show_header=False, show_edge=False,
                          expand=True, padding=(0, 1), pad_edge=False)
            table.add_column(width=2, no_wrap=True)
            table.add_column(min_width=14, ratio=5, overflow='ellipsis', no_wrap=True)
            table.add_column(width=12, no_wrap=True)
            table.add_column(min_width=12, ratio=7, style='grey62', overflow='ellipsis', no_wrap=True)
            for label, detail, sym, color, ansi, word in rows:
                table.add_row(Text(sym, style=color), Text(label, style='white'),
                              Text(word, style=color), Text(detail, style='grey62'))
            self.rich_console.print(table)
        else:
            for label, detail, sym, color, ansi, word in rows:
                self._direct(f' {self.paint(sym,ansi)} {label[:25]:<26}{self.paint(word,ansi):<13} {detail[:50]}')

    def dashboard(self, findings: dict, manifest: dict, *, mode='check'):
        """Small factual overview, not a repeating list of all 25 components."""
        self.flush()
        if self.json or self.quiet:
            return
        plat = findings['platform']
        tools = findings['tools']
        skills = findings['skills']
        from exelia.capabilities import resolve
        required = {item['name'] for item in resolve(self.root)['selected']}
        use_python = bool((__import__('json').loads((self.root/'project.config.json').read_text()) if (self.root/'project.config.json').exists() else {}).get('stack',{}).get('backend'))
        local_tools = [t for t in manifest['tools'] if t.get('install','').startswith('local-')
                       and (t['id'] not in ('uv','ruff') or use_python)
                       and (t['id'] != 'playwright-cli' or 'playwright-cli' in required)
                       and (t['id'] != 'impeccable-cli' or 'impeccable' in required)]
        ready_tools = sum(tools[t['id']]['status'] == 'ready' for t in local_tools)
        ready_skills = sum(s['status'] == 'ready' for name, s in skills.items() if name in required)
        missing_skills = [name for name, s in skills.items() if name in required and s['status'] != 'ready']
        own_git = findings['git'].get('own_repo',False)
        host_core = ('git','python','node','npm','npx','codex')
        host_ready = sum(tools[t]['status'] == 'ready' for t in host_core)
        lines = [
            ('HOST', f'{host_ready}/{len(host_core)} ready', f"{plat['os']} · {plat['architecture']}"),
            ('LOCAL TOOLS',f'{ready_tools}/{len(local_tools)} ready', f'{len(local_tools)-ready_tools} to prepare'),
            ('PROJECT SKILLS',f'{ready_skills}/{len(required)} selected ready',f'{len(missing_skills)} remaining'),
            ('CODEX MCP', f"{len(findings['mcp']['configured_names'])} configured",'live access: verify in Codex'),
            ('GIT', 'READY' if own_git else 'NEW REPOSITORY', 'local only, no push'),
        ]
        self.section('Environment overview')
        if self.rich_console:
            from rich import box
            from rich.table import Table
            from rich.text import Text
            t = Table(box=box.ROUNDED, border_style='steel_blue', expand=True,
                      show_header=True, header_style='bold grey70', padding=(0, 2))
            t.add_column('COMPONENT', min_width=14, ratio=3)
            t.add_column('STATE', min_width=13, ratio=3)
            t.add_column('DETAIL', min_width=12, ratio=5, style='grey62')
            for name, value, desc in lines:
                style = 'green' if (name=='HOST' and host_ready==len(host_core)) or (name=='PROJECT SKILLS' and not missing_skills) or (name=='LOCAL TOOLS' and ready_tools == len(local_tools)) or (name=='GIT' and own_git) else 'yellow' if name in ('PROJECT SKILLS','LOCAL TOOLS','GIT') else 'cyan'
                t.add_row(name, Text(value, style=style), desc)
            self.rich_console.print(t)
            self.rich_console.print('')
        else:
            for name, value, desc in lines:
                self._direct(f'  {name:<17} {value:<18} {desc}')
        if self.verbose:
            self.section('Host details')
            self.status('Operating system','ready' if plat['supported'] else 'blocked', f"{plat['os']} {plat['architecture']}")
            self.status('Package manager','ready' if plat['package_manager'] else 'missing',plat['package_manager'] or 'absent')
            self.status('Memory','ready' if plat['ram_gb'] is not None else 'unknown',f"{plat['ram_gb']} GiB")
            self.status('Disk space','ready' if (plat['disk_free_gb'] or 0)>10 else 'warning',f"{plat['disk_free_gb']} GiB")
            self.flush()
            self.section('Runtime details')
            for item in manifest['tools']:
                t=tools[item['id']]
                self.status(item['id'],t['status'],t['version'] or t['detail'])
            self.flush()
            self.section('Skill inventory')
            for item in manifest['skills']:
                s=skills[item['name']]
                self.status(item['name'],s['status'],s['detail'])
            self.flush()

    def plan(self, actions: list[dict]):
        self.section('Installation plan')
        if not actions:
            self.note('No changes required. Project tools and skills are already present.',kind='success')
            return
        groups = [
            ('PYTHON & NODE TOOLS', [a for a in actions if a['kind'] in ('local-npm','local-python')]),
            ('PROJECT SKILLS', [a for a in actions if a['kind'] not in ('local-npm','local-python') and not a.get('blocked')]),
            ('MANUAL ACTIONS', [a for a in actions if a.get('blocked')]),
        ]
        if self.rich_console:
            from rich import box
            from rich.table import Table
            from rich.text import Text
            table=Table(box=box.SIMPLE_HEAVY, expand=True, show_header=True,header_style='bold grey70',padding=(0,1))
            table.add_column('CATEGORY',ratio=5)
            table.add_column('STEPS',ratio=2,justify='right')
            table.add_column('SCOPE',ratio=5)
            for name, elements in groups:
                if elements:
                    table.add_row(name,Text(str(len(elements)),style='cyan'),
                                  'Local repository' if name != 'MANUAL ACTIONS' else 'Your confirmation')
            self.rich_console.print(table)
            self.rich_console.print('')
        else:
            for name, elements in groups:
                if elements:
                    self._direct(f'  {name}: {len(elements)}')
        for name, elements in groups:
            if name == 'MANUAL ACTIONS':
                for a in elements:
                    self.note(f"{a['name']}: {a['reason']}", kind='warning')
        if self.verbose:
            self.section('Full plan · verbose')
            for a in actions:
                self.status(a['name'],'manual' if a.get('blocked') else 'missing',a['reason'])
                self.flush()
                if a.get('command'):
                    self.say('  $ '+' '.join(a['command']))
        self.note('No global installs. Review third-party sources before approving external downloads.',kind='info')

    @contextmanager
    def batch(self, name, total):
        self.flush()
        self._current_group=name
        self._steps_done=0
        if total<=0:
            yield
            return
        self.section(name)
        if self.rich_console and self.color and not self.json and not self.quiet:
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
            progress=Progress(
                SpinnerColumn('dots', style='bright_cyan'),
                TextColumn('[bold cyan]{task.description}[/]', justify='left'),
                BarColumn(bar_width=None, complete_style='cyan', finished_style='green'),
                TaskProgressColumn(),
                console=self.rich_console, transient=False, expand=True, refresh_per_second=8,
            )
            self._progress=progress
            progress.start()
            self._progress_id=progress.add_task(name, total=total)
            try:
                yield
            finally:
                progress.stop()
                self._progress=None
                self._progress_id=None
                self.rich_console.print('')
        else:
            yield

    @contextmanager
    def step(self, label: str, index: int, total: int):
        self.flush()
        if self._progress is not None:
            self._progress.update(self._progress_id, description=f'{self._current_group}  ·  {label}')
            try:
                yield
            finally:
                self._progress.advance(self._progress_id, 1)
        else:
            self._direct('  ' + self.paint('▸', '36') + f'  [{index}/{total}] {label}')
            yield

    def note(self, message, *, kind='info'):
        self.flush()
        if self.json or self.quiet:
            return
        styles={'info':'cyan', 'warning':'yellow', 'danger':'red', 'success':'green'}
        if self.rich_console:
            from rich import box
            from rich.panel import Panel
            from rich.text import Text
            self.rich_console.print(Panel(Text(str(message),style='white'),
                                          title=Text(kind.upper(),style=styles.get(kind,'cyan')),
                                          border_style=styles.get(kind,'cyan'),box=box.ROUNDED,
                                          padding=(0,2)))
        else:
            self._direct('  '+self.paint(kind.upper()+': '+str(message),'36' if kind=='info' else '33'))

    def summary(self, report, *, core_ok=True):
        self.flush()
        if self.json or self.quiet:
            return
        missing=report.get('missing_skills',[])
        git=report.get('git_checkpoint',{})
        outcome=report.get('outcome','unknown')
        selected=report.get('selected_skills', list(report.get('skills',{})))
        total=len(selected)
        ok_count=sum(report.get('skills',{}).get(name)=='ready' for name in selected)
        complete=(outcome=='completed_with_manual_checks')
        label='COMPLETE' if complete else outcome.upper()
        color='green' if complete else 'yellow' if outcome=='partial' else 'red'
        actions=[]
        if 'impeccable' in missing:
            actions.append('Install Impeccable: ./scripts/local-tool.sh impeccable install  (Codex / Project)')
        extra=[x for x in missing if x!='impeccable']
        if extra:
            actions.append('Retry skills: '+', '.join(extra)+'  →  ./install.sh --resume')
        if git.get('status') in ('blocked','failed'):
            actions.append('Git checkpoint: '+str(git.get('reason','see report'))[:140])
        if not core_ok:
            actions.append('Fix host prerequisites listed in ./install.sh --check')
        if not actions:
            actions.append('Open Codex and paste START_NEW_PROJECT.md')
        actions.append('Check MCP live connections and subagents in Codex')
        actions.append('Verify: ./install.sh --verify')
        self.section('Installation result')
        if self.rich_console:
            from rich import box
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
            t=Table.grid(expand=True,padding=(0,1))
            t.add_column(ratio=6)
            t.add_column(ratio=4)
            t.add_row('PROJECT SKILLS', Text(f'{ok_count} / {total} ready',style='green' if not missing else 'yellow'))
            t.add_row('LOCAL GIT',Text(str(git.get('status','unknown')).upper(),style='green' if git.get('status') in ('passed','skipped') else 'yellow'))
            t.add_row('GLOBAL CHANGES',Text('NONE',style='green'))
            t.add_row('MCP',Text('Live verification in Codex',style='cyan'))
            self.rich_console.print(Panel(t,title=f'[bold {color}]◆ INSTALLATION {label}[/]',
                                          border_style=color,box=box.ROUNDED,padding=(1,2)))
            self.rich_console.print('')
            self.rich_console.print(' [bold bright_cyan]NEXT STEPS[/]')
            for i,action in enumerate(actions,1):
                self.rich_console.print(f' [cyan]{i:02d}[/]  {action}',soft_wrap=True)
            self.rich_console.print(' [dim]Report: .exelia-install/report.json · Nothing pushed or deployed[/]\n')
        else:
            self._direct(self.paint(f'◆ INSTALLATION {label}','1;33'))
            self._direct(f'  Local skills: {ok_count}/{total}  |  Git: {git.get("status","unknown")}  |  Global installs: NONE')
            for i,action in enumerate(actions,1):
                self._direct(f'  {i}. {action}')
            self._direct('  Report: .exelia-install/report.json · No push/deploy')

    def demo(self):
        """Read-only UI demonstration: representative EXAMPLE data, never real discovery."""
        self.header('Interface preview  /  no changes')
        self.note('DEMO DATA — this screen does not inspect or modify the system.',kind='info')
        fake={
          'platform':{'os':'macOS','architecture':'arm64','package_manager':'brew','ram_gb':18,'disk_free_gb':280,'supported':True},
          'tools':{},'skills':{},
          'mcp':{'configured_names':['context7','openaiDeveloperDocs']},
          'git':{'own_repo':False},
        }
        fake_manifest={'tools':[], 'skills':[]}
        for name in ('git','python','node','npm','npx','codex'):
            fake['tools'][name]={'status':'ready'}
            fake_manifest['tools'].append({'id':name,'install':'host-manual'})
        for name in ('uv','ruff','playwright-cli'):
            fake['tools'][name]={'status':'ready' if name!='ruff' else 'missing'}
            fake_manifest['tools'].append({'id':name,'install':'local-python'})
        for name in ('frontend-design','shadcn','ponytail','impeccable'):
            fake['skills'][name]={'status':'missing' if name=='impeccable' else 'ready'}
            fake_manifest['skills'].append({'name':name})
        self.dashboard(fake,fake_manifest,mode='plan')
        fake_actions=[{'kind':'local-python','name':'ruff','reason':'Project-local package','blocked':False},
                      {'kind':'skill','name':'shadcn','reason':'Project-local skill','blocked':False},
                      {'kind':'skill','name':'impeccable','reason':'Select Codex + Project','blocked':True}]
        self.plan(fake_actions)
        self.section('Quality gates · example')
        self.status('Structure & documentation','pass','12 roles verified')
        self.status('Ponytail · project skill','pass','No global hooks required')
        self.status('Git checkpoint','passed','Local commit created')
        self.status('MCP connection','not_tested','Test inside Codex')
        self.flush()
        self.summary({'outcome':'partial','skills':fake['skills'],'missing_skills':['impeccable'],
                      'git_checkpoint':{'status':'passed'}},core_ok=True)
