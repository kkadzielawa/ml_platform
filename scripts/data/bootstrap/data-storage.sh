#!/usr/bin/env bash
set -euo pipefail

: "${KIND_CLUSTER_NAME:=ml-platform-study-dev}"
: "${CLUSTER_GARAGE_NAMESPACE:=ml-platform-data}"

context="kind-${KIND_CLUSTER_NAME}"
garage_namespace="${CLUSTER_GARAGE_NAMESPACE}"
status_file="$(mktemp)"

garage() {
  kubectl --context "${context}" exec --namespace "${garage_namespace}" garage-0 -- /garage "$@"
}

wait_for_garage() {
  for _ in $(seq 1 60); do
    if garage status >"${status_file}" 2>/tmp/ml-platform-data-storage-garage-status.err; then
      return 0
    fi
    sleep 2
  done
  cat /tmp/ml-platform-data-storage-garage-status.err
  return 1
}

ensure_key() {
  local scope="$1"
  local key_id="$2"
  local secret_key="$3"

  if ! garage key info "${key_id}" >/dev/null 2>&1; then
    garage key import --yes -n "data-${scope}" "${key_id}" "${secret_key}" >/dev/null
  fi
}

ensure_bucket() {
  local bucket="$1"
  local key_id="$2"

  if ! garage bucket info "${bucket}" >/dev/null 2>&1; then
    garage bucket create "${bucket}" >/dev/null
  fi

  garage bucket allow --read --write "${bucket}" --key "${key_id}" >/dev/null
}

apply_credentials_secret() {
  kubectl --context "${context}" apply -f - <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: data-storage-scoped-credentials
  namespace: ml-platform-data
  labels:
    app.kubernetes.io/name: data-storage
    app.kubernetes.io/component: scoped-credentials
type: Opaque
stringData:
  raw-access-key-id: GK333333333333333333333333
  raw-secret-access-key: "3333333333333333333333333333333333333333333333333333333333333333"
  curated-access-key-id: GK444444444444444444444444
  curated-secret-access-key: "4444444444444444444444444444444444444444444444444444444444444444"
  artifacts-access-key-id: GK555555555555555555555555
  artifacts-secret-access-key: "5555555555555555555555555555555555555555555555555555555555555555"
  models-access-key-id: GK666666666666666666666666
  models-secret-access-key: "6666666666666666666666666666666666666666666666666666666666666666"
  evaluation-access-key-id: GK777777777777777777777777
  evaluation-secret-access-key: "7777777777777777777777777777777777777777777777777777777777777777"
YAML
}

wait_for_garage

ensure_key "raw" "GK333333333333333333333333" "3333333333333333333333333333333333333333333333333333333333333333"
ensure_key "curated" "GK444444444444444444444444" "4444444444444444444444444444444444444444444444444444444444444444"
ensure_key "artifacts" "GK555555555555555555555555" "5555555555555555555555555555555555555555555555555555555555555555"
ensure_key "models" "GK666666666666666666666666" "6666666666666666666666666666666666666666666666666666666666666666"
ensure_key "evaluation" "GK777777777777777777777777" "7777777777777777777777777777777777777777777777777777777777777777"

ensure_bucket "ml-platform-raw" "GK333333333333333333333333"
ensure_bucket "ml-platform-curated" "GK444444444444444444444444"
ensure_bucket "ml-platform-artifacts" "GK555555555555555555555555"
ensure_bucket "ml-platform-models" "GK666666666666666666666666"
ensure_bucket "ml-platform-evaluation" "GK777777777777777777777777"

apply_credentials_secret

echo "data storage buckets and scoped credentials are ready"
