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


def goaltending_sequence():
    return [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(
            327,
            clock="PT03M26S",
            shotResult="Made",
            qualifiers=["pointsinthepaint", "defensivegoaltending"],
        ),
        event(329, "violation", 200, 100, "defensive goaltending", "PT03M26S"),
        event(330, "3pt", 200, 200, clock="PT03M17S", shotResult="Made"),
        end(999),
    ]


@pytest.mark.parametrize(
    "qualifiers",
    [
        ["pointsinthepaint", "defensivegoaltending"],
        "pointsinthepaint, defensivegoaltending",
    ],
)
def test_corroborated_defensive_goaltending_companion_keeps_made_basket_boundary(
    qualifiers,
):
    actions = goaltending_sequence()
    actions[1]["qualifiers"] = qualifiers
    saved = json.dumps(actions)
    r = parse(actions)
    assert [p.event_action_numbers for p in r.possessions] == [
        (327, 329),
        (330, 999),
    ]
    assert r.possessions[0].boundary_reason == "made_field_goal"
    assert r.possessions[0].foul_indicator == 0
    assert r.possessions[0].audit_flags == ()
    assert [(i.code, i.action_number) for i in r.issues if i.action_number] == [
        ("corroborated_goaltending_companion", 329)
    ]
    assert not r.eligible
    assert r.audit_status == "blocked_pending_independent_audit"
    assert json.dumps(actions) == saved
    assert [e.source_row for e in r.events] == list(range(len(actions)))
    assert sorted(
        [n for p in r.possessions for n in p.event_action_numbers]
        + list(r.unassigned_action_numbers)
    ) == [0, 327, 329, 330, 999]


@pytest.mark.parametrize(
    "shot_change, companion_change",
    [
        ({"qualifiers": []}, {}),
        ({"qualifiers": None}, {}),
        ({"qualifiers": "notdefensivegoaltending"}, {}),
        ({"qualifiers": {"defensivegoaltending": True}}, {}),
        ({"qualifiers": ["offensivegoaltending"]}, {}),
        ({"teamId": 200}, {}),
        ({}, {"teamId": 100}),
        ({}, {"teamId": None}),
        ({}, {"possession": 200}),
        ({}, {"clock": "PT03M25S"}),
        ({}, {"period": 2}),
        ({}, {"subType": "offensive goaltending"}),
        ({}, {"subType": "defensive 3 seconds"}),
    ],
)
def test_uncorroborated_violation_does_not_pair_with_pending_basket(
    shot_change, companion_change
):
    actions = goaltending_sequence()
    actions[1].update(shot_change)
    actions[2].update(companion_change)
    if "period" in companion_change:
        for action in actions[3:]:
            action["period"] = 2
    r = parse(actions)
    assert r.possessions[0].event_action_numbers == (327,)
    assert any(i.code == "violation_requires_audit" for i in r.issues)
    assert not r.eligible


def test_repeated_goaltending_companion_is_not_blindly_merged():
    actions = goaltending_sequence()
    actions.insert(3, dict(actions[2], actionNumber=330, orderNumber=330))
    actions[4].update(actionNumber=331, orderNumber=331)
    r = parse(actions)
    assert [p.event_action_numbers for p in r.possessions] == [
        (327, 329),
        (330,),
        (331, 999),
    ]
    assert [
        i.action_number for i in r.issues if i.code == "violation_requires_audit"
    ] == [330]


def test_goaltending_companion_preserves_subsequent_and_one():
    actions = goaltending_sequence()
    actions[3:3] = [
        event(330, "foul", 200, 100, "shooting", "PT03M26S"),
        event(331, "freethrow", sub="1 of 1", clock="PT03M26S", shotResult="Made"),
    ]
    actions[5].update(actionNumber=332, orderNumber=332)
    r = parse(actions)
    assert r.possessions[0].event_action_numbers == (327, 329, 330, 331)
    assert r.possessions[0].boundary_reason == "final_made_free_throw"
    assert r.possessions[0].counted_foul_action_numbers == (330,)
    assert r.possessions[0].foul_indicator == 1
    assert not r.possessions[0].audit_flags


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


