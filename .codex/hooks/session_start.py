#!/usr/bin/env python3
"""Lightweight advisory Codex hook. Never print secrets or run remote processes."""
import json
from pathlib import Path
import subprocess

def main():
    root = Path.cwd()
    try:
        found = subprocess.run(['git','rev-parse','--show-toplevel'],check=True,text=True,capture_output=True,timeout=2)
        root = Path(found.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        config = json.loads((root/'project.config.json').read_text())
        state = json.loads((root/'tasks/STATE.json').read_text())
    except (OSError, ValueError):
        return
    language = config.get('conversation_language') or 'NOT_SET'
    if language == 'NOT_SET':
        directive = 'Ask whether the user wants to converse in Polish or English BEFORE discussing the project.'
    else:
        directive = f'Human language={language}; all technical artifacts/code English. App UI language set separately.'
    note = f"Exelia state: phase={state.get('phase')}; approved={state.get('documentation_approved')}; stage={state.get('current_stage')}; {directive} Use project-local Ponytail skill for coding if installed; no plugin hooks required. Exelia SessionStart hook is separate; QA+Git checkpoint required before completion."
    print(json.dumps({'hookSpecificOutput':{'hookEventName':'SessionStart','additionalContext':note}}))

if __name__=='__main__':
    main()
