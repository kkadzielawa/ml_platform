import base64
import json
import os
import time
import urllib.parse
import urllib.request


def main():
    prometheus_url = os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")
    grafana_url = os.environ.get("GRAFANA_URL", "http://127.0.0.1:3000").rstrip("/")

    prometheus_query = 'up{job="prometheus"}'
    encoded_prometheus_query = urllib.parse.urlencode({"query": prometheus_query})
    assert read_json(f"{prometheus_url}/api/v1/query?{encoded_prometheus_query}")["status"] == "success"
    wait_for_prometheus_metric(prometheus_url, prometheus_query, expected_value="1")

    grafana_health = read_json(f"{grafana_url}/api/health")
    assert grafana_health["database"] == "ok"

    auth_header = basic_auth(
        os.environ.get("GRAFANA_ADMIN_USER", "admin"),
        os.environ.get("GRAFANA_ADMIN_PASSWORD", "local-dev-grafana-password"),
    )
    datasource = read_json(f"{grafana_url}/api/datasources/uid/prometheus", headers=auth_header)
    assert datasource["name"] == "Prometheus"
    assert datasource["url"] == "http://prometheus:9090"

    search = read_json(
        f"{grafana_url}/api/search?{urllib.parse.urlencode({'query': 'Service Health'})}",
        headers=auth_header,
    )
    assert any(item["uid"] == "service-health" for item in search)


def wait_for_prometheus_metric(prometheus_url, query, expected_value):
    encoded_query = urllib.parse.urlencode({"query": query})
    for _ in range(30):
        payload = read_json(f"{prometheus_url}/api/v1/query?{encoded_query}")
        results = payload["data"]["result"]
        if results and results[0]["value"][1] == expected_value:
            return
        time.sleep(1)
    raise AssertionError(f"Prometheus query did not return {expected_value}: {query}")


def read_json(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


if __name__ == "__main__":
    main()
