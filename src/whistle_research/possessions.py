"""Conservative, traceable NBA CDN candidate; never independent validation."""

from dataclasses import dataclass, replace
import json
import math
import re
from typing import Mapping, Sequence

PARSER_VERSION = "canonical_candidate_v7"
ADMIN = {
    "substitution",
    "timeout",
    "instantreplay",
    "replay",
    "game",
    "period",
    "stoppage",
    "block",
    "ejection",
    "memo",
}
FOULS = {
    "personal",
    "shooting",
    "loose ball",
    "offensive",
    "technical",
    "double technical",
    "double personal",
    "flagrant1",
    "flagrant2",
    "clear path",
    "away from play",
    "transition take",
    "take",
}
SPECIAL = {
    "flagrant1",
    "flagrant2",
    "clear path",
    "away from play",
    "transition take",
    "take",
}


@dataclass(frozen=True)
class ParseIssue:
    code: str
    action_number: int | None
    detail: str
    blocking: bool = True


@dataclass(frozen=True)
class NormalizedEvent:
    game_id: str
    source_row: int
    action_number: int
    order_number: int
    period: int
    clock: float
    team_id: int | None
    possession_team_id: int | None
    kind: str
    subtype: str
    shot_result: str
    home_score: int | None
    away_score: int | None
    classification: str
    raw_json: str


@dataclass(frozen=True)
class BeforeState:
    reference_action_number: int | None
    reference_kind: str
    period: int
    clock: float | None
    home_score: int | None
    away_score: int | None
    defense_counted_fouls: int | None
    previous_foul_indicators: tuple[int | None, ...]


@dataclass(frozen=True)
class Possession:
    game_id: str
    possession_number: int
    period: int
    offense_team_id: int
    defense_team_id: int
    start_action_number: int
    start_state: BeforeState
    event_action_numbers: tuple[int, ...]
    source_rows: tuple[int, ...]
    boundary_reason: str
    foul_indicator: int | None
    counted_foul_action_numbers: tuple[int, ...]
    complete: bool
    audit_flags: tuple[str, ...]


@dataclass(frozen=True)
class ReconstructionResult:
    game_id: str
    home_team_id: int
    away_team_id: int
    parser_version: str
    source_sha256: str | None
    provenance_status: str
    events: tuple[NormalizedEvent, ...]
    possessions: tuple[Possession, ...]
    unassigned_action_numbers: tuple[int, ...]
    issues: tuple[ParseIssue, ...]
    audit_status: str
    eligible: bool = False


def _integer(value, label, optional=False):
    if optional and value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"invalid {label}")
    try:
        number = float(value)
    except TypeError, ValueError:
        raise ValueError(f"invalid {label}") from None
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"invalid {label}")
    return int(number)


def _tokens(value):
    """Only the two observed CDN list encodings; never substring matching."""
    if isinstance(value, str):
        return [token.strip() for token in value.split(",")]
    return value if isinstance(value, list) else []


