"""Export a compact research notebook payload from immutable local run files."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path


def read_input(path: Path) -> tuple[dict, dict]:
    """Hash the same bytes that are parsed, retaining a portable input reference."""
    raw = path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return data, {"path": path.name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def verify_binding(report: Path, catalog: object, role: str, evidence: dict) -> None:
    """Bind a supplied role to the report's original raw artifact, before compaction."""
    if not isinstance(catalog, dict) or not isinstance(catalog.get(role), dict):
        raise ValueError(f"Missing report artifact binding for {role}")
    binding = catalog[role]
    path = binding.get("path")
    digest = binding.get("sha256")
    size = binding.get("bytes")
    if (not isinstance(path, str) or not path or Path(path).is_absolute()
            or not isinstance(digest, str) or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or type(size) is not int or size < 0):
        raise ValueError(f"Invalid report artifact binding for {role}")
    bound_path = report.parent / path
    raw = bound_path.read_bytes()
    if sha256(raw).hexdigest() != digest or len(raw) != size:
        raise ValueError(f"{role} bound artifact does not match report hash/byte count")
    if evidence["sha256"] != digest or evidence["bytes"] != size:
        raise ValueError(f"Supplied {role} does not match report binding")
    evidence["report_binding"] = path


def export(report: Path, math: Path, models: Path, output: Path,
           footage: Path | None = None) -> Path:
    """Write a new output directory; existing run artifacts are never replaced."""
    if output.exists():
        raise ValueError("Output must be a new directory")
    payload = {"schema_version": "research-explorer-v1", "input_files": []}
    for label, path in (("report", report), ("math", math), ("models", models),
                        ("footage", footage)):
        if path is None:
            continue
        data, evidence = read_input(path)
        evidence["role"] = label
        payload[label] = data
        payload["input_files"].append(evidence)
    if payload["report"].get("schema_version") != "development-research-report-v1":
        raise ValueError("Unsupported development report schema")
    if payload["math"].get("schema_version") != "synthetic-mathematics-v1":
        raise ValueError("Unsupported synthetic mathematics schema")
    if payload["models"].get("schema") != "synthetic-model-demo-v1":
        raise ValueError("Unsupported synthetic model schema")
    for role in ("math", "models"):
        evidence = next(item for item in payload["input_files"] if item["role"] == role)
        verify_binding(report, payload["report"].get("artifacts"), role, evidence)
    payload["models"].get("evaluation", {}).pop("row_ids", None)
    serialized = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    output.mkdir(parents=True, exist_ok=False)
    destination = output / "data.json"
    destination.write_text(serialized)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "math", "models", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--footage", type=Path)
    args = parser.parse_args()
    try:
        destination = export(args.report, args.math, args.models, args.output, args.footage)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")
    print(destination)


if __name__ == "__main__":
    main()
