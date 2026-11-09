"""Explicitly provisional retrospective fits; no scientific gate is satisfied here."""

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil

import numpy as np
import sklearn

from whistle_research import audit, evaluation, modeling
from whistle_research.sources import file_digest

STATUS = "EXPLORATORY_ONLY_NOT_VALIDATED"
EXPOSURE = "retrospective_previously_exposed"
PLAN_KEYS = {
    "analysis_id", "cohort", "cohort_policy", "cohort_policy_details", "declared_at",
    "declared_date", "eligible", "evaluation_exposure", "limitations", "max_selected_rows",
    "meaningful_gain", "model_specification", "model_specification_sha256",
    "publication_authorized", "schema_version", "scientific_approval", "split",
}


def _plan(raw):
    plan = modeling._strict_json(raw.decode("utf-8"))
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise ValueError("exact provisional plan fields required")
    if plan["schema_version"] != "provisional-exploratory-plan-v1":
        raise ValueError("unsupported exploratory plan schema")
    if any(plan[key] is not False for key in ("eligible", "scientific_approval", "publication_authorized")):
        raise ValueError("exploratory authorization flags must remain false")
    if plan["evaluation_exposure"] != EXPOSURE or plan["meaningful_gain"] is not None:
        raise ValueError("retrospective exposure and no meaningful-gain threshold required")
    if type(plan["max_selected_rows"]) is not int or plan["max_selected_rows"] != 250000:
        raise ValueError("predeclared 250000 row ceiling required")
    if plan["cohort_policy"] != "whole_game_quality_filter_v1":
        raise ValueError("unsupported whole-game cohort policy")
    if (not isinstance(plan["cohort"], dict) or set(plan["cohort"]) != {"season", "game_type"}
            or not all(audit.text(value) for value in plan["cohort"].values())):
        raise ValueError("explicit season and game_type required")
    for key in ("analysis_id",):
        if not audit.text(plan[key]):
            raise ValueError(f"nonempty {key} required")
    for key in ("limitations", "cohort_policy_details"):
        if not isinstance(plan[key], list) or not plan[key] or not all(audit.text(v) for v in plan[key]):
            raise ValueError(f"nonempty {key} required")
    spec = modeling.specification()
    if (plan["model_specification"] != spec or audit.digest(plan["model_specification"]) != audit.digest(spec)
            or plan["model_specification_sha256"] != audit.digest(spec)):
        raise ValueError("predeclared model specification or code hash mismatch")
    keys = ("train_start", "tune_start", "test_start", "test_end")
    if not isinstance(plan["split"], dict) or set(plan["split"]) != set(keys):
        raise ValueError("exact chronological split boundaries required")
    days = [date.fromisoformat(plan["split"][key]) for key in keys]
    if any(day.isoformat() != plan["split"][key] for day, key in zip(days, keys)):
        raise ValueError("split dates must use YYYY-MM-DD")
    declared = date.fromisoformat(plan["declared_date"])
    timestamp = audit.timestamp(plan["declared_at"])
    if (declared.isoformat() != plan["declared_date"] or abs((timestamp.date() - declared).days) > 1
            or not all(a < b for a, b in zip(days, days[1:])) or days[-1] > declared):
        raise ValueError("ordered past split and consistent declaration dates required")
    return plan


def _flags(plan):
    return {"status": STATUS, "eligible": False, "scientific_approval": False,
            "publication_authorized": False, "evaluation_exposure": EXPOSURE,
            "analysis_id": plan["analysis_id"]}


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _markdown(report, result):
    lines = ["# PROVISIONAL retrospective exploratory fit", "", STATUS, "",
             "Real recorded-call data; reconstruction and scientific validity remain unvalidated.",
             "No publication authorization or meaningful-gain classification.", "",
             "| Model | Test log loss | Test Brier |", "| --- | ---: | ---: |"]
    for name, metrics in result["evaluation"]["models"].items():
        lines.append(f"| {name} | {metrics['possession_logloss']:.8f} | {metrics['brier']:.8f} |")
    paired = result["evaluation"]["paired_logloss"]
    lines += ["", f"History minus context log-loss delta: {paired['estimate']:+.8f}; "
              f"conditional 95% interval [{paired['interval'][0]:+.8f}, {paired['interval'][1]:+.8f}].",
              "Negative values favor history on this selected held-out set; this is not a usefulness decision.",
              "Whole-game intervals condition on fitted/development-selected models and selected games.",
              paired["assumption"] + ". " + paired["limitations"], "", "## Cohort counts", "",
              "```json", json.dumps(report["cohort"].get("counts", {}), indent=2, sort_keys=True), "```",
              "", "Exclusion reason counts (nonexclusive):", "```json",
              json.dumps(report["cohort"].get("exclusion_reason_counts", {}), indent=2, sort_keys=True),
              "```", "", "## Limitations", ""]
    lines.extend(f"- {item}" for item in report["limitations"])
    return ("\n".join(lines) + "\n").encode()


