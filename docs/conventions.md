# Naming Conventions

This document defines portable names, labels, and artifact prefixes for the study platform. The goal is to choose names that work across common filesystems, DNS labels, Kubernetes labels where applicable, and object storage paths.

## Name Rules

Use lowercase ASCII slugs for project, environment, dataset, and model names:

- Use only `a-z`, `0-9`, and `-`.
- Start and end with a letter or number.
- Keep names between 3 and 63 characters.
- Do not include spaces, underscores, dots, uppercase letters, dates of birth, email addresses, usernames, credentials, or personal names.
- Prefer stable semantic names over implementation details.

Examples:

- Valid project: `ml-platform`
- Valid environment: `local`
- Valid dataset: `iris-classifier`
- Valid model: `iris-baseline`
- Invalid names: `ML_Platform`, `dev.local`, `konrad-test`, `model_latest`, `a`

## Run IDs

Run IDs must be unique, sortable, and portable:

```text
run-<yyyymmdd>t<hhmmss>z-<8 lowercase hex chars>
```

Example:

```text
run-20260808t142233z-a1b2c3d4
```

The timestamp is UTC. The suffix prevents collisions when several runs start in the same second.

## Versions

Dataset versions use monotonically increasing study versions:

```text
v0001
v0002
```

Model versions use semantic versions:

```text
0.1.0
1.2.3
```

Do not use floating aliases such as `latest`, `stable`, or `dev` as artifact versions.

## Required Labels

Every platform-owned artifact that supports labels should carry these labels:

| Label | Purpose | Example |
|---|---|---|
| `app.kubernetes.io/name` | Portable component name | `iris-baseline` |
| `app.kubernetes.io/part-of` | Owning project | `ml-platform` |
| `ml-platform-study/phase` | Backlog phase that introduced it | `00` |
| `ml-platform-study/component` | Platform capability area | `training` |
| `ml-platform-study/environment` | Target environment | `local` |
| `ml-platform-study/owner` | Non-personal owner group | `study` |

Label values must be lowercase, portable slugs unless a later contract gives a narrower format.

## Artifact Prefixes

Object prefixes must not contain credentials, personal data, emails, usernames, or secret-like terms. Prefixes are logical paths, not bucket names:

```text
projects/<project>/datasets/<dataset>/versions/<dataset-version>/
projects/<project>/models/<model>/versions/<model-version>/
projects/<project>/runs/<run-id>/
projects/<project>/experiments/<experiment-name>/
```

Examples:

```text
projects/ml-platform/datasets/iris-classifier/versions/v0001/
projects/ml-platform/models/iris-baseline/versions/0.1.0/
projects/ml-platform/runs/run-20260808t142233z-a1b2c3d4/
projects/ml-platform/experiments/local-classic-ml/
```

Prefixes must be relative paths. Do not include URI schemes, bucket credentials, access keys, usernames, `..`, duplicate slashes, or leading slashes.

## Schema

The machine-readable contract lives in `contracts/naming.schema.json`. Valid and invalid examples are tested in `tests/contracts/test_naming_schema.py`.
