"""Bind human judgments to provisional rows; never alter either input.

Grouping rule admin-attachment-only-v1 ignores only actionType members of the
parser's ADMIN set when comparing source groups. It never removes possessions.
Exact counted-foul references verify attribution against supplied human labels;
raw subtype truth still requires external evidence. prediction_start fields match
features.build_rows at the declared before-state reference. score_difference is
defense score minus offense score; reference_ref is null only for period_start.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from itertools import zip_longest
import json
from pathlib import Path

from whistle_research import audit, features
from whistle_research.audit import digest
from whistle_research.possessions import ADMIN
from whistle_research.reconcile import metadata_rows
from whistle_research.review_evidence import (
    InvalidEvidence, load_json, read_bound, require, validate_annotation,
    validate_delivered_kits,
)
from whistle_research.review_packet import BINDINGS
from whistle_research.sources import safe_path

VERSION = "human-parser-comparison-v1"
GROUPING_RULE = "admin-attachment-only-v1"
LIMITS = ["raw_foul_subtype_truth_not_independently_labeled",
          "human_identity_footage_authenticity_and_label_truth_not_authenticated"]
START_FIELDS = ("period", "clock", "score_margin", "score_difference", "home_defense",
                "defense_counted_fouls", "previous_foul_1", "previous_foul_2", "start_type")


def _bound(root, path, consumed):
    raw = safe_path(root, path).read_bytes()
    consumed.append({"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return raw


def _reproduce(rows, ledger, metadata):
    """Re-run the parser against delivered raw bytes, without source repairs."""
    require(bool(rows), "comparison_missing_candidate_rows")
    events = ledger["events"]
    actions = [{key: None if value in ("", "NA", "NaN", "nan") else value
                for key, value in event["raw"].items()} for event in events]
    result = features._reconstruct_game(actions, ledger["game_id"], metadata, ledger["source_sha256"])
    reproduced_rows = features.build_rows(result, rows[0][0])
    require(reproduced_rows == [row for row, _ in rows], "reproduced_parser_feature_rows_mismatch")
    require(len(result.possessions) == len(rows), "reproduced_possession_count_mismatch")
    counted = []
    for possession, (_, trace) in zip(result.possessions, rows, strict=True):
        expected = {"game_id": result.game_id, "possession_number": possession.possession_number,
                    "source_rows": [events[index]["row"] for index in possession.source_rows],
                    "event_action_numbers": list(possession.event_action_numbers),
                    "reference_action_number": possession.start_state.reference_action_number,
                    "complete": possession.complete, "audit_flags": list(possession.audit_flags)}
        require(trace == expected, "reproduced_parser_provenance_mismatch")
        refs = []
        for action in possession.counted_foul_action_numbers:
            matches = [event["ref"] for event in events if event["event_id"] == action]
            require(len(matches) == 1, "missing_unique_counted_foul_reference_comparison")
            refs.append(matches[0])
        counted.append(refs)
    return counted


def _compare_game(rows, annotations, ledger, member, counted):
    events = ledger["events"]
    refs = [event["ref"] for event in events]
    positions = {ref: i for i, ref in enumerate(refs)}
    by_ref = {event["ref"]: event for event in events}
    administrative = {event["ref"] for event in events
                      if str(event["raw"].get("actionType", "")).lower() in ADMIN}
    results = []
    for slot, annotation in annotations:
        reasons, differences = [], []
        labels = annotation["possessions"]
        if len(labels) != len(rows):
            reasons.append("possession_count_mismatch")
        used = set()
        for index, ((row, trace), label) in enumerate(zip(rows, labels), 1):
            local = []
            candidate = [f"{member}:{number}" for number in trace["source_rows"]]
            human = refs[positions[label["start_ref"]]:positions[label["end_ref"]] + 1]
            if (len(candidate) != len(set(candidate)) or any(ref not in by_ref for ref in candidate)
                    or used.intersection(candidate)):
                local.append("unknown_or_duplicate_source_reference")
            used.update(candidate)
            if any(ref not in by_ref or by_ref[ref]["event_id"] != action
                   for ref, action in zip(candidate, trace["event_action_numbers"], strict=True)):
                local.append("source_action_identity_mismatch")
            if [ref for ref in candidate if ref not in administrative] != [ref for ref in human if ref not in administrative]:
                local.append("nonadministrative_source_group_mismatch")
            elif candidate != human:
                differences.append({"possession_number": index, "reason": "administrative_attachment_difference"})
            if (str(row["offense_team_id"]), str(row["defense_team_id"])) != (
                    str(label["offense_team_id"]), str(label["defense_team_id"])):
                local.append("offense_defense_mismatch")
            if type(row["outcome"]) is not int or row["outcome"] != int(bool(label["counted_foul_refs"])):
                local.append("binary_counted_foul_target_mismatch")
            if row["period"] != int(by_ref[label["start_ref"]]["raw"]["period"]):
                local.append("period_mismatch")
            if label["counted_foul_refs"] != counted[index - 1]:
                local.append("counted_foul_reference_mismatch")
            start = label.get("prediction_start")
            if not isinstance(start, dict) or not all(key in start for key in (*START_FIELDS, "reference_ref")):
                local.append("missing_independent_prediction_start_comparison")
            else:
                for key in START_FIELDS:
                    if type(start[key]) is not type(row[key]) or start[key] != row[key]:
                        if not (key == "clock" and type(start[key]) in (int, float)
                                and type(row[key]) in (int, float) and start[key] == row[key]):
                            local.append(f"prediction_start_{key}_mismatch")
                reference = trace["reference_action_number"]
                matches = [event["ref"] for event in events if event["event_id"] == reference]
                if reference is None:
                    if row["start_type"] != "period_start" or start["reference_ref"] is not None:
                        local.append("declared_start_reference_mismatch")
                elif len(matches) != 1:
                    local.append("missing_unique_declared_start_reference_comparison")
                elif matches[0] != start["reference_ref"]:
                    local.append("declared_start_reference_mismatch")
            reasons.extend(f"possession_{index}:{reason}" for reason in local)
        results.append({"reviewer_slot": slot, "ok": not reasons, "reasons": reasons,
                        "administrative_differences": differences})
    return results


def _compare(directory, plan, reviews, root, evidence, metadata, consumed):
    manifest_raw = _bound(directory, "manifest.json", consumed["features"])
    manifest = load_json(manifest_raw)
    require(metadata is not None, "missing_independent_metadata_comparison")
    metadata_paths = [Path(path) for path in metadata]
    metadata_snapshots = [(path, path.read_bytes()) for path in metadata_paths]
    historical, bindings = metadata_rows(metadata_paths)
    require([entry["sha256"] for entry in bindings]
            == [hashlib.sha256(raw).hexdigest() for _, raw in metadata_snapshots],
            "comparison_metadata_changed_during_read")
    require([{key: entry[key] for key in ("file", "sha256")} for entry in bindings]
            == [{key: entry[key] for key in ("file", "sha256")} for entry in manifest["historical_metadata"]],
            "comparison_metadata_binding_mismatch")
    consumed["metadata"] = bindings
    require(manifest["parser_sha256"] == audit.parser_digest()
            and manifest["feature_sha256"] == features.feature_module_sha256(), "comparison_implementation_changed")
    packet_raw = _bound(root, "manifest.json", consumed["evidence"])
    packet = load_json(packet_raw)
    require(evidence.get("schema_version") == "human-review-evidence-validation-v1"
            and evidence.get("ok") is True and evidence.get("status") == "STRUCTURALLY_COMPLETE",
            "successful_annotation_validation_required")
    require(evidence.get("packet_manifest_sha256") == hashlib.sha256(packet_raw).hexdigest(),
            "validated_packet_hash_mismatch")
    require(all(packet[k] == plan[k] == manifest[k] for k in BINDINGS if k != "plan_sha256")
            and packet["plan_sha256"] == plan["plan_sha256"], "comparison_parser_or_plan_mismatch")
    require(load_json(read_bound(root, packet["plan_file"])) == plan, "comparison_plan_file_mismatch")
    read_bound(root, packet["protocol_file"])
    require(evidence.get("protocol_sha256") == packet["protocol_file"]["sha256"], "validated_protocol_hash_mismatch")
    validate_delivered_kits(root, packet, plan)
    selected = {game["game_id"]: game for game in plan["games"]}
    games = {game["game_id"]: game for game in manifest["games"]}
    packet_games = {game["game_id"]: game for game in packet["games"]}
    require(len(packet_games) == len(packet["games"]) and set(packet_games) == set(selected), "comparison_selected_games_mismatch")
    records = {record["game_id"]: record for record in reviews["games"]}
    rows_by_game = defaultdict(list)
    row_hash, trace_hash, canonical = hashlib.sha256(), hashlib.sha256(), hashlib.sha256(b"[")
    counts = defaultdict(int)
    row_bytes, trace_bytes = 0, 0
    with safe_path(directory, manifest["rows_file"]).open("rb") as rows, safe_path(directory, manifest["row_provenance_file"]).open("rb") as traces:
        for number, pair in enumerate(zip_longest(rows, traces)):
            raw_row, raw_trace = pair
            require(raw_row is not None and raw_trace is not None, "comparison_stream_length_mismatch")
            row_bytes += len(raw_row)
            trace_bytes += len(raw_trace)
            row_hash.update(raw_row)
            trace_hash.update(raw_trace)
            row, trace = load_json(raw_row), load_json(raw_trace)
            gid = row["game_id"]
            counts[gid] += 1
            require((row["possession_number"], trace["game_id"], trace["possession_number"]) == (counts[gid], gid, counts[gid]), "comparison_row_order_mismatch")
            require(len(trace["source_rows"]) == len(trace["event_action_numbers"]), "comparison_source_alignment_mismatch")
            if number:
                canonical.update(b",")
            canonical.update(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())
            if gid in selected:
                rows_by_game[gid].append((row, trace))
    canonical.update(b"]")
    consumed["features"].extend([{"path": manifest["rows_file"], "bytes": row_bytes, "sha256": row_hash.hexdigest()},
                                  {"path": manifest["row_provenance_file"], "bytes": trace_bytes, "sha256": trace_hash.hexdigest()}])
    require(row_hash.hexdigest() == manifest["rows_file_sha256"] and trace_hash.hexdigest() == manifest["row_provenance_sha256"]
            and canonical.hexdigest() == manifest["rows_sha256"] and sum(counts.values()) == manifest["row_count"], "comparison_feature_bytes_mismatch")
    results, expected_annotations, descriptors = [], [], []
    for gid, game in selected.items():
        item = packet_games[gid]
        require(all(game[key] == item[key] == games[gid][key] for key in ("source_file", "source_sha256", "source_member")), "comparison_source_identity_mismatch")
        ledgers = []
        for slot in ("A", "B"):
            descriptor = item["ledgers"][slot]
            ledger = load_json(read_bound(root, descriptor))
            consumed["evidence"].append(descriptor)
            require(all(ledger[key] == game[key] for key in ("game_id", "source_file", "source_sha256", "source_member")), "comparison_ledger_identity_mismatch")
            previous_row = 1
            for event in ledger["events"]:
                require(event["member"] == game["source_member"] and type(event["row"]) is int
                        and event["row"] > previous_row
                        and event["ref"] == f'{event["member"]}:{event["row"]}', "comparison_ledger_raw_reference_mismatch")
                require(str(event["raw"]["gameId"]).zfill(10) == gid
                        and int(event["raw"]["actionNumber"]) == event["event_id"], "comparison_ledger_raw_identity_mismatch")
                previous_row = event["row"]
            ledgers.append(ledger)
        require(ledgers[0] == ledgers[1], "comparison_reviewer_ledgers_mismatch")
        record = records[gid]
        judgments = list(zip(("A", "B"), record["reviewers"], strict=True))
        if record.get("adjudication") is not None:
            judgments.append(("C", record["adjudication"]))
        annotations = []
        for slot, review in judgments:
            descriptor = {"path": review["annotation_ref"], "bytes": review["annotation_bytes"], "sha256": review["annotation_sha256"]}
            annotation = load_json(read_bound(root, descriptor))
            # Repeat structural checks. The preceding validator owns freeze chronology;
            # its actual descriptors and label signatures must match below.
            signature = validate_annotation(annotation, review, plan, game, ledgers[0], slot, datetime.min.replace(tzinfo=timezone.utc))
            expected_annotations.append({"game_id": gid, "reviewer_slot": slot, **signature, **descriptor})
            descriptors.append(descriptor)
            consumed["evidence"].append(descriptor)
            annotations.append((slot, annotation))
        require(len(rows_by_game[gid]) == games[gid]["row_count"], "comparison_game_row_count_mismatch")
        try:
            counted = _reproduce(rows_by_game[gid], ledgers[0], historical[gid])
            comparisons = _compare_game(rows_by_game[gid], annotations, ledgers[0], game["source_member"], counted)
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
            reason = str(exc) if isinstance(exc, InvalidEvidence) else "missing_or_invalid_parser_reproduction"
            comparisons = [{"reviewer_slot": slot, "ok": False, "reasons": [reason]} for slot, _ in annotations]
        results.append({"game_id": gid, "reviews": comparisons})
    require(evidence.get("annotations") == expected_annotations and evidence.get("annotations_sha256") == digest(descriptors), "validated_annotation_descriptors_mismatch")
    require(all(path.read_bytes() == raw for path, raw in metadata_snapshots),
            "comparison_metadata_changed_during_comparison")
    reasons = [f'{game["game_id"]}:{review["reviewer_slot"]}:{reason}' for game in results for review in game["reviews"] for reason in review["reasons"]]
    return {"ok": not reasons, "reasons": reasons, "games": results, "consumed": consumed,
            "plan_sha256": digest(plan), "reviews_sha256": digest(reviews), "annotation_evidence_sha256": digest(evidence)}


def compare_annotations(directory, plan, reviews, evidence_root, annotation_evidence, *, metadata=None):
    """Re-read consumed bytes after structural/export validation; fail closed."""
    consumed = {"features": [], "evidence": []}
    implementation_hashes = {}
    try:
        implementation_paths = {"comparison": Path(__file__),
                                "parser": Path(audit.__file__).with_name("possessions.py"),
                                "feature": Path(features.__file__)}
        snapshots = {name: path.read_bytes() for name, path in implementation_paths.items()}
        implementation_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in snapshots.items()}
        consumed["implementation"] = [{"file": implementation_paths[name].name,
                                       "bytes": len(raw), "sha256": implementation_hashes[name]}
                                      for name, raw in snapshots.items()]
        result = _compare(Path(directory), plan, reviews, Path(evidence_root), annotation_evidence, metadata, consumed)
        require(all(path.read_bytes() == snapshots[name] for name, path in implementation_paths.items()),
                "comparison_implementation_changed_during_comparison")
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        result = {"ok": False, "reasons": [str(exc) if isinstance(exc, InvalidEvidence) else "malformed_or_missing_comparison_input"]}
    result = {"schema_version": VERSION, "grouping_rule": GROUPING_RULE, "limitations": LIMITS,
              "consumed": consumed, "comparison_module_sha256": implementation_hashes.get("comparison"),
              "implementation_sha256": implementation_hashes, **result}
    return {**result, "receipt_sha256": digest(result)}
