# OpenBao chart values

This directory records the pinned local OpenBao Helm values for the `02.05.a` study secrets route.

The deployment is a single-node standalone OpenBao server with file storage on a local PVC. Bootstrap material is stored in Kubernetes Secrets for study convenience only.

Production unseal, HSM/KMS integration, high availability, audit hardening, and broad secret migration belong to later backlog issues.
