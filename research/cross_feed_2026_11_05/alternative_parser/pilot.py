"""Offline fixed-pilot comparison; no fetching, event corrections or model use."""

import argparse
from collections import Counter
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import socket
import sys
import tarfile
import traceback
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

VERSION = "pbpstats-1.3.11-mobile-pilot-v1"
WHEEL_SHA256 = "bf25d508e0956f8b5c5055e85b2d35d9259677e2b62410ce1121eb4d0f6683a0"
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
# Capture project sources before importing or calling their implementation.
CODE_BYTES = {path: path.read_bytes() for path in [
    Path(__file__).resolve(), ROOT / "src/whistle_research/feed_compare.py",
    ROOT / "src/whistle_research/reconcile.py"]}

from whistle_research.feed_compare import compare_pair  # noqa: E402 - snapshot before import
from whistle_research.reconcile import verified_snapshot  # noqa: E402 - snapshot before import


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record_consumed(fingerprints, path, raw):
    """Fingerprint the supplied consumed bytes, never a later path reopening."""
    fingerprints[path] = hashlib.sha256(raw).hexdigest()


def verify_no_drift(fingerprints):
    """Fail before publishing evidence if a consumed input/source changed."""
    for path, expected in fingerprints.items():
        if digest(path) != expected:
            raise ValueError("Consumed input/source changed during run: " + path.name)


def wrap_rows(rows):
    """Preserve every CSV field; restore only etype's required integer type."""
    periods = []
    for row in rows:
        period = int(row["PERIOD"])
        if not periods or periods[-1]["p"] != period:
            if any(item["p"] == period for item in periods):
                raise ValueError("Noncontiguous period in original archive order")
            periods.append({"p": period, "pla": []})
        event = dict(row)
        event["etype"] = int(event["etype"])
        if str(event["etype"]) != row["etype"]:
            raise ValueError("Non-lossless etype conversion")
        periods[-1]["pla"].append(event)
    return {"g": {"pd": periods}}


def verify_wheel(wheel, unpacked):
    if digest(wheel) != WHEEL_SHA256:
        raise ValueError("Unverified pbpstats wheel")
    sources = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith("pbpstats/") and name.endswith(".py"):
                content = archive.read(name)
                if (unpacked / name).read_bytes() != content:
                    raise ValueError(f"Installed source differs from wheel: {name}")
                sources[name] = hashlib.sha256(content).hexdigest()
    actual = {str(p.relative_to(unpacked)) for p in (unpacked / "pbpstats").rglob("*.py")}
    if actual != set(sources):
        raise ValueError("Unexpected installed pbpstats sources")
    return sources


def blocked_network(*args, **kwargs):
    raise RuntimeError("OFFLINE_POLICY: parser network request blocked")


def verify_assignment(input_rows, boundaries):
    original = [int(row["evt"]) for row in input_rows]
    assigned = [event for boundary in boundaries for event in boundary["event_nums"]]
    if len(set(original)) != len(original):
        raise ValueError("Duplicate source event IDs")
    if assigned != original:
        raise ValueError("Parser dropped, duplicated, injected or reordered events")


