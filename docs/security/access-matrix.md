# Phase 2 access matrix

`02.01` defines the least-privilege identity baseline for the study platform.

This document is a design contract only. It does not install an identity provider, create users, create Kubernetes RBAC, rotate secrets, or configure GitOps. Later Phase 2 issues implement the controls recorded here.

## Baseline principles

- Every permission has an owner.
- Every privilege escalation has an approval boundary.
- Human access is role-based and time-bounded where practical.
- Service access is scoped to one workload or integration.
- CI access is scoped to build, attest, and publish artifacts for one repository or project.
- Read-only access excludes Secrets, private credentials, mutable deploy actions, and destructive APIs.
- Deny cases are explicit and should fail closed in tests.
- Local bootstrap credentials are temporary study credentials, not reusable production credentials.

## Personas

| Persona | Type | Owner | Purpose | Credential type | Lifetime | Approval boundary |
|---|---|---|---|---|---|---|
| Platform learner | Human | Platform owner | Administer the local study platform during implementation. | OIDC user plus local break-glass kubeconfig during bootstrap. | OIDC session <= 8 hours; bootstrap kubeconfig only while local cluster exists. | Self-approved for local lab tasks; reviewer approval before broad admin changes. |
| Project developer | Human | Project owner | Build, test, and deploy project workloads through approved paths. | OIDC user/group membership. | OIDC session <= 8 hours; group membership reviewed per phase. | Project owner approves project membership. |
| Project viewer | Human / read-only | Project owner | Inspect project status, logs, metrics, model metadata, and non-sensitive artifacts. | OIDC user/group membership. | OIDC session <= 8 hours. | Project owner approves viewer membership. |
| Platform observer | Human / read-only | Platform owner | Inspect platform health, dashboards, alerts, and non-sensitive configuration. | OIDC user/group membership. | OIDC session <= 8 hours. | Platform owner approval. |
| Platform admin | Human | Platform owner | Operate identity, GitOps, policy, registry, backup, and shared platform services. | OIDC admin group; audited break-glass credential for local emergencies. | OIDC session <= 4 hours; break-glass credential rotated after use. | Platform owner approval; side effects recorded in ADR/runbook when material. |
| CI builder | CI | Repository owner | Run tests, build images, generate SBOMs, scan, sign, and push approved artifacts. | CI service identity with registry/project token. | Job token <= 1 hour; registry push token <= 24 hours or rotated per issue. | Repository owner approves pipeline definition and token scope. |
| GitOps reconciler | Service | Platform owner | Reconcile cluster state from approved Git paths. | Kubernetes service account plus repository deploy key/token. | Service account while controller exists; repo credential <= 90 days or externally rotated. | Platform owner approves repositories, paths, and sync policy. |
| Application runtime | Service | Project owner | Run one application or model service. | Kubernetes service account and mounted/synced runtime Secret. | Service account while workload exists; credentials rotated by secret route. | Project owner approves workload identity and scopes. |
| Model training job | Service | Project owner | Read approved data snapshots, write metrics/artifacts, and register candidates. | Kubernetes service account; object-storage scoped credential. | Per-run token preferred; local fallback <= 24 hours. | Project owner approves data and artifact scopes. |
| Model serving runtime | Service | Project owner | Read one approved model artifact and serve predictions. | Kubernetes service account; read-only model artifact credential. | While deployed; refreshed on rollout or <= 30 days. | Promotion approval required before serving production-simulation traffic. |
| RAG indexer | Service | Project owner | Read approved corpus sources, write chunks/embeddings/index metadata. | Kubernetes service account; scoped storage/vector credentials. | Per-index job token preferred; local fallback <= 24 hours. | Data owner approves corpus scope. |
| RAG answer service | Service | Project owner | Query approved indexes and call approved LLM endpoint. | Kubernetes service account; read-only vector and LLM client credentials. | While deployed; rotated <= 30 days. | Project owner approves index/model scopes. |
| Agent runtime | Service | Project owner + platform owner | Execute bounded agent state machine and allowlisted tools. | Kubernetes service account; scoped tool credentials issued per run/tool. | Per-run and per-tool credentials; expire <= 1 hour. | Human approval required for side-effecting tools. |
| Backup operator | Service | Platform owner | Create and inventory platform backups. | Kubernetes service account; object-storage write credential. | Controller lifetime; object credential rotated <= 90 days. | Platform owner approves backup scopes and restore actions. |

## Permission matrix

Legend:

- `Read`: list/view non-sensitive resources or metadata.
- `Write`: create/update scoped non-sensitive resources.
- `Admin`: manage configuration, identities, policies, or shared services.
- `Deny`: explicitly forbidden.
- `Approve`: may approve a bounded action but does not directly execute it.

