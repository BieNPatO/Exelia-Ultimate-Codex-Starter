#!/usr/bin/env python3
"""Manage small durable starter state. Not an access-control boundary for human approval."""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
CONFIG=ROOT/'project.config.json'
STATE=ROOT/'tasks/STATE.json'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def iso(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main(argv=None):
 p=argparse.ArgumentParser()
 sub=p.add_subparsers(dest='action',required=True)
 a=sub.add_parser('language');a.add_argument('code',choices=['pl','en'])
 a=sub.add_parser('ui-language');a.add_argument('locales',help='Comma-separated BCP47 language tags, e.g. en,pl')
 a=sub.add_parser('approve');a.add_argument('--evidence',required=True,help='Exact human approval text from chat; do not fabricate')
 a=sub.add_parser('stage');a.add_argument('name')
 a=sub.add_parser('qa');a.add_argument('status',choices=['PASS','FAIL','BLOCKED','NOT_RUN'])
 sub.add_parser('status')
 args=p.parse_args(argv)
 if args.action=='language':
  config=load(CONFIG); config['conversation_language']=args.code;save(CONFIG,config);print('Conversation language saved.')
 elif args.action=='ui-language':
  import re
  locales=[i.strip() for i in args.locales.split(',') if i.strip()]
  if not locales or any(not re.fullmatch(r'[a-z]{2,3}(?:-[A-Z]{2})?',i) for i in locales):p.error('Invalid locale list')
  config=load(CONFIG);config['application_ui_languages']=locales;save(CONFIG,config);print('App UI locale(s) recorded separately from conversation language.')
 elif args.action=='approve':
  if len(args.evidence.strip())<3: p.error('Real human approval evidence must be recorded')
  validation=subprocess.run([sys.executable,str(ROOT/'scripts/validate-docs.py')],cwd=ROOT)
  if validation.returncode!=0:p.error('Complete and validate documentation before recording approval')
  state=load(STATE)
  if state.get('documentation_approved'): p.error('Documentation already approved; revise scope via an ADR and user change decision')
  state.update(documentation_approved=True,approval_evidence=args.evidence.strip(),approval_at=iso(),phase='implementation',updated_at=iso());save(STATE,state)
  print('Approval evidence recorded. IMPORTANT: script cannot independently authenticate who typed the evidence.')
 elif args.action=='stage':
  state=load(STATE)
  if not state.get('documentation_approved'): p.error('Document approval required before an implementation stage')
  state.update(current_stage=args.name,updated_at=iso(),last_quality_gate='NOT_RUN');save(STATE,state)
  print('Stage updated; present model selection rationale before development.')
 elif args.action=='qa':
  state=load(STATE);state.update(last_quality_gate=args.status,updated_at=iso());save(STATE,state)
  print('Recorded QA result:',args.status)
 else:
  print(json.dumps({'config':load(CONFIG),'state':load(STATE)},indent=2,ensure_ascii=False))
if __name__=='__main__': main()
