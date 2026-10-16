#!/usr/bin/env bash
# Create local commit after a fresh passing quality gate; never push or rewrite history.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mode="${1:---app}"
msg="${2:-}"
case "$mode" in --starter|--docs|--app) ;; *) echo 'Usage: git-checkpoint.sh --starter|--docs|--app "type: subject"' >&2;exit 2;; esac
if [[ ! "$msg" =~ ^(feat|fix|docs|test|refactor|perf|chore|build|ci|revert)(\([a-z0-9-]+\))?:[[:space:]].+ ]];then
 echo 'Commit message must follow Conventional Commits, e.g. feat(auth): add login.' >&2;exit 2
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1;then echo 'No local git repo. Run bootstrap first.' >&2;exit 2;fi
shift 2
python3 scripts/checkpoint.py "$@"
checkpoint_tree="$(git write-tree)"
checkpoint_head="$(git rev-parse --verify HEAD 2>/dev/null || true)"
./scripts/quality-gate.sh "$mode"
if [[ "$(git write-tree)" != "$checkpoint_tree" || "$(git rev-parse --verify HEAD 2>/dev/null || true)" != "$checkpoint_head" ]];then
 echo 'CHECKPOINT BLOCKED: quality gate changed the index or HEAD; review changes.' >&2;exit 10
fi
python3 scripts/checkpoint.py --staged
if git diff --cached --quiet;then echo 'No new changes; no checkpoint commit.';exit 0;fi
# Keep the exact Git diagnostic visible; vendor-specific exceptions live in .gitattributes.
if ! git diff --cached --check; then
  echo 'CHECKPOINT BLOCKED: Git whitespace validation failed (paths/lines shown above).' >&2
  echo 'Upstream Vercel skills are exempted narrowly in .gitattributes; fix own files, do not disable global checks.' >&2
  exit 9
fi
# Git itself records the verified commit hash. Do not mutate tracked state after commit.
git commit -m "$msg"
printf '\nLocal checkpoint saved. Nothing was pushed.\n'
