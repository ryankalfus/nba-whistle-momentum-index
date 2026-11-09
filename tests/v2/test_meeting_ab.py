"""meeting-ab-v1 contract tests on synthetic rows; software behavior, not scientific validity."""

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from whistle_research import audit, exploratory, meeting_ab, modeling

SPLIT = {"train_start": "2030-01-01", "tune_start": "2030-01-31",
         "test_start": "2030-02-15", "test_end": "2030-03-02"}


@pytest.fixture(scope="module")
def rows():
    return meeting_ab.synthetic_rows(5, games=60, possessions=30)


@pytest.fixture(scope="module")
def fitted(rows):
    return meeting_ab.fit(copy.deepcopy(rows), SPLIT)


@pytest.mark.parametrize("lag1,lag2,flag,complete", [
    (0, 0, 0, True), (1, 0, 1, True), (0, 1, 1, True), (1, 1, 1, True),
    (None, None, 0, False), (0, None, 0, False), (1, None, 1, False), (None, 1, 1, False)])
def test_history_flag_truth_table_never_turns_unavailable_into_observed(lag1, lag2, flag, complete):
    assert meeting_ab.history_flag({"previous_foul_1": lag1, "previous_foul_2": lag2}) == (flag, complete)


@pytest.mark.parametrize("bad", [True, 2, -1, 0.5, "1"])
def test_history_flag_rejects_nonbinary_lags(bad):
    with pytest.raises(ValueError, match="0, 1 or null"):
        meeting_ab.history_flag({"previous_foul_1": bad, "previous_foul_2": 0})


def test_lag_integrity_reasons_and_interleaved_games():
    def row(game, number, lag1, lag2, outcome):
        return {"game_id": game, "possession_number": number, "previous_foul_1": lag1,
                "previous_foul_2": lag2, "outcome": outcome}
    rows = [row("a", 1, None, None, 1), row("b", 1, None, None, 0), row("a", 2, 1, None, 0),
            row("b", 2, 0, None, 1), row("a", 3, 0, 1, 1), row("b", 3, 1, 0, 0)]
    assert meeting_ab.check_lags(rows) == ["game_start"] * 4 + [None, None]


def test_lag_integrity_refuses_possession_gap_even_when_lags_coincide(rows):
    game = copy.deepcopy([r for r in rows if r["game_id"] == rows[0]["game_id"]])
    del game[10]
    # Rewrite lags so they match list neighbours; only the gap should be caught.
    for i, r in enumerate(game):
        r["previous_foul_1"] = game[i - 1]["outcome"] if i >= 1 else None
        r["previous_foul_2"] = game[i - 2]["outcome"] if i >= 2 else None
    with pytest.raises(ValueError, match="contiguous"):
        meeting_ab.check_lags(game)


def test_lag_integrity_refuses_unknown_outcome(rows):
    game = copy.deepcopy([r for r in rows if r["game_id"] == rows[0]["game_id"]])
    game[4]["outcome"] = None
    with pytest.raises(ValueError, match="known binary outcomes"):
        meeting_ab.check_lags(game)


@pytest.mark.parametrize("case", ["start_lag_filled", "wrong_observed_lag", "observed_lag_nulled"])
def test_lag_integrity_fails_closed(rows, case):
    game = copy.deepcopy([r for r in rows if r["game_id"] == rows[0]["game_id"]])
    if case == "start_lag_filled":
        game[0]["previous_foul_1"] = 0
    elif case == "wrong_observed_lag":
        game[3]["previous_foul_1"] = 1 - game[2]["outcome"]
    else:
        game[5]["previous_foul_2"] = None
    with pytest.raises(ValueError, match="does not equal"):
        meeting_ab.check_lags(game)


