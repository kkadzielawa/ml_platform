#!/usr/bin/env bash
set -euo pipefail

KIND_CLUSTER_NAME="${KIND_CLUSTER_NAME:-ml-platform-study-dev}"
VELERO_NAMESPACE="${VELERO_NAMESPACE:-velero}"
BACKUP_NAME_FILE="${BACKUP_NAME_FILE:-/tmp/ml-platform-phase-01-backup-name}"

kubectl_cmd() {
  kubectl --context "kind-${KIND_CLUSTER_NAME}" "$@"
}

if [[ -f "${BACKUP_NAME_FILE}" ]]; then
  BACKUP_NAME="$(cat "${BACKUP_NAME_FILE}")"
else
  BACKUP_NAME="$(
    kubectl_cmd get backups.velero.io --namespace "${VELERO_NAMESPACE}" \
      -l 'ml-platform.local/phase=01,ml-platform.local/backup-scope=phase-01' \
      -o jsonpath='{range .items[*]}{.metadata.creationTimestamp}{" "}{.metadata.name}{"\n"}{end}' \
      | sort \
      | tail -n 1 \
      | awk '{print $2}'
  )"
fi

if [[ -z "${BACKUP_NAME}" ]]; then
  echo "No Phase 1 Velero backup found" >&2
  exit 1
fi

echo "Inventory for Velero backup: ${BACKUP_NAME}"
kubectl_cmd get backups.velero.io "${BACKUP_NAME}" --namespace "${VELERO_NAMESPACE}" -o yaml
