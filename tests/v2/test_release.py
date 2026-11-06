"""Synthetic artifact/evidence fixtures validate contracts, never external truth."""

from collections import Counter
import copy
import csv
from functools import lru_cache
import hashlib
import io
import json
import tarfile

import pytest

from whistle_research import audit, features, modeling, release, simulations, sources
from whistle_research.possessions import PARSER_VERSION, reconstruct
from whistle_research.review_packet import build_packet


@lru_cache
def _synthetics():
    return simulations.run_study(games=8, trials=2, resamples=5), modeling.synthetic_demo()


def _synthetic_annotations(root, plan, reviews, config, source_manifest, cache):
    """Real files for a synthetic contract; no human or basketball validation."""
    plan_path, protocol = root / "plan.json", root / "review-protocol.md"
    release.write_json(plan_path, plan)
    protocol.write_text("SYNTHETIC review contract only; no real people or footage.\n")
    evidence_root = root / "review-evidence"
    manifest = build_packet(plan_path, source_manifest, cache, None, protocol, evidence_root)
    config.update(packet_manifest_sha256=sources.file_digest(evidence_root / "manifest.json")[1],
                  protocol_sha256=manifest["protocol_file"]["sha256"])
    for record in reviews["games"]:
        gid = record["game_id"]
        for slot, review in zip(("A", "B"), record["reviewers"], strict=True):
            path = evidence_root / f"reviewer_{slot}/annotations/{gid}.json"
            annotation = json.loads(path.read_text())
            ledger = release.read_json(evidence_root / f"reviewer_{slot}/raw_events/{gid}.json")
            events = ledger["events"]
            result = reconstruct([event["raw"] for event in events], gid, 100, 200,
                                 ledger["source_sha256"])
            feature_rows = features.build_rows(result, {
                "game_id": gid, "date": "2030-01-01", "season": "2020-21",
                "game_type": "regular_season"})
            by_action = {event["event_id"]: event["ref"] for event in events}
            positions = {event["ref"]: index for index, event in enumerate(events)}
            possessions, periods, covered = [], {}, set()
            def footage(start, end):
                return {"reference": review["evidence_ref"], "start_seconds": start,
                        "end_seconds": end}
            for index, event in enumerate(events):
                periods.setdefault(int(event["raw"]["period"]), []).append((index, event["ref"]))
            for possession, row in zip(result.possessions, feature_rows, strict=True):
                refs = [by_action[action] for action in possession.event_action_numbers]
                lo, hi = positions[refs[0]], positions[refs[-1]]
                covered.update(event["ref"] for event in events[lo:hi + 1])
                context = {key: row[key] for key in (
                    "period", "clock", "score_margin", "score_difference", "home_defense",
                    "defense_counted_fouls", "previous_foul_1", "previous_foul_2", "start_type")}
                context["reference_ref"] = by_action[possession.start_state.reference_action_number]
                possessions.append({"start_ref": refs[0], "end_ref": refs[-1],
                                    "offense_team_id": possession.offense_team_id,
                                    "defense_team_id": possession.defense_team_id,
                                    "counted_foul_refs": [by_action[action] for action in possession.counted_foul_action_numbers],
                                    "prediction_start": context,
                                    "uncertain": False, "material_discrepancy": False,
                                    "evidence": footage(lo, hi + 1)})
            coverage = [{"period": period, "start_ref": refs[0][1], "end_ref": refs[-1][1],
                         "evidence": footage(refs[0][0], refs[-1][0] + 1)}
                        for period, refs in periods.items()]
            excluded = [{"ref": event["ref"], "reason": "administrative", "uncertain": False,
                         "material_discrepancy": False, "evidence": footage(index, index + 1)}
                        for index, event in enumerate(events) if event["ref"] not in covered]
            review["reviewer_kind"] = "human"
            annotation.update({key: review[key] for key in (
                "reviewer_id", "reviewer_kind", "started_at", "completed_at", "evidence_ref",
                "full_game_reviewed", "independent", "material_discrepancy", "critical_unresolved")})
            annotation.update(coverage={"continuous_full_game": True, "periods": coverage},
                              possessions=possessions, excluded_events=excluded)
            path.write_text(json.dumps(annotation))
            size, sha = sources.file_digest(path)
            review.update(annotation_ref=path.relative_to(evidence_root).as_posix(),
                          annotation_bytes=size, annotation_sha256=sha)
    return evidence_root


