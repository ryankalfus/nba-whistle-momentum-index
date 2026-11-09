"""plan-stage5-v1 contract tests on synthetic multi-season rows; software behavior, not scientific validity."""

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from plan_stage5_fixtures import SPLIT, synthetic
from whistle_research import audit, evaluation, exploratory, exploratory_cohort, modeling, plan_stage5, team_fouls


@pytest.fixture(scope="module")
def data():
    return synthetic()


@pytest.fixture(scope="module")
def fitted(data):
    rows, supplement = data
    return plan_stage5.fit(copy.deepcopy(rows), copy.deepcopy(supplement), SPLIT)


@pytest.fixture(scope="module")
def evaluated(fitted):
    return plan_stage5.evaluate(fitted)


def row(**kw):
    base = {"clock": 100.0, "score_difference": -5, "home_defense": 0, "period": 4, "game_type": "regular_season"}
    return {**base, **kw}


STATE = {"defense_team_fouls": 4, "offense_team_fouls": 2, "defense_in_penalty": 1, "offense_in_penalty": 0}


def test_context_definitions():
    values = dict(zip(plan_stage5.NUMERIC, plan_stage5.context(row(), STATE)))
    assert values["offense_home"] == 1 and values["offense_margin"] == 5
    assert values["clock_squared"] == 10000 and values["margin_squared"] == 25
    assert values["playoff"] == 0 and values["late_close"] == 1
    assert values["defense_team_fouls"] == 4 and values["offense_in_penalty"] == 0
    assert dict(zip(plan_stage5.NUMERIC, plan_stage5.context(row(game_type="playoffs"), STATE)))["playoff"] == 1
    for change, late in ((dict(period=3), 0), (dict(clock=121.0), 0), (dict(clock=120.0), 1),
                         (dict(score_difference=11), 0), (dict(score_difference=-10), 1), (dict(period=5), 1)):
        assert dict(zip(plan_stage5.NUMERIC, plan_stage5.context(row(**change), STATE)))["late_close"] == late
    missing = dict(zip(plan_stage5.NUMERIC, plan_stage5.context(row(score_difference=None),
                                                                {**STATE, "offense_team_fouls": None})))
    assert np.isnan(missing["offense_margin"]) and np.isnan(missing["late_close"])
    assert np.isnan(missing["offense_team_fouls"])


def test_outcome_and_future_fields_never_enter_context():
    changed = row(outcome=1, final_wmi=9.0, next_two_foul=1, date="2030-01-01", game_id="x")
    assert plan_stage5.context(changed, STATE) == plan_stage5.context(row(), STATE)


def test_model_b_is_model_a_plus_exactly_one_column(data):
    rows, supplement = data
    states = team_fouls.attach(rows, supplement)
    numeric, teams, history = plan_stage5._columns(rows, states)
    index = np.arange(len(rows))
    a = plan_stage5._design(numeric, teams, history, index, with_history=False)
    b = plan_stage5._design(numeric, teams, history, index, with_history=True)
    k = 2 * len(plan_stage5.NUMERIC)
    assert b.shape[1] == a.shape[1] + 1
    assert np.array_equal(np.nan_to_num(a[:, :k], nan=-9), np.nan_to_num(b[:, :k], nan=-9))
    assert np.array_equal(a[:, k:], b[:, k + 1:])
    assert plan_stage5.feature_names(True) == [*plan_stage5.feature_names(False), plan_stage5.HISTORY]


def test_folds_are_chronological_whole_game_and_expanding(fitted):
    manifest = fitted["diagnostics"]["split_manifest"]
    seasons = {g: g.split("-")[0] + "-" + g.split("-")[1] for g in
               (game for fold in manifest.values() for part in fold.values() for game in part)}
    assert {seasons[g] for g in manifest["validation"]["train_games"]} == {"2020-21"}
    assert {seasons[g] for g in manifest["validation"]["evaluate_games"]} == {"2021-22"}
    for fold in plan_stage5.TEST_FOLDS:
        record = manifest[fold["evaluate"]]
        assert not set(record["train_games"]) & set(record["evaluate_games"])
        assert {seasons[g] for g in record["train_games"]} == set(fold["train"])
        assert {seasons[g] for g in record["evaluate_games"]} == {fold["evaluate"]}
    assert len(manifest["2024-25"]["evaluate_games"]) == 30  # regular season plus playoffs


