"""Synthetic artifact/evidence fixtures validate contracts, never external truth."""

from collections import Counter
import copy
from functools import lru_cache
import hashlib
import json

import pytest

from whistle_research import audit, features, modeling, release, simulations, sources
from whistle_research.possessions import PARSER_VERSION


@lru_cache
def _synthetics():
    return simulations.run_study(games=8, trials=2, resamples=5), modeling.synthetic_demo()


def synthetic_artifacts(root):
    root.mkdir(parents=True, exist_ok=True)
    cache = root / "cache"
    cache.mkdir()
    source = cache / "cdnnba_2020.tar.xz"
    source.write_bytes(b"SYNTHETIC byte-identity fixture; not a real archive")
    sha = sources.file_digest(source)[1]
    source_manifest = root / "sources.json"
    release.write_json(source_manifest, [{"file": source.name, "bytes": source.stat().st_size,
                                         "sha256": sha, "url": "synthetic-fixture"}])
    verification = sources.verify_sources(source_manifest, cache)
    rows = modeling._synthetic_rows(71, games=6, possessions=24)
    mapping = {gid: f"002300000{i}" for i, gid in enumerate(sorted({r['game_id'] for r in rows}))}
    for row in rows:
        row["game_id"] = mapping[row["game_id"]]
    frame = [{"game_id": gid, "source_file": source.name, "source_sha256": sha,
              "source_member": "synthetic.csv", "season": "synthetic-2030",
              "game_type": next(r["game_type"] for r in rows if r["game_id"] == gid)} for gid in mapping.values()]
    schedule = root / "schedule.json"
    release.write_json(schedule, {"games": [{"game_id": gid, "season": "synthetic-2030", "game_type": frame[i]["game_type"],
                                            "date": next(r["date"] for r in rows if r["game_id"] == gid)}
                                           for i, gid in enumerate(mapping.values())],
                                  "provenance": "synthetic independent schedule fixture"})
    coverage = {"status": "schedule_checked", "completeness": "accounted_for",
                "schedule_evidence": {"sha256": sources.file_digest(schedule)[1], "provenance": "synthetic schedule"},
                "games": [{"game_id": gid, "observation": "observed", "observed": True} for gid in mapping.values()]}
    inventory = {"kind": "game_inventory", "ok": True, "manifest_sha256": verification["manifest_sha256"],
                 "source_failures": [], "coverage": coverage,
                 "games": [{**game, "disposition": "observed", "anomalies": [], "event_count": 24} for game in frame]}
    inventory_path = root / "inventory.json"
    release.write_json(inventory_path, inventory)
    metadata = root / "metadata.csv"
    metadata.write_text("synthetic metadata bytes\n")
    metadata_binding = [{"file": metadata.name, "sha256": sources.file_digest(metadata)[1]}]
    dataset_dir = root / "features"
    dataset_dir.mkdir()
    raw_rows = [json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows]
    (dataset_dir / "rows.jsonl").write_text("".join(raw_rows))
    traces = [{"game_id": row["game_id"], "possession_number": row["possession_number"],
               "event_action_numbers": [row["possession_number"]], "source_rows": [row["possession_number"] + 1],
               "reference_action_number": None, "complete": True, "audit_flags": []} for row in rows]
    (dataset_dir / "row_provenance.jsonl").write_text("".join(json.dumps(trace) + "\n" for trace in traces))
    games = [{**game, "date": next(r["date"] for r in rows if r["game_id"] == game["game_id"]),
              "parser_sha256": audit.parser_digest(), "eligible": False, "complete": True,
              "critical_unresolved": False, "row_count": 24, "source_event_count": 24,
              "unknown_outcomes": 0, "status": "provisional_reconstruction",
              "issues": [{"code": "independent_audit_required", "blocking": True}],
              "unassigned_control_events": False} for game in frame]
    missing = Counter(k for row in rows for k, value in row.items() if value is None)
    dataset = {"schema_version": "provisional-feature-dataset-v1", "status": "PROVISIONAL_AUDIT_BLOCKED",
               "ok": True, "eligible_games": 0, "plan_sha256": None,
               "parser_version": PARSER_VERSION, "parser_sha256": audit.parser_digest(),
               "feature_version": features.FEATURE_VERSION, "feature_sha256": features.feature_module_sha256(),
               "frame": frame, "frame_sha256": audit.digest(frame), "source_map": {source.name: sha},
               "source_verification": verification, "source_failures": [], "historical_metadata": metadata_binding,
               "schedule_binding": {"sha256": sources.file_digest(schedule)[1], "corrected_dates": 0},
               "selection": {"method": "all", "limit_per_source": 0}, "games": games,
               "row_count": len(rows), "unknown_outcomes": 0, "missing_fields": dict(missing),
               "rows_file": "rows.jsonl", "rows_sha256": modeling.row_digest(rows),
               "rows_file_sha256": sources.file_digest(dataset_dir / "rows.jsonl")[1],
               "row_provenance_file": "row_provenance.jsonl",
               "row_provenance_sha256": sources.file_digest(dataset_dir / "row_provenance.jsonl")[1]}
    release.write_json(dataset_dir / "manifest.json", dataset)
    reconciliation = {"ok": True, "parser_version": PARSER_VERSION, "parser_sha256": audit.parser_digest(),
                      "verification": verification, "metadata": metadata_binding,
                      "selection": {"limit_per_source": 0}, "source_failures": [], "issue_counts": {},
                      "games": [{**game, "candidate_possessions": 24, "status": "candidate_diagnostic_only"} for game in frame]}
    reconciliation_path = root / "reconciliation.json"
    release.write_json(reconciliation_path, reconciliation)
    enriched = [frame[0]["game_id"]]
    plan = audit.prepare_plan(inventory_path, 2, 20261102, enriched, {enriched[0]: "synthetic diagnostic fixture"})
    binding = {key: plan[key] for key in ("plan_sha256", "parser_version", "parser_sha256")}
    reviews = {**binding, "games": [{"game_id": game["game_id"], "source_sha256": sha,
        "reviewers": [{"reviewer_id": name, "evidence_ref": "synthetic-footage-fixture", "annotation_ref": "synthetic-annotation",
                       "independent": True, "full_game_reviewed": True, "started_at": "2029-01-02T00:00:00Z",
                       "completed_at": "2029-01-03T00:00:00Z", "material_discrepancy": False,
                       "critical_unresolved": False} for name in ("fixture-A", "fixture-B")]}
        for game in plan["games"]]}
    config = {**binding, "frozen": True, "freeze_id": "synthetic-only-test", "frozen_at": "2029-01-01T00:00:00Z",
              "review_data_status_at_freeze": "unseen", "confidence": .95, "max_game_error_rate": .999,
              "min_random_games": 2, "sample_assumption": audit.ASSUMPTION}
    math, models = copy.deepcopy(_synthetics())
    math_path, model_path = root / "math.json", root / "models.json"
    release.write_json(math_path, math)
    release.write_json(model_path, models)
    return {"root": root, "cache": cache, "source_manifest": source_manifest, "verification": verification,
            "schedule": schedule, "metadata": [metadata], "inventory": inventory, "inventory_path": inventory_path,
            "frame": frame, "dataset": dataset, "feature_dir": dataset_dir, "rows": rows,
            "reconciliation": reconciliation, "reconciliation_path": reconciliation_path,
            "plan": plan, "reviews": reviews, "config": config, "math": math, "models": models,
            "math_path": math_path, "model_path": model_path, "enriched": enriched}


