# Trivy scan configuration

This directory contains the pinned Trivy scan configuration and generated fixture scan report for `02.12`.

Run:

```bash
make scan-fixture
make test-scan-policy
```

The scan report is local study evidence. Later issues own admission enforcement, signing, and production promotion gates.
