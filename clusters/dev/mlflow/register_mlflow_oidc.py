from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


KEYCLOAK_URL = os.environ["KEYCLOAK_URL"].rstrip("/")
REALM = os.environ.get("KEYCLOAK_REALM", "ml-platform-study")
ADMIN_USERNAME = os.environ["KEYCLOAK_ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["KEYCLOAK_ADMIN_PASSWORD"]
CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
REDIRECT_URI = os.environ["OIDC_REDIRECT_URI"]
BROWSER_ORIGIN = os.environ["OIDC_BROWSER_ORIGIN"]


def main() -> None:
    token = admin_token()
    upsert_client(token)
    print(f"registered client {CLIENT_ID!r} in realm {REALM!r}")


def admin_token() -> str:
    response = post_form(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        {
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
    )
    return str(response["access_token"])


def upsert_client(token: str) -> None:
    existing = get_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={urllib.parse.quote(CLIENT_ID)}",
        token,
    )
    body = {
        "clientId": CLIENT_ID,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "secret": CLIENT_SECRET,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "redirectUris": [REDIRECT_URI],
        "webOrigins": [BROWSER_ORIGIN],
        "attributes": {"post.logout.redirect.uris": f"{BROWSER_ORIGIN}/*"},
    }
    if existing:
        put_json(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/{existing[0]['id']}",
            token,
            body,
        )
    else:
        post_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients", token, body)


def get_json(url: str, token: str) -> Any:
    request = urllib.request.Request(url, headers=auth_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, token: str, body: Any) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20):
        return


def put_json(url: str, token: str, body: Any) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**auth_headers(token), "Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=20):
        return


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


if __name__ == "__main__":
    main()
