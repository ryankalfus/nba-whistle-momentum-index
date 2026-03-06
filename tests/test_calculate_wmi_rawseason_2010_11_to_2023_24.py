from calculate_wmi_rawseason_2010_11_to_2023_24 import game_id, game_wmi_components, season_label


def test_season_label_and_game_id_are_stable():
    assert season_label(24) == "2024-25"
    assert game_id(24, 7) == "0022400007"


def test_game_wmi_components_uses_two_possession_window():
    actions = [
        {
            "orderNumber": 1,
            "actionNumber": 1,
            "clock": "PT12M00.00S",
            "period": 1,
            "teamId": 1,
            "teamTricode": "OKC",
            "possession": 1,
            "actionType": "2pt",
            "subType": "",
        },
        {
            "orderNumber": 2,
            "actionNumber": 2,
            "clock": "PT11M59.00S",
            "period": 1,
            "teamId": 2,
            "teamTricode": "MIL",
            "possession": 1,
            "actionType": "foul",
            "subType": "personal",
        },
        {
            "orderNumber": 3,
            "actionNumber": 3,
            "clock": "PT11M40.00S",
            "period": 1,
            "teamId": 2,
            "teamTricode": "MIL",
            "possession": 2,
            "actionType": "2pt",
            "subType": "",
        },
        {
            "orderNumber": 4,
            "actionNumber": 4,
            "clock": "PT11M20.00S",
            "period": 1,
            "teamId": 1,
            "teamTricode": "OKC",
            "possession": 3,
            "actionType": "2pt",
            "subType": "",
        },
    ]

    assert game_wmi_components(actions) == (1, 1, 0.0, 1.0)
