#!/usr/bin/env bash
set -euo pipefail

: "${MLFLOW_TRACKING_URI:?MLFLOW_TRACKING_URI is required}"

for _ in $(seq 1 120); do
  if python -c "import urllib.request; urllib.request.urlopen('${MLFLOW_TRACKING_URI%/}/health', timeout=2).read()" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

docker compose ps mlflow
docker compose logs --tail=100 mlflow
exit 1
