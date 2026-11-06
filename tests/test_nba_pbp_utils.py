import pandas as pd

from nba_pbp_utils import (
    DEFAULT_SINGLE_GAME_ID,
    actions_to_dataframe,
    calculate_context_flags,
    clock_to_seconds,
    count_defensive_fouls,
    playbyplay_url,
)


def test_clock_to_seconds_parses_nba_clock_strings():
    assert clock_to_seconds("PT11M24.50S") == 684.5
    assert clock_to_seconds(None) is None


def test_playbyplay_url_uses_shared_default_game_id():
    assert DEFAULT_SINGLE_GAME_ID in playbyplay_url(DEFAULT_SINGLE_GAME_ID)


def test_calculate_context_flags_uses_two_possession_window():
    prior, upcoming = calculate_context_flags([1, 0, 1, 0])

    assert prior == [0, 1, 1, 1]
    assert upcoming == [1, 1, 0, 0]


def test_count_defensive_fouls_ignores_technical_and_offensive_calls():
    group = pd.DataFrame(
        [
            {"actionType": "foul", "subType": "personal", "teamId": 2},
            {"actionType": "foul", "subType": "technical", "teamId": 2},
            {"actionType": "foul", "subType": "offensive", "teamId": 2},
            {"actionType": "2pt", "subType": "", "teamId": 2},
        ]
    )

    assert count_defensive_fouls(group, defense_team_id=2) == 1


def test_legacy_event_timeline_uses_five_minute_overtime_and_decimal_clock():
    events = [
        {"orderNumber": 10, "actionNumber": 10, "period": 5, "clock": "PT05M00S"},
        {"orderNumber": 11, "actionNumber": 11, "period": 5, "clock": "PT04M59.5S"},
    ]
    assert actions_to_dataframe(events)["game_seconds_elapsed"].tolist() == [2880, 2880.5]
