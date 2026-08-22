# Unexpected errors and resolutions

This note records surprising local failures encountered while building the study platform. These are not formal ADRs; they are field notes for debugging and learning.

## MLflow rejected Docker service hostnames

### Symptom

Training or serving failed when MLflow was addressed through the Docker Compose service name:

```text
Invalid Host header - possible DNS rebinding attack detected
```

### Cause

MLflow rejected requests whose Host header used the internal Docker DNS name, such as `mlflow:5000`.

### Resolution

For Phase 0 local workflows, route MLflow clients through localhost from the host network:

```text
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
```

The Dockerized training, service smoke tests, and manual baseline-serving path use host networking for this reason.

## Docker Compose did not see Makefile defaults

### Symptom

Running Compose directly failed with missing variables:

```text
required variable POSTGRES_USER is missing a value
```

### Cause

The local defaults live in `Makefile` exports. `docker compose` does not read Makefile defaults when invoked directly from the shell.

### Resolution

Prefer Make targets for local workflows:

```bash
make compose-up-mlflow
BASELINE_MODEL_VERSION=3 make serve-baseline
```

If direct Compose usage is needed later, add a reviewed `.env` strategy rather than relying on manual shell exports.

## FastAPI prediction returned 500

### Symptom

`/healthz` and `/metadata` worked, but `/predict` returned:

```text
500 Internal Server Error
```

### Cause

Prediction lazily loaded the MLflow model on first request. Model loading contacted MLflow through the rejected internal hostname and hit the same Host-header protection as training.

### Resolution

Run the manual baseline-serving container with host networking and localhost MLflow/Garage endpoints:

```text
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_S3_ENDPOINT_URL=http://127.0.0.1:3900
```

The fixed `make serve-baseline` target also waits for `/healthz` before printing endpoint instructions.

## kind worker join failed with kubeadm

### Symptom

kind failed while joining worker nodes:

```text
failed to join node with kubeadm
[preflight] found NodeName empty; using OS hostname as NodeName
```

The NodeName line was misleading; it was only informational.

### Actual cause

Retained kind node logs showed kubelet repeatedly crashing:

```text
error creating fsnotify watcher: too many open files
inotify_init: too many open files
Failed to start cAdvisor
kubelet.service: Failed with result 'exit-code'
```

The host shell had a high file limit, but Docker containers had:

```text
ulimit -n = 1024
```

That was too low for the Kubernetes `v1.34.0` worker kubelet/cAdvisor path on this laptop.

### Resolution

Raise Docker's default container `nofile` limit in `/etc/docker/daemon.json`, then restart Docker:

```json
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Soft": 1048576,
      "Hard": 1048576
    }
  }
}
```

Validate with:

```bash
docker run --rm ghcr.io/mlflow/mlflow:v3.13.0 sh -lc 'ulimit -n'
```

Expected:

```text
1048576
```

## kind workers briefly reported NotReady

### Symptom

Immediately after cluster creation, status failed:

```text
ml-platform-study-dev-worker    NotReady
ml-platform-study-dev-worker2   NotReady
error: not all nodes are Ready
```

### Cause

The workers had joined, but CNI/kubelet readiness had not fully settled yet. They became Ready shortly afterward.

### Resolution

The cluster scripts now wait for all nodes to become Ready:

```bash
kubectl --context kind-ml-platform-study-dev wait node --all --for=condition=Ready --timeout=180s
```

This makes:

```bash
make cluster-create && make cluster-status
```

stable instead of timing-sensitive.

## Argo CD apply was blocked by a broken kind worker

### Symptom

During `02.08.a`, `make apply-gitops` repeatedly failed before Argo CD could finish installing. The visible failure came from the Envoy Gateway Helm dependency:

```text
UPGRADE FAILED: pre-upgrade hooks failed
job eg-gateway-helm-certgen failed: BackoffLimitExceeded
```

Other platform pods on the same worker showed DNS or service-connection failures, including Keycloak failing to reach Postgres and Harbor components failing to resolve peer services.

### Cause

The Argo CD manifests were not the root cause. One kind worker was unhealthy:

```text
ml-platform-study-dev-worker2
  kube-proxy: CrashLoopBackOff
```

The kube-proxy log showed:

```text
failed complete: too many open files
```

Because kube-proxy programs Kubernetes Service networking on each node, pods scheduled onto that worker could be alive while cluster Service routing was broken. Helm hook jobs for Envoy Gateway kept landing on the bad worker and failed there.

### Resolution

Restarting the Docker node container helped some pods but did not fix kube-proxy:

```bash
docker restart ml-platform-study-dev-worker2
```

Cordoning the worker avoided new pods, but it made the existing cluster-status script fail because the node reported `Ready,SchedulingDisabled`.

The practical workaround was to keep the node `Ready` while steering generic new pods away from it with a `NoSchedule` taint:

```bash
kubectl --context kind-ml-platform-study-dev taint node ml-platform-study-dev-worker2 ml-platform.local/workload-class=ml:NoSchedule --overwrite
```

