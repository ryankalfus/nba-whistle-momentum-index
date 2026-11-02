"""Synthetic model contracts; fixture attestations are not scientific evidence."""

import copy
import json

import numpy as np
import pytest

from whistle_research import audit, modeling
from whistle_research.evaluation import _evaluate


SPLIT = {"train_start": "2030-01-01", "tune_start": "2030-01-04",
         "test_start": "2030-01-05", "test_end": "2030-01-07"}


def synthetic_bound_evidence(tmp_path):
    from test_release import synthetic_artifacts, promote_args
    from whistle_research import release
    fixture = synthetic_artifacts(tmp_path)
    rows = fixture["rows"]
    dataset, _ = release.prepare_promotion(**promote_args(fixture))
    plan = fixture["plan"]
    protocol = {key: plan[key] for key in ("plan_sha256", "parser_version", "parser_sha256", "frame_sha256")}
    protocol.update(feature_version=dataset["feature_version"], feature_sha256=dataset["feature_sha256"],
                    rows_sha256=dataset["rows_sha256"], frozen=True, freeze_id="synthetic-model-fixture",
                    frozen_at="2029-02-01T00:00:00Z", evaluation_exposure="unseen_at_freeze",
                    exposure_inventory_ref="synthetic inventory", unused_cohort_evidence_ref="synthetic unused fixture",
                    specification_sha256=audit.digest(modeling.specification()), meaningful_gain=.01, split=SPLIT)
    protocol["protocol_sha256"] = audit.digest(protocol)
    return rows, {"plan": plan, "reviews": fixture["reviews"], "config": fixture["config"],
                  "dataset": dataset, "protocol": protocol, "source_root": str(fixture["cache"]),
                  "evaluation_started_at": "2031-01-01T00:00:00Z"}


def test_chronological_whole_game_split_and_boundaries():
    rows = modeling._synthetic_rows(4, games=6, possessions=12)
    split = modeling.chronological_split(rows, SPLIT)
    sets = [{r["game_id"] for r in split[k]} for k in ("train", "tune", "test")]
    assert [len(s) for s in sets] == [3, 1, 2]
    assert not sets[0] & sets[1] and not sets[1] & sets[2] and not sets[0] & sets[2]
    assert max(r["date"] for r in split["train"]) < min(r["date"] for r in split["tune"])
    for invalid in ({**SPLIT, "tune_start": SPLIT["test_start"]}, {**SPLIT, "test_end": "2030-01-05"}):
        with pytest.raises(ValueError):
            modeling.chronological_split(rows, invalid)


@pytest.mark.parametrize("change", ["duplicate", "date", "season", "order", "outcome", "target_nan", "negative_margin"])
def test_ambiguous_or_missing_rows_fail_without_dropping(change):
    rows = modeling._synthetic_rows(4, games=6, possessions=12)
    if change == "duplicate":
        rows.insert(1, copy.deepcopy(rows[0]))
    elif change == "date":
        rows[1]["date"] = "2030-01-05"
    elif change == "season":
        rows[1]["season"] = "changed"
    elif change == "order":
        rows[0], rows[1] = rows[1], rows[0]
    elif change == "negative_margin":
        rows[0]["score_margin"] = -1
    else:
        rows[0]["outcome"] = None if change == "outcome" else float("nan")
    with pytest.raises(ValueError):
        modeling.validate_rows(rows)


def test_design_allowlist_ignores_outcome_future_and_unknown_extra_columns():
    rows = modeling._synthetic_rows(3, games=6, possessions=12)
    changed = copy.deepcopy(rows)
    for row in changed:
        row.update(outcome=1 - row["outcome"], next_foul=1, final_wmi=1000, terminal_score=999)
    before, names = modeling._design(rows, nonlinear=True, history=True)
    after, new_names = modeling._design(changed, nonlinear=True, history=True)
    assert names == new_names
    assert before.tolist() == after.tolist()
    suffix = copy.deepcopy(rows)
    for row in suffix[20:]:
        row["score_margin"] = 1000
        row["outcome"] = 1
    assert modeling._design(suffix, nonlinear=True, history=True)[0][:20].tolist() == before[:20].tolist()


