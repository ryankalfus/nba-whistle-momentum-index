"""Bound development reports and conditional audit promotion; never publication."""

from collections import Counter
import copy
import hashlib
from itertools import zip_longest
import json
import os
from pathlib import Path

from whistle_research import audit, features, modeling
from whistle_research.possessions import PARSER_VERSION
from whistle_research.sources import OFFICIAL_ARCHIVES, file_digest, read_schedule, safe_path, verify_sources


class ArtifactError(ValueError):
    pass


def read_json(path):
    return modeling._strict_json(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    serialized = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(serialized)


def artifact(path, relative_to):
    size, sha = file_digest(Path(path))
    return {"path": os.path.relpath(path, relative_to), "sha256": sha, "bytes": size}


def source_map(verification):
    if verification.get("ok") is not True or not verification.get("sources"):
        raise ArtifactError("all declared source bytes must verify")
    result = {}
    for source in verification["sources"]:
        if source.get("status") != "verified" or source.get("source_sha256") != source.get("expected_sha256"):
            raise ArtifactError("source verification is incomplete")
        if source["source_file"] in OFFICIAL_ARCHIVES:
            result[source["source_file"]] = source["source_sha256"]
    if not result:
        raise ArtifactError("no verified event archives")
    return result


def _validated_schedule(path):
    try:
        # Strict JSON rejects nonfinite/duplicate fields before the canonical
        # loader validates IDs, duplicate games, statuses, reasons and provenance.
        read_json(path)
        rows, _ = read_schedule(Path(path))
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ArtifactError(f"invalid declared schedule: {error}") from error
    return rows


def verify_inventory(inventory, verification, schedule):
    sources = source_map(verification)
    schedule_rows = _validated_schedule(schedule)
    expected = [g["game_id"] for g in schedule_rows if g["status"] == "expected"]
    games = inventory.get("games", [])
    ids = [g["game_id"] for g in games]
    coverage = inventory.get("coverage", {})
    if (inventory.get("kind") != "game_inventory" or inventory.get("ok") is not True
            or inventory.get("manifest_sha256") != verification["manifest_sha256"]
            or len(ids) != len(set(ids)) or set(ids) != set(expected)
            or len(expected) != len(set(expected)) or inventory.get("source_failures")
            or coverage.get("status") != "schedule_checked" or coverage.get("completeness") != "accounted_for"
            or coverage.get("schedule_evidence", {}).get("sha256") != file_digest(Path(schedule))[1]):
        raise ArtifactError("inventory source/schedule coverage binding failed")
    for game in games:
        if (game.get("disposition") != "observed" or game.get("anomalies")
                or game.get("source_sha256") != sources.get(game.get("source_file"))):
            raise ArtifactError("inventory contains unverified or excluded games")
    return sorted([{key: game[key] for key in audit.SOURCE_KEYS} for game in games], key=lambda game: game["game_id"])


def verify_reconciliation(report, verification, frame, metadata):
    if (report.get("ok") is not True or report.get("parser_version") != PARSER_VERSION
            or report.get("parser_sha256") != audit.parser_digest() or report.get("source_failures")
            or report.get("selection", {}).get("limit_per_source") != 0
            or report.get("verification", {}).get("manifest_sha256") != verification["manifest_sha256"]
            or source_map(report["verification"]) != source_map(verification)):
        raise ArtifactError("reconciliation is stale, partial or source-unbound")
    actual_metadata = {Path(p).name: file_digest(Path(p))[1] for p in metadata}
    if {entry["file"]: entry["sha256"] for entry in report.get("metadata", [])} != actual_metadata:
        raise ArtifactError("reconciliation metadata changed")
    games = report.get("games", [])
    identity_keys = ("game_id", "source_file", "source_sha256", "source_member")
    identities = [{key: game[key] for key in identity_keys} for game in games]
    expected = [{key: game[key] for key in identity_keys} for game in frame]
    if sorted(identities, key=lambda game: game["game_id"]) != expected:
        raise ArtifactError("reconciliation game/source frame differs from inventory")
    return report


def verify_feature_export(directory, verification, schedule, metadata, frame):
    """Re-read aligned JSONL streams, checking exact file/list hashes and ledgers.

    This checks artifact integrity and row accounting, not reconstruction truth.
    Memory is O(number of games), not O(number of possessions).
    """
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    expected_versions = {"parser_version": PARSER_VERSION, "parser_sha256": audit.parser_digest(),
                         "feature_version": features.FEATURE_VERSION, "feature_sha256": features.feature_module_sha256()}
    if any(manifest.get(key) != value for key, value in expected_versions.items()):
        raise ArtifactError("stale parser or feature implementation")
    if (manifest.get("schema_version") != "provisional-feature-dataset-v1" or manifest.get("ok") is not True
            or manifest.get("status") != "PROVISIONAL_AUDIT_BLOCKED" or manifest.get("eligible_games") != 0
            or manifest.get("plan_sha256") is not None or manifest.get("source_failures")
            or manifest.get("selection") != {"method": "all", "limit_per_source": 0}
            or manifest.get("source_map") != source_map(verification)
            or manifest.get("source_verification", {}).get("manifest_sha256") != verification["manifest_sha256"]
            or manifest.get("schedule_binding", {}).get("sha256") != file_digest(Path(schedule))[1]
            or manifest.get("frame") != frame or manifest.get("frame_sha256") != audit.digest(frame)):
        raise ArtifactError("feature manifest is not the complete bound provisional export")
    schedule_rows = [row for row in _validated_schedule(schedule) if row["status"] == "expected"]
    expected_schedule = {row["game_id"]: row for row in schedule_rows}
    if (len(expected_schedule) != len(schedule_rows) or set(expected_schedule) != {game["game_id"] for game in frame}
            or any((game["season"], game["game_type"]) != (expected_schedule[game["game_id"]]["season"],
                                                        expected_schedule[game["game_id"]]["game_type"]) for game in frame)):
        raise ArtifactError("complete frame differs from actual expected schedule")
    actual_metadata = {Path(p).name: file_digest(Path(p))[1] for p in metadata}
    if {entry["file"]: entry["sha256"] for entry in manifest.get("historical_metadata", [])} != actual_metadata:
        raise ArtifactError("feature metadata changed")
    games = {g["game_id"]: g for g in manifest["games"]}
    if len(games) != len(manifest["games"]) or set(games) != {g["game_id"] for g in frame}:
        raise ArtifactError("feature game ledger differs from complete frame")
    frame_by_id = {g["game_id"]: g for g in frame}
    for gid, game in games.items():
        if any(game.get(key) != expected_schedule[gid].get(key) for key in ("date", "season", "game_type")):
            raise ArtifactError("game metadata differs from actual expected schedule")
        if game.get("eligible") is not False or game.get("parser_sha256") != audit.parser_digest():
            raise ArtifactError("manually altered eligibility or stale game parser hash")
        if any(game.get(k) != frame_by_id[gid][k] for k in audit.SOURCE_KEYS):
            raise ArtifactError("game source identity differs from frame")
    row_path = safe_path(directory, manifest["rows_file"])
    provenance_path = safe_path(directory, manifest["row_provenance_file"])
    row_file_hash, provenance_hash = hashlib.sha256(), hashlib.sha256()
    canonical = hashlib.sha256(b"[")
    counts, unknown, missing = Counter(), Counter(), Counter()
    incomplete_provenance, flagged_provenance, total = 0, 0, 0
    audit_flags = Counter()
    closed, current_game = set(), None
    with row_path.open("rb") as rows, provenance_path.open("rb") as provenance:
        for raw_row, raw_provenance in zip_longest(rows, provenance):
            if raw_row is None or raw_provenance is None:
                raise ArtifactError("row/provenance stream lengths differ")
            row_file_hash.update(raw_row)
            provenance_hash.update(raw_provenance)
            row = modeling._strict_json(raw_row.decode("utf-8"))
            trace = modeling._strict_json(raw_provenance.decode("utf-8"))
            gid = row["game_id"]
            if gid not in games:
                raise ArtifactError("row game missing from complete ledger")
            if gid != current_game:
                if gid in closed:
                    raise ArtifactError("noncontiguous duplicate game block")
                if current_game is not None:
                    closed.add(current_game)
                current_game = gid
            counts[gid] += 1
            if (type(row.get("possession_number")) is not int or row["possession_number"] != counts[gid]
                    or (trace.get("game_id"), trace.get("possession_number")) != (gid, counts[gid])
                    or any(row.get(k) != games[gid].get(k) for k in ("date", "season", "game_type"))):
                raise ArtifactError("row/provenance identity, order or metadata mismatch")
            outcome = row.get("outcome")
            if outcome is not None and (type(outcome) is not int or outcome not in (0, 1)):
                raise ArtifactError("invalid target; only known binary or explicit null allowed")
            if "outcome" not in row:
                raise ArtifactError("missing target field")
            unknown[gid] += outcome is None
            missing.update(k for k, value in row.items() if value is None)
            action_ids, source_rows = trace.get("event_action_numbers"), trace.get("source_rows")
            if (not isinstance(action_ids, list) or not action_ids or not isinstance(source_rows, list)
                    or len(action_ids) != len(source_rows)
                    or any(type(v) is not int or v < 1 for v in [*action_ids, *source_rows])
                    or type(trace.get("complete")) is not bool or not isinstance(trace.get("audit_flags"), list)
                    or any(not audit.text(flag) for flag in trace["audit_flags"])):
                raise ArtifactError("incomplete row event/source provenance")
            incomplete_provenance += not trace["complete"]
            flagged_provenance += bool(trace["audit_flags"])
            audit_flags.update(trace["audit_flags"])
            if total:
                canonical.update(b",")
            canonical.update(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
            total += 1
    canonical.update(b"]")
    if (canonical.hexdigest() != manifest.get("rows_sha256")
            or row_file_hash.hexdigest() != manifest.get("rows_file_sha256")
            or provenance_hash.hexdigest() != manifest.get("row_provenance_sha256")
            or total != manifest.get("row_count") or sum(unknown.values()) != manifest.get("unknown_outcomes")
            or dict(missing) != manifest.get("missing_fields")):
        raise ArtifactError("feature/provenance bytes or accounting hash mismatch")
    for gid, game in games.items():
        if counts[gid] != game.get("row_count") or unknown[gid] != game.get("unknown_outcomes", 0):
            raise ArtifactError("per-game emitted rows differ from ledger")
    if audit.parser_digest() != expected_versions["parser_sha256"] or features.feature_module_sha256() != expected_versions["feature_sha256"]:
        raise ArtifactError("parser/feature code changed during verification")
    return manifest, {"rows": total, "unknown_outcomes": sum(unknown.values()),
                      "incomplete_provenance_rows": incomplete_provenance,
                      "flagged_provenance_rows": flagged_provenance,
                      "audit_flag_counts": dict(sorted(audit_flags.items()))}


def verify_synthetic(math, models):
    from whistle_research import metrics, simulations
    versions = math.get("versions", {})
    if (math.get("schema_version") != "synthetic-mathematics-v1"
            or versions.get("simulation_source_sha256") != file_digest(Path(simulations.__file__))[1]
            or versions.get("metric_source_sha256") != file_digest(Path(metrics.__file__))[1]
            or models.get("status") != "SYNTHETIC_ONLY_NO_SCIENTIFIC_ACCEPTANCE"
            or models.get("specification") != modeling.specification()):
        raise ArtifactError("synthetic artifact source/specification is stale")


def prepare_promotion(directory, *, plan, reviews, config, source_manifest, cache, schedule, metadata,
                      evidence_root=None):
    """Create a new in-memory audited adapter manifest; never mutate originals.

    Passing external attestations is necessary but not independently authenticated.
    The entire declared frame must have complete, known, noncritical data; no
    quarantine, unknown target or unselected game may be quietly removed.
    """
    implementation_sha = file_digest(Path(__file__))[1]
    gate = audit.check_gate(plan, reviews, config)
    if gate.get("status") != "PASS_CONDITIONAL":
        raise modeling.BlockedError(["independent_audit_not_passed", *gate.get("reasons", [])])
    if evidence_root is None:
        raise modeling.BlockedError(["annotation_content_evidence_required"])
    from whistle_research.review_evidence import validate_evidence
    annotation_evidence = validate_evidence(plan, reviews, config, Path(evidence_root))
    if annotation_evidence.get("ok") is not True:
        raise modeling.BlockedError(["annotation_contents_unverified", *annotation_evidence.get("reasons", [])])
    verification = verify_sources(Path(source_manifest), Path(cache))
    source_map(verification)
    if (plan.get("inventory_coverage", {}).get("schedule_evidence", {}).get("sha256") != file_digest(Path(schedule))[1]
            or plan.get("frame_sha256") != audit.digest(plan.get("frame"))):
        raise modeling.BlockedError(["promotion_schedule_or_frame_binding_mismatch"])
    try:
        original, stream = verify_feature_export(directory, verification, schedule, metadata, plan["frame"])
    except (ArtifactError, OSError, ValueError, TypeError, KeyError) as error:
        raise modeling.BlockedError([f"promotion_artifact_integrity: {error}"]) from error
    reasons = []
    if original["unknown_outcomes"] or stream["incomplete_provenance_rows"]:
        reasons.append("promotion_requires_all_known_targets_and_complete_row_provenance")
    if stream["flagged_provenance_rows"]:
        reasons.append("promotion_requires_no_unresolved_row_audit_flags")
    for game in original["games"]:
        issues = game.get("issues")
        if (game.get("unassigned_control_events") is not False or not isinstance(issues, list)
                or any(not isinstance(issue, dict) or not audit.text(issue.get("code"))
                       or type(issue.get("blocking")) is not bool for issue in issues)
                or any(issue["blocking"] and issue["code"] != "independent_audit_required" for issue in issues)):
            reasons.append("promotion_game_issues_or_unassigned_control_unresolved")
    if any(g.get("status") != "provisional_reconstruction" or g.get("complete") is not True
           or g.get("critical_unresolved") is not False or g.get("row_count", 0) < 1 for g in original["games"]):
        reasons.append("promotion_requires_complete_noncritical_full_frame_no_quarantine")
    if reasons:
        raise modeling.BlockedError(reasons)
    from whistle_research.review_comparison import compare_annotations
    comparison = compare_annotations(directory, plan, reviews, Path(evidence_root), annotation_evidence,
                                     metadata=metadata)
    if comparison.get("ok") is not True:
        raise modeling.BlockedError(["independent_labels_disagree_or_comparison_incomplete",
                                     *comparison.get("reasons", [])])
    if file_digest(Path(__file__))[1] != implementation_sha:
        raise modeling.BlockedError(["promotion_implementation_changed_during_verification"])
    promotion_inputs = {
        "feature_directory": os.path.relpath(Path(directory), Path.cwd()),
        "source_manifest": os.path.relpath(Path(source_manifest), Path.cwd()),
        "cache": os.path.relpath(Path(cache), Path.cwd()),
        "schedule": os.path.relpath(Path(schedule), Path.cwd()),
        "metadata": [os.path.relpath(Path(path), Path.cwd()) for path in metadata],
        "evidence_root": os.path.relpath(Path(evidence_root), Path.cwd()),
    }
    promoted = copy.deepcopy(original)
    promoted.update(schema_version="conditionally-audited-feature-dataset-v1",
                    status="CONDITIONALLY_AUDITED_ADAPTER_NOT_PUBLICATION", plan_sha256=plan["plan_sha256"],
                    eligible_games=len(original["games"]), promotion_inputs=promotion_inputs,
                    provisional_manifest_sha256=file_digest(Path(directory) / "manifest.json")[1],
                    audit_reviews_sha256=gate["reviews_sha256"], audit_config_sha256=gate["config_sha256"],
                    annotation_evidence=annotation_evidence,
                    annotation_comparison=comparison,
                    promotion_implementation_sha256=implementation_sha,
                    limitations="Conditional external audit attestations; not authenticated independent truth, protocol lock or publication approval.")
    for game in promoted["games"]:
        game["eligible"] = True
    return promoted, gate


def validate_promoted_dataset(dataset, *, plan, reviews, config):
    """Authoritative real-entry validation: replay promotion from actual files.

    Neither an eligible boolean nor a self-declared promoted schema is evidence.
    Regenerate every binding from the immutable provisional export and require
    exact equality with the supplied conditional manifest.
    """
    try:
        if dataset.get("schema_version") != "conditionally-audited-feature-dataset-v1":
            raise modeling.BlockedError(["conditionally_audited_adapter_required"])
        inputs = dataset["promotion_inputs"]
        expected, gate = prepare_promotion(
            inputs["feature_directory"], plan=plan, reviews=reviews, config=config,
            source_manifest=inputs["source_manifest"], cache=inputs["cache"],
            schedule=inputs["schedule"], metadata=inputs["metadata"],
            evidence_root=inputs.get("evidence_root"))
        if audit.digest(dataset) != audit.digest(expected):
            raise modeling.BlockedError(["promoted_manifest_differs_from_reverified_original"])
    except modeling.BlockedError:
        raise
    except (ArtifactError, OSError, ValueError, TypeError, KeyError) as error:
        raise modeling.BlockedError([f"promotion_reverification_required: {error}"]) from error
    return gate


def build_report(*, verification, inventory, reconciliation, dataset, gate, math, models, artifacts):
    verify_synthetic(math, models)
    games = dataset["games"]
    issues = reconciliation.get("issue_counts", {})
    counts = {
        "source_files": len(verification["sources"]), "expected_games": len(inventory["coverage"]["games"]),
        "observed_games": len(inventory["games"]),
        "reconstructed_games": sum(g.get("status") == "provisional_reconstruction" for g in games),
        "quarantined_games": sum(g.get("status") == "quarantined" for g in games),
        "possession_rows": dataset["row_count"], "unknown_outcomes": dataset["unknown_outcomes"],
        "complete_games": sum(g.get("complete") is True for g in games),
        "critical_unresolved_games": sum(g.get("critical_unresolved") is True for g in games),
        "eligible_games": dataset["eligible_games"],
        "corrected_schedule_dates": dataset["schedule_binding"].get("corrected_dates", 0),
        "unresolved_transfer_flags": issues.get("unexplained_control_transfer", 0),
        "unresolved_violation_flags": issues.get("violation_requires_audit", 0),
    }
    compact_gate = {k: v for k, v in gate.items() if k not in ("inventory_coverage", "enriched_reasons")}
    compact_gate.update(selected_games=gate.get("selected_games", gate.get("random_games", 0) + gate.get("enriched_games", 0)),
                        review_records=gate.get("review_records", gate.get("completed_random_games", 0) + gate.get("completed_enriched_games", 0)))
    return {
        "schema_version": "development-research-report-v1", "software_status": "DEVELOPMENT_RUN_COMPLETE",
        "scientific_status": "BLOCKED", "publication_status": "NOT_AUTHORIZED", "counts": counts,
        "versions": {k: dataset[k] for k in ("parser_version", "parser_sha256", "feature_version", "feature_sha256")},
        "audit": compact_gate, "artifacts": artifacts,
        "synthetic": {"status": "SYNTHETIC_ONLY", "math": {"scenario_count": len(math["scenarios"]),
                       "exact_reference": math["exact_nonstationary_reference"], "coverage": math["coverage"]},
                      "models": {"paired_logloss": models["evaluation"]["paired_logloss"],
                                 "decision": models["evaluation"]["decision"]}},
        "limitations": ["Provisional reconstruction, not independently validated live possession opportunities.",
                        "Unknown outcomes, quarantines and unresolved parser flags remain explicitly counted.",
                        "Synthetic arithmetic/model checks do not establish basketball validity or usefulness.",
                        "Source hashes bind reused artifacts; they do not independently authenticate derived annotations."],
        "next_required_evidence": ["Independent full-game annotations and adjudication under prospectively frozen audit tolerances.",
                                   "Complete noncritical reconstruction and known targets for the entire declared frame.",
                                   "Frozen modeling/evaluation protocol, genuine unused-cohort evidence and meaningful gain.",
                                   "All upstream evidence and a separately authorized publication decision."],
    }


def write_report(output, report):
    output = Path(output)
    write_json(output / "report.json", report)
    counts = report["counts"]
    lines = ["# Development research report", "", "Scientific status: **BLOCKED**. Publication: **NOT AUTHORIZED**.",
             "", "Software diagnostics completed; this does not complete independent scientific validation.", "",
             "| Quantity | Count |", "| --- | ---: |"]
    lines += [f"| {key.replace('_', ' ')} | {value:,} |" for key, value in counts.items()]
    lines += ["", "## Required evidence", "", *[f"- {item}" for item in report["next_required_evidence"]],
              "", "## Limitations", "", *[f"- {item}" for item in report["limitations"]], ""]
    with (output / "report.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines))
    draft = """# Research manuscript development draft

Status: NOT AN EMPIRICAL RESULTS RELEASE. Independent audit and protocol lock remain blocked.

## Methods draft

Predict at least one recorded counted defensive foul at declared possession start.
Preserve immutable raw events, source hashes, global possession order and explicit
unknown outcomes. Compare matched chronological context and history models with
training-only preprocessing. Primary endpoint: paired held-out log loss, history
minus context; whole-game uncertainty conditions on fitted models. These methods
are development specifications until audit, exposure and meaningful-effect decisions
are independently evidenced and frozen.

## Results placeholders

Independent reconstruction accuracy: NOT AVAILABLE; full-game reviews pending.
Real held-out predictive performance: NOT EVALUATED; audit/protocol gates blocked.
Practical usefulness: NOT CLASSIFIED; no real meaningful-effect threshold frozen.
The adjacent report contains software accounting and separately labeled synthetic
diagnostics only. Do not substitute synthetic output for these missing results.

## Limitations

Final corrected feed reconstruction is not proof of live feature availability,
call correctness, referee intent or causality. Parser agreement and software tests
cannot substitute for independent full-game annotation.
"""
    with (output / "draft_paper.md").open("x", encoding="utf-8") as stream:
        stream.write(draft)
