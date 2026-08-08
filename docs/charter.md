# Study Charter

## Purpose

This repository is a study-first, fully open source ML/LLM platform project. Its purpose is to learn how modern platforms are designed, assembled, operated, and evaluated across classic ML, LLM serving, RAG, and bounded agentic workflows.

## Goals

- Build a runnable local vertical slice for data ingestion, training, model registration, serving, observability, RAG, and agent control flow.
- Keep each backlog issue small enough for a lesser model to implement with explicit context, allowed paths, verification commands, and acceptance criteria.
- Produce durable learning artifacts: ADRs, contracts, runbooks, manifests, tests, and experiment reports.
- Preserve reproducibility by recording versions, inputs, outputs, metrics, and decisions before relying on each component.
- Learn platform engineering tradeoffs by implementing at least one paved route for each major capability and documenting why alternatives were deferred.

## Measurable Outcomes

- Complete Phase 0 with one end-to-end local ML workflow that runs without external services beyond local containers.
- Complete at least one route for each required route group before starting optional explorations that depend on it.
- For every completed issue, record changed files, verification commands, assumptions, and remaining risks.
- Maintain passing verification for completed issues as later issues add capabilities.
- Produce at least three reviewer-ready architecture artifacts: a platform charter, route ADRs, and operational runbooks.

## Hardware

- Primary environment: a single Linux laptop.
- CPU: Intel Core i7-7700HQ class hardware.
- Memory: 16 GiB RAM.
- Storage: approximately 168 GiB free on the main Linux filesystem at charter time, plus a larger secondary data drive available for non-critical artifacts.
- GPU: NVIDIA GTX 1050 Ti Mobile is present, but GPU availability is not assumed because the driver/runtime was not verified.
- Baseline assumption: CPU-first local development; GPU and distributed training tasks require explicit readiness checks before execution.

## Budget

- Default budget: zero cloud spend and zero paid SaaS dependencies.
- Any cloud GPU, managed Kubernetes, hosted vector database, commercial model API, or paid observability service requires explicit human approval before use.
- Prefer small public datasets, synthetic fixtures, quantized local models, and disposable local environments.
- Avoid long-running workloads that would monopolize the laptop or risk thermal instability.

## First Three Experiments

1. Local classic ML vertical slice: train a small baseline model on a small tabular dataset, register its metadata, serve predictions locally, and capture basic metrics.
2. Local RAG vertical slice: ingest a small document corpus from the filesystem, chunk it deterministically, embed it with a lightweight local model, retrieve passages, and produce cited answers.
3. Bounded agent vertical slice: implement an explicit state-machine agent with a small tool registry, deterministic budgets, audit logging, and no code execution.

## Non-goals

- Production operation of a business-critical ML platform.
- High-availability guarantees on the single laptop.
- Multi-node GPU training unless suitable external hardware is explicitly approved.
- Paid cloud or SaaS services by default.
- Building proprietary platform components when a maintained open source option is available for study.
- Optimizing for scale before the local learning path is reproducible.
- Handling regulated production data, secrets, or customer workloads.

## Reviewer Approval

- [x] Approved as the governing study charter for this platform backlog.