def test_delay_warning_is_administrative_even_with_conflicting_source_owner():
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, shotResult="Missed"),
        event(2, "violation", 200, 200, "delay-of-game", qualifiers="team"),
        event(3, "turnover"),
        end(),
    ]
    original = json.dumps(actions)
    r = parse(actions)
    assert r.events[2].classification == "administrative"
    assert r.possessions[0].event_action_numbers == (1, 2, 3, 99)
    assert r.possessions[0].foul_indicator == 0
    assert json.dumps(actions) == original
    assert {i.code for i in r.issues if i.blocking} == {"independent_audit_required"}


def test_delay_warning_cannot_establish_opening_control():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "violation", 200, 200, "delay-of-game", qualifiers=["team"]),
            event(2, "turnover"),
            end(),
        ]
    )
    assert r.unassigned_action_numbers == (0, 1)
    assert r.possessions[0].start_action_number == 2


@pytest.mark.parametrize(
    "team, terminal", [(100, "offensive_kicked_ball"), (200, "turnover")]
)
def test_kicked_ball_uses_explicit_actor_and_offense(team, terminal):
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, shotResult="Missed"),
            event(2, "violation", team, 100, "kicked ball"),
            *([] if team == 100 else [event(3, "turnover")]),
            event(4, "turnover", 200, 200, clock="PT10M59S"),
            end(),
        ]
    )
    assert r.possessions[0].boundary_reason == terminal
    assert r.possessions[0].foul_indicator == 0
    assert {i.code for i in r.issues if i.blocking} == {"independent_audit_required"}


def test_offensive_kick_and_exact_turnover_companion_are_one_loss():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "violation", sub="kicked ball"),
            event(2, "turnover", sub="offensive-kicked-ball"),
            event(3, "turnover", 200, 200, clock="PT10M59S"),
            end(),
        ]
    )
    assert r.possessions[0].event_action_numbers == (1, 2)
    assert r.possessions[0].boundary_reason == "offensive_kicked_ball"
    assert len(r.possessions) == 2


@pytest.mark.parametrize(
    "kind, sub, extra",
    [
        ("violation", "kicked ball", {"team": None}),
        ("violation", "lane", {}),
        ("violation", "double lane", {}),
        ("violation", "jumpball", {"team": None}),
        ("violation", "delay-of-game", {"qualifiers": "notteam"}),
    ],
)
def test_unsupported_violation_evidence_remains_unknown(kind, sub, extra):
    action = event(2, kind, sub=sub, **extra)
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, shotResult="Missed"),
            action,
            end(),
        ]
    )
    assert r.possessions[0].foul_indicator is None
    assert any(i.code == "violation_requires_audit" for i in r.issues)
    assert not r.eligible


@pytest.mark.parametrize("descriptor", ["clear-path", "transition take"])
def test_explicit_special_descriptor_preserves_retained_sequence_and_unknown(
    descriptor,
):
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, "foul", 200, 100, "personal", descriptor=descriptor),
        event(2, "freethrow", sub="1 of 1", shotResult="Made", descriptor=descriptor),
        event(3, "turnover", clock="PT10M59S"),
        event(4, "turnover", 200, 200, clock="PT10M58S"),
        end(),
    ]
    r = parse(actions)
    assert r.possessions[0].event_action_numbers == (1, 2, 3)
    assert r.possessions[0].foul_indicator is None
    assert r.possessions[0].counted_foul_action_numbers == (1,)
    assert "retained_ball_requires_audit" in r.possessions[0].audit_flags
    assert r.possessions[1].start_state.previous_foul_indicators == (None,)
    assert r.possessions[1].start_state.defense_counted_fouls == 0
    assert parse(actions[:4]).possessions[0].start_state == r.possessions[0].start_state
    assert sorted(
        [n for p in r.possessions for n in p.event_action_numbers]
        + list(r.unassigned_action_numbers)
    ) == [0, 1, 2, 3, 4, 99]
    assert not r.eligible


