"""Synthetic positives only test structure; adversarial files must stay blocked."""

import json

import pytest

from whistle_research.audit import ASSUMPTION
from whistle_research.review_evidence import main, validate_evidence
from whistle_research.sources import file_digest
from tests.v2.test_review_packet import synthetic_packet


def completed_synthetic_evidence(tmp_path):
    """Return plan/reviews/config/root for integration tests, explicitly synthetic."""
    plan, root, manifest = synthetic_packet(tmp_path)
    game = manifest["games"][0]
    binding = {k: plan[k] for k in ("plan_sha256", "parser_version", "parser_sha256")}
    config = {**binding, "frozen": True, "freeze_id": "synthetic-only",
              "frozen_at": "2026-01-01T00:00:00Z", "review_data_status_at_freeze": "unseen",
              "confidence": .95, "max_game_error_rate": .99, "min_random_games": 1,
              "sample_assumption": ASSUMPTION,
              "packet_manifest_sha256": file_digest(root / "manifest.json")[1],
              "protocol_sha256": manifest["protocol_file"]["sha256"]}
    evidence = {"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 10}
    reviewers = []
    for slot in ("A", "B"):
        path = root / f"reviewer_{slot}/annotations/{game['game_id']}.json"
        annotation = json.loads(path.read_text())
        annotation.update(reviewer_id=f"synthetic-human-{slot}", reviewer_kind="human",
                          started_at="2026-01-01T12:00:00Z", completed_at="2026-01-02T00:00:00Z",
                          evidence_ref=evidence["reference"], full_game_reviewed=True, independent=True,
                          material_discrepancy=False, critical_unresolved=False,
                          coverage={"continuous_full_game": True, "periods": [
                              {"period": 1, "start_ref": "events.csv:2", "end_ref": "events.csv:3", "evidence": evidence},
                              {"period": 2, "start_ref": "events.csv:4", "end_ref": "events.csv:5", "evidence": {**evidence, "start_seconds": 10, "end_seconds": 20}}]},
                          possessions=[{"start_ref": f"events.csv:{n}", "end_ref": f"events.csv:{n+1}",
                                        "offense_team_id": 10, "defense_team_id": 20,
                                        "counted_foul_refs": ["events.csv:3"] if n == 2 else [],
                                        "uncertain": False, "material_discrepancy": False,
                                        "evidence": {**evidence, "start_seconds": 0 if n == 2 else 10, "end_seconds": 10 if n == 2 else 20}}
                                       for n in (2, 4)])
        path.write_text(json.dumps(annotation))
        size, sha = file_digest(path)
        reviewers.append({k: annotation[k] for k in ("reviewer_id", "reviewer_kind", "started_at", "completed_at",
                                                    "evidence_ref", "full_game_reviewed", "independent",
                                                    "material_discrepancy", "critical_unresolved")})
        reviewers[-1].update(annotation_ref=path.relative_to(root).as_posix(), annotation_bytes=size, annotation_sha256=sha)
    reviews = {**binding, "games": [{"game_id": game["game_id"], "source_sha256": game["source_sha256"],
                                   "reviewers": reviewers}]}
    return plan, reviews, config, root


def mutate_annotation(root, review, mutation):
    path = root / review["annotation_ref"]
    annotation = json.loads(path.read_text())
    mutation(annotation)
    path.write_text(json.dumps(annotation))
    review["annotation_bytes"], review["annotation_sha256"] = file_digest(path)


def test_positive_synthetic_full_game_contract(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    result = validate_evidence(plan, reviews, config, root)
    assert result["ok"], result
    assert len(result["annotations"]) == 2
    assert len(result["annotations_sha256"]) == 64
    assert "not authenticated" in result["limitations"]


@pytest.mark.parametrize("mutation,reason", [
    (lambda a: a.update(possessions=[]), "completed_possessions_required"),
    (lambda a: a.update(coverage=None), "continuous_full_game_coverage_required"),
    (lambda a: a["coverage"]["periods"].pop(), "all_source_periods_required"),
    (lambda a: a["coverage"]["periods"][0].update(end_ref="events.csv:2"), "incomplete_period_range"),
    (lambda a: a["possessions"][0].update(start_ref="events.csv:999"), "unknown_possession_event_ref"),
    (lambda a: a["possessions"][0].update(start_ref="events.csv:3", end_ref="events.csv:2"), "reversed_overlapping_or_unordered_possessions"),
    (lambda a: a["possessions"].reverse(), "reversed_overlapping_or_unordered_possessions"),
    (lambda a: a["possessions"][1].update(start_ref="events.csv:3"), "reversed_overlapping_or_unordered_possessions"),
    (lambda a: a["possessions"][1].update(end_ref="events.csv:4"), "missing_or_duplicate_event_labels"),
    (lambda a: a["possessions"][0].update(uncertain=True), "uncertain_possession_blocks_evidence"),
    (lambda a: a["possessions"][0].update(counted_foul_refs=["events.csv:2"]), "counted_ref_is_not_raw_foul"),
    (lambda a: a["possessions"][0].update(counted_foul_refs=["events.csv:3", "events.csv:3"]), "duplicate_foul_ref"),
    (lambda a: a["possessions"][0].update(counted_foul_refs=["events.csv:5"]), "unknown_or_outside_foul_ref"),
    (lambda a: a["possessions"][0].update(offense_team_id=999), "unknown_or_invalid_team_assignment"),
    (lambda a: a["possessions"][0].update(material_discrepancy=True), "inconsistent_material_verdict"),
    (lambda a: a["possessions"][0].update(evidence={"reference": "words only"}), "missing_or_inconsistent_footage_reference"),
    (lambda a: a.update(source_sha256="0" * 64), "annotation_identity_mismatch"),
    (lambda a: a.update(reviewer_kind="parser"), "annotation_metadata_mismatch"),
    (lambda a: a.update(excluded_events=[{"ref": "events.csv:2", "reason": "administrative", "uncertain": False, "material_discrepancy": False,
                                        "evidence": {"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 1}}]),
     "missing_or_duplicate_event_labels"),
])
def test_mutated_actual_contents_fail_even_after_rehash(tmp_path, mutation, reason):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    mutate_annotation(root, reviews["games"][0]["reviewers"][0], mutation)
    result = validate_evidence(plan, reviews, config, root)
    assert not result["ok"]
    assert reason in result["reasons"]


@pytest.mark.parametrize("target", ["annotation", "ledger", "protocol", "manifest"])
def test_byte_tampering_blocks(tmp_path, target):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    paths = {"annotation": root / reviews["games"][0]["reviewers"][0]["annotation_ref"],
             "ledger": root / "reviewer_A/raw_events/0022400001.json", "protocol": root / "protocol.md",
             "manifest": root / "manifest.json"}
    with paths[target].open("ab") as stream:
        stream.write(b" ")
    assert not validate_evidence(plan, reviews, config, root)["ok"]


def test_frozen_hashes_paths_and_normalized_identity(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    config.pop("protocol_sha256")
    assert validate_evidence(plan, reviews, config, root)["reasons"] == ["protocol_not_bound_to_freeze"]
    config["protocol_sha256"] = file_digest(root / "protocol.md")[1]
    review = reviews["games"][0]["reviewers"][0]
    review["annotation_ref"] = "../escape.json"
    assert not validate_evidence(plan, reviews, config, root)["ok"]


def test_labels_disagree_despite_same_summary_need_adjudication(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    mutate_annotation(root, reviews["games"][0]["reviewers"][0],
                      lambda a: a["possessions"][0].update(offense_team_id=20, defense_team_id=10))
    assert validate_evidence(plan, reviews, config, root)["reasons"] == ["label_disagreement_requires_adjudication"]


def test_cli_templates_block_without_modifying_originals(tmp_path, capsys):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    review = reviews["games"][0]["reviewers"][0]
    mutate_annotation(root, review, lambda a: a.update(possessions=[], coverage=None))
    before = (root / review["annotation_ref"]).read_bytes()
    paths = []
    for name, value in (("plan", plan), ("reviews", reviews), ("config", config)):
        path = tmp_path / f"{name}-input.json"
        path.write_text(json.dumps(value))
        paths.extend(["--" + name, str(path)])
    result = main(["import", *paths, "--evidence-root", str(root), "--output", str(tmp_path / "validation")])
    assert result == 1
    assert "BLOCKED" in capsys.readouterr().out
    assert (root / review["annotation_ref"]).read_bytes() == before
    assert json.loads((tmp_path / "validation/evidence_validation.json").read_text())["ok"] is False


def test_explicit_exclusions_can_cover_nonpossession_rows(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    def label(annotation):
        annotation["possessions"][1]["end_ref"] = "events.csv:4"
        annotation["excluded_events"] = [{"ref": "events.csv:5", "reason": "administrative", "uncertain": False, "material_discrepancy": False,
                                            "evidence": {"reference": "synthetic-footage-only",
                                                         "start_seconds": 10, "end_seconds": 12}}]
    for review in reviews["games"][0]["reviewers"]:
        mutate_annotation(root, review, label)
    assert validate_evidence(plan, reviews, config, root)["ok"]


def test_third_annotation_must_bind_preserved_originals(tmp_path):
    import copy
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    record = reviews["games"][0]
    mutate_annotation(root, record["reviewers"][0],
                      lambda a: a["possessions"][0].update(offense_team_id=20, defense_team_id=10))
    adjudicator = copy.deepcopy(record["reviewers"][1])
    adjudicator.update(reviewer_id="synthetic-adjudicator-C", annotation_ref="adjudication.json",
                       rationale="Synthetic evidence-based resolution only", completed_at="2026-01-03T00:00:00Z")
    annotation = json.loads((root / record["reviewers"][1]["annotation_ref"]).read_text())
    annotation.update(reviewer_slot="C", reviewer_id=adjudicator["reviewer_id"], completed_at=adjudicator["completed_at"])
    (root / "adjudication.json").write_text(json.dumps(annotation))
    adjudicator["annotation_bytes"], adjudicator["annotation_sha256"] = file_digest(root / "adjudication.json")
    record["adjudication"] = adjudicator
    assert validate_evidence(plan, reviews, config, root)["reasons"] == ["adjudication_must_bind_original_annotations"]
    annotation["adjudication"] = {"resolved": True, "rationale": adjudicator["rationale"],
                                  "original_annotation_sha256": [r["annotation_sha256"] for r in record["reviewers"]],
                                  "evidence": {"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 10}}
    (root / "adjudication.json").write_text(json.dumps(annotation))
    adjudicator["annotation_bytes"], adjudicator["annotation_sha256"] = file_digest(root / "adjudication.json")
    assert validate_evidence(plan, reviews, config, root)["ok"]


@pytest.mark.parametrize("mutation", ["normalized_identity", "nonhuman", "timestamp", "symlink", "empty_file", "duplicate_key"])
def test_identity_and_file_attacks(tmp_path, mutation):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    a, b = reviews["games"][0]["reviewers"]
    if mutation == "normalized_identity":
        b["reviewer_id"] = "  " + a["reviewer_id"].upper() + "  "
        mutate_annotation(root, b, lambda annotation: annotation.update(reviewer_id=b["reviewer_id"]))
    elif mutation == "nonhuman":
        a["reviewer_kind"] = "model"
        mutate_annotation(root, a, lambda annotation: annotation.update(reviewer_kind="model"))
    elif mutation == "timestamp":
        mutate_annotation(root, a, lambda annotation: annotation.update(completed_at="2027-01-01T00:00:00Z"))
    else:
        path = root / a["annotation_ref"]
        if mutation == "symlink":
            outside = tmp_path / "outside.json"
            outside.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(outside)
        elif mutation == "empty_file":
            path.write_text("")
            a["annotation_bytes"], a["annotation_sha256"] = file_digest(path)
        else:
            raw = path.read_text()
            path.write_text('{"reviewer_kind":"model",' + raw[1:])
            a["annotation_bytes"], a["annotation_sha256"] = file_digest(path)
    assert not validate_evidence(plan, reviews, config, root)["ok"]


@pytest.mark.parametrize("mutation,reason", [
    (lambda a: a["coverage"]["periods"][1].update(evidence={"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 10}), "overlapping_or_unordered_period_footage"),
    (lambda a: a["possessions"][1].update(evidence={"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 10}), "possession_footage_outside_period"),
])
def test_temporal_coverage_consistency(tmp_path, mutation, reason):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    mutate_annotation(root, reviews["games"][0]["reviewers"][0], mutation)
    assert validate_evidence(plan, reviews, config, root)["reasons"] == [reason]


@pytest.mark.parametrize("delivered_file", ["protocol.md", "INSTRUCTIONS.md", "manifest.json"])
def test_delivered_reviewer_material_tampering_blocks(tmp_path, delivered_file):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    with (root / "reviewer_A" / delivered_file).open("ab") as stream:
        stream.write(b"\nChanged delivered reviewer instructions.\n")
    assert not validate_evidence(plan, reviews, config, root)["ok"]


def test_exclusion_verdict_is_part_of_complete_label_signature(tmp_path):
    from whistle_research.audit import timestamp
    from whistle_research.review_evidence import validate_annotation
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    signatures = []
    ledger = json.loads((root / "reviewer_A/raw_events/0022400001.json").read_text())
    for slot, review in zip(("A", "B"), reviews["games"][0]["reviewers"], strict=True):
        annotation = json.loads((root / review["annotation_ref"]).read_text())
        annotation["material_discrepancy"] = review["material_discrepancy"] = True
        annotation["possessions"][0]["material_discrepancy"] = True
        annotation["possessions"][1]["end_ref"] = "events.csv:4"
        annotation["excluded_events"] = [{"ref": "events.csv:5", "reason": "administrative",
                                            "uncertain": False, "material_discrepancy": slot == "A",
                                            "evidence": {"reference": "synthetic-footage-only",
                                                         "start_seconds": 10, "end_seconds": 20}}]
        result = validate_annotation(annotation, review, plan, plan["games"][0], ledger, slot,
                                     timestamp(config["frozen_at"]))
        signatures.append(result["labels_sha256"])
    assert signatures[0] != signatures[1]


def rebind_delivered_manifest(root, config, redacted):
    """Synthetic structural mutations only; never rewrite real freezes."""
    path = root / "reviewer_A/manifest.json"
    path.write_text(json.dumps(redacted))
    coordinator_path = root / "manifest.json"
    coordinator = json.loads(coordinator_path.read_text())
    size, sha = file_digest(path)
    coordinator["reviewer_kits"]["A"]["manifest_file"].update(bytes=size, sha256=sha)
    coordinator_path.write_text(json.dumps(coordinator))
    config["packet_manifest_sha256"] = file_digest(coordinator_path)[1]


@pytest.mark.parametrize("mutation,reason", [
    (lambda m: m.update(frame=[]), "unblinded_or_malformed_reviewer_manifest"),
    (lambda m: m.update(reviewer_slot="B"), "reviewer_manifest_identity_mismatch"),
    (lambda m: m["games"][0].update(source_sha256="0" * 64), "reviewer_manifest_games_or_descriptors_mismatch"),
    (lambda m: m["games"][0]["ledger"].update(path="../reviewer_B/raw_events/0022400001.json"), "reviewer_manifest_games_or_descriptors_mismatch"),
    (lambda m: m["games"][0].update(stratum="random"), "reviewer_manifest_games_or_descriptors_mismatch"),
    (lambda m: m["instructions_file"].update(model_score=.9), "malformed_or_unblinded_file_descriptor"),
])
def test_rehashed_delivered_manifest_remains_structurally_blinded(tmp_path, mutation, reason):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    redacted = json.loads((root / "reviewer_A/manifest.json").read_text())
    mutation(redacted)
    rebind_delivered_manifest(root, config, redacted)
    assert validate_evidence(plan, reviews, config, root)["reasons"] == [reason]


def test_rehashed_delivered_protocol_must_match_original_freeze(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    path = root / "reviewer_A/protocol.md"
    path.write_text("Undisclosed replacement protocol.\n")
    redacted = json.loads((root / "reviewer_A/manifest.json").read_text())
    size, sha = file_digest(path)
    redacted["protocol_file"].update(bytes=size, sha256=sha)
    rebind_delivered_manifest(root, config, redacted)
    assert validate_evidence(plan, reviews, config, root)["reasons"] == ["delivered_protocol_differs_from_frozen_protocol"]


def collection_fixture(tmp_path):
    plan, reviews, config, root = completed_synthetic_evidence(tmp_path)
    config_path = tmp_path / "frozen-config.json"
    config_path.write_text(json.dumps(config))
    return plan, reviews, config, root, config_path


def test_collect_derives_portable_bundle_from_actual_files(tmp_path):
    from pathlib import Path
    from whistle_research.review_evidence import collect_evidence
    plan, reviews, config, root, config_path = collection_fixture(tmp_path)
    originals = {p: p.read_bytes() for p in root.rglob("*.json")}
    output = tmp_path / "collected"
    result = collect_evidence(root, config_path, output)
    assert result["ok"], result
    assert result["completed_game_entries"] == 1
    assert [s["status"] for s in result["submissions"]] == ["STRUCTURALLY_COMPLETE"] * 2
    bundle = json.loads((output / "audit_evidence.json").read_text())
    assert bundle["plan"] == plan and bundle["reviews"] == reviews and bundle["config"] == config
    assert bundle["evidence_root_relative_to"] == "audit_evidence_file"
    assert not Path(bundle["evidence_root"]).is_absolute()
    assert (output / bundle["evidence_root"]).resolve() == root.resolve()
    assert "evaluation_started_at" not in bundle
    assert all(p.read_bytes() == before for p, before in originals.items())
    with pytest.raises(FileExistsError):
        collect_evidence(root, config_path, output)


def test_collect_blank_templates_produces_zero_completed_entries(tmp_path, capsys):
    _, root, manifest = synthetic_packet(tmp_path)
    from whistle_research.audit import ASSUMPTION
    config = {k: manifest[k] for k in ("plan_sha256", "parser_version", "parser_sha256")}
    config.update(frozen=True, freeze_id="synthetic-only", frozen_at="2026-01-01T00:00:00Z",
                  review_data_status_at_freeze="unseen", confidence=.95, max_game_error_rate=.99,
                  min_random_games=1, sample_assumption=ASSUMPTION,
                  packet_manifest_sha256=file_digest(root / "manifest.json")[1],
                  protocol_sha256=manifest["protocol_file"]["sha256"])
    config_path = tmp_path / "config-collect.json"
    config_path.write_text(json.dumps(config))
    output = tmp_path / "collected"
    assert main(["collect", "--evidence-root", str(root), "--config", str(config_path), "--output", str(output)]) == 1
    assert "BLOCKED" in capsys.readouterr().out
    report = json.loads((output / "collection_report.json").read_text())
    assert report["completed_game_entries"] == 0
    assert len(report["submissions"]) == 2
    assert all(s["status"] == "FAILED" for s in report["submissions"])
    assert json.loads((output / "reviews.json").read_text())["games"] == []


@pytest.mark.parametrize("mutation", ["game", "slot", "source", "critical", "missing", "bad_json", "packet_tampered"])
def test_collection_blocks_invalid_actual_submissions(tmp_path, mutation):
    from whistle_research.review_evidence import collect_evidence
    _, reviews, _, root, config_path = collection_fixture(tmp_path)
    path = root / reviews["games"][0]["reviewers"][0]["annotation_ref"]
    annotation = json.loads(path.read_text())
    if mutation in {"game", "slot", "source", "critical"}:
        key, value = {"game": ("game_id", "0022400999"), "slot": ("reviewer_slot", "B"),
                      "source": ("source_sha256", "0" * 64), "critical": ("critical_unresolved", True)}[mutation]
        annotation[key] = value
        path.write_text(json.dumps(annotation))
    elif mutation == "missing":
        path.unlink()
    elif mutation == "bad_json":
        path.write_text("not a completed annotation")
    else:
        (root / "reviewer_A/raw_events/0022400001.json").write_text("tampered ledger")
    before = path.read_bytes() if path.exists() else None
    output = tmp_path / "collected"
    result = collect_evidence(root, config_path, output)
    assert not result["ok"] and result["status"] == "BLOCKED"
    assert result["completed_game_entries"] == 0
    assert json.loads((output / "reviews.json").read_text())["games"] == []
    assert (path.read_bytes() if path.exists() else None) == before
    if mutation == "critical":
        failed = result["submissions"][0]
        assert failed["status"] == "FAILED"
        assert failed["submitted_metadata"]["critical_unresolved"] is True
        assert failed["sha256"] == file_digest(path)[1]


def test_collect_optional_adjudication_derives_bound_rationale(tmp_path):
    from whistle_research.review_evidence import collect_evidence
    _, reviews, _, root, config_path = collection_fixture(tmp_path)
    original_a, original_b = reviews["games"][0]["reviewers"]
    mutate_annotation(root, original_a,
                      lambda a: a["possessions"][0].update(offense_team_id=20, defense_team_id=10))
    annotation = json.loads((root / original_b["annotation_ref"]).read_text())
    annotation.update(reviewer_slot="C", reviewer_id="synthetic-adjudicator-C",
                      started_at="2026-01-02T01:00:00Z", completed_at="2026-01-03T00:00:00Z",
                      adjudication={"resolved": True, "rationale": "Synthetic recorded resolution only",
                                    "original_annotation_sha256": [r["annotation_sha256"] for r in (original_a, original_b)],
                                    "evidence": {"reference": "synthetic-footage-only", "start_seconds": 0, "end_seconds": 20}})
    folder = root / "adjudications"
    folder.mkdir()
    path = folder / "0022400001.json"
    path.write_text(json.dumps(annotation))
    result = collect_evidence(root, config_path, tmp_path / "collected")
    assert result["ok"], result
    collected = json.loads((tmp_path / "collected/reviews.json").read_text())["games"][0]["adjudication"]
    assert collected["rationale"] == annotation["adjudication"]["rationale"]
    assert collected["annotation_ref"] == "adjudications/0022400001.json"
    assert collected["annotation_sha256"] == file_digest(path)[1]
    annotation["adjudication"]["original_annotation_sha256"].reverse()
    path.write_text(json.dumps(annotation))
    blocked = collect_evidence(root, config_path, tmp_path / "blocked")
    assert not blocked["ok"] and blocked["completed_game_entries"] == 0
    assert "adjudication_must_bind_original_annotations" in blocked["reasons"]


def test_collect_cli_positive_and_no_overwrite(tmp_path, capsys):
    _, _, _, root, config_path = collection_fixture(tmp_path)
    output = tmp_path / "collected"
    args = ["collect", "--evidence-root", str(root), "--config", str(config_path), "--output", str(output)]
    assert main(args) == 0
    assert "STRUCTURALLY_COMPLETE" in capsys.readouterr().out
    before = (output / "audit_evidence.json").read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert (output / "audit_evidence.json").read_bytes() == before


def test_collect_overflowing_numeric_submission_still_writes_blocked_report(tmp_path):
    from whistle_research.review_evidence import collect_evidence
    _, reviews, _, root, config_path = collection_fixture(tmp_path)
    path = root / reviews["games"][0]["reviewers"][0]["annotation_ref"]
    path.write_text('{"reviewer_id": 1e999}')
    result = collect_evidence(root, config_path, tmp_path / "collected")
    assert not result["ok"] and result["completed_game_entries"] == 0
    assert "nonfinite_json_constant" in result["reasons"]
    assert (tmp_path / "collected/collection_report.json").is_file()
