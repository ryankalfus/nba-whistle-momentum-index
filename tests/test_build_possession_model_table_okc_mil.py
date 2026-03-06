import pandas as pd

from build_possession_model_table_okc_mil import build_table


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, timeout=30):
        return DummyResponse(self._payload)


def make_payload():
    return {
        "game": {
            "actions": [
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
                    "scoreHome": "2",
                    "scoreAway": "0",
                },
                {
                    "orderNumber": 2,
                    "actionNumber": 2,
                    "clock": "PT11M50.00S",
                    "period": 1,
                    "teamId": 2,
                    "teamTricode": "MIL",
                    "possession": 1,
                    "actionType": "foul",
                    "subType": "personal",
                    "scoreHome": "2",
                    "scoreAway": "0",
                },
                {
                    "orderNumber": 3,
                    "actionNumber": 3,
                    "clock": "PT11M30.00S",
                    "period": 1,
                    "teamId": 2,
                    "teamTricode": "MIL",
                    "possession": 2,
                    "actionType": "2pt",
                    "subType": "",
                    "scoreHome": "2",
                    "scoreAway": "2",
                },
            ]
        }
    }


def test_build_table_uses_shared_context(monkeypatch):
    monkeypatch.setattr("nba_pbp_utils.requests.get", lambda url, timeout=30: DummyResponse(make_payload()))
    table = build_table("0022500789")

    assert isinstance(table, pd.DataFrame)
    assert table["F_t"].tolist() == [1, 0]
    assert table["L_t"].tolist() == [0, 1]
    assert table["N_t"].tolist() == [0, 0]
