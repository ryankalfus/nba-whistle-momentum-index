from pathlib import Path
import math
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculate_wmi_controlledgames_2025_26 import add_z_scores
from wmi_controlled_run_utils import compute_controlled_summary_for_game_ids
from wmi_controlled_utils import DEFAULT_CONTROLLED_FORMULA
from wmi_controlled_utils import add_controlled_exclusion_columns
from wmi_controlled_utils import build_controlled_possession_table_from_actions
from wmi_controlled_utils import calculate_wmi_controlled
from wmi_controlled_utils import period_to_bucket


def test_period_to_bucket_maps_regulation_and_overtime():
    assert period_to_bucket(1) == "1"
    assert period_to_bucket(4) == "4"
    assert period_to_bucket(5) == "OT"
    assert period_to_bucket(7) == "OT"


def test_build_controlled_possession_table_from_actions_keeps_raw_variables():
    actions = [
        {
            "orderNumber": 1,
            "actionNumber": 1,
            "clock": "PT12M00.00S",
            "period": 1,
            "teamId": 100,
            "teamTricode": "HOM",
            "possession": 100,
            "actionType": "jumpball",
            "subType": "",
            "scoreHome": "0",
            "scoreAway": "0",
        },
        {
            "orderNumber": 2,
            "actionNumber": 2,
            "clock": "PT11M50.00S",
            "period": 1,
            "teamId": 200,
            "teamTricode": "AWY",
            "possession": 100,
            "actionType": "foul",
            "subType": "personal",
            "scoreHome": "0",
            "scoreAway": "0",
        },
        {
            "orderNumber": 3,
            "actionNumber": 3,
            "clock": "PT11M40.00S",
            "period": 1,
            "teamId": 100,
            "teamTricode": "HOM",
            "possession": 100,
            "actionType": "shot",
            "subType": "2pt",
            "scoreHome": "2",
            "scoreAway": "0",
        },
        {
            "orderNumber": 4,
            "actionNumber": 4,
            "clock": "PT11M20.00S",
            "period": 1,
            "teamId": 200,
            "teamTricode": "AWY",
            "possession": 200,
            "actionType": "shot",
            "subType": "miss",
            "scoreHome": "2",
            "scoreAway": "0",
        },
        {
            "orderNumber": 5,
            "actionNumber": 5,
            "clock": "PT11M00.00S",
            "period": 1,
            "teamId": 200,
            "teamTricode": "AWY",
            "possession": 100,
            "actionType": "foul",
            "subType": "personal",
            "scoreHome": "2",
            "scoreAway": "0",
        },
        {
            "orderNumber": 6,
            "actionNumber": 6,
            "clock": "PT10M50.00S",
            "period": 1,
            "teamId": 200,
            "teamTricode": "AWY",
            "possession": 100,
            "actionType": "shot",
            "subType": "2pt",
            "scoreHome": "4",
            "scoreAway": "0",
        },
        {
            "orderNumber": 7,
            "actionNumber": 7,
            "clock": "PT10M30.00S",
            "period": 1,
            "teamId": 200,
            "teamTricode": "AWY",
            "possession": 200,
            "actionType": "shot",
            "subType": "miss",
            "scoreHome": "4",
            "scoreAway": "0",
        },
    ]

    out = build_controlled_possession_table_from_actions(actions=actions, game_id="002TEST")

    assert list(out["period"]) == [1, 1, 1, 1]
    assert list(out["period_bucket"]) == ["1", "1", "1", "1"]
    assert list(out["score_difference"]) == [2, -2, 4, -4]
    assert list(out["F_t"]) == [1, 0, 1, 0]
    assert list(out["L_t"]) == [0, 1, 1, 1]
    assert list(out["N_t"]) == [1, 1, 0, 0]
    assert list(out["M_t"]) == [2, 0, 1, 0]
    assert list(out["score_margin_excluded_t"]) == [0, 0, 0, 0]
    assert list(out["intentional_foul_excluded_t"]) == [0, 0, 0, 0]
    assert list(out["controlled_excluded_t"]) == [0, 0, 0, 0]


