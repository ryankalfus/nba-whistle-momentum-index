"""Synthetic runner fixtures test software contracts, not source validity."""

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import warnings

import pytest
from sklearn.exceptions import ConvergenceWarning

from whistle_research import audit, exploratory, modeling, release


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    plan = json.loads(Path("research/exploratory_2026_11_08/specification.json").read_text())
    rows = modeling._synthetic_rows(5, games=6, possessions=24)
    for row in rows:
        row["date"] = row["date"].replace("2030", "2024")
    plan["split"] = {"train_start": "2024-01-01", "tune_start": "2024-01-04",
                     "test_start": "2024-01-05", "test_end": "2024-01-07"}
    plan["model_specification"] = modeling.specification()
    plan["model_specification_sha256"] = audit.digest(plan["model_specification"])
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    source = tmp_path / "input.json"
    source.write_text("immutable fixture")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    calls = []
    rechecks = []

    def prepare(**kwargs):
        calls.append(kwargs)
        return {"rows": rows, "report": {"counts": {"included_games": 6, "included_rows": len(rows)},
                                        "exclusion_reason_counts": {}, "parser_version": "synthetic-parser-v1",
                                        "parser_sha256": "a" * 64, "feature_version": "synthetic-features-v1",
                                        "feature_sha256": "b" * 64, "frame_sha256": "c" * 64,
                                        "source_map": {"synthetic-input": digest}},
                "inputs": [{"role": "synthetic_fixture", "path": source, "bytes": source.stat().st_size,
                            "sha256": digest}], "recheck": lambda: rechecks.append(True)}

    monkeypatch.setitem(sys.modules, "whistle_research.exploratory_cohort", SimpleNamespace(prepare_cohort=prepare))
    kwargs = {"plan_path": path, "feature_dir": tmp_path / "features", "inventory_path": tmp_path / "inventory",
              "reconciliation_path": tmp_path / "reconciliation", "source_manifest": tmp_path / "manifest",
              "cache": tmp_path / "cache", "schedule": tmp_path / "schedule", "metadata": [tmp_path / "metadata"],
              "output": tmp_path / "result"}
    return SimpleNamespace(plan=plan, rows=rows, path=path, source=source, calls=calls,
                           rechecks=rechecks, kwargs=kwargs)


def save_plan(fixture):
    fixture.path.write_text(json.dumps(fixture.plan))


def load_result(output):
    return json.loads((output / "model_result.json").read_text())


