#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "${SCRIPT_DIR}/common-kind.sh"

require_exact_cluster_name
require_command docker
require_command kind
require_kind_config

if cluster_exists; then
  echo "kind cluster '${KIND_CLUSTER_NAME}' already exists"
else
  kind create cluster \
    --name "${KIND_CLUSTER_NAME}" \
    --config "${KIND_CONFIG}" \
    --wait 120s
fi

kind get kubeconfig --name "${KIND_CLUSTER_NAME}" >/dev/null
wait_for_nodes_ready
echo "kind cluster '${KIND_CLUSTER_NAME}' is available"
