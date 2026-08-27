# lakeFS dev deployment

This directory records the local kind deployment notes for lakeFS.

The actual Kubernetes objects are rendered from the pinned upstream Helm chart and `platform/charts/lakefs/values-dev-kind.yaml` by `make apply-lakefs`.

Do not store lakeFS database, object-store, or admin credentials in this directory.
