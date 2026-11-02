"""Synthetic attestations test gate logic, never establish independent validation."""

import copy
import json

import pytest

from whistle_research.audit import (
    ASSUMPTION,
    check_gate,
    main,
    parser_digest,
    plan_digest,
    prepare_plan,
    upper_game_error_bound,
)


def packet(tmp_path, sample_size=2, enriched=True, coverage=True):
    inventory = {"kind": "game_inventory", "ok": True, "coverage": {
        "status": "schedule_checked" if coverage else "observed_only",
        "completeness": "accounted_for" if coverage else "unverified",
        "schedule_evidence": {"sha256": "f" * 64, "provenance": "synthetic external schedule"} if coverage else None},
        "games": [{"game_id": f"002240000{i}", "source_file": "fixture.tar.xz", "source_sha256": "a" * 64,
                   "source_member": "events.csv", "season": "2024-25", "game_type": "regular_season",
                   "disposition": "observed", "anomalies": []} for i in range(1, 5)]}
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(inventory))
    plan = prepare_plan(path, sample_size, 42, ["0022400002"] if enriched else [],
                        {"0022400002": "Synthetic retained-ball disagreement, fixture-7"} if enriched else {})
    binding = {k: plan[k] for k in ("plan_sha256", "parser_version", "parser_sha256")}
    config = {**binding, "frozen": True, "freeze_id": "synthetic-test-protocol",
              "frozen_at": "2026-01-01T00:00:00Z", "review_data_status_at_freeze": "unseen",
              "confidence": .95, "max_game_error_rate": .99, "min_random_games": sample_size,
              "sample_assumption": ASSUMPTION}
    reviews = {**binding, "games": []}
    for game in plan["games"]:
        reviewers = [{"reviewer_id": name, "evidence_ref": "synthetic-footage-ref", "annotation_ref": "synthetic-annotation",
                      "full_game_reviewed": True, "independent": True, "started_at": "2026-01-01T12:00:00Z",
                      "completed_at": "2026-01-02T00:00:00Z",
                      "material_discrepancy": False, "critical_unresolved": False} for name in ("reviewer-A", "reviewer-B")]
        adjudication = {"reviewer_id": "adjudicator-C", "evidence_ref": "synthetic-footage-ref", "rationale": "synthetic agreement",
                        "completed_at": "2026-01-03T00:00:00Z", "material_discrepancy": False, "critical_unresolved": False}
        reviews["games"].append({"game_id": game["game_id"], "source_sha256": game["source_sha256"],
                                 "reviewers": reviewers, "adjudication": adjudication})
    return plan, reviews, config, path


def test_seed_frame_plan_and_parser_hash_are_deterministic(tmp_path):
    plan, _, _, inventory = packet(tmp_path)
    assert plan == prepare_plan(inventory, 2, 42, ["0022400002"],
                                {"0022400002": "Synthetic retained-ball disagreement, fixture-7"})
    assert plan["plan_sha256"] == plan_digest(plan)
    assert plan["parser_sha256"] == parser_digest()
    assert plan["review_status"] == "absent"
    assert plan["protocol_status"] == "development_packet_not_locked"
    assert len({g["game_id"] for g in plan["games"]}) == len(plan["games"])
    assert [g["game_id"] for g in plan["games"] if g["stratum"] == "random"] == ["0022400001", "0022400004"]


def test_hand_known_exact_one_sided_bounds():
    assert upper_game_error_bound(0, 10, .95) == pytest.approx(1 - .05 ** .1)
    assert upper_game_error_bound(1, 2, .95) == pytest.approx(.95 ** .5)
    assert upper_game_error_bound(2, 2, .95) == 1
    for args in [(0, 0, .95), (3, 2, .95), (-1, 2, .95), (0, 2, 1), (0, 2, float("nan"))]:
        with pytest.raises(ValueError):
            upper_game_error_bound(*args)


