from __future__ import annotations

import urllib.error

import pytest

from clusters.dev.openmetadata import register_baseline_metadata as registration


def test_register_seed_publishes_quality_result_and_two_lineage_edges(monkeypatch):
    seed = registration.load_seed()
    calls: list[tuple[str, str, dict]] = []

    def fake_put(url: str, token: str, body: dict) -> dict:
        calls.append(("PUT", url, body))
        if "/lineage" in url:
            return body
        name = body.get("name", "entity")
        entity_type = "pipeline" if "/pipelines" in url else "entity"
        return {"id": f"{entity_type}-{name}", "name": name}

    def fake_post(url: str, token: str, body: dict) -> dict:
        calls.append(("POST", url, body))
        if "/testCaseResults/" in url:
            return body
        return {
            "id": "test-case-id",
            "name": body["name"],
            "fullyQualifiedName": (
                f"{seed['table']['databaseSchema']}.{seed['table']['name']}.{body['name']}"
            ),
        }

    def missing_test_case(url: str, token: str) -> dict:
        raise urllib.error.HTTPError(url, 404, "missing", {}, None)

    monkeypatch.setattr(
        registration,
        "ensure_team",
        lambda base_url, token, owner: {"id": "team-id", "name": owner["name"]},
    )
    monkeypatch.setattr(registration, "get_json", missing_test_case)
    monkeypatch.setattr(registration, "put_json", fake_put)
    monkeypatch.setattr(registration, "post_json", fake_post)
    monkeypatch.setattr(registration, "patch_table_owner", lambda *args: {"owners": []})

    responses = registration.register_seed("http://openmetadata/api", "token", seed)

    quality_result_calls = [
        (url, body)
        for method, url, body in calls
        if method == "POST" and "/testCaseResults/" in url
    ]
    assert len(quality_result_calls) == 1
    assert quality_result_calls[0][0].endswith(
        "/testCaseResults/"
        "ml-platform-lakefs.housing-sale-ingestion.curated.housing-sale-features-v0001."
        "housing_sale_features_quality_fixture"
    )
    assert quality_result_calls[0][1]["testCaseStatus"] == "Success"
    assert {item["name"] for item in quality_result_calls[0][1]["testResultValue"]} == {
        "evidence",
        "suite",
        "dataset_revision",
        "run",
    }

    lineage_calls = [
        body
        for method, url, body in calls
        if method == "PUT" and url.endswith("/v1/lineage")
    ]
    assert len(lineage_calls) == 2
    assert all(call["edge"]["toEntity"]["id"].startswith("entity-") for call in lineage_calls)
    assert all(
        call["edge"]["lineageDetails"]["pipeline"]["id"].startswith("pipeline-")
        for call in lineage_calls
    )
    assert all(
        seed["lineage"]["run"] in call["edge"]["lineageDetails"]["description"]
        and seed["lineage"]["commit"] in call["edge"]["lineageDetails"]["description"]
        for call in lineage_calls
    )
    assert responses["quality"]["testCase"]["id"] == "test-case-id"
    test_case_calls = [body for method, url, body in calls if method == "POST" and url.endswith("/testCases")]
    assert test_case_calls[0]["testDefinition"] == seed["quality"]["testCaseName"]
    assert "testSuite" not in test_case_calls[0]


@pytest.mark.parametrize(
    ("value", "expected"),
    [("pass", "Success"), ("fail", "Failed"), ("aborted", "Aborted")],
)
def test_quality_status_is_explicit(value: str, expected: str):
    assert registration.quality_status(value) == expected


def test_quality_status_rejects_an_unmapped_result():
    with pytest.raises(ValueError, match="unsupported quality result"):
        registration.quality_status("unknown")


def test_quality_validation_rejects_missing_evidence():
    with pytest.raises(ValueError, match="evidence"):
        registration.validate_quality(
            {
                "suite": "suite",
                "testCaseName": "case",
                "result": "pass",
                "source": "report.json",
                "observedAt": "2026-08-27T00:00:00Z",
            }
        )


def test_register_quality_reuses_a_matching_result_at_the_fixture_timestamp(monkeypatch):
    seed = registration.load_seed()
    expected_result = registration.quality_result_payload(seed)
    calls: list[tuple[str, str, dict]] = []

    def fake_put(url: str, token: str, body: dict) -> dict:
        calls.append(("PUT", url, body))
        return {"id": "definition-id", "name": body["name"]}

    def existing_test_case(base_url: str, token: str, fqn: str) -> dict:
        return {"id": "test-case-id", "testCaseResult": expected_result}

    monkeypatch.setattr(registration, "put_json", fake_put)
    monkeypatch.setattr(registration, "get_quality_test_case_by_name", existing_test_case)
    monkeypatch.setattr(
        registration,
        "post_json",
        lambda *args: pytest.fail("a matching existing quality result must not be posted again"),
    )

    result = registration.register_quality("http://openmetadata/api", "token", seed)

    assert result["result"] == expected_result
    assert len(calls) == 1
