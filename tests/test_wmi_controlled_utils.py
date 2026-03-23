from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wmi_controlled_utils import CONTROLLED_FORMULA
from wmi_controlled_utils import add_controlled_context_columns
from wmi_controlled_utils import fit_wmi_controlled_model
from wmi_controlled_utils import period_bucket_for_period


def test_add_controlled_context_columns_adds_l_count_t_and_period_bucket():
    df = pd.DataFrame(
        {
            "game_id": ["002TEST"] * 4,
            "possession_group": [1, 2, 3, 4],
            "period": [1, 2, 4, 5],
            "offense_team": ["AAA", "BBB", "AAA", "BBB"],
            "defense_team": ["BBB", "AAA", "BBB", "AAA"],
            "seconds_left_in_game": [4200.0, 3600.0, 40.0, 20.0],
            "score_difference": [0, 1, 4, 5],
            "foul_called_this_possession": [1, 1, 0, 1],
        }
    )

    out = add_controlled_context_columns(df)

    assert list(out["L_count_t"]) == [0, 1, 2, 1]
    assert list(out["L_t"]) == [0, 1, 1, 1]
    assert list(out["F_t"]) == [1, 1, 0, 1]
    assert list(out["N_t"]) == [1, 1, 1, 0]
    assert list(out["M_t"]) == [2, 2, 0, 1]
    assert list(out["period_bucket"]) == [1, 2, 4, "OT"]


def test_period_bucket_for_period_maps_overtime_to_ot():
    assert period_bucket_for_period(1) == 1
    assert period_bucket_for_period(4) == 4
    assert period_bucket_for_period(5) == "OT"
    assert period_bucket_for_period(7) == "OT"


def test_add_controlled_context_columns_flags_intentional_fouls():
    df = pd.DataFrame(
        {
            "game_id": ["002TEST"] * 5,
            "period": [4, 4, 4, 3, 4],
            "offense_team": ["AAA"] * 5,
            "defense_team": ["BBB"] * 5,
            "seconds_left_in_game": [45.0, 46.0, 20.0, 20.0, 20.0],
            "score_difference": [3, 5, 2, 10, 10],
            "foul_called_this_possession": [1, 1, 1, 1, 0],
        }
    )

    out = add_controlled_context_columns(df)

    assert list(out["intentional_foul_excluded_t"]) == [1, 0, 0, 0, 0]


def test_fit_wmi_controlled_model_returns_trigger_summary():
    rng = np.random.default_rng(7)
    offense_teams = ["AAA", "BBB", "CCC", "DDD"]
    defense_teams = ["BBB", "CCC", "DDD", "AAA"]
    period_buckets = [1, 2, 3, 4, "OT"]
    rows = []

    for i in range(240):
        trigger = i % 3
        period_bucket = period_buckets[i % len(period_buckets)]
        seconds_left = float(4300 - ((i * 17) % 4300))
        score_difference = float((i % 13) - 6)
        logit = -1.2 + (0.45 * trigger) - (0.00005 * seconds_left) + (0.03 * score_difference)
        probability = 1.0 / (1.0 + np.exp(-logit))
        rows.append(
                {
                    "L_count_t": trigger,
                    "F_t": int(rng.binomial(1, probability)),
                    "seconds_left_in_game": seconds_left,
                    "score_difference": score_difference,
                    "period_bucket": period_bucket,
                    "offense_team": offense_teams[i % len(offense_teams)],
                    "defense_team": defense_teams[(i // 2) % len(defense_teams)],
                }
            )

    df = pd.DataFrame(rows)
    result = fit_wmi_controlled_model(df)

    assert result["trigger_variable"] == "L_count_t"
    assert result["formula"] == CONTROLLED_FORMULA
    assert result["fit_method"] == "logit"
    assert result["rows_used_in_model"] == len(df)
    assert isinstance(result["converged"], bool)
    assert np.isfinite(result["beta_trigger"])
    assert np.isfinite(result["odds_ratio_trigger"])
    assert np.isfinite(result["std_err_trigger"])
    assert np.isfinite(result["p_value_trigger"])
    assert np.isfinite(result["ci_low_beta"])
    assert np.isfinite(result["ci_high_beta"])