def test_shared_c_comes_from_model_a_validation_and_is_used_everywhere(fitted):
    validation = fitted["diagnostics"]["validation"]
    best = min(validation["candidate_scores"], key=lambda c: (c["validation_logloss"],
                                                              plan_stage5.C_GRID.index(c["C"])))
    assert validation["shared_C"] == best["C"]
    for record in fitted["diagnostics"]["folds"].values():
        assert record["C"] == record["context_a"]["C"] == record["history_b"]["C"] == validation["shared_C"]


def test_paired_rows_exclude_only_game_starts_and_models_are_matched(fitted):
    probabilities, folds = fitted["predictions"]["probabilities"], fitted["predictions"]["fold"]
    test_rows = fitted["subsets"]["test"]
    for name in plan_stage5.MODELS:
        assert [p is None for p in probabilities[name]] == [r["possession_number"] <= 2 for r in test_rows]
    assert [f is None for f in folds] == [r["possession_number"] <= 2 for r in test_rows]
    assert all(f == r["season"] for f, r in zip(folds, test_rows) if f is not None)
    for season, record in fitted["diagnostics"]["history_exclusions"].items():
        assert record["excluded_game_start_rows"] == record["rows"] - record["paired_rows"]


def test_playoff_indicator_is_constant_in_training_and_unlearned(fitted):
    for label, record in fitted["diagnostics"]["folds"].items():
        for name in ("context_a", "history_b"):
            assert record[name]["coefficients"]["playoff"] == 0.0
            assert record[name]["scaler_mean"]["playoff"] == 0.0


def test_preprocessing_uses_training_rows_only(fitted):
    rows = fitted["rows"]
    record = fitted["diagnostics"]["folds"]["2023-24"]["context_a"]
    train_seasons = set(plan_stage5.TEST_FOLDS[1]["train"])
    clocks = [r["clock"] for r in rows if r["season"] in train_seasons and r["possession_number"] > 2]
    assert record["scaler_mean"]["clock"] == pytest.approx(np.mean(clocks))
    assert record["imputer_medians"]["clock"] == pytest.approx(np.median(clocks))


def test_test_season_changes_do_not_change_selection_or_earlier_fits(data, fitted):
    rows, supplement = copy.deepcopy(data[0]), copy.deepcopy(data[1])
    for r in rows:
        if r["season"] == "2024-25":
            r["outcome"] = 1 - r["outcome"]
            r["clock"] = 5.0
            r["score_difference"] = 30
            r["score_margin"] = 30
    # Keep lags consistent with flipped outcomes so the integrity check still passes.
    by_game = {}
    for r in rows:
        by_game.setdefault(r["game_id"], []).append(r)
    for block in by_game.values():
        for i, r in enumerate(block):
            r["previous_foul_1"] = block[i - 1]["outcome"] if i >= 1 else None
            r["previous_foul_2"] = block[i - 2]["outcome"] if i >= 2 else None
    refit = plan_stage5.fit(rows, supplement, SPLIT)
    assert refit["diagnostics"]["validation"] == fitted["diagnostics"]["validation"]
    for label in ("2022-23", "2023-24", "2024-25"):
        for name in ("context_a", "history_b"):
            assert (modeling._fitted_pipeline_digest(refit["pipelines"][f"{label}/{name}"])
                    == modeling._fitted_pipeline_digest(fitted["pipelines"][f"{label}/{name}"]))


