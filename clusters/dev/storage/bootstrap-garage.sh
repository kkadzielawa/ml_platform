#!/usr/bin/env bash
set -euo pipefail

: "${KIND_CLUSTER_NAME:?KIND_CLUSTER_NAME is required}"
: "${CLUSTER_GARAGE_NAMESPACE:?CLUSTER_GARAGE_NAMESPACE is required}"
: "${GARAGE_BUCKET:?GARAGE_BUCKET is required}"
: "${GARAGE_KEY_ID:?GARAGE_KEY_ID is required}"
: "${GARAGE_SECRET_KEY:?GARAGE_SECRET_KEY is required}"

context="kind-${KIND_CLUSTER_NAME}"
status_file="$(mktemp)"

garage() {
  kubectl --context "${context}" exec --namespace "${CLUSTER_GARAGE_NAMESPACE}" garage-0 -- /garage "$@"
}

for _ in $(seq 1 60); do
  if garage status >"${status_file}" 2>/tmp/ml-platform-garage-status.err; then
    break
  fi
  sleep 2
done

if [ ! -s "${status_file}" ]; then
  cat /tmp/ml-platform-garage-status.err
  exit 1
fi

node_id="$(awk '/^[0-9a-f]+/ {print $1; exit}' "${status_file}")"
if [ -z "${node_id}" ]; then
  cat "${status_file}"
  exit 1
fi

short_node_id="$(printf '%s' "${node_id}" | cut -c 1-8)"
if ! garage layout show | grep -q "${short_node_id}"; then
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
