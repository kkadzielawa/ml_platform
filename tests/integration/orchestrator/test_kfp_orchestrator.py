from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINES_DIR = REPO_ROOT / "clusters/dev/pipelines"
KUSTOMIZATION = PIPELINES_DIR / "kustomization.yaml"
BUDGET = PIPELINES_DIR / "namespace-budget.yaml"
SMOKE = Path(__file__).with_name("smoke_kfp.py")


def test_kfp_overlay_is_pinned_and_removes_development_extras():
    config = yaml.safe_load(KUSTOMIZATION.read_text(encoding="utf-8"))

    assert config["resources"][0] == (
        "https://github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=2.17.0"
    )
    images = {item["name"]: item["newTag"] for item in config["images"]}
    assert images["ghcr.io/kubeflow/kfp-api-server"] == "2.17.0"
    assert images["ghcr.io/kubeflow/kfp-visualization-server"] == "2.17.0"
    assert all(tag != "master" for tag in images.values())

    rendered = KUSTOMIZATION.read_text(encoding="utf-8")
    assert "name: proxy-agent" in rendered
    assert "name: seaweedfs" in rendered
    assert rendered.count("$patch: delete") >= 7


def test_kfp_overlay_uses_garage_and_constrained_namespace_budget():
    config = KUSTOMIZATION.read_text(encoding="utf-8")
    assert "garage-s3.ml-platform-data.svc.cluster.local:3900" in config
    assert "s3://ml-platform-artifacts/projects/ml-platform/artifacts/kfp/v2" in config
    assert "BLOCK_V1_PIPELINES: \"true\"" in config

    assert "providers: |" in config
    assert "forcePathStyle: true" in config
    assert "secretName: mlpipeline-minio-artifact" in config
    assert "s3ForcePathStyle" not in config
    assert "secretKeyKey: secretkey" in config
    assert "name: kfp-launcher" in config
    assert config.count("defaultPipelineRoot:") >= 2
    quota, limits = list(yaml.safe_load_all(BUDGET.read_text(encoding="utf-8")))
    assert quota["kind"] == "ResourceQuota"
    assert quota["metadata"]["namespace"] == "kubeflow"
    assert quota["spec"]["hard"]["requests.cpu"] == "2"
    assert quota["spec"]["hard"]["requests.memory"] == "6Gi"
    assert quota["spec"]["hard"]["limits.cpu"] == "8"
    assert quota["spec"]["hard"]["limits.memory"] == "14Gi"
    assert limits["spec"]["limits"][0]["default"]["memory"] == "1Gi"
    assert limits["kind"] == "LimitRange"


def test_smoke_workflow_contains_two_artifact_passing_components():
    source = SMOKE.read_text(encoding="utf-8")

    assert source.count("@dsl.component") == 2
    assert "source: Input[Artifact]" in source
    assert "artifact: Output[Artifact]" in source
    assert 'pipeline_func=artifact_passing_pipeline' in source
    assert 'pipeline_root=PIPELINE_ROOT' in source
    assert 'parameters.get("message") != message' in source
