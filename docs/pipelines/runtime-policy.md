# Classic ML runtime policy

The classic ML pipeline declares a runtime policy for every stage. The policy
is part of the pipeline source and is verified against the compiled KFP v2 IR;
it is not an operator-wide scheduler policy.

## Stage policy

| Stage | Cache | Cache identity | Retry class / retries | Deadline | Requests / limits |
| --- | --- | --- | --- | --- | --- |
| `snapshot` | disabled | mutable reference cannot prove a resolved commit | transient container / 2 | 300s + 30s cleanup grace | 100m / 500m CPU, 256Mi / 512Mi memory |
| `validate` | automatic inputs | snapshot manifest, dataset path, validation suite | transient container / 2 | 600s + 30s cleanup grace | 250m / 1 CPU, 512Mi / 1Gi memory |
| `transform` | disabled | run ID, content checksum, implementation, configuration | idempotent output / 2 | 900s + 30s cleanup grace | 250m / 1 CPU, 512Mi / 1Gi memory |
| `train` | disabled | dataset revision, code, model, training implementation | non-idempotent side effect / 0 | 1800s + 60s cleanup grace | 500m / 2 CPU, 1Gi / 2Gi memory |
| `evaluate` | automatic inputs | transformed data, training output, dataset/model/code identity | idempotent output / 2 | 900s + 30s cleanup grace | 250m / 1 CPU, 512Mi / 1Gi memory |
| `register` | disabled | evaluation checksum, MLflow run, model, source, license | non-idempotent registration / 0 | 600s + 30s cleanup grace | 100m / 500m CPU, 256Mi / 512Mi memory |

CPU and memory values are expressed as Kubernetes requests / limits. The
pipeline's sequential graph keeps the declared requests within the local KFP
namespace budget.

## Cache identity

KFP's custom `cacheKey` replaces automatic input fingerprinting. A static
custom key would therefore ignore runtime parameters, artifacts, the base
image, and command arguments. This pipeline intentionally does not emit custom
KFP cache keys. Cacheable tasks use KFP's automatic key and the source table
declares the complete identity that must remain connected to those tasks.

Training is never cached: its current component creates an MLflow run and the
pipeline does not provide a complete content-addressed training identity.
Snapshot is not cached because its input is a mutable branch/reference.
Transform is not cached because its current inputs do not include an immutable
dataset-content checksum. Registration is never cached because it mutates the
model registry.

## Retry classes

`set_retry` is applied only to stages whose output is read-only or atomically
published. The compiled IR carries the retry count and bounded exponential
backoff. The KFP backend's default error policy is expected to retry container
or transport errors, while component-level validation and evaluation gate exit
codes remain permanent failures. Training and registration receive no retry
policy; in particular, registration has no blind retry after a registry write.

## Deadlines and cleanup

KFP 2.17 exposes no task-level timeout method or task timeout field in its
portable IR. Each task therefore starts through GNU `timeout` in the pinned
Debian-based component image. It sends `SIGTERM` at the deadline and allows the
declared grace period before `SIGKILL`.

Failure cleanup is local-only. Component staging directories and temporary
files are removed by the component's failure paths; the runtime wrapper never
deletes durable input or output artifacts. Registry state, MLflow runs, and
other external resources are not cleaned up automatically by the pipeline.

The policy can be inspected without KFP installed with:

```python
from pipelines.classic_ml.pipeline import pipeline_spec

pipeline_spec()["runtime_policies"]
```