def test_evaluation_arithmetic_and_closed_decision(fitted, evaluated):
    probabilities, folds = fitted["predictions"]["probabilities"], fitted["predictions"]["fold"]
    keep = [i for i, f in enumerate(folds) if f is not None]
    test_rows = fitted["subsets"]["test"]
    y = np.array([test_rows[i]["outcome"] for i in keep], dtype=float)
    a = np.array([probabilities["context_a"][i] for i in keep])
    b = np.array([probabilities["history_b"][i] for i in keep])
    delta = evaluation.log_losses(y, b) - evaluation.log_losses(y, a)
    pooled = evaluated["pooled"]
    assert pooled["paired_logloss"]["estimate"] == pytest.approx(delta.mean(), abs=1e-14)
    assert pooled["paired_logloss"]["relative_reduction"] == pytest.approx(
        delta.mean() / evaluation.log_losses(y, a).mean())
    assert pooled["rows"] == len(keep) == evaluated["row_count"]
    assert sum(s["rows"] for s in evaluated["seasons"].values()) == pooled["rows"]
    for block in (pooled, *evaluated["seasons"].values()):
        low, high = block["paired_logloss"]["interval"]
        assert low <= high
    assert evaluated["decision"]["classification"] == "NOT_SPECIFIED"
    assert set(evaluated["game_type_breakdown"]) == {"regular_season", "playoffs"}
    assert all(p >= plan_stage5.CLIP and p <= 1 - plan_stage5.CLIP for p in a)


def test_stratified_bootstrap_resamples_within_strata():
    strata = [(np.array([1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0])),
              (np.array([0.0, 0.0]), np.array([2.0, 2.0]))]
    # Every draw keeps three stratum-one games and two stratum-two games: 3 / 7 exactly.
    assert plan_stage5.stratified_bootstrap(strata, np.random.default_rng(1), 50) == pytest.approx([3 / 7, 3 / 7])
    one = plan_stage5.stratified_bootstrap(strata, np.random.default_rng(5), 200)
    two = plan_stage5.stratified_bootstrap(strata, np.random.default_rng(5), 200)
    assert one == two
    with pytest.raises(ValueError, match="two games"):
        plan_stage5.stratified_bootstrap([(np.array([1.0]), np.array([1.0]))], np.random.default_rng(0), 10)


def test_calibration_fits_recover_perfect_calibration():
    rng = np.random.default_rng(3)
    p = rng.uniform(0.05, 0.6, 200_000)
    y = (rng.random(p.size) < p).astype(float)
    assert plan_stage5.calibration_intercept(y, p) == pytest.approx(0, abs=0.02)
    intercept, slope = plan_stage5.calibration_slope(y, p)
    assert slope == pytest.approx(1, abs=0.03) and intercept == pytest.approx(0, abs=0.05)


def test_clipping_is_counted():
    values, count = plan_stage5.clip([0.0, 1e-9, 0.5, 1.0])
    assert count == 3 and values.min() == plan_stage5.CLIP and values.max() == 1 - plan_stage5.CLIP


@pytest.mark.parametrize("tamper", ["season_partition", "defense_count", "missing_state"])
def test_fit_fails_closed(data, tamper):
    rows, supplement = copy.deepcopy(data[0]), copy.deepcopy(data[1])
    if tamper == "season_partition":
        for r in rows:
            if r["season"] == "2021-22":
                r["season"] = "2022-23"
        match = "season and date partition"
    elif tamper == "defense_count":
        supplement[rows[50]["game_id"]][rows[50]["possession_number"]]["defense_team_fouls"] = 99
        match = "disagree"
    else:
        del supplement[rows[50]["game_id"]][rows[50]["possession_number"]]
        match = "cover exactly"
    with pytest.raises(ValueError, match=match):
        plan_stage5.fit(rows, supplement, SPLIT)


def test_specification_binds_data_and_model_path():
    spec = plan_stage5.specification()
    assert spec == plan_stage5.specification() and spec["schema"] == "plan-stage5-v1"
    assert set(spec["sources"]) == set(plan_stage5.SOURCES)
    assert spec["meaningful_gain"] is None and spec["probability_clip"] == [1e-6, 1 - 1e-6]
    assert spec["bootstrap"]["resamples"] == 2000


