"""Build a source-bound coordinator lookup, never footage or human evidence.

Run from the repository root with --output NEW_DIRECTORY. Report/designed-plan
pins come from the existing committed handoff. Correction/access pins retain
their exact historical snapshots; their statements are not independently
authenticated here. Archive bytes and cited external correction pages are not
retrieved or reverified by this offline catalog builder.
"""

import argparse
import csv
from datetime import date
import hashlib
import io
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from whistle_research import audit

ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION = Path(__file__)
SCRIPT_PATH = "research/audit_access_2026_11_06/prepare_catalog.py"
BASE = "research/hypotheses_2026_09_12"
COHORTS = ("2020", "2021", "2022", "2023", "2024", "po_2024")
PATHS = {
    "report": "output/v2/development-pipeline-v7-2026-11-02/report.json",
    "inventory": "output/v2/development-pipeline-v7-2026-11-02/inventory.json",
    "design": "research/audit_handoff_2026_11_06/design.json",
    "selection": "research/audit_handoff_2026_11_06/selected_games.json",
    "plan": "output/v2/audit-design-2026-11-06/audit_plan.json",
    "schedule": "research/rewrite_completion_2026_11_02/schedule_expected.json",
    "corrections": "research/rewrite_completion_2026_11_02/schedule_date_corrections.json",
    "source_manifest": f"{BASE}/source_manifest.json",
    "historical_access": "research/cross_feed_2026_11_05/league_pass_access.json",
    **{f"historical_metadata_{i}": f"{BASE}/cdnnba_{cohort}_games.csv"
       for i, cohort in enumerate(COHORTS)},
}
PINS = {
    "report": "31ed644257686112632bfa6a8235c9d00d0664bd0e8c6e90e14cca3f1ab8cbc8",
    "inventory": "473e0ac45f96ba3c2c78e3cea43b8af4c33cf291ca26ec4ae89099cf7308d2fc",
    "design": "fefc2c19a109ec41e013664c1d15f39a8188453f3970cfaa3f1f49f8d40346e1",
    "selection": "93f984ebf1c67d5b42a279cbd437b956e74ab64fd537742f2feaad0321f854b4",
    "plan": "0993697bb897668454f94b27e8fd02f3d7f42683e846ebcbbdab2ef3dde7aff5",
    "corrections": "7a21631b89772eaba52c596d1a85cc49ba63ab54febebc68484358ca89f0c398",
    "historical_access": "d45b89e6b29f8cbd1ca19070b9230c0543755e9bb9f65412fb20c51025fafe1d",
}
EXPECTED_FRAME = 6084
EXPECTED_SELECTED = 303
EXPECTED_RANDOM = 299
EXPECTED_ENRICHED = 4


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def load_json(raw):
    def invalid_constant(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)


def unique_games(rows, label):
    require(isinstance(rows, list), label + " games must be a list")
    result = {}
    for index, row in enumerate(rows):
        gid = row["game_id"]
        require(isinstance(gid, str) and re.fullmatch(r"\d{10}", gid), label + " noncanonical game ID")
        require(gid not in result, label + " duplicate game ID")
        result[gid] = (index, row)
    return result


def iso_date(value):
    require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value, "invalid game date")
    return value


def official_url(value, game_id, away=None, home=None):
    require(isinstance(value, str), "official URL must be text")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.netloc == "www.nba.com"
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r"/game/[a-z]{3}-vs-[a-z]{3}-" + game_id + r"(?:/(?:box-score|play-by-play))?", parsed.path),
            "malformed or wrong-game official URL")
    if away is not None and home is not None:
        require(parsed.path.split("/")[2] == f"{away.lower()}-vs-{home.lower()}-{game_id}",
                "official URL matchup mismatch")
    return value


