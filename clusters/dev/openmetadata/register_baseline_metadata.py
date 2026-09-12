from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPO_ROOT / "clusters/dev/openmetadata/catalog-seed-configmap.yaml"


def main() -> None:
    with local_openmetadata_session() as session:
        seed = load_seed()
        responses = register_seed(session.base_url, session.token, seed)
    print(json.dumps({"registered": sorted(responses)}, sort_keys=True))


def load_seed() -> dict[str, Any]:
    content = SEED_PATH.read_text(encoding="utf-8")
    marker = "  baseline-catalog.json: |\n"
    payload = content.split(marker, 1)[1]
    lines = [line[4:] if line.startswith("    ") else line for line in payload.splitlines()]
    return json.loads("\n".join(lines))


def register_seed(base_url: str, token: str, seed: dict[str, Any]) -> dict[str, Any]:
    service = seed["service"]
    database = seed["database"]
    schema = seed["schema"]
    table = seed["table"]
    owner = ensure_team(base_url, token, seed["owner"])

    responses = {
        "team": owner,
        "service": put_json(
            f"{base_url}/v1/services/databaseServices",
            token,
            {
                "name": service["name"],
                "serviceType": service["serviceType"],
                "description": service["description"],
                "connection": {"config": {"type": service["serviceType"]}},
            },
        ),
        "database": put_json(
            f"{base_url}/v1/databases",
            token,
            {
                "name": database["name"],
                "service": database["service"],
                "description": database["description"],
                "retentionPeriod": "P365D",
            },
        ),
        "schema": put_json(
            f"{base_url}/v1/databaseSchemas",
            token,
            {
                "name": schema["name"],
                "database": schema["database"],
                "description": schema["description"],
                "retentionPeriod": "P365D",
            },
        ),
        "rawSchema": put_json(
            f"{base_url}/v1/databaseSchemas",
            token,
            {
                "name": seed["rawSchema"]["name"],
                "database": seed["rawSchema"]["database"],
                "description": seed["rawSchema"]["description"],
                "retentionPeriod": "P365D",
            },
        ),
        "table": put_json(
            f"{base_url}/v1/tables",
            token,
            table,
        ),
    }
    responses["rawTables"] = [
        put_json(f"{base_url}/v1/tables", token, raw_table)
        for raw_table in seed["rawTables"]
    ]
    responses["tableOwner"] = patch_table_owner(base_url, token, table, owner)
    responses["pipelineService"] = put_json(
        f"{base_url}/v1/services/pipelineServices",
        token,
        {
            "name": seed["pipelineService"]["name"],
            "serviceType": seed["pipelineService"]["serviceType"],
            "description": seed["pipelineService"]["description"],
            "connection": {"config": {"type": seed["pipelineService"]["serviceType"]}},
        },
    )
    responses["pipeline"] = put_json(
        f"{base_url}/v1/pipelines",
        token,
        seed["pipeline"],
    )
    responses["quality"] = register_quality(base_url, token, seed)
    responses["lineage"] = register_lineage(base_url, token, seed, responses)
    return responses