def test_model_b_is_model_a_plus_exactly_one_column(rows):
    a, a_names = meeting_ab._design(rows, history=False)
    b, b_names = meeting_ab._design([r for r in rows if r["possession_number"] > 2], history=True)
    a_kept = a[[i for i, r in enumerate(rows) if r["possession_number"] > 2]]
    assert b_names == [*a_names[:len(a_names)], "recent_defensive_foul"]
    assert b.shape[1] == a.shape[1] + 1
    numeric = len(a_names)
    assert (b[:, :numeric] == a_kept[:, :numeric]).all()
    assert (b[:, numeric + 1:] == a_kept[:, numeric:]).all()
    _, s1_names = meeting_ab._design(rows, history=True, incomplete=True)
    assert s1_names == [*a_names, "recent_defensive_foul", "history_incomplete"]


def test_outcome_and_future_fields_never_enter_design(rows):
    changed = copy.deepcopy(rows)
    for row in changed:
        row["outcome"] = 1 - row["outcome"]
        row["final_wmi"] = 9.9
        row["next_two_foul"] = 1
        row["defense_counted_fouls"] = 99
        row["start_type"] = "changed"
    for history, incomplete in ((False, False), (True, False), (True, True)):
        before = meeting_ab._design(rows, history=history, incomplete=incomplete)[0]
        after = meeting_ab._design(changed, history=history, incomplete=incomplete)[0]
        assert (before == after).all()


def test_primary_rows_exclude_only_unavailable_history_and_models_are_matched(rows, fitted):
    exclusions = fitted["diagnostics"]["history_exclusions"]
    for part, block in fitted["subsets"].items():
        games = len({r["game_id"] for r in block})
        assert exclusions[part]["excluded_by_reason"] == {"game_start": 2 * games}
        assert exclusions[part]["primary_rows"] == len(block) - 2 * games
        assert all(r["previous_foul_1"] is not None and r["previous_foul_2"] is not None
                   for r in fitted["primary"][part])
    probabilities = fitted["predictions"]["probabilities"]
    for name in meeting_ab.PRIMARY:
        assert [p is None for p in probabilities[name]] == [r["possession_number"] <= 2
                                                            for r in fitted["subsets"]["test"]]
    for name in meeting_ab.S1:
        assert None not in probabilities[name]
    train = fitted["primary"]["train"]
    assert fitted["diagnostics"]["base_rate"]["training_rate"] == np.mean([r["outcome"] for r in train])
    assert fitted["diagnostics"]["context_a"]["training_rows"] == len(train)
    assert fitted["diagnostics"]["s1_context_a"]["training_rows"] == len(fitted["subsets"]["train"])


def test_evaluation_reports_primary_and_s1_with_closed_decision(fitted):
    result = meeting_ab.evaluate(fitted)
    assert set(result["models"]) == set(meeting_ab.PRIMARY)
    assert result["row_count"] == len(fitted["primary"]["test"])
    paired = result["paired_logloss"]
    y = np.array([r["outcome"] for r in fitted["primary"]["test"]])
    probabilities = fitted["predictions"]["probabilities"]
    a = np.array([p for p in probabilities["context_a"] if p is not None])
    b = np.array([p for p in probabilities["history_b"] if p is not None])
    from whistle_research.evaluation import log_losses
    assert paired["estimate"] == pytest.approx((log_losses(y, b) - log_losses(y, a)).mean(), abs=1e-14)
    assert paired["interval"][0] <= paired["interval"][1]
    assert result["decision"]["classification"] == "NOT_SPECIFIED"
    s1 = result["sensitivities"]["s1_all_rows_incomplete_indicator"]
    assert set(s1["models"]) == set(meeting_ab.S1)
    assert s1["row_count"] == len(fitted["subsets"]["test"])


