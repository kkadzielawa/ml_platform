export POSTGRES_DB ?= ml_platform_local
export POSTGRES_USER ?= ml_platform_app
export POSTGRES_PASSWORD ?= local-dev-postgres-password
export POSTGRES_PORT ?= 5432
export GARAGE_RPC_SECRET ?= 1111111111111111111111111111111111111111111111111111111111111111
export GARAGE_ADMIN_TOKEN ?= local-dev-garage-admin-token
export GARAGE_METRICS_TOKEN ?= local-dev-garage-metrics-token
export GARAGE_KEY_ID ?= GK111111111111111111111111
export GARAGE_SECRET_KEY ?= 2222222222222222222222222222222222222222222222222222222222222222
export GARAGE_BUCKET ?= ml-platform-artifacts
export GARAGE_S3_REGION ?= garage
export GARAGE_S3_ENDPOINT ?= http://127.0.0.1:3900
export GARAGE_S3_PORT ?= 3900
export GARAGE_ADMIN_PORT ?= 3903
export MLFLOW_PORT ?= 5000
export MLFLOW_TRACKING_URI ?= http://127.0.0.1:$(MLFLOW_PORT)
export PROMETHEUS_PORT ?= 19090
export PROMETHEUS_URL ?= http://127.0.0.1:$(PROMETHEUS_PORT)
export GRAFANA_PORT ?= 13000
export GRAFANA_URL ?= http://127.0.0.1:$(GRAFANA_PORT)
export GRAFANA_ADMIN_USER ?= admin
export GRAFANA_ADMIN_PASSWORD ?= local-dev-grafana-password
export BASELINE_TRAIN_IMAGE ?= ghcr.io/mlflow/mlflow:v3.13.0@sha256:a5cd51cd14b570ec4374a4dad76a8ff92b7a0a6f66904c871cee18703487d23f
export BASELINE_TRAIN_PACKAGES ?= boto3==1.43.67 pytest==8.4.2
export BASELINE_SERVE_PACKAGES ?= boto3==1.43.67 fastapi==0.115.6 httpx==0.28.1 pytest==8.4.2 uvicorn==0.32.1
export BASELINE_MODEL_NAME ?= housing-sale-baseline
export BASELINE_SERVE_PORT ?= 18080
export KIND_CLUSTER_NAME ?= ml-platform-study-dev
export KIND_CONFIG ?= clusters/dev/kind/cluster.yaml
export ENVOY_GATEWAY_VERSION ?= v1.8.3
export ENVOY_GATEWAY_RELEASE ?= eg
export ENVOY_GATEWAY_NAMESPACE ?= ml-platform-system
export GATEWAY_HOST ?= gateway.ml-platform.local
export GATEWAY_HTTP_PORT ?= 8080
export HELM_RUNNER_IMAGE ?= docker.io/alpine/helm:3.18.6@sha256:b158d7f0fe1fb84abb59a15973ef25adf66affa2028a8328c083046c5ca04e91
export KUBECONFIG ?= $(HOME)/.kube/config
export CERT_MANAGER_VERSION ?= v1.21.0
export CERT_MANAGER_RELEASE ?= cert-manager
export CERT_MANAGER_NAMESPACE ?= ml-platform-system
export CERT_MANAGER_CHART ?= oci://quay.io/jetstack/charts/cert-manager
export GATEWAY_HTTPS_PORT ?= 8443
export TLS_CA_BUNDLE ?= /tmp/ml-platform-local-ca.crt
export CLOUDNATIVEPG_CHART_VERSION ?= 0.29.0
export CLOUDNATIVEPG_APP_VERSION ?= 1.30.0
export CLOUDNATIVEPG_RELEASE ?= cnpg
export CLOUDNATIVEPG_NAMESPACE ?= ml-platform-system
export CLOUDNATIVEPG_CHART_REPO ?= https://cloudnative-pg.github.io/charts
export HARBOR_CHART_VERSION ?= 1.19.1
export HARBOR_APP_VERSION ?= 2.15.1
export HARBOR_RELEASE ?= harbor
export HARBOR_NAMESPACE ?= ml-platform-system
export HARBOR_CHART_REPO ?= https://helm.goharbor.io
export HARBOR_ADMIN_USER ?= admin
export HARBOR_ADMIN_PASSWORD ?= local-dev-harbor-password
export CLUSTER_REGISTRY_HOST ?= 127.0.0.1:15000
export CLUSTER_REGISTRY_PORT ?= 15000
export VELERO_CHART_VERSION ?= 12.1.0
export VELERO_APP_VERSION ?= 1.18.1
export VELERO_AWS_PLUGIN_VERSION ?= 1.14.1
export VELERO_RELEASE ?= velero
export VELERO_NAMESPACE ?= velero
export VELERO_CHART_REPO ?= https://vmware-tanzu.github.io/helm-charts
export OPENBAO_CHART_VERSION ?= 0.28.5
export OPENBAO_APP_VERSION ?= 2.6.0
export OPENBAO_RELEASE ?= openbao
export OPENBAO_NAMESPACE ?= ml-platform-system
export OPENBAO_CHART_REPO ?= https://openbao.github.io/openbao-helm
export EXTERNAL_SECRETS_CHART_VERSION ?= 2.8.0
export EXTERNAL_SECRETS_APP_VERSION ?= v2.8.0
export EXTERNAL_SECRETS_RELEASE ?= external-secrets
export EXTERNAL_SECRETS_NAMESPACE ?= ml-platform-system
export EXTERNAL_SECRETS_CHART_REPO ?= https://charts.external-secrets.io
export SECRETS_EXAMPLE_NAMESPACE ?= ml-platform-project-housing
export FORGEJO_CHART_VERSION ?= 17.1.0
export FORGEJO_APP_VERSION ?= 15.0.6
export FORGEJO_RELEASE ?= forgejo
export FORGEJO_NAMESPACE ?= ml-platform-ci
export FORGEJO_CHART ?= oci://code.forgejo.org/forgejo-helm/forgejo
export FORGEJO_ADMIN_USERNAME ?= forgejo_admin
export FORGEJO_ADMIN_PASSWORD ?= local-dev-forgejo-password
export WOODPECKER_CHART_VERSION ?= 3.6.4
export WOODPECKER_APP_VERSION ?= 3.15.0
export WOODPECKER_RELEASE ?= woodpecker
export WOODPECKER_NAMESPACE ?= ml-platform-ci
export WOODPECKER_CHART ?= oci://ghcr.io/woodpecker-ci/helm/woodpecker
export WOODPECKER_AGENT_SECRET ?= local-dev-woodpecker-agent-secret
export WOODPECKER_FORGEJO_CLIENT ?= local-dev-forgejo-client
export WOODPECKER_FORGEJO_SECRET ?= local-dev-forgejo-secret
export WOODPECKER_SECRET ?= local-dev-woodpecker-server-secret
export ARGOCD_CHART_VERSION ?= 9.5.21
export ARGOCD_APP_VERSION ?= v3.4.3
export ARGOCD_RELEASE ?= argocd
export ARGOCD_NAMESPACE ?= ml-platform-gitops
export ARGOCD_CHART_REPO ?= https://argoproj.github.io/argo-helm
export ARGOCD_OIDC_CLIENT_SECRET ?= local-dev-argocd-oidc-secret
export ARGOCD_PORT ?= 18083
export KYVERNO_CHART_VERSION ?= 3.8.2
export KYVERNO_APP_VERSION ?= v1.18.2
export KYVERNO_RELEASE ?= kyverno
export KYVERNO_NAMESPACE ?= ml-platform-system
export KYVERNO_CHART_REPO ?= https://kyverno.github.io/kyverno
export LAKEFS_CHART_VERSION ?= 1.12.25
export LAKEFS_APP_VERSION ?= 1.86.0
export LAKEFS_RELEASE ?= lakefs
export LAKEFS_NAMESPACE ?= ml-platform-data
export LAKEFS_CHART_REPO ?= https://charts.lakefs.io
export LAKEFS_PORT ?= 18084
export LAKEFS_ADMIN_USERNAME ?= lakefs-admin
export LAKEFS_ADMIN_ACCESS_KEY ?= LAKEFS03333333333333333333
export LAKEFS_ADMIN_SECRET_KEY ?= lakefs-admin-secret-033333333333333333333333333333333333333333
export LAKEFS_AUTH_ENCRYPT_SECRET_KEY ?= 8888888888888888888888888888888888888888888888888888888888888888
export BUILD_FIXTURE_IMAGE ?= ml-platform-study/build-fixture:local
export BUILD_FIXTURE_SECRET_VALUE ?= fixture-build-secret-value
export SYFT_VERSION ?= v1.50.0
export SYFT_IMAGE ?= docker.io/anchore/syft:$(SYFT_VERSION)@sha256:1288ea4c8b38767b4e620c1e312c8cb26b6e887a99b4f07ab6cd19fc6f225026
export TRIVY_VERSION ?= 0.72.0
export TRIVY_IMAGE ?= docker.io/aquasec/trivy:$(TRIVY_VERSION)@sha256:cffe3f5161a47a6823fbd23d985795b3ed72a4c806da4c4df16266c02accdd6f
export COSIGN_VERSION ?= v3.0.6
export COSIGN_IMAGE ?= gcr.io/projectsigstore/cosign:$(COSIGN_VERSION)@sha256:de9c65609e6bde17e6b48de485ee788407c9502fa08b8f4459f595b21f56cd00
export COSIGN_ARTIFACT_DIR ?= config/cosign
export KEYCLOAK_VERSION ?= 26.6.4
export KEYCLOAK_IMAGE ?= quay.io/keycloak/keycloak:$(KEYCLOAK_VERSION)
export KEYCLOAK_NAMESPACE ?= ml-platform-system
export KEYCLOAK_DB_NAMESPACE ?= ml-platform-data
export KEYCLOAK_DB_CLUSTER ?= keycloak-postgres
export KEYCLOAK_DB_NAME ?= keycloak
export KEYCLOAK_DB_USER ?= keycloak
export KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME ?= admin
export KEYCLOAK_PORT ?= 18081
export OIDC_ECHO_CLIENT_ID ?= oidc-echo
export OIDC_ECHO_NAMESPACE ?= ml-platform-system
export OIDC_ECHO_PORT ?= 18082
export OIDC_ECHO_VIEWER_USERNAME ?= oidc-viewer
export OIDC_ECHO_ADMIN_USERNAME ?= oidc-admin
export CLUSTER_POSTGRES_NAME ?= study-postgres
export CLUSTER_POSTGRES_NAMESPACE ?= ml-platform-data
export CLUSTER_POSTGRES_DATABASE ?= study_app
export CLUSTER_POSTGRES_USER ?= study_app
export CLUSTER_POSTGRES_PASSWORD ?= local-dev-cluster-postgres-password
export CLUSTER_GARAGE_NAMESPACE ?= ml-platform-data
export CLUSTER_GARAGE_PORT ?= 13900