def ensure_team(base_url: str, token: str, owner: dict[str, str]) -> dict[str, Any]:
    name = owner["name"]
    try:
        return get_json(f"{base_url}/v1/teams/name/{urllib.parse.quote(name, safe='')}", token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise

    return post_json(
        f"{base_url}/v1/teams",
        token,
        {
            "name": name,
            "displayName": name,
            "teamType": "Group",
            "description": "Study platform learners that own exploratory ML platform datasets.",
        },
    )


def get_table_by_name(base_url: str, token: str, fqn: str, *, fields: str | None = None) -> dict[str, Any]:
    query = f"?fields={urllib.parse.quote(fields, safe=',')}" if fields else ""
    return get_json(f"{base_url}/v1/tables/name/{urllib.parse.quote(fqn, safe='')}{query}", token)


def patch_table_owner(base_url: str, token: str, table: dict[str, Any], owner: dict[str, Any]) -> dict[str, Any]:
    fqn = f"{table['databaseSchema']}.{table['name']}"
    current_table = get_table_by_name(base_url, token, fqn, fields="owners")
    operation = "replace" if "owners" in current_table else "add"
    return patch_json(
        f"{base_url}/v1/tables/name/{urllib.parse.quote(fqn, safe='')}?changeSource=Automated",
        token,
        [
            {
                "op": operation,
                "path": "/owners",
                "value": [
                    {
                        "id": owner["id"],
                        "type": "team",
                        "name": owner["name"],
                    }
                ],
            }
        ],
    )


def register_quality(
    base_url: str,
    token: str,
    seed: dict[str, Any],
) -> dict[str, Any]:
    """Register the fixture quality result as a retrievable OpenMetadata test case."""

    quality = seed["quality"]
    validate_quality(quality)
    table = seed["table"]
    table_fqn = table_fully_qualified_name(table)
    definition = put_json(
        f"{base_url}/v1/dataQuality/testDefinitions",
        token,
        {
            "name": quality["testCaseName"],
            "displayName": "Housing sale features quality fixture",
            "description": (
                "Records the result produced by the local housing-sale quality route. "
                "This 03.10 seed is explicitly a fixture until a measured report is supplied."
            ),
            "entityType": "TABLE",
            "testPlatforms": ["Other"],
            "parameterDefinition": [],
        },
    )
    test_case_fqn = f"{table_fqn}.{quality['testCaseName']}"
    try:
        test_case = get_quality_test_case_by_name(base_url, token, test_case_fqn)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        test_case = post_json(
            f"{base_url}/v1/dataQuality/testCases",
            token,
            {
                "entityLink": f"<#E::table::{table_fqn}>",
                "name": quality["testCaseName"],
                "testDefinition": entity_fully_qualified_name(definition),
                "parameterValues": [],
            },
        )

    result_payload = quality_result_payload(seed)
    existing_result = test_case.get("testCaseResult")
    if existing_result and existing_result.get("timestamp") == result_payload["timestamp"]:
        validate_existing_quality_result(existing_result, result_payload)
        result = existing_result
    else:
        result = post_json(
            f"{base_url}/v1/dataQuality/testCases/testCaseResults/{urllib.parse.quote(test_case_fqn, safe='')}",
            token,
            result_payload,
        )
    return {
        "definition": definition,
        "suiteName": quality["suite"],
        "testCase": test_case,
        "result": result,
    }


def register_lineage(
    base_url: str,
    token: str,
    seed: dict[str, Any],
    responses: dict[str, Any],
) -> list[dict[str, Any]]:
    """Register raw-to-curated edges and attach the local ingestion pipeline."""

    pipeline = responses["pipeline"]
    curated_table = responses["table"]
    output_uri = seed["lineage"]["outputs"][0]
    registered: list[dict[str, Any]] = []
    for raw_table, input_uri in zip(seed["rawTables"], seed["lineage"]["inputs"], strict=True):
        raw_response = next(
            item for item in responses["rawTables"] if item.get("name") == raw_table["name"]
        )
        registered.append(
            put_json(
                f"{base_url}/v1/lineage",
                token,
                {
                    "edge": {
                        "fromEntity": entity_reference(raw_response, "table"),
                        "toEntity": entity_reference(curated_table, "table"),
                        "lineageDetails": {
                            "description": (
                                f"run={seed['lineage']['run']}; commit={seed['lineage']['commit']}; "
                                f"input={input_uri}; output={output_uri}"
                            ),
                            "pipeline": entity_reference(pipeline, "pipeline"),
                            "source": "OpenLineage",
                            "createdAt": timestamp_millis(seed["quality"]["observedAt"]),
                            "createdBy": "study",
                        },
                    }
                },
            )
        )
    return registered


def get_quality_test_case_by_name(base_url: str, token: str, fqn: str) -> dict[str, Any]:
    return get_json(
        f"{base_url}/v1/dataQuality/testCases/name/{urllib.parse.quote(fqn, safe='')}?fields=testCaseResult,testDefinition,testSuite",
        token,
    )


def get_lineage_by_name(
    base_url: str,
    token: str,
    fqn: str,
    *,
    upstream_depth: int = 3,
    downstream_depth: int = 1,
) -> dict[str, Any]:
    return get_json(
        f"{base_url}/v1/lineage/table/name/{urllib.parse.quote(fqn, safe='')}"
        f"?upstreamDepth={upstream_depth}&downstreamDepth={downstream_depth}",
        token,
    )


def table_fully_qualified_name(table: dict[str, Any]) -> str:
    return f"{table['databaseSchema']}.{table['name']}"


def entity_reference(entity: dict[str, Any], entity_type: str) -> dict[str, str]:
    if not entity.get("id"):
        raise RuntimeError(f"OpenMetadata {entity_type} response did not contain an id")
    reference = {"id": str(entity["id"]), "type": entity_type}
    if entity.get("name"):
        reference["name"] = str(entity["name"])
    return reference


def entity_fully_qualified_name(entity: dict[str, Any]) -> str:
    name = entity.get("fullyQualifiedName") or entity.get("name")
    if not name:
        raise RuntimeError("OpenMetadata response did not contain a fully qualified name or name")
    return str(name)


def quality_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "pass":
        return "Success"
    if normalized == "fail":
        return "Failed"
    if normalized == "aborted":
        return "Aborted"
    raise ValueError(f"unsupported quality result: {value!r}")


def validate_quality(quality: dict[str, Any]) -> None:
    required = {"suite", "testCaseName", "result", "source", "evidence", "observedAt"}
    missing = sorted(field for field in required if not quality.get(field))
    if missing:
        raise ValueError(f"quality report is missing required fields: {', '.join(missing)}")
    quality_status(str(quality["result"]))


def quality_result_payload(seed: dict[str, Any]) -> dict[str, Any]:
    quality = seed["quality"]
    return {
        "result": f"Fixture quality result: {quality['result']} (source={quality['source']})",
        "testCaseStatus": quality_status(quality["result"]),
        "timestamp": timestamp_millis(quality["observedAt"]),
        "testResultValue": [
            {"name": "evidence", "value": quality["evidence"]},
            {"name": "suite", "value": quality["suite"]},
            {"name": "dataset_revision", "value": seed["lineage"]["commit"]},
            {"name": "run", "value": seed["lineage"]["run"]},
        ],
    }


def validate_existing_quality_result(existing: dict[str, Any], expected: dict[str, Any]) -> None:
    if existing.get("testCaseStatus") != expected["testCaseStatus"]:
        raise RuntimeError("existing quality result at the fixture timestamp has a different status")
    existing_values = {
        item.get("name"): item.get("value") for item in existing.get("testResultValue", [])
    }
    expected_values = {item["name"]: item["value"] for item in expected["testResultValue"]}
    if existing_values != expected_values:
        raise RuntimeError("existing quality result at the fixture timestamp has different evidence")


def timestamp_millis(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


class OpenMetadataSession:
    def __init__(self, *, base_url: str, token: str) -> None:
        self.base_url = base_url
        self.token = token


@contextmanager
def local_openmetadata_session():
    token = os.environ.get("OPENMETADATA_JWT_TOKEN")
    base_url = os.environ.get("OPENMETADATA_URL")
    if token and base_url:
        yield OpenMetadataSession(base_url=base_url.rstrip("/"), token=token)
        return

    cluster_name = os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")
    keycloak_namespace = os.environ.get("KEYCLOAK_NAMESPACE", "ml-platform-system")
    openmetadata_namespace = os.environ.get("OPENMETADATA_NAMESPACE", "ml-platform-data")
    keycloak_port = int(os.environ.get("KEYCLOAK_PORT", "18081"))
    openmetadata_port = int(os.environ.get("OPENMETADATA_PORT", "8585"))

    with (
        port_forward(cluster_name, keycloak_namespace, "svc/keycloak", keycloak_port, 8080),
        port_forward(cluster_name, openmetadata_namespace, "svc/openmetadata", openmetadata_port, 8585),
    ):
        yield OpenMetadataSession(
            base_url=f"http://127.0.0.1:{openmetadata_port}/api",
            token=keycloak_token(cluster_name, openmetadata_namespace, keycloak_port),
        )


def keycloak_token(cluster_name: str, openmetadata_namespace: str, keycloak_port: int) -> str:
    client = read_secret(cluster_name, openmetadata_namespace, "openmetadata-oidc-client")
    password = os.environ.get("OPENMETADATA_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError(
            "OPENMETADATA_ADMIN_PASSWORD is required for the local Keycloak token flow; "
            "use make test-openmetadata or provide it explicitly"
        )
    response = post_form(
        f"http://127.0.0.1:{keycloak_port}/realms/ml-platform-study/protocol/openid-connect/token",
        {
            "grant_type": "password",
            "client_id": "openmetadata",
            "client_secret": client["clientSecret"],
            "username": os.environ.get("OPENMETADATA_ADMIN_USERNAME", "admin"),
            "password": password,
        },
    )
    return str(response["access_token"])


def put_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata PUT {url} failed with HTTP {exc.code}: {detail}") from exc
    if not body.strip():
        return {}
    parsed = json.loads(body)
    assert isinstance(parsed, dict)
    return parsed


def post_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata POST {url} failed with HTTP {exc.code}: {detail}") from exc
    assert isinstance(parsed, dict)
    return parsed


def patch_json(url: str, token: str, body: Any) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json-patch+json"},
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenMetadata PATCH {url} failed with HTTP {exc.code}: {detail}") from exc
    assert isinstance(parsed, dict)
    return parsed


def get_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=auth_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


@contextmanager
def port_forward(cluster_name: str, namespace: str, resource: str, local_port: int, remote_port: int):
    process = subprocess.Popen(
        [
            "kubectl",
            "--context",
            f"kind-{cluster_name}",
            "port-forward",
            "--namespace",
            namespace,
            resource,
            f"{local_port}:{remote_port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_local_port(local_port)
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_local_port(port: int) -> None:
    for _ in range(80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.5)
    raise TimeoutError(f"port-forward did not open 127.0.0.1:{port}")


def read_secret(cluster_name: str, namespace: str, name: str) -> dict[str, str]:
    result = subprocess.run(
        [
            "kubectl",
            "--context",
            f"kind-{cluster_name}",
            "get",
            "secret",
            name,
            "--namespace",
            namespace,
            "-o",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    import base64

    return {key: base64.b64decode(value).decode("utf-8") for key, value in payload["data"].items()}


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


if __name__ == "__main__":
    main()
