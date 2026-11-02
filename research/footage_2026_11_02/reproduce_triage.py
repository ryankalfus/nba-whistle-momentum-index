"""Reproduce the frozen v1 triage offline, without importing the current parser.

Run with the project .venv. Archive and metadata bytes are verified before use.
No possession metric, model evaluation, scientific eligibility or clock repair.
"""

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import types


BASELINE_SHA256 = "a0fc53a3389002d79affef35300ce76f12a7fe058621d6231d35b0676a45743a"
BASELINE_COMMIT = "618d480eb7f97781515907452e5d43ab4b7f9a57"
ADMIN = {
    "substitution", "timeout", "instantreplay", "replay", "game", "period",
    "stoppage", "block", "ejection",
}


def read_json(path):
    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(path.read_text(), parse_constant=reject_constant)


def load_baseline(path, evidence):
    """Execute only the verified bytes, registering dataclasses' owning module."""
    raw = path.read_bytes()
    if evidence["parser_sha256"] != BASELINE_SHA256:
        raise ValueError("Evidence does not name the frozen baseline parser")
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError(f"Baseline parser SHA256 mismatch; obtain {BASELINE_COMMIT}")
    name = "nba_whistle_triage_baseline_" + BASELINE_SHA256[:16]
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
    except BaseException:
        del sys.modules[name]
        raise
    if module.PARSER_VERSION != "canonical_candidate_v1":
        raise ValueError("Unexpected baseline parser version")
    return module


def canonical_game_id(value):
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", value):
        raise ValueError(f"Invalid game ID: {value!r}")
    return value.zfill(10)


@contextmanager
def verified_snapshot(path, expected):
    """Hash the same immutable snapshot that is subsequently streamed."""
    digest, size = hashlib.sha256(), 0
    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as snapshot:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                snapshot.write(block)
                digest.update(block)
                size += len(block)
        if size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
            raise ValueError(f"Source size/SHA256 mismatch: {path.name}")
        snapshot.seek(0)
        yield snapshot