.PHONY: test test-versions test-contracts test-dataset-contracts test-baseline-data test-data-transforms test-data-quality test-ingestion test-manifests test-environments compose-up-postgres test-postgres compose-up-object-store test-object-store compose-up-mlflow test-mlflow compose-up-observability test-observability transform-baseline-data ingest-baseline train-baseline test-baseline-training serve-baseline serve-baseline-smoke e2e-phase-00 cluster-create cluster-status cluster-delete apply-namespaces apply-gateway test-gateway apply-tls test-tls apply-network-policy test-network-policy apply-postgres test-cluster-postgres apply-object-storage test-cluster-object-storage apply-data-storage test-data-storage-access test-data-retention apply-lakefs test-lakefs apply-registry test-registry backup-phase-01 verify-backup-phase-01 restore-drill-phase-01 e2e-phase-01 apply-keycloak test-keycloak apply-oidc-fixture test-oidc apply-rbac test-rbac apply-secrets test-secrets test-secret-rotation apply-ci test-ci apply-gitops test-gitops apply-admission-policy test-admission-policy e2e-phase-02 build-fixture test-image sbom-fixture test-sbom scan-fixture test-scan-policy sign-fixture verify-fixture
test:
	python -m pytest

test-versions:
	python -m pytest tests/config

test-contracts:
	python -m pytest tests/contracts

test-dataset-contracts:
	python -m pytest tests/contracts/datasets

test-baseline-data:
	python -m pytest tests/examples

test-data-transforms:
	python -m pytest tests/unit/data

test-data-quality:
	python -m pytest tests/data_quality

test-ingestion:
	python -m pytest tests/integration/ingestion

test-manifests:
	python -m pytest tests/manifests

test-environments:
	python -m pytest tests/manifests/test_environments.py

build-fixture:
	@set -eu; secret_file="$$(mktemp)"; trap 'rm -f "$$secret_file"' EXIT; printf '%s' "$(BUILD_FIXTURE_SECRET_VALUE)" > "$$secret_file"; DOCKER_BUILDKIT=1 docker buildx build --load --provenance=false --secret id=fixture_build_secret,src="$$secret_file" --file build/Dockerfile.build-fixture --tag "$(BUILD_FIXTURE_IMAGE)-first" .; first_image_id="$$(docker image inspect "$(BUILD_FIXTURE_IMAGE)-first" --format '{{.Id}}')"; DOCKER_BUILDKIT=1 docker buildx build --load --provenance=false --secret id=fixture_build_secret,src="$$secret_file" --file build/Dockerfile.build-fixture --tag "$(BUILD_FIXTURE_IMAGE)-second" .; second_image_id="$$(docker image inspect "$(BUILD_FIXTURE_IMAGE)-second" --format '{{.Id}}')"; docker tag "$(BUILD_FIXTURE_IMAGE)-second" "$(BUILD_FIXTURE_IMAGE)"; mkdir -p build/reports; if [ "$$first_image_id" = "$$second_image_id" ]; then ids_match=true; else ids_match=false; fi; { printf 'first_image_id=%s\n' "$$first_image_id"; printf 'second_image_id=%s\n' "$$second_image_id"; printf 'ids_match=%s\n' "$$ids_match"; } > build/reports/build-fixture-digests.txt; cat build/reports/build-fixture-digests.txt

