#!/usr/bin/env bash
# Project-local tool launcher; does not read global npm/pip installations.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: scripts/local-tool.sh playwright-cli|skills|impeccable|uv|ruff [args...]" >&2; exit 2; }
name="$1"; shift
cd "$ROOT"
bin="$(python3 -m installer.localtools "$ROOT" "$name")"
cd "$ROOT"
exec "$bin" "$@"
