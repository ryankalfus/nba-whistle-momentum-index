"""Structural human annotation checking, not authentication or film validation.

human-full-game-annotation-v1 repeats the packet's plan/parser/game/source identity
and review metadata: reviewer_id, reviewer_kind='human', reviewer_slot A/B,
started_at/completed_at (zoned ISO), evidence_ref, independent/full_game_reviewed,
material_discrepancy/critical_unresolved booleans. Metadata annotation_ref is a
contained file with annotation_sha256 and annotation_bytes. Config freezes
packet_manifest_sha256 and protocol_sha256 alongside the existing audit config.
The coordinator manifest reviewer_kits[slot].manifest_file binds each delivered
blinded manifest and its local protocol_file/instructions_file/ledger descriptors.
Delivered protocols must also be byte-identical to the frozen coordinator protocol;
all redacted identities, keys and canonical relative paths are checked.

possessions is a nonempty ordered list of {start_ref,end_ref,offense_team_id,
defense_team_id,counted_foul_refs:[],uncertain:false,material_discrepancy:bool,
evidence:{reference,start_seconds,end_seconds}}. Refs are exact ledger member:row
identities, not action IDs (which can repeat). Ranges are inclusive, disjoint and
source-ordered; a possession cannot cross periods. Teams are distinct positive
integer IDs observed somewhere in the raw game's teamId/possession fields. This
checks identity plausibility, not that a raw feed ownership field is correct.

Each possession may additionally contain prediction_start={reference_ref,period,
clock,score_margin,score_difference,home_defense,defense_counted_fouls,
previous_foul_1,previous_foul_2,start_type}. It is optional for structural intake
and REQUIRED by the production candidate comparison. Fill every field independently
from raw events and film at the declared BEFORE-EVENT prediction point, never from
candidate parser values or the current possession's outcome. reference_ref is that
point's exact raw member:row ref and may precede the possession's own range; null
is permitted only for an actual period_start without a source-event reference.
period and clock describe that same point. score_difference is defense score minus
offense score; score_margin is its absolute value. home_defense is integer 0 or 1.
defense_counted_fouls is the defense's independently recorded pre-event count;
previous_foul_1 and previous_foul_2 are independently labeled preceding possession
outcomes, with explicit null allowed when historical indicators are unavailable.
start_type independently identifies the declared opportunity start. Optional
start_context_footage uses the same {reference,start_seconds,end_seconds} evidence
shape to locate the prediction point, including a point preceding this group's
own footage. The separate production comparison defines exact value types and
checks those annotations against candidate context reconstructed from frozen raw
ledgers. Structural intake alone does not validate prediction_start or confer
production acceptance. Empty-template _guidance is field help, never annotation.

In the blinded first phase material_discrepancy means a discrepancy between raw
records and independently observed film, not candidate agreement. The coordinator
later computes agreement with the candidate from both original annotations. Any
candidate mismatch blocks promotion; two false human material_discrepancy flags
cannot establish that the candidate passed.

Every remaining raw row appears once in excluded_events as {ref,reason,evidence,uncertain:false,material_discrepancy:bool},
reason administrative or no_possession. Coverage is {continuous_full_game:true,
periods:[{period,start_ref,end_ref,evidence}]}, exactly one entry per source period
with its exact first/last refs. Evidence objects need a reference matching the
review evidence_ref plus finite ordered seconds in one continuous recording's
first broadcast occurrence, never replay clips. Period ranges are chronological
and nonoverlapping. Possession/exclusion evidence is contained in its period;
possessions have chronological starts. Overlap in possession evidence intervals
requires an explicit footage_overlap_note (e.g. one shared boundary sequence). Labels cover every raw row,
including administrative ones; this conservative partition cannot express shared
boundary rows. Evidence cannot establish unseen feed periods or validate film.

Material verdict equals any possession or exclusion material_discrepancy. Uncertain labels,
unresolved critical issues, incomplete coverage and blank templates fail closed.
Adjudications, when provided, require the same complete file contract (slot C) and
retain both originals. Their annotation adds adjudication={resolved:true,
original_annotation_sha256:[A hash,B hash],rationale,evidence}; the rationale is a
human attestation, while both original hashes are checked. This version rejects
label disagreements even if summary
verdicts match unless a third independently stored annotation is supplied.

CLI validate/import are read-only aliases producing a fresh report directory:
python -m whistle_research.review_evidence validate --plan ... --reviews ...
--config ... --evidence-root ... --output NEW_DIRECTORY
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path

from whistle_research.audit import check_gate, digest, text, timestamp, validate_plan
from whistle_research.review_packet import ANNOTATION_VERSION, BINDINGS, write_json
from whistle_research.sources import file_digest, safe_path, write_artifact


class InvalidEvidence(ValueError):
    """A structural evidence failure with a stable reportable reason."""


def require(condition, reason: str) -> None:
    if not condition:
        raise InvalidEvidence(reason)


def load_json(raw: bytes):
    """Reject ambiguous duplicate keys and non-JSON numeric constants."""
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def constant(value):
        raise InvalidEvidence("nonfinite_json_constant")
    def finite_float(value):
        number = float(value)
        require(math.isfinite(number), "nonfinite_json_constant")
        return number
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def read_bound(root: Path, entry: dict) -> bytes:
    require(isinstance(entry, dict) and set(entry) == {"path", "bytes", "sha256"},
            "malformed_or_unblinded_file_descriptor")
    path = safe_path(root, entry["path"])
    require(type(entry["bytes"]) is int and entry["bytes"] > 0, "invalid_evidence_size")
    raw = path.read_bytes()
    require((len(raw), hashlib.sha256(raw).hexdigest()) == (entry["bytes"], entry["sha256"]),
            "evidence_file_hash_mismatch")
    return raw


def footage(evidence, reference: str) -> tuple:
    require(isinstance(evidence, dict) and text(reference) and evidence.get("reference") == reference,
            "missing_or_inconsistent_footage_reference")
    start, end = evidence.get("start_seconds"), evidence.get("end_seconds")
    require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
                for v in (start, end)) and 0 <= start < end, "invalid_footage_range")
    return start, end


def integer(value):
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number.is_integer() and number > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def validate_annotation(annotation: dict, review: dict, plan: dict, game: dict,
                        ledger: dict, slot: str, frozen_at) -> dict:
    require(annotation.get("schema_version") == ANNOTATION_VERSION, "annotation_schema_mismatch")
    for key in (*BINDINGS, "game_id", "source_file", "source_sha256", "source_member"):
        require(annotation.get(key) == (plan[key] if key in BINDINGS else game[key]),
                "annotation_identity_mismatch")
    require(annotation.get("reviewer_slot") == slot, "annotation_reviewer_slot_mismatch")
    for key in ("reviewer_id", "reviewer_kind", "started_at", "completed_at", "evidence_ref",
                "full_game_reviewed", "independent", "material_discrepancy", "critical_unresolved"):
        require(annotation.get(key) == review.get(key), "annotation_metadata_mismatch")
    require(annotation.get("reviewer_kind") == "human" and text(annotation.get("reviewer_id")),
            "explicit_human_reviewer_required")
    require(annotation.get("independent") is True and annotation.get("full_game_reviewed") is True,
            "independent_full_game_review_required")
    require(frozen_at < timestamp(annotation["started_at"]) <= timestamp(annotation["completed_at"]),
            "annotation_not_after_freeze")
    require(type(annotation.get("material_discrepancy")) is bool
            and annotation.get("critical_unresolved") is False, "incomplete_or_critical_verdict")
    events = ledger["events"]
    refs = [e["ref"] for e in events]
    require(bool(refs) and len(refs) == len(set(refs)), "duplicate_or_empty_ledger_refs")
    positions = {ref: i for i, ref in enumerate(refs)}
    periods, teams = {}, set()
    for event in events:
        period = integer(event["raw"].get("period"))
        require(period is not None, "unknown_source_period")
        periods.setdefault(period, []).append(event["ref"])
        for key in ("teamId", "possession"):
            team = integer(event["raw"].get(key))
            if team is not None:
                teams.add(team)
    coverage = annotation.get("coverage")
    require(isinstance(coverage, dict) and coverage.get("continuous_full_game") is True,
            "continuous_full_game_coverage_required")
    labels = coverage.get("periods")
    require(isinstance(labels, list) and len(labels) == len(periods), "all_source_periods_required")
    require([p["period"] for p in labels] == list(periods), "source_period_coverage_mismatch")
    period_times, previous_period_end = {}, -1
    for label in labels:
        require(type(label["period"]) is int, "invalid_period_label")
        source_refs = periods[label["period"]]
        require(label["start_ref"] == source_refs[0] and label["end_ref"] == source_refs[-1],
                "incomplete_period_range")
        start_time, end_time = footage(label.get("evidence"), review["evidence_ref"])
        require(start_time >= previous_period_end, "overlapping_or_unordered_period_footage")
        previous_period_end = end_time
        period_times[label["period"]] = (start_time, end_time)
    possessions = annotation.get("possessions")
    require(isinstance(possessions, list) and bool(possessions), "completed_possessions_required")
    covered, foul_refs, last_end, material = [], [], -1, False
    signature = []
    previous_start_time, previous_end_time = -1, -1
    for possession in possessions:
        start, end = possession["start_ref"], possession["end_ref"]
        require(start in positions and end in positions, "unknown_possession_event_ref")
        lo, hi = positions[start], positions[end]
        require(last_end < lo <= hi, "reversed_overlapping_or_unordered_possessions")
        range_refs = refs[lo:hi + 1]
        require(len({integer(events[i]["raw"].get("period")) for i in range(lo, hi + 1)}) == 1,
                "possession_crosses_source_period")
        last_end = hi
        offense, defense = possession.get("offense_team_id"), possession.get("defense_team_id")
        require(type(offense) is int and type(defense) is int and offense != defense
                and offense in teams and defense in teams, "unknown_or_invalid_team_assignment")
        require(possession.get("uncertain") is False and possession.get("critical_unresolved", False) is False,
                "uncertain_possession_blocks_evidence")
        require(type(possession.get("material_discrepancy")) is bool, "missing_possession_verdict")
        material |= possession["material_discrepancy"]
        counted = possession.get("counted_foul_refs")
        require(isinstance(counted, list) and all(r in range_refs for r in counted), "unknown_or_outside_foul_ref")
        require(len(counted) == len(set(counted)), "duplicate_foul_ref")
        for ref in counted:
            require(str(events[positions[ref]]["raw"].get("actionType", "")).lower() == "foul",
                    "counted_ref_is_not_raw_foul")
        foul_refs.extend(counted)
        start_time, end_time = footage(possession.get("evidence"), review["evidence_ref"])
        period_start, period_end = period_times[integer(events[lo]["raw"]["period"])]
        require(period_start <= start_time < end_time <= period_end, "possession_footage_outside_period")
        require(start_time >= previous_start_time, "possession_footage_out_of_order")
        require(start_time >= previous_end_time or text(possession.get("footage_overlap_note")),
                "overlapping_possession_footage_requires_note")
        previous_start_time, previous_end_time = start_time, end_time
        covered.extend(range_refs)
        signature.append({k: possession[k] for k in ("start_ref", "end_ref", "offense_team_id",
                                                    "defense_team_id", "counted_foul_refs", "material_discrepancy", "uncertain")}
                         | {"critical_unresolved": possession.get("critical_unresolved", False)})
    exclusions = annotation.get("excluded_events")
    require(isinstance(exclusions, list), "explicit_nonpossession_labels_required")
    for exclusion in exclusions:
        require(exclusion["ref"] in positions, "unknown_excluded_event_ref")
        require(exclusion.get("reason") in {"administrative", "no_possession"}, "invalid_exclusion_reason")
        require(exclusion.get("uncertain") is False and exclusion.get("critical_unresolved", False) is False,
                "uncertain_exclusion_blocks_evidence")
        require(type(exclusion.get("material_discrepancy")) is bool, "missing_exclusion_verdict")
        material |= exclusion["material_discrepancy"]
        start_time, end_time = footage(exclusion.get("evidence"), review["evidence_ref"])
        period_start, period_end = period_times[integer(events[positions[exclusion["ref"]]]["raw"]["period"])]
        require(period_start <= start_time < end_time <= period_end, "excluded_event_footage_outside_period")
        covered.append(exclusion["ref"])
    require(material == annotation["material_discrepancy"], "inconsistent_material_verdict")
    require(Counter(covered) == Counter(refs), "missing_or_duplicate_event_labels")
    require(len(foul_refs) == len(set(foul_refs)), "duplicate_foul_ref")
    return {"labels_sha256": digest({"possessions": signature,
                                    "excluded_events": [{k: e[k] for k in ("ref", "reason", "material_discrepancy", "uncertain")}
                                                        | {"critical_unresolved": e.get("critical_unresolved", False)}
                                                        for e in exclusions]})}


def validate_delivered_kits(root: Path, manifest: dict, plan: dict) -> None:
    """Validate everything fixed and delivered to each blinded reviewer."""
    require(set(manifest["reviewer_kits"]) == {"A", "B"}, "missing_or_unknown_reviewer_kit")
    for slot in ("A", "B"):
        kit = root / f"reviewer_{slot}"
        entry = manifest["reviewer_kits"][slot]
        require(set(entry) == {"manifest_file"}
                and entry["manifest_file"]["path"] == f"reviewer_{slot}/manifest.json",
                "invalid_reviewer_manifest_path")
        redacted = load_json(read_bound(root, entry["manifest_file"]))
        require(set(redacted) == {"schema_version", "reviewer_slot", "status", *BINDINGS,
                                  "protocol_file", "instructions_file", "games"},
                "unblinded_or_malformed_reviewer_manifest")
        require(redacted["schema_version"] == "blinded-review-kit-v1"
                and redacted["reviewer_slot"] == slot and redacted["status"] == "PREPARATION_ONLY"
                and all(redacted[k] == plan[k] for k in BINDINGS), "reviewer_manifest_identity_mismatch")
        require(redacted["protocol_file"]["path"] == "protocol.md"
                and redacted["instructions_file"]["path"] == "INSTRUCTIONS.md", "invalid_delivered_instructions_path")
        read_bound(kit, redacted["protocol_file"])
        read_bound(kit, redacted["instructions_file"])
        require(all(redacted["protocol_file"][k] == manifest["protocol_file"][k]
                    for k in ("bytes", "sha256")), "delivered_protocol_differs_from_frozen_protocol")
        expected_games = []
        for game in manifest["games"]:
            gid = game["game_id"]
            require(game["ledgers"][slot]["path"] == f"reviewer_{slot}/raw_events/{gid}.json",
                    "invalid_reviewer_ledger_path")
            expected_games.append({
                **{k: game[k] for k in ("game_id", "source_file", "source_sha256", "source_member",
                                        "official_game_url", "official_url_status", "access_status")},
                "continuous_coverage": "unverified",
                "ledger": {**game["ledgers"][slot], "path": f"raw_events/{gid}.json"},
                "annotation_path": f"annotations/{gid}.json"})
        require(redacted["games"] == expected_games, "reviewer_manifest_games_or_descriptors_mismatch")
        for game in redacted["games"]:
            read_bound(kit, game["ledger"])


def _validate(plan: dict, reviews: dict, config: dict, root: Path) -> dict:
    reasons = validate_plan(plan)
    require(not reasons, "invalid_audit_plan")
    gate = check_gate(plan, reviews, config)
    # Statistical/tolerance requirements remain the public gate's responsibility,
    # but missing provenance or review structure must also fail this importer.
    require(gate["status"] == "PASS_CONDITIONAL", "metadata_audit_gate_blocked")
    manifest_path = root / "manifest.json"
    require(file_digest(manifest_path)[1] == config.get("packet_manifest_sha256"), "packet_not_bound_to_freeze")
    manifest = load_json(manifest_path.read_bytes())
    require(manifest.get("schema_version") == "review-packet-v1", "packet_schema_mismatch")
    require(all(manifest.get(k) == plan[k] for k in BINDINGS), "packet_binding_mismatch")
    bound_plan = load_json(read_bound(root, manifest["plan_file"]))
    require(bound_plan == plan, "packet_plan_mismatch")
    read_bound(root, manifest["protocol_file"])
    require(manifest["protocol_file"]["sha256"] == config.get("protocol_sha256"), "protocol_not_bound_to_freeze")
    selected = {g["game_id"]: g for g in plan["games"]}
    games = manifest["games"]
    require(len(games) == len(selected) and {g["game_id"] for g in games} == set(selected),
            "packet_selected_games_mismatch")
    validate_delivered_kits(root, manifest, plan)
    records = {r["game_id"]: r for r in reviews["games"]}
    frozen_at = timestamp(config["frozen_at"])
    consumed, review_results, identities, annotations = set(), [], {}, []
    for item in games:
        gid = item["game_id"]
        game = selected[gid]
        require(all(item[k] == game[k] for k in ("source_file", "source_sha256", "source_member")),
                "packet_source_mismatch")
        signatures = []
        ledgers = {}
        for slot in ("A", "B"):
            ledger = load_json(read_bound(root, item["ledgers"][slot]))
            require(ledger.get("schema_version") == "raw-review-ledger-v1" and all(
                ledger.get(k) == game[k] for k in ("game_id", "source_file", "source_sha256", "source_member")),
                "ledger_identity_mismatch")
            previous_row = 1
            for event in ledger["events"]:
                require(event["member"] == game["source_member"] and type(event["row"]) is int
                        and event["row"] >= 2 and event["ref"] == f'{event["member"]}:{event["row"]}',
                        "ledger_event_identity_mismatch")
                require(event["row"] > previous_row, "ledger_rows_out_of_order")
                previous_row = event["row"]
                require(integer(event["raw"].get("actionNumber")) == event["event_id"]
                        or str(event["raw"].get("actionNumber")) == "0" and event["event_id"] == 0,
                        "ledger_raw_event_mismatch")
                require(str(event["raw"]["gameId"]).zfill(10) == gid, "ledger_raw_game_mismatch")
            ledgers[slot] = ledger
        require(ledgers["A"] == ledgers["B"], "reviewer_ledger_mismatch")
        record = records[gid]
        judgments = [("A", record["reviewers"][0]), ("B", record["reviewers"][1])]
        if record.get("adjudication") is not None:
            judgments.append(("C", record["adjudication"]))
        for slot, review in judgments:
            name = review["reviewer_id"].strip().casefold()
            require(name not in identities or identities[name] == slot, "reviewer_identity_reused_across_roles")
            identities[name] = slot
            require(review["annotation_ref"] not in consumed, "duplicate_annotation_path")
            consumed.add(review["annotation_ref"])
            entry = {"path": review["annotation_ref"], "bytes": review["annotation_bytes"],
                     "sha256": review["annotation_sha256"]}
            annotation = load_json(read_bound(root, entry))
            result = validate_annotation(annotation, review, plan, game, ledgers["A" if slot == "C" else slot], slot, frozen_at)
            if slot == "C":
                resolution = annotation.get("adjudication")
                require(isinstance(resolution, dict) and resolution.get("resolved") is True
                        and text(resolution.get("rationale"))
                        and resolution.get("rationale") == review.get("rationale")
                        and resolution.get("original_annotation_sha256") == [r["annotation_sha256"] for r in record["reviewers"]],
                        "adjudication_must_bind_original_annotations")
                footage(resolution.get("evidence"), review["evidence_ref"])
            signatures.append(result["labels_sha256"])
            review_results.append({"game_id": gid, "reviewer_slot": slot, **result, **entry})
            annotations.append(entry)
        require(len(set(signatures[:2])) == 1 or len(judgments) == 3, "label_disagreement_requires_adjudication")
    return {"ok": True, "reasons": [], "annotations": review_results,
            "packet_manifest_sha256": file_digest(manifest_path)[1],
            "protocol_sha256": manifest["protocol_file"]["sha256"], "annotations_sha256": digest(annotations)}


def validate_evidence(plan: dict, reviews: dict, config: dict, evidence_root: Path) -> dict:
    """Read and hash actual files; malformed or empty evidence yields BLOCKED."""
    try:
        result = _validate(plan, reviews, config, Path(evidence_root))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        result = {"ok": False, "reasons": [str(exc) if isinstance(exc, InvalidEvidence)
                                           else "malformed_or_missing_evidence_file"]}
    return {"schema_version": "human-review-evidence-validation-v1", **result,
            "status": "STRUCTURALLY_COMPLETE" if result["ok"] else "BLOCKED",
            "limitations": "Structural checks only. Human identity, independence, truthful attestations, footage authenticity and scientific correctness are not authenticated."}



REVIEW_METADATA = ("reviewer_id", "reviewer_kind", "started_at", "completed_at", "evidence_ref",
                   "full_game_reviewed", "independent", "material_discrepancy", "critical_unresolved")


def collect_evidence(evidence_root: Path, config_path: Path, output: Path) -> dict:
    """Collect existing submissions without inventing or changing human evidence.

    Read canonical reviewer_A/B/annotations/<game_id>.json and optional
    adjudications/<game_id>.json (slot C). Derive metadata and exact byte hashes
    from actual files. Incomplete/critical submissions remain failed evidence in
    collection_report.json and originals stay untouched. A game enters reviews.json
    only when both original annotations and any supplied adjudication pass structural
    checks. audit_evidence.json stores evidence_root relative to its own directory;
    a consumer must resolve that path against the bundle location, never its cwd.
    No evaluation-start timestamp or scientific acceptance is generated.
    """
    root, output = Path(evidence_root), Path(output)
    # Fail before reading or writing anything when an output already exists.
    output.mkdir(parents=True, exist_ok=False)
    plan, config, reviews = None, None, {"games": []}
    submissions, collection_reasons = [], []
    try:
        config = load_json(config_path.read_bytes())
        manifest_path = root / "manifest.json"
        manifest_bytes = manifest_path.read_bytes()
        require(hashlib.sha256(manifest_bytes).hexdigest() == config.get("packet_manifest_sha256"),
                "packet_not_bound_to_freeze")
        manifest = load_json(manifest_bytes)
        require(manifest.get("schema_version") == "review-packet-v1", "packet_schema_mismatch")
        plan = load_json(read_bound(root, manifest["plan_file"]))
        require(not validate_plan(plan), "invalid_audit_plan")
        require(all(manifest.get(k) == plan[k] == config.get(k) for k in BINDINGS), "packet_binding_mismatch")
        read_bound(root, manifest["protocol_file"])
        require(manifest["protocol_file"]["sha256"] == config.get("protocol_sha256"),
                "protocol_not_bound_to_freeze")
        require(config.get("frozen") is True and config.get("review_data_status_at_freeze") == "unseen",
                "tolerances_not_frozen_before_review")
        frozen_at = timestamp(config.get("frozen_at"))
        require(len(manifest["games"]) == len(plan["games"])
                and {g["game_id"] for g in manifest["games"]} == {g["game_id"] for g in plan["games"]},
                "packet_selected_games_mismatch")
        validate_delivered_kits(root, manifest, plan)
        reviews.update({k: plan[k] for k in BINDINGS})
        packet_games = {g["game_id"]: g for g in manifest["games"]}
        for game in plan["games"]:
            gid = game["game_id"]
            original_reviews, adjudication, game_failed = [], None, False
            paths = [(slot, f"reviewer_{slot}/annotations/{gid}.json") for slot in ("A", "B")]
            adjudication_path = f"adjudications/{gid}.json"
            if (root / adjudication_path).exists() or (root / adjudication_path).is_symlink():
                paths.append(("C", adjudication_path))
            for slot, relative in paths:
                submission = {"game_id": gid, "reviewer_slot": slot, "path": relative, "status": "FAILED"}
                try:
                    path = safe_path(root, relative)
                    raw = path.read_bytes()
                    submission.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                    annotation = load_json(raw)
                    require(isinstance(annotation, dict), "annotation_object_required")
                    submission["submitted_metadata"] = {k: annotation[k] for k in REVIEW_METADATA if k in annotation}
                    require(all(k in annotation for k in REVIEW_METADATA), "incomplete_submitted_metadata")
                    review = {k: annotation[k] for k in REVIEW_METADATA}
                    review.update(annotation_ref=relative, annotation_bytes=len(raw),
                                  annotation_sha256=submission["sha256"])
                    if slot == "C":
                        resolution = annotation.get("adjudication")
                        require(isinstance(resolution, dict), "adjudication_must_bind_original_annotations")
                        review["rationale"] = resolution.get("rationale")
                    ledger_slot = "A" if slot == "C" else slot
                    ledger = load_json(read_bound(root, packet_games[gid]["ledgers"][ledger_slot]))
                    require(all(ledger.get(k) == game[k] for k in
                                ("game_id", "source_file", "source_sha256", "source_member")),
                            "ledger_identity_mismatch")
                    validate_annotation(annotation, review, plan, game, ledger, slot, frozen_at)
                    if slot == "C":
                        require(len(original_reviews) == 2 and resolution.get("resolved") is True
                                and text(resolution.get("rationale"))
                                and resolution.get("original_annotation_sha256") == [r["annotation_sha256"] for r in original_reviews],
                                "adjudication_must_bind_original_annotations")
                        footage(resolution.get("evidence"), review["evidence_ref"])
                        adjudication = review
                    else:
                        original_reviews.append(review)
                    submission.update(status="STRUCTURALLY_COMPLETE", reasons=[])
                except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
                    reason = str(exc) if isinstance(exc, InvalidEvidence) else "malformed_or_missing_annotation_file"
                    submission["reasons"] = [reason]
                    collection_reasons.append(reason)
                    game_failed = True
                submissions.append(submission)
            if not game_failed and len(original_reviews) == 2:
                record = {"game_id": gid, "source_sha256": game["source_sha256"], "reviewers": original_reviews}
                if adjudication is not None:
                    record["adjudication"] = adjudication
                reviews["games"].append(record)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        collection_reasons.append(str(exc) if isinstance(exc, InvalidEvidence) else "malformed_or_missing_collection_input")
    validation = validate_evidence(plan, reviews, config, root)
    reasons = sorted(set(collection_reasons + validation["reasons"]))
    result = {"schema_version": "human-review-collection-v1", "ok": not reasons,
              "status": "STRUCTURALLY_COMPLETE" if not reasons else "BLOCKED", "reasons": reasons,
              "completed_game_entries": len(reviews["games"]), "submissions": submissions,
              "limitations": validation["limitations"]}
    write_json(output / "reviews.json", reviews)
    write_json(output / "audit_evidence.json", {"plan": plan, "reviews": reviews, "config": config,
                                               "evidence_root": Path(os.path.relpath(root.resolve(), output.resolve())).as_posix(),
                                               "evidence_root_relative_to": "audit_evidence_file"})
    write_json(output / "evidence_validation.json", validation)
    write_json(output / "collection_report.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "import", "collect"),
                        help="collect derives metadata from existing packet annotations and writes a portable bundle")
    for name in ("plan", "reviews", "config", "evidence-root", "output"):
        parser.add_argument("--" + name, type=Path, required=name not in {"plan", "reviews"})
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            result = collect_evidence(args.evidence_root, args.config, args.output)
        else:
            if args.plan is None or args.reviews is None:
                parser.error("validate/import require --plan and --reviews")
            plan, reviews, config = (load_json(path.read_bytes()) for path in (args.plan, args.reviews, args.config))
            result = validate_evidence(plan, reviews, config, args.evidence_root)
            write_artifact(args.output, "evidence_validation.json", result)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"review evidence error: {exc}\n")
    print(json.dumps({"status": result["status"], "reasons": result["reasons"]}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