@pytest.mark.parametrize(
    "kind, sub",
    [
        ("instantreplay", "request"),
        ("turnover", "shot clock"),
        ("violation", "delay-of-game"),
    ],
)
def test_recorded_clock_rises_are_not_assumed_to_be_live_clock_repairs(kind, sub):
    actions = [
        event(1, "turnover", clock="PT01M00S"),
        event(2, kind, sub=sub, clock="PT01M01S", qualifiers="team"),
    ]
    with pytest.raises(ValueError, match="clock/period regression at action 2"):
        parse(actions)


def test_archive_away_descriptor_after_made_basket_does_not_prove_retained_entitlement():
    # 0022000018 actions 9/11/15/16: recorded early-period basket, off-ball
    # foul and one FT. Descriptor alone does not prove the formal special rule.
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(9, "3pt", shotResult="Made", clock="PT11M26S"),
            event(
                11,
                "foul",
                200,
                100,
                "personal",
                "PT11M26S",
                descriptor="away-from-play",
            ),
            event(
                15,
                "freethrow",
                sub="1 of 1",
                clock="PT11M26S",
                shotResult="Made",
                descriptor="away-from-play",
            ),
            event(16, "3pt", 200, 200, clock="PT11M14S", shotResult="Missed"),
            end(),
        ]
    )
    assert r.possessions[0].event_action_numbers == (9, 11, 15)
    assert r.possessions[0].boundary_reason == "final_made_free_throw"
    assert r.possessions[0].foul_indicator is None
    assert "special_descriptor_requires_audit" in r.possessions[0].audit_flags
    assert not any(i.code == "unexplained_control_transfer" for i in r.issues)


def test_retained_entitlement_does_not_leak_into_later_ordinary_foul_sequence():
    # 0022000045 actions 323..332: a clear-path entitlement is followed by
    # a distinct later-clock shooting foul, whose ordinary FT sequence ends.
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(
                323, "foul", 200, 100, "personal", "PT09M03S", descriptor="clear-path"
            ),
            event(326, "freethrow", sub="1 of 2", clock="PT09M03S", shotResult="Made"),
            event(327, "freethrow", sub="2 of 2", clock="PT09M03S", shotResult="Made"),
            event(328, "foul", 200, 100, "personal", "PT08M58S", descriptor="shooting"),
            event(330, "freethrow", sub="1 of 2", clock="PT08M58S", shotResult="Made"),
            event(331, "freethrow", sub="2 of 2", clock="PT08M58S", shotResult="Made"),
            event(332, "turnover", 200, 200, clock="PT08M39S"),
            end(999),
        ]
    )
    assert r.possessions[0].event_action_numbers == (323, 326, 327, 328, 330, 331)
    assert r.possessions[0].boundary_reason == "final_made_free_throw"
    assert r.possessions[0].counted_foul_action_numbers == (323, 328)
    assert r.possessions[0].foul_indicator is None
    assert not any(i.code == "unexplained_control_transfer" for i in r.issues)


def clock_restoration_sequence():
    return [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(337, "turnover", sub="traveling", clock="PT00M00S"),
        event(
            338,
            "instantreplay",
            None,
            200,
            "request",
            "PT00M00.2S",
            descriptor="support",
            value="Travel with time on the clock",
        ),
        event(339, "turnover", 200, 200, clock="PT00M00.2S"),
        end(999),
    ]


def test_explicit_supported_travel_replay_retains_recorded_clocks_and_audit_reason():
    actions = clock_restoration_sequence()
    original = json.dumps(actions)
    r = parse(actions)
    assert [e.clock for e in r.events[1:4]] == [0, 0.2, 0.2]
    assert r.possessions[1].start_state.reference_action_number == 338
    assert r.possessions[1].start_state.clock == 0.2
    assert "source_clock_correction_requires_audit" in r.possessions[0].audit_flags
    assert r.possessions[0].foul_indicator is None
    assert r.possessions[1].start_state.previous_foul_indicators == (None,)
    issue = next(
        i for i in r.issues if i.code == "source_clock_correction_requires_audit"
    )
    assert issue.action_number == 338 and "337" in issue.detail and issue.blocking
    assert json.dumps(actions) == original
    assert parse(actions[:3]).possessions[0].start_state == r.possessions[0].start_state
    assert not r.eligible


