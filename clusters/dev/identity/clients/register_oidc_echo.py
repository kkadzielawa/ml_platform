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
VIEWER_USERNAME = os.environ["OIDC_VIEWER_USERNAME"]
VIEWER_PASSWORD = os.environ["OIDC_VIEWER_PASSWORD"]
ADMIN_TEST_USERNAME = os.environ["OIDC_ADMIN_USERNAME"]
ADMIN_TEST_PASSWORD = os.environ["OIDC_ADMIN_PASSWORD"]


def main() -> None:
    token = admin_token()
    client_uuid = upsert_client(token)
    assert client_uuid
    upsert_user(token, VIEWER_USERNAME, VIEWER_PASSWORD, "viewer")
    upsert_user(token, ADMIN_TEST_USERNAME, ADMIN_TEST_PASSWORD, "admin")
    print(f"registered client {CLIENT_ID!r} and test users in realm {REALM!r}")


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


def upsert_client(token: str) -> str:
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
        "attributes": {
            "post.logout.redirect.uris": f"{BROWSER_ORIGIN}/*",
        },
    }
    if existing:
        client_uuid = existing[0]["id"]
        put_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients/{client_uuid}", token, body)
        return str(client_uuid)

    post_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients", token, body)
    created = get_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/clients?clientId={urllib.parse.quote(CLIENT_ID)}",
        token,
    )
    return str(created[0]["id"])


def upsert_user(token: str, username: str, password: str, role_name: str) -> None:
    user_body = {
        "username": username,
        "enabled": True,
        "email": f"{username}@ml-platform.local",
        "emailVerified": True,
        "firstName": username,
        "lastName": "study",
        "requiredActions": [],
    }
    users = get_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?username={urllib.parse.quote(username)}&exact=true",
        token,
    )
    if users:
        user_id = users[0]["id"]
        put_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}", token, user_body)
    else:
        post_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users", token, user_body)
        users = get_json(
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users?username={urllib.parse.quote(username)}&exact=true",
            token,
        )
        user_id = users[0]["id"]

    put_json(
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/reset-password",
        token,
        {
            "type": "password",
            "value": password,
            "temporary": False,
        },
    )
    role = get_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/roles/{urllib.parse.quote(role_name)}", token)
    post_json(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/role-mappings/realm", token, [role])


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
