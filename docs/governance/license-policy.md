# Open Source and Asset License Policy

This policy defines how the study platform records and reviews licenses for software packages, model weights, datasets, and generated adapters. It is a local study policy, not legal advice.

## Principles

- Prefer OSI-approved open source software licenses for platform code and dependencies.
- Use SPDX license identifiers when available.
- Treat source-available licenses as distinct from open source, even when source code can be viewed.
- Record license, source, attribution, and review status before using models, datasets, or generated adapters in reproducible runs.
- Reject unknown or missing licenses until reviewed.

The Open Source Initiative defines open source through the Open Source Definition and maintains OSI-approved licenses. Access to source code alone is not enough to call something open source. SPDX identifiers are used for consistent machine-readable license records.

## Accepted by Default

These licenses are accepted for local study use when the source and attribution are recorded:

| Asset type | Accepted default licenses |
|---|---|
| Software packages | `Apache-2.0`, `MIT`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `0BSD` |
| Documentation and examples | `CC-BY-4.0`, `CC0-1.0`, `Apache-2.0`, `MIT` |
| Datasets | `CC0-1.0`, `CC-BY-4.0`, `ODC-BY-1.0`, `PDDL-1.0`, public domain records |
| Model weights | OSI-style permissive terms where applicable, `Apache-2.0`, `MIT`, or a clearly documented open model license approved for study use |
| Generated adapters | The base model license plus the dataset license and any training-code license obligations |

Acceptance does not mean an artifact is safe, high quality, or production-ready. It only means the license class is allowed by default for this study platform.

## Review Required

These licenses or conditions require explicit review before use beyond disposable local experiments:

- Strong copyleft software licenses such as `GPL-2.0-only`, `GPL-2.0-or-later`, `GPL-3.0-only`, `GPL-3.0-or-later`, and `AGPL-3.0-only`.
- Network copyleft or service-distribution obligations, especially AGPL-style terms.
- Weak copyleft licenses such as `LGPL-2.1-only`, `LGPL-3.0-only`, `MPL-2.0`, `EPL-2.0`, and `CDDL-1.0`.
- Creative Commons ShareAlike licenses such as `CC-BY-SA-4.0`.
- Creative Commons NonCommercial or NoDerivatives licenses such as `CC-BY-NC-4.0`, `CC-BY-ND-4.0`, and `CC-BY-NC-ND-4.0`.
- Custom model, dataset, benchmark, or research-only licenses.
- Any license with field-of-use restrictions, commercial restrictions, output-use restrictions, or redistribution restrictions.

Review-required assets may be acceptable for study, but the decision must be recorded before they become dependencies of reusable platform workflows.

## Rejected by Default

These are rejected unless a human explicitly approves a narrow exception:

- Missing, unknown, or ambiguous license terms.
- Source-available defaults that are not OSI-approved open source licenses.
- Licenses that prohibit modification, redistribution, benchmarking, publication of results, or normal study use.
- Licenses that restrict use by field, organization type, geography, or revenue.
- Model or dataset terms that claim broad ownership over generated outputs without review.
- Artifacts copied from private, paid, or credential-gated sources without permission.

Examples of source-available or restricted defaults include licenses that allow reading source code but restrict production use, hosted-service use, commercial use, or redistribution. These must not be described as open source in this project unless they are OSI-approved.

## License Records

Every reusable asset should have a license record using `contracts/license-record.schema.json`.

Required record types:

- `software-package`: package name, version, source URL, SPDX license expression, and review status.
- `model-weights`: model name, version, source URL, license expression or custom license name, upstream base model when applicable, and review status.
- `dataset`: dataset name, version, source URL, license expression or custom license name, attribution requirements, and review status.
- `generated-adapter`: adapter name, version, source model, training dataset records, generated-by run ID, inherited obligations, and review status.

## Review Status

Use one of these statuses:

- `accepted`: allowed by default under this policy.
- `review-required`: usable only after explicit human review.
- `rejected`: not allowed for reusable workflows.
- `unknown`: blocked until clarified.

## Local Study Rules

- Do not add license text files for third-party projects unless an issue asks for them.
- Do not scan the full dependency tree in this issue.
- Do not treat model weights or datasets as open source just because they are downloadable.
- Record licenses in run manifests and artifact metadata when a later issue consumes the asset.
- When in doubt, mark the asset `review-required` or `unknown`, not `accepted`.
