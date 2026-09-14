# Portable pipeline-component contract

Every Phase 4 component is a container that can run locally or under a future orchestrator without
changing its behavioral contract. The specification in `contracts/pipeline-component.schema.json`
defines the static interface a component implementation must declare.

## Runtime rules

- Inputs and outputs are named, durable artifact URIs. Inputs must be immutable references; outputs
  are published only through declared artifact locations.
- Containers communicate only through parameters, durable artifacts, a run manifest, and lineage
  events. Shared memory, local disk hand-offs, and orchestrator-specific state are prohibited.
- Every component writes a run manifest on success or failure and emits OpenLineage `START`,
  `COMPLETE`, or `FAIL` events.
- Logs are JSON Lines with `run_id`, component name, and attempt. Raw data values are never logged.
- A retry must be idempotent or publish to a deduplicated output location. Retrying an unsafe
  side-effect is not permitted.
- On `SIGTERM`, stop accepting new work, clean up only local temporary state, and exit `130` within
  the declared grace period. Do not delete durable input or output artifacts.

## Exit codes

| Code | Meaning | Orchestrator action |
| --- | --- | --- |
| `0` | completed | consume declared outputs |
| `75` | retryable failure | retry only within declared attempt limit |
| `1` | permanent failure | stop this path |
| `130` | cancelled | do not retry automatically |

## Minimal example

The valid fixture under `tests/contracts/pipelines/fixtures/valid/` describes a snapshot component.
It consumes a commit-pinned source dataset and produces a commit-pinned snapshot manifest. KFP,
Flyte, a local runner, or a plain container command may map this same declaration to their own
runtime configuration, but none may change its artifacts, exit behavior, cancellation behavior, or
provenance requirements.

Validate the contract with:

```bash
make test-pipeline-contracts
```