@pytest.mark.parametrize(
    "change",
    [
        {"descriptor": "overturned"},
        {"value": "Foul occurred prior to expiration of time"},
        {"value": "Travel with time on the clock?"},
        {"possession": 100},
        {"actionType": "memo"},
        {"subType": "unknown"},
    ],
)
def test_uncorroborated_clock_rise_is_not_repaired(change):
    actions = clock_restoration_sequence()
    actions[2].update(change)
    with pytest.raises(ValueError, match="clock/period regression"):
        parse(actions)


def source_neighborhood(game_id, action_number):
    """Unmodified rows from a SHA256-verified archive; refs live beside evidence."""
    evidence = json.loads(
        Path(
            "research/parser_followthrough_2026_11_02/semantic_changes.json"
        ).read_text()
    )
    case = next(
        c
        for c in evidence["source_neighborhoods"]
        if c["game_id"] == game_id and c["action_number"] == action_number
    )
    actions = case["events"]
    return reconstruct(
        actions,
        game_id,
        case["home_team_id"],
        case["away_team_id"],
        case["source_sha256"],
    )


def test_source_recovered_jump_actor_establishes_control_despite_stale_owner():
    r = source_neighborhood("0022000003", 571)
    group = next(p for p in r.possessions if 566 in p.event_action_numbers)
    assert group.offense_team_id == 1610612749
    assert 571 in group.event_action_numbers
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 571
        for i in r.issues
    )
    assert (
        next(e for e in r.events if e.action_number == 566).possession_team_id
        == 1610612738
    )


def test_source_foul_recorded_after_final_free_throw_keeps_entitlement_boundary():
    r = source_neighborhood("0022000013", 506)
    group = next(p for p in r.possessions if 505 in p.event_action_numbers)
    assert 500 in group.event_action_numbers
    assert group.counted_foul_action_numbers == (500,)
    assert group.boundary_reason == "final_made_free_throw"
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 506
        for i in r.issues
    )


def test_source_goaltending_after_final_free_throw_shares_awarded_point():
    r = source_neighborhood("0022000114", 363)
    group = next(p for p in r.possessions if 361 in p.event_action_numbers)
    assert 362 in group.event_action_numbers
    assert group.boundary_reason == "final_made_free_throw"
    assert not any(
        i.code in {"violation_requires_audit", "unexplained_control_transfer"}
        and i.action_number in {362, 363}
        for i in r.issues
    )


def test_source_deadball_team_rebound_does_not_interrupt_free_throws():
    r = source_neighborhood("0022400921", 60)
    group = next(p for p in r.possessions if 60 in p.event_action_numbers)
    assert (
        63 in r.unassigned_action_numbers
    )  # This neighborhood begins with dead-ball rows.
    assert 64 in group.event_action_numbers
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 60
        for i in r.issues
    )
    assert (
        next(e for e in r.events if e.action_number == 63).classification
        == "administrative"
    )


def test_source_flagrant_descriptor_keeps_retained_ball_after_final_throw():
    r = source_neighborhood("0022400875", 550)
    group = next(p for p in r.possessions if 544 in p.event_action_numbers)
    assert {549, 550, 551}.issubset(group.event_action_numbers)
    assert "retained_ball_requires_audit" in group.audit_flags
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 550
        for i in r.issues
    )


def test_personal_double_descriptor_is_not_an_ordinary_defensive_foul():
    evidence = json.loads(
        Path(
            "research/parser_followthrough_2026_11_02/semantic_changes.json"
        ).read_text()
    )
    case = next(
        c["example"]
        for c in evidence["label_inventory"]
        if c["kind"] == "foul"
        and c["subtype"] == "personal"
        and c["descriptor"] == "double"
    )
    r = reconstruct(
        case["events"], case["game_id"], case["home_team_id"], case["away_team_id"]
    )
    assert not any(p.counted_foul_action_numbers for p in r.possessions)
    assert {
        i.action_number for i in r.issues if i.code == "double_foul_requires_audit"
    } == {437, 439}