def test_add_controlled_exclusion_columns_applies_score_margin_and_intentional_rules():
    df = pd.DataFrame(
        {
            "period": [4, 4, 3, 4, 4, 5, 4],
            "seconds_left_in_game": [45, 35, 20, 15, 14, 12, 80],
            "score_difference": [15, 4, 6, 1, 0, 16, -15],
            "F_t": [0, 1, 1, 1, 1, 0, 0],
        }
    )

    out = add_controlled_exclusion_columns(df)

    assert list(out["period_bucket"]) == ["4", "4", "3", "4", "4", "OT", "4"]
    assert list(out["score_margin_excluded_t"]) == [1, 0, 0, 0, 0, 1, 1]
    assert list(out["intentional_foul_excluded_t"]) == [0, 1, 0, 1, 0, 0, 0]
    assert list(out["controlled_excluded_t"]) == [1, 1, 0, 1, 0, 1, 1]


def _synthetic_controlled_df():
    return pd.DataFrame(
        {
            "game_id": ["G1"] * 12,
            "possession_number": list(range(1, 13)),
            "period": [1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 5, 5],
            "period_bucket": ["1", "1", "1", "1", "2", "2", "2", "2", "4", "4", "OT", "OT"],
            "offense_team": ["AAA", "AAA", "BBB", "BBB", "AAA", "AAA", "BBB", "BBB", "AAA", "BBB", "AAA", "BBB"],
            "defense_team": ["BBB", "BBB", "AAA", "AAA", "BBB", "BBB", "AAA", "AAA", "BBB", "AAA", "BBB", "AAA"],
            "seconds_left_in_game": [2800, 2750, 2700, 2650, 2000, 1950, 1900, 1850, 100, 95, 25, 20],
            "score_difference": [2, 1, -1, -2, 4, 3, -3, -4, 2, -2, 4, -1],
            "L_t": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            "F_t": [0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1],
            "N_t": [0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 0],
            "M_t": [0, 2, 1, 2, 0, 2, 0, 1, 2, 0, 0, 1],
            "score_margin_excluded_t": [0] * 12,
            "intentional_foul_excluded_t": [0] * 12,
            "controlled_excluded_t": [0] * 12,
        }
    )


def test_calculate_wmi_controlled_returns_adjusted_ratio_and_formula():
    result = calculate_wmi_controlled(_synthetic_controlled_df())

    assert result["fit_status"] == "ok"
    assert result["formula"] == DEFAULT_CONTROLLED_FORMULA
    assert result["rows_before_exclusion"] == 12
    assert result["rows_used_in_model"] == 12
    assert result["adjusted_mean_M_t_if_L_t_eq_1"] is not None
    assert result["adjusted_mean_M_t_if_L_t_eq_0"] is not None
    assert result["WMI_controlled"] is not None
    assert result["beta_L_t"] is not None
    assert result["irr_L_t"] is not None
    assert math.isclose(
        result["WMI_controlled"],
        result["adjusted_mean_M_t_if_L_t_eq_1"] / result["adjusted_mean_M_t_if_L_t_eq_0"],
    )


def test_calculate_wmi_controlled_handles_no_l_t_variation():
    df = _synthetic_controlled_df()
    df["L_t"] = 0

    result = calculate_wmi_controlled(df)

    assert result["fit_status"] == "no_l_t_variation"
    assert result["WMI_controlled"] is None


def test_compute_controlled_summary_for_game_ids_builds_pooled_summary(monkeypatch):
    df = _synthetic_controlled_df()
    df["game_id"] = ["G1"] * 6 + ["G2"] * 6

    def fake_build_controlled_tables_for_game_ids(game_ids, session, timeout, max_workers):
        assert game_ids == ["G1", "G2"]
        return [df[df["game_id"] == "G1"].copy(), df[df["game_id"] == "G2"].copy()], []

    monkeypatch.setattr(
        "wmi_controlled_run_utils.build_controlled_tables_for_game_ids",
        fake_build_controlled_tables_for_game_ids,
    )

    summary, all_possessions, failed_ids = compute_controlled_summary_for_game_ids(
        ["G1", "G2"],
        season="TEST",
        session=object(),
        as_of_utc_date="2026-03-01",
        max_workers=2,
    )

    assert summary["season"] == "TEST"
    assert summary["games_requested"] == 2
    assert summary["games_succeeded"] == 2
    assert summary["games_failed"] == 0
    assert summary["fit_status"] == "ok"
    assert len(all_possessions) == 12
    assert failed_ids == []


def test_add_z_scores_for_controlled_game_list():
    df = pd.DataFrame({"WMI_controlledgame": [0.9, 1.1, 1.3]})

    out, mean_wmi, std_wmi = add_z_scores(df)

    assert math.isclose(mean_wmi, 1.1)
    assert math.isclose(std_wmi, pd.Series([0.9, 1.1, 1.3]).std(ddof=0))
    assert "wmi_controlledgame_z_score" in out.columns