def reconstruct(
    actions: Sequence[Mapping],
    game_id: str,
    home_team_id: int,
    away_team_id: int,
    source_sha256: str | None = None,
) -> ReconstructionResult:
    """Normalize without mutating inputs; invalid structure raises ValueError.

    A supplied hash is a declaration, not verified bytes. A source-ledger caller
    must verify it independently. All results remain gated by independent audit.
    """
    home = _integer(home_team_id, "home_team_id")
    away = _integer(away_team_id, "away_team_id")
    if home <= 0 or away <= 0 or home == away or not str(game_id).strip():
        raise ValueError("explicit distinct teams and game_id required")
    if source_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("invalid SHA256")
    teams = {home, away}
    events, issues, seen = [], [], set()
    for row, a in enumerate(actions):
        raw_game_id = a.get("gameId")
        if raw_game_id is not None:
            raw_id = str(raw_game_id)
            expected_id = str(game_id)
            same_game = (
                int(raw_id) == int(expected_id)
                if raw_id.isdigit() and expected_id.isdigit()
                else raw_id == expected_id
            )
            if not same_game:
                raise ValueError("event gameId differs from explicit game metadata")
        n = _integer(a.get("actionNumber"), "actionNumber")
        order = _integer(a.get("orderNumber"), "orderNumber")
        period = _integer(a.get("period"), "period")
        match = re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", str(a.get("clock")))
        if period < 1 or not match or float(match[2]) >= 60:
            raise ValueError(f"invalid clock/period at action {n}")
        clock = float(match[1]) * 60 + float(match[2])
        if clock > (720 if period <= 4 else 300):
            raise ValueError(f"clock outside period at action {n}")
        if n in seen:
            raise ValueError(f"duplicate actionNumber {n}")
        seen.add(n)
        team = _integer(a.get("teamId"), "teamId", True)
        owner = _integer(a.get("possession"), "possession", True)
        team, owner = team or None, owner or None
        if (team is not None and team not in teams) or (
            owner is not None and owner not in teams
        ):
            raise ValueError(f"event team outside game at action {n}")
        kind = str(a.get("actionType") or "").lower()
        sub = str(a.get("subType") or "").lower()
        technical = kind == "foul" and sub in {"technical", "double technical"}
        text = " ".join(
            str(a.get(k) or "").lower()
            for k in ("description", "descriptor", "qualifiers")
        )
        technical = technical or (kind == "freethrow" and "technical" in text)
        delay_warning = (
            kind == "violation"
            and sub == "delay-of-game"
            and "team" in _tokens(a.get("qualifiers"))
        )
        classification = (
            "administrative"
            if kind in ADMIN or technical or delay_warning
            else "control"
        )
        if delay_warning:
            issues.append(
                ParseIssue(
                    "administrative_delay_of_game",
                    n,
                    "team delay record does not establish or transfer live control",
                    False,
                )
            )
        if kind == "foul" and sub not in FOULS:
            classification = "unsupported"
        elif kind not in ADMIN | {
            "foul",
            "freethrow",
            "2pt",
            "3pt",
            "rebound",
            "turnover",
            "steal",
            "jumpball",
            "violation",
        }:
            classification = "unsupported"
        if classification == "unsupported":
            issues.append(ParseIssue("unsupported_label", n, f"{kind}/{sub}"))
        events.append(
            NormalizedEvent(
                str(game_id),
                row,
                n,
                order,
                period,
                clock,
                team,
                owner,
                kind,
                sub,
                str(a.get("shotResult") or "").lower(),
                _integer(a.get("scoreHome"), "scoreHome", True),
                _integer(a.get("scoreAway"), "scoreAway", True),
                classification,
                json.dumps(dict(a), sort_keys=True, allow_nan=False),
            )
        )
    events.sort(key=lambda e: (e.order_number, e.action_number))
    for previous, e in zip(events, events[1:]):
        if e.order_number == previous.order_number:
            raise ValueError("ambiguous duplicate orderNumber")
    # A memo's timestamp is source-note metadata, not a live-state update.
    # Compare across notes so they cannot conceal a genuine subsequent rise.
    clock_events = [e for e in events if e.kind != "memo"]
    source_clock_corrections = {}
    for position, (previous, e) in enumerate(zip(clock_events, clock_events[1:]), 1):
        if e.period < previous.period:
            raise ValueError(f"clock/period regression at action {e.action_number}")
        if e.period == previous.period and e.clock > previous.clock:
            raw = json.loads(e.raw_json)
            supported_travel_restoration = (
                previous.kind == "turnover"
                and previous.subtype == "traveling"
                and previous.clock == 0
                and previous.team_id == previous.possession_team_id
                and previous.team_id in teams
                and e.kind == "instantreplay"
                and e.subtype == "request"
                and raw.get("descriptor") == "support"
                and raw.get("value") == "Travel with time on the clock"
                and e.possession_team_id in teams - {previous.team_id}
            )
            preceding_shot = clock_events[position - 2] if position >= 2 else None
            supported_foul_restoration = (
                preceding_shot is not None
                and preceding_shot.kind in {"2pt", "3pt"}
                and preceding_shot.shot_result == "missed"
                and preceding_shot.clock == previous.clock == 0
                and preceding_shot.period == previous.period == e.period
                and preceding_shot.team_id == previous.team_id == e.possession_team_id
                and previous.team_id in teams
                and previous.possession_team_id == previous.team_id
                and preceding_shot.possession_team_id == previous.team_id
                and previous.kind == "rebound"
                and previous.subtype == "offensive"
                and "team" in _tokens(json.loads(previous.raw_json).get("qualifiers"))
                and str(json.loads(previous.raw_json).get("shotActionNumber"))
                == str(preceding_shot.action_number)
                and e.kind == "instantreplay"
                and e.subtype == "request"
                and raw.get("descriptor") == "support"
                and raw.get("value") == "Foul occurred prior to expiration of time"
            )
            if not (supported_travel_restoration or supported_foul_restoration):
                raise ValueError(f"clock/period regression at action {e.action_number}")
            source_clock_corrections[e.action_number] = (
                f"source replay after {'traveling' if supported_travel_restoration else 'zero-clock rebound'} "
                f"action {previous.action_number}: "
                f"recorded {previous.clock} -> {e.clock}; source-supported timing, "
                "not independently verified live time"
            )
    possessions, unassigned = [], []
    current = None
    prior = None
    counts = {}
    uncertain_counts = set()
    observed_period_starts = set()
    pending = None
    retained = False
    retained_clock = None

    def flag(code, e, detail):
        if code in {
            "foul_defense_unresolved",
            "offensive_foul_owner_conflict",
            "double_foul_requires_audit",
        }:
            uncertain_counts.update((e.period, team) for team in teams)
        issues.append(ParseIssue(code, e.action_number, detail))
        if current is not None:
            current["flags"].add(code)

    def finish(reason, complete=True):
        nonlocal current, pending, retained, retained_clock
        if current is None:
            return
        possessions.append(
            Possession(
                str(game_id),
                len(possessions) + 1,
                current["period"],
                current["owner"],
                (teams - {current["owner"]}).pop(),
                current["events"][0].action_number,
                current["before"],
                tuple(e.action_number for e in current["events"]),
                tuple(e.source_row for e in current["events"]),
                reason,
                None if current["flags"] else int(bool(current["fouls"])),
                tuple(current["fouls"]),
                complete,
                tuple(sorted(current["flags"])),
            )
        )
        current, pending, retained, retained_clock = None, None, False, None

    for event_index, e in enumerate(events):
        if e.kind == "memo":
            # Notes may describe omitted officiating. Preserve their raw fields,
            # but never let their clock, score, owner or period become live state.
            affected_periods = {e.period}
            if current is not None:
                affected_periods.add(current["period"])
            elif prior is not None:
                affected_periods.add(prior.period)
            uncertain_counts.update(
                (period, team) for period in affected_periods for team in teams
            )
            flag(
                "source_note_requires_audit",
                e,
                "out-of-band memo metadata retained; any implied missing officiating event requires adjudication",
            )
            if current is not None:
                current["events"].append(e)
            else:
                unassigned.append(e.action_number)
            continue
        if e.kind == "period" and e.subtype == "start":
            observed_period_starts.add(e.period)
        if current is not None and e.period != current["period"]:
            flag(
                "missing_period_end", e, "closed on next period; boundary event absent"
            )
            finish("period_change")
        if e.kind == "period" and e.subtype == "end":
            if current is not None:
                current["events"].append(e)
                finish("period_end")
            else:
                unassigned.append(e.action_number)
            prior = e
            continue
        if e.kind == "rebound" and {"team", "deadball"}.issubset(
            _tokens(json.loads(e.raw_json).get("qualifiers"))
        ):
            preceding = next(
                (
                    p
                    for p in reversed(events[:event_index])
                    if p.classification != "administrative" or p.kind == "freethrow"
                ),
                None,
            )
            ft = (
                re.fullmatch(r"(\d+) of (\d+)", preceding.subtype)
                if preceding is not None and preceding.kind == "freethrow"
                else None
            )
            if (
                preceding is not None
                and preceding.kind == "freethrow"
                and preceding.period == e.period
                and preceding.clock == e.clock
                and (
                    preceding.classification == "administrative"
                    or (ft is not None and 1 <= int(ft[1]) < int(ft[2]) <= 3)
                    or retained
                )
            ):
                e = replace(e, classification="administrative")
                events[event_index] = e
                issues.append(
                    ParseIssue(
                        "administrative_deadball_rebound",
                        e.action_number,
                        "same-clock team dead-ball rebound during nonfinal, technical or retained free throws",
                        False,
                    )
                )
        if e.classification == "administrative":
            if e.action_number in source_clock_corrections:
                flag(
                    "source_clock_correction_requires_audit",
                    e,
                    source_clock_corrections[e.action_number],
                )
            if current is not None:
                current["events"].append(e)
            else:
                unassigned.append(e.action_number)
            prior = e
            continue
        owner = e.possession_team_id
        event_flags = set()
        preceding_control = (
            next(
                (
                    p
                    for p in reversed(current["events"])
                    if p.classification != "administrative" or p.kind == "freethrow"
                ),
                None,
            )
            if current is not None
            else None
        )
        jump_raw = (
            json.loads(preceding_control.raw_json)
            if preceding_control is not None
            else {}
        )
        paired_jump_turnover = (
            current is not None
            and preceding_control is not None
            and preceding_control.kind == "jumpball"
            and preceding_control.subtype == "recovered"
            and jump_raw.get("descriptor") == "heldball"
            and preceding_control.team_id == current["owner"]
            and owner == e.team_id == preceding_control.possession_team_id
            and owner in teams - {current["owner"]}
            and e.kind == "turnover"
            and e.subtype in {"lost ball", "bad pass"}
            and e.clock <= preceding_control.clock
            and jump_raw.get("jumpBallLostPersonId") is not None
            and json.loads(e.raw_json).get("personId")
            == jump_raw.get("jumpBallLostPersonId")
        )
        if paired_jump_turnover:
            owner = current["owner"]
        if e.kind == "jumpball" and e.subtype == "recovered" and e.team_id in teams:
            # Recovery identifies the gaining team; the archive can retain the
            # pre-toss possession field. Preserve that original field in events.
            owner = e.team_id
            if owner != e.possession_team_id:
                issues.append(
                    ParseIssue(
                        "recovered_jump_actor_control",
                        e.action_number,
                        "explicit recovered jump actor establishes candidate control; source owner retained",
                        False,
                    )
                )
        if e.kind == "rebound" and e.subtype == "defensive":
            # CDN possession on defensive rebound names the *new* offense.
            owner = e.team_id
            if e.possession_team_id != owner:
                flag("rebound_ownership_conflict", e, "team and possession disagree")
                event_flags.add("rebound_ownership_conflict")
                uncertain_counts.update((e.period, team) for team in teams)
        if owner is None:
            if e.kind == "foul":
                uncertain_counts.update((e.period, team) for team in teams)
            flag("unknown_ownership", e, "no explicit source possession")
            if current is not None:
                current["events"].append(e)
            else:
                unassigned.append(e.action_number)
            prior = e
            continue
        paired_offensive_turnover = (
            pending == "offensive_foul"
            and current is not None
            and not current["offensive_turnover_paired"]
            and owner == current["owner"] == e.team_id
            and e.clock == current["terminal_clock"]
            and e.kind == "turnover"
            and e.subtype == "offensive foul"
        )
        paired_kick_turnover = (
            pending == "offensive_kicked_ball"
            and current is not None
            and not current["kick_turnover_paired"]
            and owner == current["owner"] == e.team_id
            and e.clock == current["terminal_clock"]
            and e.kind == "turnover"
            and e.subtype == "offensive-kicked-ball"
        )
        paired_goaltending = (
            pending == "made_field_goal"
            and current is not None
            and current["terminal_goaltending_qualified"]
            and not current["goaltending_paired"]
            and e.period == current["period"]
            and e.clock == current["terminal_clock"]
            and owner == current["owner"]
            and e.team_id in teams - {owner}
            and e.kind == "violation"
            and e.subtype == "defensive goaltending"
        )
        previous_control = preceding_control
        previous_ft = (
            re.fullmatch(r"(\d+) of (\d+)", previous_control.subtype)
            if previous_control is not None and previous_control.kind == "freethrow"
            else None
        )
        valid_previous_ft = bool(
            previous_ft and 1 <= int(previous_ft[1]) <= int(previous_ft[2]) <= 3
        )
        paired_ft_goaltending = (
            current is not None
            and previous_control is not None
            and previous_control.kind == "freethrow"
            and previous_control.shot_result == "made"
            and previous_control.team_id == current["owner"]
            and valid_previous_ft
            and e.clock == previous_control.clock
            and owner == current["owner"]
            and e.team_id in teams - {owner}
            and e.kind == "violation"
            and e.subtype == "defensive goaltending"
        )
        defensive_lane_entitlement = (
            current is not None
            and e.kind == "violation"
            and e.subtype == "lane"
            and e.team_id in teams - {owner}
            and owner == current["owner"]
            and current["entitlement_clock"] == e.clock
            and previous_control is not None
            and (
                previous_control.kind == "foul"
                or (valid_previous_ft and previous_control.shot_result == "made")
            )
        )
        paired_late_foul = (
            pending == "final_made_free_throw"
            and current is not None
            and not current["late_foul_paired"]
            and not current["entitlement_foul_recorded"]
            and owner == current["owner"]
            and e.clock == current["terminal_clock"]
            and e.kind == "foul"
            and e.subtype in {"personal", "shooting", "loose ball"}
            and e.team_id in teams - {owner}
            and str(json.loads(e.raw_json).get("descriptor") or "").lower()
            not in {
                "double",
                "away-from-play",
                "flagrant-type-1",
                "flagrant-type-2",
                "clear-path",
                "transition take",
                "punching",
            }
            and f"{current['terminal_ft_total']}freethrow"
            in _tokens(json.loads(e.raw_json).get("qualifiers"))
        )
        continuation = (
            paired_offensive_turnover
            or paired_kick_turnover
            or paired_goaltending
            or paired_ft_goaltending
            or paired_late_foul
            or defensive_lane_entitlement
            or paired_jump_turnover
            or (
                pending == "made_field_goal"
                and current is not None
                and owner == current["owner"]
                and e.clock == current["terminal_clock"]
                and e.kind in {"foul", "freethrow"}
            )
        )
        if current is not None and (
            owner != current["owner"] or (pending and not continuation)
        ):
            reason = pending or (
                "defensive_rebound"
                if e.kind == "rebound"
                else "jump_control"
                if e.kind == "jumpball"
                else "source_control_transfer"
            )
            if not pending and e.kind not in {"rebound", "jumpball"}:
                flag("unexplained_control_transfer", e, "no observed terminal event")
            finish(reason)
        if current is None:
            defense = (teams - {owner}).pop()
            new_period = prior is None or prior.period != e.period
            clock = (720 if e.period <= 4 else 300) if new_period else prior.clock
            before = BeforeState(
                None if prior is None else prior.action_number,
                "period_start" if new_period else "before_control_event",
                e.period,
                clock,
                None if prior is None else prior.home_score,
                None if prior is None else prior.away_score,
                (
                    None
                    if (
                        (e.period, defense) in uncertain_counts
                        or e.period not in observed_period_starts
                    )
                    else counts.get((e.period, defense), 0)
                ),
                tuple(p.foul_indicator for p in possessions[-2:]),
            )
            current = dict(
                period=e.period,
                owner=owner,
                before=before,
                events=[],
                fouls=[],
                flags=set(),
                terminal_clock=None,
                offensive_turnover_paired=False,
                kick_turnover_paired=False,
                terminal_goaltending_qualified=False,
                goaltending_paired=False,
                terminal_ft_total=None,
                late_foul_paired=False,
                entitlement_foul_recorded=False,
                entitlement_clock=None,
            )
            if e.period not in observed_period_starts and not any(
                p.period == e.period for p in possessions
            ):
                flag(
                    "partial_start",
                    e,
                    "first observed event does not establish opening control",
                )
        current["events"].append(e)
        current["flags"].update(event_flags)
        if e.classification == "unsupported":
            current["flags"].add("unsupported_label")
        if (
            e.kind in {"2pt", "3pt", "freethrow", "turnover"}
            and e.team_id != owner
            and not paired_jump_turnover
        ):
            flag("event_owner_conflict", e, "acting team differs from offense")
        if e.kind == "foul":
            raw = json.loads(e.raw_json)
            descriptor = str(raw.get("descriptor") or "").lower()
            if e.subtype not in FOULS or e.team_id is None:
                uncertain_counts.update((e.period, team) for team in teams)
            if e.subtype not in FOULS:
                current["flags"].add("unsupported_foul")
            elif e.subtype == "offensive":
                if e.team_id != owner:
                    flag(
                        "offensive_foul_owner_conflict",
                        e,
                        "offensive foul team differs",
                    )
                pending = "offensive_foul"
                current["terminal_clock"] = e.clock
            elif e.subtype == "double personal" or (
                e.subtype == "personal" and descriptor == "double"
            ):
                flag(
                    "double_foul_requires_audit", e, "offsetting attribution unresolved"
                )
            elif e.team_id is None or e.team_id == owner:
                flag(
                    "foul_defense_unresolved",
                    e,
                    "counted defensive attribution unavailable",
                )
            else:
                current["fouls"].append(e.action_number)
                key = (e.period, e.team_id)
                counts[key] = counts.get(key, 0) + 1
                if paired_late_foul:
                    current["late_foul_paired"] = True
                if any(
                    t in _tokens(raw.get("qualifiers"))
                    for t in {"1freethrow", "2freethrow", "3freethrow"}
                ):
                    current["entitlement_foul_recorded"] = True
                    current["entitlement_clock"] = e.clock
                # These exact archive descriptors name special categories; they
                # do not establish season-specific entitlement or FT completeness.
                if e.subtype in SPECIAL or descriptor in {
                    "clear-path",
                    "transition take",
                    "flagrant-type-1",
                    "flagrant-type-2",
                    "punching",
                }:
                    retained = True
                    retained_clock = e.clock
                    pending = None
                    flag(
                        "retained_ball_requires_audit",
                        e,
                        "special foul rule/season requires adjudication",
                    )
                else:
                    if descriptor == "away-from-play":
                        flag(
                            "special_descriptor_requires_audit",
                            e,
                            "archive off-ball descriptor alone does not establish formal entitlement",
                        )
                    # A distinct later-clock ordinary foul establishes a new
                    # entitlement; an earlier retained award cannot carry into it.
                    if (
                        retained
                        and retained_clock is not None
                        and e.clock < retained_clock
                    ):
                        retained = False
                        retained_clock = None
                    if continuation and not paired_late_foul:
                        pending = None
        elif e.kind in {"2pt", "3pt"}:
            if e.shot_result not in {"made", "missed"}:
                flag("unknown_shot_result", e, "cannot determine terminal state")
            elif e.shot_result == "made":
                pending = "made_field_goal"
                current["terminal_clock"] = e.clock
                # Only pair the explicitly corroborated companion row; neither
                # a violation label alone nor malformed qualifiers suffice.
                qualifiers = json.loads(e.raw_json).get("qualifiers")
                if isinstance(qualifiers, str):
                    # The archived CSV stores the CDN qualifier list this way.
                    qualifiers = [token.strip() for token in qualifiers.split(",")]
                current["terminal_goaltending_qualified"] = (
                    e.team_id == owner
                    and isinstance(qualifiers, list)
                    and "defensivegoaltending" in qualifiers
                )
                current["goaltending_paired"] = False
        elif e.kind == "turnover":
            if paired_jump_turnover:
                issues.append(
                    ParseIssue(
                        "paired_jump_loss_companion",
                        e.action_number,
                        f"explicit lost-jumper turnover after recovered jump action {previous_control.action_number}; raw owner retained",
                        False,
                    )
                )
                if e.clock != previous_control.clock:
                    flag(
                        "jump_loss_timing_requires_audit",
                        e,
                        "loss companion and jump have different recorded clocks",
                    )
            elif paired_offensive_turnover:
                current["offensive_turnover_paired"] = True
            elif paired_kick_turnover:
                current["kick_turnover_paired"] = True
            else:
                pending = "turnover"
        elif e.kind == "freethrow":
            ft = re.fullmatch(r"(\d+) of (\d+)", e.subtype)
            if not ft or not 1 <= int(ft[1]) <= int(ft[2]) <= 3:
                flag("unsupported_free_throw", e, "unknown sequence position")
            elif e.shot_result not in {"made", "missed"}:
                flag("unknown_shot_result", e, "free throw result unavailable")
            elif ft[1] == ft[2] and e.shot_result == "made" and not retained:
                pending = "final_made_free_throw"
                current["terminal_clock"] = e.clock
                current["terminal_ft_total"] = int(ft[2])
                current["goaltending_paired"] = False
            current["entitlement_clock"] = e.clock
        elif e.kind == "rebound":
            if e.subtype not in {"offensive", "defensive"}:
                flag("unsupported_rebound", e, "unknown rebound control")
            elif e.team_id != owner:
                flag("rebound_ownership_conflict", e, "rebound team differs from owner")
        elif e.kind == "jumpball" and e.subtype != "recovered":
            flag("unsupported_jump_control", e, "source jump outcome not recognized")
        elif e.kind == "jumpball" and e.team_id not in teams:
            flag("unsupported_jump_control", e, "recovery actor is unavailable")
        elif e.kind == "violation":
            if paired_goaltending or paired_ft_goaltending:
                current["goaltending_paired"] = True
                issues.append(
                    ParseIssue(
                        "corroborated_goaltending_companion",
                        e.action_number,
                        "explicit awarded-score companion retains terminal scoring boundary",
                        False,
                    )
                )
            elif defensive_lane_entitlement:
                issues.append(
                    ParseIssue(
                        "classified_defensive_lane",
                        e.action_number,
                        "defensive lane record during explicit same-clock free-throw entitlement; no live transfer",
                        False,
                    )
                )
            elif e.subtype == "jumpball" and e.team_id in teams:
                if e.team_id == owner:
                    pending = "offensive_jump_violation"
                    detail = "explicit violating offense loses jump-ball entitlement"
                else:
                    detail = (
                        "explicit opponent violation retains source offense entitlement"
                    )
                issues.append(
                    ParseIssue(
                        "classified_jump_violation",
                        e.action_number,
                        detail,
                        False,
                    )
                )
            elif e.subtype == "kicked ball" and e.team_id in teams:
                if e.team_id == owner:
                    pending = "offensive_kicked_ball"
                    current["terminal_clock"] = e.clock
                    current["kick_turnover_paired"] = False
                    detail = "explicit offensive actor loses possession"
                else:
                    detail = (
                        "explicit defensive actor; source offense retains possession"
                    )
                issues.append(
                    ParseIssue("classified_kicked_ball", e.action_number, detail, False)
                )
            else:
                flag(
                    "violation_requires_audit",
                    e,
                    "unresolved violation/control entitlement",
                )
        prior = e
    if current is not None:
        # A terminal basket may still acquire an and-one in an appended suffix.
        current["flags"].add("provisional_final_possession")
        issues.append(
            ParseIssue(
                "provisional_final_possession",
                None,
                "input ends without period-end evidence",
            )
        )
        finish("input_exhausted", False)
    if not events:
        issues.append(ParseIssue("empty_source", None, "no events"))
    issues.append(
        ParseIssue(
            "independent_audit_required",
            None,
            "candidate has no independent reconstruction validation",
        )
    )
    return ReconstructionResult(
        str(game_id),
        home,
        away,
        PARSER_VERSION,
        source_sha256,
        "declared_unverified" if source_sha256 else "missing",
        tuple(events),
        tuple(possessions),
        tuple(unassigned),
        tuple(issues),
        "blocked_pending_independent_audit",
    )
