"""Team-foul and penalty-state contracts (NBA Rule 12 B.V); software behavior, not live bonus truth."""

import json
from types import SimpleNamespace

import pytest

from test_possessions import end, event, parse
from whistle_research import possessions, team_fouls


@pytest.mark.parametrize("total,late,clock,period,expected", [
    (3, 0, 600.0, 1, 0), (4, 0, 600.0, 1, 1), (9, 0, 600.0, 4, 1),
    (2, 0, 100.0, 2, 0), (2, 1, 100.0, 2, 1), (3, 1, 121.0, 3, 0), (1, 1, 120.0, 4, 1),
    (2, 0, 200.0, 5, 0), (3, 0, 200.0, 5, 1), (1, 1, 90.0, 6, 1),
    (None, 0, 100.0, 1, None), (2, 1, None, 1, None), (4, 0, None, 1, 1)])
def test_penalty_state_follows_quota_and_last_two_minutes(total, late, clock, period, expected):
    assert team_fouls.in_penalty(total, late, clock, period) == expected


def foul(subtype, team=100, descriptor=None):
    return SimpleNamespace(subtype=subtype, team_id=team, raw_json=json.dumps({"descriptor": descriptor}))


@pytest.mark.parametrize("subtype,descriptor,team,expected", [
    ("personal", None, 100, True), ("shooting", None, 100, True), ("loose ball", None, 200, True),
    ("flagrant1", None, 100, True), ("flagrant2", None, 100, True), ("clear path", None, 100, True),
    ("away from play", None, 100, True), ("transition take", None, 100, True), ("take", None, 100, True),
    ("offensive", None, 100, False), ("technical", None, 100, False), ("double technical", None, 100, False),
    ("double personal", None, 100, False), ("personal", "double", 100, False),
    ("mystery", None, 100, None), ("personal", None, None, None)])
def test_team_foul_classification(subtype, descriptor, team, expected):
    assert team_fouls.is_team_foul(foul(subtype, team, descriptor)) is expected


def test_classification_covers_every_parser_foul_subtype():
    assert team_fouls.TEAM_FOUL_SUBTYPES | team_fouls.NON_TEAM_FOUL_SUBTYPES == possessions.FOULS
    assert not team_fouls.TEAM_FOUL_SUBTYPES & team_fouls.NON_TEAM_FOUL_SUBTYPES


def game():
    return [event(1, "period", None, None, "start", "PT12M00S"),
            event(2, shotResult="Made", clock="PT11M00S"),
            event(3, "2pt", 200, 200, clock="PT10M30S", shotResult="Made"),
            event(4, "foul", 100, 200, "personal", "PT10M00S"),
            event(5, "2pt", 200, 200, clock="PT09M50S", shotResult="Made"),
            event(6, "2pt", 100, 100, clock="PT02M10S", shotResult="Made"),
            event(7, "foul", 200, 100, "personal", "PT01M50S"),
            event(8, "2pt", 100, 100, clock="PT01M45S", shotResult="Made"),
            event(9, "foul", 100, 100, "offensive", "PT01M40S"),
            event(10, "2pt", 200, 200, clock="PT01M30S", shotResult="Made"),
            end()]


def test_states_match_parser_defense_counts_and_rules():
    result = parse(game())
    states = team_fouls.states(result)
    assert set(states) == {p.possession_number for p in result.possessions}
    for p in result.possessions:
        assert states[p.possession_number]["defense_team_fouls"] == p.start_state.defense_counted_fouls
        assert states[p.possession_number]["counted_foul_events"] == len(p.counted_foul_action_numbers)
    by_start = {p.start_action_number: states[p.possession_number] for p in result.possessions}
    # Defense 200 fouled once at 1:50; with 1:45 left it is in the penalty.
    assert by_start[9]["defense_team_fouls"] == 1 and by_start[9]["defense_in_penalty"] == 1
    # Offense 200's single late foul puts it in the penalty; defense 100's early foul and
    # its uncounted offensive foul do not.
    assert by_start[10]["offense_team_fouls"] == 1 and by_start[10]["offense_in_penalty"] == 1
    assert by_start[10]["defense_team_fouls"] == 1 and by_start[10]["defense_in_penalty"] == 0