test-image:
	BUILD_FIXTURE_IMAGE="$(BUILD_FIXTURE_IMAGE)" python -m pytest tests/supply-chain

sbom-fixture: build-fixture
	@mkdir -p config/syft
	@docker image inspect "$(BUILD_FIXTURE_IMAGE)" --format '{{.Id}}' > config/syft/build-fixture.image-id
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$(SYFT_IMAGE)" "$(BUILD_FIXTURE_IMAGE)" -o cyclonedx-json > config/syft/build-fixture.cdx.json
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock "$(SYFT_IMAGE)" "$(BUILD_FIXTURE_IMAGE)" -o spdx-json > config/syft/build-fixture.spdx.json
	python config/syft/annotate_fixture_sbom.py config/syft/build-fixture.cdx.json config/syft/build-fixture.spdx.json config/syft/build-fixture-application.json config/syft/build-fixture.image-id

test-sbom:
	BUILD_FIXTURE_IMAGE="$(BUILD_FIXTURE_IMAGE)" python -m pytest tests/supply-chain/sbom

scan-fixture: sbom-fixture
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$(CURDIR):/workspace:ro" "$(TRIVY_IMAGE)" image --config /workspace/config/trivy/trivy.yaml --format json --scanners vuln,secret --ignore-unfixed=false "$(BUILD_FIXTURE_IMAGE)" > config/trivy/build-fixture.scan.json
	python config/license-policy/check_policy.py config/license-policy/policy.json config/syft/build-fixture.spdx.json config/trivy/build-fixture.scan.json

test-scan-policy:
	python -m pytest tests/supply-chain/policy

sign-fixture: scan-fixture
	bash scripts/supply-chain/sign_fixture.sh

verify-fixture:
	bash scripts/supply-chain/verify_fixture.sh
	python -m pytest tests/supply-chain/signing

compose-up-postgres:
	docker compose up -d postgres
	bash config/postgres/wait-for-postgres.sh

test-postgres:
	bash tests/integration/postgres/smoke.sh

compose-up-object-store:
	docker compose up -d garage
	bash config/garage/bootstrap.sh

test-object-store:
	python tests/integration/object_store/smoke_s3.py

compose-up-mlflow: compose-up-postgres compose-up-object-store
	docker compose up -d mlflow
	bash config/mlflow/wait-for-mlflow.sh

test-mlflow:
	docker compose exec -T mlflow python /opt/mlflow/tests/smoke_mlflow.py

compose-up-observability:
	docker compose up -d prometheus grafana
	bash config/prometheus/wait-for-prometheus.sh
	bash config/grafana/wait-for-grafana.sh

test-observability:
	python tests/integration/observability/smoke_observability.py

transform-baseline-data:
	python examples/data_transform/transform_baseline.py

ingest-baseline: apply-lakefs
	python scripts/data/ingest_baseline.py

train-baseline: compose-up-mlflow
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, sklearn" || python -m pip install --no-cache-dir $(BASELINE_TRAIN_PACKAGES); python examples/sklearn_baseline/train.py --config examples/sklearn_baseline/config.yaml'

test-baseline-training: compose-up-mlflow
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src -e RUN_BASELINE_INTEGRATION=1 -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, pytest, sklearn" || python -m pip install --no-cache-dir $(BASELINE_TRAIN_PACKAGES); python -m pytest examples/sklearn_baseline/tests'

serve-baseline: compose-up-mlflow
	@if [ -z "$(BASELINE_MODEL_VERSION)" ]; then echo "BASELINE_MODEL_VERSION is required, for example: BASELINE_MODEL_VERSION=3 make serve-baseline"; exit 2; fi
	docker compose up -d baseline-serving
	@for attempt in $$(seq 1 30); do python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$(BASELINE_SERVE_PORT)/healthz', timeout=2).read()" >/dev/null 2>&1 && exit 0; sleep 2; done; echo "baseline-serving did not become healthy"; exit 1
	@echo "Baseline serving API: http://127.0.0.1:$(BASELINE_SERVE_PORT)"
	@echo "Health: curl http://127.0.0.1:$(BASELINE_SERVE_PORT)/healthz"
	@echo "Metadata: curl http://127.0.0.1:$(BASELINE_SERVE_PORT)/metadata"

serve-baseline-smoke: train-baseline
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src:/workspace -e RUN_BASELINE_SERVICE_INTEGRATION=1 -e BASELINE_MODEL_NAME="$(BASELINE_MODEL_NAME)" -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" sh -ec 'python -c "import boto3, fastapi, httpx, pytest, sklearn, uvicorn" || python -m pip install --no-cache-dir $(BASELINE_SERVE_PACKAGES); export BASELINE_MODEL_VERSION="$$(python -m examples.sklearn_baseline.service.resolve_model_version)"; python -m pytest examples/sklearn_baseline/tests/test_service.py'

e2e-phase-00: compose-up-mlflow
	docker run --rm --network host -v "$(CURDIR):/workspace" -w /workspace -e PYTHONPATH=/workspace/src:/workspace -e RUN_PHASE_00_E2E=1 -e BASELINE_SERVE_PACKAGES="$(BASELINE_SERVE_PACKAGES)" -e MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT) -e MLFLOW_S3_ENDPOINT_URL="$(GARAGE_S3_ENDPOINT)" -e AWS_ACCESS_KEY_ID="$(GARAGE_KEY_ID)" -e AWS_SECRET_ACCESS_KEY="$(GARAGE_SECRET_KEY)" -e AWS_DEFAULT_REGION="$(GARAGE_S3_REGION)" -e GIT_PYTHON_REFRESH=quiet "$(BASELINE_TRAIN_IMAGE)" bash scripts/phase_00/e2e.sh

cluster-create:
	bash scripts/cluster/create-kind.sh

cluster-status:
	bash scripts/cluster/status-kind.sh

cluster-delete:
	bash scripts/cluster/delete-kind.sh

apply-namespaces: cluster-status
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/quotas
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply --dry-run=server -f tests/manifests/fixtures/project-pod-with-resources.yaml
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) apply --dry-run=server -f tests/manifests/fixtures/project-pod-without-resources.yaml >/tmp/ml-platform-unresourced-pod.out 2>&1; then cat /tmp/ml-platform-unresourced-pod.out; echo "expected unresourced project pod to be rejected"; exit 1; else cat /tmp/ml-platform-unresourced-pod.out; echo "project namespace rejects pods without explicit resources"; fi

