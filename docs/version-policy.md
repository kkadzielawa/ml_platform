# Version Policy

This project records Phase 0 tool and image versions in `config/versions.yaml` before later issues consume them. The catalog is intentionally small and pinned: it is a source of truth for local study workflows, not a package manager lockfile.

## Research

Use primary sources when selecting or updating versions:

- Python: Python.org release pages.
- PostgreSQL: PostgreSQL versioning and release notes.
- MLflow: official GitHub releases.
- Prometheus: Prometheus download metadata or official GitHub releases.
- Grafana: Grafana download page or official image metadata.
- Container digests: resolve the linux/amd64 manifest digest from the registry before committing the catalog.

## Pinning Rules

- Do not use `latest`, floating branches, wildcard versions, or unbounded ranges in the catalog.
- Runtime versions must be exact releases, such as `3.12.13` or `16.14`.
- Container images must include a concrete tag and a `sha256` digest for the target platform when the registry exposes one.
- Keep the human-readable tag and immutable digest together so later Compose files can use `repository:tag@digest`.
- Unknown values must be recorded as open decisions in the owning issue, not guessed in the catalog.

## Updates

Update versions through a small reviewable change:

1. Read the upstream release notes and check for breaking changes or security fixes.
2. Resolve the new image digest for `linux/amd64`.
3. Update `config/versions.yaml`.
4. Run `make test-versions`.
5. Record any required migration or compatibility work in the issue that consumes the changed component.

Do not upgrade running software as part of a catalog-only change. Installation and rollout belong to later backlog issues.
