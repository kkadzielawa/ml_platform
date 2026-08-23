from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_DIR = REPO_ROOT / "platform" / "policies" / "supply-chain"
KYVERNO_VALUES = REPO_ROOT / "platform" / "charts" / "kyverno" / "values-dev-kind.yaml"
PROJECT_NAMESPACE = "ml-platform-project-housing"
KIND_CONTEXT = f"kind-{os.environ.get('KIND_CLUSTER_NAME', 'ml-platform-study-dev')}"


def load_yaml_documents(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def kubectl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", KIND_CONTEXT, *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def pod_manifest(name: str, image: str) -> str:
    return f"""
apiVersion: v1
kind: Pod
metadata:
  name: {name}
  namespace: {PROJECT_NAMESPACE}
spec:
  restartPolicy: Never
  containers:
    - name: main
      image: {image}
      command: ["sh", "-c", "sleep 1"]
      resources:
        requests:
          cpu: 10m
          memory: 32Mi
        limits:
          cpu: 50m
          memory: 64Mi
"""


def kubectl_apply_stdin(manifest: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--context", KIND_CONTEXT, "apply", "--dry-run=server", "-f", "-"],
        input=manifest,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_kyverno_values_are_pinned_for_local_kind() -> None:
    values = yaml.safe_load(KYVERNO_VALUES.read_text(encoding="utf-8"))

    assert values["admissionController"]["replicas"] == 1
    assert values["backgroundController"]["enabled"] is False
    assert values["cleanupController"]["enabled"] is False
    assert values["reportsController"]["enabled"] is False
    assert values["features"]["policyExceptions"]["enabled"] is True
    assert values["features"]["policyExceptions"]["namespace"] == "*"


def test_project_policy_enforces_signed_image_verification() -> None:
    policy = load_yaml_documents(POLICY_DIR / "verify-project-images.yaml")[0]
    rule = policy["spec"]["rules"][0]
    verification = rule["verifyImages"][0]
    key_entry = verification["attestors"][0]["entries"][0]["keys"]

    assert policy["kind"] == "ClusterPolicy"
    assert policy["spec"]["validationFailureAction"] == "Enforce"
    assert policy["spec"]["failurePolicy"] == "Fail"
    assert rule["match"]["any"][0]["resources"]["namespaceSelector"]["matchLabels"] == {
        "ml-platform.local/namespace-class": "project"
    }
    assert verification["imageReferences"] == ["ghcr.io/kyverno/test-verify-image*"]
    assert verification["required"] is True
    assert verification["verifyDigest"] is True
    assert "BEGIN PUBLIC KEY" in key_entry["publicKeys"]
    assert key_entry["rekor"]["ignoreTlog"] is True


def test_platform_namespaces_are_documented_as_audit_rollout() -> None:
    policy = load_yaml_documents(POLICY_DIR / "platform-rollout-mode.yaml")[0]

    assert policy["spec"]["validationFailureAction"] == "Audit"
    assert policy["metadata"]["annotations"]["ml-platform.local/rollout-mode"] == "audit-platform-namespaces"


def test_policy_exception_requires_expiry_annotation() -> None:
    policy = load_yaml_documents(POLICY_DIR / "policy-exception-expiry.yaml")[0]
    rules = {rule["name"]: rule for rule in policy["spec"]["rules"]}

    assert policy["spec"]["validationFailureAction"] == "Enforce"
    assert "require-expires-on-annotation" in rules
    assert "require-expires-on-date-shape" in rules
    assert (
        rules["require-expires-on-annotation"]["validate"]["pattern"]["metadata"]["annotations"][
            "ml-platform.local/expires-on"
        ]
        == "?*"
    )


@pytest.mark.skipif(
    os.environ.get("RUN_ADMISSION_INTEGRATION") != "1",
    reason="set RUN_ADMISSION_INTEGRATION=1 to exercise a live kind cluster",
)
def test_live_admission_allows_signed_and_rejects_unsigned_images() -> None:
    signed = kubectl_apply_stdin(
        pod_manifest("admission-signed-allow", "ghcr.io/kyverno/test-verify-image:signed")
    )
    assert "pod/admission-signed-allow created" in signed.stdout

    unsigned = kubectl_apply_stdin(
        pod_manifest("admission-unsigned-deny", "ghcr.io/kyverno/test-verify-image:unsigned"),
        check=False,
    )
    combined = f"{unsigned.stdout}\n{unsigned.stderr}"

    assert unsigned.returncode != 0
    assert "verify-project-signed-images" in combined
    assert any(
        message in combined
        for message in [
            "signature not found",
            "image verification failed",
            "no matching signatures",
        ]
    )


@pytest.mark.skipif(
    os.environ.get("RUN_ADMISSION_INTEGRATION") != "1",
    reason="set RUN_ADMISSION_INTEGRATION=1 to exercise a live kind cluster",
)
def test_live_policy_exception_without_expiry_is_rejected() -> None:
    manifest = """
apiVersion: kyverno.io/v2
kind: PolicyException
metadata:
  name: missing-expiry
  namespace: ml-platform-project-housing
spec:
  exceptions:
    - policyName: verify-project-signed-images
      ruleNames:
        - verify-kyverno-test-image-signature
  match:
    any:
      - resources:
          kinds:
            - Pod
          names:
            - unsigned-exception-test
"""
    result = kubectl_apply_stdin(manifest, check=False)
    combined = f"{result.stdout}\n{result.stderr}"

    assert result.returncode != 0
    assert "ml-platform.local/expires-on" in combined
