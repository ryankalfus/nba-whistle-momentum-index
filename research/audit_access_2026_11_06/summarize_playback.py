"""Summarize captured UI metadata, without certifying footage or human evidence."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit

CATALOG = "research/audit_access_2026_11_06/catalog.json"
BASELINE = "research/audit_access_2026_11_06/first_batch_observations.json"
CATALOG_SHA256 = "06aa44fb27877752a7044acf13a0a8b73b0c792a230236cf2b22017abed4a7b4"
BASELINE_SHA256 = "b43dc5cf55dfe022c7d2bb88d5f25fe5caf94e0d3cafd8607296771b89caadd4"
TEAMS = dict(zip(
    "ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WAS".split(),
    ["Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
     "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
     "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers",
     "LA Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat",
     "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
     "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns",
     "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors",
     "Utah Jazz", "Washington Wizards"], strict=True,
))
OBSERVATION_KINDS = frozenset({
    "opening_playback_check", "followup_after_incomplete_first_read",
    "followup_after_browser_session_reset_and_visible_poster_click",
    "followup_after_initial_player_load_timeout", "followup_after_previous_observation",
    "followup_after_separate_ad_element_identified",
})
LIMITS = [
    "METADATA_CONSISTENCY_ONLY: assertions are checked against recorded UI fields, not authenticated footage or person truth.",
    "Full Games tab observations and named-team long streams are separate categories; named-team full-game classification remains inferred.",
    "Opening playback and runtime do not verify uninterrupted coverage, all periods, or annotation correctness.",
    "Access depends on account, region and observation time; account entitlements do not transfer.",
    "Default feeds remain unknown without a captured player header; listed feeds do not prove every feed plays.",
    "No audit-gate input, eligibility change, independent human evidence or model approval is created or evaluated.",
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"non-finite JSON number: {value}")

    def floating(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("non-finite JSON number")
        return parsed

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid, parse_float=floating)


def public_game_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parts = urlsplit(value)
    return (
        parts.scheme == "https" and parts.netloc == "www.nba.com"
        and re.fullmatch(r"/game/[a-z]{2,3}-vs-[a-z]{2,3}-[0-9]{10}", parts.path) is not None
        and parts.query in ("", "watchFullGame=true") and not parts.fragment
    )


def privacy_check(value):
    """Check the entire preserved snapshot, including failed reads and recovery."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            if (normalized in {"src", "currentsrc", "username", "userid", "apikey", "privatekey", "secret"}
                    or any(word in normalized for word in
                           ("password", "email", "token", "cookie", "authorization", "credential", "account"))):
                raise ValueError(f"sensitive key forbidden: {key}")
            if key in {"official_url", "final_url"} and not public_game_url(child):
                raise ValueError("invalid public game URL field")
            if ("url" in normalized and key not in {"official_url", "final_url"}
                    and isinstance(child, str)):
                raise ValueError("URL field is not allowlisted")
            if key in {"full_coverage_verified", "independent_reviews_completed"}:
                expected = False if key == "full_coverage_verified" else 0
                if type(child) is not type(expected) or child != expected:
                    raise ValueError("source claims coverage or human evidence")
            privacy_check(child)
    elif isinstance(value, list):
        for child in value:
            privacy_check(child)
    elif isinstance(value, str):
        if re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", value):
            raise ValueError("email address forbidden")
        if re.search(r"(?:blob|data):", value, re.IGNORECASE):
            raise ValueError("media addresses forbidden")
        for url in re.findall(r"https?://[^\s\"<>]+", value, re.IGNORECASE):
            if not public_game_url(url):
                raise ValueError("only public NBA game URLs are permitted")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite number forbidden")


def aware_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include timezone")
    return value


def title_matches(title, game):
    if not isinstance(title, str):
        return False
    day = date.fromisoformat(game["date"])
    stamp = f"{day.strftime('%b')} {day.day}, {day.year}"
    expected = f"{TEAMS[game['away']]} vs {TEAMS[game['home']]} {stamp} Game Summary | NBA.com"
    # The official title uses this full name on some older Clippers pages.
    return title in (expected, expected.replace("LA Clippers", "Los Angeles Clippers"))


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def identity_matches(row, game):
    candidate = game["candidate_game_url"]
    return (row.get("final_url") in (candidate, candidate + "?watchFullGame=true")
            and title_matches(row.get("page_title"), game))