def test_test_label_changes_do_not_change_selection_or_fits(rows, fitted):
    changed = copy.deepcopy(rows)
    test_games = {r["game_id"] for r in fitted["subsets"]["test"]}
    # Flip test outcomes and keep lags consistent so the integrity check still holds.
    for game in test_games:
        block = [r for r in changed if r["game_id"] == game]
        for i, row in enumerate(block):
            row["outcome"] = 1 - row["outcome"]
            row["previous_foul_1"] = block[i - 1]["outcome"] if i >= 1 else None
            row["previous_foul_2"] = block[i - 2]["outcome"] if i >= 2 else None
    refit = meeting_ab.fit(changed, SPLIT)
    for name in ("context_a", "history_b", "s1_context_a", "s1_history_b"):
        assert refit["diagnostics"][name]["selected_C"] == fitted["diagnostics"][name]["selected_C"]
        assert (modeling._fitted_pipeline_digest(refit["pipelines"][name])
                == modeling._fitted_pipeline_digest(fitted["pipelines"][name]))


def test_tune_and_test_feature_changes_do_not_change_training_fit(rows, fitted):
    changed = copy.deepcopy(rows)
    held_out = {r["game_id"] for part in ("tune", "test") for r in fitted["subsets"][part]}
    for row in changed:
        if row["game_id"] in held_out:
            row["clock"] = 1.0
            row["score_margin"] = row["score_difference"] = 40.0
            row["defense_team_id"] = "unseen-team"
    refit = meeting_ab.fit(changed, SPLIT)
    for name in ("context_a", "history_b", "s1_context_a", "s1_history_b"):
        assert (modeling._fitted_pipeline_digest(refit["pipelines"][name])
                == modeling._fitted_pipeline_digest(fitted["pipelines"][name]))


def test_short_games_leave_primary_game_set_and_empty_primary_partition_is_refused(rows, fitted):
    test_games = sorted({r["game_id"] for r in fitted["subsets"]["test"]})
    short = test_games[0]
    trimmed = [r for r in copy.deepcopy(rows) if r["game_id"] != short or r["possession_number"] <= 2]
    result = meeting_ab.evaluate(meeting_ab.fit(trimmed, SPLIT))
    assert result["models"]["context_a"]["games"] == len(test_games) - 1
    assert result["sensitivities"]["s1_all_rows_incomplete_indicator"]["models"]["s1_context_a"]["games"] == len(test_games)
    all_short = [r for r in copy.deepcopy(rows) if r["game_id"] not in test_games or r["possession_number"] <= 2]
    with pytest.raises(ValueError, match="empty primary partition"):
        meeting_ab.fit(all_short, SPLIT)


@pytest.mark.parametrize("tamper", ["reorder", "shift_none", "drop_kept_row"])
def test_evaluate_refuses_misaligned_predictions(fitted, tamper):
    broken = copy.deepcopy(fitted)
    probabilities = broken["predictions"]["probabilities"]
    if tamper == "reorder":
        broken["predictions"]["row_ids"] = list(reversed(broken["predictions"]["row_ids"]))
    elif tamper == "shift_none":
        values = probabilities["history_b"]
        first = values.index(None)
        values[first], values[first + 2] = values[first + 2], values[first]
    else:
        broken["primary"]["test"] = broken["primary"]["test"][1:]
    with pytest.raises(ValueError, match="rows"):
        meeting_ab.evaluate(broken)


def test_single_class_training_refused(rows):
    changed = copy.deepcopy(rows)
    for row in changed:
        row["outcome"] = 0
        row["previous_foul_1"] = None if row["possession_number"] == 1 else 0
        row["previous_foul_2"] = None if row["possession_number"] <= 2 else 0
    with pytest.raises(ValueError, match="single-class"):
        meeting_ab.fit(changed, SPLIT)


def test_specification_is_stable_and_binds_reused_sources():
    spec = meeting_ab.specification()
    assert spec == meeting_ab.specification()
    assert spec["schema"] == "meeting-ab-v1"
    assert set(spec["sources"]) == {"meeting_ab.py", "modeling.py", "evaluation.py"}
    assert spec["models"] == ["base_rate", "context_a", "history_b", "s1_context_a", "s1_history_b"]
    assert "defense_counted_fouls" not in json.dumps(spec["context_numeric"])
    assert "game_type" not in spec["context_numeric"] + spec["categorical"]