def build_catalog(raw):
    """Validate captured inputs, then build a deterministic lookup from those bytes."""
    for role, pin in PINS.items():
        require(sha(raw[role]) == pin, "pinned input drift: " + role)
    report, design, selection, plan, inventory, schedule, corrections, access = (
        load_json(raw[role]) for role in
        ("report", "design", "selection", "plan", "inventory", "schedule", "corrections", "historical_access"))
    require(report.get("schema_version") == "development-research-report-v1", "unknown development report")
    require(design.get("schema_version") == "audit-design-evidence-v1"
            and selection.get("schema_version") == "audit-selected-games-v1", "unknown design/selection schema")
    require(not audit.validate_plan(plan), "invalid or stale parser-bound audit plan")
    require(report.get("versions", {}).get("parser_version") == plan["parser_version"]
            and report["versions"].get("parser_sha256") == plan["parser_sha256"], "development parser mismatch")
    for role in ("inventory", "schedule", "source_manifest", *(f"historical_metadata_{i}" for i in range(6))):
        binding = report["artifacts"][role]
        require(binding["sha256"] == sha(raw[role]) and binding["bytes"] == len(raw[role]),
                "development artifact binding mismatch: " + role)
        resolved = (Path(PATHS["report"]).parent / binding["path"]).as_posix()
        # Resolve path traversal without filesystem access: actual loader also bounds paths.
        require((ROOT / resolved).resolve() == (ROOT / PATHS[role]).resolve(), "development artifact role path mismatch")
    for role, name in (("selection", "selected_games.json"), ("plan", "audit_plan.json")):
        require(design["outputs"][name] == {"sha256": sha(raw[role]), "bytes": len(raw[role])},
                "design output binding mismatch: " + role)
    require(design["inputs"]["report.json"]["sha256"] == sha(raw["report"])
            and plan["inventory_sha256"] == sha(raw["inventory"]), "design inventory/report mismatch")
    coverage = inventory.get("coverage", {})
    require(inventory.get("kind") == "game_inventory" and inventory.get("ok") is True
            and inventory.get("source_failures") == [] and coverage.get("status") == "schedule_checked"
            and coverage.get("completeness") == "accounted_for"
            and coverage.get("schedule_evidence", {}).get("sha256") == sha(raw["schedule"])
            and plan["inventory_coverage"] == coverage, "unverified source/schedule accounting")
    frame = unique_games(plan["frame"], "frame")
    source_rows = unique_games(inventory["games"], "inventory")
    require(len(frame) == EXPECTED_FRAME and set(frame) == set(source_rows), "incomplete declared frame")
    require(all(g.get("disposition") == "observed" and g.get("anomalies") == []
                and {k: g[k] for k in audit.SOURCE_KEYS} == frame[gid][1]
                for gid, (_, g) in source_rows.items()), "inventory frame/source mismatch")
    selected = unique_games(selection["games"], "selection")
    require(selection["plan_sha256"] == plan["plan_sha256"] == design["selection"]["plan_sha256"]
            and selection["frame_sha256"] == plan["frame_sha256"] == design["selection"]["frame_sha256"],
            "selection plan/frame binding mismatch")
    expected = [{**g, "in_random_sample": g["stratum"] == "random",
                 "in_enriched_sample": g["game_id"] in plan["enriched_game_ids"],
                 "enriched_reason": plan["enriched_reasons"].get(g["game_id"])} for g in plan["games"]]
    require(selection["games"] == expected and len(selected) == EXPECTED_SELECTED
            and plan["sample_size"] == EXPECTED_RANDOM and len(plan["enriched_game_ids"]) == EXPECTED_ENRICHED,
            "changed or incomplete selected sample")
    manifest_rows = load_json(raw["source_manifest"])
    sources = {g["file"]: g for g in manifest_rows}
    require(len(sources) == len(manifest_rows), "duplicate source manifest entry")
    for _, g in frame.values():
        require(g["source_file"] in sources and g["source_sha256"] == sources[g["source_file"]]["sha256"],
                "unknown or mismatched archive source")
    scheduled = unique_games(schedule["games"], "schedule")
    require(audit.text(schedule.get("provenance")) and set(scheduled) == set(frame), "incomplete schedule frame")
    require(corrections.get("kind") == "official-NBA-rendered-date-corrections-v1", "unknown correction schema")
    corrected = unique_games(corrections["corrections"], "date corrections")
    metadata = {}
    for i, cohort in enumerate(COHORTS):
        role = f"historical_metadata_{i}"
        reader = csv.DictReader(io.StringIO(raw[role].decode("utf-8")), strict=True)
        required = {"game_id", "year", "postseason", "date", "home", "away"}
        require(reader.fieldnames is not None and len(set(reader.fieldnames)) == len(reader.fieldnames)
                and all(name.strip() for name in reader.fieldnames)
                and required.issubset(reader.fieldnames), "invalid metadata CSV header")
        for row in reader:
            require(None not in row and all(v is not None for v in row.values()), "malformed metadata CSV row")
            gid = row["game_id"]
            require(re.fullmatch(r"\d{10}", gid) and gid not in metadata, "duplicate/noncanonical metadata game")
            require(gid in frame, "metadata game outside declared frame")
            require(row["year"] == cohort.removeprefix("po_")
                    and row["postseason"] == ("1" if cohort.startswith("po_") else "0"), "metadata cohort mismatch")
            archive = f"cdnnba_{cohort}.tar.xz"
            require(frame[gid][1]["source_file"] == archive, "metadata archive mapping mismatch")
            require(re.fullmatch(r"[A-Z]{3}", row["home"]) and re.fullmatch(r"[A-Z]{3}", row["away"])
                    and row["home"] != row["away"], "invalid metadata teams")
            iso_date(row["date"])
            metadata[gid] = (role, reader.line_num, row)
    require(set(metadata) == set(frame), "missing metadata game")
    for gid, (_, game) in scheduled.items():
        old = metadata[gid][2]
        require(game.get("status", "expected") == "expected" and all(game[k] == frame[gid][1][k]
                    for k in ("season", "game_type")), "schedule status/cohort mismatch")
        require(game["home"] == old["home"] and game["away"] == old["away"]
                and game["historical_date"] == old["date"], "metadata/schedule matchup or original-date mismatch")
        iso_date(game["date"])
        correction = game["date_correction"]
        if game["date"] == old["date"]:
            require(correction is None and gid not in corrected, "unnecessary or stale date correction")
        else:
            require(gid in corrected and corrected[gid][1] == correction
                    and all(correction[k] == game[k] for k in ("game_id", "home", "away", "date", "historical_date"))
                    and audit.valid_sha(correction["source_sha256"]) and audit.text(correction["reason"]),
                    "missing or inconsistent official date correction")
            official_url(correction["url"], gid, game["away"], game["home"])
    require(set(corrected).issubset(scheduled), "date correction outside schedule")
    require(access.get("schema_version") == "league-pass-access-observations-v1", "unknown historical access schema")
    accessed = unique_games(access["games"], "historical access")
    require(access["summary"]["fixed_games"] == len(accessed)
            and access["summary"]["full_length_playback_verified_games"] == len(accessed)
            and access["summary"]["full_coverage_verified_games"] == 0
            and access["summary"]["independent_reviews_completed"] == 0, "unsupported historical access summary")
    iso_date(access["checked_on"])
    for gid, (_, observed) in accessed.items():
        require(gid in scheduled, "historical access game outside schedule")
        game = scheduled[gid][1]
        matchup = re.fullmatch(r"([A-Z]{3})\s*@\s*([A-Z]{3})", observed["matchup"])
        require(observed["date"] == game["date"] and observed["date"] <= access["checked_on"]
                and matchup is not None and matchup.groups() == (game["away"], game["home"]),
                "historical access identity/date mismatch")
        official_url(observed["official_url"], gid, game["away"], game["home"])
        opening = [o for o in observed.get("observations", []) if o.get("kind") == "opening"]
        require(observed.get("full_length_playback_verified") is True and audit.text(observed.get("stream_label"))
                and len(opening) >= 1 and all(
                    type(o.get("current_time_seconds")) in (int, float) and math.isfinite(o["current_time_seconds"])
                    and o["current_time_seconds"] > 0 and type(o.get("duration_seconds")) in (int, float)
                    and math.isfinite(o["duration_seconds"]) and o["duration_seconds"] > o["current_time_seconds"]
                    and o.get("paused") is False and type(o.get("ready_state")) is int and o["ready_state"] == 4
                    and "media_error" in o and o["media_error"] is None for o in opening),
                "historical playback observation incomplete")
        require(observed.get("full_coverage_verified") is False
                and observed.get("independent_reviews_completed") == 0, "unexpected historical human/coverage claim")
    games = []
    for gid in selected:
        source = frame[gid][1]
        schedule_index, game = scheduled[gid]
        role, csv_row, old = metadata[gid]
        observations = []
        if gid in accessed:
            index, observed = accessed[gid]
            observations.append({"kind": "historical_playback_observation", "input_role": "historical_access",
                                 "record_index": index, "checked_on": access["checked_on"], "record": observed})
        if gid in corrected:
            observations.append({"kind": "historical_official_date_page_observation",
                                 "input_role": "corrections", "record_index": corrected[gid][0],
                                 "url": corrected[gid][1]["url"],
                                 "meaning": "Date/matchup page evidence only; not replay access"})
        games.append({**source, "home": game["home"], "away": game["away"],
                      "date": game["date"], "historical_metadata_date": old["date"],
                      "date_correction": game["date_correction"],
                      "schedule_record_index": schedule_index, "metadata_input_role": role, "metadata_csv_row": csv_row,
                      "candidate_game_url": f'https://www.nba.com/game/{game["away"].lower()}-vs-{game["home"].lower()}-{gid}',
                      "candidate_url_status": "inferred_from_pinned_matchup_not_individually_verified",
                      "historical_page_observations": observations,
                      "continuous_coverage": "unverified", "independent_reviews_completed": 0})
    return {"schema_version": "audit-access-catalog-v1", "status": "COORDINATOR_LOOKUP_ONLY",
            "plan_sha256": plan["plan_sha256"], "frame_sha256": plan["frame_sha256"],
            "parser_version": plan["parser_version"], "parser_sha256": plan["parser_sha256"],
            "inputs": {role: {"path": PATHS[role], "bytes": len(value), "sha256": sha(value)}
                       for role, value in sorted(raw.items())},
            "counts": {"selected_games": len(games), "metadata_matched_games": len(games),
                       "corrected_date_games": sum(g["date_correction"] is not None for g in games),
                       "games_with_historical_playback_observations": sum(g["game_id"] in accessed for g in games),
                       "games_without_historical_playback_observations": sum(g["game_id"] not in accessed for g in games),
                       "continuous_coverage_verified_games": 0, "independent_reviews_completed": 0},
            "limits": ["Candidate URLs are inferred lookup leads, not verified replay listings or playback.",
                       "Historical observations retain their dates; access is account-, region- and time-dependent.",
                       "Correction source hashes are declarations preserved in the pinned schedule; cited pages are not retrieved here.",
                       "Archive hashes bind declared sources; archive bytes are not consumed or reverified by this catalog.",
                       "No footage, human labels, eligibility, scientific validity or model-fit authorization is created."],
            "games": games}


def prepare(root, output):
    """Capture fixed bytes, refuse in-run drift and write only a fresh directory."""
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError("output already exists")
    implementation = IMPLEMENTATION.read_bytes()
    paths = {role: root / relative for role, relative in PATHS.items()}
    require(all(path.resolve().is_relative_to(root.resolve()) for path in paths.values()), "input path escapes root")
    raw = {role: path.read_bytes() for role, path in paths.items()}
    result = build_catalog(raw)
    result["implementation"] = {"path": SCRIPT_PATH, "bytes": len(implementation), "sha256": sha(implementation)}
    require(IMPLEMENTATION.read_bytes() == implementation, "catalog implementation changed during run")
    require(all(path.read_bytes() == raw[role] for role, path in paths.items()), "catalog input changed during run")
    output.mkdir(parents=True, exist_ok=False)
    with (output / "catalog.json").open("xb") as stream:
        stream.write(encoded(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.root, args.output)
    except (OSError, ValueError, TypeError, KeyError, csv.Error) as exc:
        parser.exit(2, f"audit access catalog error: {exc}\n")
    print(json.dumps({"status": result["status"], **result["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
