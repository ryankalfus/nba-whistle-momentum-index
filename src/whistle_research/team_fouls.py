"""Team fouls and penalty state before each possession; see docs/PLAN_STAGE5.md.

Rules follow NBA Rule No. 12, Section B.V (read 2026-11-09): a quota of four
team fouls per regulation period and three per overtime period, and one team
foul without penalty in the last two minutes when the quota was not reached
earlier. Counts are taken over the existing parser's sorted event order strictly
before each possession's first event, mirroring its before-state snapshot.
These are reconstructions from final play-by-play, not official live bonus flags.
"""

import json

from whistle_research import possessions as parser

TEAM_FOUL_SUBTYPES = frozenset({
    "personal", "shooting", "loose ball", "flagrant1", "flagrant2", "clear path",
    "away from play", "transition take", "take",
})
NON_TEAM_FOUL_SUBTYPES = frozenset({"offensive", "technical", "double technical", "double personal"})
LATE_SECONDS = 120.0
FIELDS = ("defense_team_fouls", "offense_team_fouls", "defense_in_penalty", "offense_in_penalty",
          "counted_foul_events")
if TEAM_FOUL_SUBTYPES | NON_TEAM_FOUL_SUBTYPES != parser.FOULS:
    raise ImportError("team-foul classification must cover every supported parser foul subtype")


def quota(period):
    """Team fouls allowed before the penalty: 4 in regulation, 3 in overtime (B.V.1, V.1.b)."""
    return 4 if period <= 4 else 3


def in_penalty(total, late, clock, period):
    """1 when the team's next common foul is penalized, 0 when not, None when unknown.

    Penalized once the period total reaches the quota, or, with at most two
    minutes left, once one team foul has been committed in the last two minutes
    (B.V.1.c). A foul at exactly 120.0 seconds counts as a last-two-minutes foul.
    """
    if total is None:
        return None
    if total >= quota(period):
        return 1
    if clock is None:
        return None
    return int(clock <= LATE_SECONDS and late >= 1)


def is_team_foul(event):
    """Classify one normalized foul event; None means the label cannot be classified."""
    if event.subtype not in parser.FOULS or event.team_id is None:
        return None
    if event.subtype in NON_TEAM_FOUL_SUBTYPES:
        return False
    descriptor = str(json.loads(event.raw_json).get("descriptor") or "").lower()
    if event.subtype == "personal" and descriptor == "double":
        return False
    return True


def states(result):
    """Return {possession_number: state} for one ReconstructionResult.

    Parity with the parser's before-state nullness is only guaranteed for
    unflagged possessions, so any flagged possession withholds the states.
    """
    if any(p.audit_flags for p in result.possessions):
        raise ValueError(f"team-foul states require unflagged possessions in game {result.game_id}")
    starts = {p.start_action_number: p for p in result.possessions}
    if len(starts) != len(result.possessions):
        raise ValueError("duplicate possession start events")
    teams = (result.home_team_id, result.away_team_id)
    total, late, uncertain, observed, out = {}, {}, set(), set(), {}
    for event in result.events:
        if event.kind == "memo":
            uncertain.update((event.period, team) for team in teams)
            continue
        if event.kind == "period" and event.subtype == "start":
            observed.add(event.period)
        possession = starts.pop(event.action_number, None)
        if possession is not None:
            before = possession.start_state
            state = {}
            for role, team in (("defense", possession.defense_team_id), ("offense", possession.offense_team_id)):
                key = (before.period, team)
                known = before.period in observed and key not in uncertain
                count = total.get(key, 0) if known else None
                state[f"{role}_team_fouls"] = count
                state[f"{role}_in_penalty"] = in_penalty(count, late.get(key, 0), before.clock, before.period)
            state["counted_foul_events"] = len(possession.counted_foul_action_numbers)
            out[possession.possession_number] = state
        if event.kind != "foul" or event.classification == "administrative":
            continue
        classified = is_team_foul(event)
        if classified is None:
            uncertain.update((event.period, team) for team in teams)
        elif classified:
            key = (event.period, event.team_id)
            total[key] = total.get(key, 0) + 1
            if event.clock <= LATE_SECONDS:
                late[key] = late.get(key, 0) + 1
    if starts:
        raise ValueError("possession start event missing from parser event order")
    return out


def attach(rows, supplement):
    """Join states to rows; fail closed unless every row matches and defense counts agree.

    In quality-selected games the defense team-foul count must equal the
    parser's research `defense_counted_fouls`, including nullness.
    """
    by_game = {}
    for row in rows:
        by_game.setdefault(row["game_id"], set()).add(row["possession_number"])
    for game_id, numbers in by_game.items():
        if set(supplement.get(game_id, {})) != numbers:
            raise ValueError(f"team-foul states do not cover exactly the rows of game {game_id}")
    joined = []
    for row in rows:
        state = supplement[row["game_id"]][row["possession_number"]]
        if state["defense_team_fouls"] != row["defense_counted_fouls"]:
            raise ValueError(f"defense team fouls disagree with parser counts in game {row['game_id']} "
                             f"possession {row['possession_number']}")
        joined.append(state)
    return joined


def supplement_for_games(game_ids, *, source_manifest, cache, metadata):
    """Reconstruct only the requested games from verified archives; {game_id: {number: state}}."""
    from whistle_research.features import _reconstruct_game
    from whistle_research.reconcile import archive_games, metadata_rows, verified_snapshot
    from whistle_research.sources import OFFICIAL_ARCHIVES, safe_path, verify_sources

    wanted = set(game_ids)
    historical, _ = metadata_rows(list(metadata))
    verification = verify_sources(source_manifest, cache)
    out = {}
    for source in verification["sources"]:
        name = source.get("source_file")
        if name not in OFFICIAL_ARCHIVES:
            continue
        if source["status"] != "verified":
            raise ValueError(f"source not verified: {name}")
        with verified_snapshot(safe_path(cache, name), source["expected_bytes"],
                               source["expected_sha256"]) as snapshot:
            for game_id, actions, _, _ in archive_games(snapshot):
                if game_id not in wanted:
                    continue
                if game_id in out:
                    raise ValueError("duplicate game across source archives")
                result = _reconstruct_game(actions, game_id, historical[game_id], source["expected_sha256"])
                out[game_id] = states(result)
    if set(out) != wanted:
        raise ValueError("selected games missing from verified archives")
    return out
