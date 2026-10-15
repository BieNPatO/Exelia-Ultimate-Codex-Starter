"""Offline UI and Ponytail tests. No network or modification of ~/.codex."""
import contextlib
import io
import pathlib
import tempfile
import subprocess
import sys
import json
import unittest
from installer.ui import UI

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TerminalUITests(unittest.TestCase):
    def test_no_global_rich_for_a_fresh_repo(self):
        # Even if this test runner has global Rich, an unrelated repo must not use it.
        with tempfile.TemporaryDirectory() as directory:
            ui = UI(pathlib.Path(directory), '2.0.4')
            self.assertIsNone(ui.rich_console)
            self.assertIn('fallback', ui.renderer)

    def test_bundled_rich_works_from_first_frame_without_site_packages(self):
        script = "from installer.ui import UI;from pathlib import Path;u=UI(Path.cwd(),'2.0.4');assert u.rich_console; print(u.renderer)"
        p = subprocess.run([sys.executable,'-S','-c',script],cwd=ROOT,
                           capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode, 0,p.stderr)
        self.assertIn('bundled / project-local',p.stdout)

    def test_ui_demo_is_read_only_and_renders_real_components(self):
        with tempfile.TemporaryDirectory() as d:
            # Explicit --ui-demo must not perform inspection, download or mutate repo.
            output = subprocess.run([sys.executable,'-S','-m','installer','--ui-demo'],
                                    cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(output.returncode,0,output.stderr)
            for token in ('EXELIA', 'DEMO DATA', 'ENVIRONMENT OVERVIEW',
                          'INSTALLATION PARTIAL','NEXT STEPS'):
                self.assertIn(token,output.stdout)
            self.assertIn('╭',output.stdout)

    def test_json_plan_stays_clean_without_third_party_site_packages(self):
        p=subprocess.run([sys.executable,'-S','-m','installer','--plan','--json'],
                         cwd=ROOT,capture_output=True,text=True,timeout=25)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['mode'],'plan')
        self.assertNotIn('╭',p.stdout)

    def test_bootstrap_status_and_summary_actionable(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as buf:
            ui = UI(pathlib.Path(directory), '2.0.4')
            ui.header('Clean Mac setup')
            ui.section('Skills')
            ui.status('impeccable', 'manual', 'Codex / Project')
            ui.status('ponytail', 'ready', 'repo skill')
            ui.summary({'outcome': 'partial', 'missing_skills': ['impeccable'],
                        'git_checkpoint': {'status': 'passed'},
                        'skills': {'impeccable': 'missing', 'ponytail': 'ready'}})
            output = buf.getvalue()
        self.assertIn('INSTALLATION PARTIAL', output)
        self.assertIn('./scripts/local-tool.sh impeccable install', output)
        self.assertIn('Global installs:', output)
        self.assertIn('ponytail', output)

    def test_json_mode_emits_no_decoration(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as buf:
            ui = UI(pathlib.Path(directory), '2.0.4', json_mode=True)
            ui.header('Invisible')
            ui.section('Invisible')
            ui.status('MCP', 'configured', 'server')
            ui.note('not displayed')
            ui.summary({'outcome': 'partial', 'missing_skills': [], 'skills': {}})
            ui.flush()
        self.assertEqual(buf.getvalue(), '')

    def test_potentially_global_plugin_is_never_required_by_project_prompt(self):
        for filename in ('AGENTS.md', 'START_NEW_PROJECT.md', '.codex/hooks/session_start.py'):
            content = (ROOT / filename).read_text()
            self.assertNotIn('Ponytail plugin must be validated independently', content)
            self.assertNotIn('check that its plugin and trusted hooks are working', content)
        self.assertIn('no global Ponytail plugin or trust required', (ROOT/'installer/engine.py').read_text())
        self.assertIn('NOT to Ponytail', (ROOT/'START_NEW_PROJECT.md').read_text())

    def test_project_exelia_hook_is_separate_from_ponytail(self):
        content=(ROOT/'.codex/hooks/session_start.py').read_text()
        self.assertIn('Exelia SessionStart hook is separate', content)
        self.assertNotIn('trusted hooks are working', (ROOT/'START_NEW_PROJECT.md').read_text())


if __name__ == '__main__':
    unittest.main()
