# Phase 1 backup runbook

`01.11` installs Velero and creates a labeled backup of Phase 1 Kubernetes metadata.

This is a backup baseline, not a full disaster recovery guarantee. The goal is to prove that cluster API objects can be captured, inventoried, and verified without leaking local credential values into logs.

## Apply and test

```bash
make backup-phase-01
make verify-backup-phase-01
```

`make backup-phase-01`:

1. confirms the kind cluster and Garage object store are available;
2. creates the `velero` namespace;
3. creates a local-only Velero credentials Secret from the Garage credentials in the `Makefile`;
4. installs pinned Velero chart `12.1.0`;
5. waits for Velero to become available;
6. creates a labeled `phase-01-*` Backup object.

`make verify-backup-phase-01`:

1. inventories the latest labeled Phase 1 backup with Velero;
2. verifies the Backup completed;
3. verifies the backup storage location points at Garage;
4. checks recent Velero logs for local secret values.

## Backup storage

Velero writes its backup objects to Garage:

```text
s3://ml-platform-artifacts/velero/phase-01
```

The in-cluster endpoint is:

```text
http://garage-s3.ml-platform-data.svc.cluster.local:3900
```

## Included scope

The Phase 1 backup includes Kubernetes API objects from:

```text
ml-platform-system
ml-platform-data
ml-platform-observability
ml-platform-project-housing
```

The backup is labeled:

```text
ml-platform.local/phase=01
ml-platform.local/backup-scope=phase-01
```

## Exclusions and boundaries

This baseline intentionally excludes:

- Kubernetes `Secret` resources;
- Kubernetes events;
- volume snapshots;
- node-agent file-system backups;
- PostgreSQL native database dumps;
- Garage native data export or replication;
- Harbor registry blob durability beyond its current PVC.

That means this backup can help recover cluster metadata, but it is not sufficient to recreate application data after total storage loss.

## What is recoverable

Recoverable from this baseline:

- most namespace-scoped Kubernetes resource definitions in the Phase 1 namespaces;
- labels, annotations, service definitions, deployments, StatefulSets, ConfigMaps, and custom resources included by Velero;
- enough metadata to inspect what the Phase 1 cluster looked like at backup time.

Not recoverable from this baseline alone:

- plaintext or encoded secret material;
- PostgreSQL table contents;
- Garage object data if the Garage PVC/storage is lost;
- Harbor image blobs if Harbor storage is lost;
- proven RPO/RTO targets.

`01.12` owns the restore drill and should make these boundaries concrete by restoring into a controlled target and recording what comes back.
