#!/bin/sh
# Release task (IMP-218; A1 §4.5, IMD-103): a one-off ECS task, run with the new image before any
# service is updated. Any failure stops the deploy, except an embedding outage (index exit 3,
# IMD-112). Each step prints one line and no secret.
set -eu

echo "release: auth stub"
python -m app.db.auth_stub --if-missing

echo "release: migrations"
alembic upgrade head

for dir in ${SEED_DIRS:-}; do
  echo "release: seed $dir"
  python -m app.places.seed "$dir"
done

# The index covers curated destinations only (data_tier = 'curated', A2 §6.5): live destinations
# are indexed by their own import job, and this step never touches their documents.
echo "release: RAG index (curated destinations)"
status=0
python -m app.rag.index --strict || status=$?
case "$status" in
  0) ;;
  3) echo "release: warning: embedding provider unavailable; the index is incomplete until the next release" ;;
  *) exit "$status" ;;
esac

echo "release: done"