apply-gateway: apply-namespaces
	@if command -v helm >/dev/null; then helm upgrade --install $(ENVOY_GATEWAY_RELEASE) oci://docker.io/envoyproxy/gateway-helm --version $(ENVOY_GATEWAY_VERSION) --namespace $(ENVOY_GATEWAY_NAMESPACE) --create-namespace --values platform/charts/envoy-gateway/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(ENVOY_GATEWAY_RELEASE) oci://docker.io/envoyproxy/gateway-helm --version $(ENVOY_GATEWAY_VERSION) --namespace $(ENVOY_GATEWAY_NAMESPACE) --create-namespace --values platform/charts/envoy-gateway/values-dev-kind.yaml; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(ENVOY_GATEWAY_NAMESPACE) deployment/envoy-gateway --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/gateway
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace ml-platform-project-housing deployment/gateway-echo --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m gatewayclass/ml-platform-envoy --for=condition=Accepted
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(ENVOY_GATEWAY_NAMESPACE) gateway/ml-platform-local --for=condition=Programmed
	@echo "Gateway route: curl -H 'Host: $(GATEWAY_HOST)' http://127.0.0.1:$(GATEWAY_HTTP_PORT)/gateway-echo"

test-gateway:
	RUN_GATEWAY_INTEGRATION=1 GATEWAY_HOST=$(GATEWAY_HOST) GATEWAY_HTTP_PORT=$(GATEWAY_HTTP_PORT) KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) python -m pytest tests/integration/gateway

apply-tls: apply-gateway
	@if command -v helm >/dev/null; then helm upgrade --install $(CERT_MANAGER_RELEASE) $(CERT_MANAGER_CHART) --version $(CERT_MANAGER_VERSION) --namespace $(CERT_MANAGER_NAMESPACE) --create-namespace --values platform/charts/cert-manager/values-dev-kind.yaml --wait --timeout 5m; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(CERT_MANAGER_RELEASE) $(CERT_MANAGER_CHART) --version $(CERT_MANAGER_VERSION) --namespace $(CERT_MANAGER_NAMESPACE) --create-namespace --values platform/charts/cert-manager/values-dev-kind.yaml --wait --timeout 5m; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/tls
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(CERT_MANAGER_NAMESPACE) certificate/ml-platform-local-ca --for=condition=Ready
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(CERT_MANAGER_NAMESPACE) certificate/gateway-echo-tls --for=condition=Ready
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(ENVOY_GATEWAY_NAMESPACE) gateway/ml-platform-local --for=condition=Programmed
	kubectl --context kind-$(KIND_CLUSTER_NAME) get secret ml-platform-local-ca --namespace $(CERT_MANAGER_NAMESPACE) --output=jsonpath='{.data.ca\.crt}' | base64 --decode > "$(TLS_CA_BUNDLE)"
	@echo "Local CA bundle written to $(TLS_CA_BUNDLE)"
	@echo "HTTPS route: curl --cacert $(TLS_CA_BUNDLE) --resolve $(GATEWAY_HOST):$(GATEWAY_HTTPS_PORT):127.0.0.1 https://$(GATEWAY_HOST):$(GATEWAY_HTTPS_PORT)/gateway-echo"

test-tls:
	RUN_TLS_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) GATEWAY_HOST=$(GATEWAY_HOST) GATEWAY_HTTP_PORT=$(GATEWAY_HTTP_PORT) GATEWAY_HTTPS_PORT=$(GATEWAY_HTTPS_PORT) TLS_CA_BUNDLE=$(TLS_CA_BUNDLE) python -m pytest tests/integration/tls

apply-network-policy: apply-namespaces
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/base/network-policies

test-network-policy:
	RUN_NETWORK_POLICY_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) python -m pytest tests/integration/network

apply-postgres: apply-namespaces
	@if command -v helm >/dev/null; then helm upgrade --install $(CLOUDNATIVEPG_RELEASE) cloudnative-pg --repo $(CLOUDNATIVEPG_CHART_REPO) --version $(CLOUDNATIVEPG_CHART_VERSION) --namespace $(CLOUDNATIVEPG_NAMESPACE) --create-namespace --values platform/charts/cloudnativepg/values-dev-kind.yaml --wait --timeout 5m; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(CLOUDNATIVEPG_RELEASE) cloudnative-pg --repo $(CLOUDNATIVEPG_CHART_REPO) --version $(CLOUDNATIVEPG_CHART_VERSION) --namespace $(CLOUDNATIVEPG_NAMESPACE) --create-namespace --values platform/charts/cloudnativepg/values-dev-kind.yaml --wait --timeout 5m; fi
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic $(CLUSTER_POSTGRES_NAME)-app --namespace $(CLUSTER_POSTGRES_NAMESPACE) --type=kubernetes.io/basic-auth --from-literal=username="$(CLUSTER_POSTGRES_USER)" --from-literal=password="$(CLUSTER_POSTGRES_PASSWORD)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/databases
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(CLUSTER_POSTGRES_NAMESPACE) cluster/$(CLUSTER_POSTGRES_NAME) --for=condition=Ready
	@echo "CloudNativePG cluster: $(CLUSTER_POSTGRES_NAME).rw.$(CLUSTER_POSTGRES_NAMESPACE).svc.cluster.local:5432/$(CLUSTER_POSTGRES_DATABASE)"

test-cluster-postgres:
	RUN_CLOUDNATIVEPG_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) CLUSTER_POSTGRES_NAME=$(CLUSTER_POSTGRES_NAME) CLUSTER_POSTGRES_NAMESPACE=$(CLUSTER_POSTGRES_NAMESPACE) CLUSTER_POSTGRES_DATABASE=$(CLUSTER_POSTGRES_DATABASE) CLUSTER_POSTGRES_USER=$(CLUSTER_POSTGRES_USER) python -m pytest tests/integration/cloudnativepg

apply-object-storage: apply-namespaces
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic garage-credentials --namespace $(CLUSTER_GARAGE_NAMESPACE) --from-literal=rpc-secret="$(GARAGE_RPC_SECRET)" --from-literal=admin-token="$(GARAGE_ADMIN_TOKEN)" --from-literal=metrics-token="$(GARAGE_METRICS_TOKEN)" --from-literal=access-key-id="$(GARAGE_KEY_ID)" --from-literal=secret-access-key="$(GARAGE_SECRET_KEY)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	kubectl --context kind-$(KIND_CLUSTER_NAME) delete job garage-bootstrap --namespace $(CLUSTER_GARAGE_NAMESPACE) --ignore-not-found=true
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/storage
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(CLUSTER_GARAGE_NAMESPACE) statefulset/garage --for=jsonpath='{.status.readyReplicas}'=1
	bash clusters/dev/storage/bootstrap-garage.sh
	kubectl --context kind-$(KIND_CLUSTER_NAME) delete job garage-bootstrap --namespace $(CLUSTER_GARAGE_NAMESPACE) --ignore-not-found=true
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f clusters/dev/storage/bootstrap-job.yaml
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(CLUSTER_GARAGE_NAMESPACE) job/garage-bootstrap --for=condition=Complete
	@echo "Garage S3 service: garage-s3.$(CLUSTER_GARAGE_NAMESPACE).svc.cluster.local:3900"

