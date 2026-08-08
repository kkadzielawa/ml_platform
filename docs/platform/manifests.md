# Kubernetes manifest conventions

## Purpose

This document defines the repository layout and rendering rules for Kubernetes manifests. It covers both Kustomize overlays and future first-party Helm charts.

`01.03` creates conventions only. It does not install applications, create namespaces, or apply resources to the cluster.

## Layout

```text
clusters/
  base/
    kustomization.yaml
  dev/
    kind/
      kustomization.yaml
platform/
  charts/
```

`clusters/base` contains environment-neutral resources. `clusters/dev/**` contains local development overlays. `platform/charts` is reserved for reusable Helm charts owned by later issues.

## Base and overlay rules

Base manifests must not contain:

- hostnames;
- localhost ports;
- credentials;
- user-specific paths;
- cluster node names;
- environment names such as `dev`, `stage`, or `prod`;
- resource quotas or namespaces before their owning issues.

Overlays may contain environment-specific values when the values are local, documented, and scoped to the selected cluster route.

The current selected development overlay is:

```text
clusters/dev/kind
```

## Standard labels

Every rendered resource should eventually carry these labels:

- `app.kubernetes.io/part-of: ml-platform-study`
- `app.kubernetes.io/managed-by`
- `ml-platform.local/lifecycle`

Development overlays may add:

- `ml-platform.local/environment: dev`
- `ml-platform.local/cluster-route: kind`

Workload-specific labels belong to the issue that creates the workload.

## Namespace ownership

Namespace creation is intentionally deferred to `01.04`.

Once namespaces exist:

- platform services own platform namespaces;
- example project workloads own project namespaces;
- quotas and limit ranges belong in the overlay that scopes them to the recorded development cluster;
- ownership labels must make platform and project boundaries visible.

## Helm value-file rules

Future charts under `platform/charts/**` must keep reusable defaults in the chart and put environment-specific settings in overlay values files.

Value-file naming:

- `values.yaml`: chart defaults only;
- `values-dev.yaml`: local development environment values;
- `values-dev-kind.yaml`: kind-specific overrides.

Secrets must not be committed as Helm values. Use later secret-management issues for real secret material.

## Image rules

Rendered manifests must not use mutable image references:

- reject `latest`;
- reject image references without a tag or digest;
- prefer digest-pinned images using `@sha256:...`.

The manifest tests enforce this for rendered `containers` and `initContainers`.

## Render targets

Use:

```bash
make test-manifests
```

The target renders current Kustomize entries and validates parsed YAML. It does not apply resources to the cluster.

