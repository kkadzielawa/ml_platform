# OpenMetadata Helm values

Issue `03.10` uses OpenMetadata OSS as the study metadata catalog.

These values are sized for a local kind cluster:

- one OpenMetadata server replica;
- PostgreSQL via the existing CloudNativePG operator;
- single-node OpenSearch from the OpenMetadata dependencies chart;
- Airflow disabled;
- Keycloak OIDC configured as the interactive identity provider.

Implementation details, production hardening, and broad connector coverage belong to later backlog issues.
