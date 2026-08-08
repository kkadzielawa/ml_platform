#!/usr/bin/env bash
set -eu

EXPECTED_KIND_CLUSTER_NAME="ml-platform-study-dev"
KIND_CLUSTER_NAME="${KIND_CLUSTER_NAME:-${EXPECTED_KIND_CLUSTER_NAME}}"
KIND_CONFIG="${KIND_CONFIG:-clusters/dev/kind/cluster.yaml}"
KIND_CONTEXT="kind-${KIND_CLUSTER_NAME}"

fail() {
  echo "error: $*" >&2
  exit 1
}

require_exact_cluster_name() {
  if [ "${KIND_CLUSTER_NAME}" != "${EXPECTED_KIND_CLUSTER_NAME}" ]; then
    fail "refusing unexpected cluster name '${KIND_CLUSTER_NAME}'; expected '${EXPECTED_KIND_CLUSTER_NAME}'"
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command '$1' is not installed"
}

require_kind_config() {
  [ -f "${KIND_CONFIG}" ] || fail "kind config not found: ${KIND_CONFIG}"
}

cluster_exists() {
  kind get clusters 2>/dev/null | grep -Fx "${KIND_CLUSTER_NAME}" >/dev/null 2>&1
}

wait_for_nodes_ready() {
  require_command kubectl
  kubectl --context "${KIND_CONTEXT}" wait node --all --for=condition=Ready --timeout=180s
}