def opening_predicate(row, game):
    playback = row.get("playback")
    if not isinstance(playback, dict):
        return False
    duration = playback.get("duration_seconds")
    current = playback.get("current_time_seconds")
    return (
        row.get("official_url") == game["candidate_game_url"]
        and identity_matches(row, game) and row.get("full_games_selected") is True
        and finite_number(duration) and duration > 3000
        and finite_number(current) and 0 < current < duration
        and playback.get("paused") is False
        and type(playback.get("ready_state")) is int and playback["ready_state"] == 4
        and "media_error" in playback and playback["media_error"] is None
    )


def header_matches(header, game):
    """Match actual header matchup, allowing title names, suffix nicknames and tricodes."""
    if not isinstance(header, str) or not header.strip():
        return False
    first_line, separator, suffix = header.strip().splitlines()[0].partition(",")
    if separator:
        stamp = re.sub(r"\s*,\s*", ", ", suffix.strip())
        parsed_date = None
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                parsed_date = datetime.strptime(stamp, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date is None or parsed_date.isoformat() != game["date"]:
            return False
    first_line = first_line.strip()
    teams = re.split(r"\s+@\s+", first_line)
    if len(teams) != 2:
        return False
    for actual, code in zip(teams, (game["away"], game["home"]), strict=True):
        actual = actual.strip().casefold()
        expected = TEAMS[code].casefold()
        if actual == code.casefold():
            continue
        if len(actual) < 3 or not (actual == expected or re.search(r"\b" + re.escape(actual) + r"$", expected)):
            # Preserve the alternate official full Clippers name.
            if not (code == "LAC" and actual == "los angeles clippers"):
                return False
    return True


def reviewer_descriptor(item):
    """Export typed access fields; raw methods and headers stay coordinator-only."""
    allowed = {"timestamps", "duration_seconds", "evidence_mode",
               "full_game_classification", "stream_label", "stream_selection_observed_at"}
    result = {key: item[key] for key in allowed if key in item}
    result["timestamp_kind"] = "observed_at" if "observed_at" in item["timestamps"] else "checked_at"
    return result


def team_stream_predicate(row, game):
    """Separate long named-team stream observation; its full-game meaning is inferred."""
    selection = row.get("team_stream_selection")
    playback = row.get("playback")
    if not isinstance(selection, dict) or not isinstance(playback, dict):
        return False
    label = selection.get("label")
    options = selection.get("menu_options")
    header = row.get("player_header_text")
    if (not isinstance(label, str) or len(label) < 3 or label != label.strip()
            or not isinstance(options, list) or not all(isinstance(item, str) for item in options)
            or label not in options or not isinstance(header, str) or not header.strip()
            or header.rstrip().splitlines()[-1].strip() != label):
        return False
    if re.search(r"condens|recap|possessions|mobile|audio|radio|court\s*vision|generic", label, re.IGNORECASE):
        return False
    if not any(re.search(r"\b(?:recap|condensed)\b", item, re.IGNORECASE) for item in options):
        return False
    if not identity_matches(row, game):
        return False
    day = date.fromisoformat(game["date"])
    suffix = f" {day.strftime('%b')} {day.day}, {day.year} Game Summary | NBA.com"
    parsed_teams = row["page_title"][:-len(suffix)].split(" vs ")
    if selection.get("title_teams") != parsed_teams:
        return False
    if not any(label == team or re.search(r"\b" + re.escape(label) + r"$", team) for team in parsed_teams):
        return False
    aware_timestamp(selection.get("observed_at"))
    # Reuse the exact old health/identity predicate on a copy, without changing raw fields.
    health_row = dict(row, full_games_selected=True)
    return (
        opening_predicate(health_row, game)
        and row.get("full_games_selected") is False
        and row.get("evidence_mode") == "named_team_stream_v1"
        and row.get("full_game_classification") == "inferred"
        and all(finite_number(playback.get(key)) and playback[key] > 0
                for key in ("video_width", "video_height"))
    )


def validate_observation(row, game):
    if not isinstance(row, dict):
        raise ValueError("observation must be an object")
    candidate = game["candidate_game_url"]
    if "kind" in row and (not isinstance(row["kind"], str) or row["kind"] not in OBSERVATION_KINDS):
        raise ValueError("observation kind must be a controlled string")
    header = row.get("player_header_text")
    if header is not None and not header_matches(header, game):
        raise ValueError("captured player header contradicts game matchup or has invalid type")
    for key in ("official_url", "final_url"):
        if key in row and row[key] not in (candidate, candidate + "?watchFullGame=true"):
            raise ValueError(f"wrong game URL for {game['game_id']}")
    if "page_title" in row and not title_matches(row["page_title"], game):
        raise ValueError(f"wrong page title/date for {game['game_id']}")
    times = {key: aware_timestamp(row[key]) for key in ("checked_at", "observed_at") if key in row}
    if not times:
        raise ValueError("observation lacks actual timestamp")
    for key, value in row.items():
        if key.endswith("_at") and value is not None:
            aware_timestamp(value)
    success = opening_predicate(row, game)
    team_success = team_stream_predicate(row, game)
    status = row.get("status")
    if status not in ("OPENING_PLAYBACK_VERIFIED", "TEAM_STREAM_PLAYBACK_OBSERVED", "NOT_VERIFIED"):
        raise ValueError("unknown observation status")
    if (status == "OPENING_PLAYBACK_VERIFIED") != success:
        raise ValueError("status disagrees with computed playback predicates")
    if (status == "TEAM_STREAM_PLAYBACK_OBSERVED") != team_success:
        raise ValueError("status disagrees with named team stream predicates")
    if "team_broadcast_playback_observed" in row:
        if type(row["team_broadcast_playback_observed"]) is not bool or row["team_broadcast_playback_observed"] != team_success:
            raise ValueError("team stream flag disagrees with computed predicates")
    elif team_success:
        raise ValueError("team stream observation requires explicit flag")
    if "full_length_playback_verified" in row:
        if type(row["full_length_playback_verified"]) is not bool or row["full_length_playback_verified"] != success:
            raise ValueError("playback flag disagrees with computed predicates")
    elif success or team_success or not row.get("reason"):
        raise ValueError("missing playback flag requires explicit failure reason")
    for key, expected in (("full_coverage_verified", False), ("independent_reviews_completed", 0)):
        if key in row:
            if type(row[key]) is not type(expected) or row[key] != expected:
                raise ValueError("coverage and human evidence cannot be created")
        elif success or team_success:
            raise ValueError("success lacks coverage/human evidence limits")
    return success, team_success, times


def summarize(source, catalog, baseline):
    """Pure metadata transformation; callers of this helper supply their own fixtures."""
    privacy_check(source)
    if not isinstance(source, dict) or not isinstance(source.get("observations"), list):
        raise ValueError("source must contain observations")
    rows = source["observations"]
    if rows[:len(baseline["observations"])] != baseline["observations"]:
        raise ValueError("initial baseline observations changed or missing")
    games = catalog["games"]
    by_id = {game["game_id"]: game for game in games}
    if len(by_id) != len(games):
        raise ValueError("duplicate catalog game")
    if "catalog_sha256" in source and source["catalog_sha256"] != CATALOG_SHA256:
        raise ValueError("source catalog hash mismatch")
    if "selected_game_ids" in source:
        selected = source["selected_game_ids"]
        if len(selected) != len(set(selected)) or set(selected) != set(by_id):
            raise ValueError("selected IDs disagree with complete catalog")
    for key, expected in (("full_coverage_verified", False), ("independent_reviews_completed", 0)):
        if key in source and (type(source[key]) is not type(expected) or source[key] != expected):
            raise ValueError("source claims coverage or human evidence")
    if "saved_at" in source:
        aware_timestamp(source["saved_at"])
    attempts = {gid: [] for gid in by_id}
    successes = {gid: [] for gid in by_id}
    team_successes = {gid: [] for gid in by_id}
    missing_limits = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("game_id") not in by_id:
            raise ValueError("unknown observation game ID")
        gid = row["game_id"]
        success, team_success, times = validate_observation(row, by_id[gid])
        attempts[gid].append(index)
        missing_limits += int("full_coverage_verified" not in row or "independent_reviews_completed" not in row)
        if success or team_success:
            descriptor = {"observation_index": index, "timestamps": times,
                          "kind": row.get("kind", "not_recorded"),
                          "duration_seconds": row["playback"]["duration_seconds"],
                          "player_header": row.get("player_header_text") or "unknown_default_feed"}
            if success:
                descriptor.update(evidence_mode="full_games_tab_v1", full_game_classification="explicit_full_games_selection")
                successes[gid].append(descriptor)
            else:
                descriptor.update(evidence_mode="named_team_stream_v1", full_game_classification="inferred",
                                  stream_label=row["team_stream_selection"]["label"],
                                  stream_selection_observed_at=row["team_stream_selection"]["observed_at"])
                team_successes[gid].append(descriptor)
    verified = [gid for gid in by_id if successes[gid]]
    team_observed = [gid for gid in by_id if team_successes[gid]]
    playback_observed = [gid for gid in by_id if successes[gid] or team_successes[gid]]
    playback_unobserved = [gid for gid in by_id if not successes[gid] and not team_successes[gid]]
    attempted = [gid for gid in by_id if attempts[gid]]
    unattempted = [gid for gid in by_id if not attempts[gid]]
    unverified = [gid for gid in by_id if not successes[gid]]
    status = ("ALL_SELECTED_OPENINGS_VERIFIED" if not unverified else
              "ALL_SELECTED_REPLAY_ACCESS_OBSERVED" if not playback_unobserved else
              "ALL_SELECTED_ACCESS_ATTEMPTED" if not unattempted else "PARTIAL_ACCESS_CHECK")
    summary_games = []
    links = []
    for game in games:
        gid = game["game_id"]
        summary_games.append({"game_id": gid, "date": game["date"], "observation_indices": attempts[gid],
                              "successful_observations": successes[gid],
                              "team_broadcast_observations": team_successes[gid], "continuous_coverage": "unverified",
                              "independent_reviews_completed": 0})
        matching = [rows[index] for index in attempts[gid] if identity_matches(rows[index], game)]
        links.append({"game_id": gid, "date": game["date"],
                      "matchup": f"{game['away']} @ {game['home']}",
                      "public_url": matching[-1]["final_url"] if matching else game["candidate_game_url"],
                      "url_status": "observed_matching_page" if matching else "inferred_lead",
                      "opening_playback_observed": bool(successes[gid] or team_successes[gid]),
                      "successful_observations": [reviewer_descriptor(item) for item in successes[gid]],
                      "team_broadcast_observations": [reviewer_descriptor(item) for item in team_successes[gid]],
                      "continuous_coverage": "unverified"})
    summary = {"schema_version": "nba-playback-metadata-summary-v1", "status": status,
               "verification_scope": "METADATA_CONSISTENCY_ONLY", "limits": LIMITS,
               "counts": {"selected_games": len(games), "raw_observations": len(rows),
                          "successful_reads": sum(map(len, successes.values())),
                          "unique_verified_games": len(verified), "strict_verified_games": len(verified),
                          "full_game_classification_explicit_games": len(verified),
                          "team_broadcast_observed_games": len(team_observed),
                          "unique_playback_observed_games": len(playback_observed),
                          "team_broadcast_observed_reads": sum(map(len, team_successes.values())),
                          "playback_observed_reads": sum(map(len, successes.values())) + sum(map(len, team_successes.values())),
                          "attempted_games": len(attempted),
                          "unattempted_games": len(unattempted), "unverified_games": len(unverified),
                          "observations_with_unknown_coverage_or_human_fields": missing_limits,
                          "continuous_coverage_verified_games": 0, "independent_reviews_completed": 0},
               "unattempted_game_ids": unattempted, "unverified_game_ids": unverified,
               "playback_unobserved_game_ids": playback_unobserved,
               "games": summary_games}
    addendum = {"schema_version": "reviewer-access-links-v1", "resource_kind": "separate_access_addendum",
                "limits": LIMITS, "games": links}
    return summary, addendum


def descriptor(path, data, root):
    return {"path": path.resolve().relative_to(root).as_posix(), "bytes": len(data), "sha256": sha256(data)}


def export(observations: Path, output: Path, root: Path):
    root = root.resolve()
    paths = {"observations": observations.resolve(), "catalog": root / CATALOG,
             "baseline": root / BASELINE, "implementation": Path(__file__).resolve()}
    for path in (*paths.values(), output.resolve()):
        path.relative_to(root)
    if output.exists():
        raise FileExistsError("output directory must be new")
    consumed = {key: path.read_bytes() for key, path in paths.items()}
    if sha256(consumed["catalog"]) != CATALOG_SHA256 or sha256(consumed["baseline"]) != BASELINE_SHA256:
        raise ValueError("pinned catalog or baseline bytes changed")
    source, catalog, baseline = (strict_json(consumed[key]) for key in ("observations", "catalog", "baseline"))
    if len(catalog["games"]) != 303 or len(baseline["observations"]) != 24:
        raise ValueError("fixed catalog/baseline count mismatch")
    summary, addendum = summarize(source, catalog, baseline)
    summary["inputs"] = {key: descriptor(paths[key], consumed[key], root) for key in paths}
    summary["source_snapshot"] = {"path": "observations.json", "bytes": len(consumed["observations"]),
                                  "sha256": sha256(consumed["observations"])}

    def check_drift():
        if any(path.read_bytes() != consumed[key] for key, path in paths.items()):
            raise ValueError("input or implementation bytes changed during run")

    check_drift()
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "observations.json").write_bytes(consumed["observations"])
        for filename, value in (("summary.json", summary), ("reviewer_access_addendum.json", addendum)):
            (output / filename).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
        check_drift()
    except Exception:
        shutil.rmtree(output)
        raise
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        summary = export(args.observations, args.output, args.root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"playback summary refused: {exc}\n")
    print(json.dumps({"status": summary["status"], "counts": summary["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
