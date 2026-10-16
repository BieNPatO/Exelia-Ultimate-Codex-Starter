#!/usr/bin/env python3
"""Offline structural audit for the distributable starter."""
import json
import sys
import tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
REQUIRED=['AGENTS.md','START_HERE.md','START_NEW_PROJECT.md','CONTINUE_PROJECT.md','starter.yaml','project.config.json','tasks/STATE.json','tasks/backlog.json','.codex/config.toml','.codex/hooks.json','scripts/bootstrap.sh','scripts/doctor.sh','scripts/quality-gate.sh','scripts/git-checkpoint.sh','scripts/task-ledger.py','tests/test_starter.py','tests/test_installer.py','tests/integration_smoke.py','install.sh','install.ps1','install.command','installer/__init__.py','installer/__main__.py','installer/cli.py','installer/ui.py','installer/engine.py','installer/probe.py','installer/platforms.py','installer/localtools.py','scripts/local-tool.sh','manifests/components.json','docs/installer/PLATFORMS.md','docs/installer/ROLLBACK.md','docs/installer/SECURITY.md','docs/installer/PONYTAIL.md','docs/installer/TERMINAL_UI.md','docs/installer/TROUBLESHOOTING.md','tests/test_terminal_ui.py','exelia/__init__.py','exelia/__main__.py','exelia/common.py','exelia/capabilities.py','exelia/dispatch.py','exelia/worktrees.py','exelia/quality.py','exelia/visual.py','exelia/evaluations.py','exelia/models.py','LICENSE','SECURITY.md','CONTRIBUTING.md','docs/GITHUB_SETUP.md','docs/automation/README.md','docs/automation/WORKFLOW.md','docs/automation/QUALITY.md','scripts/check-publication.py','tests/test_exelia_automation.py']
ROLES=['coordinator','product-analyst','solution-architect','frontend-engineer','backend-engineer','database-engineer','ui-ux-designer','devops-engineer','qa-engineer','security-auditor','code-reviewer','documentation-agent']
CUSTOM=['premium-motion','python-backend-engineering','project-delivery']
DOCS=['PRODUCT','PRD','ARCHITECTURE','TECH_STACK','DATABASE','API_SPEC','UI_UX','SECURITY','TEST_STRATEGY','DEPLOYMENT','MODEL_POLICY','IMPLEMENTATION_PLAN','BACKLOG','DECISIONS']

def validate():
 problems=[]
 def error(s): problems.append(s)
 for f in REQUIRED:
  if not (ROOT/f).is_file():error('missing '+f)
 try:
  conf=tomllib.loads((ROOT/'.codex/config.toml').read_text())
  if conf.get('sandbox_mode')!='workspace-write':error('unsafe sandbox config')
  if conf.get('sandbox_workspace_write',{}).get('network_access') is not False:error('network must be disabled by default')
  if conf.get('approval_policy')!='on-request':error('unsafe project approval policy')
  if conf.get('agents',{}).get('max_concurrent_threads_per_session',100)>4:error('excessive agent concurrency')
 except Exception as e:error('config TOML invalid '+str(e))
 for package in ('rich','markdown_it','mdurl','pygments'):
  if not (ROOT/'installer/_vendor'/package/'__init__.py').is_file():error('missing bundled UI dependency '+package)
 for file in ('rich-LICENSE.txt','markdown-it-py-LICENSE.txt','mdurl-LICENSE.txt','Pygments-LICENSE.txt'):
  if not (ROOT/'installer/_vendor/licenses'/file).is_file():error('missing vendor license '+file)
 for r in ROLES:
  p=ROOT/f'.codex/agents/{r}.toml'
  if not p.exists():error('missing role '+r);continue
  try:
   data=tomllib.loads(p.read_text())
   if not all(k in data for k in ('name','description','developer_instructions')):error('missing role metadata '+r)
  except Exception as e:error('invalid agent TOML '+r+str(e))
 for s in CUSTOM:
  p=ROOT/f'.agents/skills/{s}/SKILL.md'
  if not p.exists():error('missing custom skill '+s)
  elif not p.read_text().startswith('---\nname: '+s+'\n'):error('invalid skill frontmatter '+s)
 for d in DOCS:
  for prefix in ['templates','project']:
   if not (ROOT/f'docs/{prefix}/{d}.md').is_file():error('missing document '+prefix+'/'+d)
 for f in ['project.config.json','tasks/STATE.json','tasks/backlog.json','.codex/hooks.json','manifests/components.json']:
  try:json.loads((ROOT/f).read_text())
  except Exception as e:error('invalid JSON '+f+str(e))
 try:
  manifest=json.loads((ROOT/'manifests/components.json').read_text())
  if manifest.get('version')!='2.1.2':error('installer manifest version mismatch')
  if (ROOT/'VERSION').read_text().strip()!='2.1.2':error('VERSION mismatch')
  if len(manifest['skills'])<10:error('too few external skills in manifest')
  names=[x['name'] for x in manifest['skills']]
  if len(names)!=len(set(names)):error('duplicate external skill names')
  if 'ponytail' not in [x['name'] for x in manifest['plugins']]:error('ponytail missing from manifest')
  if 'openaiDeveloperDocs' not in [x['name'] for x in manifest['mcp']]:error('OpenAI Docs MCP missing from manifest')
 except Exception as e:error('invalid installer manifest '+str(e))
 if problems:
  print('FAIL: '+str(len(problems))+' problems')
  for x in problems:print(' - '+x)
  return 1
 print(f'PASS: starter structure, {len(ROLES)} role files, {len(CUSTOM)} original skills, {len(DOCS)} document pairs')
 return 0
if __name__=='__main__':sys.exit(validate())
