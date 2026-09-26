# MLflow runbook

Issue `04.02` moves the experiment tracker from the Phase-0 Compose stack into the study
Kubernetes cluster. The route is intentionally small: one MLflow server, one CloudNativePG
database, Garage for artifacts, and an OAuth2 Proxy backed by the existing Keycloak realm.

## Apply and verify

```bash
make apply-mlflow
make test-cluster-mlflow
```

`apply-mlflow` creates the `mlflow-postgres-app`, `mlflow-backend`, and `mlflow-oidc-client`
Secrets from Make variables, applies the server and proxy, registers the OIDC client, and runs a
one-shot explicit recreation of the Phase-0 baseline experiment. It does not copy every old run;
the recreation is the deliberately bounded migration proof for this study issue.

The target checks `platform-data-quota` before creating MLflow workloads. On the study laptop,
OpenMetadata, lakeFS, Garage, and the PostgreSQL clusters can consume most of the local data
namespace quota. The current study quota is 8 CPU and 12 GiB of limits, with roughly 2 CPU of
headroom reserved for MLflow. If the check reports less than that, scale down a service you are
not using for the exercise or raise the local quota, then rerun the target; the target does not
silently evict existing workloads.

The cluster-side resources are in `clusters/dev/mlflow/`. The MLflow server only receives the
artifact-scoped Garage credentials (`artifacts-access-key-id` and
`artifacts-secret-access-key`) from `data-storage-scoped-credentials`. It has no models,
evaluation, raw, or curated bucket credentials.

## Browser access

Keep both port-forwards running:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-data svc/mlflow-auth 15001:4180
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-system svc/keycloak 18081:8080
```

Open `http://127.0.0.1:15001`. An unauthenticated request is redirected to Keycloak. The
pre-created study users are available through the values used by `apply-oidc-fixture` (the
defaults are `oidc-viewer` and `oidc-admin`); the Keycloak bootstrap administrator is a separate
credential. The OIDC callback is bound to `127.0.0.1:15001/oauth2/callback`.

The direct `mlflow` Service is cluster-internal and is not the browser route. The smoke target
temporarily port-forwards it to `15002` so an MLflow SDK client can prove tracking, artifact
download, model registration, and alias lookup without putting an unauthenticated MLflow API on
the host.

## Storage and migration shape

- PostgreSQL database: `mlflow-postgres` / database `mlflow` in `ml-platform-data`.
- Artifact prefix: `s3://ml-platform-artifacts/projects/ml-platform/artifacts/mlflow`.
- OIDC client: `mlflow` in realm `ml-platform-study`.
- Baseline experiment: `housing-sale-baseline-cluster`.
- Baseline registered model: `housing-sale-baseline-cluster`, alias `candidate`.

The recreation Job reads `clusters/dev/mlflow/phase-0-baseline-export.json`, writes that export as
a provenance artifact, and replays its parameters and metrics into the cluster experiment. It is
idempotent at the experiment/model names and is not intended to be a bulk historical export.

## Troubleshooting

Inspect the server, proxy, database, and one-shot jobs:

```bash
kubectl --context kind-ml-platform-study-dev get pods -n ml-platform-data
kubectl --context kind-ml-platform-study-dev logs -n ml-platform-data deployment/mlflow
kubectl --context kind-ml-platform-study-dev logs -n ml-platform-data deployment/mlflow-auth
kubectl --context kind-ml-platform-study-dev logs -n ml-platform-system job/mlflow-oidc-client-registration
kubectl --context kind-ml-platform-study-dev logs -n ml-platform-data job/mlflow-baseline-recreation
```

If an apply is retried, the two Jobs are deleted and recreated by the Make target. If an
unauthenticated request does not redirect, confirm that the Keycloak port-forward is running and
that the proxy's `--login-url` points to `127.0.0.1:18081`. If the baseline Job cannot upload an
artifact, check that Garage and the `data-storage-scoped-credentials` Secret were applied first.

## Non-goals

This local route does not provide MLflow HA, external ingress, bulk Phase-0 history migration,
production secret management, or project-level authorization inside MLflow itself. Artifact
scope is enforced at Garage credentials and the public entrypoint is protected by Keycloak.
