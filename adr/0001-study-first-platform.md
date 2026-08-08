# ADR 0001: Study-First Platform Scope

## Status

Accepted

## Context

This project aims to explore a complete modern ML/LLM platform while remaining executable as a learning backlog. The user is working primarily from a single laptop and wants each issue to be small enough for lesser models to implement step by step.

The platform should cover classic ML, LLM serving, RAG, observability, deployment, governance, and bounded agentic workflows, but it is not intended to become a production service during the first implementation pass.

## Decision

Treat this repository as a study-first platform. Optimize the implementation sequence for learning value, reproducibility, small runnable slices, and explicit decisions before scale or production hardening.

Prefer fully open source components, local execution, small fixtures, and documented tradeoffs. Require explicit human approval before using paid services, external cloud infrastructure, sensitive data, or hardware-dependent routes.

## Consequences

- Early issues should produce contracts, ADRs, tests, and local workflows before larger infrastructure.
- Laptop-compatible routes are preferred when they teach the same platform concept.
- Hardware-heavy and production-grade tasks may be documented, simulated, or deferred until the required resources exist.
- Route choices must be recorded rather than silently selected by an implementation model.
- Production concerns remain visible in the backlog, but study safety and reproducibility take priority.
