"""Loss aggregation and paired game resampling have explicit units/weights."""

import numpy as np
import pytest

from whistle_research.evaluation import (
    _evaluate,
    evaluate_real,
    log_losses,
    paired_game_bootstrap,
    practical_decision,
)
from whistle_research.modeling import BlockedError, MODEL_NAMES, _synthetic_rows


def test_logloss_and_brier_hand_calculation_and_clipping():
    y, p = [0, 1], [.25, .75]
    assert log_losses(y, p) == pytest.approx([-np.log(.75)] * 2)
    assert np.isfinite(log_losses([0, 1], [1, 0])).all()
    assert log_losses([1], [1])[0] < 1e-12


@pytest.mark.parametrize("y,p", [([None], [.5]), ([0, 1], [.5]), ([0], [np.nan]),
                                ([1], [1.01]), ([], []), ([2], [.2])])
def test_unknown_targets_probabilities_or_mismatches_rejected(y, p):
    with pytest.raises(ValueError):
        log_losses(y, p)


def test_bootstrap_resamples_paired_game_sums_with_their_counts():
    sums, counts = [2., -3.], [2, 6]
    result = paired_game_bootstrap(sums, counts, resamples=200, seed=9)
    assert result["estimate"] == -.125  # (-1)/8, not the equal-game mean .25
    assert result["equal_game_estimate"] == .25
    assert result["interval"] == [-.5, 1.]
    assert result["conditions_on_fitted_models"] is True
    # Independent reconstruction of the same resampling axis/weighting.
    rng = np.random.default_rng(9)
    expected = []
    for _ in range(200):
        indices = rng.integers(2, size=2)
        expected.append(np.array(sums)[indices].sum() / np.array(counts)[indices].sum())
    assert result["interval"] == np.quantile(expected, [.025, .975]).tolist()
    # Scaling both paired sums and counts preserves the possession target.
    scaled = paired_game_bootstrap(np.array(sums) * 10, np.array(counts) * 10, resamples=200, seed=9)
    assert scaled["estimate"] == result["estimate"]
    assert scaled["interval"] == result["interval"]


@pytest.mark.parametrize("sums,counts", [([1], [1]), ([1, 2], [1]), ([1, 2], [1, 0]),
                                       ([1, np.nan], [1, 2]), ([1, 2], [1, 1.5])])
def test_cluster_inputs_fail_closed(sums, counts):
    with pytest.raises(ValueError):
        paired_game_bootstrap(sums, counts)


def scoring_fixture():
    rows = _synthetic_rows(1, games=2, possessions=3)
    # Unequal game lengths: 1 and 3 observations.
    rows = [rows[0], *rows[3:]]
    for row in rows:
        row["outcome"] = 1
    packet = {"row_ids": [[r["game_id"], r["possession_number"]] for r in rows],
              "probabilities": {name: [.5] * 4 for name in MODEL_NAMES}}
    packet["probabilities"]["nonlinear_history"] = [.9, .4, .4, .4]
    return rows, packet


def test_heldout_possession_equal_game_brier_and_breakdown_math():
    rows, packet = scoring_fixture()
    result = _evaluate(rows, packet)
    differences = np.log(.5) - np.log([.9, .4, .4, .4])
    assert result["paired_logloss"]["estimate"] == pytest.approx(differences.mean())
    assert result["paired_logloss"]["equal_game_estimate"] == pytest.approx((differences[0] + differences[1]) / 2)
    assert result["models"]["nonlinear_history"]["brier"] == pytest.approx((.1**2 + 3 * .6**2) / 4)
    assert result["models"]["base_rate"]["possession_logloss"] == pytest.approx(-np.log(.5))
    assert sum(b["count"] for b in result["models"]["nonlinear_history"]["calibration"]) == 4
    assert result["breakdown"]["game_type"]["playoffs"]["rows"] == 1
    assert result["breakdown"]["game_type"]["regular_season"]["rows"] == 3
    assert result["undefined_or_dropped_targets"] == 0
    assert result["decision"]["classification"] == "NOT_SPECIFIED"


@pytest.mark.parametrize("change", ["ids", "missing_model", "length", "missing_target"])
def test_all_models_score_identical_exact_rows_without_silent_drops(change):
    rows, packet = scoring_fixture()
    if change == "ids":
        packet["row_ids"].reverse()
    elif change == "missing_model":
        packet["probabilities"].pop("additive_context")
    elif change == "length":
        packet["probabilities"]["nonlinear_history"].pop()
    else:
        rows[0]["outcome"] = None
    with pytest.raises(ValueError):
        _evaluate(rows, packet)


def test_no_usefulness_without_frozen_meaningful_gain_or_equivalence_from_zero():
    assert practical_decision([-.01, .01])["classification"] == "NOT_SPECIFIED"
    assert practical_decision([-.1, .1], .01)["classification"] == "INCONCLUSIVE"
    assert practical_decision([-.03, -.02], .01)["classification"] == "USEFUL"
    assert practical_decision([-.005, .005], .01)["classification"] == "NEGLIGIBLE_UNDER_DECLARED_BAND"
    assert practical_decision([.02, .03], .01)["classification"] == "UNSUPPORTED_HISTORY_HARMFUL"
    # Touching a practical boundary remains inconclusive.
    assert practical_decision([-.02, -.01], .01)["classification"] == "INCONCLUSIVE"
    with pytest.raises(ValueError):
        practical_decision([-.01, .01], 0)


def test_real_evaluation_without_evidence_refuses_before_scoring():
    rows, packet = scoring_fixture()
    with pytest.raises(BlockedError):
        evaluate_real(rows, evidence=None)


def test_public_real_evaluation_cannot_accept_injected_or_stale_prediction_packets():
    rows, packet = scoring_fixture()
    packet["probabilities"]["nonlinear_history"] = [.99 if row["outcome"] else .01 for row in rows]
    with pytest.raises(TypeError):
        evaluate_real(rows, packet, evidence=None)
    with pytest.raises(TypeError):
        evaluate_real(rows, predictions=packet, evidence=None)
