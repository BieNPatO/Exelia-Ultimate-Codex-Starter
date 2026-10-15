#!/usr/bin/env python3
"""Coordinator-owned durable task ledger with verified completion."""
import argparse
import datetime
import json
import os
import subprocess
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'tasks/backlog.json'

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(value):
    fd,tmp=tempfile.mkstemp(prefix='.backlog-',suffix='.json',dir=str(PATH.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
        os.replace(tmp,PATH)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def main():
    p=argparse.ArgumentParser(description='Project task ledger (one coordinator writes at a time).')
    s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('add');a.add_argument('id');a.add_argument('--title',required=True);a.add_argument('--owner',required=True);a.add_argument('--scope',required=True);a.add_argument('--acceptance',required=True);a.add_argument('--deps',default='')
    for op in ('start','review','complete','block'):
        b=s.add_parser(op);b.add_argument('id')
        if op in ('complete','block'): b.add_argument('--evidence',required=True)
    s.add_parser('list')
    args=p.parse_args()
    data=json.loads(PATH.read_text());tasks=data['tasks'];lookup={t['id']:t for t in tasks}
    if args.cmd=='list':
        print(json.dumps(tasks,indent=2,ensure_ascii=False));return
    if args.cmd=='add':
        if args.id in lookup:p.error('Task ID already exists')
        deps=[d.strip() for d in args.deps.split(',') if d.strip()]
        if args.id in deps or any(d not in lookup for d in deps):p.error('Dependencies must exist and must not include self')
        tasks.append({'id':args.id,'title':args.title,'owner':args.owner,'scope':args.scope,'acceptance':args.acceptance,'dependencies':deps,'status':'todo','evidence':[],'updated_at':now()})
    else:
        if args.id not in lookup:p.error('Unknown task ID')
        t=lookup[args.id]
        wanted={'start':('todo','in_progress'),'review':('in_progress','ready_for_review'),'complete':('ready_for_review','done'),'block':(None,'blocked')}
        previous,next_status=wanted[args.cmd]
        if previous is not None and t['status']!=previous:p.error(f'Expected {previous} but found {t["status"]}')
        if args.cmd=='start':
            for d in t.get('dependencies',[]):
                if lookup[d]['status']!='done':p.error(f'Dependency {d} not done')
        if args.cmd=='complete':
            if not args.evidence.strip():p.error('Real evidence is required')
            r=subprocess.run([str(ROOT/'scripts/quality-gate.sh'),'--app'],cwd=ROOT)
            if r.returncode!=0:p.error('Actual application QA gate failed; cannot complete task')
            t['evidence'].append({'checked_at':now(),'text':args.evidence.strip(),'gate':'PASS'})
        if args.cmd=='block':
            t['evidence'].append({'checked_at':now(),'text':args.evidence.strip(),'gate':'BLOCKED'})
        t['status']=next_status;t['updated_at']=now()
    save(data)
    print('Task ledger updated; Git checkpoint after independent review is still required.')

if __name__=='__main__':main()
