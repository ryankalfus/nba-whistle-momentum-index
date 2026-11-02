"""Prepare full-game review packets and conservatively check audit evidence.

Reviews JSON: {plan_sha256, parser_version, parser_sha256, games: [{game_id, source_sha256,
reviewers: [{reviewer_id, evidence_ref, annotation_ref, full_game_reviewed: true,
independent: true, started_at: ISO8601 with timezone, completed_at: ISO8601
with timezone, material_discrepancy: bool,
critical_unresolved: bool}], adjudication: {reviewer_id, evidence_ref, rationale,
completed_at, material_discrepancy: bool, critical_unresolved: bool}}]}.
Exactly two distinct independent reviewers are required for every game. A third
named adjudicator is required when their material/critical verdicts disagree;
optional adjudication records are validated whenever supplied. Original labels remain intact; disagreement cannot be
resolved by silently choosing a favorable label. Evidence references must identify
footage/log access and stored full-game annotations; this tool cannot verify the
truth of attestations or inspect those external materials.

Config JSON: {plan_sha256, parser_version, parser_sha256, frozen: true, freeze_id, frozen_at,
review_data_status_at_freeze: "unseen", confidence, max_game_error_rate,
min_random_games, sample_assumption: "random_games_represent_declared_cohort"}.
Tolerances must be frozen before review completion; timestamps and unseen status
are attestations, not proof. A packet alone never locks the scientific protocol.
Plans retain enriched_game_ids and enriched_reasons (game ID to nonblank documented
selection reason). At least one nominated diagnostic game is required for the
gate. CLI --enriched-reason supplies a common user-written rationale for nominated
IDs; programmatic callers may provide per-game reasons. These nominations are not
automatically validated evidence. Overlap with the random sample is retained in
both diagnostic accounting and the unchanged random denominator. Schedule coverage
requires an evidence object with a valid SHA256 and nonblank provenance; the
observed inventory/frame hash itself cannot be presented as schedule evidence.
"""

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import random

from scipy.stats import beta

from whistle_research.possessions import PARSER_VERSION
from whistle_research.sources import canonical_game_id, file_digest, write_artifact

PLAN_VERSION = "audit-plan-v1"
ASSUMPTION = "random_games_represent_declared_cohort"
SOURCE_KEYS = ("game_id", "source_file", "source_sha256", "source_member", "season", "game_type")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def parser_digest() -> str:
    return file_digest(Path(__file__).with_name("possessions.py"))[1]


def plan_digest(plan: dict) -> str:
    return digest({k: v for k, v in plan.items() if k != "plan_sha256"})


