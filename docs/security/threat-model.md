# Local-Lab Threat Model

This threat model covers the local study environment for Phase 0. It is intended to make security assumptions explicit before local services, datasets, model files, prompts, notebooks, and agent/tool outputs are added.

This is not a production security claim. The lab runs on one developer-controlled laptop and favors learning, reproducibility, and safe defaults over production-grade isolation.

## Scope

In scope:

- Local source repository and generated artifacts.
- Local containers and services added by Phase 0 issues.
- Datasets, model files, prompts, notebooks, run manifests, logs, metrics, and evaluation reports.
- Local credentials used for development services.
- Agent and tool outputs produced during study workflows.

Out of scope:

- Production multi-tenant security.
- Internet-facing deployments.
- Regulated or customer data.
- Enterprise identity, device management, endpoint detection, or managed secrets platforms.
- Protection against a fully compromised laptop operating system.

## Assets

| Asset | Why it matters |
|---|---|
| Source code and contracts | Define platform behavior and trust boundaries. |
| Datasets and document corpora | May contain sensitive, licensed, or poisoned content. |
| Model files and adapters | May execute unsafe deserialization paths or encode unwanted behavior. |
| Prompts and evaluation sets | May leak assumptions, contain prompt injection, or bias measurements. |
| Credentials and local environment files | Can grant access to object storage, databases, registries, or APIs. |
| Run manifests and lineage records | Provide provenance and audit evidence; tampering weakens reproducibility. |
| Notebooks and scripts | Can execute arbitrary local code. |
| Agent/tool output | May contain untrusted instructions, generated code, or exfiltrated data. |
| Logs, metrics, and traces | Can leak paths, prompts, credentials, document snippets, or model outputs. |
| Container images and SBOM/signature references | Establish software provenance and supply-chain evidence. |

## Actors

| Actor | Assumption |
|---|---|
| Platform learner | Trusted but can make mistakes or run unsafe commands. |
| Lesser implementation model | Untrusted assistant; must be constrained by issue scope, allowed paths, and tests. |
| Local service process | Semi-trusted; may expose local ports, persist state, or log sensitive values. |
| External package/image registry | Not fully trusted; packages and images require pinned versions and provenance checks. |
| Downloaded model or dataset publisher | Not fully trusted; artifacts can be malicious, mislabeled, poisoned, or license-incompatible. |
| Malicious document/prompt author | Can attempt prompt injection, data exfiltration, or tool misuse through content. |
| Local network peer | Out of scope for strong protection, but local services should not bind publicly by default. |

## Trust boundaries

| Boundary | Risk |
|---|---|
| Repository to local runtime | Code, notebooks, and scripts move from reviewed files into executable processes. |
| Host filesystem to containers | Bind mounts can expose source, credentials, datasets, or generated artifacts. |
| Local service to browser/API client | Local ports can expose unauthenticated dashboards or APIs. |
| Object storage to training/inference code | Artifacts loaded from storage may be tampered with or unsafe to deserialize. |
| Dataset/corpus to pipeline | Input data may be poisoned, oversized, malformed, licensed incorrectly, or prompt-injected. |
| LLM output to tools/agents | Generated text may contain unsafe commands, false claims, or instructions to bypass policy. |
| Logs/metrics/traces to observability stack | Telemetry can accidentally persist sensitive prompts, paths, tokens, or document snippets. |
| Registry/package index to local environment | Dependencies and images can introduce vulnerable or malicious code. |

## Entry Points

- `pip install`, container image pulls, and dependency updates.
- Local Compose services and exposed ports.
- Dataset ingestion and document parsing.
- Model/adaptor downloads and model deserialization.
- Notebook execution.
- Prompt templates, RAG corpus content, and user questions.
- Agent tools, generated commands, and generated files.
- Environment variables, `.env` files, and local credentials.
- Run manifests, artifact metadata, and object storage paths.

## Misuse Cases

### Data exfiltration through logs or agent/tool output

An implementation model, notebook, parser, or agent tool reads local datasets, prompts, `.env` files, or service credentials and writes them into logs, traces, generated answers, run manifests, or committed files.

Mitigations:

