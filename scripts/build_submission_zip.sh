#!/usr/bin/env bash
# Tools are installed in uvx/npx caches, never in repository dependency manifests.
set -euo pipefail
submission_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$submission_repo"
exec uvx --from python-pptx==1.0.2 --with pypdf==7.2.0 python scripts/build_submission_zip.py "$@"
