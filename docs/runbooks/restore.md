# Phase 1 restore drill runbook

`01.12` runs a scoped restore drill from the Phase 1 backup baseline.

The drill proves that selected platform state can be recovered into explicitly suffixed targets without overwriting the original resources.

## Run the drill

```bash
make restore-drill-phase-01
```

The target first creates a fresh Phase 1 Velero backup through `make backup-phase-01`, then runs the restore drill and verifies the generated report.

## What gets restored

The drill restores the example project namespace from the latest completed Phase 1 Velero backup:

```text
ml-platform-project-housing -> ml-platform-project-housing-restored-01-12
```

The restore uses `restorePVs: false` and excludes Secrets and events. The original `ml-platform-project-housing` resources are checked before and after the restore to confirm they were not replaced.

The drill also performs two small fixture restores for data-plane learning:

- a PostgreSQL fixture row is copied from a source table into `public.restore_drill_fixture_restored_01_12`;
- a Garage fixture object is copied from a source key into `restore-drill/restored-01-12/phase-01-restore-drill.txt`.

For both fixtures, the drill records backup and restored SHA-256 checksums.

## Report

The drill writes:

```text
docs/reports/phase-01-restore-drill.json
```

The report records:

- the source backup name;
- the Velero restore name;
- elapsed time;
- recovered Kubernetes objects;
- SQL row checksums;
- object checksums;
- known recovery gaps.

## Boundaries

This is not whole-cluster disaster recovery.

It does not prove:

- in-place restore safety;
- Kubernetes Secret recovery;
- PostgreSQL point-in-time recovery;
- native Garage recovery after storage loss;
- Harbor image blob recovery;
- production RPO or RTO.