@pytest.fixture
def runner(tmp_path, monkeypatch, rows):
    plan = json.loads(Path("research/exploratory_2026_11_08/specification.json").read_text())
    plan["schema_version"] = "provisional-exploratory-plan-v2"
    plan["analysis_id"] = "synthetic-meeting-ab"
    plan["split"] = SPLIT
    plan["declared_date"] = "2030-03-02"
    plan["declared_at"] = "2030-03-02T12:00:00+00:00"
    plan["model_specification"] = meeting_ab.specification()
    plan["model_specification_sha256"] = audit.digest(plan["model_specification"])
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    source = tmp_path / "input.json"
    source.write_text("immutable fixture")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    def prepare(**kwargs):
        return {"rows": copy.deepcopy(rows),
                "report": {"counts": {"included_games": 60, "included_rows": len(rows)},
                           "exclusion_reason_counts": {}, "parser_version": "synthetic-parser-v1",
                           "parser_sha256": "a" * 64, "feature_version": "synthetic-features-v1",
                           "feature_sha256": "b" * 64, "frame_sha256": "c" * 64,
                           "source_map": {"synthetic-input": digest}},
                "inputs": [{"role": "synthetic_fixture", "path": source, "bytes": source.stat().st_size,
                            "sha256": digest}], "recheck": lambda: None}

    monkeypatch.setitem(sys.modules, "whistle_research.exploratory_cohort", SimpleNamespace(prepare_cohort=prepare))
    kwargs = {"plan_path": path, "feature_dir": tmp_path / "f", "inventory_path": tmp_path / "i",
              "reconciliation_path": tmp_path / "r", "source_manifest": tmp_path / "m", "cache": tmp_path / "c",
              "schedule": tmp_path / "s", "metadata": [tmp_path / "md"], "output": tmp_path / "result"}
    return SimpleNamespace(plan=plan, path=path, kwargs=kwargs)


def test_v2_plan_runs_meeting_ab_with_closed_flags_and_bound_artifacts(runner):
    report = exploratory.run_exploratory(**runner.kwargs)
    output = runner.kwargs["output"]
    result = json.loads((output / "model_result.json").read_text())
    for packet in (report, result):
        assert packet["status"] == "EXPLORATORY_ONLY_NOT_VALIDATED"
        assert all(packet[k] is False for k in ("eligible", "scientific_approval", "publication_authorized"))
    assert set(result["evaluation"]["models"]) == set(meeting_ab.PRIMARY)
    assert "s1_all_rows_incomplete_indicator" in result["evaluation"]["sensitivities"]
    assert result["evaluation"]["decision"]["classification"] == "NOT_SPECIFIED"
    assert result["schema_version"] == "provisional-exploratory-result-v2"
    assert report["schema_version"] == "exploratory-research-report-v2"
    assert set(result["provenance"]["primary_partition_rows_sha256"]) == {"train", "tune", "test"}
    for item in report["artifacts"].values():
        assert hashlib.sha256((output / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    starts = [p for p in predictions if p["possession_number"] <= 2]
    assert starts and all(p["probabilities"]["history_b"] is None for p in starts)
    assert all(p["probabilities"]["s1_history_b"] is not None for p in predictions)
    markdown = (output / "report.md").read_text()
    assert "Model B (context + H) minus Model A (context)" in markdown
    assert "S1: all rows" in markdown and "game_start" in markdown


@pytest.mark.parametrize("change", ["v1_schema_with_meeting_spec", "v2_schema_with_matched_spec"])
def test_schema_and_specification_must_correspond(runner, change):
    if change == "v1_schema_with_meeting_spec":
        runner.plan["schema_version"] = "provisional-exploratory-plan-v1"
    else:
        runner.plan["model_specification"] = modeling.specification()
        runner.plan["model_specification_sha256"] = audit.digest(runner.plan["model_specification"])
    runner.path.write_text(json.dumps(runner.plan))
    with pytest.raises(ValueError, match="specification"):
        exploratory.run_exploratory(**runner.kwargs)
    assert not runner.kwargs["output"].exists()
