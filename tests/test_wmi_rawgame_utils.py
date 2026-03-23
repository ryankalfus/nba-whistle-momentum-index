from pathlib import Path
import sys
import math

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wmi_rawgame_utils import build_possession_model_table_from_actions
from wmi_rawgame_utils import calculate_wmi_rawgame
from wmi_rawgame_utils import default_possession_table_out_path
from wmi_rawgame_utils import default_wmi_breakdown_out_path


def test_build_possession_model_table_from_actions_builds_expected_values():
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

    out = build_possession_model_table_from_actions(actions=actions, game_id="002TEST")

    assert list(out["game_id"]) == ["002TEST", "002TEST", "002TEST", "002TEST"]
    assert list(out["offense_team"]) == ["HOM", "AWY", "HOM", "AWY"]
    assert list(out["defense_team"]) == ["AWY", "HOM", "AWY", "HOM"]
    assert list(out["score_difference"]) == [2, -2, 4, -4]
    assert list(out["F_t"]) == [1, 0, 1, 0]
    assert list(out["L_t"]) == [0, 1, 1, 1]
    assert list(out["N_t"]) == [1, 1, 0, 0]
    assert list(out["M_t"]) == [2, 0, 1, 0]


def test_calculate_wmi_rawgame_returns_expected_ratio():
    df = pd.DataFrame(
        {
            "L_t": [0, 0, 1, 1],
            "F_t": [1, 0, 1, 0],
            "N_t": [1, 0, 0, 1],
        }
    )

    result = calculate_wmi_rawgame(df)

    assert result["n1_count_L_t_eq_1"] == 2
    assert result["n0_count_L_t_eq_0"] == 2
    assert math.isclose(result["sum_M_t_where_L_t_eq_1"], 1.0)
    assert math.isclose(result["sum_M_t_where_L_t_eq_0"], 2.0)
    assert math.isclose(result["mean_M_t_where_L_t_eq_1"], 0.5)
    assert math.isclose(result["mean_M_t_where_L_t_eq_0"], 1.0)
    assert math.isclose(result["WMI_rawgame"], 0.5)


def test_calculate_wmi_rawgame_requires_expected_columns():
    with pytest.raises(ValueError, match="Missing required columns"):
        calculate_wmi_rawgame(pd.DataFrame({"L_t": [0], "F_t": [1]}))


def test_default_output_paths_use_game_id():
    assert default_possession_table_out_path("0022500802") == "possession_model_table_0022500802.csv"
    assert default_wmi_breakdown_out_path("0022500802") == "wmi_rawgame_breakdown_0022500802.csv"