def test_source_defensive_lane_during_recorded_entitlement_does_not_transfer_control():
    r = source_neighborhood("0022000002", 608)
    assert any(
        i.code == "classified_defensive_lane"
        and i.action_number == 608
        and not i.blocking
        for i in r.issues
    )
    assert not any(
        i.code == "violation_requires_audit" and i.action_number == 608
        for i in r.issues
    )


def test_source_jump_violation_by_offense_ends_that_control():
    r = source_neighborhood("0022000248", 7)
    group = next(p for p in r.possessions if 7 in p.event_action_numbers)
    assert group.boundary_reason == "offensive_jump_violation"
    assert 8 not in group.event_action_numbers
    assert any(
        i.code == "classified_jump_violation"
        and i.action_number == 7
        and not i.blocking
        for i in r.issues
    )
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 8
        for i in r.issues
    )


def test_source_jump_violation_by_defense_retains_explicit_offense():
    r = source_neighborhood("0022000033", 156)
    group = next(p for p in r.possessions if 156 in p.event_action_numbers)
    assert 158 in group.event_action_numbers
    assert any(
        i.code == "classified_jump_violation"
        and i.action_number == 156
        and not i.blocking
        for i in r.issues
    )


def test_source_memo_cannot_transfer_control_or_silently_supply_negative_target():
    r = source_neighborhood("0022000932", 599)
    group = next(p for p in r.possessions if 595 in p.event_action_numbers)
    assert {596, 599}.issubset(group.event_action_numbers)
    assert group.foul_indicator is None
    assert "source_note_requires_audit" in group.audit_flags
    assert (
        next(e for e in r.events if e.action_number == 596).classification
        == "administrative"
    )
    assert not any(
        i.code == "unsupported_label" and i.action_number == 596 for i in r.issues
    )


@pytest.mark.parametrize(
    "change",
    [
        {"clock": "PT10M59S"},
        {"qualifiers": "3freethrow"},
        {"qualifiers": "not2freethrow"},
        {"descriptor": "double"},
        {"descriptor": "flagrant-type-1"},
        {"teamId": 100},
    ],
)
def test_late_foul_companion_requires_exact_clock_actor_and_entitlement(change):
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, "freethrow", sub="1 of 2", shotResult="Made"),
        event(2, "freethrow", sub="2 of 2", shotResult="Made"),
        event(3, "foul", 200, 100, "personal", qualifiers="2freethrow"),
        end(),
    ]
    actions[3].update(change)
    r = parse(actions)
    assert r.possessions[0].event_action_numbers == (1, 2)
    assert 3 in r.possessions[1].event_action_numbers


def test_duplicate_foul_after_completed_entitlement_cannot_pair_twice():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "foul", 200, 100, "personal", qualifiers="2freethrow"),
            event(2, "freethrow", sub="2 of 2", shotResult="Made"),
            event(3, "foul", 200, 100, "personal", qualifiers="2freethrow"),
            end(),
        ]
    )
    assert r.possessions[0].event_action_numbers == (1, 2)
    assert r.possessions[1].counted_foul_action_numbers == (3,)


@pytest.mark.parametrize(
    "qualifiers", ["notdeadball, team", "deadball", ["deadball"], []]
)
def test_rebound_is_not_administrative_without_both_exact_team_deadball_tokens(
    qualifiers,
):
    r = parse(
        [
            event(1, shotResult="Missed"),
            event(2, "rebound", 200, 200, "defensive", qualifiers=qualifiers),
            end(),
        ]
    )
    assert r.events[1].classification == "control"
    assert len(r.possessions) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"teamId": 100},
        {"clock": "PT10M59S"},
        {"possession": 200},
    ],
)
def test_ft_goaltending_pair_requires_same_clock_offense_and_defensive_actor(change):
    actions = [
        event(1, "freethrow", sub="2 of 2", shotResult="Made"),
        event(2, "violation", 200, 100, "defensive goaltending"),
        end(),
    ]
    actions[1].update(change)
    r = parse(actions)
    assert any(
        i.code == "violation_requires_audit" and i.action_number == 2 for i in r.issues
    )


def test_defensive_lane_without_recorded_entitlement_stays_unknown():
    r = parse(
        [event(1, shotResult="Missed"), event(2, "violation", 200, 100, "lane"), end()]
    )
    assert any(i.code == "violation_requires_audit" for i in r.issues)


