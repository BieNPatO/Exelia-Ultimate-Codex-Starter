"""Resolve only project-relevant capabilities; inspect and freeze local SKILL.md checksums."""
from __future__ import annotations
import hashlib
from pathlib import Path
from .common import ROOT, load, save, utc

CORE = ('systematic-debugging', 'verification-before-completion', 'ponytail')
WEB = ('frontend-design', 'vercel-react-best-practices', 'vercel-composition-patterns', 'web-design-guidelines', 'shadcn', 'impeccable')
PYTHON = ('fastapi',)
SECURITY = ('differential-review',)
BROWSER = ('playwright-cli',)
CUSTOM = ('project-delivery', 'premium-motion', 'python-backend-engineering')


def resolve(root: Path = ROOT, *, include_qa: bool = False, include_security: bool = False):
    cfg = load(root / 'project.config.json', {})
    stack = cfg.get('stack') or {}
    settings = cfg.get('capabilities') or {}
    selectors = {'include_qa': include_qa, 'include_security': include_security}
    include_qa = include_qa or bool(settings.get('visual_qa', False))
    include_security = include_security or bool(settings.get('security_review', False))
    frontend = (stack.get('frontend') or '').lower()
    backend = (stack.get('backend') or '').lower()
    selected = list(CORE)
    if any(x in frontend for x in ('next', 'react', 'web', 'vue', 'svelte')):
        selected.extend(WEB)
        if include_qa:
            selected.extend(BROWSER)
    if 'fastapi' in backend:
        selected.extend(PYTHON)
    if include_security:
        selected.extend(SECURITY)
    manifest = load(root / 'manifests/components.json', {})
    known = {entry['name']: entry for entry in manifest.get('skills', [])}
    out = []
    for name in dict.fromkeys(selected):
        path = root / '.agents/skills' / name / 'SKILL.md'
        if (not path.resolve().is_relative_to(root.resolve())
                or any(parent.is_symlink() for parent in
                       (root / '.agents', root / '.agents/skills', path.parent, path))):
            raise RuntimeError('Skill path must remain inside the project without symlinks: ' + name)
        digest = None
        files_count = 0
        if path.is_file() and not path.is_symlink() and not path.parent.is_symlink():
            skill_root = path.parent
            hasher = hashlib.sha256()
            if any(p.is_symlink() for p in skill_root.rglob('*')):
                raise RuntimeError('Symlink inside skill directory; cannot safely freeze or verify: '+name)
            for file in sorted(p for p in skill_root.rglob('*') if p.is_file() and p.name != '.DS_Store' and '__pycache__' not in p.parts):
                rel = file.relative_to(skill_root).as_posix()
                hasher.update(rel.encode('utf-8') + b'\x00')
                hasher.update(hashlib.sha256(file.read_bytes()).digest())
                files_count += 1
            digest = hasher.hexdigest()
        out.append({'name': name, 'source': known.get(name, {}).get('source'),
                    'source_revision': known.get(name, {}).get('commit'),
                    'installed_local': bool(digest), 'sha256': digest, 'files_hashed': files_count,
                    'revision_pinned': bool(known.get(name, {}).get('commit'))})
    return {'schema_version': 2, 'generated_at': utc(), 'stack': stack, 'selectors': selectors,
            'selected': out, 'missing': [x['name'] for x in out if not x['installed_local']],
            'warning': 'Local SHA-256 records installed content, not supplier provenance; recorded revision pins do not authenticate package builds or suppliers.'}


def audit(root: Path = ROOT):
    locked = load(root / 'manifests/skills.lock.json')
    if not locked:
        return {'status': 'NOT_LOCKED', 'detail': 'Run capabilities freeze after installing selected skills.'}
    current_snapshot = resolve(root, **locked.get('selectors', {}))
    local = {item['name']: item for item in current_snapshot['selected']}
    previous = {item['name']: item for item in locked['selected']}
    differences = []
    for name in sorted(previous.keys() | local.keys()):
        expected, current = previous.get(name), local.get(name)
        fields = ('sha256', 'installed_local', 'source', 'source_revision')
        if expected is None or current is None or not current['installed_local'] or any(current.get(key) != expected.get(key) for key in fields):
            differences.append({'name': name, 'expected': expected, 'current': current})
    if locked.get('stack') != current_snapshot['stack']:
        differences.append({'field': 'stack', 'expected': locked.get('stack'), 'current': current_snapshot['stack']})
    return {'status': 'PASS' if not differences else 'DRIFT', 'differences':differences,
            'missing': current_snapshot['missing'],
            'note':'Detects local file changes only; no upstream authenticity guarantee.'}

def freeze(root: Path = ROOT, **kwargs):
    snapshot = resolve(root, **kwargs)
    if snapshot['missing']:
        raise RuntimeError('Cannot freeze missing project skills: ' + ', '.join(snapshot['missing']))
    # Lock is generated only after explicit action; no network access.
    save(root / 'manifests/skills.lock.json', snapshot)
    return snapshot