def boundary_comparison(cdn_rows, mobile_rows, candidate, alternative):
    cdn = {}
    mobile = {}
    for row in cdn_rows:
        cdn.setdefault(int(row["actionNumber"]), []).append(row)
    for row in mobile_rows:
        mobile.setdefault(int(row["evt"]), []).append(row)
    identities = {}
    for number in set(cdn) | set(mobile):
        if len(cdn.get(number, [])) != 1 or len(mobile.get(number, [])) != 1:
            identities[number] = {"status": "absent_or_duplicate_id"}
            continue
        evidence = compare_pair(cdn[number][0], mobile[number][0])
        comparable = bool(evidence["corroboration"]) and not (
            {"clock", "period"} & (set(evidence.get("differing_fields", []))
                                   | set(evidence.get("unknown_fields", []))))
        identities[number] = dict(evidence, comparable=comparable)
    left = {p["last_action_number"] for p in candidate}
    right = {p["last_event_num"] for p in alternative}
    comparable = {n for n, evidence in identities.items() if evidence.get("comparable")}
    groups = {"shared": sorted(left & right & comparable),
              "canonical_only": sorted((left - right) & comparable),
              "alternative_only": sorted((right - left) & comparable),
              "canonical_uncomparable": sorted(left - comparable),
              "alternative_uncomparable": sorted(right - comparable)}
    details = []
    cdn_fields = ["actionNumber", "clock", "period", "orderNumber", "timeActual", "actionType", "subType", "description"]
    mobile_fields = ["evt", "cl", "PERIOD", "ord", "wallclk", "etype", "mtype", "de"]
    for category in ["canonical_only", "alternative_only", "canonical_uncomparable", "alternative_uncomparable"]:
        for number in groups[category]:
            details.append({"category": category, "event_id": number,
                            "identity_evidence": identities.get(number, {"status": "absent_id"}),
                            "cdn_raw_fields": [{k: row.get(k) for k in cdn_fields} for row in cdn.get(number, [])],
                            "mobile_raw_fields": [{k: row.get(k) for k in mobile_fields} for row in mobile.get(number, [])]})
    return {"metric": "last_assigned_event_agreement; administrative attachment can differ without control changes",
            "counts": {key: len(value) for key, value in groups.items()},
            "event_ids": groups, "discrepancies": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mobile-cache", type=Path,
                        default=ROOT / "output/v2/cross-feed-pilot-inputs-2026-11-05")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new result path; existing evidence is immutable")
    fingerprints = {}
    for path, raw in CODE_BYTES.items():
        record_consumed(fingerprints, path, raw)
    verify_no_drift(fingerprints)
    package = args.package_dir.resolve()
    sources = verify_wheel(package / "pbpstats-1.3.11-py3-none-any.whl", package / "unpacked")
    sys.path.insert(0, str(package / "unpacked"))
    from pbpstats.data_loader import DataNbaPossessionLoader
    import pbpstats

    if Path(pbpstats.__file__).resolve() != package / "unpacked/pbpstats/__init__.py":
        raise ValueError("Unexpected imported pbpstats path")
    sample_path = ROOT / "research/parser_followthrough_2026_11_02/public_replays.json"
    manifest_path = ROOT / "research/hypotheses_2026_09_12/source_manifest.json"
    archive_path = manifest_path.parent / "cache/datanba_2024.tar.xz"
    canonical_dir = ROOT / "output/v2/features-v7-reviewed-2026-11-02"
    provenance_path = canonical_dir / "row_provenance.jsonl"
    canonical_manifest = canonical_dir / "manifest.json"
    pipeline = ROOT / "output/v2/development-pipeline-v7-2026-11-02"
    report_path = pipeline / "report.json"
    plan_path = pipeline / "audit_plan.json"
    report_bytes = report_path.read_bytes()
    record_consumed(fingerprints, report_path, report_bytes)
    report = json.loads(report_bytes)
    bound = {canonical_manifest: "feature_manifest", provenance_path: "feature_provenance",
             plan_path: "audit_plan", manifest_path: "source_manifest"}
    snapshots = {}
    for path, role in bound.items():
        record = report["artifacts"][role]
        snapshots[path] = (record["bytes"], record["sha256"])
        if path != provenance_path:
            with verified_snapshot(path, *snapshots[path]) as stream:
                snapshots[path] = stream.read()
                record_consumed(fingerprints, path, snapshots[path])
    feature_manifest = json.loads(snapshots[canonical_manifest])
    plan = json.loads(snapshots[plan_path])
    if feature_manifest["parser_version"] != "canonical_candidate_v7":
        raise ValueError("Wrong canonical parser version")
    if feature_manifest["row_provenance_sha256"] != snapshots[provenance_path][1]:
        raise ValueError("Canonical provenance binding mismatch")
    sample_bytes = sample_path.read_bytes()
    record_consumed(fingerprints, sample_path, sample_bytes)
    sample = json.loads(sample_bytes)["games"]
    if Counter(g["game_id"] for g in sample) != Counter(g["game_id"] for g in plan["games"]):
        raise ValueError("Replay sample differs from genuine audit plan")
    selected = sample
    ledger_path = HERE.parent / "pilot_mobile_sources.json"
    ledger_bytes = ledger_path.read_bytes()
    record_consumed(fingerprints, ledger_path, ledger_bytes)
    historical_sources = json.loads(snapshots[manifest_path])
    mobile_sources = json.loads(ledger_bytes)
    if isinstance(mobile_sources, dict):
        mobile_sources = mobile_sources["sources"]
    entries = {x["file"]: x for x in historical_sources}
    for entry in mobile_sources:
        if entry["file"] in entries and entry["sha256"] != entries[entry["file"]]["sha256"]:
            raise ValueError("Diagnostic ledger conflicts with historical manifest")
        entries[entry["file"]] = entry
    planned = {g["game_id"]: g for g in plan["games"]}
    frame = {g["game_id"]: g for g in feature_manifest["frame"]}
    for game in selected:
        gid = game["game_id"]
        for key in ["season", "source_file", "source_sha256"]:
            if planned[gid][key] != frame[gid][key]:
                raise ValueError("Pilot cohort not bound to canonical frame")
    rows = {g["game_id"]: [] for g in selected}
    cdn_rows = {gid: [] for gid in rows}
    consumed_archives = []
    for cdn_name in sorted({planned[gid]["source_file"] for gid in rows}):
        mobile_name = cdn_name.replace("cdnnba", "datanba")
        for name, target, id_key in [(cdn_name, cdn_rows, "gameId"), (mobile_name, rows, "GAME_ID")]:
            source = entries[name]
            if name == cdn_name and feature_manifest["source_map"][name] != source["sha256"]:
                raise ValueError("Canonical archive source binding mismatch")
            path = archive_path.with_name(name)
            if not path.exists():
                path = args.mobile_cache / name
            with verified_snapshot(path, source["bytes"], source["sha256"]) as stream, \
                    tarfile.open(fileobj=stream) as archive:
                members = archive.getmembers()
                if [m.name for m in members] != [name.replace(".tar.xz", ".csv")]:
                    raise ValueError("Unexpected archive members")
                for row in csv.DictReader(io.TextIOWrapper(archive.extractfile(members[0]))):
                    gid = row[id_key].zfill(10)
                    if gid in target:
                        if planned[gid]["source_file"] != cdn_name:
                            raise ValueError("Game appears in unexpected archive cohort")
                        target[gid].append(row)
            consumed_archives.append(dict(source, consumed_path=(str(path.relative_to(ROOT))
                                      if path.is_relative_to(ROOT) else "<mobile-cache>/" + name)))
    canonical = {gid: [] for gid in rows}
    with verified_snapshot(provenance_path, *snapshots[provenance_path]) as raw, io.TextIOWrapper(raw) as stream:
        # verified_snapshot authenticates exactly this stream before parsing.
        fingerprints[provenance_path] = snapshots[provenance_path][1]
        for line in stream:
            item = json.loads(line)
            if item["game_id"] in canonical:
                canonical[item["game_id"]].append(item)
    canonical_games = {g["game_id"]: g for g in feature_manifest["games"]}
    games = []
    for game in selected:
        gid = game["game_id"]
        entry = {"game_id": gid, "date": game["date"], "raw_events": len(rows[gid]),
                 "canonical_status": canonical_games[gid]["status"],
                 "canonical_count": len(canonical[gid]) if canonical[gid] else None,
                 "canonical_boundaries": [
                     {"possession_number": p["possession_number"],
                      "reference_action_number": p["reference_action_number"],
                      "last_action_number": p["event_action_numbers"][-1],
                      "complete": p["complete"], "audit_flags": p["audit_flags"]}
                     for p in canonical[gid]]}
        try:
            if not rows[gid]:
                raise ValueError("Missing pilot game in pinned archive")
            wrapped = wrap_rows(rows[gid])
            unchanged = copy.deepcopy(wrapped)
            source = SimpleNamespace(file_directory=None, load_data=lambda _: wrapped)
            loader_source = SimpleNamespace(file_directory=None, enhanced_pbp_source_loader=source)
            with patch("requests.sessions.Session.request", blocked_network), \
                    patch.object(socket, "create_connection", blocked_network), \
                    patch.object(socket.socket, "connect", blocked_network):
                loader = DataNbaPossessionLoader(gid, loader_source)
                boundaries = [
                    {"period": p.period, "number_in_period": p.number,
                     "start_clock": p.start_time, "end_clock": p.end_time,
                     "first_event_num": p.events[0].event_num,
                     "last_event_num": p.events[-1].event_num,
                     "event_nums": [e.event_num for e in p.events]}
                    for p in loader.items]
            if wrapped != unchanged:
                raise ValueError("Parser modified source dictionaries")
            verify_assignment(rows[gid], boundaries)
            entry.update(status="parsed", alternative_count=len(boundaries),
                         count_delta_alternative_minus_canonical=(len(boundaries) - len(canonical[gid])
                                                                 if canonical[gid] else None),
                         alternative_boundaries=boundaries, input_dicts_unchanged=True,
                         event_injection_or_reordering=False,
                         boundary_comparison=boundary_comparison(cdn_rows[gid], rows[gid],
                                                                 entry["canonical_boundaries"], boundaries)
                         if canonical[gid] else {"status": "unilateral_alternative_only",
                                                "reason": "Canonical game quarantined; no exported boundaries"})
        except Exception as exc:
            entry.update(status="failed", error_type=type(exc).__name__, error=str(exc),
                         traceback=traceback.format_exc().replace(str(ROOT), "<repo>")
                         .replace(str(package), "<isolated-package>"))
        games.append(entry)
    verify_no_drift(fingerprints)
    if verify_wheel(package / "pbpstats-1.3.11-py3-none-any.whl", package / "unpacked") != sources:
        raise ValueError("Imported package sources changed during run")
    result = {"schema_version": VERSION, "checked_on": "2026-11-05",
              "package_version": "1.3.11", "wheel_sha256": WHEEL_SHA256,
              "package_source_sha256": sources, "python_version": sys.version,
              "requests_version": __import__("requests").__version__,
              "consumed_archives": consumed_archives,
              "input_sha256": {str(path.relative_to(ROOT)): value
                               for path, value in fingerprints.items()},
              "input_fingerprints": "Consumed bytes/snapshots and sources captured before use; drift rejected before output",
              "release_role_binding_verified": True,
              "audit_plan_sha256": plan["plan_sha256"],
              "network_disabled": True, "overrides_enabled": False,
              "excluded_games": [], "games": games,
              "summary": {"fixed_pilot_games": len(sample), "selected_games": len(selected),
                          "parsed_games": sum(g["status"] == "parsed" for g in games),
                          "failed_games": sum(g["status"] == "failed" for g in games)},
              "scientific_gate": "BLOCKED; parser comparison is not independent film validation"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
