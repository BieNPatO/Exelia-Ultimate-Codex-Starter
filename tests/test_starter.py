"""Offline acceptance tests for starter scaffolding and fail-closed gates."""
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def run(*cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

class StarterTests(unittest.TestCase):
    def test_structural_validator(self):
        result = run(sys.executable, 'scripts/validate-starter.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codex_safe_config(self):
        config = tomllib.loads((ROOT/'.codex/config.toml').read_text())
        self.assertEqual(config['approval_policy'], 'on-request')
        self.assertEqual(config['sandbox_mode'], 'workspace-write')
        self.assertTrue(config['features']['multi_agent'])
        self.assertLessEqual(config['agents']['max_concurrent_threads_per_session'], 4)
        self.assertNotIn('model', config, 'Do not hardcode an unavailable main model')

    def test_language_and_approval_schema(self):
        config = json.loads((ROOT/'project.config.json').read_text())
        state = json.loads((ROOT/'tasks/STATE.json').read_text())
        self.assertIn(config['conversation_language'],(None,'pl','en'))
        self.assertIsInstance(config['application_ui_languages'],list)
        self.assertIsInstance(state['documentation_approved'],bool)

    def test_docs_gate_fails_before_discovery(self):
        result = run(sys.executable, 'scripts/validate-docs.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL', result.stdout)

    def test_app_gate_fails_without_approval(self):
        result = run('bash', 'scripts/quality-gate.sh', '--app')
        self.assertNotEqual(result.returncode, 0)

    def test_role_agent_files(self):
        roles = sorted((ROOT/'.codex/agents').glob('*.toml'))
        self.assertEqual(len(roles), 12)
        for p in roles:
            cfg = tomllib.loads(p.read_text())
            self.assertTrue(cfg['description'])
            self.assertTrue(cfg['developer_instructions'])

    def test_start_prompt_requires_language_before_product(self):
        content = (ROOT/'START_NEW_PROJECT.md').read_text()
        self.assertIn('Before doing any technical analysis', content)
        self.assertIn('application UI', content)
        self.assertIn('ONE explicit user approval', content)

    def test_shell_syntax(self):
        for f in (ROOT/'scripts').glob('*.sh'):
            proc = run('bash', '-n', str(f))
            self.assertEqual(proc.returncode, 0, f'{f}: {proc.stderr}')

    def test_state_command_rejects_stage_before_approval(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target/'scripts').mkdir()
            (target/'tasks').mkdir()
            shutil.copy2(ROOT/'scripts/project-state.py',target/'scripts/project-state.py')
            shutil.copy2(ROOT/'tasks/STATE.json',target/'tasks/STATE.json')
            shutil.copy2(ROOT/'project.config.json',target/'project.config.json')
            language = run(sys.executable,'scripts/project-state.py','language','pl',cwd=target)
            self.assertEqual(language.returncode,0,language.stderr)
            self.assertEqual(json.loads((target/'project.config.json').read_text())['conversation_language'],'pl')
            stage = run(sys.executable,'scripts/project-state.py','stage','01-backend',cwd=target)
            self.assertNotEqual(stage.returncode,0)
            denied = run(sys.executable,'scripts/project-state.py','approve','--evidence','I approve the documentation',cwd=target)
            self.assertNotEqual(denied.returncode,0,'Unfinished docs should block approval')
            # Install simulated completed documentation for the happy path.
            (target/'docs/project').mkdir(parents=True)
            for original in (ROOT/'docs/templates').glob('*.md'):
                filled=original.read_text().replace('STATUS: TEMPLATE — NOT APPROVED','STATUS: COMPLETED').replace('[TBD]','Independent user-reviewed specifications for this sample; no external requirements invented. ')
                (target/'docs/project'/original.name).write_text(filled)
            loc=run(sys.executable,'scripts/project-state.py','ui-language','en,pl',cwd=target)
            self.assertEqual(loc.returncode,0,loc.stderr)
            shutil.copy2(ROOT/'scripts/validate-docs.py',target/'scripts/validate-docs.py')
            approved = run(sys.executable,'scripts/project-state.py','approve','--evidence','I approve the documentation',cwd=target)
            self.assertEqual(approved.returncode,0,approved.stderr)
            stage = run(sys.executable,'scripts/project-state.py','stage','01-backend',cwd=target)
            self.assertEqual(stage.returncode,0,stage.stderr)

    def test_task_ledger_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)
            (target/'scripts').mkdir()
            (target/'tasks').mkdir()
            shutil.copy2(ROOT/'scripts/task-ledger.py',target/'scripts/task-ledger.py')
            shutil.copy2(ROOT/'tasks/backlog.json',target/'tasks/backlog.json')
            a=run(sys.executable,'scripts/task-ledger.py','add','TASK-001','--title','Create sample','--owner','backend-engineer','--scope','backend/**','--acceptance','All tests passing',cwd=target)
            self.assertEqual(a.returncode,0,a.stderr)
            self.assertEqual(run(sys.executable,'scripts/task-ledger.py','start','TASK-001',cwd=target).returncode,0)
            self.assertEqual(run(sys.executable,'scripts/task-ledger.py','review','TASK-001',cwd=target).returncode,0)
            # Completion cannot succeed without an actual gate executable.
            completion=run(sys.executable,'scripts/task-ledger.py','complete','TASK-001','--evidence','Tests pass',cwd=target)
            self.assertNotEqual(completion.returncode,0)
            data=json.loads((target/'tasks/backlog.json').read_text())
            self.assertEqual(data['tasks'][0]['status'],'ready_for_review')

    def test_no_remote_push_commands(self):
        for relative in ['scripts/git-checkpoint.sh','scripts/bootstrap.sh','scripts/release-local.sh']:
            script=(ROOT/relative).read_text()
            self.assertNotIn('\ngit push ',script)

if __name__ == '__main__':
    unittest.main()