test-cluster-object-storage:
	RUN_CLUSTER_OBJECT_STORE_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) CLUSTER_GARAGE_NAMESPACE=$(CLUSTER_GARAGE_NAMESPACE) CLUSTER_GARAGE_PORT=$(CLUSTER_GARAGE_PORT) GARAGE_BUCKET=$(GARAGE_BUCKET) GARAGE_KEY_ID=$(GARAGE_KEY_ID) GARAGE_SECRET_KEY=$(GARAGE_SECRET_KEY) GARAGE_S3_REGION=$(GARAGE_S3_REGION) GARAGE_S3_ENDPOINT=http://127.0.0.1:$(CLUSTER_GARAGE_PORT) python -m pytest tests/integration/object_store

apply-data-storage: apply-object-storage
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/data-storage
	bash scripts/data/bootstrap/data-storage.sh

test-data-storage-access:
	RUN_DATA_STORAGE_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) CLUSTER_GARAGE_NAMESPACE=$(CLUSTER_GARAGE_NAMESPACE) CLUSTER_GARAGE_PORT=$(CLUSTER_GARAGE_PORT) GARAGE_S3_REGION=$(GARAGE_S3_REGION) GARAGE_S3_ENDPOINT=http://127.0.0.1:$(CLUSTER_GARAGE_PORT) python -m pytest tests/integration/data_storage

test-data-retention:
	python -m pytest tests/integration/data_storage/retention

apply-lakefs: apply-postgres apply-data-storage
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic lakefs-secrets --namespace $(LAKEFS_NAMESPACE) --from-literal=database_connection_string="postgres://$(CLUSTER_POSTGRES_USER):$(CLUSTER_POSTGRES_PASSWORD)@$(CLUSTER_POSTGRES_NAME)-rw.$(CLUSTER_POSTGRES_NAMESPACE).svc.cluster.local:5432/$(CLUSTER_POSTGRES_DATABASE)?sslmode=disable" --from-literal=auth_encrypt_secret_key="$(LAKEFS_AUTH_ENCRYPT_SECRET_KEY)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic lakefs-admin-credentials --namespace $(LAKEFS_NAMESPACE) --from-literal=username="$(LAKEFS_ADMIN_USERNAME)" --from-literal=access-key-id="$(LAKEFS_ADMIN_ACCESS_KEY)" --from-literal=secret-access-key="$(LAKEFS_ADMIN_SECRET_KEY)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@if command -v helm >/dev/null; then helm upgrade --install $(LAKEFS_RELEASE) lakefs --repo $(LAKEFS_CHART_REPO) --version $(LAKEFS_CHART_VERSION) --namespace $(LAKEFS_NAMESPACE) --create-namespace --values platform/charts/lakefs/values-dev-kind.yaml --wait --timeout 5m; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(LAKEFS_RELEASE) lakefs --repo $(LAKEFS_CHART_REPO) --version $(LAKEFS_CHART_VERSION) --namespace $(LAKEFS_NAMESPACE) --create-namespace --values platform/charts/lakefs/values-dev-kind.yaml --wait --timeout 5m; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(LAKEFS_NAMESPACE) deployment/$(LAKEFS_RELEASE) --for=condition=Available
	@echo "lakeFS service: $(LAKEFS_RELEASE).$(LAKEFS_NAMESPACE).svc.cluster.local:80"
	@echo "Local access: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(LAKEFS_NAMESPACE) svc/$(LAKEFS_RELEASE) $(LAKEFS_PORT):80"

test-lakefs:
	RUN_LAKEFS_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) LAKEFS_NAMESPACE=$(LAKEFS_NAMESPACE) LAKEFS_PORT=$(LAKEFS_PORT) LAKEFS_ADMIN_USERNAME=$(LAKEFS_ADMIN_USERNAME) python -m pytest tests/integration/lakefs

apply-registry: apply-namespaces
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic harbor-admin --namespace $(HARBOR_NAMESPACE) --from-literal=HARBOR_ADMIN_PASSWORD="$(HARBOR_ADMIN_PASSWORD)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@if command -v helm >/dev/null; then helm upgrade --install $(HARBOR_RELEASE) harbor --repo $(HARBOR_CHART_REPO) --version $(HARBOR_CHART_VERSION) --namespace $(HARBOR_NAMESPACE) --create-namespace --values platform/charts/harbor/values-dev-kind.yaml --set externalURL=http://$(CLUSTER_REGISTRY_HOST); else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(HARBOR_RELEASE) harbor --repo $(HARBOR_CHART_REPO) --version $(HARBOR_CHART_VERSION) --namespace $(HARBOR_NAMESPACE) --create-namespace --values platform/charts/harbor/values-dev-kind.yaml --set externalURL=http://$(CLUSTER_REGISTRY_HOST); fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout status deployment/$(HARBOR_RELEASE)-registry --namespace $(HARBOR_NAMESPACE) --timeout=5m
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(HARBOR_NAMESPACE) deployment/$(HARBOR_RELEASE)-core --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(HARBOR_NAMESPACE) deployment/$(HARBOR_RELEASE)-nginx --for=condition=Available
	@echo "Harbor registry: http://$(CLUSTER_REGISTRY_HOST)"

test-registry:
	RUN_REGISTRY_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) HARBOR_NAMESPACE=$(HARBOR_NAMESPACE) HARBOR_ADMIN_USER=$(HARBOR_ADMIN_USER) HARBOR_ADMIN_PASSWORD=$(HARBOR_ADMIN_PASSWORD) CLUSTER_REGISTRY_HOST=$(CLUSTER_REGISTRY_HOST) CLUSTER_REGISTRY_PORT=$(CLUSTER_REGISTRY_PORT) python -m pytest tests/integration/registry

backup-phase-01: apply-postgres apply-object-storage apply-registry
	kubectl --context kind-$(KIND_CLUSTER_NAME) create namespace $(VELERO_NAMESPACE) --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@set -e; credential_file=$$(mktemp); printf '[default]\naws_access_key_id=%s\naws_secret_access_key=%s\n' "$(GARAGE_KEY_ID)" "$(GARAGE_SECRET_KEY)" > "$$credential_file"; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic velero-credentials --namespace $(VELERO_NAMESPACE) --from-file=cloud="$$credential_file" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -; rm -f "$$credential_file"
	@if command -v helm >/dev/null; then helm upgrade --install $(VELERO_RELEASE) velero --repo $(VELERO_CHART_REPO) --version $(VELERO_CHART_VERSION) --namespace $(VELERO_NAMESPACE) --create-namespace --values platform/charts/velero/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(VELERO_RELEASE) velero --repo $(VELERO_CHART_REPO) --version $(VELERO_CHART_VERSION) --namespace $(VELERO_NAMESPACE) --create-namespace --values platform/charts/velero/values-dev-kind.yaml; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout status deployment/$(VELERO_RELEASE) --namespace $(VELERO_NAMESPACE) --timeout=5m
	bash scripts/backup/phase-01-backup.sh