def test_goaltending_on_nonfinal_made_throw_keeps_remaining_throw_in_control():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "freethrow", sub="1 of 2", shotResult="Made"),
            event(2, "violation", 200, 100, "defensive goaltending"),
            event(3, "freethrow", sub="2 of 2", shotResult="Made"),
            event(4, "turnover", 200, 200, clock="PT10M50S"),
            end(),
        ]
    )
    assert r.possessions[0].event_action_numbers == (1, 2, 3)
    assert r.possessions[0].foul_indicator == 0
    assert r.possessions[0].boundary_reason == "final_made_free_throw"


def test_source_zero_clock_foul_review_preserves_clocks_and_blocks_audit():
    r = source_neighborhood("0022100865", 178)
    assert [
        (e.action_number, e.clock)
        for e in r.events
        if e.action_number in {176, 177, 178, 179}
    ] == [
        (176, 0.0),
        (177, 0.0),
        (178, 0.6),
        (179, 0.6),
    ]
    assert any(
        i.code == "source_clock_correction_requires_audit"
        and i.action_number == 178
        and i.blocking
        for i in r.issues
    )
    assert not r.eligible


@pytest.mark.parametrize(
    "game_id, action_number", [("0022100206", 159), ("0022101229", 562)]
)
def test_source_reused_foul_review_text_does_not_admit_other_clock_rises(
    game_id, action_number
):
    with pytest.raises(
        ValueError, match=f"clock/period regression at action {action_number}"
    ):
        source_neighborhood(game_id, action_number)


@pytest.mark.parametrize(
    "game_id, action_number",
    [
        ("0022000003", 571),
        ("0022000013", 506),
        ("0022000114", 363),
        ("0022400921", 60),
        ("0022400875", 550),
        ("0022000002", 608),
        ("0022000248", 7),
        ("0022000033", 156),
        ("0022000932", 599),
    ],
)
def test_source_regressions_keep_raw_accounting_and_past_only_start_states(
    game_id, action_number
):
    evidence = json.loads(
        Path(
            "research/parser_followthrough_2026_11_02/semantic_changes.json"
        ).read_text()
    )
    case = next(
        c
        for c in evidence["source_neighborhoods"]
        if c["game_id"] == game_id and c["action_number"] == action_number
    )
    actions = case["events"]
    saved = json.dumps(actions)
    r = source_neighborhood(game_id, action_number)
    assert json.dumps(actions) == saved
    assert [json.loads(e.raw_json) for e in r.events] == actions
    accounted = [n for p in r.possessions for n in p.event_action_numbers]
    accounted += list(r.unassigned_action_numbers)
    assert sorted(accounted) == sorted(int(a["actionNumber"]) for a in actions)
    prefix = reconstruct(
        actions[:-1], game_id, case["home_team_id"], case["away_team_id"]
    )
    starts = {p.start_action_number: p.start_state for p in r.possessions}
    assert all(
        starts[p.start_action_number] == p.start_state for p in prefix.possessions
    )
    assert not r.eligible


def test_missed_final_ft_defensive_lane_without_replacement_remains_unknown():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "freethrow", sub="2 of 2", shotResult="Missed"),
            event(2, "violation", 200, 100, "lane"),
            event(3, "rebound", 200, 200, "defensive", clock="PT10M59S"),
            end(),
        ]
    )
    assert r.possessions[0].foul_indicator is None
    assert any(
        i.code == "violation_requires_audit" and i.action_number == 2 for i in r.issues
    )


def test_malformed_ft_cannot_corroborate_goaltending_companion():
    r = parse(
        [
            event(1, "freethrow", sub="3 of 1", shotResult="Made"),
            event(2, "violation", 200, 100, "defensive goaltending"),
            end(),
        ]
    )
    assert any(
        i.code == "violation_requires_audit" and i.action_number == 2 for i in r.issues
    )


