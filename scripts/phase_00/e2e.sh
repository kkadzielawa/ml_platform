#!/usr/bin/env bash
set -eu

python -c "import boto3, fastapi, httpx, pytest, sklearn" || python -m pip install --no-cache-dir ${BASELINE_SERVE_PACKAGES:?BASELINE_SERVE_PACKAGES is required}
python -m pytest tests/e2e/phase_00 -s

