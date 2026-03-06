import pandas as pd

from calculate_wmi_rawseason_2024_25 import build_possession_table_for_game, get_completed_regular_season_game_ids


def test_get_completed_regular_season_game_ids_spans_full_schedule():
    game_ids = get_completed_regular_season_game_ids()

    assert game_ids[0] == "0022400001"
    assert game_ids[-1] == "0022401230"
    assert len(game_ids) == 1230


def test_build_possession_table_for_game_builds_context(monkeypatch):
    df = pd.DataFrame(
        [
            {"orderNumber": 1, "actionNumber": 1, "teamId": 1, "teamTricode": "OKC", "possession": 1, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 1.0, "timeline_time": 1.0},
            {"orderNumber": 2, "actionNumber": 2, "teamId": 2, "teamTricode": "MIL", "possession": 1, "actionType": "foul", "subType": "personal", "game_seconds_elapsed": 2.0, "timeline_time": 2.0},
            {"orderNumber": 3, "actionNumber": 3, "teamId": 2, "teamTricode": "MIL", "possession": 2, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 3.0, "timeline_time": 3.0},
        ]
    )

    monkeypatch.setattr("calculate_wmi_rawseason_2024_25.load_game_dataframe_with_retry", lambda session, game_id, timeout=30, tries=4: df)
    table = build_possession_table_for_game(object(), "0022400001")

    assert table is not None
    assert table["F_t"].tolist() == [1, 0]
    assert table["L_t"].tolist() == [0, 1]