def test_ft_goaltending_companion_cannot_skip_intervening_technical_throw():
    r = parse(
        [
            event(0, "period", None, None, "start", "PT12M00S"),
            event(1, "freethrow", sub="2 of 2", shotResult="Made"),
            event(
                2,
                "freethrow",
                200,
                100,
                "1 of 1",
                shotResult="Made",
                descriptor="technical",
            ),
            event(3, "violation", 200, 100, "defensive goaltending"),
            end(),
        ]
    )
    assert any(
        i.code == "violation_requires_audit" and i.action_number == 3 for i in r.issues
    )


def test_source_ordinary_final_miss_deadball_rebound_awards_defensive_control():
    r = source_neighborhood("0022300470", 653)
    group = next(p for p in r.possessions if 653 in p.event_action_numbers)
    assert group.offense_team_id == 1610612761
    assert 654 in group.event_action_numbers
    assert (
        next(e for e in r.events if e.action_number == 653).classification == "control"
    )
    assert not any(
        i.code == "unexplained_control_transfer" and i.action_number == 654
        for i in r.issues
    )


@pytest.mark.parametrize(
    "game_id, action_number, jump, following",
    [
        ("0022000003", 301, 298, 302),
        ("0022000005", 114, 111, 115),
    ],
)
def test_source_lost_jumper_turnover_is_one_jump_loss_companion(
    game_id, action_number, jump, following
):
    r = source_neighborhood(game_id, action_number)
    group = next(p for p in r.possessions if jump in p.event_action_numbers)
    assert {action_number, following}.issubset(group.event_action_numbers)
    assert any(
        i.code == "paired_jump_loss_companion" and i.action_number == action_number
        for i in r.issues
    )
    assert not any(
        i.code in {"unexplained_control_transfer", "event_owner_conflict"}
        and i.action_number in {action_number, following}
        for i in r.issues
    )
    if game_id == "0022000003":
        assert "jump_loss_timing_requires_audit" in group.audit_flags


@pytest.mark.parametrize(
    "mutation", ["actor", "label", "intervening", "duplicate", "no_jump"]
)
def test_jump_loss_companion_requires_exact_prior_jump_actor_and_one_loss(mutation):
    jump = event(
        2,
        "jumpball",
        200,
        100,
        "recovered",
        descriptor="heldball",
        personId="22",
        jumpBallRecoverdPersonId="22",
        jumpBallLostPersonId="11",
    )
    loss = event(3, "turnover", sub="lost ball", personId="11")
    if mutation == "actor":
        loss["personId"] = "33"
    if mutation == "label":
        loss["subType"] = "traveling"
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, shotResult="Missed"),
    ]
    if mutation != "no_jump":
        actions.append(jump)
    if mutation == "intervening":
        actions.append(event(21, "2pt", 200, 200, shotResult="Missed"))
        actions[-1]["orderNumber"] = 3
        loss["orderNumber"] = 4
    actions.append(loss)
    if mutation == "duplicate":
        actions.append(event(4, "turnover", sub="lost ball", personId="11"))
    actions.append(end())
    r = parse(actions)
    paired = [
        i.action_number for i in r.issues if i.code == "paired_jump_loss_companion"
    ]
    assert paired == ([3] if mutation == "duplicate" else [])


def test_memo_metadata_cannot_supply_next_before_state_clock_score_or_reference():
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, clock="PT11M00S", shotResult="Made"),
        event(2, "memo", None, 200, clock="PT10M30S", value="career high"),
        event(3, "turnover", 200, 200, clock="PT10M20S"),
        end(),
    ]
    actions[1]["scoreHome"] = 2
    actions[2]["scoreHome"] = 99
    r = parse(actions)
    before = r.possessions[1].start_state
    assert before.reference_action_number == 1
    assert before.clock == 660
    assert before.home_score == 2
    assert before.defense_counted_fouls is None
    assert "source_note_requires_audit" in r.possessions[0].audit_flags
    assert json.loads(r.events[2].raw_json)["scoreHome"] == 99
    assert r.events[2].clock == 630


def test_memo_clock_does_not_mask_rise_between_nonmemo_events():
    actions = [
        event(1, "turnover", clock="PT01M00S"),
        event(2, "memo", None, None, clock="PT02M00S", value="career high"),
        event(3, "turnover", 200, 200, clock="PT01M01S"),
    ]
    with pytest.raises(ValueError, match="clock/period regression at action 3"):
        parse(actions)