verify-backup-phase-01:
	bash scripts/backup/inventory-phase-01-backup.sh
	@RUN_PHASE_01_BACKUP_VERIFY=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) VELERO_NAMESPACE=$(VELERO_NAMESPACE) GARAGE_BUCKET=$(GARAGE_BUCKET) GARAGE_KEY_ID=$(GARAGE_KEY_ID) GARAGE_SECRET_KEY=$(GARAGE_SECRET_KEY) HARBOR_ADMIN_PASSWORD=$(HARBOR_ADMIN_PASSWORD) CLUSTER_POSTGRES_PASSWORD=$(CLUSTER_POSTGRES_PASSWORD) python -m pytest tests/dr

restore-drill-phase-01: backup-phase-01
	python -m tests.dr.phase_01.restore_drill
	@RUN_PHASE_01_RESTORE_DRILL=1 python -m pytest tests/dr/phase_01

e2e-phase-01:
	python -m scripts.phase_01.e2e
	@RUN_PHASE_01_E2E=1 python -m pytest tests/e2e/phase_01

apply-keycloak: cluster-create apply-tls apply-postgres
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) get secret keycloak-bootstrap-admin --namespace $(KEYCLOAK_NAMESPACE) >/dev/null 2>&1; then echo "secret/keycloak-bootstrap-admin unchanged"; else admin_password="$${KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD:-}"; if [ -z "$$admin_password" ]; then admin_password="$$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"; fi; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic keycloak-bootstrap-admin --namespace $(KEYCLOAK_NAMESPACE) --from-literal=username="$(KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME)" --from-literal=password="$$admin_password"; fi
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) get secret $(KEYCLOAK_DB_CLUSTER)-app --namespace $(KEYCLOAK_DB_NAMESPACE) >/dev/null 2>&1; then echo "secret/$(KEYCLOAK_DB_CLUSTER)-app unchanged"; else db_password="$${KEYCLOAK_DB_PASSWORD:-}"; if [ -z "$$db_password" ]; then db_password="$$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"; fi; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic $(KEYCLOAK_DB_CLUSTER)-app --namespace $(KEYCLOAK_DB_NAMESPACE) --type=kubernetes.io/basic-auth --from-literal=username="$(KEYCLOAK_DB_USER)" --from-literal=password="$$db_password"; fi
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) get secret keycloak-database --namespace $(KEYCLOAK_NAMESPACE) >/dev/null 2>&1; then echo "secret/keycloak-database unchanged"; else db_username="$$(kubectl --context kind-$(KIND_CLUSTER_NAME) get secret $(KEYCLOAK_DB_CLUSTER)-app --namespace $(KEYCLOAK_DB_NAMESPACE) -o jsonpath='{.data.username}' | base64 --decode)"; db_password="$$(kubectl --context kind-$(KIND_CLUSTER_NAME) get secret $(KEYCLOAK_DB_CLUSTER)-app --namespace $(KEYCLOAK_DB_NAMESPACE) -o jsonpath='{.data.password}' | base64 --decode)"; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic keycloak-database --namespace $(KEYCLOAK_NAMESPACE) --from-literal=username="$$db_username" --from-literal=password="$$db_password"; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/identity
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(KEYCLOAK_DB_NAMESPACE) cluster/$(KEYCLOAK_DB_CLUSTER) --for=condition=Ready
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(KEYCLOAK_NAMESPACE) deployment/keycloak --for=condition=Available
	@echo "Keycloak service: keycloak.$(KEYCLOAK_NAMESPACE).svc.cluster.local:8080"
	@echo "Local access: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(KEYCLOAK_NAMESPACE) svc/keycloak $(KEYCLOAK_PORT):8080"

test-keycloak:
	@RUN_KEYCLOAK_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) KEYCLOAK_NAMESPACE=$(KEYCLOAK_NAMESPACE) KEYCLOAK_DB_NAMESPACE=$(KEYCLOAK_DB_NAMESPACE) KEYCLOAK_PORT=$(KEYCLOAK_PORT) python -m pytest tests/integration/keycloak

apply-oidc-fixture: apply-keycloak
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) get secret oidc-echo-client --namespace $(OIDC_ECHO_NAMESPACE) >/dev/null 2>&1; then echo "secret/oidc-echo-client unchanged"; else client_secret="$${OIDC_ECHO_CLIENT_SECRET:-}"; if [ -z "$$client_secret" ]; then client_secret="$$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"; fi; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic oidc-echo-client --namespace $(OIDC_ECHO_NAMESPACE) --from-literal=client-id="$(OIDC_ECHO_CLIENT_ID)" --from-literal=client-secret="$$client_secret"; fi
	@if kubectl --context kind-$(KIND_CLUSTER_NAME) get secret oidc-echo-test-users --namespace $(OIDC_ECHO_NAMESPACE) >/dev/null 2>&1; then echo "secret/oidc-echo-test-users unchanged"; else viewer_password="$${OIDC_ECHO_VIEWER_PASSWORD:-}"; admin_password="$${OIDC_ECHO_ADMIN_PASSWORD:-}"; if [ -z "$$viewer_password" ]; then viewer_password="$$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"; fi; if [ -z "$$admin_password" ]; then admin_password="$$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"; fi; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic oidc-echo-test-users --namespace $(OIDC_ECHO_NAMESPACE) --from-literal=viewer-username="$(OIDC_ECHO_VIEWER_USERNAME)" --from-literal=viewer-password="$$viewer_password" --from-literal=admin-username="$(OIDC_ECHO_ADMIN_USERNAME)" --from-literal=admin-password="$$admin_password"; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) create configmap oidc-echo-app --namespace $(OIDC_ECHO_NAMESPACE) --from-file=app.py=examples/oidc_echo/app.py --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	kubectl --context kind-$(KIND_CLUSTER_NAME) delete job oidc-echo-client-registration --namespace $(OIDC_ECHO_NAMESPACE) --ignore-not-found=true
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/identity/clients
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(OIDC_ECHO_NAMESPACE) job/oidc-echo-client-registration --for=condition=Complete
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout restart --namespace $(OIDC_ECHO_NAMESPACE) deployment/oidc-echo
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(OIDC_ECHO_NAMESPACE) deployment/oidc-echo --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(OIDC_ECHO_NAMESPACE) httproute/oidc-echo --for=jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}'=True
	@echo "OIDC echo fixture: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(OIDC_ECHO_NAMESPACE) svc/oidc-echo $(OIDC_ECHO_PORT):8080"

test-oidc:
	@RUN_OIDC_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) KEYCLOAK_NAMESPACE=$(KEYCLOAK_NAMESPACE) KEYCLOAK_PORT=$(KEYCLOAK_PORT) OIDC_ECHO_NAMESPACE=$(OIDC_ECHO_NAMESPACE) OIDC_ECHO_PORT=$(OIDC_ECHO_PORT) python -m pytest tests/integration/oidc

