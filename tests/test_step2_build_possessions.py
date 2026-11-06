import pandas as pd

from step2_build_possessions import parse_possessions


def test_parse_possessions_accepts_explicit_game_id():
    df = pd.DataFrame(
        [
            {"orderNumber": 1, "actionNumber": 1, "teamId": 1, "teamTricode": "OKC", "possession": 1, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 10.0},
            {"orderNumber": 2, "actionNumber": 2, "teamId": 2, "teamTricode": "MIL", "possession": 1, "actionType": "foul", "subType": "personal", "game_seconds_elapsed": 10.0},
            {"orderNumber": 3, "actionNumber": 3, "teamId": 2, "teamTricode": "MIL", "possession": 2, "actionType": "2pt", "subType": "", "game_seconds_elapsed": 20.0},
        ]
    )

    possessions = parse_possessions(df, game_id="demo-game")

    assert possessions["game_id"].tolist() == ["demo-game", "demo-game"]
    assert possessions["defensive_foul_count"].tolist() == [1, 0]
