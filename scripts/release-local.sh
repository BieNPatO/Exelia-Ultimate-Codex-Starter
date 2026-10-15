#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)";cd "$ROOT"
tag="${1:-}"
if [[ ! "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]];then echo 'Usage: release-local.sh vX.Y.Z' >&2;exit 2;fi
if [[ -n "$(git status --porcelain)" ]];then echo 'Refusing tag on dirty working tree; make a QA checkpoint first.' >&2;exit 3;fi
./scripts/quality-gate.sh --app
if git rev-parse "$tag" >/dev/null 2>&1;then echo 'Tag already exists' >&2;exit 4;fi
git tag -a "$tag" -m "Local release $tag"
echo "Created local annotated release tag $tag. No push was performed."
