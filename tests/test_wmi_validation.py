import json

import numpy as np
import pandas as pd

from wmi_possessions import (
    bonus_eligible,
    clock_seconds,
    components,
    reconstruct,
    sequence_features,
)
from wmi_utils import add_recent_foul_columns, calculate_wmi


def event(
    n,
    owner=100,
    team=100,
    period=1,
    clock="PT11M00.00S",
    kind="2pt",
    subtype="",
    home=2,
    away=0,
):
    return dict(
        actionNumber=n,
        orderNumber=n,
        teamId=team,
        teamTricode="HOM" if team == 100 else "AWY",
        period=period,
        clock=clock,
        possession=owner,
        actionType=kind,
        subType=subtype,
        scoreHome=home,
        scoreAway=away,
    )


def test_period_boundary_splits_same_owner_and_resets_clock():
    actions = [
        event(1, home=2),
        event(2, owner=200, team=200, clock="PT00M00.00S"),
        event(3, owner=200, team=200, period=2, clock="PT11M50.00S"),
    ]
    result = reconstruct(actions, "g")
    assert len(result) == 3
    assert list(result.period) == [1, 1, 2]
    assert result.iloc[-1].start_clock == 720
    assert result.iloc[-1].seconds_left_before == 2160


def test_future_overtime_and_scores_do_not_change_start_features():
    actions = [
        event(1),
        event(2, owner=200, team=200),
        event(3, owner=100, team=200, kind="foul", subtype="personal"),
    ]
    prefix = reconstruct(actions, "g")
    extended = reconstruct(
        actions + [event(4, period=5, clock="PT04M50.00S", home=99, away=99)], "g"
    )
    fields = [
        "start_clock",
        "score_difference_before",
        "seconds_left_before",
        "defense_team_fouls_before",
        "defense_bonus_before",
    ]
    pd.testing.assert_frame_equal(prefix[fields], extended.iloc[: len(prefix)][fields])
    assert extended.iloc[-1].seconds_left_before == 300
    assert extended.iloc[-1].elapsed_before == 2880


def test_bonus_is_before_foul_and_excludes_offensive_technical_double():
    actions = [event(1)]
    for n, subtype in enumerate(
        ["personal", "technical", "offensive", "double personal"], 2
    ):
        actions.append(event(n, team=200, kind="foul", subtype=subtype))
    actions += [
        event(6, owner=200, team=200),
        event(7, owner=100, team=200, kind="foul", subtype="personal"),
    ]
    out = reconstruct(actions, "g")
    assert out.iloc[0].defense_team_fouls_before == 0
    assert out.iloc[-1].defense_team_fouls_before == 1
    assert json.loads(out.iloc[-1].foul_events)[0]["team"] == "AWY"
    assert bonus_eligible(1, 121, 3, 0) == 0
    assert bonus_eligible(1, 120, 1, 1) == 1
    assert bonus_eligible(1, 120, 4, 0) == 1
    assert bonus_eligible(5, 200, 3, 0) == 1


def test_foul_windows_edges_and_decomposition():
    for n in [0, 1, 2, 20]:
        f = np.array(([1, 0, 1, 1, 0] * 4)[:n])
        d = add_recent_foul_columns(pd.DataFrame({"foul_called_this_possession": f}))
        assert d.L_t.tolist() == [int(any(f[max(0, i - 2) : i])) for i in range(n)]
        assert d.N_t.tolist() == [int(any(f[i + 1 : i + 3])) for i in range(n)]
        if n == 20:
            c = components(d)
            assert np.isclose(
                c["immediate_ratio"] * c["continuation_ratio"], calculate_wmi(d)["WMI"]
            )


def test_late_exclusion_is_outcome_independent_and_history_is_past_only():
    first = [
        event(1),
        event(2, owner=200, team=200, period=4, clock="PT00M10.00S"),
        event(
            3,
            owner=100,
            team=200,
            period=4,
            clock="PT00M09.00S",
            kind="foul",
            subtype="personal",
        ),
    ]
    second = [dict(e) for e in first]
    second[-1]["actionType"] = "2pt"
    a = sequence_features(add_recent_foul_columns(reconstruct(first, "g")))
    b = sequence_features(add_recent_foul_columns(reconstruct(second, "g")))
    assert a.iloc[-1].late_strategy_context == b.iloc[-1].late_strategy_context == 1
    cols = [c for c in a if "lag_" in c]
    pd.testing.assert_frame_equal(a[cols], b[cols])
    assert a.iloc[-1].F_t != b.iloc[-1].F_t


def test_clock_fractional_precision():
    assert clock_seconds("PT01M02.5S") == 62.5
    assert clock_seconds("PT00M00.001S") == 0.001


def test_admin_ownership_cannot_create_phantom_possessions():
    actions = [
        event(1),
        event(
            2, owner=200, team=200, kind="period", subtype="end", clock="PT00M00.00S"
        ),
        event(
            3, owner=100, team=200, kind="substitution", period=2, clock="PT12M00.00S"
        ),
        event(4, owner=200, team=200, period=2),
    ]
    result = reconstruct(actions, "g")
    assert len(result) == 2
    assert list(result.offense_team) == ["HOM", "AWY"]
    assert list(result.start_action_number) == [1, 4]
    assert result.iloc[-1].start_clock == 720


def test_reviewed_real_opening_sequence():
    from pathlib import Path

    actions = json.loads(
        (Path(__file__).parent / "fixtures/0022400001_opening.json").read_text()
    )
    table = add_recent_foul_columns(reconstruct(actions, "0022400001"))
    # Manually reviewed source events: offensive rebounds retain control; steal
    # sequences alternate; Brown's foul/Capela FTs remain one ATL possession.
    assert table.start_action_number.tolist() == [
        4,
        11,
        13,
        15,
        16,
        18,
        20,
        23,
        24,
        30,
        32,
        37,
        39,
        41,
    ]
    assert table.F_t.tolist() == [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert table.iloc[8].end_action_number == 29
    assert table.iloc[8].free_throw_attempts == 2
    assert table.iloc[10].defense_team_fouls_before == 1


def test_forecast_targets_censor_game_end_and_keep_team_direction():
    from forecast_foul_sequences import targets

    game = pd.DataFrame({"F_t": [0, 1, 0, 1, 0], "home_defense": [0, 0, 1, 1, 0]})
    assert targets(game, 3, "team").tolist() == [1, 1, 2, -1, -1]
    assert targets(game, 3, "time").tolist() == [2, 1, 2, -1, -1]


def test_technical_only_ownership_does_not_add_possession():
    a = [
        event(1),
        event(2, owner=200, team=200, kind="foul", subtype="technical"),
        event(3),
    ]
    d = reconstruct(a, "g")
    assert len(d) == 1
    assert d.administrative_groups_removed.iloc[0] == 1


def test_made_basket_retained_ball_exception_keeps_distinct_possessions():
    a = [
        event(1),
        event(2, owner=200, team=200, kind="foul", subtype="technical"),
        event(3),
    ]
    a[0]["shotResult"] = "Made"
    d = reconstruct(a, "g")
    assert len(d) == 2
    assert list(d.offense_team) == ["HOM", "HOM"]


def test_interval_oracle_and_vectorized_statistic():
    from validate_wmi_intervals import oracle, ratio

    f = np.array([0, 1, 0, 1, 1, 0, 0, 1, 0, 1], dtype=np.int8)
    d = add_recent_foul_columns(pd.DataFrame({"foul_called_this_possession": f}))
    assert np.isclose(ratio(f), calculate_wmi(d)["WMI"])
    assert abs(oracle(200, 0.16, 0.16) - 1) < 0.02
