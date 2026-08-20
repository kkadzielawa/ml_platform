# Forgejo chart configuration

This directory contains the pinned Helm values for the local Forgejo deployment used by the study CI route.

Forgejo provides the self-hosted Git forge side of the CI lab. The values are sized for a single-node kind study cluster: one replica, small persistent storage, ClusterIP services, and no ingress.

Production hardening, external databases, HA storage, SSO, repository migration, and backup policy belong to later backlog issues.
