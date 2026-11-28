#!/usr/bin/env bash
# The sandbox adds a directory level; preserve repository-relative SAMPLE fixture lookup.
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_link="$repo_dir/apps/data"
if [[ -e "$fixture_link" || -L "$fixture_link" ]]; then
  echo "mutation: apps/data already exists; refusing to replace it" >&2
  exit 1
fi
ln -s ../data "$fixture_link"
trap 'rm -- "$fixture_link"' EXIT
cd "$repo_dir/apps/api"
timeout --signal=INT --kill-after=20s 15m .venv/bin/mutmut run --max-children 4 "$@"
