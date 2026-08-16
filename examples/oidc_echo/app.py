from __future__ import annotations

import base64
import http.cookies
import json
import os
import secrets
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


REALM = os.environ.get("OIDC_REALM", "ml-platform-study")
CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
CLIENT_SECRET = os.environ["OIDC_CLIENT_SECRET"]
INTERNAL_ISSUER = os.environ["OIDC_INTERNAL_ISSUER"].rstrip("/")
BROWSER_ISSUER = os.environ["OIDC_BROWSER_ISSUER"].rstrip("/")
REDIRECT_URI = os.environ["OIDC_REDIRECT_URI"]
PORT = int(os.environ.get("PORT", "8080"))
FRONTEND_HOST = urllib.parse.urlparse(BROWSER_ISSUER).netloc

SESSION_COOKIE = "oidc_echo_access_token"
STATE_COOKIE = "oidc_echo_state"
NEXT_COOKIE = "oidc_echo_next"


class OidcEchoHandler(BaseHTTPRequestHandler):
    server_version = "oidc-echo/0.1"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/healthz":
            self.send_json({"status": "ok"})
            return
        if path == "/login":
            self.redirect_to_login(query.get("next", ["/viewer"])[0])
            return
        if path == "/callback":
            self.handle_callback(query)
            return
        if path == "/logout":
            self.clear_session()
            return
        if path in {"/", "/viewer"}:
            principal = self.require_principal(required_role=None)
            if principal is None:
                return
            self.send_json(
                {
                    "message": "viewer path allowed",
                    "subject": principal.get("preferred_username") or principal.get("username") or principal.get("sub"),
                    "roles": sorted(principal.get("roles", [])),
                }
            )
            return
        if path == "/admin":
            principal = self.require_principal(required_role="admin")
            if principal is None:
                return
            self.send_json(
                {
                    "message": "admin path allowed",
                    "subject": principal.get("preferred_username") or principal.get("username") or principal.get("sub"),
                    "roles": sorted(principal.get("roles", [])),
                }
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "unknown path")

    def require_principal(self, *, required_role: str | None) -> dict[str, Any] | None:
        token = self.bearer_token() or self.cookie_value(SESSION_COOKIE)
        if not token:
            self.redirect_to_login(self.path)
            return None

        principal = validate_token(token)
        if principal is None:
            self.clear_session(status=HTTPStatus.UNAUTHORIZED, body={"error": "inactive token"})
            return None

        if required_role and required_role not in principal.get("roles", set()):
            self.send_json({"error": "forbidden", "required_role": required_role}, status=HTTPStatus.FORBIDDEN)
            return None

        return principal

    def redirect_to_login(self, next_path: str) -> None:
        state = secrets.token_urlsafe(24)
        params = urllib.parse.urlencode(
            {
                "client_id": CLIENT_ID,
                "response_type": "code",
                "scope": "openid profile",
                "redirect_uri": REDIRECT_URI,
                "state": state,
            }
        )
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", f"{BROWSER_ISSUER}/protocol/openid-connect/auth?{params}")
        self.set_cookie(STATE_COOKIE, state)
        self.set_cookie(NEXT_COOKIE, safe_next_path(next_path))
        self.end_headers()

    def handle_callback(self, query: dict[str, list[str]]) -> None:
        expected_state = self.cookie_value(STATE_COOKIE)
        actual_state = query.get("state", [""])[0]
        code = query.get("code", [""])[0]
        if not expected_state or not secrets.compare_digest(expected_state, actual_state):
            self.send_json({"error": "invalid state"}, status=HTTPStatus.BAD_REQUEST)
            return
        if not code:
            self.send_json({"error": "missing code"}, status=HTTPStatus.BAD_REQUEST)
            return

        token_response = token_request(
            {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            }
        )
        access_token = token_response["access_token"]
        next_path = self.cookie_value(NEXT_COOKIE) or "/viewer"

        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", safe_next_path(next_path))
        self.set_cookie(SESSION_COOKIE, access_token, httponly=True)
        self.delete_cookie(STATE_COOKIE)
        self.delete_cookie(NEXT_COOKIE)
        self.end_headers()

    def bearer_token(self) -> str | None:
        authorization = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if authorization.startswith(prefix):
            return authorization[len(prefix) :]
        return None

    def cookie_value(self, name: str) -> str | None:
        cookies = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookies.get(name)
        if morsel is None:
            return None
        return morsel.value

    def set_cookie(self, name: str, value: str, *, httponly: bool = False) -> None:
        cookie = http.cookies.SimpleCookie()
        cookie[name] = value
        cookie[name]["path"] = "/"
        cookie[name]["samesite"] = "Lax"
        if httponly:
            cookie[name]["httponly"] = True
        self.send_header("Set-Cookie", cookie.output(header="").strip())

    def delete_cookie(self, name: str) -> None:
        cookie = http.cookies.SimpleCookie()
        cookie[name] = ""
        cookie[name]["path"] = "/"
        cookie[name]["max-age"] = "0"
        self.send_header("Set-Cookie", cookie.output(header="").strip())

    def clear_session(self, *, status: HTTPStatus = HTTPStatus.FOUND, body: dict[str, Any] | None = None) -> None:
        if body is None:
            self.send_response(status)
            self.send_header("Location", "/")
            self.delete_cookie(SESSION_COOKIE)
            self.end_headers()
            return
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.delete_cookie(SESSION_COOKIE)
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, body: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        return


def token_request(data: dict[str, str]) -> dict[str, Any]:
    return post_form(f"{INTERNAL_ISSUER}/protocol/openid-connect/token", data)


def validate_token(token: str) -> dict[str, Any] | None:
    userinfo = get_userinfo(token)
    if userinfo is None:
        return None

    claims = jwt_claims(token)
    roles = set(claims.get("realm_access", {}).get("roles", []))
    userinfo["roles"] = roles
    userinfo["preferred_username"] = claims.get("preferred_username") or userinfo.get("preferred_username")
    return userinfo


def get_userinfo(token: str) -> dict[str, Any] | None:
    request = urllib.request.Request(
        f"{INTERNAL_ISSUER}/protocol/openid-connect/userinfo",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Host": FRONTEND_HOST},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Host": FRONTEND_HOST},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def jwt_claims(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        parsed = json.loads(decoded)
    except (IndexError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def safe_next_path(path: str) -> str:
    if not path.startswith("/") or path.startswith("//"):
        return "/viewer"
    return path


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), OidcEchoHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