| Persona | Kubernetes | Registry / Harbor | MLflow / model registry | Object storage / Garage | Identity / Keycloak | Secrets route | Git / CI | GitOps | Observability | Future LLM/RAG/agent services |
|---|---|---|---|---|---|---|---|---|---|---|
| Platform learner | Admin on exact local study cluster only. | Admin for local registry setup. | Admin for local study experiments. | Admin for local study buckets. | Admin during study realm setup. | Admin during selected route setup. | Write to study repo. | Admin during controller setup. | Admin for local dashboards. | Admin for local fixtures only. |
| Project developer | Write in own project namespace; Read platform APIs needed for deploy. | Push/pull only own project images. | Create runs and candidate models in own project. | Read/write own project prefixes. | Read own identity claims. | Request own project runtime secrets; cannot read secret values directly unless explicitly approved. | Write project code and pipelines. | Request/sync own project app through approved path. | Read own project logs/metrics. | Invoke approved project endpoints; no unrestricted tools. |
| Project viewer | Read own project namespace except Secrets. | Pull/read metadata for own project images. | Read own project experiments/models. | Read approved non-sensitive project artifacts. | Read own identity claims. | Deny. | Read project repository. | Read sync/status only. | Read own dashboards/logs with redaction. | Read/query approved endpoints only. |
| Platform observer | Read platform namespaces except Secrets. | Read registry health and metadata. | Read platform-wide metadata where non-sensitive. | Read bucket inventory metadata, not object contents by default. | Read realm/group metadata. | Deny secret value reads. | Read CI status. | Read GitOps status/drift. | Read platform dashboards/alerts. | Read service health, not prompts/tools/results unless approved. |
| Platform admin | Admin shared platform namespaces. | Admin registry projects/retention. | Admin shared MLflow configuration. | Admin shared buckets/policies. | Admin realm, groups, clients, tokens. | Admin policies and issuers; audited secret break-glass only. | Admin CI integration configuration. | Admin GitOps projects and sync windows. | Admin telemetry stack. | Admin policy and runtime configuration; human approval for side effects. |
| CI builder | Deny direct cluster mutation except test namespace when explicitly granted. | Push signed fixture/project images; pull bases. | Write build/test run metadata only when pipeline owns the run. | Write build artifacts/SBOMs under CI prefix. | Use service client only. | Consume scoped build secrets; cannot print or list all secrets. | Execute pipeline. | Write manifest/image-digest change only through approved repo path. | Write CI logs/metrics. | Run tests/evals; Deny production-simulation tool execution. |
| GitOps reconciler | Apply only allowlisted paths/namespaces. | Pull images by digest. | Deny direct model registry mutation. | Deny object mutation except controller state if needed. | OIDC client only. | Read decrypted/synced manifests only through selected secret route. | Read deploy repository. | Reconcile, detect drift, and report health. | Emit controller metrics/logs. | Deploy approved services; Deny runtime tool execution. |
| Application runtime | Read own ConfigMaps; Deny Kubernetes write. | Pull own image by digest. | Read own model metadata if needed. | Read/write only declared runtime artifact prefixes. | Validate tokens only. | Read mounted/synced own runtime Secret. | Deny. | Deny. | Emit logs/metrics/traces. | Serve only approved endpoint behavior. |
| Model training job | Read own namespace config; create own job pods only via pipeline. | Pull training image by digest. | Create runs, metrics, artifacts, candidate model versions. | Read approved data snapshots; write run artifacts. | Service auth only. | Read scoped data/model credentials. | Deny direct repo mutation. | Deny. | Emit training telemetry. | Deny agent tools; may call approved evaluation endpoints. |
| Model serving runtime | Read own deployment config. | Pull serving image by digest. | Read promoted model version metadata. | Read promoted model artifact only. | Validate tokens only. | Read serving credential only. | Deny. | Deny. | Emit inference telemetry. | Serve approved LLM/model endpoint with quotas. |
| RAG indexer | Read own config. | Pull indexer image by digest. | Write index build run metadata. | Read approved corpus; write chunks/embeddings. | Service auth only. | Read scoped corpus/index credentials. | Deny. | Deny. | Emit indexing telemetry. | Deny answer generation and agent tools. |
| RAG answer service | Read own config. | Pull answer image by digest. | Read model/index metadata. | Read approved retrieved chunks/artifacts. | Validate user token and claims. | Read query/runtime credentials only. | Deny. | Deny. | Emit redacted query metrics/traces. | Call approved LLM endpoint; Deny side-effect tools. |
| Agent runtime | Read own state/config; write own checkpoints only through approved storage/database. | Pull agent runtime image by digest. | Read model/tool metadata. | Read/write own run artifacts/audit references. | Validate user and approval claims. | Receive scoped per-tool credentials. | Deny. | Deny. | Emit audit-safe telemetry. | Execute allowlisted tools only with budgets, approvals, and audit events. |
| Backup operator | Read backup-scoped Kubernetes metadata; Deny Secrets unless future restore issue explicitly approves. | Read registry metadata; Deny blob mutation. | Read metadata for inventory. | Write backup prefixes; read backup prefixes for restore drill. | Service auth only. | Read only backup storage credential. | Deny. | Deny. | Emit backup metrics/logs. | Deny model/tool execution. |

## Explicit deny cases

