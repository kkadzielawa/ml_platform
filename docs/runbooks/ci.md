# CI runbook

This runbook covers the local study CI route from issue `02.07.a`: Forgejo as the Git forge, Woodpecker as the CI service, and Harbor as the image registry.

## Components

- Forgejo runs in `ml-platform-ci` as `Deployment/forgejo`.
- Woodpecker runs in `ml-platform-ci` as `StatefulSet/woodpecker-server` and `StatefulSet/woodpecker-agent`.
- Harbor remains in `ml-platform-system` and is used as the registry.
- A sample CI identity is represented by a Harbor robot account scoped to the `ci-study` project.

## Apply and test

```bash
make apply-ci
make test-ci
```

`make apply-ci` creates local-only bootstrap Secrets, installs pinned Forgejo and Woodpecker charts, and waits for the CI pods to become ready.

`make test-ci` verifies the services are ready, creates a sample commit-attributed pipeline image tag from the current Git commit, pushes it to Harbor with the scoped CI robot identity, and confirms the same identity cannot push outside the intended Harbor project.

## Local access

Forgejo:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-ci svc/forgejo-http 13000:3000
```

Open `http://127.0.0.1:13000`.

Woodpecker:

```bash
kubectl --context kind-ml-platform-study-dev \
  port-forward -n ml-platform-ci svc/woodpecker-server 18000:80
```

Open `http://127.0.0.1:18000`.

## Scope notes

This lab proves the deployment shape and scoped registry identity. It intentionally does not migrate this repository into Forgejo or automate the full interactive OAuth/webhook activation flow between Forgejo and Woodpecker.