Then roll back the failed Envoy Gateway Helm release metadata and rerun the apply:

```bash
helm rollback eg 10 -n ml-platform-system --wait --timeout 5m
make apply-gitops
```

After the taint, the Envoy Gateway hook scheduled onto the healthy worker, the dependency chain completed, and Argo CD installed successfully.

### Follow-up

The taint is acceptable as a local lab workaround, but the worker should be repaired or the kind cluster recreated before relying on the `ml` worker for later heavier workloads.

Useful checks:

```bash
kubectl --context kind-ml-platform-study-dev get pods -n kube-system -o wide
kubectl --context kind-ml-platform-study-dev logs -n kube-system -l k8s-app=kube-proxy --tail=80 --prefix=true
kubectl --context kind-ml-platform-study-dev get events -n ml-platform-system --sort-by=.metadata.creationTimestamp
```


## Kubernetes admission policy did not reject project pods

### Symptom

During `01.04`, we wanted project namespaces to reject pods without explicit CPU and memory resources. A `ValidatingAdmissionPolicy` rendered and applied successfully, but both server dry-run and real pod creation still allowed an unresourced pod.

```text
pod/quota-rejects-unresourced-pod created
```

### Cause

The kind API server was not running the admission plugin needed to enforce `ValidatingAdmissionPolicy`. Its flags showed only:

```text
--enable-admission-plugins=NodeRestriction
```

So the policy object existed, but it was inert for this cluster. We also saw CEL type-checking warnings while experimenting with resource field expressions, which made the policy path more fragile than necessary for this issue.

### Resolution

Use native `ResourceQuota` behavior instead of a custom admission policy for this issue. The project namespace now has normal compute quotas plus a quota scoped to `BestEffort` pods:

```yaml
spec:
  hard:
    pods: "0"
  scopes:
    - BestEffort
```

A pod with no resource requests/limits is BestEffort, so Kubernetes rejects it once no implicit defaults are added.

## LimitRange silently defaulted missing resources

### Symptom

After adding the `BestEffort` quota, an unresourced pod was still admitted. The quota existed and showed `pods: 0` for `BestEffort`, but the supposedly unresourced pod did not count as BestEffort.

### Cause

The project `LimitRange` included only `min` and `max`. Kubernetes defaulted missing `default` and `defaultRequest` values from the `max` values:

```yaml
default:
  cpu: "1"
  memory: 2Gi
defaultRequest:
  cpu: "1"
  memory: 2Gi
```

That silently turned an unresourced pod into a resourced pod, bypassing the BestEffort quota.

### Resolution

For the project namespace, remove the `max` from the `LimitRange` and keep only the minimum container bounds. That prevents Kubernetes from defaulting missing requests/limits. The `ResourceQuota` requiring `requests.*` and `limits.*` then rejects pods that omit explicit resources.

The final behavior is:

```text
resourced pod: accepted
unresourced pod: rejected by ResourceQuota
```

The verification output includes:

```text
failed quota: project-housing-quota: must specify limits.cpu ... limits.memory ...
project namespace rejects pods without explicit resources
```

## General debugging pattern that worked

When kind creation failed, the useful path was:

1. reproduce with retained containers;
2. inspect Docker node containers;
3. read kubelet logs from inside the worker;
4. distinguish noisy informational lines from the real fatal error;
5. patch scripts to wait for the state the platform actually requires.

Useful commands:

```bash
kind create cluster --name ml-platform-study-dev --config clusters/dev/kind/cluster.yaml --wait 120s --retain
docker ps -a --filter name=ml-platform-study-dev
docker exec ml-platform-study-dev-worker journalctl -u kubelet --no-pager -n 160
kubectl --context kind-ml-platform-study-dev get nodes -o wide
kubectl --context kind-ml-platform-study-dev get pods -A -o wide
```

## Platform namespace quota blocked Harbor reinstall

### Symptom

During `02.07.a`, `make apply-ci` tried to apply the registry dependency and Harbor could not create pods:

```text
exceeded quota: platform-system-quota
requested: limits.cpu=175m,limits.memory=384Mi
used: limits.cpu=2950m,limits.memory=4Gi
limited: limits.cpu=3,limits.memory=4Gi
```

The namespace also hit its Secret quota because Helm stores release history as Kubernetes Secrets:

```text
secrets: used 50, hard 50
```

### Cause

The original Phase 1 platform-system quota fit the early cluster services, but Phase 2 added identity, secrets, and CI dependencies. The platform namespace had become legitimately larger than the old quota allowed. Repeated Helm upgrades also accumulated release-history Secrets.

### Resolution

For the local study cluster:

1. prune old Helm release-history Secrets while keeping recent revisions;
2. raise the `ml-platform-system` dev quota from `3 CPU / 4Gi / 50 secrets` to `5 CPU / 6Gi / 80 secrets`.

This keeps quota pressure visible while allowing the platform service stack to run on the laptop.
