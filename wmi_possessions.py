"""Possession reconstruction with period boundaries and past-only start state.

Ownership follows the source possession field. This is a feed-based reconstruction,
not a claim of film-validated live-ball tracking. Final corrected feeds can contain
retrospective edits; historical prediction evaluates these recorded feeds.
"""

import json
import re

import pandas as pd

PARSER_VERSION = "period_start_v2"
EXCLUDED = {"offensive", "technical", "double technical"}


def clock_seconds(value):
    match = re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", str(value))
    return float(match[1]) * 60 + float(match[2]) if match else None


def elapsed_seconds(period, clock):
    return (
        (period - 1) * 720 + 720 - clock
        if period <= 4
        else 2880 + (period - 5) * 300 + 300 - clock
    )


def known_seconds_left(period, clock):
    return (4 - period) * 720 + clock if period <= 4 else clock


def bonus_eligible(period, clock, count, last_two_count):
    return int(
        count >= (4 if period <= 4 else 3) or (clock <= 120 and last_two_count >= 1)
    )


def num(value, default=0):
    try:
        return int(float(value)) if pd.notna(value) else default
    except (ValueError, TypeError):
        return default


def text(value):
    return "" if pd.isna(value) else str(value)


def reconstruct(actions, game_id):
    df = pd.DataFrame(actions).sort_values(
        ["orderNumber", "actionNumber"], kind="stable"
    )
    if df.empty:
        raise ValueError(f"No actions for {game_id}")
    teams = {
        num(r.teamId): str(r.teamTricode)
        for r in df[["teamId", "teamTricode"]].dropna().itertuples()
        if num(r.teamId)
    }
    if len(teams) != 2:
        raise ValueError(f"Expected two teams for {game_id}")
    ids = list(teams)
    # Explicit metadata if supplied, otherwise first unambiguous scoring change.
    home = None
    previous = (0, 0)
    records = df.to_dict("records")
    for a in records:
        scores = (num(a.get("scoreHome")), num(a.get("scoreAway")))
        tid = num(a.get("teamId"))
        if tid in teams and (scores[0] > previous[0]) != (scores[1] > previous[1]):
            home = tid if scores[0] > previous[0] else next(t for t in ids if t != tid)
            break
        previous = scores
    if home is None:
        raise ValueError(f"Cannot infer home team for {game_id}")
    away = next(t for t in ids if t != home)
    rim_available = "area" in df.columns and df["area"].notna().any()
    rows = []
    current = None
    previous_clock = None
    scores = (0, 0)
    counts = {}
    last_two = {}
    player_counts = {}
    orphan_fouls = 0
    invalid_timed = 0

    administrative_groups_removed = 0

    def finish():
        nonlocal administrative_groups_removed
        if current is None:
            return
        if not current["control_event_count"]:
            administrative_groups_removed += 1
            return
        # Technical foul/FT ownership can briefly switch without live control.
        # Join a returning team's segment only if its preceding live segment
        # did not end in a made basket, turnover, offensive foul or final made FT.
        if (
            rows
            and rows[-1]["period"] == current["period"]
            and rows[-1]["offense_team_id"] == current["offense_team_id"]
            and not rows[-1]["last_control_terminal"]
        ):
            previous = rows[-1]
            for field in [
                "defensive_foul_count",
                "free_throw_attempts",
                "free_throw_points",
                "field_goal_attempts",
                "control_event_count",
            ]:
                previous[field] += current[field]
            if previous["rim_attempts"] is not None:
                previous["rim_attempts"] += current["rim_attempts"]
            previous["foul_events"].extend(current["foul_events"])
            for field in [
                "end_action_number",
                "end_clock",
                "seconds_left_in_game",
                "score_difference",
                "home_score_after",
                "away_score_after",
                "last_control_terminal",
            ]:
                previous[field] = current[field]
            previous["foul_called_this_possession"] = int(
                previous["defensive_foul_count"] > 0
            )
        else:
            current["foul_called_this_possession"] = int(
                current["defensive_foul_count"] > 0
            )
            rows.append(current.copy())

    for a in records:
        period = num(a.get("period"))
        clock = clock_seconds(a.get("clock"))
        if clock is None or period < 1:
            invalid_timed += 1
            continue
        tid = num(a.get("teamId"))
        owner = num(a.get("possession"))
        kind = text(a.get("actionType")).lower()
        subtype = text(a.get("subType")).lower()
        descriptor = text(a.get("descriptor")).lower()
        is_foul = kind == "foul"
        is_team_foul = (
            is_foul
            and subtype not in EXCLUDED
            and "double" not in subtype
            and "double" not in descriptor
        )
        is_live = kind in {
            "jumpball",
            "jump ball",
            "2pt",
            "3pt",
            "heave",
            "rebound",
            "turnover",
            "steal",
            "foul",
            "freethrow",
            "free throw",
            "violation",
            "made shot",
            "missed shot",
            "shot",
        }
        new_period = current is None or current["period"] != period
        if (
            is_live
            and owner in teams
            and (
                current is None
                or current["offense_team_id"] != owner
                or current["period"] != period
            )
        ):
            finish()
            defense = next(t for t in ids if t != owner)
            # No future event time or eventual overtime enters the start state.
            start_clock = (
                (720 if period <= 4 else 300) if new_period else previous_clock
            )
            if start_clock is None:
                start_clock = 720 if period <= 4 else 300
            margin = scores[0] - scores[1] if owner == home else scores[1] - scores[0]
            count = counts.get((period, defense), 0)
            lt = last_two.get((period, defense), 0)
            current = dict(
                game_id=str(game_id),
                possession_group=len(rows) + 1,
                possession_number=len(rows) + 1,
                period=period,
                offense_team_id=owner,
                defense_team_id=defense,
                offense_team=teams[owner],
                defense_team=teams[defense],
                home_team=teams[home],
                away_team=teams[away],
                home_defense=int(defense == home),
                start_action_number=num(a.get("actionNumber")),
                start_clock=start_clock,
                seconds_left_before=known_seconds_left(period, start_clock),
                elapsed_before=elapsed_seconds(period, start_clock),
                score_difference_before=margin,
                score_margin_before=abs(margin),
                home_score_before=scores[0],
                away_score_before=scores[1],
                defense_team_fouls_before=count,
                defense_last_two_fouls_before=lt,
                defense_bonus_before=bonus_eligible(period, start_clock, count, lt),
                control_event_count=0,
                last_control_terminal=False,
                defensive_foul_count=0,
                foul_events=[],
                free_throw_attempts=0,
                free_throw_points=0,
                field_goal_attempts=0,
                rim_attempts=0 if rim_available else None,
                rim_attempts_available=bool(rim_available),
                player_foul_max_before=max(player_counts.values(), default=0),
                parser_version=PARSER_VERSION,
            )
        if (
            current is not None
            and current["period"] == period
            and (owner in teams or not is_live)
        ):
            current["end_action_number"] = num(a.get("actionNumber"))
            current["end_clock"] = clock
            current["seconds_left_in_game"] = known_seconds_left(period, clock)
            current["score_difference"] = (
                num(a.get("scoreHome")) - num(a.get("scoreAway"))
            ) * (1 if current["offense_team_id"] == home else -1)
            current["home_score_after"] = num(a.get("scoreHome"))
            current["away_score_after"] = num(a.get("scoreAway"))
            technical = (is_foul and "technical" in subtype) or (
                kind in {"freethrow", "free throw"}
                and "technical" in text(a.get("description")).lower()
            )
            if is_live and not technical:
                current["control_event_count"] += 1
                made = (
                    text(a.get("shotResult")).lower() == "made" or kind == "made shot"
                )
                final_ft = re.fullmatch(r"(\d+) of (\d+)", subtype)
                current["last_control_terminal"] = bool(
                    kind == "turnover"
                    or (is_foul and subtype == "offensive")
                    or (
                        made
                        and (
                            kind in {"2pt", "3pt", "made shot", "shot"}
                            or (final_ft and final_ft[1] == final_ft[2])
                        )
                    )
                )
            if (
                is_foul
                and subtype not in EXCLUDED
                and tid == current["defense_team_id"]
            ):
                current["defensive_foul_count"] += 1
                current["foul_events"].append(
                    dict(
                        action=num(a.get("actionNumber")),
                        period=period,
                        clock=clock,
                        team=teams[tid],
                        player_id=num(a.get("personId")),
                        drawn_player_id=num(a.get("foulDrawnPersonId")),
                        subtype=subtype,
                        descriptor=descriptor,
                        description=text(a.get("description")),
                    )
                )
            if kind in {"freethrow", "free throw"}:
                current["free_throw_attempts"] += 1
                current["free_throw_points"] += int(
                    text(a.get("shotResult")).lower() == "made"
                )
            if num(a.get("isFieldGoal")):
                current["field_goal_attempts"] += 1
                if rim_available:
                    current["rim_attempts"] += int(
                        text(a.get("area")).lower() == "restricted area"
                    )
        elif is_foul:
            orphan_fouls += 1
        if is_team_foul and tid in teams:
            counts[(period, tid)] = counts.get((period, tid), 0) + 1
            if clock <= 120:
                last_two[(period, tid)] = last_two.get((period, tid), 0) + 1
        if is_foul and subtype not in {"technical", "double technical"}:
            player = num(a.get("personId"))
            if player:
                player_counts[player] = player_counts.get(player, 0) + 1
        scores = (
            num(a.get("scoreHome"), scores[0]),
            num(a.get("scoreAway"), scores[1]),
        )
        previous_clock = clock
    finish()
    out = pd.DataFrame(rows)
    out["foul_events"] = out["foul_events"].map(
        lambda events: json.dumps(events, separators=(",", ":"))
    )
    out["possession_number"] = range(1, len(out) + 1)
    out["possession_group"] = out["possession_number"]
    out["administrative_groups_removed"] = administrative_groups_removed
    if out.empty:
        raise ValueError(f"No possessions for {game_id}")
    out["unassigned_foul_events"] = orphan_fouls
    out["invalid_timed_events"] = invalid_timed
    out["points_home"] = out.home_score_after - out.home_score_before
    out["points_away"] = out.away_score_after - out.away_score_before
    out["late_strategy_context"] = (
        (out.period >= 4)
        & (
            ((out.start_clock <= 35) & (out.score_difference_before > 3))
            | ((out.start_clock <= 15) & (out.score_difference_before >= 1))
        )
    ).astype(int)
    return out


def components(df):
    f = df.F_t.to_numpy()
    n = df.N_t.to_numpy()
    recent = df.L_t.to_numpy()
    result = {}
    for level in (0, 1):
        mask = recent == level
        hits = mask & (f == 1)
        result[f"p{level}"] = float(f[mask].mean()) if mask.any() else None
        result[f"q{level}"] = float(n[hits].mean()) if hits.any() else None
    p0, p1, q0, q1 = (result[k] for k in ("p0", "p1", "q0", "q1"))
    result["immediate_ratio"] = p1 / p0 if p0 and p1 is not None else None
    result["continuation_ratio"] = (
        (1 + q1) / (1 + q0) if q0 is not None and q1 is not None else None
    )
    return result


def sequence_features(table):
    out = table.copy()
    f = out.F_t
    for k in range(1, 6):
        out[f"foul_lag_{k}"] = f.shift(k, fill_value=0)
        out[f"same_defense_foul_lag_{k}"] = (
            (f.shift(k, fill_value=0) == 1)
            & (out.defense_team.shift(k) == out.defense_team)
        ).astype(int)
    return out
