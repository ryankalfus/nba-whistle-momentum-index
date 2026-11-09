"""Source-bound exploratory selection; never promotion or scientific approval."""

from collections import Counter
from datetime import date
from itertools import zip_longest
from pathlib import Path
import re

from whistle_research import audit, modeling, release, sources

MAX_ROWS = 250_000
STATUS = "PROVISIONAL_NOT_INDEPENDENTLY_VALIDATED"
SPLIT_KEYS = ("train_start", "tune_start", "test_start", "test_end")


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("split and game dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def _selection(plan):
    cohort, split = plan.get("cohort"), plan.get("split")
    if (not isinstance(cohort, dict) or set(cohort) != {"season", "game_type"}
            or not isinstance(cohort["season"], str)
            or not re.fullmatch(r"\d{4}-\d{2}", cohort["season"])
            or int(cohort["season"][-2:]) != (int(cohort["season"][:4]) + 1) % 100
            or cohort["game_type"] not in {"regular_season", "playoffs"}):
        raise ValueError("exact season/game_type cohort required")
    if not isinstance(split, dict) or set(split) != set(SPLIT_KEYS):
        raise ValueError("four exact split dates required")
    dates = [_date(split[key]) for key in SPLIT_KEYS]
    if not all(a < b for a, b in zip(dates, dates[1:])):
        raise ValueError("split dates must be strictly increasing")
    return dict(cohort), dict(split)


def _partition(game, cohort, split):
    # Validate even excluded metadata instead of letting lexical comparisons hide it.
    _date(game["date"])
    if game["game_type"] not in {"regular_season", "playoffs"}:
        raise release.ArtifactError("unknown game type")
    season = game["season"]
    if (not isinstance(season, str) or not re.fullmatch(r"\d{4}-\d{2}", season)
            or int(season[-2:]) != (int(season[:4]) + 1) % 100):
        raise release.ArtifactError("unknown game season")
    if any(game[key] != value for key, value in cohort.items()):
        return None, "outside_cohort"
    if not split["train_start"] <= game["date"] < split["test_end"]:
        return None, "outside_date_range"
    if game["date"] < split["tune_start"]:
        return "train", None
    return ("tune" if game["date"] < split["test_start"] else "test"), None


def _snapshot(role, path):
    path = Path(path)
    before = sources.file_identity(path.stat())
    size, sha = sources.file_digest(path)
    if before != sources.file_identity(path.stat()):
        raise release.ArtifactError("input changed while hashing")
    return {"role": role, "path": path, "bytes": size, "sha256": sha}, before


def _quality(game, diagnostic):
    reasons = []
    if game["status"] != "provisional_reconstruction":
        reasons.append("not_reconstructed")
    if game.get("complete") is not True:
        reasons.append("game_incomplete")
    if game.get("critical_unresolved") is not False:
        reasons.append("critical_unresolved")
    if not game.get("row_count"):
        reasons.append("no_rows")
    if game.get("unknown_outcomes", 0):
        reasons.append("unknown_target")
    if game.get("unassigned_control_events") is not False:
        reasons.append("unassigned_control_events")
    if any(type(game.get(key)) is not bool for key in
           ("complete", "critical_unresolved", "unassigned_control_events")):
        reasons.append("unknown_quality_metadata")
    if game["status"] == "provisional_reconstruction" and any(
            type(diagnostic.get(key)) is not bool
            for key in ("full_game_markers", "unassigned_control_events")):
        if "unknown_quality_metadata" not in reasons:
            reasons.append("unknown_quality_metadata")
    issues = game.get("issues")
    if (not isinstance(issues, list) or any(
            not isinstance(issue, dict) or not audit.text(issue.get("code"))
            or type(issue.get("blocking")) is not bool for issue in issues)):
        reasons.append("undocumented_issues")
    else:
        if any(issue["blocking"] and issue["code"] != "independent_audit_required"
               for issue in issues):
            reasons.append("blocking_issue")
        expected = diagnostic.get("issues")
        if not isinstance(expected, dict):
            reasons.append("unknown_reconciliation_issues")
        elif dict(Counter(issue["code"] for issue in issues)) != expected:
            raise release.ArtifactError("reconciliation/feature issue accounting mismatch")
    return reasons


def _boolean(value):
    """Malformed quality values remain unknown, never truthy or report text."""
    return value if type(value) is bool else None


def prepare_cohort(*, feature_dir, inventory_path, reconciliation_path,
                   source_manifest, cache, schedule, metadata, plan):
    """Verify the whole frame, then retain only whole selected games in memory.

    No files are written. ``inputs`` contains internal paths for the caller's
    portable catalog; the report deliberately contains no filesystem paths.
    ``recheck`` hashes the same inputs again immediately before caller output.
    Split intervals are left-closed and right-open, including test_end.
    """
    cohort, split = _selection(plan)
    feature_dir, cache = Path(feature_dir), Path(cache)
    metadata = [Path(path) for path in metadata]
    if len({path.name for path in metadata}) != len(metadata):
        raise release.ArtifactError("duplicate metadata filenames")
    paths = [("source_manifest", Path(source_manifest)), ("inventory", Path(inventory_path)),
             ("reconciliation", Path(reconciliation_path)), ("schedule", Path(schedule)),
             ("feature_manifest", feature_dir / "manifest.json")]
    paths.extend((f"metadata_{index}", path) for index, path in enumerate(metadata))
    # Include the verifier/parser dependency code, without retaining source bytes.
    paths.extend((f"code_{path.stem}", path) for path in sorted(Path(__file__).parent.glob("*.py")))
    inputs, identities = [], []

    def track(role, path):
        entry, identity = _snapshot(role, path)
        inputs.append(entry)
        identities.append(identity)

    for role, path in paths:
        track(role, path)
    source_entries = release.read_json(source_manifest)
    if not isinstance(source_entries, list):
        raise release.ArtifactError("source manifest must be a list")
    for index, entry in enumerate(source_entries):
        track(f"raw_source_{index}", sources.safe_path(cache, entry["file"]))
    initial_manifest = release.read_json(feature_dir / "manifest.json")
    row_path = sources.safe_path(feature_dir, initial_manifest["rows_file"])
    provenance_path = sources.safe_path(feature_dir, initial_manifest["row_provenance_file"])
    track("feature_rows", row_path)
    track("feature_provenance", provenance_path)

    def recheck():
        for entry, identity in zip(inputs, identities, strict=True):
            current, current_identity = _snapshot(entry["role"], entry["path"])
            if current != entry or current_identity != identity:
                raise release.ArtifactError("consumed input or implementation changed")

    verification = sources.verify_sources(Path(source_manifest), cache)
    inventory = release.read_json(inventory_path)
    frame = release.verify_inventory(inventory, verification, Path(schedule))
    reconciliation = release.read_json(reconciliation_path)
    release.verify_reconciliation(reconciliation, verification, frame, metadata)
    dataset, stream = release.verify_feature_export(
        feature_dir, verification, Path(schedule), metadata, frame)
    diagnostics = {game["game_id"]: game for game in reconciliation["games"]}
    inventory_games = {game["game_id"]: game for game in inventory["games"]}
    ledger = {}
    for game in dataset["games"]:
        gid = game["game_id"]
        diagnostic = diagnostics[gid]
        if diagnostic.get("eligible") is not False:
            raise release.ArtifactError("manually altered reconciliation eligibility")
        if any(type(game.get(key)) is not int or game[key] < 0
               for key in ("row_count", "source_event_count")):
            raise release.ArtifactError("invalid per-game row/event accounting")
        if (game["row_count"] != diagnostic.get("candidate_possessions", 0)
                or game.get("source_event_count") != inventory_games[gid]["event_count"]
                or game.get("source_event_count") != diagnostic.get("source_event_count")
                or (game["status"] == "quarantined") != (diagnostic["status"] == "quarantined")):
            raise release.ArtifactError("inventory/reconciliation/feature per-game accounting mismatch")
        if diagnostic["status"] not in {"quarantined", "candidate_diagnostic_only"}:
            raise release.ArtifactError("unknown reconciliation status")
        if game["status"] == "provisional_reconstruction":
            if diagnostic.get("unassigned_control_events") != game.get("unassigned_control_events"):
                raise release.ArtifactError("reconciliation/feature quality accounting mismatch")
        sources.safe_path(cache, game["source_member"])
        partition, outside = _partition(game, cohort, split)
        reasons = _quality(game, diagnostic)
        if outside:
            reasons.insert(0, outside)
        ledger[gid] = {
            **{key: game[key] for key in (*audit.SOURCE_KEYS, "date")},
            "eligible": False, "scientific_approval": False,
            "candidate": partition is not None, "partition": partition,
            "selected_for_exploration": False, "reasons": reasons,
            "row_count": game["row_count"], "unknown_outcomes": game.get("unknown_outcomes", 0),
            "source_event_count": game.get("source_event_count"),
            "original_status": game["status"] if game["status"] in {
                "provisional_reconstruction", "quarantined", "not_selected", "missing_source_game"} else "unknown",
            "complete": _boolean(game.get("complete")),
            "critical_unresolved": _boolean(game.get("critical_unresolved")),
            "unassigned_control_events": _boolean(game.get("unassigned_control_events")),
            "unassigned_action_numbers": game.get("unassigned_action_numbers"),
            "issue_counts": diagnostic.get("issues"),
            "missing_fields": {}, "incomplete_provenance_rows": 0, "flagged_provenance_rows": 0,
            "uncertain_rows": 0,
        }
    # A separate pass is necessary: row-level flags can exclude an entire game.
    # Retain prospective rows only; never materialize other seasons' rows.
    selected, missing = {}, {gid: Counter() for gid in ledger}
    retained = 0
    with row_path.open("r", encoding="utf-8") as rows, provenance_path.open("r", encoding="utf-8") as traces:
        for raw, raw_trace in zip_longest(rows, traces):
            if raw is None or raw_trace is None:
                raise release.ArtifactError("row/provenance stream lengths differ")
            row, trace = modeling._strict_json(raw), modeling._strict_json(raw_trace)
            game = ledger[row["game_id"]]
            if (trace.get("game_id"), trace.get("possession_number")) != (row["game_id"], row["possession_number"]):
                raise release.ArtifactError("row/provenance identity changed")
            missing[row["game_id"]].update(key for key, value in row.items() if value is None)
            for flag, reason in ((trace["complete"] is not True, "incomplete_row_provenance"),
                                 (bool(trace["audit_flags"]), "flagged_row_provenance")):
                if flag and reason not in game["reasons"]:
                    game["reasons"].append(reason)
            game["incomplete_provenance_rows"] += trace["complete"] is not True
            game["flagged_provenance_rows"] += bool(trace["audit_flags"])
            game["uncertain_rows"] += row["outcome"] is None or trace["complete"] is not True
            if game["reasons"]:
                retained -= len(selected.pop(row["game_id"], []))
            else:
                retained += 1
                if retained > MAX_ROWS:
                    raise release.ArtifactError("exploratory row capacity exceeded; never truncated")
                selected.setdefault(row["game_id"], []).append(row)
    result_rows = sorted((row for block in selected.values() for row in block),
                         key=lambda row: (row["date"], row["game_id"], row["possession_number"]))
    counts, primary, partitions = Counter(), Counter(), {}
    partition_missing = {part: Counter() for part in ("train", "tune", "test")}
    for gid, game in ledger.items():
        diagnostic = diagnostics[gid]
        if diagnostic["status"] == "candidate_diagnostic_only":
            if diagnostic.get("uncertain_possessions") != game["uncertain_rows"]:
                raise release.ArtifactError("reconciliation/feature uncertain-row accounting mismatch")
            if (type(game["complete"]) is bool and type(diagnostic.get("full_game_markers")) is bool
                    and game["complete"] != (
                    diagnostic.get("full_game_markers") is True and not game["incomplete_provenance_rows"])):
                raise release.ArtifactError("reconciliation/feature completion accounting mismatch")
        game["missing_fields"] = dict(sorted(missing[gid].items()))
        game["selected_for_exploration"] = gid in selected
        if game["candidate"] and game["reasons"]:
            counts.update(game["reasons"])
            primary.update(game["reasons"][:1])
        if game["selected_for_exploration"]:
            partition_missing[game["partition"]].update(missing[gid])
    for partition in partition_missing:
        games = [game for game in ledger.values() if game["partition"] == partition]
        included = [game for game in games if game["selected_for_exploration"]]
        partitions[partition] = {"candidate_games": len(games), "included_games": len(included),
                                 "excluded_games": len(games) - len(included),
                                 "rows": sum(game["row_count"] for game in included),
                                 "missing_fields": dict(sorted(partition_missing[partition].items()))}
    candidates = sum(game["candidate"] for game in ledger.values())
    report = {
        "schema_version": "provisional-exploratory-cohort-v1", "status": STATUS,
        "eligible": False, "scientific_approval": False, "publication_authorized": False,
        "evaluation_exposure": "retrospective_previously_exposed", "cohort": cohort, "split": split,
        "counts": {"full_frame_games": len(frame), "full_frame_rows": stream["rows"],
                   "full_frame_unknown_outcomes": stream["unknown_outcomes"],
                   "candidate_games": candidates, "included_games": len(selected),
                   "excluded_games": candidates - len(selected), "included_rows": len(result_rows),
                   "candidate_rows": sum(game["row_count"] for game in ledger.values() if game["candidate"]),
                   "candidate_unknown_outcomes": sum(game["unknown_outcomes"] for game in ledger.values()
                                                     if game["candidate"]),
                   "excluded_rows": sum(game["row_count"] for game in ledger.values()
                                        if game["candidate"] and not game["selected_for_exploration"]),
                   "out_of_cohort_games": len(frame) - candidates},
        "exclusion_reason_counts": dict(sorted(counts.items())),
        "primary_exclusion_reason_counts": dict(sorted(primary.items())),
        "source_frame": {"games": len(frame), "rows": stream["rows"],
                         "out_of_cohort_game_ids": [gid for gid, game in sorted(ledger.items()) if not game["candidate"]]},
        "games": list(sorted(ledger.values(), key=lambda game: game["game_id"])),
        "partitions": partitions, "rows_sha256": modeling.row_digest(result_rows),
        "source_map": dataset["source_map"], "source_manifest_sha256": verification["manifest_sha256"],
        "frame_sha256": dataset["frame_sha256"],
        **{key: dataset[key] for key in ("parser_version", "parser_sha256", "feature_version", "feature_sha256")},
        "original_rows_sha256": dataset["rows_sha256"],
        "selection_is_scientific_eligibility": False,
        "unassigned_event_policy": "Explicit administrative unassigned references are retained; unassigned_control_events must be exactly false.",
    }
    recheck()
    return {"rows": result_rows, "report": report, "inputs": inputs, "recheck": recheck}