def test_cohort_selection_accepts_lists_and_keeps_dict_behavior():
    plan = {"cohort": {"season": "2024-25", "game_type": "regular_season"}, "split": SPLIT}
    cohort, _ = exploratory_cohort._selection(plan)
    game = {"date": "2024-11-01", "season": "2024-25", "game_type": "regular_season"}
    assert exploratory_cohort._partition(game, cohort, SPLIT) == ("test", None)
    assert exploratory_cohort._partition({**game, "game_type": "playoffs", "date": "2025-05-01"},
                                         cohort, SPLIT) == (None, "outside_cohort")
    listed = [{"season": "2020-21", "game_type": "regular_season"}, {"season": "2024-25", "game_type": "playoffs"}]
    cohort, _ = exploratory_cohort._selection({"cohort": listed, "split": SPLIT})
    assert exploratory_cohort._partition({**game, "game_type": "playoffs", "date": "2025-05-01"},
                                         cohort, SPLIT) == ("test", None)
    assert exploratory_cohort._partition(game, cohort, SPLIT) == (None, "outside_cohort")
    for bad in ([], [listed[0], listed[0]], [{"season": "2024-26", "game_type": "playoffs"}]):
        with pytest.raises(ValueError, match="cohort"):
            exploratory_cohort._selection({"cohort": bad, "split": SPLIT})


@pytest.fixture
def runner(tmp_path, monkeypatch, data):
    rows, supplement = data
    plan = json.loads(Path("research/exploratory_2026_11_08/specification.json").read_text())
    plan.update(schema_version="provisional-exploratory-plan-v3", analysis_id="synthetic-plan-stage5",
                split=SPLIT, declared_date="2026-11-09", declared_at="2026-11-09T12:00:00+00:00",
                max_selected_rows=1_000_000,
                cohort=[{"season": s, "game_type": "regular_season"} for s in plan_stage5.SEASON_PARTITION]
                + [{"season": "2024-25", "game_type": "playoffs"}])
    plan["model_specification"] = plan_stage5.specification()
    plan["model_specification_sha256"] = audit.digest(plan["model_specification"])
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    source = tmp_path / "input.json"
    source.write_text("immutable fixture")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    calls, prepared = [], []

    def prepare(**kwargs):
        prepared.append(True)
        return {"rows": copy.deepcopy(rows),
                "report": {"counts": {"included_games": 156, "included_rows": len(rows)},
                           "exclusion_reason_counts": {}, "parser_version": "synthetic-parser-v1",
                           "parser_sha256": "a" * 64, "feature_version": "synthetic-features-v1",
                           "feature_sha256": "b" * 64, "frame_sha256": "c" * 64,
                           "source_map": {"synthetic-input": digest}},
                "inputs": [{"role": "synthetic_fixture", "path": source, "bytes": source.stat().st_size,
                            "sha256": digest}], "recheck": lambda: None}

    def supplement_for_games(game_ids, **kwargs):
        calls.append((set(game_ids), kwargs))
        return copy.deepcopy(supplement)

    monkeypatch.setitem(sys.modules, "whistle_research.exploratory_cohort", SimpleNamespace(prepare_cohort=prepare))
    monkeypatch.setattr(team_fouls, "supplement_for_games", supplement_for_games)
    kwargs = {"plan_path": path, "feature_dir": tmp_path / "f", "inventory_path": tmp_path / "i",
              "reconciliation_path": tmp_path / "r", "source_manifest": tmp_path / "m", "cache": tmp_path / "c",
              "schedule": tmp_path / "s", "metadata": [tmp_path / "md"], "output": tmp_path / "result"}
    return SimpleNamespace(plan=plan, path=path, kwargs=kwargs, calls=calls, rows=rows, prepared=prepared)


