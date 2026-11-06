"""Synthetic file comparisons establish fail-closed software behavior only."""

import json

import pytest

from tests.v2.test_release import synthetic_artifacts
from whistle_research import sources
from whistle_research.review_comparison import compare_annotations
from whistle_research.review_evidence import validate_evidence


def compare(fixture, evidence=None):
    if evidence is None:
        evidence = validate_evidence(fixture["plan"], fixture["reviews"], fixture["config"], fixture["evidence_root"])
    return compare_annotations(fixture["feature_dir"], fixture["plan"], fixture["reviews"], fixture["evidence_root"], evidence, metadata=fixture["metadata"])


def mutate_annotations(fixture, change):
    for record in fixture["reviews"]["games"]:
        for review in record["reviewers"]:
            path = fixture["evidence_root"] / review["annotation_ref"]
            annotation = json.loads(path.read_bytes())
            change(annotation)
            path.write_text(json.dumps(annotation))
            size, sha = sources.file_digest(path)
            review.update(annotation_bytes=size, annotation_sha256=sha)


def test_genuine_matching_synthetic_labels_have_bound_receipt(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    result = compare(fixture)
    assert result["ok"], result
    assert len(result["receipt_sha256"]) == 64
    assert result["consumed"]["features"][0]["path"] == "manifest.json"
    assert result == compare(fixture)


@pytest.mark.parametrize("change,reason", [("teams", "offense_defense_mismatch"), ("target", "binary_counted_foul_target_mismatch"), ("count", "possession_count_mismatch"), ("boundary", "nonadministrative_source_group_mismatch")])
def test_mutually_agreeing_but_wrong_annotations_block(tmp_path, change, reason):
    fixture = synthetic_artifacts(tmp_path)

    def alter(annotation):
        labels = annotation["possessions"]
        if change == "teams":
            for label in labels:
                label["offense_team_id"], label["defense_team_id"] = label["defense_team_id"], label["offense_team_id"]
        elif change == "target":
            next(label for label in labels if label["counted_foul_refs"])["counted_foul_refs"] = []
        else:
            first = labels.pop(0)
            labels[0]["start_ref"] = first["start_ref"]
            labels[0]["counted_foul_refs"] = first["counted_foul_refs"] + labels[0]["counted_foul_refs"]
            labels[0]["evidence"]["start_seconds"] = first["evidence"]["start_seconds"]

    mutate_annotations(fixture, alter)
    evidence = validate_evidence(fixture["plan"], fixture["reviews"], fixture["config"], fixture["evidence_root"])
    assert evidence["ok"], evidence
    result = compare(fixture, evidence)
    assert not result["ok"]
    assert any(reason in value for value in result["reasons"]), result


@pytest.mark.parametrize("target", ["rows.jsonl", "row_provenance.jsonl", "annotation", "ledger"])
def test_changed_bytes_after_validation_block(tmp_path, target):
    fixture = synthetic_artifacts(tmp_path)
    evidence = validate_evidence(fixture["plan"], fixture["reviews"], fixture["config"], fixture["evidence_root"])
    if target == "annotation":
        path = fixture["evidence_root"] / fixture["reviews"]["games"][0]["reviewers"][0]["annotation_ref"]
    elif target == "ledger":
        gid = fixture["reviews"]["games"][0]["game_id"]
        path = fixture["evidence_root"] / f"reviewer_A/raw_events/{gid}.json"
    else:
        path = fixture["feature_dir"] / target
    with path.open("ab") as stream:
        stream.write(b" ")
    assert not compare(fixture, evidence)["ok"]


def test_rehashed_source_mismatch_blocks(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    manifest_path = fixture["feature_dir"] / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    gid = fixture["plan"]["games"][0]["game_id"]
    next(game for game in manifest["games"] if game["game_id"] == gid)["source_member"] = "another.csv"
    manifest_path.write_text(json.dumps(manifest))
    result = compare(fixture)
    assert not result["ok"]
    assert result["reasons"] == ["comparison_source_identity_mismatch"]


def test_ok_flag_cannot_replace_actual_validation_descriptors(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    assert not compare(fixture, {"ok": True})["ok"]


@pytest.mark.parametrize("change,reason", [("missing", "missing_independent_prediction_start_comparison"), ("context", "prediction_start_score_difference_mismatch"), ("reference", "declared_start_reference_mismatch")])
def test_missing_or_contradictory_independent_start_inputs_block(tmp_path, change, reason):
    fixture = synthetic_artifacts(tmp_path)

    def alter(annotation):
        label = annotation["possessions"][0]
        if change == "missing":
            label.pop("prediction_start")
        elif change == "context":
            label["prediction_start"]["score_difference"] = 54321
        else:
            label["prediction_start"]["reference_ref"] = label["end_ref"]

    mutate_annotations(fixture, alter)
    result = compare(fixture)
    assert not result["ok"]
    assert any(reason in value for value in result["reasons"]), result


@pytest.mark.parametrize("target", ["row", "trace"])
def test_rehashed_candidate_changes_are_checked_against_raw_parser(tmp_path, target):
    fixture = synthetic_artifacts(tmp_path)
    filename = "rows.jsonl" if target == "row" else "row_provenance.jsonl"
    path = fixture["feature_dir"] / filename
    items = [json.loads(line) for line in path.read_text().splitlines()]
    gid = fixture["plan"]["games"][0]["game_id"]
    item = next(item for item in items if item["game_id"] == gid)
    if target == "row":
        item["outcome"] = 1 - item["outcome"]
    else:
        item["reference_action_number"] = 99999
    path.write_text("".join(json.dumps(item) + "\n" for item in items))
    manifest_path = fixture["feature_dir"] / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    key = "rows_file_sha256" if target == "row" else "row_provenance_sha256"
    manifest[key] = sources.file_digest(path)[1]
    if target == "row":
        from whistle_research.modeling import row_digest
        manifest["rows_sha256"] = row_digest(items)
    manifest_path.write_text(json.dumps(manifest))
    result = compare(fixture)
    assert not result["ok"]
    assert any("reproduced_parser" in reason for reason in result["reasons"]), result


def test_missing_metadata_has_explicit_block_reason(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    result = compare_annotations(fixture["feature_dir"], fixture["plan"], fixture["reviews"], fixture["evidence_root"], {})
    assert result["reasons"] == ["missing_independent_metadata_comparison"]


def test_only_administrative_attachment_difference_is_recorded_and_allowed(tmp_path):
    fixture = synthetic_artifacts(tmp_path)
    row_path = fixture["feature_dir"] / "rows.jsonl"
    original_rows = row_path.read_bytes()

    def attach(annotation):
        first = annotation["possessions"][0]
        admin = annotation["excluded_events"].pop(0)
        first["start_ref"] = admin["ref"]
        first["evidence"]["start_seconds"] = admin["evidence"]["start_seconds"]

    mutate_annotations(fixture, attach)
    result = compare(fixture)
    assert result["ok"], result
    assert all(review["administrative_differences"] for game in result["games"] for review in game["reviews"])
    assert row_path.read_bytes() == original_rows


def test_empty_administrative_opportunity_cannot_be_silently_dropped(tmp_path):
    fixture = synthetic_artifacts(tmp_path)

    def add_opportunity(annotation):
        admin = annotation["excluded_events"].pop(0)
        original = annotation["possessions"][0]
        label = {**original, "start_ref": admin["ref"], "end_ref": admin["ref"],
                 "counted_foul_refs": [], "evidence": admin["evidence"]}
        annotation["possessions"].insert(0, label)

    mutate_annotations(fixture, add_opportunity)
    result = compare(fixture)
    assert not result["ok"]
    assert any("possession_count_mismatch" in reason for reason in result["reasons"]), result


@pytest.mark.parametrize("target", ["implementation", "metadata"])
def test_in_run_source_or_metadata_mutation_blocks_receipt(tmp_path, monkeypatch, target):
    from whistle_research import features, review_comparison

    fixture = synthetic_artifacts(tmp_path)
    if target == "implementation":
        # Shadow the source path to exercise drift without editing live project code.
        path = tmp_path / "features.py"
        from pathlib import Path
        path.write_bytes(Path(features.__file__).read_bytes())
        monkeypatch.setattr(features, "__file__", str(path))
    else:
        path = fixture["metadata"][0]
    original = path.read_bytes()
    original_reproduce = review_comparison._reproduce
    changed = False

    def reproduce_and_mutate(*args):
        nonlocal changed
        result = original_reproduce(*args)
        if not changed:
            path.write_bytes(original + b"\n")
            changed = True
        return result

    monkeypatch.setattr(review_comparison, "_reproduce", reproduce_and_mutate)
    try:
        result = compare(fixture)
        assert changed
        assert not result["ok"]
        reason = ("comparison_implementation_changed_during_comparison" if target == "implementation"
                  else "comparison_metadata_changed_during_comparison")
        assert result["reasons"] == [reason], result
        if target == "implementation":
            import hashlib
            assert result["implementation_sha256"]["feature"] == hashlib.sha256(original).hexdigest()
            assert result["implementation_sha256"]["feature"] != sources.file_digest(path)[1]
    finally:
        path.write_bytes(original)