| Deny case | Applies to | Reason | Test owner |
|---|---|---|---|
| Viewer cannot create, update, patch, or delete Kubernetes resources. | Project viewer, platform observer. | Read-only roles must not mutate runtime state. | `02.04` RBAC tests. |
| Viewer cannot read Kubernetes Secrets or synced secret values. | Project viewer, platform observer. | Secret data is never read-only observability data. | `02.04`, `02.05`. |
| Editor cannot access another project namespace. | Project developer. | Project boundaries must be explicit. | `02.04`. |
| CI cannot use cluster-admin. | CI builder. | CI compromise must not become cluster compromise. | `02.07`, `02.15`. |
| CI cannot push to registry projects it does not own. | CI builder. | Prevent cross-project artifact poisoning. | `02.07`, `02.10`. |
| GitOps viewer cannot sync or override drift. | Project viewer, platform observer. | Observability must not imply deployment control. | `02.08`. |
| GitOps reconciler cannot apply outside allowlisted paths/namespaces. | GitOps reconciler. | Prevent repository/path confusion from mutating unrelated resources. | `02.08`, `02.09`. |
| Runtime workloads cannot list all Secrets. | Application/model/RAG/agent runtimes. | Workloads receive only their own scoped secret material. | `02.05`, `02.06`. |
| Model serving runtime cannot write model registry state. | Model serving runtime. | Serving should consume promoted state, not promote itself. | `05.x`, `08.x`. |
| RAG answer service cannot mutate corpus/index state. | RAG answer service. | Query-time services must not silently change evidence. | `09.x`, `10.x`. |
| Agent runtime cannot execute unknown tools. | Agent runtime. | Tool execution is allowlisted and typed. | `11.04`, `11.05`. |
| Agent runtime cannot execute side-effecting tools without approval. | Agent runtime. | Human approval boundary protects irreversible actions. | `11.11`. |
| Backup operator cannot restore in-place by default. | Backup operator. | Restore drills use suffixed targets until an explicit recovery issue approves overwrite. | `01.12`, future DR issues. |

## Credential lifetime baseline

| Credential | Owner | Lifetime | Rotation / renewal rule | Storage rule |
|---|---|---|---|---|
| Human OIDC session | Identity admin | <= 8 hours; <= 4 hours for platform admin. | Re-authenticate after expiry. | Browser/client token cache only. |
| Local bootstrap kubeconfig | Platform owner | While exact local cluster exists. | Recreated with cluster; never reused across clusters. | Local workstation only; never committed. |
| Break-glass platform credential | Platform owner | Disabled or offline by default; rotate after every use. | Use requires note in runbook/ADR when material. | Local secret store or selected secret route; never committed. |
| CI job token | Repository owner | <= 1 hour or one job. | New token per job. | CI secret store only; redacted logs. |
| Registry push token | Registry owner | <= 24 hours for study route or rotated per issue. | Rotate after leak or route change. | Secret route/CI secret store. |
| GitOps repository credential | Platform owner | <= 90 days or deploy-key lifecycle. | Rotate on repository/controller change. | GitOps controller Secret via selected route. |
| Runtime service credential | Project owner | While workload exists, max 30 days unless shorter route exists. | Rotate on redeploy, leak, or membership change. | Mounted/synced Secret only. |
| Training job data credential | Data owner | Per-run preferred, max 24 hours. | New credential per run/snapshot. | Pipeline secret injection only. |
| Agent tool credential | Tool owner | Per-run and per-tool, max 1 hour. | Mint on approved tool call; revoke/expire after call. | Agent runtime memory/secret route; audit reference only. |
| Backup storage credential | Platform owner | <= 90 days for study route. | Rotate after restore test, leak, or route change. | Backup operator Secret via selected route. |

## Approval boundaries

| Action | Required approver | Record |
|---|---|---|
| Add or remove a human from platform-admin group. | Platform owner. | Access change note or issue comment. |
| Add project developer/editor membership. | Project owner. | Project access record. |
| Grant CI registry push permission. | Repository owner and registry owner. | CI runbook/config review. |
| Add GitOps sync path or namespace. | Platform owner. | GitOps runbook and reviewed manifest. |
| Create or rotate long-lived runtime credential. | Secret owner. | Secret rotation runbook entry. |
| Promote model or adapter to serving. | Project owner plus model reviewer. | Evaluation/promotion record. |
| Restore over existing resources. | Platform owner. | Explicit DR issue/runbook; denied by default in Phase 2. |
| Execute side-effecting agent tool. | Human requester or designated approver. | Append-only agent audit event. |
| Create policy exception for scan/sign/admission failure. | Platform owner with expiry. | Exception record with owner and expiry. |

## Future-service defaults

Future services inherit deny-by-default access unless a later issue extends this matrix:

- Feature store: project runtimes read approved online/offline feature views only; only pipelines write features.
- LLM gateway: users and services receive token budgets; anonymous calls are denied.
- RAG corpus/index APIs: corpus write access is separate from query access.
- Agent tools: side effects require typed tool contracts, scoped credentials, budgets, and audit events.
- Tenant/project APIs: project owners can administer their project but not platform-wide identity, policy, registry, or secret backends.

