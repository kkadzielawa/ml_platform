#!/usr/bin/env bash
set -euo pipefail

: "${GRAFANA_URL:?GRAFANA_URL is required}"

for _ in $(seq 1 60); do
  if python -c "import urllib.request; urllib.request.urlopen('${GRAFANA_URL%/}/api/health', timeout=2).read()" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

docker compose ps grafana
docker compose logs --tail=100 grafana
exit 1