def test_real_pure_fit_outputs_reopenable_bound_artifacts_and_closed_gates(fixture):
    report = exploratory.run_exploratory(**fixture.kwargs)
    output = fixture.kwargs["output"]
    result = load_result(output)
    assert report == json.loads((output / "report.json").read_text())
    assert len(fixture.rechecks) == 3
    for packet in (report, result):
        assert packet["status"] == "EXPLORATORY_ONLY_NOT_VALIDATED"
        assert packet["evaluation_exposure"] == "retrospective_previously_exposed"
        assert all(packet[k] is False for k in ("eligible", "scientific_approval", "publication_authorized"))
    for item in report["artifacts"].values():
        path = output / item["path"]
        assert path.resolve().is_relative_to(output.resolve())
        assert path.stat().st_size == item["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    selected = [json.loads(line) for line in (output / "rows.selected.jsonl").read_text().splitlines()]
    assert selected == fixture.rows
    predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    assert [[p["game_id"], p["possession_number"]] for p in predictions] == result["evaluation"]["row_ids"]
    assert all(set(p["probabilities"]) == set(modeling.MODEL_NAMES) for p in predictions)
    assert result["evaluation"]["decision"]["classification"] == "NOT_SPECIFIED"
    assert result["provenance"]["rows_sha256"] == modeling.row_digest(fixture.rows)
    for descriptor in result["provenance"]["inputs"]:
        assert not Path(descriptor["path"]).is_absolute()
        data = (output / descriptor["path"]).read_bytes()
        assert len(data) == descriptor["bytes"]
        assert hashlib.sha256(data).hexdigest() == descriptor["sha256"]
    for key in ("parser_version", "parser_sha256", "feature_version", "feature_sha256", "frame_sha256", "source_map"):
        assert result["provenance"][key] == report["cohort"][key]
    raw_plan = (output / "plan.snapshot.json").read_bytes()
    assert raw_plan == fixture.path.read_bytes()
    assert report["plan_sha256"] == result["plan_sha256"] == hashlib.sha256(raw_plan).hexdigest()
    assert "row_ids" not in report
    assert str(output.parent) not in json.dumps(report) + json.dumps(result)
    with pytest.raises(modeling.BlockedError):
        modeling.fit_real(fixture.rows, evidence=result)
    with pytest.raises(modeling.BlockedError):
        release.prepare_promotion(output, plan=result, reviews=[], config={},
                                  source_manifest=fixture.source, cache=output,
                                  schedule=fixture.source, metadata=[])
    with pytest.raises(ValueError):
        modeling.require_evidence(fixture.rows, None)


@pytest.mark.parametrize("change", ["unknown", "eligible", "threshold", "schema", "spec", "spec_bool", "digest", "date", "exposure", "cohort", "max"])
def test_invalid_plan_refused_before_source_access(fixture, change):
    if change == "unknown":
        fixture.plan["unexpected"] = True
    elif change == "eligible":
        fixture.plan["eligible"] = True
    elif change == "threshold":
        fixture.plan["meaningful_gain"] = .01
    elif change == "schema":
        fixture.plan["schema_version"] = "other"
    elif change == "spec":
        fixture.plan["model_specification"]["C_grid"] = [1]
    elif change == "spec_bool":
        fixture.plan["model_specification"]["C_grid"][1] = True
    elif change == "digest":
        fixture.plan["model_specification_sha256"] = "0" * 64
    elif change == "date":
        fixture.plan["split"]["test_start"] = "2024-01-01"
    elif change == "exposure":
        fixture.plan["evaluation_exposure"] = "unseen_at_freeze"
    elif change == "cohort":
        fixture.plan["cohort"]["unexpected"] = 1
    else:
        fixture.plan["max_selected_rows"] = True
    save_plan(fixture)
    with pytest.raises((ValueError, TypeError)):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.calls
    assert not fixture.kwargs["output"].exists()


@pytest.mark.parametrize("raw", ['{"schema_version":1,"schema_version":2}', '{"x":NaN}', '{"x":1e999}'])
def test_nonfinite_duplicate_plan_before_source_reads(fixture, raw):
    fixture.path.write_text(raw)
    with pytest.raises(ValueError):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.calls


def test_output_collision_refused_before_even_plan_read(fixture):
    fixture.path.unlink()
    fixture.kwargs["output"].mkdir()
    sentinel = fixture.kwargs["output"] / "preserve"
    sentinel.write_text("original")
    with pytest.raises(ValueError, match="output already exists"):
        exploratory.run_exploratory(**fixture.kwargs)
    assert sentinel.read_text() == "original"
    assert not fixture.calls


def test_unknown_targets_never_silently_dropped(fixture):
    fixture.rows[0]["outcome"] = None
    with pytest.raises(ValueError, match="binary integer outcome"):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.kwargs["output"].exists()


def test_test_label_and_future_column_changes_preserve_fits(fixture):
    exploratory.run_exploratory(**fixture.kwargs)
    original = load_result(fixture.kwargs["output"])
    fixture.kwargs["output"] = fixture.kwargs["output"].with_name("changed")
    for row in fixture.rows:
        row["future_outcome"] = 999
        row["final_score"] = 1000
        if row["date"] >= fixture.plan["split"]["test_start"]:
            row["outcome"] = 1 - row["outcome"]
    exploratory.run_exploratory(**fixture.kwargs)
    changed = load_result(fixture.kwargs["output"])
    assert original["diagnostics"] == changed["diagnostics"]
    assert original["provenance"]["fitted_pipeline_sha256"] == changed["provenance"]["fitted_pipeline_sha256"]
    assert original["provenance"]["test_features_sha256"] == changed["provenance"]["test_features_sha256"]
    assert original["evaluation"]["models"] != changed["evaluation"]["models"]


def test_single_class_and_nonconvergence_refused_without_outputs(fixture, monkeypatch):
    original = copy.deepcopy(fixture.rows)
    for row in fixture.rows:
        row["outcome"] = 0
    with pytest.raises(ValueError, match="single-class"):
        exploratory.run_exploratory(**fixture.kwargs)
    fixture.rows[:] = original
    fit = modeling.LogisticRegression.fit

    def nonconvergent(self, *args, **kwargs):
        result = fit(self, *args, **kwargs)
        warnings.warn("test convergence failure", ConvergenceWarning)
        return result

    monkeypatch.setattr(modeling.LogisticRegression, "fit", nonconvergent)
    with pytest.raises(ValueError, match="nonconvergence"):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.kwargs["output"].exists()


@pytest.mark.parametrize("target", ["input", "plan", "code"])
def test_consumed_bytes_drift_refuses_publication(fixture, monkeypatch, target):
    fit = modeling._fit
    digest = exploratory.file_digest
    drift = []

    def changed_fit(*args, **kwargs):
        fitted = fit(*args, **kwargs)
        if target == "input":
            fixture.source.write_text("mutated")
        elif target == "plan":
            fixture.path.write_text("{}")
        else:
            drift.append(True)
        return fitted

    def changed_digest(path):
        size, sha = digest(path)
        return (size, "0" * 64) if drift and path.name == "exploratory.py" else (size, sha)

    monkeypatch.setattr(modeling, "_fit", changed_fit)
    monkeypatch.setattr(exploratory, "file_digest", changed_digest)
    with pytest.raises(ValueError, match="changed"):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.kwargs["output"].exists()


def test_write_failure_cleans_new_directory_only(fixture, monkeypatch):
    original = Path.open

    def fail_report(self, *args, **kwargs):
        if self.name == "report.json" and args == ("xb",):
            raise OSError("simulated disk failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_report)
    with pytest.raises(OSError, match="simulated"):
        exploratory.run_exploratory(**fixture.kwargs)
    assert not fixture.kwargs["output"].exists()
    assert fixture.source.read_text() == "immutable fixture"


def test_cli_requires_every_explicit_input_and_returns_provisional_status(fixture, capsys):
    with pytest.raises(SystemExit):
        exploratory.main([])
    flags = {"plan": "plan_path", "features": "feature_dir", "inventory": "inventory_path",
             "reconciliation": "reconciliation_path", "source-manifest": "source_manifest", "cache": "cache",
             "schedule": "schedule", "output": "output"}
    args = [part for flag, key in flags.items() for part in ("--" + flag, str(fixture.kwargs[key]))]
    args += ["--metadata", str(fixture.kwargs["metadata"][0])]
    assert exploratory.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == exploratory.STATUS
