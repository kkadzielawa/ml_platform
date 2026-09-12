from __future__ import annotations

import os
import subprocess
from typing import Any


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
    current = read_authentication_settings(cluster_name, namespace, database_pod)
    if current["authority"] == BROWSER_AUTHORITY and current["discovery_uri"] == DISCOVERY_URI:
        return False

    authority = sql_literal(BROWSER_AUTHORITY)
    discovery_uri = sql_literal(DISCOVERY_URI)
    update_sql = f"""
UPDATE openmetadata_settings
SET json = jsonb_set(
  jsonb_set(json::jsonb, '{{authority}}', to_jsonb('{authority}'::text), true),
  '{{oidcConfiguration,discoveryUri}}', to_jsonb('{discovery_uri}'::text), true
)::json
WHERE configtype = 'authenticationConfiguration';
"""
    kubectl_psql(cluster_name, namespace, database_pod, update_sql)
    updated = read_authentication_settings(cluster_name, namespace, database_pod)
    if updated["authority"] != BROWSER_AUTHORITY or updated["discovery_uri"] != DISCOVERY_URI:
        raise RuntimeError("OpenMetadata OIDC settings did not match the requested values after update")
    return True


def read_authentication_settings(cluster_name: str, namespace: str, database_pod: str) -> dict[str, Any]:
    """Read and validate exactly one persisted authentication configuration row."""

    sql = """
SELECT count(*)::text
       || E'\t' || COALESCE(max(json::jsonb #>> '{authority}'), '')
       || E'\t' || COALESCE(max(json::jsonb #>> '{oidcConfiguration,discoveryUri}'), '')
       || E'\t' || COALESCE(bool_and((json::jsonb ? 'authority') AND (json::jsonb ? 'oidcConfiguration')), false)::text
FROM openmetadata_settings
WHERE configtype = 'authenticationConfiguration';
"""
    result = kubectl_psql(cluster_name, namespace, database_pod, sql)
    fields = result.stdout.strip().split("\t")
    if len(fields) != 4:
        raise RuntimeError("OpenMetadata authentication settings query returned an unexpected shape")
    try:
        row_count = int(fields[0])
    except ValueError as exc:
        raise RuntimeError("OpenMetadata authentication settings row count was not numeric") from exc
    if row_count != 1:
        raise RuntimeError(
            "expected exactly one OpenMetadata authenticationConfiguration row; "
            f"found {row_count}"
        )
    if fields[3].lower() != "true":
        raise RuntimeError(
            "OpenMetadata authenticationConfiguration is missing the authority or oidcConfiguration parent"
        )
    return {"authority": fields[1], "discovery_uri": fields[2]}


def kubectl_psql(cluster_name: str, namespace: str, database_pod: str, sql: str) -> subprocess.CompletedProcess[str]:
    return kubectl(
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
        # A cold JVM start can exceed five minutes on the laptop-sized Kind
        # nodes. Keep the operation bounded, but do not report a successful
        # settings migration before the replacement server is actually ready.
        "--timeout=10m",
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
