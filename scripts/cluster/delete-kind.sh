#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
. "${SCRIPT_DIR}/common-kind.sh"

require_exact_cluster_name
require_command kind

if cluster_exists; then
  kind delete cluster --name "${KIND_CLUSTER_NAME}"
else
  echo "kind cluster '${KIND_CLUSTER_NAME}' does not exist"
fi

