#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${EXELIA_PYTHON:-python3}"
mode="${1:---starter}"
case "$mode" in
 --starter)
   "$PY" scripts/validate-starter.py
   "$PY" -m unittest discover -s tests -v
   ;;
 --docs)
   "$PY" scripts/validate-docs.py
   ;;
 --app)
   "$PY" scripts/validate-starter.py
   "$PY" scripts/validate-docs.py
   "$PY" - <<'PY'
import json,sys
with open('tasks/STATE.json',encoding='utf-8') as f:s=json.load(f)
if not s.get('documentation_approved'):
 print('FAIL: application implementation gate requires approved docs');sys.exit(3)
PY
   if [[ ! -f quality/commands.txt ]]; then
     echo 'FAIL: set actual app validation commands in quality/commands.txt' >&2;exit 4
   fi
   count=0
   while IFS= read -r cmd || [[ -n "$cmd" ]]; do
     [[ "$cmd" =~ ^[[:space:]]*(#|$) ]] && continue
     count=$((count + 1))
     echo "QUALITY [$count]: $cmd"
     bash -o pipefail -c "$cmd"
   done < quality/commands.txt
   if [[ "$count" -eq 0 ]]; then echo 'FAIL: no executable app checks configured' >&2; exit 5; fi
   ;;
 *) echo 'Usage: quality-gate.sh --starter|--docs|--app' >&2;exit 2;;
esac
printf 'QUALITY GATE: PASS (%s)\n' "$mode"
