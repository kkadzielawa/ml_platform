from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ID_RE = re.compile(r'^id: "([0-9]{2}\.[0-9]{2}(?:\.[a-z])?|X\.[A-H]\.[0-9]{2}(?:\.[a-z])?)"$')
DEP_RE = re.compile(r'^depends_on: \[(.*)]$')
ROUTE_RE = re.compile(r'^route: "([^"]+)"$')


def quoted_values(raw: str) -> list[str]:
    return re.findall(r'"([^"]+)"', raw)


def main() -> int:
    records: dict[str, tuple[Path, list[str], str]] = {}
    route_groups: defaultdict[str, list[str]] = defaultdict(list)
    core_numbers: defaultdict[str, set[int]] = defaultdict(set)
    exploration_numbers: defaultdict[str, set[int]] = defaultdict(set)
    errors: list[str] = []

    for path in sorted(ROOT.glob("phase-*/*.md")) + sorted(ROOT.glob("explorations/*.md")):
        if path.name == "README.md":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        issue_id = next((m.group(1) for line in lines if (m := ID_RE.match(line))), None)
        dep_match = next((m for line in lines if (m := DEP_RE.match(line))), None)
        route_match = next((m for line in lines if (m := ROUTE_RE.match(line))), None)
        if not issue_id or not dep_match or not route_match:
            errors.append(f"{path}: missing or malformed id/depends_on/route metadata")
            continue
        required_sections = {
            "## Outcome",
            "## Allowed paths",
            "## Deliverables",
            "## Acceptance",
            "## Verify",
            "## Non-goals",
        }
        missing_sections = sorted(required_sections - set(lines))
        if missing_sections:
            errors.append(f"{path}: missing sections {missing_sections}")
        if sum(1 for line in lines if line.startswith("```")) % 2:
            errors.append(f"{path}: unbalanced fenced code blocks")
        if not path.name.startswith(issue_id + "-"):
            errors.append(f"{path}: filename must start with {issue_id}-")
        if issue_id in records:
            errors.append(f"{path}: duplicate id {issue_id} (also {records[issue_id][0]})")
        dependencies = quoted_values(dep_match.group(1))
        route = route_match.group(1)
        records[issue_id] = (path, dependencies, route)
        if issue_id.startswith("X."):
            _, branch, number, *_ = issue_id.split(".")
            exploration_numbers[branch].add(int(number))
        else:
            phase, number, *_ = issue_id.split(".")
            core_numbers[phase].add(int(number))
        if route.startswith("choose-one:"):
            route_groups[route.split(":", 1)[1]].append(issue_id)

    for issue_id, (path, dependencies, _) in records.items():
        for dependency in dependencies:
            if dependency not in records and dependency not in route_groups:
                errors.append(f"{path}: unknown dependency {dependency}")
            elif dependency == issue_id:
                errors.append(f"{path}: self dependency")

    for group, members in route_groups.items():
        if len(members) < 2:
            errors.append(f"route group {group} has fewer than two alternatives: {members}")

    for phase, numbers in core_numbers.items():
        expected = set(range(1, max(numbers) + 1))
        if numbers != expected:
            errors.append(f"phase {phase} task numbers are not continuous: missing {sorted(expected - numbers)}")

    for branch, numbers in exploration_numbers.items():
        expected = set(range(1, max(numbers) + 1))
        if numbers != expected:
            errors.append(f"exploration {branch} task numbers are not continuous: missing {sorted(expected - numbers)}")

    expanded_dependencies: dict[str, list[str]] = {}
    for issue_id, (_, dependencies, _) in records.items():
        expanded: list[str] = []
        for dependency in dependencies:
            expanded.extend(route_groups.get(dependency, [dependency]))
        expanded_dependencies[issue_id] = [dep for dep in expanded if dep in records]

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(issue_id: str, trail: list[str]) -> None:
        if issue_id in visiting:
            errors.append(f"dependency cycle: {' -> '.join(trail + [issue_id])}")
            return
        if issue_id in visited:
            return
        visiting.add(issue_id)
        for dependency in expanded_dependencies[issue_id]:
            visit(dependency, trail + [issue_id])
        visiting.remove(issue_id)
        visited.add(issue_id)

    for issue_id in records:
        visit(issue_id, [])

    if errors:
        print("Backlog validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(records)} issues across {len(route_groups)} alternative route groups.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