def test_train_only_scaling_selection_and_matched_rows():
    rows = modeling._synthetic_rows(5, games=6, possessions=24)
    for row in rows:
        if row["date"] >= SPLIT["tune_start"]:
            row["score_margin"] = 1000
            row["start_type"] = "unseen-after-training"
    fitted = modeling._fit(rows, SPLIT)
    train = fitted["subsets"]["train"]
    for name, pipe in fitted["pipelines"].items():
        scaler = pipe.named_steps["transform"].named_transformers_["numeric"].named_steps["scale"]
        assert scaler.mean_[2] == pytest.approx(np.mean([r["score_margin"] for r in train]))
        categories = pipe.named_steps["transform"].named_transformers_["categorical"].categories_
        assert "value:unseen-after-training" not in categories[-1]
        assert fitted["diagnostics"][name]["tuning_candidates"] == len(modeling.C_GRID)
    predictions = fitted["predictions"]
    assert set(predictions["probabilities"]) == set(modeling.MODEL_NAMES)
    assert all(len(p) == len(predictions["row_ids"]) for p in predictions["probabilities"].values())
    changed = copy.deepcopy(rows)
    for row in changed:
        if row["date"] >= SPLIT["test_start"]:
            row["outcome"] = 1 - row["outcome"]
    other = modeling._fit(changed, SPLIT)
    assert fitted["diagnostics"] == other["diagnostics"]
    assert fitted["predictions"] == other["predictions"]


def test_missing_context_has_fixed_indicators_and_is_not_target_filtering():
    rows = modeling._synthetic_rows(6, games=6, possessions=24)
    for row in rows:
        row["clock"] = None
        row["start_type"] = None
        row["previous_foul_2"] = None
    fitted = modeling._fit(rows, SPLIT)
    assert len(fitted["predictions"]["row_ids"]) == 48
    design, names = modeling._design(rows, nonlinear=True, history=True)
    assert all(design[:, len(names) + 1] == 1)
    assert all(design[:, -1] == modeling.UNKNOWN)


def test_single_class_and_nonconvergence_fail_explicitly(monkeypatch):
    rows = modeling._synthetic_rows(7, games=6, possessions=24)
    single = copy.deepcopy(rows)
    for row in single:
        if row["date"] < SPLIT["tune_start"]:
            row["outcome"] = 0
    with pytest.raises(ValueError, match="single-class"):
        modeling._fit(single, SPLIT)
    monkeypatch.setattr(modeling, "MAX_ITER", 1)
    with pytest.raises(ValueError, match="nonconvergence"):
        modeling._fit(rows, SPLIT)


def test_bound_synthetic_evidence_passes_existing_gate_and_real_api(tmp_path):
    rows, evidence = synthetic_bound_evidence(tmp_path)
    assert audit.check_gate(evidence["plan"], evidence["reviews"], evidence["config"])["status"] == "PASS_CONDITIONAL"
    result = modeling.fit_real(rows, evidence=evidence)
    assert result["evaluation"]["row_count"] == 48
    assert result["protocol_sha256"] == evidence["protocol"]["protocol_sha256"]


@pytest.mark.parametrize("change", ["audit", "freeze", "protocol_hash", "source", "parser", "frame", "rows", "eligible", "critical", "threshold", "spec", "exposure", "feature", "complete"])
def test_missing_or_broken_bound_evidence_refuses_before_fit(tmp_path, change, monkeypatch):
    rows, evidence = synthetic_bound_evidence(tmp_path)
    if change == "audit":
        evidence["reviews"]["games"] = []
    elif change == "source":
        source = evidence["plan"]["frame"][0]["source_file"]
        (tmp_path / "cache" / source).write_text("changed bytes")
    elif change == "rows":
        rows[0]["outcome"] = 1 - rows[0]["outcome"]
    elif change == "parser":
        evidence["dataset"]["parser_sha256"] = "a" * 64
    elif change == "frame":
        evidence["dataset"]["frame_sha256"] = "a" * 64
    elif change == "feature":
        evidence["dataset"]["feature_sha256"] = "a" * 64
    elif change == "complete":
        evidence["dataset"]["games"][0]["complete"] = None
    elif change in ("eligible", "critical"):
        evidence["dataset"]["games"][0]["eligible" if change == "eligible" else "critical_unresolved"] = None
    else:
        field, value = {"freeze": ("frozen", False), "protocol_hash": ("protocol_sha256", "x"),
                        "threshold": ("meaningful_gain", None), "spec": ("specification_sha256", "a" * 64),
                        "exposure": ("evaluation_exposure", "already_viewed")}[change]
        evidence["protocol"][field] = value
        if change != "protocol_hash":
            evidence["protocol"]["protocol_sha256"] = audit.digest({k: v for k, v in evidence["protocol"].items() if k != "protocol_sha256"})
    def forbidden(*args, **kwargs):
        pytest.fail("fit executed before gate refusal")
    monkeypatch.setattr(modeling, "_fit", forbidden)
    with pytest.raises(modeling.BlockedError):
        modeling.fit_real(rows, evidence=evidence)


