#!/usr/bin/env python3
"""Offline public repository hygiene; deliberately conservative and non-destructive."""
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'auth.json','credentials.json','.env','.env.local','service-account.json','id_rsa','id_ed25519'}
DIRECTORIES={'.exelia','.exelia-install','.exelia-tools','node_modules','__pycache__','.git'}

def check():
    problems=[]
    files=[]
    cmd=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True)
    if cmd.returncode==0 and cmd.stdout:
        files=[Path(i.decode()) for i in cmd.stdout.split(b'\0') if i]
    else:
        files=[p.relative_to(ROOT) for p in ROOT.rglob('*') if p.is_file() and not any(x in DIRECTORIES for x in p.relative_to(ROOT).parts)]
    for path in files:
        if path.is_absolute() or '..' in path.parts:
            problems.append('unsafe tracked path: '+str(path));continue
        if any(x in DIRECTORIES for x in path.parts):problems.append('private runtime path: '+str(path));continue
        if path.name in FORBIDDEN or (path.name.startswith('.env.') and not path.name.endswith('.example')):
            problems.append('credential filename: '+str(path));continue
        full=ROOT/path
        if not full.is_file() or full.is_symlink():continue
        if full.stat().st_size>10_000_000:problems.append('oversized tracked file: '+str(path))
        if full.stat().st_size > 1_000_000 or path.suffix in {'.png','.jpg','.jpeg','.zip','.pdf'}:continue
        text=full.read_text(encoding='utf-8',errors='replace')
        # Construct patterns from segments to avoid flagging this scanner as a false positive.
        if re.search('-----BEGIN ' + '(?:RSA |EC |OPENSSH )?' + 'PRIVATE KEY-----',text):
            problems.append('private key marker: '+str(path))
        if re.search('gh' + 'p_[A-Za-z0-9]{30,}',text):
            problems.append('GitHub token marker: '+str(path))
    for needed in ('LICENSE','SECURITY.md','CONTRIBUTING.md','.gitignore','README.md','docs/GITHUB_SETUP.md'):
        if not (ROOT/needed).is_file():problems.append('missing publication file: '+needed)
    print('PUBLICATION AUDIT:', 'PASS' if not problems else 'FAIL')
    print('Inspected',len(files),'files. This is not a full secret/third-party license scanner.')
    for error in problems:print(' -',error)
    return 1 if problems else 0
if __name__=='__main__':sys.exit(check())