def synthetic_artifacts(root):
    root.mkdir(parents=True, exist_ok=True)
    cache = root / "cache"
    cache.mkdir()
    source = cache / "cdnnba_2020.tar.xz"
    # Entirely synthetic source, but genuine parser/feature outputs and references.
    game_ids = [f"002300000{i}" for i in range(6)]
    actions_by_game, source_rows = {}, {}
    raw = io.StringIO(newline="")
    columns = ["gameId", "actionNumber", "orderNumber", "timeActual", "clock", "teamId",
               "teamTricode", "possession", "period", "actionType", "subType",
               "scoreHome", "scoreAway", "description"]
    writer = csv.DictWriter(raw, fieldnames=columns)
    writer.writeheader()
    csv_row = 2
    for gid in game_ids:
        actions = []
        def add(kind, period, clock, team=0, owner=0, sub=""):
            actions.append({"gameId": gid, "actionNumber": len(actions), "orderNumber": len(actions),
                            "timeActual": "", "clock": clock, "teamId": team,
                            "teamTricode": "HOM" if team == 100 else "AWY" if team == 200 else "",
                            "possession": owner, "period": period, "actionType": kind, "subType": sub,
                            "scoreHome": 12, "scoreAway": 9,
                            "description": "SYNTHETIC contract fixture, not an NBA event"})
        for period in range(1, 5):
            add("period", period, "PT12M00S", sub="start")
            for index in range(6):
                offense = 100 if index % 2 == 0 else 200
                if index % 3 == 0:
                    add("foul", period, f"PT{11-index:02}M30S", 300 - offense, offense, "personal")
                add("turnover", period, f"PT{11-index:02}M00S", offense, offense)
            add("period", period, "PT00M00S", sub="end")
        add("game", 4, "PT00M00S", sub="end")
        actions_by_game[gid] = actions
        for action in actions:
            source_rows[gid, action["actionNumber"]] = csv_row
            writer.writerow(action)
            csv_row += 1
    raw_bytes = raw.getvalue().encode()
    with tarfile.open(source, "w:xz") as archive:
        member = tarfile.TarInfo("synthetic.csv")
        member.size = len(raw_bytes)
        archive.addfile(member, io.BytesIO(raw_bytes))
    sha = sources.file_digest(source)[1]
    source_manifest = root / "sources.json"
    release.write_json(source_manifest, [{"file": source.name, "bytes": source.stat().st_size,
                                         "sha256": sha, "url": "synthetic-fixture"}])
    verification = sources.verify_sources(source_manifest, cache)
    results = {gid: reconstruct(actions, gid, 100, 200, sha)
               for gid, actions in actions_by_game.items()}
    rows = [row for index, gid in enumerate(game_ids) for row in features.build_rows(results[gid], {
        "game_id": gid, "date": f"2030-01-{index + 1:02}", "season": "2020-21",
        "game_type": "regular_season"})]
    frame = [{"game_id": gid, "source_file": source.name, "source_sha256": sha,
              "source_member": "synthetic.csv", "season": "2020-21",
              "game_type": next(r["game_type"] for r in rows if r["game_id"] == gid)} for gid in game_ids]
    schedule = root / "schedule.json"
    release.write_json(schedule, {"games": [{"game_id": gid, "season": "2020-21", "game_type": frame[i]["game_type"],
                                            "date": next(r["date"] for r in rows if r["game_id"] == gid)}
                                           for i, gid in enumerate(game_ids)],
                                  "provenance": "synthetic independent schedule fixture"})
    coverage = {"status": "schedule_checked", "completeness": "accounted_for",
                "schedule_evidence": {"sha256": sources.file_digest(schedule)[1], "provenance": "synthetic schedule"},
                "games": [{"game_id": gid, "observation": "observed", "observed": True} for gid in game_ids]}
    inventory = {"kind": "game_inventory", "ok": True, "manifest_sha256": verification["manifest_sha256"],
                 "source_failures": [], "coverage": coverage,
                 "games": [{**game, "disposition": "observed", "anomalies": [], "event_count": len(actions_by_game[game["game_id"]])} for game in frame]}
    inventory_path = root / "inventory.json"
    release.write_json(inventory_path, inventory)
    metadata = root / "metadata.csv"
    with metadata.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["game_id", "home", "away", "date", "season", "game_type"])
        writer.writeheader()
        for index, gid in enumerate(game_ids):
            writer.writerow({"game_id": gid, "home": "HOM", "away": "AWY",
                             "date": f"2030-01-{index + 1:02}", "season": "2020-21",
                             "game_type": "regular_season"})
    metadata_binding = [{"file": metadata.name, "sha256": sources.file_digest(metadata)[1]}]
    dataset_dir = root / "features"
    dataset_dir.mkdir()
    raw_rows = [json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows]
    (dataset_dir / "rows.jsonl").write_text("".join(raw_rows))
    traces = [{"game_id": gid, "possession_number": possession.possession_number,
               "event_action_numbers": list(possession.event_action_numbers),
               "source_rows": [source_rows[gid, action] for action in possession.event_action_numbers],
               "reference_action_number": possession.start_state.reference_action_number,
               "complete": possession.complete, "audit_flags": list(possession.audit_flags)}
              for gid, result in results.items() for possession in result.possessions]
    (dataset_dir / "row_provenance.jsonl").write_text("".join(json.dumps(trace) + "\n" for trace in traces))
    games = [{**game, "date": next(r["date"] for r in rows if r["game_id"] == game["game_id"]),
              "parser_sha256": audit.parser_digest(), "eligible": False, "complete": True,
              "critical_unresolved": False, "row_count": 24,
              "source_event_count": len(actions_by_game[game["game_id"]]),
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
    evidence_root = _synthetic_annotations(root, plan, reviews, config, source_manifest, cache)
    math, models = copy.deepcopy(_synthetics())
    math_path, model_path = root / "math.json", root / "models.json"
    release.write_json(math_path, math)
    release.write_json(model_path, models)
    return {"root": root, "cache": cache, "source_manifest": source_manifest, "verification": verification,
            "schedule": schedule, "metadata": [metadata], "inventory": inventory, "inventory_path": inventory_path,
            "frame": frame, "dataset": dataset, "feature_dir": dataset_dir, "rows": rows,
            "reconciliation": reconciliation, "reconciliation_path": reconciliation_path,
            "plan": plan, "reviews": reviews, "config": config, "evidence_root": evidence_root,
            "math": math, "models": models,
            "math_path": math_path, "model_path": model_path, "enriched": enriched}


def promote_args(fixture):
    return {"directory": fixture["feature_dir"], "plan": fixture["plan"], "reviews": fixture["reviews"],
            "config": fixture["config"], "source_manifest": fixture["source_manifest"], "cache": fixture["cache"],
            "schedule": fixture["schedule"], "metadata": fixture["metadata"],
            "evidence_root": fixture["evidence_root"]}


def _rebind_synthetic_plan(fixture):
    """Adversarial fixture rehashes every review binding, not just metadata."""
    root, plan = fixture["evidence_root"], fixture["plan"]
    plan_path = root / "plan.json"
    plan_path.write_text(json.dumps(plan))
    manifest_path = root / "manifest.json"
    manifest = release.read_json(manifest_path)
    manifest["plan_sha256"] = plan["plan_sha256"]
    size, sha = sources.file_digest(plan_path)
    manifest["plan_file"].update(bytes=size, sha256=sha)
    for game in fixture["reviews"]["games"]:
        for reviewer in game["reviewers"]:
            path = root / reviewer["annotation_ref"]
            annotation = release.read_json(path)
            annotation["plan_sha256"] = plan["plan_sha256"]
            path.write_text(json.dumps(annotation))
            reviewer["annotation_bytes"], reviewer["annotation_sha256"] = sources.file_digest(path)
    for kit in manifest["reviewer_kits"].values():
        entry = kit["manifest_file"]
        path = root / entry["path"]
        delivered = release.read_json(path)
        delivered["plan_sha256"] = plan["plan_sha256"]
        path.write_text(json.dumps(delivered))
        entry["bytes"], entry["sha256"] = sources.file_digest(path)
    manifest_path.write_text(json.dumps(manifest))
    fixture["config"]["packet_manifest_sha256"] = sources.file_digest(manifest_path)[1]


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


def test_metadata_only_pass_cannot_promote_without_annotation_files(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    assert audit.check_gate(fixture["plan"], fixture["reviews"], fixture["config"])["status"] == "PASS_CONDITIONAL"
    arguments = promote_args(fixture)
    arguments.pop("evidence_root")
    with pytest.raises(modeling.BlockedError, match="annotation_content_evidence_required"):
        release.prepare_promotion(**arguments)


def test_actual_annotation_contents_are_reverified_before_reusing_promotion(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    promoted, _ = release.prepare_promotion(**promote_args(fixture))
    reviewer = fixture["reviews"]["games"][0]["reviewers"][0]
    path = fixture["evidence_root"] / reviewer["annotation_ref"]
    with path.open("a") as stream:
        stream.write(" ")
    with pytest.raises(modeling.BlockedError, match="annotation_contents_unverified"):
        release.validate_promoted_dataset(promoted, plan=fixture["plan"], reviews=fixture["reviews"],
                                          config=fixture["config"])


def test_rehashed_invalid_annotations_cannot_pass_with_summary_flags(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    reviewer = fixture["reviews"]["games"][0]["reviewers"][0]
    path = fixture["evidence_root"] / reviewer["annotation_ref"]
    annotation = release.read_json(path)
    annotation["possessions"] = []
    path.write_text(json.dumps(annotation))
    reviewer["annotation_bytes"], reviewer["annotation_sha256"] = sources.file_digest(path)
    assert audit.check_gate(fixture["plan"], fixture["reviews"], fixture["config"])["status"] == "PASS_CONDITIONAL"
    with pytest.raises(modeling.BlockedError, match="completed_possessions_required"):
        release.prepare_promotion(**promote_args(fixture))


@pytest.mark.parametrize("change", ["swap_ownership", "missing_start_context"])
def test_matching_human_files_must_agree_with_actual_candidate_before_promotion(tmp_path, change):
    fixture = synthetic_artifacts(tmp_path)
    for record in fixture["reviews"]["games"]:
        for reviewer in record["reviewers"]:
            path = fixture["evidence_root"] / reviewer["annotation_ref"]
            annotation = release.read_json(path)
            for possession in annotation["possessions"]:
                if change == "swap_ownership":
                    possession["offense_team_id"], possession["defense_team_id"] = (
                        possession["defense_team_id"], possession["offense_team_id"])
                else:
                    possession.pop("prediction_start")
            path.write_text(json.dumps(annotation))
            reviewer["annotation_bytes"], reviewer["annotation_sha256"] = sources.file_digest(path)
    assert audit.check_gate(fixture["plan"], fixture["reviews"], fixture["config"])["status"] == "PASS_CONDITIONAL"
    with pytest.raises(modeling.BlockedError, match="independent_labels_disagree_or_comparison_incomplete"):
        release.prepare_promotion(**promote_args(fixture))


def test_promotion_rejects_implementation_drift_during_comparison(tmp_path, monkeypatch):
    from whistle_research import review_comparison
    fixture = synthetic_artifacts(tmp_path)
    implementation = tmp_path / "release-source-snapshot.py"
    implementation.write_text("initial source fingerprint")
    monkeypatch.setattr(release, "__file__", str(implementation))
    original_compare = review_comparison.compare_annotations

    def drifting_comparison(*args, **kwargs):
        result = original_compare(*args, **kwargs)
        implementation.write_text("changed after validation started")
        return result

    monkeypatch.setattr(review_comparison, "compare_annotations", drifting_comparison)
    with pytest.raises(modeling.BlockedError, match="promotion_implementation_changed_during_verification"):
        release.prepare_promotion(**promote_args(fixture))


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
    _rebind_synthetic_plan(fixture)
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
    _rebind_synthetic_plan(fixture)
    with pytest.raises(modeling.BlockedError, match="invalid declared schedule"):
        release.prepare_promotion(**promote_args(fixture))
