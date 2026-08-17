# Secret rotation runbook

This runbook demonstrates rotating one study credential through the selected secrets route: OpenBao as the source of truth and External Secrets Operator as the Kubernetes sync mechanism.

## Scope

The rotation target is the OIDC echo fixture viewer password:

- source: `kv/projects/identity/oidc-echo/test-users` in OpenBao;
- sync route: `SecretStore/openbao-oidc-echo` and `ExternalSecret/oidc-echo-test-users`;
- target: `Secret/oidc-echo-test-users` in `ml-platform-system`;
- provider token: a scoped OpenBao reader token stored as key `openbao-token` on the existing `Secret/oidc-echo-client`, avoiding an extra Secret object in the quota-limited study namespace;
- consumer update: call the Keycloak Admin API so Keycloak accepts the new password.

This is intentionally a narrow study workflow. It does not rotate every platform credential.

## Run

From the repository root:

```bash
make test-secret-rotation
```

The test target expects the phase 2 identity fixture and the OpenBao route to be available. It rotates the viewer password, verifies the old password no longer works, verifies the new password works, and checks the rotation command output does not print either credential.

If the dependency labs are not currently applied, run `make apply-oidc-fixture` and `make apply-secrets` first.

## Operational notes

- Do not edit plaintext passwords into Git.
- Do not paste rotated values into issue comments, logs, or documentation.
- The study cluster stores OpenBao bootstrap material in a Kubernetes Secret from issue `02.05.a`; production deployments need a stronger unseal and root-token custody model.
- External Secrets syncs the new value into Kubernetes, but Keycloak is the system that validates OIDC passwords, so the rotation script updates the matching Keycloak user after the Kubernetes Secret changes.
