#!/usr/bin/env bash
# Project-local tool launcher; does not read global npm/pip installations.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: scripts/local-tool.sh playwright-cli|skills|impeccable|uv|ruff [args...]" >&2; exit 2; }
name="$1"; shift
case "$name" in
  playwright-cli|skills|impeccable) bin="$ROOT/.exelia-tools/node/node_modules/.bin/$name";;
  uv|ruff) bin="$ROOT/.exelia-tools/python/bin/$name";;
  *) echo "Unsupported tool: $name" >&2; exit 2;;
esac
[[ -x "$bin" ]] || { echo "Local tool missing: $bin; run ./install.sh --apply" >&2; exit 3; }
cd "$ROOT"
exec "$bin" "$@"