def test_memo_period_cannot_end_live_group_or_establish_new_period():
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, shotResult="Missed"),
        event(2, "memo", None, 200, value="career high"),
        event(3, "turnover", clock="PT10M59S"),
        end(),
    ]
    actions[2]["period"] = 2
    r = parse(actions)
    assert len(r.possessions) == 1
    assert r.possessions[0].event_action_numbers == (1, 2, 3, 99)
    assert r.possessions[0].period == 1
    assert r.events[2].period == 2
    assert not any(i.code == "missing_period_end" for i in r.issues)
    assert r.possessions[0].foul_indicator is None


def test_source_memo_does_not_supply_next_possession_reference_clock():
    r = source_neighborhood("0022000035", 558)
    group = next(p for p in r.possessions if p.start_action_number == 559)
    assert group.start_state.reference_action_number == 556
    assert group.start_state.clock == 702
    assert next(e for e in r.events if e.action_number == 558).clock == 694
    assert any(
        i.code == "source_note_requires_audit" and i.action_number == 558 and i.blocking
        for i in r.issues
    )
    assert group.start_state.defense_counted_fouls is None
    assert not r.eligible


def test_source_postgame_memo_preserves_raw_time_without_clock_restoration():
    r = source_neighborhood("0022000254", 661)
    note = next(e for e in r.events if e.action_number == 661)
    assert note.clock == 71
    assert r.events[-1].action_number == 661
    assert any(
        i.code == "source_note_requires_audit" and i.action_number == 661 and i.blocking
        for i in r.issues
    )
    assert not any(i.code == "source_clock_correction_requires_audit" for i in r.issues)
    assert 661 in r.unassigned_action_numbers
    assert not r.eligible


@pytest.mark.parametrize(
    "game_id, action_number", [("0022100750", 456), ("0022100954", 667)]
)
def test_source_memo_exclusion_keeps_actual_nonmemo_clock_rises_quarantined(
    game_id, action_number
):
    with pytest.raises(
        ValueError, match=f"clock/period regression at action {action_number}"
    ):
        source_neighborhood(game_id, action_number)


def test_memo_exclusion_preserves_duplicate_source_order_validation():
    actions = [event(1, "turnover"), event(2, "memo", None, None)]
    actions[1]["orderNumber"] = 1
    with pytest.raises(ValueError, match="ambiguous duplicate orderNumber"):
        parse(actions)


def test_out_of_band_memo_still_requires_structurally_valid_clock():
    with pytest.raises(ValueError, match="clock outside period"):
        parse([event(1, "memo", None, None, clock="PT13M00S")])


def test_memo_cannot_supply_opening_control_or_initial_score():
    actions = [event(1, "memo", None, 100), event(2, "turnover", 200, 200), end()]
    actions[0]["scoreHome"] = 99
    r = parse(actions)
    assert r.unassigned_action_numbers == (1,)
    group = r.possessions[0]
    assert group.start_action_number == 2
    assert group.offense_team_id == 200
    assert group.start_state.reference_action_number is None
    assert group.start_state.home_score is None
    assert group.start_state.clock == 720
    assert not r.eligible


def test_mismatched_period_note_keeps_active_and_raw_period_foul_counts_unknown():
    actions = [
        event(0, "period", None, None, "start", "PT12M00S"),
        event(1, shotResult="Missed"),
        event(2, "memo", None, None, value="officiating note"),
        event(3, "turnover"),
        event(4, "turnover", 200, 200, clock="PT10M59S"),
        end(5),
        event(6, "period", None, None, "start", "PT12M00S"),
        event(7, "turnover", 200, 200),
        end(8),
    ]
    actions[2]["period"] = 2
    for action in actions[6:]:
        action["period"] = 2
    r = parse(actions)
    starts = {p.start_action_number: p.start_state for p in r.possessions}
    assert starts[4].defense_counted_fouls is None
    assert starts[7].defense_counted_fouls is None
    assert not any(i.code == "missing_period_end" for i in r.issues)
