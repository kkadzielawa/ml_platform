# Local CA runbook

`01.06` adds study-only TLS for the local kind gateway. It uses cert-manager to create a private local CA and issue the `gateway.ml-platform.local` certificate used by Envoy Gateway.

This CA is for local study only. Do not reuse it for public services, shared environments, or production workloads.

## Apply and test

```bash
make apply-tls
make test-tls
```

`make apply-tls` writes the CA bundle to:

```text
/tmp/ml-platform-local-ca.crt
```

## Manual HTTPS smoke test

Use `curl --resolve` so the local hostname resolves to the kind gateway port on this laptop:

```bash
curl --cacert /tmp/ml-platform-local-ca.crt \
  --resolve gateway.ml-platform.local:8443:127.0.0.1 \
  https://gateway.ml-platform.local:8443/gateway-echo
```

## Plain HTTP policy

Plain HTTP for the echo route redirects to HTTPS:

```bash
curl -I -H 'Host: gateway.ml-platform.local' \
  http://127.0.0.1:8080/gateway-echo
```

The expected status is `301` with a `Location` header pointing to:

```text
https://gateway.ml-platform.local:8443/gateway-echo
```

## Inspecting certificates

```bash
kubectl --context kind-ml-platform-study-dev \
  get certificate -n ml-platform-system

kubectl --context kind-ml-platform-study-dev \
  describe certificate gateway-echo-tls -n ml-platform-system
```

Local operating-system trust-store installation is intentionally not automated. If you want browser trust, import `/tmp/ml-platform-local-ca.crt` into your OS/browser trust store manually and map `gateway.ml-platform.local` to `127.0.0.1` in your local hosts file.
