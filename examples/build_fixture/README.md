# Build fixture

This directory contains a tiny Python HTTP fixture used by `02.10` to study reproducible OCI image builds.

The fixture intentionally has no third-party runtime dependencies. The image build demonstrates:

- a digest-pinned base image;
- BuildKit syntax;
- a non-root runtime user;
- a build-time secret passed without leaking into the final image.

Run through:

```bash
make build-fixture
make test-image
```
