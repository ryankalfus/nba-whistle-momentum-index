from dataclasses import FrozenInstanceError, asdict
import json
from pathlib import Path

import pytest

from whistle_research.possessions import reconstruct


def event(n, kind="2pt", team=100, owner=100, sub="", clock="PT11M00S", **kw):
    return dict(
        actionNumber=n,
        orderNumber=n,
        actionType=kind,
        subType=sub,
        teamId=team,
        possession=owner,
        period=1,
        clock=clock,
        scoreHome=0,
        scoreAway=0,
        **kw,
    )


def parse(actions):
    return reconstruct(actions, "g", 100, 200)


def end(n=99):
    return event(n, "period", None, None, "end", "PT00M00S")


def test_offensive_rebound_continues_defensive_rebound_starts_new_control():
    actions = [
        event(1, shotResult="Missed"),
        event(2, "rebound", sub="offensive"),
        event(3, shotResult="Missed"),
        event(4, "rebound", 200, 200, "defensive"),
        event(5, "turnover", 200, 200),
        end(),
    ]
    r = parse(actions)
    assert [p.event_action_numbers for p in r.possessions] == [(1, 2, 3), (4, 5, 99)]
    assert r.possessions[0].boundary_reason == "defensive_rebound"
    assert r.possessions[1].offense_team_id == 200


def test_made_basket_and_one_and_terminal_free_throw():
    r = parse(
        [
            event(1, shotResult="Made"),
            event(2, "foul", 200, 100, "personal"),
            event(3, "freethrow", sub="1 of 1", shotResult="Made"),
            event(4, "turnover", 200, 200),
            end(),
        ]
    )
    assert r.possessions[0].event_action_numbers == (1, 2, 3)
    assert r.possessions[0].boundary_reason == "final_made_free_throw"
    assert r.possessions[0].counted_foul_action_numbers == (2,)


def test_admin_technical_does_not_switch_ownership_and_is_preserved():
    r = parse(
        [
            event(1, shotResult="Missed"),
            event(2, "foul", 100, 200, "technical"),
            event(
                3,
                "freethrow",
                200,
                200,
                "1 of 1",
                shotResult="Made",
                description="Technical Free Throw",
            ),
            event(4, "rebound", sub="offensive"),
            end(),
        ]
    )
    assert len(r.possessions) == 1
    assert r.possessions[0].event_action_numbers == (1, 2, 3, 4, 99)
    assert r.possessions[0].counted_foul_action_numbers == ()
    assert [e.classification for e in r.events[1:3]] == ["administrative"] * 2


def test_offensive_foul_and_paired_turnover_are_one_possession_loss():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "foul", sub="offensive"),
            event(2, "turnover", sub="offensive foul"),
            event(3, "turnover", 200, 200, clock="PT10M59S"),
            end(),
        ]
    )
    assert [p.event_action_numbers for p in r.possessions] == [(1, 2), (3, 99)]
    assert r.possessions[0].boundary_reason == "offensive_foul"
    assert r.possessions[0].counted_foul_action_numbers == ()
    assert r.possessions[0].foul_indicator == 0


@pytest.mark.parametrize(
    "sub, clock", [("bad pass", "PT11M00S"), ("offensive foul", "PT10M59S")]
)
def test_distinct_same_team_terminal_event_is_not_blindly_merged(sub, clock):
    r = parse(
        [
            event(1, "foul", sub="offensive"),
            event(2, "turnover", sub=sub, clock=clock),
            end(),
        ]
    )
    assert len(r.possessions) == 2
    assert r.possessions[0].event_action_numbers == (1,)


def test_retained_ball_free_throws_quarantined_and_do_not_end_control():
    r = parse(
        [
            event(1, "foul", 200, 100, "clear path"),
            event(2, "freethrow", sub="1 of 2", shotResult="Made"),
            event(3, "freethrow", sub="2 of 2", shotResult="Made"),
            event(4, "turnover"),
            end(),
        ]
    )
    assert len(r.possessions) == 1
    assert r.possessions[0].foul_indicator is None
    assert "retained_ball_requires_audit" in r.possessions[0].audit_flags


def test_missed_terminal_ft_requires_rebound_not_automatic_transfer():
    r = parse(
        [
            event(1, "foul", 200, 100, "personal"),
            event(2, "freethrow", sub="1 of 1", shotResult="Missed"),
            event(3, "rebound", sub="offensive"),
            event(4, "turnover"),
            end(),
        ]
    )
    assert len(r.possessions) == 1
    assert r.possessions[0].counted_foul_action_numbers == (1,)


def test_jump_control_period_boundary_and_membership_accounting():
    actions = [
        event(1, "jumpball", sub="recovered"),
        event(2, "jumpball", 200, 200, "recovered"),
        end(3),
        dict(event(4, "turnover", 200, 200), period=2),
        dict(end(5), period=2),
    ]
    r = parse(actions)
    assert [p.offense_team_id for p in r.possessions] == [100, 200, 200]
    assert [p.boundary_reason for p in r.possessions] == [
        "jump_control",
        "period_end",
        "period_end",
    ]
    assigned = [n for p in r.possessions for n in p.event_action_numbers]
    assert sorted(assigned + list(r.unassigned_action_numbers)) == [1, 2, 3, 4, 5]


