# Backlog Index and Route Guide

The backlog contains 310 atomic issues: 240 core issues across Phases 0–12 and 70 optional exploration issues. Alternative files are included in those totals; completing one route does not require completing its siblings.

## Core phase map

| Phase | Directory | Files | Entry | Exit |
|---|---|---:|---|---|
| 0 — Local vertical slice | `phase-00/` | 18 | `00.01` | `00.17` |
| 1 — Kubernetes foundation | `phase-01/` | 18 | `01.01` | `01.13` |
| 2 — Identity/GitOps/supply chain | `phase-02/` | 18 | `02.01` | `02.15` |
| 3 — Versioned data | `phase-03/` | 15 | `03.01` | `03.13` |
| 4 — ML pipelines | `phase-04/` | 17 | `04.01` | `04.16` |
| 5 — Model serving | `phase-05/` | 18 | `05.01` | `05.15` |
| 6 — Observability | `phase-06/` | 18 | `06.01` | `06.16` |
| 7 — GPU/distributed training | `phase-07/` | 16 | `07.01` | `07.13` |
| 8 — LLM serving/adaptation | `phase-08/` | 19 | `08.01` | `08.17` |
| 9 — RAG v1 | `phase-09/` | 20 | `09.01` | `09.18` |
| 10 — RAG scale/lifecycle | `phase-10/` | 18 | `10.01` | `10.16` |
| 11 — Bounded agents | `phase-11/` | 21 | `11.01` | `11.17` |
| 12 — Tenancy/hardening | `phase-12/` | 24 | `12.01` | `12.23` |

The exit issue is the phase-level integration test. It should be completed before treating that phase as a reusable capability. Hardware phases may be postponed without blocking unrelated study branches unless those branches declare the hardware phase as a dependency.

## Recommended study route

These choices follow the paved road in `IMPLEMENTATION_PLAN.md`; they are recommendations, not pre-approved decisions.

| Route group | Recommended starting route | Reason |
|---|---|---|
| `00.11` | `00.11.a` Garage | Lightweight local S3-compatible storage. |
| `01.02` | `01.02.a` kind | Disposable and easy to reproduce. |
| `01.05` | `01.05.a` Envoy Gateway | Standard Gateway API path. |
| `01.09` | `01.09.a` Garage | Avoid Ceph until storage itself is being studied. |
| `02.05` | `02.05.a` OpenBao | Teaches dynamic/scoped secret management. |
| `02.07` | `02.07.a` Forgejo/Woodpecker | Smaller fully self-hosted CI path. |
| `02.08` | `02.08.a` Argo CD | Matches the plan's GitOps paved road. |
| `03.07` | `03.07.a` Great Expectations | Broad data-quality learning path. |
| `03.11` | `03.11.a` Parquet + lakeFS | Avoid early lakehouse complexity. |
| `04.03` | `04.03.a` Kubeflow Pipelines | Matches the ML-first pipeline architecture. |
| `05.02` | `05.02.a` KServe | Shared predictive/generative serving control plane. |
| `05.03` | `05.03.a` MLServer | Small portable classic-model runtime. |
| `05.13` | `05.13.a` GitOps promotion | More transparent than an early custom reconciler. |
| `06.06` | `06.06.a` Tempo | Fits the selected Grafana OSS stack. |
| `06.10` | `06.10.a` Evidently | Broad introductory drift/reporting workflow. |
| `07.03` / `07.04` | Match installed NVIDIA or AMD hardware | These two route groups must select the same vendor. |
| `07.08` | `07.08.a` PyTorch runtime | Learn native distributed fundamentals first. |
| `08.04` | `08.04.a` vLLM | Default LLM serving baseline. |
| `08.14` | Select only after model/runtime compatibility check | AWQ and GPTQ support varies by model and hardware. |
| `09.02` | `09.02.a` filesystem connector | Removes network/crawler concerns from first RAG. |
| `09.03` | `09.03.b` Docling | Useful layout-aware learning path; Tika is the smaller fallback. |
| `10.09` | `10.09.a` Qdrant | Evaluate only after pgvector reaches a measured limit. |
| `11.03` | `11.03.a` explicit state machine | Makes agent control flow visible before frameworks. |
| `11.08` | `11.08.a` PostgreSQL checkpoints | Reuses an existing primitive; Temporal is a later durability study. |
| `11.13` | `11.13.c` no code execution | Safest first agent route. |
| `12.21` | `12.21.b` static docs portal | Lower operational cost for a study platform. |

## Optional exploration map

| Branch | IDs | Focus |
|---|---|---|
| A | `X.A.*` | Time series, recommenders, anomaly detection, online learning, causal ML, graph ML, RL |
| B | `X.B.*` | Tokenizers, tiny transformers, pretraining, checkpoints, scaling, parallelism |
| C | `X.C.*` | Instruction/preference data, SFT, DPO/ORPO, reward/verifiers, RL post-training |
| D | `X.D.*` | Inference benchmarks, runtimes, profiling, speculative decoding, caching, distributed inference |
| E | `X.E.*` | Vision, audio, document layout, multimodal RAG, image generation and safety |
| F | `X.F.*` | Retrieval ablations, late interaction, SQL, graphs, entity resolution, temporal facts |
| G | `X.G.*` | Event streams, Feast, online drift, edge inference, federated learning, differential privacy |
| H | `X.H.*` | Annotation, agreement, active learning, synthetic data, A/B experimentation |

## Route rules

1. Read all files in a route group, but give the implementation model only the selected file.
2. Record the selection in an ADR when the issue requests one.
3. A downstream dependency such as `"04.03"` means “the selected route in group `04.03` is complete.”
4. Never merge alternative routes into one implementation issue. Create a later, optional comparison issue if comparison is the learning goal.
5. Route choices may be revisited by a new ADR and migration task; do not silently replace an implemented route.

## Suggested first session

Complete only:

1. `00.01-study-charter.md`
2. `00.02-use-case-matrix.md`
3. `00.03-repository-skeleton.md`
4. `00.04-version-catalog.md`

Then review the artifacts before giving `00.05` to another model. This establishes the scope, repository contract, and pinned versions used by every later issue.