def test_v3_plan_runs_with_closed_flags_and_bound_artifacts(runner):
    report = exploratory.run_exploratory(**runner.kwargs)
    output = runner.kwargs["output"]
    result = json.loads((output / "model_result.json").read_text())
    for packet in (report, result):
        assert packet["status"] == "EXPLORATORY_ONLY_NOT_VALIDATED"
        assert all(packet[k] is False for k in ("eligible", "scientific_approval", "publication_authorized"))
    assert result["schema_version"] == "provisional-exploratory-result-v3"
    assert report["schema_version"] == "exploratory-research-report-v3"
    assert runner.calls and runner.calls[0][0] == {r["game_id"] for r in runner.rows}
    assert result["evaluation"]["decision"]["classification"] == "NOT_SPECIFIED"
    assert set(result["provenance"]["fitted_pipeline_sha256"]) == {
        f"{f['evaluate']}/{m}" for f in plan_stage5.TEST_FOLDS for m in ("context_a", "history_b")}
    for item in report["artifacts"].values():
        assert hashlib.sha256((output / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    states = [json.loads(line) for line in (output / "team_foul_states.jsonl").read_text().splitlines()]
    assert len(states) == len(runner.rows)
    predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text().splitlines()]
    assert {p["fold"] for p in predictions} == {None, "2022-23", "2023-24", "2024-25"}
    markdown = (output / "report.md").read_text()
    assert "plan-stage5-v1" in markdown and "Pooled" in markdown and "playoffs" in markdown


@pytest.mark.parametrize("change", ["dict_cohort", "ceiling", "v2_spec"])
def test_v3_plan_validation(runner, change):
    if change == "dict_cohort":
        runner.plan["cohort"] = {"season": "2024-25", "game_type": "regular_season"}
    elif change == "ceiling":
        runner.plan["max_selected_rows"] = 250000
    else:
        from whistle_research import meeting_ab
        runner.plan["model_specification"] = meeting_ab.specification()
        runner.plan["model_specification_sha256"] = audit.digest(runner.plan["model_specification"])
    runner.path.write_text(json.dumps(runner.plan))
    with pytest.raises(ValueError):
        exploratory.run_exploratory(**runner.kwargs)
    assert not runner.kwargs["output"].exists() and not runner.calls and not runner.prepared


@pytest.mark.parametrize("schema", ["provisional-exploratory-plan-v1", "provisional-exploratory-plan-v2"])
@pytest.mark.parametrize("change", ["list_cohort", "v3_ceiling"])
def test_v1_v2_plans_keep_single_cohort_and_250000_ceiling(runner, schema, change):
    from whistle_research import meeting_ab
    runner.plan["schema_version"] = schema
    spec = modeling.specification() if schema.endswith("v1") else meeting_ab.specification()
    runner.plan["model_specification"], runner.plan["model_specification_sha256"] = spec, audit.digest(spec)
    if change == "list_cohort":
        runner.plan["max_selected_rows"] = 250000
    else:
        runner.plan["cohort"] = {"season": "2024-25", "game_type": "regular_season"}
    runner.path.write_text(json.dumps(runner.plan))
    with pytest.raises(ValueError):
        exploratory.run_exploratory(**runner.kwargs)
    assert not runner.prepared


def test_bootstrap_golden_call_pattern_and_season_seeds(fitted, evaluated):
    """Pin the declared draw order: one integers((2000, n)) call per season in fold order."""
    probabilities, folds = fitted["predictions"]["probabilities"], fitted["predictions"]["fold"]
    test_rows = fitted["subsets"]["test"]
    strata = []
    for fold in plan_stage5.TEST_FOLDS:
        idx = [i for i, f in enumerate(folds) if f == fold["evaluate"]]
        y = np.array([test_rows[i]["outcome"] for i in idx], dtype=float)
        a = np.array([probabilities["context_a"][i] for i in idx])
        b = np.array([probabilities["history_b"][i] for i in idx])
        delta = evaluation.log_losses(y, b) - evaluation.log_losses(y, a)
        g = np.array([test_rows[i]["game_id"] for i in idx])
        order = sorted(set(g))
        strata.append((np.array([delta[g == k].sum() for k in order]),
                       np.array([(g == k).sum() for k in order], dtype=float)))

    def literal(parts, rng):
        td, tn = np.zeros(2000), np.zeros(2000)
        for sums, counts in parts:
            draw = rng.integers(len(sums), size=(2000, len(sums)))
            td += sums[draw].sum(1)
            tn += counts[draw].sum(1)
        return np.quantile(td / tn, [0.025, 0.975])

    assert np.allclose(literal(strata, np.random.default_rng(137)),
                       evaluated["pooled"]["paired_logloss"]["interval"], rtol=0, atol=1e-14)
    for k, fold in enumerate(plan_stage5.TEST_FOLDS, start=1):
        assert np.allclose(literal([strata[k - 1]], np.random.default_rng([137, k])),
                           evaluated["seasons"][fold["evaluate"]]["paired_logloss"]["interval"], rtol=0, atol=1e-14)
