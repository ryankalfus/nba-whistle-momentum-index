"""Cross-feed diagnostics must preserve unknowns and fail closed on identity."""
import csv
import io
import json
from pathlib import Path
import tarfile

import pytest

from whistle_research.feed_compare import (
    CDN, MOBILE, bind_run_report, bound_cases, clock, compare_pair, integer, run, stream_rows,
)
from whistle_research.sources import file_digest


def pair():
    return ({"gameId": "22400001", "actionNumber": "7", "orderNumber": "70000",
             "timeActual": "2024-01-01T01:02:03Z", "clock": "PT01M02.50S",
             "teamId": "1610612737", "possession": "1610612738", "period": "1"},
            {"GAME_ID": "22400001", "evt": "7", "ord": "70000",
             "wallclk": "2024-01-01T01:02:03Z", "cl": "1:02.5",
             "tid": "1610612737", "oftid": "1610612738", "PERIOD": "1"})


def evidence():
    sha = file_digest(Path(__file__).parents[2] / "src/whistle_research/possessions.py")[1]
    game = {"game_id": "0022400001", "season": "2024-25", "game_type": "regular_season",
            "source_file": CDN, "source_sha256": "a" * 64, "source_event_count": 1,
            "status": "provisional_reconstruction", "critical_unresolved": True, "eligible": False,
            "issues": [{"action_number": 7, "blocking": True, "code": "unresolved"}]}
    common = {"ok": True, "parser_version": "canonical_candidate_v7", "parser_sha256": sha, "selection": {"limit_per_source": 0}}
    features = {**common, "frame": [game.copy()], "games": [game.copy()], "source_map": {CDN: "a" * 64}}
    report = {**common, "games": [{**game, "status": "candidate_diagnostic_only", "issues": {"unresolved": 1}}],
              "verification": {"ok": True, "sources": [{"source_file": CDN, "source_sha256": "a" * 64, "status": "verified"}]}}
    return features, report, {CDN: {"sha256": "a" * 64}}


def test_normalized_clock_and_unknown_ownership():
    a, b = pair()
    assert compare_pair(a, b)["status"] == "agreement"
    assert clock("PT01M02.50S") == clock("1:02.5")
    b["tid"], a["teamId"] = "0", ""
    result = compare_pair(a, b)
    assert result["status"] == "incomplete"
    assert result["unknown_fields"] == ["team"]
    assert integer("0", zero_missing=True) is None
    with pytest.raises(ValueError):
        clock("1:60")
    with pytest.raises(ValueError):
        integer("1.2")


def test_disagreement_requires_corroborated_identity():
    a, b = pair()
    b.update(cl="1:00", tid="1610612738", oftid="1610612737", PERIOD="2")
    assert compare_pair(a, b)["differing_fields"] == ["clock", "team", "offense", "period"]
    b.update(ord="42", wallclk="other")
    assert compare_pair(a, b)["status"] == "identity_unverified"
    b["ord"] = a["orderNumber"]
    assert compare_pair(a, b)["corroboration"] == ["order"]


@pytest.mark.parametrize("mutation", ["parser", "cohort", "source", "report_count", "report_issues", "duplicate", "partial", "critical", "eligible", "status"])
def test_evidence_binding_rejects_stale_or_substituted_inputs(mutation):
    features, report, sources = evidence()
    if mutation == "parser":
        report["parser_sha256"] = "0" * 64
    elif mutation == "cohort":
        features["frame"][0]["season"] = "2023-24"
    elif mutation == "source":
        features["source_map"][CDN] = "0" * 64
    elif mutation == "report_count":
        report["games"][0]["source_event_count"] = 2
    elif mutation == "duplicate":
        features["frame"].append(features["frame"][0])
    elif mutation == "partial":
        report["selection"] = {"limit_per_source": 1}
    elif mutation == "critical":
        features["games"][0]["critical_unresolved"] = "true"
    elif mutation == "eligible":
        report["games"][0]["eligible"] = True
    elif mutation == "status":
        features["games"][0]["status"] = "published"
    else:
        report["games"][0]["issues"] = {}
    with pytest.raises(ValueError):
        bound_cases(features, report, sources)


def archive(path, records):
    data = io.StringIO()
    writer = csv.DictWriter(data, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)
    payload = data.getvalue().encode()
    with tarfile.open(path, "w:xz") as tar:
        member = tarfile.TarInfo("events.csv")
        member.size = len(payload)
        tar.addfile(member, io.BytesIO(payload))


