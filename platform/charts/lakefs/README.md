# lakeFS chart values

Issue `03.04` deploys the pinned upstream `lakefs/lakefs` Helm chart with these local kind values.

Secrets are not committed here. The Make target creates Kubernetes Secrets for the PostgreSQL connection string, lakeFS auth encryption key, and lakeFS admin test credentials at apply time.

This is a single-replica study deployment. Production high availability, garbage collection, retention tuning, external ingress, and large-data performance are later concerns.
