# Phase 0 local vertical slice runbook

## Purpose

The Phase 0 e2e command proves the local study platform can complete a minimal ML lifecycle without Kubernetes or production infrastructure:

1. start local PostgreSQL, Garage object storage, and MLflow;
2. train the synthetic housing-sale baseline twice;
3. register two distinct versions of a temporary MLflow model;
4. serve one explicit registered model version through the FastAPI prediction app;
5. verify a successful prediction, a forced bad payload, and a failed quality gate;
6. delete the temporary e2e registered model and active MLflow experiment.

## Command

```bash
make e2e-phase-00
```

The command is noninteractive. It runs the e2e test inside the pinned MLflow image and installs the bounded Phase 0 serving-test packages if the image does not already contain them.

## Expected runtime

Typical runtime on the study laptop is 45-120 seconds after Docker images are already present. The first run can take longer because Docker may need to pull images and Python packages.

## Local ports

- PostgreSQL: `127.0.0.1:5432`
- Garage S3 API: `127.0.0.1:3900`
- Garage admin API: `127.0.0.1:3903`
- MLflow: `127.0.0.1:5000`
- Baseline FastAPI service, when started manually: `127.0.0.1:18080`

The e2e test exercises the FastAPI app in-process with `TestClient`; it does not leave a serving container running.

## Artifacts and resources

During the run, MLflow receives:

- two successful training runs with distinct platform run IDs;
- two registered versions of a temporary e2e model;
- one failed-quality-gate training run that must not register a model;
- metrics, dataset metadata, model artifacts, and run manifests for each training run.

The e2e test deletes its temporary registered model and active MLflow experiment in a `finally` block. MLflow and object storage may still retain backend rows or stored artifacts according to their local retention behavior.

## Common failures

- Docker is not running: start Docker and rerun `make e2e-phase-00`.
- Port already in use: stop the conflicting local service or override the relevant Make variable, such as `MLFLOW_PORT`.
- MLflow rejects an internal hostname with an invalid host-header error: use the Make targets, which route Phase 0 training and e2e calls through `127.0.0.1`.
- Package install fails because the network is unavailable: rerun after network access is available, or use a future pinned custom image once that backlog issue exists.
- The quality-gate check unexpectedly registers a model: treat this as a real failure; do not weaken the threshold to pass the test.

