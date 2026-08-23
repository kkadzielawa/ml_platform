from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"ML_PLATFORM_FORBIDDEN_SECRET_[A-Z0-9]{16,}"),
]


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: check_policy.py <policy.json> <spdx-sbom.json> <scan-report.json>")

    policy = read_json(Path(sys.argv[1]))
    spdx = read_json(Path(sys.argv[2]))
    scan = read_json(Path(sys.argv[3]))

    violations = []
    violations.extend(check_exception_schema(policy))
    violations.extend(check_spdx_licenses(policy, spdx))
    violations.extend(check_trivy_report(scan))

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        raise SystemExit(1)


def check_exception_schema(policy: dict[str, Any]) -> list[str]:
    violations = []
    today = dt.date.today()
    for exception in policy.get("exceptions", []):
        missing = {"id", "owner", "reason", "expires_on", "scope"} - set(exception)
        if missing:
            violations.append(f"exception {exception!r} is missing {sorted(missing)}")
            continue
        expires_on = dt.date.fromisoformat(exception["expires_on"])
        if expires_on < today:
            violations.append(f"exception {exception['id']} expired on {exception['expires_on']}")
    return violations


def check_spdx_licenses(policy: dict[str, Any], spdx: dict[str, Any]) -> list[str]:
    forbidden = set(policy["forbidden_license_expressions"])
    violations = []

    for package in spdx.get("packages", []):
        name = package.get("name", "<unknown>")
        expressions = {
            package.get("licenseDeclared", "NOASSERTION"),
            package.get("licenseConcluded", "NOASSERTION"),
        }
        for expression in expressions:
            if expression in forbidden:
                violations.append(f"forbidden license {expression} on package {name}")
    return violations


def check_trivy_report(scan: dict[str, Any]) -> list[str]:
    violations = []
    for result in scan.get("Results", []):
        for secret in result.get("Secrets", []) or []:
            rule_id = secret.get("RuleID", "<unknown>")
            severity = secret.get("Severity", "<unknown>")
            violations.append(f"secret finding {rule_id} severity={severity}")
    return violations


def find_forbidden_secrets(path: Path) -> list[str]:
    findings = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(str(file_path))
    return findings


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
