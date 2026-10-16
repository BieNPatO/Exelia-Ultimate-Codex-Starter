"""Offline tests: real Git worktrees, approval gates, scope boundaries and evaluation honesty."""
from __future__ import annotations
import json
import pathlib
import subprocess
import tempfile
import unittest
from exelia import capabilities, dispatch, evaluations, models, quality, visual, worktrees
from exelia.common import save

ROOT=pathlib.Path(__file__).resolve().parents[1]


def repository(root, *, status='todo', approved=False, tasks=None):
    (root/'tasks').mkdir(parents=True, exist_ok=True)
    save(root/'tasks/STATE.json',{'documentation_approved':approved})
    save(root/'tasks/backlog.json',{'schema_version':1,'tasks':tasks if tasks is not None else [{
        'id':'TASK-1','title':'Test task','owner':'backend-engineer','scope':'api/src',
        'acceptance':'Run actual QA','dependencies':[], 'status':status,'evidence':[]}]})
    save(root/'project.config.json',{'stack': {'frontend':None, 'backend':None},'conversation_language':'en'})
    (root/'.gitignore').write_text('.exelia/\n')
    (root/'scripts').mkdir(exist_ok=True)
    script=root/'scripts/quality-gate.sh'
    script.write_text('#!/usr/bin/env bash\nset -e\nexit 0\n')
    script.chmod(0o755)
    subprocess.run(['git','init','-q','-b','main'],cwd=root,check=True)
    subprocess.run(['git','config','user.name','Exelia Test'],cwd=root,check=True)
    subprocess.run(['git','config','user.email','test@exelia.invalid'],cwd=root,check=True)
    subprocess.run(['git','add','-A'],cwd=root,check=True)
    subprocess.run(['git','commit','-qm','test: initial'],cwd=root,check=True)