def test_stream_retains_raw_row_reference(tmp_path):
    a, _ = pair()
    path = tmp_path / CDN
    archive(path, [a])
    with path.open("rb") as stream:
        rows = list(stream_rows(stream))
    assert rows == [("0022400001", 7, {"member": "events.csv", "row": 2, "raw": a})]


@pytest.mark.parametrize("case,status", [("paired", "agreement"), ("duplicate_mobile", "ambiguous_id"),
    ("duplicate_cdn", "ambiguous_id"), ("missing_game", "missing_mobile_game"), ("missing_id", "unmatched_id"), ("quarantine", "agreement")])
def test_full_pinned_run(tmp_path, case, status):
    a, b = pair()
    features, report, _ = evidence()
    cdn_records, mobile_records = [a], [b]
    if case == "quarantine":
        for game in (features["games"][0], report["games"][0]):
            game.update(status="quarantined", error="clock/period regression at action 7")
        features["games"][0]["issues"] = []
    if case == "duplicate_mobile":
        mobile_records.append(b)
    if case == "duplicate_cdn":
        cdn_records.append(a)
        features["games"][0]["source_event_count"] = 2
        report["games"][0]["source_event_count"] = 2
    if case == "missing_game":
        mobile_records = [{**b, "GAME_ID": "22400002"}]
    if case == "missing_id":
        mobile_records = [{**b, "evt": "8"}]
    archive(tmp_path / CDN, cdn_records)
    archive(tmp_path / MOBILE, mobile_records)
    entries = []
    for name in (CDN, MOBILE):
        size, sha = file_digest(tmp_path / name)
        entries.append({"file": name, "bytes": size, "sha256": sha})
    sha = entries[0]["sha256"]
    features["source_map"][CDN] = sha
    for row in (features["frame"][0], features["games"][0], report["games"][0], report["verification"]["sources"][0]):
        row["source_sha256"] = sha
    for name, value in (("manifest", entries), ("features", features), ("report", report)):
        (tmp_path / (name + ".json")).write_text(json.dumps(value))
    import hashlib
    run_report = {"schema_version": "development-research-report-v1", "versions": {
        "parser_version": features["parser_version"], "parser_sha256": features["parser_sha256"]}, "artifacts": {}}
    for name, role in (("manifest", "source_manifest"), ("features", "feature_manifest"), ("report", "reconciliation")):
        raw = (tmp_path / (name + ".json")).read_bytes()
        run_report["artifacts"][role] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    run_report_path = tmp_path / "run_report.json"
    run_report_path.write_text(json.dumps(run_report))
    output = tmp_path / "output"
    summary = run(tmp_path / "manifest.json", tmp_path, tmp_path / "features.json", tmp_path / "report.json", output, run_report_path)
    assert summary["counts"] == {status: len(cdn_records)}
    assert summary["critical_action_counts"] == {status: len(cdn_records)}
    assert summary["eligible_games"] == 0
    assert summary["paired_rows_sha256"] == file_digest(output / "paired_rows.jsonl")[1]
    with pytest.raises(FileExistsError):
        run(tmp_path / "manifest.json", tmp_path, tmp_path / "features.json", tmp_path / "report.json", output, run_report_path)


def test_tampered_archive_fails_before_diagnostic_summary(tmp_path):
    from whistle_research.reconcile import verified_snapshot

    path = tmp_path / CDN
    path.write_bytes(b"original")
    size, sha = file_digest(path)
    path.write_bytes(b"modified")
    with pytest.raises(ValueError, match="snapshot does not match"):
        with verified_snapshot(path, size, sha):
            pytest.fail("unverified bytes became available")


@pytest.mark.parametrize("role", ["features", "reconciliation", "source_manifest"])
def test_typed_development_run_bindings_reject_shifted_action_ids_and_mobile_entry(role):
    import hashlib
    features, _, _ = evidence()
    inputs = {"features": b"issue action 7", "reconciliation": b"report", "source_manifest": b"mobile hash original"}
    names = {"features": "feature_manifest", "reconciliation": "reconciliation", "source_manifest": "source_manifest"}
    report = {"schema_version": "development-research-report-v1", "versions": {
        "parser_version": features["parser_version"], "parser_sha256": features["parser_sha256"]},
        "artifacts": {names[k]: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()} for k, v in inputs.items()}}
    bind_run_report(inputs, report)
    inputs[role] += b"changed"
    with pytest.raises(ValueError, match="artifact binding mismatch"):
        bind_run_report(inputs, report)