def test_future_suffix_does_not_change_existing_before_event_features():
    actions = [
        event(1, "foul", 200, 100, "personal"),
        event(2, "turnover"),
        event(3, "turnover", 200, 200),
    ]
    a = parse(actions)
    suffix = [
        dict(
            event(4, "turnover", clock="PT04M00S"), period=5, scoreHome=99, scoreAway=98
        )
    ]
    b = parse(actions + suffix)
    assert [p.start_state for p in a.possessions] == [
        p.start_state for p in b.possessions[:2]
    ]
    assert a.possessions[0].start_state.defense_counted_fouls is None
    assert b.possessions[-1].start_state.clock == 300
    assert a.possessions[0].start_state.home_score is None


@pytest.mark.parametrize(
    "change",
    [
        dict(actionNumber=1),
        dict(orderNumber=1),
        dict(clock="PT11M01S"),
        dict(clock="bad"),
        dict(teamId=999),
        dict(possession=999),
        dict(period=0),
    ],
)
def test_invalid_structure_fails_closed(change):
    with pytest.raises(ValueError):
        parse([event(1), dict(event(2), **change)])


def test_unknown_foul_does_not_become_zero_and_raw_events_immutable():
    actions = [event(1, "foul", 200, 100, "new label"), end()]
    saved = json.dumps(actions)
    r = parse(actions)
    assert r.possessions[0].foul_indicator is None
    assert any(i.code == "unsupported_label" for i in r.issues)
    assert json.dumps(actions) == saved
    assert json.loads(r.events[0].raw_json) == actions[0]
    with pytest.raises(FrozenInstanceError):
        r.events[0].kind = "other"
    json.dumps(asdict(r))


def test_partial_fixture_and_declared_hash_never_release_eligible():
    path = Path(__file__).parents[1] / "fixtures" / "0022400001_opening.json"
    actions = json.loads(path.read_text())
    r = reconstruct(actions, "0022400001", 1610612738, 1610612737, "a" * 64)
    assert r.provenance_status == "declared_unverified"
    assert not r.eligible
    assert r.parser_version != "period_start_v2"
    assert not r.possessions[-1].complete
    assert r.possessions[-1].foul_indicator is None
    assert len(r.events) == len(actions)
    with pytest.raises(ValueError):
        reconstruct(actions, "g", 100, 200, "nope")


def test_unknown_foul_propagates_missing_count_to_later_before_state():
    start = event(0, "period", None, None, "start", "PT12M00S")
    r = parse(
        [
            start,
            event(1, "foul", 200, 100, "new label"),
            event(2, "turnover"),
            event(3, "turnover", 200, 200),
            event(4, "turnover"),
            end(),
        ]
    )
    assert r.possessions[0].start_state.defense_counted_fouls == 0
    assert r.possessions[2].start_state.defense_counted_fouls is None
    assert r.possessions[1].start_state.previous_foul_indicators == (None,)


def test_explicit_game_metadata_conflict_rejected():
    with pytest.raises(ValueError, match="gameId"):
        parse([event(1, gameId="another-game")])


def test_source_order_sort_preserves_original_row_identity():
    first = event(1, "turnover")
    second = event(2, "turnover", 200, 200)
    r = parse([second, first, end()])
    assert [e.action_number for e in r.events] == [1, 2, 99]
    assert [e.source_row for e in r.events] == [1, 0, 2]
    assert r.possessions[0].source_rows == (1,)
    assert r.possessions[1].source_rows == (0, 2)


def test_no_ownership_and_unknown_shot_results_quarantine_instead_of_guess():
    r = parse(
        [
            event(1, "turnover"),
            event(2, "foul", 200, None, "personal"),
            event(3, "2pt", 200, 200),
            end(),
        ]
    )
    assert {i.code for i in r.issues} >= {"unknown_ownership", "unknown_shot_result"}
    assert all(p.foul_indicator is None for p in r.possessions)
    assert sorted(n for p in r.possessions for n in p.event_action_numbers) == [
        1,
        2,
        3,
        99,
    ]


def test_actor_defense_conflict_propagates_unknown_count():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "foul", 100, 100, "personal"),
            event(2, "turnover"),
            event(3, "turnover", 200, 200),
            event(4, "turnover"),
            end(),
        ]
    )
    assert r.possessions[0].foul_indicator is None
    assert r.possessions[2].start_state.defense_counted_fouls is None
    assert r.possessions[1].start_state.previous_foul_indicators == (None,)


def test_rebound_owner_conflict_quarantines_both_sides_and_later_history():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, shotResult="Missed"),
            event(2, "rebound", 200, 100, "defensive"),
            event(3, "turnover", 200, 200),
            event(4, "turnover"),
            end(),
        ]
    )
    assert [p.event_action_numbers for p in r.possessions] == [(1,), (2, 3), (4, 99)]
    for p in r.possessions[:2]:
        assert p.foul_indicator is None
        assert "rebound_ownership_conflict" in p.audit_flags
    assert r.possessions[2].start_state.previous_foul_indicators == (None, None)
    assert r.possessions[2].start_state.defense_counted_fouls is None
