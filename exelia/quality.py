"""Generate a strict, inspectable product QA gate from real package configuration."""
from __future__ import annotations
import json
from pathlib import Path
from .common import ROOT, approved, load


def commands(root: Path = ROOT):
    cfg = load(root / 'project.config.json', {})
    frontend = (cfg.get('stack') or {}).get('frontend') or ''
    backend = (cfg.get('stack') or {}).get('backend') or ''
    result = []
    warnings = []
    web = root / 'app' / 'package.json'
    if frontend:
        if not web.is_file():
            warnings.append('Configured frontend but app/package.json is missing.')
        else:
            content = json.loads(web.read_text(encoding='utf-8'))
            scripts = content.get('scripts') or {}
            for name in ('lint', 'typecheck', 'test', 'build'):
                if name in scripts:
                    result.append(f'npm --prefix app run {name}')
                else:
                    warnings.append('Frontend package.json lacks an explicit '+name+' script.')
    api = root / 'api'
    if backend:
        if not api.is_dir():
            warnings.append('Configured backend but api/ is missing.')
        else:
            if (api / 'tests').is_dir():
                if (api / '.venv/bin/python').is_file():
                    result.append('api/.venv/bin/python -m pytest api/tests')
                else:
                    warnings.append('Python backend requires project-local api/.venv/bin/python for pytest.')
            else:
                warnings.append('Backend api/tests is missing.')
            if (api / 'pyproject.toml').is_file():
                result.append('./scripts/local-tool.sh ruff check api')
            else:
                warnings.append('Backend api/pyproject.toml is missing.')
    if not frontend and not backend:
        warnings.append('Technology stack not selected; QA commands cannot yet be generated.')
    if not result:
        warnings.append('No checks configured. A production quality gate must not silently pass.')
    return {'commands': result, 'warnings': warnings,
            'ready': bool(result) and not warnings}


def configure(root: Path = ROOT, *, overwrite=False):
    approved(root)
    plan = commands(root)
    if not plan['ready']:
        raise RuntimeError('QA configuration incomplete: ' + '; '.join(plan['warnings']))
    target = root / 'quality/commands.txt'
    current = target.read_text(encoding='utf-8') if target.exists() else ''
    if any(not line.strip().startswith('#') and line.strip() for line in current.splitlines()) and not overwrite:
        raise RuntimeError('Existing application gate would be overwritten; use --overwrite after review.')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('# Generated from actual app stack; edit intentionally if needed.\n' + '\n'.join(plan['commands']) + '\n', encoding='utf-8')
    return plan
