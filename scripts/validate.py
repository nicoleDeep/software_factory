#!/usr/bin/env python3
"""Validate the factory's local documentation contract (Python 3.10+, stdlib only).

This is not an APP test runner, Markdown renderer, network checker or gate approver.
Local file targets are checked; Markdown heading anchors are deliberately not checked.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT_FILES = ("README.md", "Home.md", "AGENTS.md", "CHANGELOG.md")
DOC_DIRS = ("factory", "lines", "templates", "projects", "improvements", "00-Inbox", ".dsh/skills")
NODE_IDS = [f"APP-{i:02d}" for i in range(1, 11)]
GATES = {"G1": "APP-02", "G2": "APP-04", "G3": "APP-07", "G4": "APP-08", "G5": "APP-10"}
GATE_STATES = ("pending", "blocked", "rejected", "passed", "conditional", "waived")
LINK = re.compile(r"\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|([^\s)]+))(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*```.*?^\s*```\s*$", re.MULTILINE | re.DOTALL)


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def local_file(relative: str) -> Path | None:
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            errors.append(f"Missing or out-of-root file: {relative}")
            return None
        return path

    def text(relative: str) -> str:
        path = local_file(relative)
        if path is None:
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read {relative}: {exc}")
            return ""

    def data(relative: str) -> dict:
        content = text(relative)
        try:
            value = json.loads(content)
            if not isinstance(value, dict):
                raise ValueError("expected JSON object")
            return value
        except (ValueError, TypeError) as exc:
            errors.append(f"Invalid JSON {relative}: {exc}")
            return {}

    docs = {root / name for name in ROOT_FILES}
    for directory in DOC_DIRS:
        base = root / directory
        require(base.is_dir(), f"Missing directory: {directory}")
        if base.is_dir():
            docs.update(base.rglob("*.md"))
    for path in sorted(docs):
        relative = str(path.relative_to(root))
        content = FENCE.sub("", text(relative))
        for match in LINK.finditer(content):
            target = match.group(1) or match.group(2)
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            require(resolved.is_relative_to(root) and resolved.is_file(),
                    f"Broken or out-of-root link in {relative}: {target}")

    registry = data("factory/production-lines.json")
    pipeline = data("lines/app/pipeline.json")
    version = text("lines/app/VERSION").strip()
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), "Invalid APP VERSION")
    require(registry.get("schema_version") == 1, "Invalid registry schema_version")
    require(pipeline.get("schema_version") == 1, "Invalid pipeline schema_version")
    require(pipeline.get("line") == "app", "Invalid pipeline line")
    require(pipeline.get("execution_mode") == "human-agent-assisted", "Unexpected execution mode")
    require(pipeline.get("version") == version, "Pipeline VERSION mismatch")

    def objects(value: object, label: str) -> list[dict]:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            errors.append(f"{label} must be an array of objects")
            return []
        return value

    lines = objects(registry.get("lines"), "lines")
    ids = [line.get("id") for line in lines]
    require(all(isinstance(i, str) for i in ids) and len(ids) == len(set(map(str, ids))),
            "Duplicate or invalid line IDs")
    require("app" in ids and "game" in ids, "APP and game registrations required")
    for line in lines:
        entry = line.get("entry")
        if isinstance(entry, str):
            local_file(entry)
        else:
            errors.append("Line entry must be a path")
        if line.get("status") == "planned":
            require(line.get("version") is None and line.get("pipeline") is None,
                    "Planned line must not claim a version or pipeline")
        elif line.get("status") == "baseline":
            if isinstance(line.get("pipeline"), str):
                local_file(line["pipeline"])
            else:
                errors.append("Baseline line requires pipeline path")
        else:
            errors.append(f"Unsupported line status: {line.get('status')}")
        if line.get("id") == "app":
            require(line.get("status") == "baseline" and line.get("version") == version,
                    "APP registry VERSION/status mismatch")
            require(line.get("pipeline") == "lines/app/pipeline.json", "APP pipeline path mismatch")
        if line.get("id") == "game":
            require(line.get("status") == "planned", "Game is not implemented in this baseline")

    require(pipeline.get("spec") == "lines/app/pipeline.md", "Pipeline spec path mismatch")
    require(pipeline.get("quality_spec") == "lines/app/quality-gates.md", "Quality spec path mismatch")
    spec = text("lines/app/pipeline.md")
    quality = text("lines/app/quality-gates.md")
    require(re.findall(r"^### (APP-\d{2})\b", spec, re.MULTILINE) == NODE_IDS,
            "Markdown must define APP-01 through APP-10 once, in order")
    require(re.findall(r"^### (G\d)\b", quality, re.MULTILINE) == list(GATES),
            "Markdown must define G1 through G5 once, in order")
    for relative in ("lines/app/README.md", "lines/app/pipeline.md", "lines/app/quality-gates.md", "CHANGELOG.md"):
        require(version in text(relative), f"Version absent from {relative}")
    for state in GATE_STATES:
        require(state in quality, f"Gate state missing from quality spec: {state}")

    nodes = objects(pipeline.get("nodes"), "nodes")
    require([node.get("id") for node in nodes] == NODE_IDS, "Invalid node IDs/order or duplicate node")
    reverse_gates = {node: gate for gate, node in GATES.items()}
    for node in nodes:
        require(node.get("gate") == reverse_gates.get(node.get("id")), "Node gate mapping mismatch")
        successors = node.get("next")
        require(isinstance(successors, list) and all(item in NODE_IDS for item in successors),
                f"Invalid next targets for {node.get('id')}")
        require(isinstance(node.get("name"), str) and bool(node.get("name")), "Node name required")
    gates = objects(pipeline.get("gates"), "gates")
    require([gate.get("id") for gate in gates] == list(GATES), "Invalid gate IDs/order or duplicate gate")
    for gate in gates:
        require(gate.get("after") == GATES.get(gate.get("id")), "Gate location mismatch")
        require(gate.get("approval") == "human", "Baseline gates require human approval")

    skill = text(".dsh/skills/app-production-line/SKILL.md")
    frontmatter = re.match(r"\A---\n(.*?)\n---(?:\n|$)", skill, re.DOTALL)
    require(frontmatter is not None, "Skill frontmatter missing")
    if frontmatter:
        header = frontmatter.group(1)
        require(bool(re.search(r"^name: app-production-line\s*$", header, re.MULTILINE)),
                "Skill name mismatch")
        require(bool(re.search(r"^description: \S.+$", header, re.MULTILINE)), "Skill description missing")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errors = validate(root)
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: local links, registry, APP version, 10 nodes, 5 gates and Skill metadata")
    print("Scope: documentation contract only; no APP tests, live DSH discovery or release approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