apply-rbac: apply-namespaces
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/base/rbac

test-rbac:
	@RUN_RBAC_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) python -m pytest tests/integration/rbac

apply-secrets: apply-postgres
	@if command -v helm >/dev/null; then helm upgrade --install $(OPENBAO_RELEASE) openbao --repo $(OPENBAO_CHART_REPO) --version $(OPENBAO_CHART_VERSION) --namespace $(OPENBAO_NAMESPACE) --create-namespace --values platform/charts/openbao/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(OPENBAO_RELEASE) openbao --repo $(OPENBAO_CHART_REPO) --version $(OPENBAO_CHART_VERSION) --namespace $(OPENBAO_NAMESPACE) --create-namespace --values platform/charts/openbao/values-dev-kind.yaml; fi
	@if command -v helm >/dev/null; then helm upgrade --install $(EXTERNAL_SECRETS_RELEASE) external-secrets --repo $(EXTERNAL_SECRETS_CHART_REPO) --version $(EXTERNAL_SECRETS_CHART_VERSION) --namespace $(EXTERNAL_SECRETS_NAMESPACE) --create-namespace --values platform/charts/external-secrets/values-dev-kind.yaml --wait --timeout 5m; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(EXTERNAL_SECRETS_RELEASE) external-secrets --repo $(EXTERNAL_SECRETS_CHART_REPO) --version $(EXTERNAL_SECRETS_CHART_VERSION) --namespace $(EXTERNAL_SECRETS_NAMESPACE) --create-namespace --values platform/charts/external-secrets/values-dev-kind.yaml --wait --timeout 5m; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(OPENBAO_NAMESPACE) pod/$(OPENBAO_RELEASE)-0 --for=jsonpath='{.status.phase}'=Running
	@set -e; status="$$(kubectl --context kind-$(KIND_CLUSTER_NAME) exec --namespace $(OPENBAO_NAMESPACE) $(OPENBAO_RELEASE)-0 -- bao status -format=json 2>/dev/null || true)"; if printf '%s' "$$status" | python -c 'import json,sys; data=json.load(sys.stdin); raise SystemExit(0 if data.get("initialized") else 1)' >/dev/null 2>&1; then echo "openbao already initialized"; else init_file="$$(mktemp)"; kubectl --context kind-$(KIND_CLUSTER_NAME) exec --namespace $(OPENBAO_NAMESPACE) $(OPENBAO_RELEASE)-0 -- bao operator init -key-shares=1 -key-threshold=1 -format=json > "$$init_file"; root_token="$$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["root_token"])' "$$init_file")"; unseal_key="$$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["unseal_keys_b64"][0])' "$$init_file")"; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic openbao-bootstrap --namespace $(OPENBAO_NAMESPACE) --from-literal=root-token="$$root_token" --from-literal=unseal-key="$$unseal_key" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -; rm -f "$$init_file"; echo "openbao initialized and bootstrap material stored in Kubernetes Secret for study use"; fi
	@unseal_key="$$(kubectl --context kind-$(KIND_CLUSTER_NAME) get secret openbao-bootstrap --namespace $(OPENBAO_NAMESPACE) -o jsonpath='{.data.unseal-key}' | base64 --decode)"; kubectl --context kind-$(KIND_CLUSTER_NAME) exec --namespace $(OPENBAO_NAMESPACE) $(OPENBAO_RELEASE)-0 -- bao operator unseal "$$unseal_key" >/dev/null || true
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(OPENBAO_NAMESPACE) pod/$(OPENBAO_RELEASE)-0 --for=condition=Ready
	@root_token="$$(kubectl --context kind-$(KIND_CLUSTER_NAME) get secret openbao-bootstrap --namespace $(OPENBAO_NAMESPACE) -o jsonpath='{.data.root-token}' | base64 --decode)"; generated_password="$$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"; kubectl --context kind-$(KIND_CLUSTER_NAME) exec --namespace $(OPENBAO_NAMESPACE) $(OPENBAO_RELEASE)-0 -- sh -ec 'export BAO_TOKEN="$$1"; generated_password="$$2"; bao secrets enable -path=kv kv-v2 >/dev/null 2>&1 || true; if ! bao kv get kv/projects/housing/database/study-reader >/dev/null 2>&1; then bao kv put kv/projects/housing/database/study-reader username=housing_reader password="$$generated_password" database=study_app >/dev/null; fi; printf "%s\n" "path \"kv/data/projects/housing/database/study-reader\" {" "  capabilities = [\"read\"]" "}" "path \"kv/metadata/projects/housing/database/study-reader\" {" "  capabilities = [\"read\"]" "}" > /tmp/external-secrets-housing-reader.hcl; bao policy write external-secrets-housing-reader /tmp/external-secrets-housing-reader.hcl >/dev/null; bao token create -policy=external-secrets-housing-reader -period=24h -format=json' sh "$$root_token" "$$generated_password" > /tmp/ml-platform-openbao-reader-token.json
	@reader_token="$$(python -c 'import json; print(json.load(open("/tmp/ml-platform-openbao-reader-token.json"))["auth"]["client_token"])')"; kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic openbao-housing-reader-token --namespace $(SECRETS_EXAMPLE_NAMESPACE) --from-literal=token="$$reader_token" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -; rm -f /tmp/ml-platform-openbao-reader-token.json
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/secrets
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(SECRETS_EXAMPLE_NAMESPACE) secretstore/openbao-housing --for=condition=Ready
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m --namespace $(SECRETS_EXAMPLE_NAMESPACE) externalsecret/housing-database-credential --for=condition=Ready
	@echo "Synced example Secret: housing-database-credential in $(SECRETS_EXAMPLE_NAMESPACE)"

test-secrets:
	@RUN_SECRETS_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) OPENBAO_NAMESPACE=$(OPENBAO_NAMESPACE) SECRETS_EXAMPLE_NAMESPACE=$(SECRETS_EXAMPLE_NAMESPACE) python -m pytest tests/integration/secrets

test-secret-rotation:
	@RUN_SECRET_ROTATION_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) OPENBAO_NAMESPACE=$(OPENBAO_NAMESPACE) KEYCLOAK_NAMESPACE=$(KEYCLOAK_NAMESPACE) KEYCLOAK_PORT=$(KEYCLOAK_PORT) OIDC_ECHO_NAMESPACE=$(OIDC_ECHO_NAMESPACE) OIDC_ECHO_PORT=$(OIDC_ECHO_PORT) python -m pytest tests/integration/secrets/rotation

