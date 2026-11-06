import pandas as pd

from categorize_defensive_fouls_okc_mil import build_def_foul_context


def test_build_def_foul_context_reuses_possession_flags(monkeypatch):
    df = pd.DataFrame(
        [
            {"orderNumber": 1, "actionNumber": 1, "teamId": 1, "teamTricode": "OKC", "possession": 1, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 1.0, "timeline_time": 1.0, "scoreHome": "2", "scoreAway": "0"},
            {"orderNumber": 2, "actionNumber": 2, "teamId": 2, "teamTricode": "MIL", "possession": 1, "actionType": "foul", "subType": "personal", "game_seconds_elapsed": 2.0, "timeline_time": 2.0, "scoreHome": "2", "scoreAway": "0"},
            {"orderNumber": 3, "actionNumber": 3, "teamId": 2, "teamTricode": "MIL", "possession": 2, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 3.0, "timeline_time": 3.0, "scoreHome": "2", "scoreAway": "2"},
        ]
    )

    monkeypatch.setattr("categorize_defensive_fouls_okc_mil.load_game_dataframe", lambda game_id: df)
    context = build_def_foul_context("0022500789")

    assert context["L_t"].tolist() == [0]
    assert context["N_t"].tolist() == [0]
    assert context["M_t"].tolist() == [1]