def run_exploratory(*, plan_path, feature_dir, inventory_path, reconciliation_path,
                    source_manifest, cache, schedule, metadata, output):
    """Fit only an explicit retrospective plan into a new, byte-bound artifact set."""
    output, plan_path = Path(output), Path(plan_path)
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; choose a new directory")
    raw = plan_path.read_bytes()
    plan = _plan(raw)  # Refuse malformed plans before any cohort/source access.
    from whistle_research.exploratory_cohort import prepare_cohort

    code = [(path, *file_digest(path)) for path in sorted(Path(__file__).parent.glob("*.py"))]
    prepared = prepare_cohort(plan=plan, feature_dir=Path(feature_dir), inventory_path=Path(inventory_path),
                              reconciliation_path=Path(reconciliation_path), source_manifest=Path(source_manifest),
                              cache=Path(cache), schedule=Path(schedule), metadata=[Path(p) for p in metadata])
    rows, cohort = prepared["rows"], prepared["report"]
    modeling.validate_rows(rows)
    if len(rows) > plan["max_selected_rows"]:
        raise ValueError("selected rows exceed predeclared ceiling")
    inputs = prepared["inputs"]

    def recheck():
        if plan_path.read_bytes() != raw:
            raise ValueError("plan bytes changed during exploratory run")
        for path, size, digest in code:
            if file_digest(path) != (size, digest):
                raise ValueError("implementation bytes changed during exploratory run")
        for item in inputs:
            if file_digest(Path(item["path"])) != (item["bytes"], item["sha256"]):
                raise ValueError("consumed input bytes changed during exploratory run")
        prepared["recheck"]()

    recheck()
    fitted = modeling._fit(rows, plan["split"])
    scored = evaluation._evaluate(fitted["subsets"]["test"], fitted["predictions"], meaningful_gain=None)
    fields = ("game_id", "possession_number", *modeling.NUMERIC, *modeling.STRONG_NUMERIC,
              *modeling.CATEGORICAL, *modeling.HISTORY)
    provenance = {
        "rows_sha256": modeling.row_digest(rows),
        "partition_rows_sha256": {k: modeling.row_digest(v) for k, v in fitted["subsets"].items()},
        "test_features_sha256": audit.digest([{k: row.get(k) for k in fields} for row in fitted["subsets"]["test"]]),
        "specification_sha256": audit.digest(plan["model_specification"]),
        "implementation_sha256": {path.name: digest for path, _, digest in code},
        "inputs": [{"role": item["role"], "path": Path(os.path.relpath(Path(item["path"]).resolve(), output.resolve())).as_posix(),
                    "bytes": item["bytes"], "sha256": item["sha256"]} for item in inputs],
        "fitted_pipeline_sha256": {name: modeling._fitted_pipeline_digest(pipe) for name, pipe in fitted["pipelines"].items()},
        "base_rate": fitted["diagnostics"]["base_rate"]["training_rate"],
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__},
        **{key: cohort[key] for key in ("parser_version", "parser_sha256", "feature_version", "feature_sha256",
                                       "frame_sha256", "source_map")},
    }
    shared = {**_flags(plan), "plan_sha256": hashlib.sha256(raw).hexdigest()}
    result = {"schema_version": "provisional-exploratory-result-v1", **shared,
              "diagnostics": fitted["diagnostics"], "evaluation": scored, "provenance": provenance}
    predictions = [{"game_id": ids[0], "possession_number": ids[1],
                    "probabilities": {name: values[i] for name, values in fitted["predictions"]["probabilities"].items()}}
                   for i, ids in enumerate(fitted["predictions"]["row_ids"])]
    artifacts = {"plan": ("plan.snapshot.json", raw), "cohort": ("cohort.json", _json(cohort)),
                 "selected_rows": ("rows.selected.jsonl", b"".join(_jsonline(row) for row in rows)),
                 "predictions": ("predictions.jsonl", b"".join(_jsonline(row) for row in predictions)),
                 "model_result": ("model_result.json", _json(result))}
    report = {"schema_version": "exploratory-research-report-v1", **shared,
              "cohort": cohort, "split": {k: {"rows": len(v), "games": len({r['game_id'] for r in v})}
                                           for k, v in fitted["subsets"].items()},
              "limitations": plan["limitations"],
              "artifacts": {role: {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                            for role, (name, data) in artifacts.items()}}
    # Serialize everything before creating output; failures leave no successful report.
    files = [*artifacts.values(), ("report.json", _json(report)), ("report.md", _markdown(report, result))]
    recheck()
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files:
            with (output / name).open("xb") as stream:
                stream.write(data)
        recheck()
    except BaseException:
        shutil.rmtree(output)
        raise
    return report


def _jsonline(row):
    return (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("plan", "features", "inventory", "reconciliation", "source-manifest", "cache", "schedule", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--metadata", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    try:
        report = run_exploratory(plan_path=args.plan, feature_dir=args.features, inventory_path=args.inventory,
                                 reconciliation_path=args.reconciliation, source_manifest=args.source_manifest,
                                 cache=args.cache, schedule=args.schedule, metadata=args.metadata, output=args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}))
        return 1
    print(json.dumps({"status": report["status"], "analysis_id": report["analysis_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
