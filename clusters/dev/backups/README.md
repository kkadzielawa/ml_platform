# Dev backup baseline

This directory documents the local Phase 1 backup baseline.

Velero is installed from the pinned chart values in `platform/charts/velero`; backup objects are created by `scripts/backup/phase-01-backup.sh`.

Restore drills, schedules, native PostgreSQL backup jobs, object-store export jobs, and production retention policy belong to later backlog issues.