- Keep real secrets out of the repository.
- Use `.env.example` for placeholders and `.gitignore` for local environment files.
- Prefer synthetic or public datasets in Phase 0.
- Redact credentials and sensitive snippets before logging.
- Require issue-level allowed paths and human review before commits.
- Treat agent/tool output as untrusted until inspected.

Residual risk: local development tools and notebooks can still print sensitive values if a user runs unsafe code.

### Malicious model or artifact loading

A downloaded model, pickle, adapter, dataset artifact, or generated file is loaded by training or inference code and exploits unsafe deserialization or hidden code execution.

Mitigations:

- Prefer safe artifact formats where available.
- Record artifact URI, checksum, source, license, and provenance in the run manifest.
- Reject artifacts without expected checksums or schema references.
- Do not load arbitrary pickles or model files from untrusted sources.
- Pin image and dependency versions in the version catalog.
- Use isolated local containers for risky parsing or model experiments when later issues provide them.

Residual risk: some ML ecosystems rely on formats and loaders with broad execution or native-code attack surfaces.

### Prompt injection through RAG corpus content

A document in the local corpus includes instructions such as “ignore prior instructions,” “print secrets,” or “call a tool,” and the RAG or agent path treats that content as trusted instructions rather than untrusted evidence.

Mitigations:

- Treat retrieved text as data, not instructions.
- Require citations for factual answers.
- Add abstention behavior when retrieved evidence is weak.
- Keep tool execution separate from answer generation.
- Do not enable code execution in the first agent route.

Residual risk: model behavior can still be manipulated by adversarial content, especially before dedicated prompt-injection tests exist.

### Credential leakage through local services

Local dashboards, databases, object storage, or MLflow services expose default credentials, bind to public interfaces, or log connection strings.

Mitigations:

- Use non-default local credentials via environment variables.
- Bind local services to localhost unless an issue explicitly requires otherwise.
- Do not commit real secrets.
- Keep service smoke tests local and credential-free where possible.
- Rotate local credentials if they appear in logs, shell history, or committed files.

Residual risk: this lab is not hardened against other users or malware on the same laptop.

### Supply-chain drift or dependency confusion

A later issue uses `latest`, floating dependency ranges, or unverified images, causing non-reproducible behavior or pulling vulnerable code.

Mitigations:

- Use `config/versions.yaml` for Phase 0 components.
- Pin image digests where possible.
- Avoid unbounded dependency ranges in cataloged platform software.
- Record source and output image digests, SBOMs, and signatures in run manifests.

Residual risk: pinning reduces drift but does not prove an artifact is safe.

### Poisoned dataset or evaluation set

A dataset or evaluation fixture contains mislabeled examples, biased samples, duplicated rows, or adversarial content that makes metrics misleading.

Mitigations:

- Record dataset source, license, schema, checksum, and revision.
- Keep held-out splits deterministic and documented.
- Compare against baselines on the same evaluation boundary.
- Add data validation and slice metrics in later issues.

Residual risk: small study datasets can still produce misleading confidence.

## Residual risk

- The laptop host is a shared trust root; containers are not a complete security boundary.
- The Phase 0 lab may run unauthenticated local services for learning convenience.
- Public datasets and models can contain license, poisoning, safety, or provenance issues.
- Generated code, notebooks, and agent/tool output can be unsafe even when tests pass.
- Logs and traces may capture more information than intended until redaction is implemented.
- The lab does not yet enforce signatures, SBOM validation, sandboxing, network policy, or secret rotation.

## Out-of-Scope Production Threats

- Multi-tenant isolation between independent users or teams.
- Public ingress, WAF, DDoS protection, and internet-facing authentication.
- Formal compliance controls for regulated data.
- Enterprise key management, hardware security modules, and centralized audit retention.
- High-availability incident response and disaster recovery.
- Full supply-chain attestation enforcement.
- Runtime malware detection or endpoint compromise response.

## Local Safety Rules

- Use public or synthetic data unless a later issue explicitly approves another source.
- Do not commit secrets, personal data, private corpora, or large model artifacts.
- Do not trust generated code, agent/tool output, downloaded model files, or notebooks without review.
- Prefer pinned versions, checksums, and explicit source records.
- Keep local services private to the laptop unless a later issue requires broader access.
- When a run lacks provenance, treat it as non-reproducible and not promotable.
