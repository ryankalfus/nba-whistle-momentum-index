"""Streaming provisional recorded-before-event features; never eligibility."""

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import tarfile

from whistle_research.audit import SOURCE_KEYS, digest
from whistle_research.possessions import PARSER_VERSION, reconstruct
from whistle_research.reconcile import archive_games, metadata_rows, verified_snapshot
from whistle_research.sources import (
    OFFICIAL_ARCHIVES,
    canonical_game_id,
    file_digest,
    safe_path,
    verify_sources,
)

FEATURE_VERSION = "before_event_v1"


def feature_module_sha256():
    """Bind the exact feature implementation bytes."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _metadata(row, game_id=None):
    if not isinstance(row, dict):
        raise ValueError("game metadata must be an object")
    gid = row.get("game_id")
    if (
        not isinstance(gid, str)
        or canonical_game_id(gid) != gid
        or (game_id is not None and gid != game_id)
    ):
        raise ValueError("canonical matching metadata game_id required")
    day = row.get("date")
    if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
        raise ValueError("metadata date must use YYYY-MM-DD")
    season = row.get("season")
    if not isinstance(season, str) or not re.fullmatch(r"\d{4}-\d{2}", season):
        raise ValueError("metadata season required")
    if int(season[-2:]) != (int(season[:4]) + 1) % 100:
        raise ValueError("invalid season span")
    if row.get("game_type") not in {"regular_season", "playoffs"}:
        raise ValueError("explicit game_type required")
    return row


def build_rows(result, metadata):
    """One row per group, including unknown outcomes; context reads BeforeState."""
    meta = _metadata(metadata, result.game_id)
    rows = []
    for possession in result.possessions:
        before = possession.start_state
        home_defense = int(possession.defense_team_id == result.home_team_id)
        difference = (
            None
            if before.home_score is None or before.away_score is None
            else before.home_score - before.away_score
        )
        previous = before.previous_foul_indicators
        rows.append(
            {
                "game_id": result.game_id,
                "date": meta["date"],
                "season": meta["season"],
                "game_type": meta["game_type"],
                "possession_number": possession.possession_number,
                "period": before.period,
                "clock": before.clock,
                "score_margin": None if difference is None else abs(difference),
                "score_difference": (
                    None
                    if difference is None
                    else difference
                    if home_defense
                    else -difference
                ),
                "defense_team_id": possession.defense_team_id,
                "offense_team_id": possession.offense_team_id,
                "home_defense": home_defense,
                "defense_counted_fouls": before.defense_counted_fouls,
                "previous_foul_1": previous[-1] if previous else None,
                "previous_foul_2": previous[-2] if len(previous) > 1 else None,
                "start_type": before.reference_kind,
                "outcome": possession.foul_indicator,
            }
        )
    return rows


def load_schedule(path, historical):
    """Validate unique corrected-date bindings; never substitute historical dates."""
    raw = path.read_bytes()
    packet = json.loads(raw)
    if not isinstance(packet, dict) or not isinstance(packet.get("games"), list):
        raise ValueError("schedule games list required")
    if (
        not isinstance(packet.get("provenance"), str)
        or not packet["provenance"].strip()
    ):
        raise ValueError("schedule provenance required")
    result = {}
    for row in packet["games"]:
        _metadata(row)
        gid = row["game_id"]
        if gid in result or gid not in historical:
            raise ValueError("duplicate/unbound schedule game_id")
        old = historical[gid]
        if (row.get("home"), row.get("away")) != (old["home"], old["away"]):
            raise ValueError("schedule/historical team binding mismatch")
        if row["season"] != f"{old['year']}-{str(int(old['year']) + 1)[-2:]}" or row[
            "game_type"
        ] != ("playoffs" if old["postseason"] == "1" else "regular_season"):
            raise ValueError("schedule/historical cohort mismatch")
        if row.get("historical_date") != old["date"]:
            raise ValueError("schedule historical-date binding mismatch")
        correction = row.get("date_correction")
        if row["date"] != old["date"]:
            if not isinstance(correction, dict) or any(
                correction.get(key) != row.get(key)
                for key in ("game_id", "date", "historical_date", "home", "away")
            ):
                raise ValueError("corrected date requires matching correction binding")
            if not re.fullmatch(r"[0-9a-f]{64}", str(correction.get("source_sha256"))):
                raise ValueError("date correction source hash required")
        elif correction is not None:
            raise ValueError("unchanged date cannot carry correction")
        if (
            not isinstance(row.get("espn_event_id"), str)
            or not row["espn_event_id"].isdigit()
        ):
            raise ValueError("independent schedule event ID required")
        result[gid] = row
    if not result or set(result) != set(historical):
        raise ValueError("schedule/historical game sets must match exactly")
    return result, {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "provenance": packet["provenance"],
        "corrected_dates": sum(
            row["date"] != row["historical_date"] for row in result.values()
        ),
        "limit": "Bound derived schedule bytes; acquisition evidence is not reauthenticated here.",
    }


def _reconstruct_game(actions, gid, metadata, source_sha256):
    teams = {}
    for action in actions:
        code, value = action.get("teamTricode"), action.get("teamId")
        if code and value and str(value) != "0":
            number = float(value)
            if not number.is_integer() or number <= 0:
                raise ValueError("invalid source team metadata")
            team = int(number)
            if code in teams and teams[code] != team:
                raise ValueError("conflicting source team metadata")
            teams[code] = team
    try:
        home, away = teams[metadata["home"]], teams[metadata["away"]]
    except KeyError:
        raise ValueError(
            "source teams do not match explicit home/away metadata"
        ) from None
    return reconstruct(actions, gid, home, away, source_sha256)


def game_status(result):
    """Completeness is observed markers, independent of audit acceptance."""
    starts = Counter(
        e.period for e in result.events if e.kind == "period" and e.subtype == "start"
    )
    ends = Counter(
        e.period for e in result.events if e.kind == "period" and e.subtype == "end"
    )
    terminal = result.events[-1] if result.events else None
    complete = bool(
        terminal
        and terminal.kind == "game"
        and terminal.subtype == "end"
        and terminal.period >= 4
        and terminal.clock == 0
        and {e.period for e in result.events} == set(range(1, terminal.period + 1))
        and all(starts[p] == ends[p] == 1 for p in range(1, terminal.period + 1))
        and terminal.home_score is not None
        and terminal.away_score is not None
        and terminal.home_score != terminal.away_score
        and all(p.complete for p in result.possessions)
    )
    orphan = any(
        e.action_number in result.unassigned_action_numbers
        and e.classification != "administrative"
        for e in result.events
    )
    critical = bool(
        orphan
        or any(
            i.blocking and i.code != "independent_audit_required" for i in result.issues
        )
        or any(p.foul_indicator is None for p in result.possessions)
    )
    return {
        "complete": complete,
        "critical_unresolved": critical,
        "unassigned_control_events": orphan,
    }


def export(manifest, cache, metadata, schedule, output, limit_per_source=3):
    """Stream rows and exact canonical-list hash; preserve failure ledgers."""
    if type(limit_per_source) is not int or limit_per_source < 0:
        raise ValueError("nonnegative integer selection limit required")
    if output.exists():
        raise FileExistsError("output already exists; choose a new directory")
    historical, metadata_sources = metadata_rows(metadata)
    expected, schedule_binding = load_schedule(schedule, historical)
    output.mkdir(parents=True, exist_ok=False)
    verification = verify_sources(manifest, cache)
    feature_sha = feature_module_sha256()
    parser_sha = file_digest(Path(__file__).with_name("possessions.py"))[1]
    games, seen, failures, frame = {}, set(), [], []
    row_hash, row_count, unknown_count = hashlib.sha256(b"["), 0, 0
    missing = Counter()
    rows_path, provenance_path = output / "rows.jsonl", output / "row_provenance.jsonl"
    with (
        rows_path.open("x", encoding="utf-8") as row_stream,
        provenance_path.open("x", encoding="utf-8") as provenance,
    ):
        for source in verification["sources"]:
            name = source.get("source_file")
            if name not in OFFICIAL_ARCHIVES:
                continue
            if source["status"] != "verified":
                failures.append({"source_file": name, "error": "source not verified"})
                continue
            try:
                with verified_snapshot(
                    safe_path(cache, name),
                    source["expected_bytes"],
                    source["expected_sha256"],
                ) as snapshot:
                    selected = 0
                    for gid, actions, csv_rows, member in archive_games(snapshot):
                        if limit_per_source and selected >= limit_per_source:
                            break
                        selected += 1
                        if gid in seen:
                            raise ValueError("duplicate game across source archives")
                        seen.add(gid)
                        meta = expected.get(gid)
                        entry = {
                            "game_id": gid,
                            "source_file": name,
                            "source_sha256": source["expected_sha256"],
                            "source_member": member,
                            "parser_sha256": parser_sha,
                            "eligible": False,
                            "complete": False,
                            "critical_unresolved": True,
                            "row_count": 0,
                            "status": "quarantined",
                            "source_event_count": len(actions),
                        }
                        games[gid] = entry
                        try:
                            if meta is None:
                                raise ValueError(
                                    "source game absent from bound independent schedule"
                                )
                            entry.update(
                                {k: meta[k] for k in ("season", "game_type", "date")}
                            )
                            if (meta["season"], meta["game_type"]) != OFFICIAL_ARCHIVES[
                                name
                            ]:
                                raise ValueError("source/schedule cohort mismatch")
                            result = _reconstruct_game(
                                actions, gid, historical[gid], source["expected_sha256"]
                            )
                            rows = build_rows(result, meta)
                            entry.update(
                                game_status(result),
                                status="provisional_reconstruction",
                                row_count=len(rows),
                                unknown_outcomes=sum(
                                    row["outcome"] is None for row in rows
                                ),
                                issues=[asdict(issue) for issue in result.issues],
                                unassigned_action_numbers=list(
                                    result.unassigned_action_numbers
                                ),
                            )
                            for row, possession in zip(
                                rows, result.possessions, strict=True
                            ):
                                canonical = json.dumps(
                                    row,
                                    sort_keys=True,
                                    separators=(",", ":"),
                                    allow_nan=False,
                                )
                                if row_count:
                                    row_hash.update(b",")
                                row_hash.update(canonical.encode())
                                row_stream.write(canonical + "\n")
                                provenance.write(
                                    json.dumps(
                                        {
                                            "game_id": gid,
                                            "possession_number": possession.possession_number,
                                            "source_rows": [
                                                csv_rows[index]
                                                for index in possession.source_rows
                                            ],
                                            "event_action_numbers": possession.event_action_numbers,
                                            "reference_action_number": possession.start_state.reference_action_number,
                                            "complete": possession.complete,
                                            "audit_flags": possession.audit_flags,
                                        },
                                        sort_keys=True,
                                        allow_nan=False,
                                    )
                                    + "\n"
                                )
                                row_count += 1
                                unknown_count += row["outcome"] is None
                                missing.update(
                                    key for key, value in row.items() if value is None
                                )
                        except (ValueError, TypeError, KeyError, OverflowError) as exc:
                            entry.update(
                                status="quarantined",
                                complete=False,
                                critical_unresolved=True,
                                error=str(exc),
                            )
                        if meta is not None:
                            frame.append({key: entry[key] for key in SOURCE_KEYS})
            except (ValueError, OSError, EOFError, csv.Error, tarfile.TarError) as exc:
                failures.append({"source_file": name, "error": str(exc)})
                for entry in games.values():
                    if entry["source_file"] == name:
                        entry.update(
                            status="quarantined",
                            complete=False,
                            critical_unresolved=True,
                            error="source iteration failed; emitted rows remain provisional",
                        )
    row_hash.update(b"]")
    for gid, meta in expected.items():
        if gid not in games:
            games[gid] = {
                "game_id": gid,
                **{k: meta[k] for k in ("date", "season", "game_type")},
                "eligible": False,
                "complete": False,
                "critical_unresolved": True,
                "row_count": 0,
                "source_sha256": None,
                "parser_sha256": parser_sha,
                "status": "not_selected" if limit_per_source else "missing_source_game",
            }
    if (
        feature_module_sha256() != feature_sha
        or file_digest(Path(__file__).with_name("possessions.py"))[1] != parser_sha
    ):
        failures.append({"error": "feature or parser module changed during export"})
    packet = {
        "schema_version": "provisional-feature-dataset-v1",
        "status": "PROVISIONAL_AUDIT_BLOCKED",
        "feature_version": FEATURE_VERSION,
        "feature_sha256": feature_sha,
        "parser_version": PARSER_VERSION,
        "parser_sha256": parser_sha,
        "plan_sha256": None,
        "frame_sha256": digest(sorted(frame, key=lambda game: game["game_id"])),
        "frame": sorted(frame, key=lambda game: game["game_id"]),
        "rows_sha256": row_hash.hexdigest(),
        "rows_file_sha256": file_digest(rows_path)[1],
        "row_provenance_sha256": file_digest(provenance_path)[1],
        "rows_file": rows_path.name,
        "row_provenance_file": provenance_path.name,
        "row_count": row_count,
        "unknown_outcomes": unknown_count,
        "missing_fields": dict(sorted(missing.items())),
        "games": sorted(games.values(), key=lambda game: game["game_id"]),
        "source_map": {
            s["source_file"]: s["expected_sha256"]
            for s in verification["sources"]
            if s.get("source_file") in OFFICIAL_ARCHIVES and s["status"] == "verified"
        },
        "source_verification": verification,
        "historical_metadata": metadata_sources,
        "schedule_binding": schedule_binding,
        "source_failures": failures,
        "eligible_games": 0,
        "selection": {
            "limit_per_source": limit_per_source,
            "method": "all" if not limit_per_source else "first_per_source_diagnostic",
        },
        "ok": verification["ok"]
        and not failures
        and bool(seen)
        and (bool(limit_per_source) or seen == set(expected)),
        "limitations": "Retrospective source control; no verified live availability, independent audit, eligible rows, frozen protocol or model authorization.",
    }
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(packet, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "cache", "schedule", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--metadata", nargs="+", type=Path, required=True)
    parser.add_argument("--limit-per-source", type=int, default=3)
    args = parser.parse_args(argv)
    result = export(
        args.manifest,
        args.cache,
        args.metadata,
        args.schedule,
        args.output,
        args.limit_per_source,
    )
    print(
        json.dumps(
            {
                "ok": result["ok"],
                "games": len(result["games"]),
                "rows": result["row_count"],
                "unknown_outcomes": result["unknown_outcomes"],
                "eligible_games": 0,
                "status": result["status"],
            }
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