apply-ci: apply-registry
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k clusters/dev/ci
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic forgejo-admin --namespace $(FORGEJO_NAMESPACE) --from-literal=username="$(FORGEJO_ADMIN_USERNAME)" --from-literal=password="$(FORGEJO_ADMIN_PASSWORD)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic woodpecker-secrets --namespace $(WOODPECKER_NAMESPACE) --from-literal=WOODPECKER_AGENT_SECRET="$(WOODPECKER_AGENT_SECRET)" --from-literal=WOODPECKER_FORGEJO_CLIENT="$(WOODPECKER_FORGEJO_CLIENT)" --from-literal=WOODPECKER_FORGEJO_SECRET="$(WOODPECKER_FORGEJO_SECRET)" --from-literal=WOODPECKER_SECRET="$(WOODPECKER_SECRET)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	@if command -v helm >/dev/null; then helm upgrade --install $(FORGEJO_RELEASE) $(FORGEJO_CHART) --version $(FORGEJO_CHART_VERSION) --namespace $(FORGEJO_NAMESPACE) --create-namespace --values platform/charts/forgejo/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(FORGEJO_RELEASE) $(FORGEJO_CHART) --version $(FORGEJO_CHART_VERSION) --namespace $(FORGEJO_NAMESPACE) --create-namespace --values platform/charts/forgejo/values-dev-kind.yaml; fi
	@if command -v helm >/dev/null; then helm upgrade --install $(WOODPECKER_RELEASE) $(WOODPECKER_CHART) --version $(WOODPECKER_CHART_VERSION) --namespace $(WOODPECKER_NAMESPACE) --create-namespace --values platform/charts/woodpecker/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(WOODPECKER_RELEASE) $(WOODPECKER_CHART) --version $(WOODPECKER_CHART_VERSION) --namespace $(WOODPECKER_NAMESPACE) --create-namespace --values platform/charts/woodpecker/values-dev-kind.yaml; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(FORGEJO_NAMESPACE) deployment/forgejo --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout status --timeout=5m --namespace $(WOODPECKER_NAMESPACE) statefulset/woodpecker-server
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout status --timeout=5m --namespace $(WOODPECKER_NAMESPACE) statefulset/woodpecker-agent
	@echo "Forgejo: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(FORGEJO_NAMESPACE) svc/forgejo-http 13000:3000"
	@echo "Woodpecker: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(WOODPECKER_NAMESPACE) svc/woodpecker-server 18000:80"

test-ci:
	@RUN_CI_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) CI_NAMESPACE=$(WOODPECKER_NAMESPACE) HARBOR_NAMESPACE=$(HARBOR_NAMESPACE) HARBOR_ADMIN_USER=$(HARBOR_ADMIN_USER) HARBOR_ADMIN_PASSWORD=$(HARBOR_ADMIN_PASSWORD) CLUSTER_REGISTRY_HOST=$(CLUSTER_REGISTRY_HOST) CLUSTER_REGISTRY_PORT=$(CLUSTER_REGISTRY_PORT) python -m pytest tests/integration/ci

apply-gitops: apply-keycloak
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f clusters/dev/gitops/namespace.yaml
	@kubectl --context kind-$(KIND_CLUSTER_NAME) create secret generic argocd-oidc-client --namespace $(ARGOCD_NAMESPACE) --from-literal=clientSecret="$(ARGOCD_OIDC_CLIENT_SECRET)" --dry-run=client -o yaml | kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f -
	KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) KEYCLOAK_NAMESPACE=$(KEYCLOAK_NAMESPACE) KEYCLOAK_PORT=$(KEYCLOAK_PORT) ARGOCD_NAMESPACE=$(ARGOCD_NAMESPACE) ARGOCD_PORT=$(ARGOCD_PORT) python clusters/dev/gitops/register_argocd_oidc.py
	@if command -v helm >/dev/null; then helm upgrade --install $(ARGOCD_RELEASE) argo-cd --repo $(ARGOCD_CHART_REPO) --version $(ARGOCD_CHART_VERSION) --namespace $(ARGOCD_NAMESPACE) --create-namespace --values platform/charts/argocd/values-dev-kind.yaml; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(ARGOCD_RELEASE) argo-cd --repo $(ARGOCD_CHART_REPO) --version $(ARGOCD_CHART_VERSION) --namespace $(ARGOCD_NAMESPACE) --create-namespace --values platform/charts/argocd/values-dev-kind.yaml; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) rollout status --timeout=5m --namespace $(ARGOCD_NAMESPACE) statefulset/argocd-application-controller
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(ARGOCD_NAMESPACE) deployment/argocd-server --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(ARGOCD_NAMESPACE) deployment/argocd-repo-server --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(ARGOCD_NAMESPACE) deployment/argocd-redis --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -f clusters/dev/gitops/root-application.yaml
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(ARGOCD_NAMESPACE) application/ci-fixture --for=jsonpath='{.status.sync.status}'=Synced
	@echo "Argo CD: kubectl --context kind-$(KIND_CLUSTER_NAME) port-forward -n $(ARGOCD_NAMESPACE) svc/argocd-server $(ARGOCD_PORT):80"

test-gitops:
	@RUN_GITOPS_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) ARGOCD_NAMESPACE=$(ARGOCD_NAMESPACE) ARGOCD_PORT=$(ARGOCD_PORT) python -m pytest tests/integration/gitops

apply-admission-policy: apply-namespaces
	@if command -v helm >/dev/null; then helm upgrade --install $(KYVERNO_RELEASE) kyverno --repo $(KYVERNO_CHART_REPO) --version $(KYVERNO_CHART_VERSION) --namespace $(KYVERNO_NAMESPACE) --create-namespace --values platform/charts/kyverno/values-dev-kind.yaml --wait --timeout 5m; else if [ ! -f "$(KUBECONFIG)" ]; then echo "helm is not installed and KUBECONFIG does not point to a readable file: $(KUBECONFIG)"; exit 127; fi; docker run --rm --network host -v "$(KUBECONFIG):/root/.kube/config:ro" -v "$(CURDIR):/workspace" -w /workspace "$(HELM_RUNNER_IMAGE)" upgrade --install $(KYVERNO_RELEASE) kyverno --repo $(KYVERNO_CHART_REPO) --version $(KYVERNO_CHART_VERSION) --namespace $(KYVERNO_NAMESPACE) --create-namespace --values platform/charts/kyverno/values-dev-kind.yaml --wait --timeout 5m; fi
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=5m --namespace $(KYVERNO_NAMESPACE) deployment/$(KYVERNO_RELEASE)-admission-controller --for=condition=Available
	kubectl --context kind-$(KIND_CLUSTER_NAME) apply -k platform/policies/supply-chain
	kubectl --context kind-$(KIND_CLUSTER_NAME) wait --timeout=3m clusterpolicy/verify-project-signed-images --for=condition=Ready
	@echo "Kyverno admission policy installed. Project namespaces enforce signed-image checks; platform namespaces remain audit rollout."

test-admission-policy:
	@RUN_ADMISSION_INTEGRATION=1 KIND_CLUSTER_NAME=$(KIND_CLUSTER_NAME) python -m pytest tests/integration/admission

e2e-phase-02:
	python -m scripts.phase_02.e2e
	@RUN_PHASE_02_E2E=1 python -m pytest tests/e2e/phase_02
