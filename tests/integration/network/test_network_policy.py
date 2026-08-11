from __future__ import annotations

import os
import subprocess
from textwrap import dedent

import pytest


PROJECT_NAMESPACE = "ml-platform-project-housing"
BLOCKED_NAMESPACE = "ml-platform-data"
AGNHOST_IMAGE = (
    "registry.k8s.io/e2e-test-images/agnhost:2.53"
    "@sha256:1c5d47ecd9c4fca235ec0eeb9af0c39d8dd981ae703805a1f23676a9bf47c3bb"
)
CURL_IMAGE = "docker.io/curlimages/curl:8.16.0@sha256:5a91ea0c9c3ee27b4abe657b68cf6bf0676afa13b236b3bda34283cb3924d4f6"


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_NETWORK_POLICY_INTEGRATION") != "1",
    reason="network policy integration tests require a running kind cluster with NetworkPolicy enforcement",
)


@pytest.fixture(scope="module", autouse=True)
def network_policy_fixtures():
    apply_yaml(fixture_manifest())
    wait_for_deployment(PROJECT_NAMESPACE, "network-policy-allowed-server")
    wait_for_deployment(BLOCKED_NAMESPACE, "network-policy-blocked-server")
    wait_for_pod_ready(PROJECT_NAMESPACE, "network-policy-client")
    yield
    kubectl(
        "delete",
        "deployment",
        "network-policy-allowed-server",
        "--namespace",
        PROJECT_NAMESPACE,
        "--ignore-not-found=true",
    )
    kubectl(
        "delete",
        "service",
        "network-policy-allowed",
        "--namespace",
        PROJECT_NAMESPACE,
        "--ignore-not-found=true",
    )
    kubectl(
        "delete",
        "pod",
        "network-policy-client",
        "--namespace",
        PROJECT_NAMESPACE,
        "--ignore-not-found=true",
    )
    kubectl(
        "delete",
        "deployment",
        "network-policy-blocked-server",
        "--namespace",
        BLOCKED_NAMESPACE,
        "--ignore-not-found=true",
    )
    kubectl(
        "delete",
        "service",
        "network-policy-blocked",
        "--namespace",
        BLOCKED_NAMESPACE,
        "--ignore-not-found=true",
    )


def test_allowed_project_service_traffic_succeeds_and_dns_resolves():
    result = exec_from_client(
        "curl",
        "-sfS",
        "--max-time",
        "5",
        "http://network-policy-allowed.ml-platform-project-housing.svc.cluster.local:8080/hostname",
    )

    assert result.returncode == 0, result.stderr
    assert "network-policy-allowed-server" in result.stdout


def test_unlisted_cross_namespace_request_fails():
    result = exec_from_client(
        "curl",
        "-sfS",
        "--connect-timeout",
        "2",
        "--max-time",
        "5",
        "http://network-policy-blocked.ml-platform-data.svc.cluster.local:8080/hostname",
        check=False,
    )

    assert result.returncode != 0, "cross-namespace request unexpectedly succeeded"


def exec_from_client(*command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return kubectl(
        "exec",
        "network-policy-client",
        "--namespace",
        PROJECT_NAMESPACE,
        "--",
        *command,
        check=check,
    )


def apply_yaml(manifest: str) -> None:
    subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", "apply", "-f", "-"],
        input=manifest,
        check=True,
        text=True,
    )


def wait_for_deployment(namespace: str, name: str) -> None:
    kubectl(
        "wait",
        "--timeout=3m",
        "--namespace",
        namespace,
        f"deployment/{name}",
        "--for=condition=Available",
    )


def wait_for_pod_ready(namespace: str, name: str) -> None:
    kubectl(
        "wait",
        "--timeout=3m",
        "--namespace",
        namespace,
        f"pod/{name}",
        "--for=condition=Ready",
    )


def kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", f"kind-{kind_cluster_name()}", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def kind_cluster_name() -> str:
    return os.environ.get("KIND_CLUSTER_NAME", "ml-platform-study-dev")


def fixture_manifest() -> str:
    return dedent(
        f"""
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: network-policy-allowed-server
          namespace: {PROJECT_NAMESPACE}
          labels:
            app.kubernetes.io/name: network-policy-allowed-server
        spec:
          replicas: 1
          selector:
            matchLabels:
              app.kubernetes.io/name: network-policy-allowed-server
          template:
            metadata:
              labels:
                app.kubernetes.io/name: network-policy-allowed-server
            spec:
              containers:
                - name: agnhost
                  image: {AGNHOST_IMAGE}
                  args:
                    - netexec
                    - --http-port=8080
                  ports:
                    - name: http
                      containerPort: 8080
                  resources:
                    requests:
                      cpu: 10m
                      memory: 32Mi
                    limits:
                      cpu: 100m
                      memory: 128Mi
        ---
        apiVersion: v1
        kind: Service
        metadata:
          name: network-policy-allowed
          namespace: {PROJECT_NAMESPACE}
        spec:
          selector:
            app.kubernetes.io/name: network-policy-allowed-server
          ports:
            - name: http
              port: 8080
              targetPort: http
        ---
        apiVersion: v1
        kind: Pod
        metadata:
          name: network-policy-client
          namespace: {PROJECT_NAMESPACE}
          labels:
            app.kubernetes.io/name: network-policy-client
        spec:
          containers:
            - name: curl
              image: {CURL_IMAGE}
              command:
                - sh
                - -c
                - sleep 3600
              resources:
                requests:
                  cpu: 10m
                  memory: 32Mi
                limits:
                  cpu: 100m
                  memory: 128Mi
        ---
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: network-policy-blocked-server
          namespace: {BLOCKED_NAMESPACE}
          labels:
            app.kubernetes.io/name: network-policy-blocked-server
        spec:
          replicas: 1
          selector:
            matchLabels:
              app.kubernetes.io/name: network-policy-blocked-server
          template:
            metadata:
              labels:
                app.kubernetes.io/name: network-policy-blocked-server
            spec:
              containers:
                - name: agnhost
                  image: {AGNHOST_IMAGE}
                  args:
                    - netexec
                    - --http-port=8080
                  ports:
                    - name: http
                      containerPort: 8080
                  resources:
                    requests:
                      cpu: 10m
                      memory: 32Mi
                    limits:
                      cpu: 100m
                      memory: 128Mi
        ---
        apiVersion: v1
        kind: Service
        metadata:
          name: network-policy-blocked
          namespace: {BLOCKED_NAMESPACE}
        spec:
          selector:
            app.kubernetes.io/name: network-policy-blocked-server
          ports:
            - name: http
              port: 8080
              targetPort: http
        """
    )
