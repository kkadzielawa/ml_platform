# Syft SBOM generation

This directory contains local SBOM generation configuration and generated fixture SBOMs for `02.11`.

The fixture image SBOMs are generated with pinned Syft through:

```bash
make sbom-fixture
make test-sbom
```

Later issues own vulnerability scanning, legal review, image signing, and admission policy.
