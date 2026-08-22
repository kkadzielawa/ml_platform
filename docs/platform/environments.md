# Environment overlays

## Purpose

The environment overlays describe how the same platform workload changes as it moves from local development to stage and then to a production simulation.

These overlays are render-only for `02.09`. They are not applied to the current kind cluster.

## Overlay paths

| Environment | Overlay | Intended use |
| --- | --- | --- |
| `dev` | `clusters/dev/environment` | Fast local feedback with minimum replicas, small resources, small storage, and permissive egress for exploration. |
| `stage` | `clusters/stage/environment` | Pre-production validation with more replicas, larger resources, retained storage intent, and narrower egress. |
| `prod-simulation` | `clusters/prod/simulation` | Laptop-safe production shape with higher replicas/resources/storage and default-deny network posture. |

## Promotion inputs

A promotion between environments should be a small, reviewable Git change. The normal inputs are:

- immutable image digest, for example `image@sha256:...`;
- target environment;
- replica count;
- CPU and memory requests/limits;
- storage request and storage class intent;
- policy posture, such as egress allow-list or default deny.

Secrets are not promotion inputs in these overlays. Secret values belong in the secret-management layer created by earlier issues.

## Immutable image replacement

Do not promote mutable tags such as `:dev`, `:stage`, or `:latest`.

Promotion should replace only the digest:

```text
ghcr.io/kkadzielawa/ml-platform-study/housing-price-api@sha256:<new-digest>
```

The environment tests reject mutable image tags in rendered manifests.

## Namespace isolation

Each overlay owns exactly one sample project namespace:

- `dev`: `ml-platform-dev-housing`
- `stage`: `ml-platform-stage-housing`
- `prod-simulation`: `ml-platform-prod-housing`

The environment tests reject resources that render into another environment's namespace.
