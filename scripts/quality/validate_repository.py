"""Validate repository contracts, traceability, links, and accidental secrets."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
REQUIREMENT_ID = re.compile(r"\*\*((?:FR|NFR|AC|AC0|AC1)-\d{3})\*\*")
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Provider token": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
}
TEXT_SUFFIXES = {".json", ".md", ".py", ".ts", ".tsx", ".yaml", ".yml"}
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pnpm-store",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "coverage",
    "node_modules",
}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping or fail with a useful validation error."""

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return value


def validate_openapi(errors: list[str]) -> None:
    """Validate the minimum OpenAPI structure required in Phase 1."""

    path = ROOT / "packages/contracts/openapi/agentic-delivery-api.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("openapi") != "3.1.0":
        errors.append("OpenAPI contract must use version 3.1.0")
    if not isinstance(document.get("paths"), dict) or not document["paths"]:
        errors.append("OpenAPI contract must define at least one path")


def validate_markdown_links(errors: list[str]) -> None:
    """Ensure local Markdown links resolve from their containing document."""

    for path in ROOT.rglob("*.md"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        for match in MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).split("#", maxsplit=1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {target}")


def validate_capability_map(errors: list[str]) -> None:
    """Validate status vocabulary and every repository path in the registry."""

    registry = load_yaml(ROOT / "capability-map.yaml")
    policy = registry.get("policy", {})
    allowed_statuses = set(policy.get("statuses", [])) if isinstance(policy, dict) else set()
    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("Capability registry must contain capabilities")
        return

    seen: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, dict):
            errors.append("Each capability must be a mapping")
            continue
        capability_id = capability.get("id")
        if not isinstance(capability_id, str) or not capability_id:
            errors.append("Each capability must have a non-empty id")
            continue
        if capability_id in seen:
            errors.append(f"Duplicate capability id: {capability_id}")
        seen.add(capability_id)

        status = capability.get("status")
        if status not in allowed_statuses:
            errors.append(f"Invalid status for {capability_id}: {status}")

        for field in ("source", "tests", "demo", "documentation", "evidence"):
            paths = capability.get(field, [])
            if not isinstance(paths, list):
                errors.append(f"{capability_id}.{field} must be a list")
                continue
            for relative in paths:
                if not isinstance(relative, str) or not (ROOT / relative).exists():
                    errors.append(f"Missing {capability_id}.{field} path: {relative}")

        if status == "verified" and not capability.get("evidence"):
            errors.append(f"Verified capability lacks evidence: {capability_id}")


def validate_requirement_ids(errors: list[str]) -> None:
    """Reject duplicate stable identifiers in specification documents."""

    seen: dict[str, Path] = {}
    for path in (ROOT / "specs").rglob("*.md"):
        for requirement_id in REQUIREMENT_ID.findall(path.read_text(encoding="utf-8")):
            previous = seen.get(requirement_id)
            if previous is not None:
                errors.append(
                    f"Duplicate requirement id {requirement_id}: "
                    f"{previous.relative_to(ROOT)} and {path.relative_to(ROOT)}"
                )
            else:
                seen[requirement_id] = path


def validate_compose(errors: list[str]) -> None:
    """Validate the intended local container service boundaries."""

    compose = load_yaml(ROOT / "docker-compose.yml")
    services = compose.get("services")
    expected = {"web", "api", "worker", "evaluator"}
    if not isinstance(services, dict) or set(services) != expected:
        errors.append("Docker Compose must define exactly web, api, worker, and evaluator")
        return
    for service in ("web", "api", "worker"):
        config = services.get(service)
        if not isinstance(config, dict) or "healthcheck" not in config:
            errors.append(f"Docker Compose service lacks a healthcheck: {service}")


def validate_governance_policy(errors: list[str]) -> None:
    """Keep the reviewed baseline active and every sector template fail-closed."""

    baseline = load_yaml(ROOT / "policies/baseline/common-us-v1.yaml")
    if baseline.get("id") != "common-us-baseline" or baseline.get("enabled") is not True:
        errors.append("The common US reference baseline must be the only active policy")
    if baseline.get("legalDetermination") is not False:
        errors.append("The reference baseline must not assert a legal determination")

    for path in (ROOT / "policies/overlays").glob("*.yaml"):
        overlay = load_yaml(path)
        if overlay.get("enabled") is not False:
            errors.append(f"Industry overlay must remain disabled: {path.relative_to(ROOT)}")
        if overlay.get("status") != "requires_legal_review":
            errors.append(f"Industry overlay lacks legal-review status: {path.relative_to(ROOT)}")


def validate_secrets(errors: list[str]) -> None:
    """Detect common credential shapes in versioned source candidates."""

    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"Possible {label} in {path.relative_to(ROOT)}")


def main() -> int:
    """Run all repository validations and return a process exit code."""

    errors: list[str] = []
    validations = (
        validate_openapi,
        validate_markdown_links,
        validate_capability_map,
        validate_requirement_ids,
        validate_compose,
        validate_governance_policy,
        validate_secrets,
    )
    for validation in validations:
        try:
            validation(errors)
        except (json.JSONDecodeError, OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{validation.__name__}: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