def valid_sha(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def prepare_plan(inventory_path: Path, sample_size: int, seed: int,
                 enriched_game_ids: list[str] | None = None,
                 enriched_reasons: dict[str, str] | None = None) -> dict:
    inventory = json.loads(inventory_path.read_text())
    if inventory.get("kind") != "game_inventory" or inventory.get("ok") is not True:
        raise ValueError("a successful source inventory is required")
    frame = sorted([{k: g[k] for k in SOURCE_KEYS} for g in inventory["games"]
                    if g.get("disposition") == "observed" and not g.get("anomalies")], key=lambda g: g["game_id"])
    ids = [g["game_id"] for g in frame]
    if len(ids) != len(set(ids)) or any(canonical_game_id(g) != g for g in ids):
        raise ValueError("duplicate/noncanonical frame game IDs")
    if any(not valid_sha(g["source_sha256"]) for g in frame):
        raise ValueError("unverified source hashes in frame")
    if type(sample_size) is not int or not 1 <= sample_size <= len(frame):
        raise ValueError("sample size must be within the observed eligible frame")
    enriched = sorted(set(canonical_game_id(g) for g in (enriched_game_ids or [])))
    if not set(enriched).issubset(ids):
        raise ValueError("enriched games must be in the eligible source frame")
    rationales = {canonical_game_id(k): v for k, v in (enriched_reasons or {}).items()}
    if set(rationales) != set(enriched) or any(not text(v) for v in rationales.values()):
        raise ValueError("each enriched game requires a documented selection reason")
    random_ids = set(random.Random(seed).sample(ids, sample_size))
    games = [{**g, "stratum": "random" if g["game_id"] in random_ids else "enriched",
              "inclusion_probability": sample_size / len(frame) if g["game_id"] in random_ids else None}
             for g in frame if g["game_id"] in random_ids | set(enriched)]
    plan = {"schema_version": PLAN_VERSION, "kind": "full_game_audit_plan",
            "protocol_status": "development_packet_not_locked", "parser_version": PARSER_VERSION,
            "parser_sha256": parser_digest(),
            "inventory_sha256": file_digest(inventory_path)[1],
            "inventory_coverage": inventory.get("coverage"), "seed": seed, "sample_size": sample_size,
            "selection_method": "simple_random_without_replacement_then_enriched_union",
            "frame": frame, "frame_sha256": digest(frame), "enriched_game_ids": enriched,
            "enriched_reasons": rationales,
            "games": games, "review_status": "absent", "unit": "full_game_any_material_discrepancy"}
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def upper_game_error_bound(errors: int, games: int, confidence: float) -> float:
    """Exact one-sided Clopper-Pearson upper, under the declared binomial model."""
    if type(games) is not int or type(errors) is not int or not 0 <= errors <= games or games < 1:
        raise ValueError("need positive games and integer errors within games")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly within (0,1)")
    if errors == games:
        return 1.0
    if errors == 0:
        return -math.expm1(math.log1p(-confidence) / games)
    return float(beta.ppf(confidence, errors + 1, games - errors))


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return result


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_plan(plan: dict) -> list[str]:
    reasons = []
    try:
        if plan.get("schema_version") != PLAN_VERSION or plan.get("plan_sha256") != plan_digest(plan):
            reasons.append("plan_hash_or_schema_mismatch")
        frame = plan["frame"]
        ids = [g["game_id"] for g in frame]
        if (frame != sorted(frame, key=lambda g: g["game_id"]) or len(ids) != len(set(ids))
                or any(canonical_game_id(g) != g for g in ids)
                or plan["frame_sha256"] != digest(frame)):
            reasons.append("invalid_sampling_frame")
        if (not valid_sha(plan["inventory_sha256"])
                or any(not valid_sha(g["source_sha256"]) or any(not text(g.get(k)) for k in SOURCE_KEYS) for g in frame)):
            reasons.append("missing_source_provenance")
        size = plan["sample_size"]
        if type(size) is not int or not 1 <= size <= len(frame):
            raise ValueError("invalid sample size")
        random_ids = set(random.Random(plan["seed"]).sample(ids, size))
        enriched = plan["enriched_game_ids"]
        if not enriched:
            reasons.append("enriched_diagnostic_sample_required")
        rationales = plan.get("enriched_reasons")
        if (not isinstance(rationales, dict) or set(rationales) != set(enriched)
                or any(not text(value) for value in rationales.values())):
            reasons.append("missing_enriched_selection_rationale")
        if len(enriched) != len(set(enriched)) or not set(enriched).issubset(ids):
            reasons.append("invalid_enriched_frame")
        expected = [{**g, "stratum": "random" if g["game_id"] in random_ids else "enriched",
                     "inclusion_probability": size / len(frame) if g["game_id"] in random_ids else None}
                    for g in frame if g["game_id"] in random_ids | set(enriched)]
        if plan["games"] != expected:
            reasons.append("sample_or_source_provenance_mismatch")
        if plan["parser_version"] != PARSER_VERSION or plan.get("parser_sha256") != parser_digest():
            reasons.append("wrong_parser_version")
    except (ValueError, TypeError, KeyError):
        reasons.append("malformed_plan")
    return reasons


def _check_gate(plan: dict, reviews: dict, config: dict) -> dict:
    reasons = validate_plan(plan)
    for obj, label in ((reviews, "review"), (config, "config")):
        if any(obj.get(k) != plan.get(k) for k in ("plan_sha256", "parser_version", "parser_sha256")):
            reasons.append(f"{label}_provenance_mismatch")
    frozen_at = None
    try:
        frozen_at = timestamp(config.get("frozen_at"))
        if config.get("frozen") is not True or not text(config.get("freeze_id")) or config.get("review_data_status_at_freeze") != "unseen":
            raise ValueError("not frozen before exposure")
    except (ValueError, TypeError):
        reasons.append("tolerances_not_frozen_before_review")
    confidence, tolerance, minimum = (config.get(k) for k in ("confidence", "max_game_error_rate", "min_random_games"))
    def numeric(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    settings_valid = (numeric(confidence) and 0 < confidence < 1 and numeric(tolerance) and 0 <= tolerance < 1
                      and type(minimum) is int and minimum > 0)
    if not settings_valid:
        reasons.append("missing_or_invalid_tolerances")
    if config.get("sample_assumption") != ASSUMPTION:
        reasons.append("random_sample_assumption_undeclared")
    coverage = plan.get("inventory_coverage") or {}
    schedule_evidence = coverage.get("schedule_evidence")
    if (coverage.get("status") != "schedule_checked" or coverage.get("completeness") != "accounted_for"
            or not isinstance(schedule_evidence, dict) or not valid_sha(schedule_evidence.get("sha256"))
            or not text(schedule_evidence.get("provenance"))
            or schedule_evidence.get("sha256") in {plan.get("frame_sha256"), plan.get("inventory_sha256")}):
        reasons.append("independent_schedule_coverage_unverified")
    selected = {g["game_id"]: g for g in plan.get("games", [])}
    records = reviews.get("games", [])
    if not isinstance(records, list):
        records = []
        reasons.append("malformed_reviews")
    seen, outcomes = set(), {}
    for record in records:
        try:
            game_id = record["game_id"]
            if game_id in seen or game_id not in selected:
                raise ValueError("duplicate_or_unselected_review_game")
            seen.add(game_id)
            if record.get("source_sha256") != selected[game_id]["source_sha256"]:
                raise ValueError("review_source_hash_mismatch")
            reviewers = record.get("reviewers", [])
            if len(reviewers) != 2 or len({r.get("reviewer_id") for r in reviewers}) != 2:
                raise ValueError("two_distinct_reviewers_required")
            adjudication = record.get("adjudication")
            agreement = all(reviewers[0].get(k) == reviewers[1].get(k)
                            for k in ("material_discrepancy", "critical_unresolved"))
            if adjudication is None and not agreement:
                raise ValueError("third_named_adjudicator_required")
            if adjudication is not None and (not isinstance(adjudication, dict)
                    or adjudication.get("reviewer_id") in {r.get("reviewer_id") for r in reviewers}):
                raise ValueError("third_named_adjudicator_required")
            judgments = [*reviewers, adjudication] if adjudication is not None else reviewers
            for review in judgments:
                if not all(text(review.get(k)) for k in ("reviewer_id", "evidence_ref")):
                    raise ValueError("missing_reviewer_or_footage_evidence")
                if type(review.get("material_discrepancy")) is not bool or type(review.get("critical_unresolved")) is not bool:
                    raise ValueError("incomplete_labels")
                completed = timestamp(review.get("completed_at"))
                if frozen_at is None or completed <= frozen_at:
                    raise ValueError("review_not_after_tolerance_freeze")
            if any(timestamp(r.get("started_at")) <= frozen_at or timestamp(r.get("started_at")) > timestamp(r["completed_at"]) for r in reviewers):
                raise ValueError("review_started_before_freeze_or_after_completion")
            if any(r.get("full_game_reviewed") is not True or r.get("independent") is not True or not text(r.get("annotation_ref")) for r in reviewers):
                raise ValueError("incomplete_independent_full_game_annotations")
            if adjudication is not None and not text(adjudication.get("rationale")):
                raise ValueError("missing_adjudication_rationale")
            if any(r["critical_unresolved"] for r in judgments):
                raise ValueError("critical_issue_requires_new_parser_and_fresh_evidence")
            if adjudication is not None and timestamp(adjudication["completed_at"]) < max(timestamp(r["completed_at"]) for r in reviewers):
                raise ValueError("adjudication_precedes_reviews")
            # Preserve any material error in either original review, even if adjudicated favorably.
            outcomes[game_id] = any(r["material_discrepancy"] for r in judgments)
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            reasons.append(str(exc))
    if seen != set(selected):
        reasons.append("missing_selected_game_reviews")
    random_ids = {g["game_id"] for g in selected.values() if g["stratum"] == "random"}
    enriched_ids = set(plan.get("enriched_game_ids", []))
    complete_random = random_ids & outcomes.keys()
    errors = sum(outcomes[g] for g in complete_random)
    upper = None
    if settings_valid and len(complete_random) == len(random_ids) and random_ids and config.get("sample_assumption") == ASSUMPTION:
        upper = upper_game_error_bound(errors, len(random_ids), confidence)
        if len(random_ids) < minimum:
            reasons.append("insufficient_random_games")
        if upper > tolerance:
            reasons.append("upper_game_error_bound_exceeds_tolerance")
    else:
        reasons.append("random_error_bound_unavailable")
    reasons = sorted(set(reasons))
    return {"schema_version": "audit-gate-v1", "kind": "independent_audit_gate",
            "status": "BLOCKED" if reasons else "PASS_CONDITIONAL", "reasons": reasons,
            "plan_sha256": plan.get("plan_sha256"), "parser_version": plan.get("parser_version"),
            "parser_sha256": plan.get("parser_sha256"),
            "reviews_sha256": digest(reviews), "config_sha256": digest(config), "inventory_coverage": coverage,
            "random_games": len(random_ids), "completed_random_games": len(complete_random),
            "random_games_with_material_discrepancy": errors, "upper_bound": upper, "confidence": confidence,
            "bound_method": "one_sided_Clopper_Pearson_binomial", "sample_assumption": config.get("sample_assumption"),
            "enriched_games": len(enriched_ids), "completed_enriched_games": len(enriched_ids & outcomes.keys()),
            "enriched_reasons": plan.get("enriched_reasons"),
            "limitations": "Attestations and external evidence are not authenticated. Game-level binomial model is assumed; enriched games are not pooled. Passing is necessary, not sufficient, for scientific release."}


def check_gate(plan: dict, reviews: dict, config: dict) -> dict:
    """Invalid evidence structures fail closed with a reviewable blocked report."""
    try:
        if not all(isinstance(value, dict) for value in (plan, reviews, config)):
            raise ValueError("evidence objects required")
        return _check_gate(plan, reviews, config)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return {"schema_version": "audit-gate-v1", "kind": "independent_audit_gate",
                "status": "BLOCKED", "reasons": ["malformed_evidence_structure"],
                "upper_bound": None, "limitations": "No scientific acceptance established."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--inventory", required=True, type=Path)
    plan.add_argument("--sample-size", required=True, type=int)
    plan.add_argument("--seed", required=True, type=int)
    plan.add_argument("--enriched-game-id", action="append", default=[])
    plan.add_argument("--enriched-reason", help="Documented diagnostic selection rationale for nominated games")
    gate = commands.add_parser("gate")
    for name in ("plan", "reviews", "config"):
        gate.add_argument(f"--{name}", required=True, type=Path)
    for command in (plan, gate):
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            rationales = {game_id: args.enriched_reason for game_id in args.enriched_game_id}
            result = prepare_plan(args.inventory, args.sample_size, args.seed, args.enriched_game_id, rationales)
        else:
            result = check_gate(*(json.loads(path.read_text()) for path in (args.plan, args.reviews, args.config)))
        write_artifact(args.output, f"{args.command}.json", result)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"audit input error: {exc}\n")
    return 1 if result.get("status") == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
