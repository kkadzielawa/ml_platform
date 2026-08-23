# Supply-chain scan policy

## Purpose

`02.12` introduces a local study policy for scanning the build fixture image and checking the generated SBOM.

The policy is intentionally narrow. It does not make legal conclusions and does not remediate third-party vulnerabilities.

## Scanner

The fixture uses pinned Trivy:

```text
docker.io/aquasec/trivy:0.72.0@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f
```

The scanner runs with vulnerability and secret scanners enabled and does not ignore all unfixed vulnerabilities:

```text
--scanners vuln,secret
--ignore-unfixed=false
```

## License policy

The local policy lives at:

```text
config/license-policy/policy.json
```

It defines:

- allowed license expressions;
- forbidden license expressions;
- a required schema for severity/license/secret exceptions.

Forbidden examples include:

- `AGPL-3.0-only`
- `AGPL-3.0-or-later`
- `SSPL-1.0`
- `BUSL-1.1`

## Exception schema

Every exception must include:

- `id`
- `owner`
- `reason`
- `expires_on`
- `scope`

Expired exceptions fail the policy check. Exceptions are intentionally empty for the approved fixture.

## Local commands

Generate the fixture scan:

```bash
make scan-fixture
```

Validate policy behavior:

```bash
make test-scan-policy
```
