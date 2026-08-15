# Restore scripts

This directory contains local disaster-recovery drill entrypoints.

Issue `01.12` uses the Phase 1 restore drill to restore scoped Kubernetes metadata, SQL rows, and object data into suffixed targets without overwriting original resources.

Production restore automation, whole-cluster recovery, credential recovery, and in-place destructive restores belong to later backlog issues.