def test_complete_synthetic_contract_only_yields_conditional_status(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "PASS_CONDITIONAL"
    assert result["random_games"] == 2
    assert result["upper_bound"] == pytest.approx(1 - .05 ** .5)
    assert "not authenticated" in result["limitations"]


def test_enriched_errors_are_not_pooled_into_random_bound(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    enriched = {g["game_id"] for g in plan["games"] if g["stratum"] == "enriched"}
    assert len(enriched) == 1
    for record in reviews["games"]:
        if record["game_id"] in enriched:
            record["reviewers"][0]["material_discrepancy"] = True
    result = check_gate(plan, reviews, config)
    assert result["random_games_with_material_discrepancy"] == 0
    assert result["upper_bound"] == pytest.approx(1 - .05 ** .5)
    assert result["completed_enriched_games"] == 1


@pytest.mark.parametrize("target,key", [("plan", "parser_sha256"), ("reviews", "parser_sha256"),
    ("config", "parser_sha256"), ("reviews", "plan_sha256"), ("plan", "parser_version")])
def test_wrong_or_missing_provenance_blocks(tmp_path, target, key):
    plan, reviews, config, _ = packet(tmp_path)
    {"plan": plan, "reviews": reviews, "config": config}[target].pop(key)
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


@pytest.mark.parametrize("change", ["frame", "selected_source", "duplicate_sample", "duplicate_reviewer", "duplicate_game", "missing_game", "wrong_source"])
def test_tampered_frames_duplicates_and_missing_records_block(tmp_path, change):
    plan, reviews, config, _ = packet(tmp_path)
    if change == "frame":
        plan["frame"][0]["source_sha256"] = "b" * 64
    elif change == "selected_source":
        plan["games"][0]["source_sha256"] = "b" * 64
    elif change == "duplicate_sample":
        plan["games"].append(copy.deepcopy(plan["games"][0]))
    elif change == "duplicate_reviewer":
        reviews["games"][0]["reviewers"][1]["reviewer_id"] = "reviewer-A"
    elif change == "duplicate_game":
        reviews["games"].append(copy.deepcopy(reviews["games"][0]))
    elif change == "missing_game":
        reviews["games"].pop()
    else:
        reviews["games"][0]["source_sha256"] = "b" * 64
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


@pytest.mark.parametrize("key,value", [("full_game_reviewed", False), ("independent", False),
    ("evidence_ref", ""), ("annotation_ref", ""), ("material_discrepancy", None), ("critical_unresolved", True),
    ("completed_at", "2025-12-01T00:00:00Z"), ("started_at", "2025-12-01T00:00:00Z"),
    ("started_at", None)])
def test_incomplete_unfrozen_or_critical_review_blocks(tmp_path, key, value):
    plan, reviews, config, _ = packet(tmp_path)
    reviews["games"][0]["reviewers"][0][key] = value
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


@pytest.mark.parametrize("change", ["absent", "same_reviewer", "no_rationale", "critical", "too_early"])
def test_third_named_adjudication_required(tmp_path, change):
    plan, reviews, config, _ = packet(tmp_path)
    record = reviews["games"][0]
    if change == "absent":
        record["reviewers"][0]["material_discrepancy"] = True
        record.pop("adjudication")
    elif change == "same_reviewer":
        record["adjudication"]["reviewer_id"] = "reviewer-A"
    elif change == "no_rationale":
        record["adjudication"]["rationale"] = ""
    elif change == "critical":
        record["adjudication"]["critical_unresolved"] = True
    else:
        record["adjudication"]["completed_at"] = "2026-01-01T12:00:00Z"
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


def test_conflicting_labels_cannot_choose_favorable_adjudication(tmp_path):
    plan, reviews, config, _ = packet(tmp_path, enriched=False)
    reviews["games"][0]["reviewers"][0]["material_discrepancy"] = True
    assert check_gate(plan, reviews, config)["random_games_with_material_discrepancy"] == 1


@pytest.mark.parametrize("key,value", [("confidence", None), ("max_game_error_rate", None), ("min_random_games", 0),
    ("frozen", False), ("freeze_id", ""), ("frozen_at", None), ("review_data_status_at_freeze", "seen"),
    ("sample_assumption", None), ("min_random_games", 100), ("max_game_error_rate", .01)])
def test_unset_tolerances_exposure_or_insufficient_evidence_blocks(tmp_path, key, value):
    plan, reviews, config, _ = packet(tmp_path)
    config[key] = value
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


def test_observed_source_inventory_is_not_schedule_evidence(tmp_path):
    plan, reviews, config, _ = packet(tmp_path, coverage=False)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "BLOCKED"
    assert "independent_schedule_coverage_unverified" in result["reasons"]
    assert result["inventory_coverage"]["status"] == "observed_only"


def test_plan_excludes_quarantined_inventory_and_rejects_unverified_input(tmp_path):
    _, _, _, inventory = packet(tmp_path)
    data = json.loads(inventory.read_text())
    data["games"][0]["disposition"] = "quarantined"
    inventory.write_text(json.dumps(data))
    plan = prepare_plan(inventory, 2, 42)
    assert "0022400001" not in {g["game_id"] for g in plan["frame"]}
    data["ok"] = False
    inventory.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        prepare_plan(inventory, 2, 42)


def test_cli_empty_reviews_create_blocked_report_and_cannot_overwrite(tmp_path):
    plan, _, _, inventory = packet(tmp_path)
    plan_dir = tmp_path / "packet"
    assert main(["plan", "--inventory", str(inventory), "--sample-size", "2", "--seed", "42", "--output", str(plan_dir)]) == 0
    reviews_path, config_path = tmp_path / "reviews.json", tmp_path / "config.json"
    reviews_path.write_text(json.dumps({"games": []}))
    config_path.write_text("{}")
    output = tmp_path / "gate"
    args = ["gate", "--plan", str(plan_dir / "plan.json"), "--reviews", str(reviews_path), "--config", str(config_path), "--output", str(output)]
    assert main(args) == 1
    saved = (output / "gate.json").read_bytes()
    assert json.loads(saved)["status"] == "BLOCKED"
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert (output / "gate.json").read_bytes() == saved


@pytest.mark.parametrize("plan,reviews,config", [({}, {}, {}), ([], {}, {}), ({"games": [None]}, {}, {})])
def test_malformed_evidence_fails_closed(plan, reviews, config):
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"


def rebind_packet(plan, reviews, config):
    plan["plan_sha256"] = plan_digest(plan)
    for obj in (reviews, config):
        obj["plan_sha256"] = plan["plan_sha256"]


@pytest.mark.parametrize("evidence", [{"sha256": None, "provenance": ""},
    {"sha256": "f" * 64, "provenance": "  "}, {"sha256": "broken", "provenance": "schedule"},
    "not a schedule provenance object"])
def test_empty_or_malformed_schedule_evidence_blocks(tmp_path, evidence):
    plan, reviews, config, _ = packet(tmp_path)
    plan["inventory_coverage"]["schedule_evidence"] = evidence
    rebind_packet(plan, reviews, config)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "BLOCKED"
    assert "independent_schedule_coverage_unverified" in result["reasons"]


def test_no_diagnostic_enriched_nomination_blocks(tmp_path):
    plan, reviews, config, _ = packet(tmp_path, enriched=False)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "BLOCKED"
    assert "enriched_diagnostic_sample_required" in result["reasons"]


@pytest.mark.parametrize("rationale", [{}, {"0022400002": "  "}, {"0022400003": "wrong game"}])
def test_missing_or_wrong_diagnostic_rationale_blocks(tmp_path, rationale):
    plan, reviews, config, _ = packet(tmp_path)
    plan["enriched_reasons"] = rationale
    rebind_packet(plan, reviews, config)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "BLOCKED"
    assert "missing_enriched_selection_rationale" in result["reasons"]


def test_diagnostic_nomination_can_overlap_random_without_changing_denominator(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    original_random = {g["game_id"] for g in plan["games"] if g["stratum"] == "random"}
    overlapping = min(original_random)
    plan["enriched_game_ids"] = [overlapping]
    plan["enriched_reasons"] = {overlapping: "Synthetic retained-ball ordering disagreement, evidence fixture-7"}
    plan["games"] = [g for g in plan["games"] if g["game_id"] in original_random]
    reviews["games"] = [g for g in reviews["games"] if g["game_id"] in original_random]
    rebind_packet(plan, reviews, config)
    result = check_gate(plan, reviews, config)
    assert result["status"] == "PASS_CONDITIONAL"
    assert result["random_games"] == 2
    assert result["enriched_games"] == result["completed_enriched_games"] == 1
    assert result["upper_bound"] == pytest.approx(1 - .05 ** .5)


@pytest.mark.parametrize("internal_hash", ["frame_sha256", "inventory_sha256"])
def test_source_observed_artifact_cannot_masquerade_as_schedule(tmp_path, internal_hash):
    plan, reviews, config, _ = packet(tmp_path)
    plan["inventory_coverage"]["schedule_evidence"] = {"sha256": plan[internal_hash], "provenance": "claimed schedule"}
    rebind_packet(plan, reviews, config)
    assert "independent_schedule_coverage_unverified" in check_gate(plan, reviews, config)["reasons"]


def test_cli_diagnostic_nominations_need_explicit_reason(tmp_path):
    _, _, _, inventory = packet(tmp_path)
    args = ["plan", "--inventory", str(inventory), "--sample-size", "2", "--seed", "42",
            "--enriched-game-id", "0022400002", "--output", str(tmp_path / "diagnostic_packet")]
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert main([*args, "--enriched-reason", "Synthetic difficult retained-ball sequence, fixture-7"]) == 0
    plan = json.loads((tmp_path / "diagnostic_packet" / "plan.json").read_text())
    assert plan["enriched_reasons"] == {"0022400002": "Synthetic difficult retained-ball sequence, fixture-7"}


def test_two_agreeing_independent_reviewers_need_no_adjudication(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    for record in reviews["games"]:
        record.pop("adjudication")
    assert check_gate(plan, reviews, config)["status"] == "PASS_CONDITIONAL"


def test_disagreeing_independent_reviewers_require_adjudication(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    reviews["games"][0]["reviewers"][0]["material_discrepancy"] = True
    reviews["games"][0].pop("adjudication")
    result = check_gate(plan, reviews, config)
    assert result["status"] == "BLOCKED"
    assert "third_named_adjudicator_required" in result["reasons"]


def test_agreement_with_invalid_optional_adjudication_still_blocks(tmp_path):
    plan, reviews, config, _ = packet(tmp_path)
    reviews["games"][0]["adjudication"] = "invalid optional record"
    assert check_gate(plan, reviews, config)["status"] == "BLOCKED"
