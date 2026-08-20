# Woodpecker chart configuration

This directory contains the pinned Helm values for the local Woodpecker deployment used by the study CI route.

Woodpecker provides the CI server and Kubernetes-backed agent side of the lab. The values are sized for a laptop kind cluster: one server, one agent, small persistent storage, scoped namespace execution, and local-only service exposure.

Production runner isolation, autoscaling, external databases, public ingress, and full webhook/OAuth automation belong to later backlog issues.
