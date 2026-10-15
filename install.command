#!/usr/bin/env bash
# macOS Finder-friendly starter; terminal output persists after execution.
set -u
cd "$(dirname "$0")" || exit 2
./install.sh --apply
code=$?
printf '\nExelia installer exit status: %s\n' "$code"
if [[ -t 0 ]]; then read -r -p 'Press Enter to close this window... ' _; fi
exit "$code"
