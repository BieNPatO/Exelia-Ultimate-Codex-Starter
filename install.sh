#!/usr/bin/env bash
# Portable launcher for Python standard-library Exelia Full Installer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
find_python() {
  for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
      printf '%s' "$candidate";return 0
    fi
  done
  return 1
}
PY="$(find_python || true)"
if [[ -z "$PY" ]]; then
  echo 'EXELIA: Python >=3.11 is a host prerequisite, not installed by this project.' >&2
  echo 'Install it yourself using your preferred manager; no global packages will be changed.' >&2
  exit 2
fi

export EXELIA_PYTHON="$(command -v "$PY")"
exec "$PY" -m installer "$@"
