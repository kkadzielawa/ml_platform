from __future__ import annotations

import os
import subprocess


BROWSER_AUTHORITY = "http://127.0.0.1:18081/realms/ml-platform-study"
DISCOVERY_URI = (
    "http://openmetadata-oidc-discovery-adapter.ml-platform-data.svc.cluster.local:8080/"
    "realms/ml-platform-study/.well-known/openid-configuration"
)


def main() -> None:
    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    namespace = os.environ.get("OPENMETADATA_NAMESPACE", "ml-platform-data")
    database_pod = primary_database_pod(cluster_name, namespace)
    changed = synchronize_authentication_settings(cluster_name, namespace, database_pod)

    if changed:
        restart_openmetadata(cluster_name, namespace)
        print("OpenMetadata OIDC configuration synchronized and server restarted.")
    else:
        print("OpenMetadata OIDC configuration already synchronized.")


def primary_database_pod(cluster_name: str, namespace: str) -> str:
    result = kubectl(
        cluster_name,
        "get",
        "pod",
        "--namespace",
        namespace,
        "--selector",
        "cnpg.io/cluster=openmetadata-postgres,role=primary",
        "--output=jsonpath={.items[0].metadata.name}",
    )
    pod = result.stdout.strip()
    if not pod:
        raise RuntimeError("could not find the primary openmetadata-postgres pod")
    return pod


def synchronize_authentication_settings(cluster_name: str, namespace: str, database_pod: str) -> bool:
    authority = sql_literal(BROWSER_AUTHORITY)
    discovery_uri = sql_literal(DISCOVERY_URI)
    sql = f"""
WITH changed AS (
  UPDATE openmetadata_settings
  SET json = jsonb_set(
    jsonb_set(json::jsonb, '{{authority}}', to_jsonb('{authority}'::text), true),
    '{{oidcConfiguration,discoveryUri}}', to_jsonb('{discovery_uri}'::text), true
  )::json
  WHERE configtype = 'authenticationConfiguration'
    AND (
      json::jsonb #>> '{{authority}}' IS DISTINCT FROM '{authority}'::text
      OR json::jsonb #>> '{{oidcConfiguration,discoveryUri}}' IS DISTINCT FROM '{discovery_uri}'::text
    )
  RETURNING 1
)
SELECT count(*) FROM changed;
"""
    result = kubectl(
        cluster_name,
        "exec",
        "--namespace",
        namespace,
        database_pod,
        "--",
        "psql",
        "--username=postgres",
        "--dbname=openmetadata",
        "--tuples-only",
        "--no-align",
        "--quiet",
        "--command",
        sql,
    )
    return result.stdout.strip() == "1"


def sql_literal(value: str) -> str:
    return value.replace("'", "''")


def restart_openmetadata(cluster_name: str, namespace: str) -> None:
    kubectl(
        cluster_name,
        "delete",
        "pod",
        "--namespace",
        namespace,
        "--selector",
        "app.kubernetes.io/instance=openmetadata",
        "--wait=true",
    )
    kubectl(
        cluster_name,
        "wait",
        "--timeout=5m",
        "--namespace",
        namespace,
        "deployment/openmetadata",
        "--for=condition=Available",
    )


def kubectl(cluster_name: str, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["kubectl", "--context", f"kind-{cluster_name}", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip() or "no command output"
        raise RuntimeError(f"kubectl {' '.join(args)} failed: {message}")
    return result


if __name__ == "__main__":
    main()
