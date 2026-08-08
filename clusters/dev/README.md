# Development overlays

This directory contains local development overlays for the study cluster.

Rules:

- environment-specific values are allowed here when documented;
- overlays must reference `clusters/base` rather than duplicating base manifests;
- cluster-specific ports and node selectors belong in the selected cluster overlay;
- generated render output must not be committed unless a later issue explicitly requests it.

