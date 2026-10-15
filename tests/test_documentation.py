"""Guard that the human guides and Codex prompts remain clear and aligned."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class DocumentationTests(unittest.TestCase):
    def test_entrypoints_and_navigation(self):
        readme=(ROOT/'README.md').read_text()
        start=(ROOT/'START_HERE.md').read_text()
        for name in ('START_HERE.md','START_NEW_PROJECT.md','CONTINUE_PROJECT.md','docs/installer/TROUBLESHOOTING.md'):
            self.assertIn(name,readme)
        for cmd in ('--check','--plan','--apply','--verify'):
            self.assertIn(cmd,start)

    def test_prompts_keep_approval_and_language_guards(self):
        prompt=(ROOT/'START_NEW_PROJECT.md').read_text()
        self.assertIn('Before doing any technical analysis',prompt)
        self.assertIn('ONE explicit user approval',prompt)
        self.assertIn('application UI',prompt)
        self.assertIn('no global Ponytail plugin or trust required',prompt)
        self.assertIn('NOT to Ponytail',prompt)
        self.assertIn('First response — mandatory',prompt)
        self.assertIn('docs/project/',prompt)
        self.assertIn('scripts/project-state.py approve',prompt)
        self.assertIn('English',prompt)
        resume=(ROOT/'CONTINUE_PROJECT.md').read_text()
        self.assertIn('Git',resume)
        self.assertIn('approval',resume)

    def test_docs_dont_claim_global_install(self):
        docs='\n'.join((ROOT/p).read_text() for p in ('README.md','START_HERE.md','docs/installer/PONYTAIL.md'))
        self.assertIn('project-local',docs)
        self.assertIn('not as a global',docs.lower())
        self.assertTrue((ROOT/'docs/installer/TROUBLESHOOTING.md').is_file())

    def test_markdown_no_trailing_spaces(self):
        for rel in ('README.md','START_HERE.md','START_NEW_PROJECT.md','CONTINUE_PROJECT.md','docs/installer/TROUBLESHOOTING.md','docs/installer/PONYTAIL.md'):
            with self.subTest(rel=rel):
                self.assertFalse(any(line.rstrip('\r\n').endswith(' ') for line in (ROOT/rel).read_text().splitlines(keepends=True)))

if __name__=='__main__':unittest.main()
