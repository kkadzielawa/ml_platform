# Data Retention and Encryption

This document records the Phase 03 study policy for object-storage retention and encryption. It is intentionally conservative: current fixtures are protected, expiry is simulated in tests, and no real object deletion is enabled by this issue.

## Backend reality

The local study cluster uses Garage as the S3-compatible object store. Garage is a good fit for learning object storage, bucket isolation, and S3-style access patterns, but it is not identical to AWS S3.

Supported or usable controls:

- Garage inter-node RPC encryption is enabled by the mandatory `rpc_secret`.
- Client-side encryption is supported because clients can encrypt payloads before uploading.
- SSE-C is supported when clients send customer-provided encryption keys with each request.
- Access control is provided by scoped Garage keys and separate buckets from `03.02`.

Unsupported or deferred controls:

- Garage does not provide AWS-style SSE-S3 bucket default encryption with server-managed keys.
- Garage does not provide AWS KMS-compatible SSE-KMS bucket encryption.
- External KMS integration is out of scope for this local study issue.
- Lifecycle expiry is not enabled as destructive backend deletion in this issue.

Do not emulate unsupported encryption by storing encryption keys beside the objects. That would make the storage look encrypted while preserving the same blast radius.

## Retention policy

The machine-readable retention policy lives in `clusters/dev/data-storage/retention-configmap.yaml`.

| Scope | Bucket | Review after | Expire after | Current deletion behavior |
|---|---|---:|---:|---|
| raw | `ml-platform-raw` | 30 days | 365 days | simulation only |
| curated | `ml-platform-curated` | 180 days | 730 days | simulation only |
| artifacts | `ml-platform-artifacts` | 365 days | 1095 days | simulation only |
| models | `ml-platform-models` | 180 days | never automatically | simulation only |
| evaluation | `ml-platform-evaluation` | 180 days | 730 days | simulation only |

Protected prefixes include `smoke/`, `fixtures/`, and model baseline prefixes that are required for local tests and study reproducibility.

## Expiry simulation

The test suite performs a non-destructive expiry simulation:

1. load the retention policy from the ConfigMap manifest;
2. create fake object inventory entries with bucket, key, and creation date;
3. calculate which objects would be reviewable or expirable;
4. assert required current fixture prefixes are not eligible for deletion;
5. assert old disposable scratch objects would be selected by the policy.

No S3 `DELETE` call is issued by this simulation.

## Encryption expectation by class

| Classification | Minimum local-study expectation |
|---|---|
| public | Access control and checksums are enough. |
| internal | Access control, transport protection where exposed outside the cluster, and scoped credentials. |
| confidential | Prefer client-side encryption or SSE-C for sensitive payloads; scoped buckets are mandatory. |
| restricted | Do not store raw values in object storage. If unavoidable in a later issue, encrypt before upload and keep keys outside Garage. |

This is a learning policy, not a production compliance guarantee.
