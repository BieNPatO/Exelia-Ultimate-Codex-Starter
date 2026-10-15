"""One documented CLI surface for project-local automation."""
from __future__ import annotations
import argparse
import sys
from .common import ROOT, dump
from . import capabilities, evaluations, models, quality, visual, worktrees, dispatch


def parser():
    ap = argparse.ArgumentParser(prog='python3 -m exelia', description='Exelia 2.1: local project orchestration. No background jobs or remote pushes.')
    sub = ap.add_subparsers(dest='area', required=True)
    cap = sub.add_parser('capabilities'); cap.add_argument('action', choices=('plan', 'freeze', 'audit'))
    cap.add_argument('--qa', action='store_true');cap.add_argument('--security', action='store_true')
    wt = sub.add_parser('worktrees'); wt.add_argument('action', choices=('schedule','prepare','status','integrate'))
    wt.add_argument('task', nargs='?');wt.add_argument('--limit', type=int, default=3);wt.add_argument('--confirm',action='store_true')
    d = sub.add_parser('dispatch'); d.add_argument('action',choices=('plan','prepare'))
    d.add_argument('--limit',type=int,default=3)
    q = sub.add_parser('quality');q.add_argument('action', choices=('plan','configure'))
    q.add_argument('--overwrite', action='store_true')
    v = sub.add_parser('visual');v.add_argument('action',choices=('plan','setup','run'))
    v.add_argument('--overwrite', action='store_true')
    e = sub.add_parser('eval');e.add_argument('action',choices=('record','summary'))
    e.add_argument('--task');e.add_argument('--agent');e.add_argument('--model');e.add_argument('--outcome', choices=('pass','fail','blocked'))
    e.add_argument('--seconds', type=float);e.add_argument('--tokens', type=int);e.add_argument('--usd', type=float);e.add_argument('--evidence')
    m = sub.add_parser('model');m.add_argument('stage',choices=sorted(models.STAGES))
    m.add_argument('--risk',choices=('low','normal','high'),default='normal')
    return ap


def main(argv=None):
    p = parser(); args = p.parse_args(argv)
    try:
        if args.area == 'capabilities':
            result = capabilities.freeze(ROOT, include_qa=args.qa, include_security=args.security) if args.action == 'freeze' else capabilities.audit(ROOT) if args.action == 'audit' else capabilities.resolve(ROOT, include_qa=args.qa, include_security=args.security)
        elif args.area == 'worktrees':
            if args.action == 'schedule':result=worktrees.schedule(ROOT,args.limit)
            elif args.action == 'status':result=worktrees.inspect(ROOT)
            else:
                if not args.task:p.error('Task ID required for prepare/integrate')
                result=worktrees.create(ROOT,args.task) if args.action == 'prepare' else worktrees.integrate(ROOT,args.task,confirm=args.confirm)
        elif args.area == 'dispatch':
            result=dispatch.dispatch(ROOT,limit=args.limit,prepare=args.action=='prepare')
        elif args.area == 'quality':
            result=quality.configure(ROOT,overwrite=args.overwrite) if args.action=='configure' else quality.commands(ROOT)
        elif args.area == 'visual':
            result=visual.setup(ROOT,overwrite=args.overwrite) if args.action=='setup' else visual.run(ROOT) if args.action=='run' else visual.inspect(ROOT)
        elif args.area == 'eval':
            if args.action=='summary':result=evaluations.summary(ROOT)
            else:
                for key in ('task','agent','model','outcome','evidence'):
                    if getattr(args,key) is None:p.error('--'+key+' required for eval record')
                result=evaluations.record(ROOT,task=args.task,agent=args.agent,model=args.model,outcome=args.outcome,
                                          duration=args.seconds,tokens=args.tokens,cost=args.usd,evidence=args.evidence)
        else:result=models.recommend(ROOT,args.stage,args.risk)
        dump(result)
        return 0
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        print('EXELIA ERROR:',str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':sys.exit(main())