def test_real_data_without_evidence_and_real_cli_block(capsys):
    with pytest.raises(modeling.BlockedError):
        modeling.fit_real(modeling._synthetic_rows(2), evidence=None)
    assert modeling.main(["real"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_demo_reproducible_without_guaranteeing_improvement():
    first = modeling.synthetic_demo(20261102)
    second = modeling.synthetic_demo(20261102)
    assert first == second
    assert first["evaluation"]["decision"]["classification"] == "NOT_SPECIFIED"
    assert first["evaluation"]["paired_logloss"]["interval"][1] > 0


def test_shuffled_labels_can_worsen_history_model():
    rows = modeling._synthetic_rows(10, games=6, possessions=36)
    labels = np.array([r["outcome"] for r in rows])
    differences = []
    # Report the entire fixed seed range in the test, rather than selecting a
    # favorable permutation. Random labels need not favor either candidate.
    for seed in range(10):
        shuffled = np.random.default_rng(seed).permutation(labels)
        for row, label in zip(rows, shuffled, strict=True):
            row["outcome"] = int(label)
        fitted = modeling._fit(rows, SPLIT)
        result = _evaluate(fitted["subsets"]["test"], fitted["predictions"])
        differences.append(result["paired_logloss"]["estimate"])
    assert max(differences) > 0
    assert min(differences) < 0


def test_cli_has_no_arbitrary_input_or_overwrite_mode(tmp_path):
    with pytest.raises(SystemExit) as error:
        modeling.main(["synthetic", "--input", "unvalidated.json"])
    assert error.value.code == 2
    existing = tmp_path / "report.json"
    existing.write_text("preserve artifact\n")
    with pytest.raises(SystemExit) as error:
        modeling.main(["synthetic", "--output", str(existing)])
    assert error.value.code == 2
    assert existing.read_text() == "preserve artifact\n"


def test_signed_score_difference_is_context_for_both_stronger_models_only():
    rows = modeling._synthetic_rows(4, games=6, possessions=24)
    rows[0]["score_difference"] = -20
    rows[1]["score_difference"] = 20
    modeling.validate_rows(rows)
    additive, additive_names = modeling._design(rows, nonlinear=False, history=False)
    context, context_names = modeling._design(rows, nonlinear=True, history=False)
    history, history_names = modeling._design(rows, nonlinear=True, history=True)
    assert "score_difference" not in additive_names
    index = context_names.index("score_difference")
    assert list(context[:2, index]) == [-20, 20]
    assert context_names == history_names[:-2]
    assert history[:, :len(context_names)].tolist() == context[:, :len(context_names)].tolist()
    assert len(additive) == len(context) == len(history)


@pytest.mark.parametrize("suffix", [".json", ".jsonl"])
def test_real_cli_runs_actual_fit_with_legitimately_bound_synthetic_fixture(tmp_path, suffix):
    rows, evidence = synthetic_bound_evidence(tmp_path)
    rows_path = tmp_path / f"rows{suffix}"
    if suffix == ".jsonl":
        rows_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    else:
        rows_path.write_text(json.dumps(rows))
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence))
    output = tmp_path / "result.json"
    assert modeling.main(["real", "--rows", str(rows_path), "--evidence", str(evidence_path),
                          "--output", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["status"] == "GATED_EXPLORATORY_RESULT_NOT_PUBLICATION_APPROVAL"
    assert result["evaluation"]["row_count"] == 48
    assert result["protocol_sha256"] == evidence["protocol"]["protocol_sha256"]


@pytest.mark.parametrize("kind", ["missing_audit", "invalid_json", "nonfinite", "overflow", "missing_file", "duplicate_field"])
def test_real_cli_bad_inputs_or_gate_failures_never_fit(tmp_path, monkeypatch, kind):
    rows_path = tmp_path / "rows.json"
    evidence_path = tmp_path / "evidence.json"
    rows_path.write_text(json.dumps(modeling._synthetic_rows(1, games=6, possessions=3)))
    if kind == "missing_audit":
        evidence_path.write_text("{}")
    else:
        _, evidence = synthetic_bound_evidence(tmp_path)
        evidence_path.write_text(json.dumps(evidence))
    if kind == "invalid_json":
        rows_path.write_text("[invalid")
    elif kind == "nonfinite":
        evidence_path.write_text('{"unknown":NaN}')
    elif kind == "overflow":
        rows_path.write_text('[{"outcome":1e999}]')
    elif kind == "missing_file":
        rows_path.unlink()
    elif kind == "duplicate_field":
        evidence_path.write_text('{"frozen":true,"frozen":false}')
    def forbidden(*args, **kwargs):
        pytest.fail("model fit executed with missing/invalid gate evidence")
    monkeypatch.setattr(modeling, "_fit", forbidden)
    output = tmp_path / "blocked.json"
    assert modeling.main(["real", "--rows", str(rows_path), "--evidence", str(evidence_path),
                          "--output", str(output)]) == 1
    result = json.loads(output.read_text())
    assert result["status"] == "BLOCKED"
    assert result["reasons"]
    assert "predictions" not in result


def test_real_cli_protects_output_before_any_input_read_or_fit(tmp_path, monkeypatch, capsys):
    output = tmp_path / "preserved.json"
    output.write_text("preserve existing output\n")
    def forbidden(*args, **kwargs):
        pytest.fail("fit executed before output protection")
    monkeypatch.setattr(modeling, "fit_real", forbidden)
    assert modeling.main(["real", "--rows", "missing.json", "--evidence", "missing-evidence.json",
                          "--output", str(output)]) == 1
    assert output.read_text() == "preserve existing output\n"
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_synthetic_cli_refuses_supplied_real_rows(tmp_path):
    with pytest.raises(SystemExit) as error:
        modeling.main(["synthetic", "--rows", str(tmp_path / "rows.json")])
    assert error.value.code == 2


def test_public_evaluation_refits_once_and_binds_fresh_predictions(tmp_path, monkeypatch):
    from whistle_research.evaluation import evaluate_real
    rows, evidence = synthetic_bound_evidence(tmp_path)
    fit = modeling._fit
    calls = []
    def counted(rows, split):
        calls.append(True)
        return fit(rows, split)
    monkeypatch.setattr(modeling, "_fit", counted)
    result = evaluate_real(rows, evidence=evidence)
    assert len(calls) == 1
    provenance = result["provenance"]
    assert provenance["rows_sha256"] == modeling.row_digest(rows)
    assert provenance["protocol_sha256"] == evidence["protocol"]["protocol_sha256"]
    assert provenance["feature_sha256"] == evidence["protocol"]["feature_sha256"]
    assert set(provenance["fitted_pipeline_sha256"]) == set(modeling.MODEL_NAMES[1:])
    assert all(audit.valid_sha(value) for value in provenance["fitted_pipeline_sha256"].values())
    assert provenance["implementation_sha256"] == modeling.specification()["sources"]
    stale = {"row_ids": result["row_ids"], "probabilities": {name: [.99] * len(result["row_ids"]) for name in modeling.MODEL_NAMES}}
    with pytest.raises(TypeError):
        evaluate_real(rows, stale, evidence=evidence)


def test_real_cli_checks_failed_audit_before_loading_target_export(tmp_path, monkeypatch, capsys):
    evidence_path = tmp_path / "blocked-evidence.json"
    evidence_path.write_text("{}")
    def forbidden(*args, **kwargs):
        pytest.fail("target export read before passing independent audit gate")
    monkeypatch.setattr(modeling, "_read_rows", forbidden)
    assert modeling.main(["real", "--rows", "protected-or-large.jsonl", "--evidence", str(evidence_path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "BLOCKED"


def test_standalone_real_api_cannot_bypass_promotion_with_hand_constructed_eligibility(tmp_path, monkeypatch):
    rows, evidence = synthetic_bound_evidence(tmp_path)
    evidence["dataset"].pop("promotion_inputs")
    def forbidden(*args, **kwargs):
        pytest.fail("manual eligibility bypass reached fitting")
    monkeypatch.setattr(modeling, "_fit", forbidden)
    with pytest.raises(modeling.BlockedError, match="promotion_reverification_required"):
        modeling.fit_real(rows, evidence=evidence)


def test_standalone_real_api_rechecks_actual_trace_flags_after_promotion(tmp_path, monkeypatch):
    from pathlib import Path
    from whistle_research import release
    rows, evidence = synthetic_bound_evidence(tmp_path)
    directory = Path(evidence["dataset"]["promotion_inputs"]["feature_directory"])
    provenance = directory / "row_provenance.jsonl"
    traces = [json.loads(line) for line in provenance.read_text().splitlines()]
    traces[0]["audit_flags"] = ["violation_requires_audit"]
    provenance.write_text("".join(json.dumps(trace) + "\n" for trace in traces))
    original = release.read_json(directory / "manifest.json")
    original["row_provenance_sha256"] = release.file_digest(provenance)[1]
    (directory / "manifest.json").write_text(json.dumps(original))
    def forbidden(*args, **kwargs):
        pytest.fail("altered original provenance reached fitting")
    monkeypatch.setattr(modeling, "_fit", forbidden)
    with pytest.raises(modeling.BlockedError, match="unresolved_row_audit_flags"):
        modeling.fit_real(rows, evidence=evidence)
