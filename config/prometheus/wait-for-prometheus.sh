#!/usr/bin/env bash
set -euo pipefail

: "${PROMETHEUS_URL:?PROMETHEUS_URL is required}"

for _ in $(seq 1 60); do
  if python -c "import urllib.request; urllib.request.urlopen('${PROMETHEUS_URL%/}/-/ready', timeout=2).read()" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

docker compose ps prometheus
docker compose logs --tail=100 prometheus
exit 1