class CapabilityTests(unittest.TestCase):
    def test_core_only_before_discovery(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            save(root/'project.config.json',{'stack':{}})
            value=capabilities.resolve(root)
            self.assertEqual([x['name'] for x in value['selected']],list(capabilities.CORE))
            self.assertNotIn('frontend-design',[x['name'] for x in value['selected']])

    def test_selects_stack_specific_skills(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            save(root/'project.config.json',{'stack': {'frontend': 'Next.js React', 'backend': 'FastAPI'}})
            value=capabilities.resolve(root,include_qa=True,include_security=True)
            names=[x['name'] for x in value['selected']]
            self.assertEqual(len(names),len(set(names)))
            for name in ('ponytail','frontend-design','fastapi','impeccable','playwright-cli','differential-review'):
                self.assertIn(name,names)
            self.assertTrue(value['missing'])
            self.assertFalse(any(x['revision_pinned'] for x in value['selected']))

    def test_freeze_is_local_not_an_upstream_signature(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            for name in capabilities.CORE:
                p=root/'.agents/skills'/name/'SKILL.md';p.parent.mkdir(parents=True)
                p.write_text('test')
            value=capabilities.freeze(root)
            self.assertEqual(len([x for x in value['selected'] if x['sha256']]),3)
            self.assertEqual(capabilities.audit(root)['status'],'PASS')
            (root/'.agents/skills/ponytail/SKILL.md').write_text('tampered')
            self.assertEqual(capabilities.audit(root)['status'],'DRIFT')
            self.assertIn('not supplier provenance',value['warning'])
            self.assertTrue((root/'manifests/skills.lock.json').is_file())


class SchedulerTests(unittest.TestCase):
    def test_scopes_and_dependencies(self):
        tasks=[{'id':'A','status':'todo','scope':'app/src','dependencies':[]},
               {'id':'B','status':'todo','scope':'api/src','dependencies':[]},
               {'id':'C','status':'todo','scope':'app/src/login','dependencies':[]},
               {'id':'D','status':'todo','scope':'api/docs','dependencies':['A']}]
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);save(root/'tasks/backlog.json',{'tasks':tasks})
            schedule=worktrees.schedule(root,limit=3)
            self.assertEqual(schedule['ready'],['A','B'])
            self.assertIn('C',schedule['deferred'])
            self.assertNotIn('D',schedule['ready'])
            self.assertTrue(worktrees.overlaps('api/src','api/src/v1'))
            self.assertFalse(worktrees.overlaps('api/src','app/src'))
            self.assertTrue(worktrees.overlaps('*','app/src'))

    def test_approval_and_dirty_base_blocks_create(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            repository(root,approved=False)
            with self.assertRaises(RuntimeError):worktrees.create(root,'TASK-1')
            state=json.loads((root/'tasks/STATE.json').read_text());state['documentation_approved']=True
            save(root/'tasks/STATE.json',state)
            with self.assertRaises(RuntimeError):worktrees.create(root,'TASK-1')
            subprocess.run(['git','add','-A'],cwd=root,check=True)
            subprocess.run(['git','commit','-qm','test: approval'],cwd=root,check=True)
            result=worktrees.create(root,'TASK-1')
            self.assertTrue((root/result['path']).exists())
            self.assertTrue(result['branch'].startswith('exelia/'))
            self.assertFalse((root/'.exelia/worktrees.json').is_relative_to(root/'tasks'))
            with self.assertRaises(RuntimeError):worktrees.create(root,'TASK-1')
            self.assertEqual(len(worktrees.inspect(root)),1)

    def test_true_git_integration_no_push(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            repository(root,approved=True)
            entry=worktrees.create(root,'TASK-1')
            working=root/entry['path']
            (working/'api/src').mkdir(parents=True)
            (working/'api/src/feature.txt').write_text('implemented\n')
            subprocess.run(['git','add','api/src/feature.txt'],cwd=working,check=True)
            subprocess.run(['git','commit','-qm','feat: implemented'],cwd=working,check=True)
            backlog=json.loads((root/'tasks/backlog.json').read_text())
            backlog['tasks'][0]['status']='ready_for_review'
            from exelia.common import utc
            (root/'review.md').write_text('Independent fixture review: PASS; no outstanding findings.\n')
            backlog['tasks'][0]['review']={'reviewer':'independent-reviewer','result':'PASS',
                'commit':subprocess.run(['git','rev-parse',entry['branch']],cwd=root,capture_output=True,text=True,check=True).stdout.strip(),
                'timestamp':utc(),'evidence':'review.md','outstanding_findings':[]}
            save(root/'tasks/backlog.json',backlog)
            subprocess.run(['git','add','-A'],cwd=root,check=True)
            subprocess.run(['git','commit','-qm','test: reviewed'],cwd=root,check=True)
            before=subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout
            dry=worktrees.integrate(root,'TASK-1')
            self.assertIn('read-only',dry['action'])
            self.assertEqual(subprocess.run(['git','rev-parse','HEAD'],cwd=root,capture_output=True,text=True,check=True).stdout,before)
            done=worktrees.integrate(root,'TASK-1',confirm=True)
            self.assertIn('final main quality gate still required',done['action'])
            self.assertEqual((root/'api/src/feature.txt').read_text(),'implemented\n')
            self.assertEqual(subprocess.run(['git','remote'],cwd=root,capture_output=True,text=True).stdout.strip(),'')

    def test_dispatch_no_spawn_side_effects(self):
        tasks=[{'id':'A','status':'todo','scope':'app/src','dependencies':[], 'owner':'frontend-engineer','acceptance':'UI loads'},
               {'id':'B','status':'todo','scope':'api/src','dependencies':[], 'owner':'backend-engineer','acceptance':'API responds'}]
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);repository(root,approved=True,tasks=tasks)
            result=dispatch.dispatch(root,limit=2)
            self.assertEqual(len(result['packets']),2)
            self.assertFalse((root/'.exelia/worktrees').exists())
            self.assertFalse(any(p['model_recommendation']['actual_model_routing_verified'] for p in result['packets']))
            # Real dispatch only prepares worktrees; doesn't invoke Codex.
            # Tests replace ledger script with a stable local fixture.
            driver=root/'scripts/task-ledger.py'
            driver.write_text('import json,sys\nfrom pathlib import Path\np=Path("tasks/backlog.json")\nd=json.loads(p.read_text())\nfor x in d["tasks"]:\n if x["id"]==sys.argv[-1]:x["status"]="in_progress"\np.write_text(json.dumps(d)+"\\n")\n')
            subprocess.run(['git','add','-A'],cwd=root,check=True)
            subprocess.run(['git','commit','-qm','test: ledger script'],cwd=root,check=True)
            done=dispatch.dispatch(root,limit=2,prepare=True)
            self.assertEqual(len(done['prepared']),2)
            self.assertTrue((root/'.exelia/dispatch/last.json').is_file())
            self.assertEqual(worktrees.schedule(root)['ready'],[])


class QualityTests(unittest.TestCase):
    def test_no_app_never_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            self.assertFalse(quality.commands(root)['ready'])
            with self.assertRaises(RuntimeError):quality.configure(root)

    def test_product_scripts_required_and_explicit_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            save(root/'project.config.json',{'stack':{'frontend':'React','backend':None}})
            app=root/'app';app.mkdir()
            save(app/'package.json',{'scripts': {'lint':'eslint .','typecheck':'tsc --noEmit','test':'vitest run','build':'next build'}})
            plan=quality.commands(root)
            self.assertTrue(plan['ready'])
            with self.assertRaises(RuntimeError):quality.configure(root)
            save(root/'tasks/STATE.json',{'documentation_approved':True})
            quality.configure(root)
            lines=(root/'quality/commands.txt').read_text()
            self.assertIn('npm --prefix app run typecheck',lines)
            with self.assertRaises(RuntimeError):quality.configure(root)

    def test_browser_generator_requires_app_approval_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            self.assertFalse(visual.inspect(root)['eligible'])
            save(root/'project.config.json',{'stack':{'frontend':'Next.js'}})
            save(root/'app/package.json',{'scripts':{}})
            with self.assertRaises(RuntimeError):visual.setup(root)
            save(root/'tasks/STATE.json',{'documentation_approved':True})
            result=visual.setup(root)
            self.assertEqual(len(result['written']),2)
            self.assertIn('PLAYWRIGHT_BROWSERS_PATH',result['next'])
            with self.assertRaises(RuntimeError):visual.setup(root)
            with self.assertRaises(RuntimeError):visual.run(root)


class EvaluationTests(unittest.TestCase):
    def test_metrics_cannot_be_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            with self.assertRaises(ValueError):evaluations.record(root,task='A',agent='x',model='m',outcome='pass',evidence='')
            with self.assertRaises(ValueError):evaluations.record(root,task='A',agent='x',model='m',outcome='pass',duration=-1,evidence='output')
            evaluations.record(root,task='A',agent='qa',model='effective-model',outcome='pass',evidence='run 1')
            evaluations.record(root,task='B',agent='qa',model='effective-model',outcome='fail',tokens=123,cost=0.1,evidence='run 2')
            result=evaluations.summary(root)
            self.assertEqual(result['total_runs'],2)
            group=result['by_agent_model'][0]
            self.assertEqual(group['passed'],1)
            self.assertEqual(group['token_measured'],1)
            self.assertEqual(group['tokens_total'],123)
            self.assertEqual(group['cost_measured'],1)

    def test_model_routing_is_advisory(self):
        result=models.recommend(ROOT,'architecture','high')
        self.assertEqual(result['suggested_reasoning_effort'],'high')
        self.assertFalse(result['actual_model_routing_verified'])


if __name__=='__main__':unittest.main()
