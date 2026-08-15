# Velero chart configuration

This directory contains the pinned Helm values used to install Velero for the Phase 1 backup baseline.

The local study route stores Velero backup metadata in the Garage S3-compatible bucket from `01.09.a` and disables volume snapshots and node-agent file-system backups.

Native PostgreSQL backups, Garage durability/export backups, restore automation, schedules, and tested RPO/RTO targets belong to later backlog issues.
