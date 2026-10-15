"""Offline tests of scoped installation, path safety, and Git validation."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, unittest
from installer.engine import Session, plan_actions
from installer.probe import version, compatible, scan_skill
from installer.platforms import detect
ROOT=pathlib.Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'manifests/components.json').read_text())


def fake_findings():
    return {'platform':{'os':'darwin','architecture':'arm64','package_manager':'brew',
                        'wsl':False,'supported':True},
            'tools':{x['id']:{'status':'missing','detail':'not installed'} for x in MANIFEST['tools']},
            'skills':{x['name']:{'status':'missing','detail':'not installed'} for x in MANIFEST['skills']},
            'plugins':{'status':'ready','names':[],'marketplace_present':False,'detail':'none'},
            'mcp':{'configured_names':['openaiDeveloperDocs','context7']},
            'docker_daemon':{'status':'not-running','detail':'daemon stopped'},
            'git':{'inside_repo':False,'own_repo':False,'identity':False}}

class InstallerTests(unittest.TestCase):
    def test_versions_semantics(self):
        self.assertEqual(version('v22.16.0'),'22.16.0')
        self.assertFalse(compatible('19.9.9','20'))
        self.assertTrue(compatible('22.16.0','20'))

    def test_platform_discovery(self):
        d=detect();self.assertIn(d['os'],('darwin','linux','windows'))
        self.assertIn('architecture',d);self.assertIn('wsl',d)

    def test_no_global_or_host_install_commands_ever_planned(self):
        a=plan_actions(ROOT,MANIFEST,fake_findings(),system_changes=True,optional=True)
        runnable=[x for x in a if not x['blocked']]
        self.assertTrue(runnable)
        self.assertTrue(all(x['scope']=='project' for x in runnable))
        for x in runnable:
            text=' '.join(x['command'])
            self.assertNotIn('--global',text)
            self.assertNotIn(' -g ',text)
            self.assertNotIn('brew install',text)
            self.assertNotIn('sudo',text)
            self.assertNotIn('codex plugin',text)
            self.assertNotIn('ctx7 setup',text)

    def test_missing_host_tools_are_manual_only(self):
        a=plan_actions(ROOT,MANIFEST,fake_findings(),system_changes=True)
        host=[x for x in a if x['scope']=='host']
        self.assertTrue(host)
        self.assertTrue(all(x['blocked'] and not x['command'] for x in host))
        self.assertEqual(len(a),len({x['id'] for x in a}))

    def test_playwright_and_skills_installed_locally(self):
        a=plan_actions(ROOT,MANIFEST,fake_findings())
        self.assertNotIn('local-npm-playwright-cli',[x['id'] for x in a])  # browser tools only after web discovery
        self.assertIn('local-npm-skills-cli',[x['id'] for x in a])
        self.assertIn('skill-ponytail',[x['id'] for x in a])
        for x in a:
            if x['kind']=='skill':
                self.assertIn('--copy',x['command'])
                self.assertNotIn('-g',x['command'])

    def test_global_skill_is_not_accepted_as_project_install(self):
        with tempfile.TemporaryDirectory() as d:
            home=pathlib.Path(d)/'home';root=pathlib.Path(d)/'repo';root.mkdir()
            g=home/'.agents/skills/frontend-design/SKILL.md';g.parent.mkdir(parents=True)
            g.write_text('---\nname: frontend-design\ndescription: Design things.\n---\n')
            a=scan_skill('frontend-design',root,home)
            self.assertEqual(a['status'],'missing')
            self.assertTrue(a['global_also_present'])
            local=root/'.agents/skills/frontend-design/SKILL.md';local.parent.mkdir(parents=True)
            local.write_text(g.read_text())
            self.assertEqual(scan_skill('frontend-design',root,home)['status'],'ready')

    def test_ponytail_not_installed_as_global_plugin(self):
        a=plan_actions(ROOT,MANIFEST,fake_findings())
        self.assertFalse(any(x['kind'] in ('plugin','plugin-marketplace') for x in a))
        self.assertTrue(any(x['id']=='skill-ponytail' for x in a))

    def test_git_attributes_scope_vendor_only(self):
        attr=(ROOT/'.gitattributes').read_text()
        self.assertIn('.agents/skills/vercel-composition-patterns/** whitespace=-blank-at-eol',attr)
        self.assertIn('.agents/skills/vercel-react-best-practices/** whitespace=-blank-at-eol',attr)
        self.assertNotIn('\n* whitespace=-blank-at-eol',attr)

    def test_git_whitespace_upstream_vercel_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            (root/'.gitattributes').write_text((ROOT/'.gitattributes').read_text())
            vendor=root/'.agents/skills/vercel-react-best-practices/AGENTS.md'
            vendor.parent.mkdir(parents=True)
            vendor.write_text('**Version 1.0.0**  \n')
            subprocess.run(['git','init','-q'],cwd=root,check=True)
            subprocess.run(['git','add','.gitattributes',str(vendor.relative_to(root))],cwd=root,check=True)
            check=subprocess.run(['git','diff','--cached','--check'],cwd=root,capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stderr)
            own=root/'README.md';own.write_text('My app  \n')
            subprocess.run(['git','add','README.md'],cwd=root,check=True)
            check=subprocess.run(['git','diff','--cached','--check'],cwd=root,capture_output=True,text=True)
            self.assertNotEqual(check.returncode,0)
            self.assertIn('README.md',check.stdout)

    def test_backup_rollback_preserves_user_modifications(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);f=root/'config.toml';f.write_text('before')
            session=Session(root)
            with session.locked():
                b=session.backup('config.toml');f.write_text('after');session.backup_complete(b)
                self.assertEqual(session.restore(),['RESTORED config.toml'])
            with session.locked():
                b=session.backup('config.toml');f.write_text('installer update');session.backup_complete(b)
                f.write_text('user update')
                notes=session.restore()
                self.assertTrue(any('SKIP changed' in line for line in notes))
                self.assertEqual(f.read_text(),'user update')

    def test_lock_refuses_second_live_installer(self):
        with tempfile.TemporaryDirectory() as d:
            a=Session(pathlib.Path(d));b=Session(pathlib.Path(d))
            with a.locked():
                with self.assertRaises(RuntimeError):
                    with b.locked():pass

    def test_plan_readonly(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)
            shutil.copytree(ROOT/'installer',root/'installer')
            shutil.copytree(ROOT/'manifests',root/'manifests')
            shutil.copytree(ROOT/'exelia',root/'exelia')
            env=os.environ.copy();env['PYTHONPATH']=str(root)
            p=subprocess.run([sys.executable,'-m','installer','--plan','--json'],cwd=root,env=env,
                capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(json.loads(p.stdout)['mode'],'plan')
            self.assertFalse((root/'.git').exists());self.assertFalse((root/'.exelia-install').exists())

    def test_global_changes_flag_is_rejected(self):
        p=subprocess.run([sys.executable,'-m','installer','--plan','--allow-system-changes'],cwd=ROOT,
                         capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('project-local only',p.stderr)

    def test_rollback_rejects_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d)/'repo';root.mkdir()
            with self.assertRaises(RuntimeError):Session(root).backup('../bad')

if __name__=='__main__':unittest.main()
