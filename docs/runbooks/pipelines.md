# Kubeflow Pipelines runbook

Issue `04.03.a` installs Kubeflow Pipelines (KFP) standalone, not the full
Kubeflow distribution. It provides a local control plane for compiling,
submitting, observing, and retrying containerized pipelines.

## Apply and verify

```bash
make apply-orchestrator
make test-orchestrator
```

The apply target pins the upstream KFP source to Git tag `2.17.0`, installs
its required CRDs, copies only the existing Garage artifact-scoped credentials
into the `kubeflow` namespace, and applies the local overlay. The overlay
removes KFP's development host-network proxy and SeaweedFS deployment.

The test target compiles and submits a two-container pipeline. The first task
writes a message artifact, the second reads and verifies it. The test then
checks the run parameter through the KFP API and checks that artifacts exist
under the Garage prefix.

## Browser access

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n kubeflow svc/ml-pipeline-ui 18085:80
```

Open <http://127.0.0.1:18085>. The `04-03-orchestrator-smoke` experiment and
its runs appear there after the smoke test.

Standalone KFP does not provide multi-user authentication or authorization.
For that reason this study route has no Gateway, Ingress, NodePort, or
host-network exposure: use only a local `kubectl port-forward`. A future
production route must either use a full Kubeflow distribution or add an
authenticated boundary with project authorization.

## Storage and resource boundaries

- KFP metadata, cache, and run records use the upstream single-node MySQL
  deployment in the `kubeflow` namespace.
- Pipeline artifacts and archived logs use Garage bucket
  `ml-platform-artifacts`, prefix
  `projects/ml-platform/artifacts/kfp/`.
- The namespace is limited to 2 CPU / 6 GiB of requests and 8 CPU / 14 GiB of
  limits. This is a study budget, not a production capacity plan.

If the laptop becomes constrained, pause unrelated study services before
applying KFP. The KFP namespace quota prevents this control plane from
growing without bound, but it cannot make all platform stacks fit on a
single physical laptop simultaneously.

## Troubleshooting

```bash
kubectl --context kind-ml-platform-study-dev get pods -n kubeflow
kubectl --context kind-ml-platform-study-dev get workflows -n kubeflow
kubectl --context kind-ml-platform-study-dev logs -n kubeflow deployment/ml-pipeline
kubectl --context kind-ml-platform-study-dev logs -n kubeflow deployment/workflow-controller
```

If a workflow cannot store artifacts, confirm the Garage service and the
KFP-local credential copy:

```bash
kubectl --context kind-ml-platform-study-dev get secret   mlpipeline-minio-artifact -n kubeflow
kubectl --context kind-ml-platform-study-dev get configmap   workflow-controller-configmap -n kubeflow -o yaml
```

## Non-goals

This route does not add KFP multi-tenancy, a public endpoint, OIDC integration,
high availability, production database operations, or the classic-ML pipeline
itself. Those are separate follow-up issues.