def archive_games(stream):
    """Yield one contiguous game; preserve CSV row IDs and missing-value policy."""
    seen = set()
    with tarfile.open(fileobj=stream, mode="r|xz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(".csv"):
                continue
            with archive.extractfile(member) as raw:
                reader = csv.DictReader(line.decode("utf-8-sig") for line in raw)
                fields = reader.fieldnames
                if not fields or len(fields) != len(set(fields)) or "gameId" not in fields:
                    raise ValueError("Invalid/duplicate event CSV columns")
                current, records, source_rows = None, [], []
                for source_row, row in enumerate(reader, 2):
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("Malformed event CSV row")
                    gid = canonical_game_id(row["gameId"])
                    if current is not None and current != gid:
                        yield current, records, source_rows, member.name
                        seen.add(current)
                        records, source_rows = [], []
                    if gid in seen:
                        raise ValueError("Noncontiguous/duplicate game in source")
                    current = gid
                    records.append({
                        key: None if value in {"", "NA", "NaN", "nan"} else value
                        for key, value in row.items()
                    })
                    source_rows.append(source_row)
                if current is not None:
                    yield current, records, source_rows, member.name
                    seen.add(current)


def metadata_rows(root, sources):
    """Use hash-pinned historical home/away metadata, never an inferred schedule."""
    result = {}
    for source in sources:
        raw = (root / source["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError(f"Metadata SHA256 mismatch: {source['file']}")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Invalid metadata columns")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed metadata row")
            gid = canonical_game_id(row["game_id"])
            if gid in result or not row.get("home") or not row.get("away"):
                raise ValueError("Duplicate/incomplete game metadata")
            result[gid] = row
    return result


def reconstruct_game(baseline, actions, gid, metadata, source_sha256):
    teams = {}
    for action in actions:
        code, tid = action.get("teamTricode"), action.get("teamId")
        if code and tid and str(tid) != "0":
            numeric = float(tid)
            if not numeric.is_integer():
                raise ValueError("noninteger team metadata")
            tid = int(numeric)
            if code in teams and teams[code] != tid:
                raise ValueError("conflicting source team metadata")
            teams[code] = tid
    try:
        home, away = teams[metadata["home"]], teams[metadata["away"]]
    except KeyError:
        raise ValueError("source teams do not match declared home/away metadata") from None
    return baseline.reconstruct(actions, gid, home, away, source_sha256)


def clock(action):
    match = re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", action["clock"])
    if not match:
        raise ValueError("Malformed clock while diagnosing quarantine")
    return int(match[1]) * 60 + float(match[2])


def label(action):
    return "/".join(str(action.get(key) or "") for key in ("actionType", "subType"))


def signature(action):
    return tuple(action.get(key) or "<missing>" for key in ("subType", "qualifiers", "descriptor"))


def predecessor_candidate(action):
    # Reproduce the recorded raw-label adjacency rule, not a live-control claim.
    return action["actionType"] not in ADMIN and not (
        action["actionType"] == "foul"
        and action["subType"] in {"technical", "double technical"}
    )


def regression_class(action):
    administrative = action["actionType"] in ADMIN | {"memo"} or (
        action["actionType"] == "foul"
        and action["subType"] in {"technical", "double technical"}
    )
    return "administrative_or_unsupported_memo_row" if administrative else "control_classified_row"


def compare(actual, expected, name):
    if actual != expected:
        raise ValueError(f"Baseline reproduction differs from compact evidence: {name}")


def reproduce(args, evidence, baseline):
    metadata = metadata_rows(args.root, evidence["reproduction_metadata_sources"])
    subtypes, signatures, raw_signatures, transfers = Counter(), Counter(), Counter(), Counter()
    regression_types, regression_contexts = Counter(), Counter()
    games, quarantines, regression_refs, unknown_refs = [], [], [], []
    seen_games, control_rise_games = set(), set()
    reordered = raw_quarantined = 0
    for source in evidence["source_verification"]:
        name = source["source_file"]
        if Path(name).name != name:
            raise ValueError("Archive name must be a basename")
        print("SCANNING", name, flush=True)
        with verified_snapshot(args.cache / name, source) as snapshot:
            for gid, actions, csv_rows, member in archive_games(snapshot):
                if gid in seen_games:
                    raise ValueError(f"Duplicate game across archives: {gid}")
                seen_games.add(gid)
                pairs = sorted(zip(actions, csv_rows), key=lambda pair: (
                    float(pair[0]["orderNumber"]), float(pair[0]["actionNumber"]),
                ))
                ordered = [action for action, _ in pairs]
                reordered += actions != ordered
                result, error = None, None
                try:
                    if gid not in metadata:
                        raise ValueError("missing declared home/away metadata")
                    result = reconstruct_game(baseline, actions, gid, metadata[gid], source["sha256"])
                except (ValueError, TypeError, KeyError) as exc:
                    error = str(exc)
                game = {"game_id": gid, "source_file": name, "status": (
                    "quarantined" if error is not None else "candidate_diagnostic_only"
                ), "error": error, "eligible": False}
                games.append(game)
                if error is not None:
                    quarantines.append(game)
                action_indices = {int(float(action["actionNumber"])): i
                                  for i, action in enumerate(ordered)}
                issue_codes = {} if result is None else {
                    (issue.code, issue.action_number) for issue in result.issues
                }
                for i, (action, csv_row) in enumerate(pairs):
                    ref = {
                        "game_id": gid, "source_file": name,
                        "source_sha256": source["sha256"],
                        "action_number": action["actionNumber"], "csv_row": csv_row,
                    }
                    if action["actionType"] == "violation":
                        raw_signatures[signature(action)] += 1
                        if error is not None:
                            raw_quarantined += 1
                        elif ("violation_requires_audit", int(float(action["actionNumber"]))) in issue_codes:
                            subtypes[action["subType"]] += 1
                            signatures[signature(action)] += 1
                        elif not action.get("possession") or not float(action["possession"]):
                            unknown_refs.append({**ref, "subtype": action["subType"]})
                    if error is not None and i:
                        prev = ordered[i - 1]
                        if int(action["period"]) < int(prev["period"]) or (
                            action["period"] == prev["period"] and clock(action) > clock(prev)
                        ):
                            context = regression_class(action)
                            regression_contexts[context] += 1
                            regression_types[action["actionType"]] += 1
                            if context == "control_classified_row":
                                control_rise_games.add(gid)
                            regression_refs.append({
                                **ref, "clock_increase_seconds": round(clock(action) - clock(prev), 3),
                                "period": action["period"], "previous_label": label(prev),
                                "current_label": label(action), "previous_period": prev["period"],
                            })
                if result is not None:
                    for issue in result.issues:
                        if issue.code == "unexplained_control_transfer":
                            i = action_indices[issue.action_number]
                            prev = next((action for action in reversed(ordered[:i])
                                         if predecessor_candidate(action)), {})
                            transfers[label(prev) + " -> " + label(ordered[i])] += 1
    compare(len(games), evidence["games_seen"], "game count")
    compare(len(quarantines), evidence["quarantined_games"], "quarantined game count")
    compare(len(games) - len(quarantines), evidence["reconstructed_games"], "reconstructed games")
    compare(reordered, evidence["games_reordered_by_existing_canonical_source_order"], "source order")
    compare(dict(subtypes), evidence["violation_subtypes"], "flagged violation subtypes")
    expected_signatures = {(row["subtype"], row["qualifiers"], row["descriptor"]): row["count"]
                           for row in evidence["violation_signatures"]}
    compare(dict(signatures), expected_signatures, "flagged violation qualifier signatures")
    expected_raw = {(row["subtype"], row["qualifiers"], row["descriptor"]): row["count"]
                    for row in evidence["violation_signatures_including_quarantines"]}
    compare(dict(raw_signatures), expected_raw, "all raw violation signatures")
    compare(dict(transfers), evidence["transfer_adjacent_nonadministrative_signatures"], "transfer signatures")
    compare(sum(subtypes.values()), evidence["flagged_violation_count"], "violation total")
    compare(sum(transfers.values()), evidence["unexplained_transfer_count"], "transfer total")
    compare(sum(raw_signatures.values()), evidence["raw_violations_including_quarantines"], "raw violations")
    expected_quarantines = {row["game_id"]: row["reported_error"]
                            for row in evidence["quarantined_game_regressions"]}
    compare({row["game_id"]: row["error"] for row in quarantines}, expected_quarantines, "quarantine identities/errors")
    summary = evidence["clock_regression_summary"]
    compare(len(regression_refs), summary["adjacent_rises"], "clock rises")
    compare(dict(regression_types), summary["current_action_type_counts"], "clock-rise labels")
    compare(dict(regression_contexts), summary["diagnostic_context_counts"], "clock-rise contexts")
    compare(len(control_rise_games), summary["games_with_any_control_classified_rise"], "control-rise games")
    compare(all(row["period"] == row["previous_period"] for row in regression_refs), summary["all_same_period"], "same-period rises")
    deltas = [row["clock_increase_seconds"] for row in regression_refs]
    compare([min(deltas), max(deltas)], summary["rise_seconds_range"], "clock-rise range")
    ref_keys = ("game_id", "source_file", "source_sha256", "action_number", "csv_row",
                "clock_increase_seconds", "period", "previous_label", "current_label")
    expected_refs = [row for game in evidence["quarantined_game_regressions"] for row in game["regressions"]]
    compare(sorted(tuple(row[key] for key in ref_keys) for row in regression_refs),
            sorted(tuple(row[key] for key in ref_keys) for row in expected_refs), "all regression references")
    accounting = evidence["denominator_accounting"]
    compare(raw_quarantined, accounting["violation_rows_in_quarantined_games"], "quarantined violations")
    compare(len(unknown_refs), accounting["violation_rows_in_reconstructed_games_without_owner_so_unknown_ownership_not_violation_flag"], "unknown-owner violations")
    compare(dict(Counter(row["subtype"] for row in unknown_refs)), accounting["unknown_owner_raw_subtypes"], "unknown-owner subtypes")
    return {
        "schema_version": "baseline-triage-reproduction-v1", "matches_compact_evidence": True,
        "parser_sha256": BASELINE_SHA256, "baseline_commit": BASELINE_COMMIT,
        "parser_version": baseline.PARSER_VERSION, "python_version": sys.version,
        "source_verification": evidence["source_verification"],
        "metadata_sources": evidence["reproduction_metadata_sources"],
        "game_classifications": games, "games_seen": len(games),
        "reconstructed_games": len(games) - len(quarantines), "quarantined_games": len(quarantines),
        "violation_subtypes": dict(subtypes), "flagged_violation_count": sum(subtypes.values()),
        "unexplained_transfer_count": sum(transfers.values()), "transfer_signatures": dict(transfers),
        "regression_references": regression_refs,
        "independent_audit_status": "blocked", "eligible_games": 0,
        "interpretation": "Baseline implementation reproduction, not independent scientific validation.",
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--baseline-parser", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    cli.add_argument("--cache", type=Path)
    args = cli.parse_args()
    if args.output.exists():
        cli.error("Refusing existing output; choose a new path")
    if not args.output.parent.is_dir():
        cli.error("Output parent must be an existing directory")
    args.cache = args.cache or args.root / "research/hypotheses_2026_09_12/cache"
    evidence_path = Path(__file__).with_name("parser_triage.json")
    evidence = read_json(evidence_path)
    baseline = load_baseline(args.baseline_parser, evidence)
    result = reproduce(args, evidence, baseline)
    result["compact_evidence_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS: 6084 games / 5999 reconstructed / 85 quarantined / "
          "10347 violation flags / 2780 transfer flags / 91 clock rises; compact evidence matches")


if __name__ == "__main__":
    main()
