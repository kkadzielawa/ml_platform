#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "${SCRIPT_DIR}/common-kind.sh"

require_exact_cluster_name
require_command kind
require_command kubectl

cluster_exists || fail "kind cluster '${KIND_CLUSTER_NAME}' does not exist"

echo "kind cluster: ${KIND_CLUSTER_NAME}"
kind version
kubectl --context "${KIND_CONTEXT}" cluster-info
wait_for_nodes_ready
kubectl --context "${KIND_CONTEXT}" get nodes -L ml-platform.local/node-pool,ml-platform.local/workload-class

not_ready_nodes="$(
  kubectl --context "${KIND_CONTEXT}" get nodes --no-headers | awk '$2 != "Ready" { print $1 ":" $2 }'
)"

if [ -n "${not_ready_nodes}" ]; then
  fail "not all nodes are Ready: ${not_ready_nodes}"
fi

echo "all nodes are Ready"
