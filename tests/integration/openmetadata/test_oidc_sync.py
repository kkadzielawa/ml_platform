from __future__ import annotations

import subprocess

import pytest

from clusters.dev.openmetadata import sync_oidc_configuration as sync


def completed(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["kubectl"], returncode=0, stdout=stdout, stderr="")


def test_oidc_sync_noops_only_after_reading_matching_persisted_values(monkeypatch):
    calls: list[str] = []

    def fake_psql(cluster: str, namespace: str, pod: str, sql: str):
        calls.append(sql)
        return completed(
            "1\thttp://127.0.0.1:18081/realms/ml-platform-study\t"
            "http://openmetadata-oidc-discovery-adapter.ml-platform-data.svc.cluster.local:8080/"
            "realms/ml-platform-study/.well-known/openid-configuration\ttrue\n"
        )

    monkeypatch.setattr(sync, "kubectl_psql", fake_psql)

    assert sync.synchronize_authentication_settings("dev", "data", "postgres-0") is False
    assert len(calls) == 1
    assert "UPDATE openmetadata_settings" not in calls[0]


def test_oidc_sync_rejects_missing_or_duplicate_configuration_rows(monkeypatch):
    monkeypatch.setattr(
        sync,
        "kubectl_psql",
        lambda *args: completed("0\t\t\tfalse\n"),
    )

    with pytest.raises(RuntimeError, match="exactly one"):
        sync.synchronize_authentication_settings("dev", "data", "postgres-0")


def test_oidc_sync_updates_then_reads_back_changed_values(monkeypatch):
    calls: list[str] = []
    rows = iter(
        [
            "1\told-authority\told-discovery\ttrue\n",
            "1\thttp://127.0.0.1:18081/realms/ml-platform-study\t"
            "http://openmetadata-oidc-discovery-adapter.ml-platform-data.svc.cluster.local:8080/"
            "realms/ml-platform-study/.well-known/openid-configuration\ttrue\n",
        ]
    )

    def fake_psql(cluster: str, namespace: str, pod: str, sql: str):
        calls.append(sql)
        if sql.lstrip().startswith("UPDATE"):
            return completed("")
        return completed(next(rows))

    monkeypatch.setattr(sync, "kubectl_psql", fake_psql)

    assert sync.synchronize_authentication_settings("dev", "data", "postgres-0") is True
    assert len(calls) == 3
    assert "UPDATE openmetadata_settings" in calls[1]


def test_oidc_sync_rejects_a_failed_read_back(monkeypatch):
    rows = iter(
        [
            "1\told-authority\told-discovery\ttrue\n",
            "1\told-authority\told-discovery\ttrue\n",
        ]
    )

    def fake_psql(cluster: str, namespace: str, pod: str, sql: str):
        if sql.lstrip().startswith("UPDATE"):
            return completed("")
        return completed(next(rows))

    monkeypatch.setattr(sync, "kubectl_psql", fake_psql)

    with pytest.raises(RuntimeError, match="did not match"):
        sync.synchronize_authentication_settings("dev", "data", "postgres-0")


def test_restart_waits_for_a_bounded_cold_start(monkeypatch):
    calls: list[tuple[str, ...]] = []

    def fake_kubectl(cluster: str, *args: str):
        calls.append(args)
        return completed("")

    monkeypatch.setattr(sync, "kubectl", fake_kubectl)

    sync.restart_openmetadata("dev", "data")

    assert calls[0] == (
        "delete",
        "pod",
        "--namespace",
        "data",
        "--selector",
        "app.kubernetes.io/instance=openmetadata",
        "--wait=true",
    )
    assert "--timeout=10m" in calls[1]
