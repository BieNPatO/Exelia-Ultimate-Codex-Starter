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
./scripts/quality-gate.sh "$mode"
git add -A
if git diff --cached --quiet;then echo 'No new changes; no checkpoint commit.';exit 0;fi
if git diff --cached --name-only | grep -Ev '(^|/)\.env(\.[^/]*)?\.example$' | grep -E '(^|/)(\.env($|\.)|id_rsa|id_ed25519|credentials\.json|service-account[^/]*\.json|.*\.(pem|key|p12|pfx)$)' ;then
 echo 'REFUSED: possible credential file staged. Unstage and rotate exposed secrets.' >&2;exit 6
fi
if git grep --cached -n -I -E -- '(-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{20}|github_pat_[A-Za-z0-9_]{15})' >/dev/null 2>&1;then
 echo 'REFUSED: possible private key/token text staged; review before commit.' >&2;exit 7
fi
while IFS= read -r -d '' path;do
 [[ -f "$path" ]] || continue
 size=$(wc -c < "$path" | tr -d ' ')
 if (( size > 10485760 ));then echo "REFUSED: staged file >10MiB: $path" >&2;exit 8;fi
done < <(git diff --cached --name-only -z --diff-filter=ACMR)
# Keep the exact Git diagnostic visible; vendor-specific exceptions live in .gitattributes.
if ! git diff --cached --check; then
  echo 'CHECKPOINT BLOCKED: Git whitespace validation failed (paths/lines shown above).' >&2
  echo 'Upstream Vercel skills are exempted narrowly in .gitattributes; fix own files, do not disable global checks.' >&2
  exit 9
fi
# Git itself records the verified commit hash. Do not mutate tracked state after commit.
git commit -m "$msg"
printf '\nLocal checkpoint saved. Nothing was pushed.\n'
