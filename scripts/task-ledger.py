#!/usr/bin/env python3
"""Coordinator-owned durable task ledger with verified completion."""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'tasks/backlog.json'

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def review_context(task_id, review=None, *, allow_metadata=False):
    sys.path.insert(0,str(ROOT))
    from exelia.worktrees import validate_review
    from exelia.common import git, load
    registry=load(ROOT/'.exelia/worktrees.json',{'items':{}})['items']
    branch=registry.get(task_id,{}).get('branch')
    head=git('rev-parse',branch or 'HEAD',cwd=ROOT).stdout.strip()
    if branch or review is None:
        return validate_review,head
    if not isinstance(review,dict):
        raise RuntimeError('Review evidence must be a structured attestation.')
    evidence=Path(review.get('evidence',''))
    dedicated = (evidence.parts[:2]==('docs','reviews') and evidence.suffix in ('.md','.txt'))
    root_review = (len(evidence.parts)==1 and evidence.name.lower().startswith('review') and evidence.suffix=='.md')
    if not (dedicated or root_review) or evidence.is_absolute() or '..' in evidence.parts:
        raise RuntimeError('Sequential review evidence must use docs/reviews/*.md or *.txt (or root review*.md).')
    reviewed=review.get('commit','')
    if not allow_metadata or reviewed==head:
        return validate_review,head
    if not isinstance(reviewed,str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})',reviewed) or git('merge-base','--is-ancestor',reviewed,head,cwd=ROOT,check=False).returncode:
        raise RuntimeError('Sequential review commit is missing or is not an ancestor of main.')
    allowed={'tasks/backlog.json',evidence.as_posix()}
    for line in git('rev-list','--parents',f'{reviewed}..{head}',cwd=ROOT).stdout.splitlines():
        commits=line.split()
        if len(commits)!=2:
            raise RuntimeError('Sequential review is stale after a merge; review the current source again.')
        changed=set(git('diff','--no-renames','--name-only','-z',commits[1],commits[0],cwd=ROOT).stdout.split('\0'))-{''}
        if changed-allowed:
            raise RuntimeError('Sequential review is stale: source changed after review; only backlog and review evidence commits are allowed.')
    return validate_review,reviewed
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
    for op in ('start','review','complete','block','resume'):
        b=s.add_parser(op);b.add_argument('id')
        if op in ('complete','block','resume'): b.add_argument('--evidence',required=True)
    b=s.add_parser('attest-review');b.add_argument('id');b.add_argument('--reviewer',required=True);b.add_argument('--commit',required=True);b.add_argument('--result',choices=['PASS','FAIL'],required=True);b.add_argument('--evidence',required=True);b.add_argument('--finding',action='append',default=[])
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
        if args.cmd=='attest-review':
            if t['status']!='ready_for_review':p.error('Expected ready_for_review')
            try:
                candidate={'reviewer':args.reviewer.strip(),'commit':args.commit,'result':args.result,'timestamp':now(),'evidence':args.evidence,'outstanding_findings':args.finding}
                validate_review,head=review_context(args.id,candidate)
                if args.result=='PASS':validate_review(ROOT,{**t,'review':candidate},head)
                else:
                    validate_review(ROOT,{**t,'review':{**candidate,'result':'PASS','outstanding_findings':[]}},head)
            except (RuntimeError,ValueError) as exc:p.error(str(exc))
            t['review']=candidate;t['updated_at']=now()
            t.setdefault('history',[]).append({'at':now(),'action':'attest-review','review':candidate})
            save(data)
            print('Review attestation recorded; identities are procedural assertions, not authenticated proof.')
            return
        wanted={'start':('todo','in_progress'),'review':('in_progress','ready_for_review'),'complete':('ready_for_review','done'),'block':(None,'blocked'),'resume':('blocked','todo')}
        previous,next_status=wanted[args.cmd]
        if previous is not None and t['status']!=previous:p.error(f'Expected {previous} but found {t["status"]}')
        if args.cmd=='start':
            for d in t.get('dependencies',[]):
                if lookup[d]['status']!='done':p.error(f'Dependency {d} not done')
        if args.cmd=='complete':
            if not args.evidence.strip():p.error('Real evidence is required')
            try:
                validate_review,head=review_context(args.id,t.get('review'),allow_metadata=True)
                validate_review(ROOT,t,head)
                from exelia.common import git
                main_head=git('rev-parse','HEAD',cwd=ROOT).stdout.strip()
                if git('merge-base','--is-ancestor',head,main_head,cwd=ROOT,check=False).returncode:
                    p.error('Reviewed task commit must be integrated into main before completion QA')
                if git('status','--porcelain',cwd=ROOT).stdout.strip():
                    p.error('Commit main working tree changes before completion QA')
            except (RuntimeError,ValueError) as exc:p.error(str(exc))
            r=subprocess.run([str(ROOT/'scripts/quality-gate.sh'),'--app'],cwd=ROOT)
            if r.returncode!=0:p.error('Actual application QA gate failed; cannot complete task')
            if git('rev-parse','HEAD',cwd=ROOT).stdout.strip()!=main_head or git('status','--porcelain',cwd=ROOT).stdout.strip():
                p.error('Main changed during completion QA; commit, review and run completion again')
            t['evidence'].append({'checked_at':now(),'text':args.evidence.strip(),'gate':'PASS'})
        if args.cmd in ('block','resume'):
            if not args.evidence.strip():p.error('Real evidence is required')
            t.setdefault('evidence',[]).append({'checked_at':now(),'text':args.evidence.strip(),'gate':'BLOCKED' if args.cmd=='block' else 'RESUMED'})
        t.setdefault('history',[]).append({'at':now(),'action':args.cmd,'from':t['status'],'to':next_status})
        if args.cmd in ('start','resume'):t.pop('review',None)
        t['status']=next_status;t['updated_at']=now()
    save(data)
    print('Task ledger updated; Git checkpoint after independent review is still required.')

if __name__=='__main__':main()