def promote_args(fixture):
    return {"directory": fixture["feature_dir"], "plan": fixture["plan"], "reviews": fixture["reviews"],
            "config": fixture["config"], "source_manifest": fixture["source_manifest"], "cache": fixture["cache"],
            "schedule": fixture["schedule"], "metadata": fixture["metadata"]}


def test_full_stream_and_positive_conditional_promotion_preserve_original(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    original_bytes = (fixture["feature_dir"] / "manifest.json").read_bytes()
    promoted, gate = release.prepare_promotion(**promote_args(fixture))
    assert gate["status"] == "PASS_CONDITIONAL"
    assert promoted["eligible_games"] == 6
    assert all(game["eligible"] is True for game in promoted["games"])
    assert promoted["plan_sha256"] == fixture["plan"]["plan_sha256"]
    assert promoted["provisional_manifest_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert (fixture["feature_dir"] / "manifest.json").read_bytes() == original_bytes
    assert all(game["eligible"] is False for game in fixture["dataset"]["games"])


@pytest.mark.parametrize("change", ["stale_parser", "stale_feature", "rows_hash", "provenance_hash", "manual_eligible", "partial", "missing_game", "quarantine", "incomplete", "critical"])
def test_promotion_rejects_stale_tampered_or_incomplete_artifacts(tmp_path, change):
    fixture = synthetic_artifacts(tmp_path)
    packet = fixture["dataset"]
    if change == "stale_parser":
        packet["parser_sha256"] = "0" * 64
    elif change == "stale_feature":
        packet["feature_sha256"] = "0" * 64
    elif change == "rows_hash":
        packet["rows_file_sha256"] = "0" * 64
    elif change == "provenance_hash":
        packet["row_provenance_sha256"] = "0" * 64
    elif change == "manual_eligible":
        packet["games"][0]["eligible"] = True
    elif change == "partial":
        packet["selection"] = {"method": "first_per_source_diagnostic", "limit_per_source": 3}
    elif change == "missing_game":
        packet["games"].pop()
    elif change == "quarantine":
        packet["games"][0]["status"] = "quarantined"
    elif change == "incomplete":
        packet["games"][0]["complete"] = None
    else:
        packet["games"][0]["critical_unresolved"] = True
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(packet))
    with pytest.raises(modeling.BlockedError):
        release.prepare_promotion(**promote_args(fixture))


def test_genuinely_unknown_target_still_refuses_when_all_hashes_are_updated(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    rows = fixture["rows"]
    rows[0]["outcome"] = None
    row_path = fixture["feature_dir"] / "rows.jsonl"
    row_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    packet = fixture["dataset"]
    packet.update(rows_sha256=modeling.row_digest(rows), rows_file_sha256=sources.file_digest(row_path)[1], unknown_outcomes=1)
    packet["games"][0]["unknown_outcomes"] = 1
    packet["missing_fields"]["outcome"] = 1
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(packet))
    with pytest.raises(modeling.BlockedError, match="all_known_targets"):
        release.prepare_promotion(**promote_args(fixture))


def test_false_gate_status_never_substitutes_for_actual_reviews(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    fixture["reviews"] = {"status": "PASS_CONDITIONAL", "games": []}
    with pytest.raises(modeling.BlockedError, match="independent_audit_not_passed"):
        release.prepare_promotion(**promote_args(fixture))


def test_broken_source_bytes_and_bad_alignment_refuse(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    (fixture["cache"] / "cdnnba_2020.tar.xz").write_bytes(b"changed")
    with pytest.raises(release.ArtifactError):
        release.prepare_promotion(**promote_args(fixture))


def test_report_is_explicitly_blocked_with_draft_placeholders_and_exclusive_files(tmp_path):
    from whistle_research.pipeline import audit_templates
    fixture = synthetic_artifacts(tmp_path / "inputs")
    reviews, config = audit_templates(fixture["plan"])
    gate = audit.check_gate(fixture["plan"], reviews, config)
    report = release.build_report(verification=fixture["verification"], inventory=fixture["inventory"],
                                 reconciliation=fixture["reconciliation"], dataset=fixture["dataset"], gate=gate,
                                 math=fixture["math"], models=fixture["models"], artifacts={})
    assert report["software_status"] == "DEVELOPMENT_RUN_COMPLETE"
    assert report["scientific_status"] == "BLOCKED"
    assert report["counts"]["eligible_games"] == 0
    assert report["synthetic"]["models"]["decision"]["classification"] == "NOT_SPECIFIED"
    output = tmp_path / "report"
    output.mkdir()
    release.write_report(output, report)
    assert "NOT EVALUATED" in (output / "draft_paper.md").read_text()
    with pytest.raises(FileExistsError):
        release.write_report(output, report)


@pytest.mark.parametrize("flag", ["violation_requires_audit", "source_clock_correction_requires_audit", 7, ""])
def test_row_audit_flags_block_promotion_even_with_updated_hash_and_false_critical_ledger(tmp_path, flag):
    fixture = synthetic_artifacts(tmp_path)
    provenance = fixture["feature_dir"] / "row_provenance.jsonl"
    traces = [json.loads(line) for line in provenance.read_text().splitlines()]
    traces[0]["audit_flags"] = [flag]
    provenance.write_text("".join(json.dumps(trace) + "\n" for trace in traces))
    packet = fixture["dataset"]
    packet["row_provenance_sha256"] = sources.file_digest(provenance)[1]
    assert packet["games"][0]["critical_unresolved"] is False
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(packet))
    with pytest.raises(modeling.BlockedError):
        release.prepare_promotion(**promote_args(fixture))


@pytest.mark.parametrize("change", ["blocking_issue", "unknown_issue_status", "control_event", "missing_control_status", "missing_issues"])
def test_explicit_game_issue_or_control_evidence_overrides_false_critical_ledger(tmp_path, change):
    fixture = synthetic_artifacts(tmp_path)
    game = fixture["dataset"]["games"][0]
    if change == "blocking_issue":
        game["issues"].append({"code": "violation_requires_audit", "blocking": True})
    elif change == "unknown_issue_status":
        game["issues"].append({"code": "unresolved", "blocking": None})
    elif change == "control_event":
        game["unassigned_control_events"] = True
    elif change == "missing_control_status":
        game.pop("unassigned_control_events")
    else:
        game.pop("issues")
    assert game["critical_unresolved"] is False
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(fixture["dataset"]))
    with pytest.raises(modeling.BlockedError, match="game_issues_or_unassigned_control"):
        release.prepare_promotion(**promote_args(fixture))


def test_schedule_hash_alone_cannot_hide_a_missing_expected_game_from_promotion(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    schedule = release.read_json(fixture["schedule"])
    extra = copy.deepcopy(schedule["games"][-1])
    extra["game_id"] = "0023000099"
    schedule["games"].append(extra)
    fixture["schedule"].write_text(json.dumps(schedule))
    sha = sources.file_digest(fixture["schedule"])[1]
    fixture["dataset"]["schedule_binding"]["sha256"] = sha
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(fixture["dataset"]))
    fixture["plan"]["inventory_coverage"]["schedule_evidence"]["sha256"] = sha
    fixture["plan"]["plan_sha256"] = audit.plan_digest(fixture["plan"])
    for evidence in (fixture["reviews"], fixture["config"]):
        evidence["plan_sha256"] = fixture["plan"]["plan_sha256"]
    assert audit.check_gate(fixture["plan"], fixture["reviews"], fixture["config"])["status"] == "PASS_CONDITIONAL"
    with pytest.raises(modeling.BlockedError, match="actual expected schedule"):
        release.prepare_promotion(**promote_args(fixture))


@pytest.mark.parametrize("change", ["unknown_status", "duplicate_excluded", "missing_provenance", "missing_exclusion_reason"])
def test_invalid_nonexpected_schedule_entries_cannot_be_silently_ignored(tmp_path, change):
    fixture = synthetic_artifacts(tmp_path)
    schedule = release.read_json(fixture["schedule"])
    extra = copy.deepcopy(schedule["games"][-1])
    extra.update(game_id="0023000099", status="excluded", reason="synthetic explicit exclusion")
    if change == "unknown_status":
        extra["status"] = "typo"
    elif change == "duplicate_excluded":
        extra["game_id"] = schedule["games"][0]["game_id"]
    elif change == "missing_provenance":
        schedule.pop("provenance")
    else:
        extra.pop("reason")
    schedule["games"].append(extra)
    fixture["schedule"].write_text(json.dumps(schedule))
    sha = sources.file_digest(fixture["schedule"])[1]
    fixture["dataset"]["schedule_binding"]["sha256"] = sha
    (fixture["feature_dir"] / "manifest.json").write_text(json.dumps(fixture["dataset"]))
    fixture["plan"]["inventory_coverage"]["schedule_evidence"]["sha256"] = sha
    fixture["plan"]["plan_sha256"] = audit.plan_digest(fixture["plan"])
    for evidence in (fixture["reviews"], fixture["config"]):
        evidence["plan_sha256"] = fixture["plan"]["plan_sha256"]
    with pytest.raises(modeling.BlockedError, match="invalid declared schedule"):
        release.prepare_promotion(**promote_args(fixture))