def test_unobserved_period_start_is_flagged_and_withholds_states():
    result = parse(game()[1:])
    assert all(p.start_state.defense_counted_fouls is None for p in result.possessions)
    assert any("partial_start" in p.audit_flags for p in result.possessions)
    with pytest.raises(ValueError, match="unflagged"):
        team_fouls.states(result)


def test_overtime_quota_is_three():
    actions = [event(1, "period", None, None, "start", "PT05M00S")]
    n = 2
    for k in range(3):
        actions += [event(n, "2pt", 100, 100, clock=f"PT04M{50 - 10 * k:02d}S", shotResult="Made"),
                    event(n + 1, "foul", 100, 200, "personal", f"PT04M{48 - 10 * k:02d}S"),
                    event(n + 2, "2pt", 200, 200, clock=f"PT04M{46 - 10 * k:02d}S", shotResult="Made")]
        n += 3
    actions.append(event(n, "2pt", 100, 100, clock="PT04M00S", shotResult="Made"))
    for a in actions:
        a["period"] = 5
    actions.append(dict(end(), period=5))
    result = parse(actions)
    states = team_fouls.states(result)
    last = max(result.possessions, key=lambda p: p.possession_number)
    assert last.offense_team_id == 100
    # Team 100 committed three overtime fouls with more than two minutes left: at the quota.
    assert states[last.possession_number]["offense_team_fouls"] == 3
    assert states[last.possession_number]["offense_in_penalty"] == 1
    assert states[last.possession_number]["defense_in_penalty"] == 0
    for p in result.possessions:
        assert states[p.possession_number]["defense_team_fouls"] == p.start_state.defense_counted_fouls


def test_attach_fails_closed_on_disagreement_or_coverage_gap():
    rows = [{"game_id": "g", "possession_number": n, "defense_counted_fouls": c} for n, c in ((1, 0), (2, 1))]
    good = {"g": {1: {"defense_team_fouls": 0}, 2: {"defense_team_fouls": 1}}}
    assert team_fouls.attach(rows, good) == [good["g"][1], good["g"][2]]
    with pytest.raises(ValueError, match="disagree"):
        team_fouls.attach(rows, {"g": {1: {"defense_team_fouls": 0}, 2: {"defense_team_fouls": 2}}})
    with pytest.raises(ValueError, match="disagree"):
        team_fouls.attach(rows, {"g": {1: {"defense_team_fouls": None}, 2: {"defense_team_fouls": 1}}})
    with pytest.raises(ValueError, match="cover exactly"):
        team_fouls.attach(rows, {"g": {1: {"defense_team_fouls": 0}}})
    with pytest.raises(ValueError, match="cover exactly"):
        team_fouls.attach(rows, {})


def test_technical_fouls_are_skipped_and_counts_reset_each_period():
    actions = [event(1, "period", None, None, "start", "PT12M00S"),
               event(2, "2pt", 200, 200, clock="PT11M00S", shotResult="Made"),
               event(3, "foul", 100, 200, "technical", "PT10M55S"),
               event(4, "foul", 200, 100, "personal", "PT10M30S"),
               event(5, "2pt", 100, 100, clock="PT10M00S", shotResult="Made"),
               event(6, "2pt", 200, 200, clock="PT09M00S", shotResult="Made"), end(7)]
    second = [dict(event(8, "period", None, None, "start", "PT12M00S"), period=2),
              dict(event(9, "2pt", 100, 100, clock="PT11M00S", shotResult="Made"), period=2),
              dict(event(10, "2pt", 200, 200, clock="PT10M00S", shotResult="Made"), period=2),
              dict(end(11), period=2)]
    result = parse(actions + second)
    states = team_fouls.states(result)
    by_start = {p.start_action_number: states[p.possession_number] for p in result.possessions}
    for p in result.possessions:
        assert states[p.possession_number]["defense_team_fouls"] == p.start_state.defense_counted_fouls
    assert by_start[6]["offense_team_fouls"] == 1  # team 200's personal foul; technical not counted
    assert by_start[6]["defense_team_fouls"] == 0
    assert by_start[9]["defense_team_fouls"] == 0 and by_start[10]["offense_team_fouls"] == 0


