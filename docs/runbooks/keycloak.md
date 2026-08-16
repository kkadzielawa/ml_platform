# Keycloak runbook

`02.02` installs a local Keycloak identity provider for the study platform.

This is a small, single-replica study deployment. It is not production SSO, production federation, or a hardened identity architecture.

## Apply and test

```bash
make apply-keycloak
make test-keycloak
```

`make apply-keycloak`:

1. creates the exact local kind cluster if it is absent;
2. applies the Phase 1 TLS/gateway foundation;
3. applies CloudNativePG and the baseline study database dependency;
4. creates or preserves a locally generated Keycloak bootstrap admin Secret;
5. creates or preserves a locally generated Keycloak PostgreSQL credential in both the database and runtime namespaces;
6. applies the Keycloak PostgreSQL cluster, realm ConfigMap, Deployment, and Service;
7. waits for the database and Keycloak deployment to become ready.

`make test-keycloak`:

1. verifies manifests do not embed plaintext credentials;
2. port-forwards Keycloak locally;
3. authenticates to the admin API through the bootstrap admin Secret;
4. verifies the `ml-platform-study` realm exists;
5. verifies the `admin`, `learner`, `viewer`, and `service` realm roles exist;
6. restarts Keycloak and verifies the realm remains available.

## Local access

```bash
kubectl --context kind-ml-platform-study-dev port-forward \
  -n ml-platform-system svc/keycloak 18081:8080
```

Then open:

```text
http://127.0.0.1:18081
```

The bootstrap admin username is `admin` by default. The password is generated locally unless `KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD` is supplied before first apply.

Read it for local study only:

```bash
kubectl --context kind-ml-platform-study-dev get secret keycloak-bootstrap-admin \
  -n ml-platform-system \
  -o jsonpath='{.data.password}' | base64 --decode
```

## Realm

The declarative realm import lives in:

```text
clusters/dev/identity/realm-configmap.yaml
```

Realm:

```text
ml-platform-study
```

Initial realm roles:

- `admin`
- `learner`
- `viewer`
- `service`

Initial realm groups:

- `platform-admins`
- `platform-learners`
- `platform-viewers`
- `platform-services`

## Credential boundary

Bootstrap and database credentials are not committed to Git or rendered manifests.

The Make target creates them only if the corresponding Secret does not already exist. That keeps repeated applies from accidentally changing the bootstrap admin password after Keycloak has initialized.

For this study issue, credentials are supplied externally through environment variables or generated locally:

- `KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD`
- `KEYCLOAK_DB_PASSWORD`

Secret rotation is intentionally left to `02.06`.

## Boundaries

This issue does not:

- connect application routes to OIDC;
- configure Kubernetes API login through OIDC;
- configure production SSO federation;
- configure HA Keycloak;
- configure external identity providers;
- migrate all platform credentials.

Those belong to later Phase 2 issues.
