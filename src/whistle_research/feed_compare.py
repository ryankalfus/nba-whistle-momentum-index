"""Pinned offline CDN/mobile comparison; agreement never clears audit flags."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sqlite3
import tarfile
import tempfile

from whistle_research.reconcile import verified_snapshot
from whistle_research.sources import canonical_game_id, file_digest, safe_path

CDN = "cdnnba_2024.tar.xz"
MOBILE = "datanba_2024.tar.xz"


def integer(value, *, zero_missing=False):
    """Normalize integer-shaped fields, preserving absent IDs as unknown."""
    if value in (None, "", "NA", "NaN", "nan"):
        return None
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("invalid integer field") from None
    if not number.is_finite() or number != number.to_integral_value() or number < 0:
        raise ValueError("invalid integer field")
    result = int(number)
    return None if zero_missing and result == 0 else result


def clock(value):
    if not value:
        return None
    match = re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", value)
    if not match:
        match = re.fullmatch(r"(\d+):(\d+(?:\.\d+)?)", value)
    if not match or Decimal(match[2]) >= 60:
        raise ValueError("invalid source clock")
    return Decimal(match[1]) * 60 + Decimal(match[2])


def compare_pair(cdn, mobile):
    """Corroborate a unique ID with exact nonempty order or timestamp."""
    corroboration = []
    if integer(cdn.get("orderNumber")) is not None and integer(cdn.get("orderNumber")) == integer(mobile.get("ord")):
        corroboration.append("order")
    if cdn.get("timeActual") and cdn["timeActual"] == mobile.get("wallclk"):
        corroboration.append("timestamp")
    if not corroboration:
        return {"status": "identity_unverified", "corroboration": []}
    fields = {
        "clock": (clock(cdn.get("clock")), clock(mobile.get("cl"))),
        "team": (integer(cdn.get("teamId"), zero_missing=True), integer(mobile.get("tid"), zero_missing=True)),
        "offense": (integer(cdn.get("possession"), zero_missing=True), integer(mobile.get("oftid"), zero_missing=True)),
        "period": (integer(cdn.get("period"), zero_missing=True), integer(mobile.get("PERIOD"), zero_missing=True)),
    }
    different = [key for key, (a, b) in fields.items() if a is not None and b is not None and a != b]
    unknown = [key for key, (a, b) in fields.items() if a is None or b is None]
    return {"status": "different" if different else "incomplete" if unknown else "agreement",
            "corroboration": corroboration, "differing_fields": different,
            "unknown_fields": unknown,
            "normalized": {k: [str(v) if isinstance(v, Decimal) else v for v in pair]
                           for k, pair in fields.items()}}


def stream_rows(stream, mobile=False):
    """Yield original CSV dictionaries and exact member/row references."""
    required = {"GAME_ID", "evt", "ord", "wallclk", "cl", "tid", "oftid", "PERIOD"} if mobile else {
        "gameId", "actionNumber", "orderNumber", "timeActual", "clock", "teamId", "possession", "period"}
    members = set()
    with tarfile.open(fileobj=stream, mode="r|xz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(".csv") or member.name in members:
                raise ValueError("invalid or duplicate archive member")
            members.add(member.name)
            with archive.extractfile(member) as raw:
                reader = csv.DictReader(line.decode("utf-8-sig") for line in raw)
                fields = reader.fieldnames or []
                if len(fields) != len(set(fields)) or not required.issubset(fields):
                    raise ValueError("missing/duplicate feed columns")
                for number, row in enumerate(reader, 2):
                    if None in row or any(v is None for v in row.values()):
                        raise ValueError("malformed feed row")
                    gid = canonical_game_id(row["GAME_ID" if mobile else "gameId"])
                    aid = integer(row["evt" if mobile else "actionNumber"])
                    if aid is None:
                        raise ValueError("missing event ID")
                    yield gid, aid, {"member": member.name, "row": number, "raw": row}
    if not members:
        raise ValueError("empty source archive")


def bound_cases(features, report, sources):
    """Reject stale parsers, source substitutions and inconsistent game cohorts."""
    parser_sha = file_digest(Path(__file__).with_name("possessions.py"))[1]
    for evidence in (features, report):
        if evidence.get("parser_version") != "canonical_candidate_v7" or evidence.get("parser_sha256") != parser_sha:
            raise ValueError("evidence not bound to current v7 parser")
        if evidence.get("selection", {}).get("limit_per_source") != 0:
            raise ValueError("partial evidence run")
        if not evidence.get("ok") or evidence.get("source_failures"):
            raise ValueError("incomplete evidence run")
    expected = sources[CDN]["sha256"]
    if features.get("source_map", {}).get(CDN) != expected:
        raise ValueError("feature source binding mismatch")
    verified = report.get("verification", {})
    if not verified.get("ok") or not any(
        s.get("source_file") == CDN and s.get("source_sha256") == expected
        and s.get("status") == "verified" for s in verified.get("sources", [])
    ):
        raise ValueError("report source binding mismatch")
    for collection in (features["frame"], features["games"], report["games"]):
        ids = [g["game_id"] for g in collection]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate evidence game")
    frame = {g["game_id"]: g for g in features["frame"] if g.get("source_file") == CDN}
    games = {g["game_id"]: g for g in features["games"] if g.get("source_file") == CDN}
    other = {g["game_id"]: g for g in report["games"] if g.get("source_file") == CDN}
    if not frame or set(frame) != set(games) or set(games) != set(other):
        raise ValueError("cohort mismatch")
    for gid, game in games.items():
        if type(game.get("critical_unresolved")) is not bool or game.get("eligible") is not False:
            raise ValueError("unknown critical/eligibility state")
        if game.get("status") not in {"quarantined", "provisional_reconstruction"}:
            raise ValueError("unknown feature game status")
        if other[gid].get("status") not in {"quarantined", "candidate_diagnostic_only"} or other[gid].get("eligible") is not False:
            raise ValueError("unknown report game status/eligibility")
        if any(type(i.get("blocking")) is not bool for i in game.get("issues", [])):
            raise ValueError("unknown issue blocking state")
        for row in (frame[gid], game):
            if (row.get("season"), row.get("game_type"), row.get("source_sha256")) != ("2024-25", "regular_season", expected):
                raise ValueError("cohort/source mismatch")
        if other[gid].get("source_sha256") != expected or (other[gid].get("status") == "quarantined") != (game.get("status") == "quarantined"):
            raise ValueError("report game binding mismatch")
        if game.get("status") != "quarantined" and dict(Counter(i["code"] for i in game.get("issues", []))) != other[gid].get("issues"):
            raise ValueError("report issue binding mismatch")
        if other[gid].get("source_event_count") != game.get("source_event_count"):
            raise ValueError("source event count mismatch")
    return {gid: g for gid, g in games.items() if g.get("critical_unresolved")}


def bind_run_report(input_bytes, run_report):
    """Bind exact evidence bytes to typed roles in an existing development run."""
    if run_report.get("schema_version") != "development-research-report-v1":
        raise ValueError("unknown development report schema")
    expected_parser = file_digest(Path(__file__).with_name("possessions.py"))[1]
    if run_report.get("versions", {}).get("parser_sha256") != expected_parser or run_report["versions"].get("parser_version") != "canonical_candidate_v7":
        raise ValueError("development report not bound to current v7")
    roles = {"features": "feature_manifest", "reconciliation": "reconciliation", "source_manifest": "source_manifest"}
    for name, role in roles.items():
        artifact = run_report.get("artifacts", {}).get(role, {})
        raw = input_bytes[name]
        if artifact.get("bytes") != len(raw) or artifact.get("sha256") != hashlib.sha256(raw).hexdigest():
            raise ValueError("development report artifact binding mismatch: " + role)


def run(manifest, cache, features_path, report_path, output, run_report_path):
    input_bytes = {"source_manifest": manifest.read_bytes(), "features": features_path.read_bytes(),
                   "reconciliation": report_path.read_bytes(), "run_report": run_report_path.read_bytes()}
    bind_run_report(input_bytes, json.loads(input_bytes["run_report"]))
    entries = json.loads(input_bytes["source_manifest"])
    sources = {}
    for name in (CDN, MOBILE):
        matches = [e for e in entries if e.get("file") == name]
        if len(matches) != 1:
            raise ValueError("missing/duplicate pinned archive")
        sources[name] = matches[0]
    features = json.loads(input_bytes["features"])
    report = json.loads(input_bytes["reconciliation"])
    comparison_sha = file_digest(Path(__file__))[1]
    cases = bound_cases(features, report, sources)
    output.mkdir(parents=True, exist_ok=False)
    counts, issue_counts, differing, issue_differing = Counter(), Counter(), Counter(), Counter()
    seen, mobile_games, per_game, targets = set(), set(), {}, {}
    cdn_games = set()
    for gid, game in cases.items():
        labels = {}
        for issue in game.get("issues", []):
            if issue["blocking"] and issue["code"] != "independent_audit_required":
                labels.setdefault(issue["action_number"], []).append(issue["code"])
        if game["status"] == "quarantined":
            match = re.fullmatch(r"clock/period regression at action (\d+)", game.get("error", ""))
            if match:
                labels.setdefault(int(match[1]), []).append("quarantined_clock_regression")
        targets[gid] = labels
    # Disk index bounds working memory to a CSV row and a few duplicate matches.
    with tempfile.TemporaryDirectory(prefix="whistle-feed-") as directory, sqlite3.connect(Path(directory) / "mobile.sqlite") as db:
        db.execute("CREATE TABLE mobile (gid TEXT, aid INTEGER, payload TEXT)")
        db.execute("CREATE INDEX mobile_key ON mobile(gid, aid)")
        entry = sources[MOBILE]
        with verified_snapshot(safe_path(cache, MOBILE), entry["bytes"], entry["sha256"]) as stream:
            for gid, aid, payload in stream_rows(stream, mobile=True):
                if gid in cases:
                    mobile_games.add(gid)
                    db.execute("INSERT INTO mobile VALUES (?, ?, ?)", (gid, aid, json.dumps(payload)))
        db.commit()
        # CDN duplicate keys also fail closed, including the first occurrence.
        db.execute("CREATE TABLE cdn (gid TEXT, aid INTEGER, payload TEXT)")
        db.execute("CREATE INDEX cdn_key ON cdn(gid, aid)")
        entry = sources[CDN]
        with verified_snapshot(safe_path(cache, CDN), entry["bytes"], entry["sha256"]) as stream:
            for gid, aid, payload in stream_rows(stream):
                cdn_games.add(gid)
                if gid in cases:
                    seen.add(gid)
                    db.execute("INSERT INTO cdn VALUES (?, ?, ?)", (gid, aid, json.dumps(payload)))
        db.commit()
        with (output / "paired_rows.jsonl").open("x") as destination:
            for gid, game in sorted(cases.items()):
                game_counts, found_targets = Counter(), set()
                total = db.execute("SELECT COUNT(*) FROM cdn WHERE gid=?", (gid,)).fetchone()[0]
                if total != game["source_event_count"]:
                    raise ValueError("bound game event count differs from source")
                for aid, payload in db.execute("SELECT aid,payload FROM cdn WHERE gid=? ORDER BY rowid", (gid,)):
                    cdn = json.loads(payload)
                    matches = db.execute("SELECT payload FROM mobile WHERE gid=? AND aid=? LIMIT 3", (gid, aid)).fetchall()
                    duplicate = db.execute("SELECT COUNT(*) FROM cdn WHERE gid=? AND aid=?", (gid, aid)).fetchone()[0] > 1
                    if duplicate or len(matches) > 1:
                        result = {"status": "ambiguous_id"}
                    elif gid not in mobile_games:
                        result = {"status": "missing_mobile_game"}
                    elif not matches:
                        result = {"status": "unmatched_id"}
                    else:
                        result = compare_pair(cdn["raw"], json.loads(matches[0][0])["raw"])
                    labels = targets[gid].get(aid, [])
                    if labels:
                        found_targets.add(aid)
                        issue_counts[result["status"]] += 1
                        issue_differing.update(result.get("differing_fields", []))
                    counts[result["status"]] += 1
                    game_counts[result["status"]] += 1
                    differing.update(result.get("differing_fields", []))
                    destination.write(json.dumps({"game_id": gid, "action_number": aid, "eligible": False,
                        "issue_codes": labels, **result, "cdn": cdn,
                        "mobile_candidates": [json.loads(m[0]) for m in matches]}) + "\n")
                missing = set(targets[gid]) - found_targets
                if missing:
                    raise ValueError("critical action absent from bound CDN game")
                per_game[gid] = {"status": game["status"], "counts": dict(game_counts),
                                 "critical_action_count": len(targets[gid]),
                                 "unlocated_critical_issues": [i for i in game.get("issues", [])
                                     if i["blocking"] and i["code"] != "independent_audit_required" and i["action_number"] is None],
                                 "error": game.get("error")}
    if cdn_games != {g["game_id"] for g in features["frame"] if g.get("source_file") == CDN}:
        raise ValueError("full CDN source cohort differs from evidence frame")
    if file_digest(Path(__file__).with_name("possessions.py"))[1] != features["parser_sha256"] or file_digest(Path(__file__))[1] != comparison_sha:
        raise ValueError("implementation changed during comparison")
    if seen != set(cases):
        raise ValueError("selected game missing from CDN archive")
    summary = {"schema_version": "cross-feed-diagnostic-v1", "status": "DIAGNOSTIC_AUDIT_BLOCKED",
        "eligible_games": 0, "season": "2024-25", "game_type": "regular_season",
        "selected_critical_games": len(cases), "missing_mobile_games": sorted(set(cases) - mobile_games),
        "counts": dict(counts), "critical_action_counts": dict(issue_counts),
        "differing_fields": dict(differing), "critical_differing_fields": dict(issue_differing),
        "games": per_game, "sources": sources,
        "bindings": {**{name + "_sha256": hashlib.sha256(raw).hexdigest()
                        for name, raw in input_bytes.items()},
            "parser_sha256": features["parser_sha256"], "comparison_sha256": comparison_sha},
        "paired_rows_sha256": file_digest(output / "paired_rows.jsonl")[1],
        "limits": "Unique IDs require order or timestamp corroboration. Missing/zero team and offense IDs remain unknown. All selected-game CDN rows compared; mobile-only rows not enumerated. No source correction, independent truth, model eligibility or audit resolution is inferred."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "cache", "features", "report", "output", "run-report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.manifest, args.cache, args.features, args.report, args.output, args.run_report)
    print(json.dumps({k: result[k] for k in ("selected_critical_games", "counts", "critical_action_counts")}))


if __name__ == "__main__":
    main()
