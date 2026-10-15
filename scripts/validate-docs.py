#!/usr/bin/env python3
"""Readiness gate for a product spec, before recorded user approval."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent.parent
DOCS=['PRODUCT','PRD','ARCHITECTURE','TECH_STACK','DATABASE','API_SPEC','UI_UX','SECURITY','TEST_STRATEGY','DEPLOYMENT','MODEL_POLICY','IMPLEMENTATION_PLAN','BACKLOG','DECISIONS']
def main():
 bad=[]
 for name in DOCS:
  p=ROOT/f'docs/project/{name}.md'
  if not p.exists(): bad.append(f'missing {name}');continue
  text=p.read_text()
  if len(text.strip()) < 150:bad.append(f'{name}: insufficient content')
  if '[TBD]' in text or 'STATUS: TEMPLATE' in text:bad.append(f'{name}: unresolved template placeholders')
 config=json.loads((ROOT/'project.config.json').read_text())
 if config.get('conversation_language') not in ('pl','en'):bad.append('conversation language not selected')
 if not config.get('application_ui_languages'):bad.append('application UI language not decided')
 if bad:
  print('FAIL documentation gate:')
  for i in bad:print(' - '+i)
  return 1
 print('PASS basic documentation completeness (semantic review still required)')
 return 0
if __name__=='__main__':sys.exit(main())
