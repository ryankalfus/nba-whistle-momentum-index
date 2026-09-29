"""Independent guards for the separately stored H1-H18 research run."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_all_wmi_hypotheses import (
    clock_seconds,
    elapsed_seconds,
    penalty_next_foul,
    sequence_columns,
    component_stats,
    parse_game,
    add_research_outcomes,
    probability_metrics,
)


@pytest.mark.parametrize(
    "period,remaining,expected",
    [(1, 720, 0), (4, 0, 2880), (5, 300, 2880), (5, 0, 3180), (6, 300, 3180)],
)
def test_elapsed_does_not_use_final_overtime_length(period, remaining, expected):
    assert elapsed_seconds(period, remaining) == expected


def test_clock_parser_keeps_fractional_seconds():
    assert clock_seconds("PT01M02.50S") == 62.5
    with pytest.raises(ValueError):
        clock_seconds("bad")


@pytest.mark.parametrize(
    "args,expected",
    [
        ((1, 300, 3, 0), 0),
        ((1, 300, 4, 0), 1),
        ((5, 240, 3, 0), 1),
        ((5, 240, 2, 0), 0),
        ((4, 119, 1, 1), 1),
        ((4, 119, 0, 0), 0),
        ((4, 121, 1, 1), 0),
    ],
)
def test_bonus_before_next_foul(args, expected):
    assert penalty_next_foul(*args) == expected


def test_global_windows_and_future_safe_live_history():
    original = pd.DataFrame({"F_t": [1, 0, 1, 0, 0, 1, 0, 1, 1]})
    a = sequence_columns(original)
    assert list(a.L2[:5]) == [0, 1, 1, 1, 1]
    assert list(a.N2[:5]) == [1, 1, 0, 1, 1]
    assert (a.live_log_wmi[:3] == 0).all()
    # Changing the current and all future outcomes cannot affect current
    # past-only features, including a cumulative completed-window WMI.
    for cutoff in range(len(a)):
        changed = original.copy()
        changed.loc[cutoff:, "F_t"] = 1 - changed.loc[cutoff:, "F_t"]
        b = sequence_columns(changed)
        for col in ["L2", "recent_count", "live_log_wmi"]:
            assert a.loc[cutoff, col] == b.loc[cutoff, col]


def test_exact_decomposition_identity():
    frame = sequence_columns(
        pd.DataFrame({"game_id": ["a"] * 10, "F_t": [1, 1, 0, 0, 0, 1, 0, 1, 0, 1]})
    )
    row = component_stats(frame).iloc[0]
    assert row.WMI == pytest.approx(row.immediate * row.continuation)


def event(i, owner, team, **kwargs):
    row = dict(
        gameId=22400001,
        actionNumber=i,
        orderNumber=i,
        clock=f"PT11M{60 - i * 5:02d}.00S",
        period=1,
        possession=owner,
        teamId=team,
        teamTricode="HOM" if team == 100 else "AWY",
        actionType="turnover",
        subType="",
        descriptor="",
        qualifiers="",
        description="",
        scoreHome=0,
        scoreAway=0,
        personId=team + 1,
        foulPersonalTotal=np.nan,
        foulDrawnPersonId=np.nan,
        isFieldGoal=0,
        shotDistance=np.nan,
    )
    row.update(kwargs)
    return row


def test_parser_period_boundary_start_state_and_exclusions():
    rows = [
        event(1, 100, 200, actionType="foul", subType="personal", foulPersonalTotal=1),
        event(
            2, 100, 100, actionType="2pt", isFieldGoal=1, shotDistance=2, scoreHome=2
        ),
        event(3, 200, 100, actionType="foul", subType="technical", scoreHome=2),
        event(4, 200, 200, actionType="foul", subType="offensive", scoreHome=2),
        event(5, 100, 100, scoreHome=2),
        event(6, 100, 100, period=2, clock="PT12M00.00S", scoreHome=2),
    ]
    table, events, meta = parse_game(
        pd.DataFrame(rows),
        2024,
        0,
        {"home_team_abbr": "HOM", "game_date": "2024-10-22"},
    )
    assert list(table.F_t) == [1, 0, 0, 0]
    assert list(table.period) == [1, 1, 1, 2]
    assert table.iloc[0].score_diff == 0
    assert table.iloc[0].team_pf == 0
    assert table.iloc[0].own_points == 2
    assert table.iloc[0].prior_rim_attempts == 0
    assert table.iloc[1].prior_rim_attempts == 1
    assert table.iloc[-1].start_elapsed == 720
    assert meta["period_splits"] == 1
    assert events.counted_def_foul.sum() == 1


def test_future_windows_exclude_current_and_censor_game_end():
    frame = sequence_columns(
        pd.DataFrame({"game_id": ["a"] * 7, "F_t": [1, 0, 0, 0, 0, 0, 0]})
    )
    for col, value in {
        "defense": "AWY",
        "pos": np.arange(7),
        "home_points": np.arange(7),
        "away_points": 0,
        "home_offense": 1,
        "fta": 0,
        "turnovers": 0,
        "rim_attempts": 0,
        "reg_remaining": 700,
        "margin": 2,
        "end_elapsed": np.arange(7) * 10,
    }.items():
        frame[col] = value
    out = add_research_outcomes(frame)
    assert out.iloc[0].future_net5 == 15
    assert out.iloc[0].future_clock_seconds5 == 50
    assert out.future_net5.tail(5).isna().all()


def test_average_precision_handles_ties():
    metrics = probability_metrics(np.array([0, 1, 0, 1]), np.array([0.5] * 4))
    assert metrics["roc_auc"] == 0.5
    assert metrics["average_precision"] == 0.5
    assert metrics["brier"] == 0.25
