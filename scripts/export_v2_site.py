"""Export a compact research notebook payload from immutable local run files."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math as numeric
from pathlib import Path
import posixpath
import re
import shutil
from urllib.parse import unquote, urlsplit

MODEL_NAMES = ("base_rate", "additive_context", "nonlinear_context", "nonlinear_history")
BUNDLE_DOCUMENTS = (
    "docs/RESEARCH_PROTOCOL.md", "docs/REWRITE_PLAN.md", "docs/EXPLORER_V2.md",
    "docs/EXPLORATORY_ANALYSIS.md", "docs/MODELING_CONTRACT.md",
    "research/exploratory_2026_11_08/specification.json",
    "research/exploratory_2026_11_08/README.md",
)


def bundled_markdown(text, relative):
    """Keep only available local links in documentation copies, retaining labels."""
    def replace(match):
        image, label, target = match.groups()
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            return match.group(0)
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(relative), unquote(url.path)))
        return match.group(0) if resolved in BUNDLE_DOCUMENTS else image + label

    return re.sub(r"(!?)\[([^\]\n]+)\]\(([^)\n]+)\)", replace, text)


def finite_tree(value):
    """Reject non-JSON numeric values throughout empirical evidence."""
    if isinstance(value, float) and not numeric.isfinite(value):
        raise ValueError("Exploratory values must be finite")
    if isinstance(value, dict):
        for child in value.values():
            finite_tree(child)
    if isinstance(value, list):
        for child in value:
            finite_tree(child)


def provisional(value, schema, status=None):
    if not isinstance(value, dict) or value.get("schema_version") != schema:
        raise ValueError("Unsupported exploratory schema")
    if status and value.get("status") != status:
        raise ValueError("Invalid exploratory status")
    flags = ("eligible", "scientific_approval", "publication_authorized")
    if value.get("evaluation_exposure") != "retrospective_previously_exposed":
        raise ValueError("Exploratory exposure must be retrospective")
    if any(value.get(key) is not False for key in flags):
        raise ValueError("Exploratory approval flags must remain false")
    finite_tree(value)


def exploratory_payload(path, receipts):
    report, receipt = read_input(path)
    receipt["role"] = "exploratory_report"
    receipts.append(receipt)
    status = "EXPLORATORY_ONLY_NOT_VALIDATED"
    provisional(report, "exploratory-research-report-v1", status)
    roles = {"plan", "cohort", "selected_rows", "predictions", "model_result"}
    catalog = report.get("artifacts")
    if not isinstance(catalog, dict) or set(catalog) != roles:
        raise ValueError("Exact exploratory artifact roles required")
    parsed, paths = {}, set()
    for role in sorted(roles):
        binding = catalog[role]
        if not isinstance(binding, dict) or not isinstance(binding.get("path"), str):
            raise ValueError("Invalid exploratory artifact binding")
        relative = Path(binding["path"])
        child = path.parent / relative
        if (not binding["path"] or relative.is_absolute() or ".." in relative.parts
                or "\\" in binding["path"] or not child.resolve().is_relative_to(path.parent.resolve())
                or child.resolve() in paths or child.resolve() == path.resolve()):
            raise ValueError("Exploratory artifacts must be distinct contained child paths")
        paths.add(child.resolve())
        raw = child.read_bytes()
        evidence = {"role": f"exploratory_{role}", "path": binding["path"],
                    "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        if (type(binding.get("bytes")) is not int or binding["bytes"] != len(raw)
                or binding.get("sha256") != evidence["sha256"]):
            raise ValueError(f"Exploratory {role} hash/byte mismatch")
        receipts.append(evidence)
        if role in {"plan", "cohort", "model_result"}:
            parsed[role] = json.loads(raw)
    plan, cohort, result = (parsed[k] for k in ("plan", "cohort", "model_result"))
    provisional(plan, "provisional-exploratory-plan-v1")
    provisional(cohort, "provisional-exploratory-cohort-v1", "PROVISIONAL_NOT_INDEPENDENTLY_VALIDATED")
    provisional(result, "provisional-exploratory-result-v1", status)
    if (not isinstance(report.get("analysis_id"), str) or not report["analysis_id"].strip()
            or result.get("analysis_id") != report["analysis_id"]
            or plan.get("analysis_id") != report["analysis_id"]
            or report.get("plan_sha256") != catalog["plan"]["sha256"]
            or result.get("plan_sha256") != report["plan_sha256"]
            or report.get("cohort") != cohort
            or plan.get("cohort") != cohort.get("cohort")
            or plan.get("split") != cohort.get("split")
            or plan.get("meaningful_gain") is not None):
        raise ValueError("Exploratory plan/model/cohort identity mismatch")
    evaluation = result.get("evaluation", {})
    if not isinstance(evaluation, dict):
        raise ValueError("Exploratory evaluation object required")
    models = evaluation.get("models", {})
    decision = evaluation.get("decision")
    if (not isinstance(models, dict) or set(models) != set(MODEL_NAMES)
            or not isinstance(decision, dict) or decision.get("classification") != "NOT_SPECIFIED"):
        raise ValueError("Exploratory models and unclassified decision required")
    for model in models.values():
        if not isinstance(model, dict):
            raise ValueError("Exploratory model metrics required")
        for key in ("possession_logloss", "brier"):
            value = model.get(key)
            if type(value) not in (int, float) or not numeric.isfinite(value) or value < 0:
                raise ValueError("Finite nonnegative exploratory loss required")
    paired = evaluation.get("paired_logloss", {})
    if not isinstance(paired, dict) or not isinstance(paired.get("interval"), list):
        raise ValueError("Exploratory paired interval required")
    values = [paired.get("estimate"), *paired["interval"]]
    if (len(values) != 3 or any(type(v) not in (int, float) or not numeric.isfinite(v) for v in values)
            or values[1] > values[2] or paired.get("conditions_on_fitted_models") is not True):
        raise ValueError("Finite conditional exploratory interval required")
    evaluation.pop("row_ids", None)
    cohort.pop("games", None)
    report["cohort"] = {k: v for k, v in report["cohort"].items() if k != "games"}
    return {"report": report, "cohort": cohort, "result": result}


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
           footage: Path | None = None, exploratory: Path | None = None,
           *, bundle: bool = False) -> Path:
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
    if exploratory is not None:
        payload["exploratory"] = exploratory_payload(exploratory, payload["input_files"])
    serialized = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    output.mkdir(parents=True, exist_ok=False)
    destination = output / "data.json"
    destination.write_text(serialized)
    if bundle:
        source = Path(__file__).resolve().parents[1] / "v2"
        html = (source / "index.html").read_text()
        html = html.replace('href="../index.html">Legacy game explorer',
                            'href="#question">Back to question')
        html = html.replace('href="../docs/', 'href="docs/')
        (output / "index.html").write_text(html)
        for name in ("app.js", "styles.css"):
            shutil.copyfile(source / name, output / name)
        for relative in BUNDLE_DOCUMENTS:
            destination_doc = output / relative
            destination_doc.parent.mkdir(parents=True, exist_ok=True)
            original = source.parent / relative
            if original.suffix == ".md":
                destination_doc.write_text(bundled_markdown(original.read_text(), relative))
            else:
                shutil.copyfile(original, destination_doc)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "math", "models", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--footage", type=Path)
    parser.add_argument("--exploratory", type=Path)
    parser.add_argument("--bundle", action="store_true")
    args = parser.parse_args()
    try:
        destination = export(args.report, args.math, args.models, args.output, args.footage,
                             args.exploratory, bundle=args.bundle)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Export failed: {exc}\n")
    print(destination)


if __name__ == "__main__":
    main()
