#!/usr/bin/env bash
set -euo pipefail

: "${GARAGE_BUCKET:?GARAGE_BUCKET is required}"
: "${GARAGE_KEY_ID:?GARAGE_KEY_ID is required}"
: "${GARAGE_SECRET_KEY:?GARAGE_SECRET_KEY is required}"

garage() {
  docker compose exec -T garage /garage "$@"
}

for _ in $(seq 1 60); do
  if garage status >/tmp/garage-status.txt 2>/dev/null; then
    break
  fi
  sleep 1
done

if ! test -s /tmp/garage-status.txt; then
  docker compose ps garage
  exit 1
fi

node_id="$(awk '/^[0-9a-f]+/ {print $1; exit}' /tmp/garage-status.txt)"
if test -z "${node_id}"; then
  cat /tmp/garage-status.txt
  exit 1
fi

if ! garage layout show | grep -q "${node_id:0:8}"; then
  garage layout assign -z local -c 1GB "${node_id}"
  garage layout apply --version 1
fi

if ! garage key info "${GARAGE_KEY_ID}" >/dev/null 2>&1; then
  garage key import --yes -n local-lab "${GARAGE_KEY_ID}" "${GARAGE_SECRET_KEY}"
fi

if ! garage bucket info "${GARAGE_BUCKET}" >/dev/null 2>&1; then
  garage bucket create "${GARAGE_BUCKET}"
fi

garage bucket allow --read --write "${GARAGE_BUCKET}" --key "${GARAGE_KEY_ID}" >/dev/null
garage bucket info "${GARAGE_BUCKET}" >/dev/null