def test_foul_at_exactly_two_minutes_counts_as_late():
    actions = [event(1, "period", None, None, "start", "PT12M00S"),
               event(2, "2pt", 100, 100, clock="PT03M00S", shotResult="Made"),
               event(3, "2pt", 200, 200, clock="PT02M30S", shotResult="Made"),
               event(4, "foul", 100, 200, "personal", "PT02M00S"),
               event(5, "2pt", 200, 200, clock="PT01M58S", shotResult="Made"),
               event(6, "2pt", 100, 100, clock="PT01M50S", shotResult="Made"),
               event(7, "2pt", 200, 200, clock="PT01M40S", shotResult="Made"), end()]
    result = parse(actions)
    states = team_fouls.states(result)
    by_start = {p.start_action_number: states[p.possession_number] for p in result.possessions}
    assert by_start[7]["defense_team_fouls"] == 1 and by_start[7]["defense_in_penalty"] == 1


def test_flagged_possessions_withhold_states():
    result = parse([event(1, "period", None, None, "start", "PT12M00S"),
                    event(2, "2pt", 100, 100, clock="PT11M00S", shotResult="Made"),
                    event(3, "foul", 100, 100, "double personal", "PT10M50S"),
                    event(4, "2pt", 200, 200, clock="PT10M00S", shotResult="Made"), end()])
    assert any(p.audit_flags for p in result.possessions)
    with pytest.raises(ValueError, match="unflagged"):
        team_fouls.states(result)


def _patch_sources(monkeypatch, sources, games):
    from whistle_research import features, reconcile, sources as source_module
    from contextlib import contextmanager

    @contextmanager
    def snapshot(*args):
        yield args[0]

    monkeypatch.setattr(source_module, "verify_sources", lambda manifest, cache: {"sources": sources})
    monkeypatch.setattr(source_module, "safe_path", lambda root, name: name)
    monkeypatch.setattr(reconcile, "verified_snapshot", snapshot)
    monkeypatch.setattr(reconcile, "metadata_rows", lambda paths: ({"g1": {}, "g2": {}}, []))
    monkeypatch.setattr(reconcile, "archive_games", lambda name: iter(games[name]))
    monkeypatch.setattr(features, "_reconstruct_game", lambda actions, gid, meta, sha: parse(game()))


OFFICIAL = "cdnnba_2024.tar.xz"


def source(name=OFFICIAL, status="verified"):
    return {"source_file": name, "status": status, "expected_bytes": 1, "expected_sha256": "0" * 64}


def test_supplement_reconstructs_only_requested_games(monkeypatch):
    _patch_sources(monkeypatch, [source(), source("other.tar.xz")],
                   {OFFICIAL: [("g1", [], [], "m"), ("g2", [], [], "m")], "other.tar.xz": []})
    out = team_fouls.supplement_for_games({"g1"}, source_manifest=None, cache=None, metadata=[])
    assert set(out) == {"g1"} and out["g1"] == team_fouls.states(parse(game()))


@pytest.mark.parametrize("case,match", [("unverified", "not verified"), ("missing", "missing"),
                                        ("duplicate", "duplicate")])
def test_supplement_fails_closed(monkeypatch, case, match):
    if case == "unverified":
        sources, games = [source(status="mismatch")], {OFFICIAL: []}
    elif case == "missing":
        sources, games = [source()], {OFFICIAL: [("g1", [], [], "m")]}
    else:
        second = "cdnnba_2023.tar.xz"
        sources, games = [source(), source(second)], {OFFICIAL: [("g1", [], [], "m")],
                                                      second: [("g1", [], [], "m")]}
    _patch_sources(monkeypatch, sources, games)
    with pytest.raises(ValueError, match=match):
        team_fouls.supplement_for_games({"g1", "g2"} if case == "missing" else {"g1"},
                                        source_manifest=None, cache=None, metadata=[])
