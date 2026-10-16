"""Shared conservative release guards. Detection is heuristic, never a secret guarantee."""
from __future__ import annotations

from pathlib import PurePosixPath
import re

# Explicit example suffixes are permitted; their contents are still scanned.
EXAMPLE_SUFFIXES = ('.example', '.sample', '.template')
CREDENTIAL_NAMES = {
    '.env', 'auth.json', 'credentials.json', 'credentials', '.netrc', '_netrc',
    '.npmrc', '.pypirc', 'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    'kubeconfig', 'service-account.json',
}
PRIVATE_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.kdbx', '.jks', '.keystore')
PRIVATE_DIRECTORIES = {'.aws', '.ssh', '.secrets'}


def is_sensitive_path(path) -> bool:
    """Protect credential basenames at any depth, including Windows separators."""
    parts = PurePosixPath(str(path).replace('\\', '/')).parts
    if not parts:
        return False
    name = parts[-1].lower()
    if any(part.lower() in PRIVATE_DIRECTORIES for part in parts):
        return True
    if name.endswith(EXAMPLE_SUFFIXES):
        return False
    return (name in CREDENTIAL_NAMES or name.startswith('.env.')
            or name.endswith(PRIVATE_SUFFIXES)
            or (name.startswith(('service-account', 'service_account')) and name.endswith('.json')))


TOKEN_PATTERNS = {
    'private key': re.compile('-----BEGIN ' + r'(?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'GitLab token': re.compile(r'\bglpat-[A-Za-z0-9_-]{20,}\b'),
    'OpenAI key': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}\b'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'npm token': re.compile(r'\bnpm_[A-Za-z0-9]{30,}\b'),
    'Slack token': re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    'Google API key': re.compile(r'\bAIza[A-Za-z0-9_-]{30,}\b'),
}


def secret_markers(text: str) -> list[str]:
    """Return marker types only; never return matching credential values."""
    return [name for name, pattern in TOKEN_PATTERNS.items() if pattern.search(text)]


AUTH_OUTPUT = re.compile(
    r'(?i)(?:[\w-]*(?:api[_-]?key|access[_-]?key|token|secret|password|passwd|'
    r'authorization|credential|client[_-]?secret)[\w-]*[\'\"]?\s*[:=]|'
    r'--[\w-]*(?:token|password|passwd|api[_-]?key|secret|credential)[\w-]*(?:\s|=)|'
    r'\b(?:bearer|basic)\s+\S+|[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@)'
)


def redact(text: str) -> str:
    """Suppress auth-bearing output entirely; arbitrary CLI multiline quoting is unsafe."""
    if AUTH_OUTPUT.search(text) or secret_markers(text):
        return '[REDACTED sensitive output]\n'
    return text
