#!/usr/bin/env bash
set -euo pipefail

KIND_CLUSTER_NAME="${KIND_CLUSTER_NAME:-ml-platform-study-dev}"
VELERO_NAMESPACE="${VELERO_NAMESPACE:-velero}"
BACKUP_NAME="${BACKUP_NAME:-phase-01-$(date -u +%Y%m%d%H%M%S)}"
BACKUP_NAME_FILE="${BACKUP_NAME_FILE:-/tmp/ml-platform-phase-01-backup-name}"

kubectl_cmd() {
  kubectl --context "kind-${KIND_CLUSTER_NAME}" "$@"
}

kubectl_cmd create -f - <<YAML
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: ${BACKUP_NAME}
  namespace: ${VELERO_NAMESPACE}
  labels:
    ml-platform.local/phase: "01"
    ml-platform.local/backup-scope: phase-01
    ml-platform.local/environment: dev
spec:
  includedNamespaces:
    - ml-platform-system
    - ml-platform-data
    - ml-platform-observability
    - ml-platform-project-housing
  excludedResources:
    - events
    - events.events.k8s.io
    - secrets
  storageLocation: default
  ttl: 24h0m0s
  snapshotVolumes: false
  defaultVolumesToFsBackup: false
YAML

for _ in $(seq 1 120); do
  phase="$(kubectl_cmd get backups.velero.io "${BACKUP_NAME}" --namespace "${VELERO_NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  case "${phase}" in
    Completed)
      printf '%s\n' "${BACKUP_NAME}" > "${BACKUP_NAME_FILE}"
      echo "Velero backup completed: ${BACKUP_NAME}"
      exit 0
      ;;
    Failed|PartiallyFailed)
      kubectl_cmd get backups.velero.io "${BACKUP_NAME}" --namespace "${VELERO_NAMESPACE}" -o yaml
      echo "Velero backup did not complete successfully: ${phase}" >&2
      exit 1
      ;;
  esac
  sleep 5
done

kubectl_cmd get backups.velero.io "${BACKUP_NAME}" --namespace "${VELERO_NAMESPACE}" -o yaml
echo "Timed out waiting for Velero backup to complete: ${BACKUP_NAME}" >&2
exit 1
