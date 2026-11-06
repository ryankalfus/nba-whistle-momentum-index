"""Replay the delegated 1% audit design against the unchanged development frame.

Run from the repository root with the project environment. No review evidence,
eligibility, protocol freeze or external preregistration is created here.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from whistle_research import audit

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = Path("output/v2/development-pipeline-v7-2026-11-02")
SEED = 20261106
CONFIDENCE = .95
TOLERANCE = .01
PINNED = {
    "report.json": "31ed644257686112632bfa6a8235c9d00d0664bd0e8c6e90e14cca3f1ab8cbc8",
    "inventory.json": "473e0ac45f96ba3c2c78e3cea43b8af4c33cf291ca26ec4ae89099cf7308d2fc",
    "audit_plan.json": "f48cb8c663dfd27f6a0a8f90424f0012edc0196712f170cb6d8bfee14854ac95",
}
CODE_PINS = {
    "audit.py": "4352e95bffad7640a10d0539ed562c0b7eef7c3e8b2d567fb1c3703d1a1b157e",
    "possessions.py": "9ee7d5e81b5a99f0b42bf94e617269104bcb90e47f796af02fa4d0bb256d991f",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def minimum_zero_error_games(tolerance, confidence=CONFIDENCE):
    if not 0 < tolerance < 1:
        raise ValueError("tolerance must lie strictly within (0,1)")
    size = 1
    while audit.upper_game_error_bound(0, size, confidence) > tolerance:
        size += 1
    return size


def bind_inputs(raw):
    """Check exact input bytes and their roles; reject substitutes and stale runs."""
    for name, expected in PINNED.items():
        if sha(raw[name]) != expected:
            raise ValueError("pinned input drift: " + name)
    report, inventory, pilot = (json.loads(raw[name]) for name in PINNED)
    if report.get("schema_version") != "development-research-report-v1":
        raise ValueError("unknown development report schema")
    if (report.get("versions", {}).get("parser_sha256") != audit.parser_digest()
            or report["versions"].get("parser_version") != audit.PARSER_VERSION):
        raise ValueError("stale development parser")
    for name, role in (("inventory.json", "inventory"), ("audit_plan.json", "audit_plan")):
        binding = report.get("artifacts", {}).get(role, {})
        if binding.get("sha256") != sha(raw[name]) or binding.get("bytes") != len(raw[name]):
            raise ValueError("development report role binding mismatch: " + role)
    coverage = inventory.get("coverage", {})
    evidence = coverage.get("schedule_evidence", {})
    if (inventory.get("kind") != "game_inventory" or inventory.get("ok") is not True
            or inventory.get("source_failures") != []
            or coverage.get("status") != "schedule_checked"
            or coverage.get("completeness") != "accounted_for"
            or not audit.valid_sha(evidence.get("sha256"))
            or not audit.text(evidence.get("provenance"))
            or evidence["sha256"] != report.get("artifacts", {}).get("schedule", {}).get("sha256")):
        raise ValueError("unverified independent schedule/source inventory")
    if (len(inventory.get("games", [])) != 6084
            or any(g.get("disposition") != "observed" or g.get("anomalies") != []
                   or not audit.valid_sha(g.get("source_sha256")) for g in inventory["games"])):
        raise ValueError("full unchanged 6084-game source frame required")
    if audit.validate_plan(pilot) or pilot["sample_size"] != 10 or len(pilot["games"]) != 14:
        raise ValueError("invalid unchanged pilot")
    if pilot["inventory_sha256"] != sha(raw["inventory.json"]):
        raise ValueError("pilot inventory identity mismatch")
    return inventory, pilot


def prepare(input_dir, output):
    """Write a fresh plan and compact deterministic evidence; never overwrite."""
    if output.exists():
        raise FileExistsError("output already exists: " + str(output))
    code_dir = Path(audit.__file__).parent
    for name, expected in CODE_PINS.items():
        if sha((code_dir / name).read_bytes()) != expected:
            raise ValueError("pinned implementation drift: " + name)
    raw = {name: (input_dir / name).read_bytes() for name in PINNED}
    inventory, pilot = bind_inputs(raw)
    size = minimum_zero_error_games(TOLERANCE)
    plan = audit.prepare_plan(input_dir / "inventory.json", size, SEED,
                              pilot["enriched_game_ids"], pilot["enriched_reasons"])
    # prepare_plan reads a path: also bind the exact bytes it actually consumed.
    if plan["inventory_sha256"] != sha(raw["inventory.json"]) or audit.validate_plan(plan):
        raise ValueError("inventory changed during selection or invalid plan")
    if plan["frame"] != pilot["frame"] or plan["inventory_coverage"] != inventory["coverage"]:
        raise ValueError("pilot frame or coverage identity mismatch")
    random_ids = {g["game_id"] for g in plan["games"] if g["stratum"] == "random"}
    enriched = set(plan["enriched_game_ids"])
    pilot_ids = {g["game_id"] for g in pilot["games"]}
    ledger = {
        "schema_version": "audit-selected-games-v1", "plan_sha256": plan["plan_sha256"],
        "frame_sha256": plan["frame_sha256"], "games": [
            {**game, "in_random_sample": game["game_id"] in random_ids,
             "in_enriched_sample": game["game_id"] in enriched,
             "enriched_reason": plan["enriched_reasons"].get(game["game_id"])}
            for game in plan["games"]],
    }
    plan_raw, ledger_raw = encoded(plan), encoded(ledger)
    design = {
        "schema_version": "audit-design-evidence-v1", "date": "2026-11-06",
        "status": "DESIGN_SELECTED_FREEZE_PENDING", "audit_gate": "BLOCKED",
        "policy": {
            "decision": "1% maximum game-level material-error rate at 95% one-sided confidence",
            "authority": "Delegated research-lead policy judgment after user authorized the recommendation",
            "reason": "Prefer a stricter population game-error tolerance for research credibility",
            "qualification": "Policy choice, not a mathematical necessity or an external standard",
        },
        "settings": {"confidence": CONFIDENCE, "max_game_error_rate": TOLERANCE,
                     "min_random_games": size, "sample_assumption": audit.ASSUMPTION},
        "bound_method": "one_sided_Clopper_Pearson_binomial",
        "estimand": "Probability a game contains any material reconstruction discrepancy; not per-possession error",
        "assumption_limits": "Declared binomial game model; within-game dependence is not converted into independent possessions. No finite-population correction is used.",
        "zero_error_design_comparisons": [
            {"max_game_error_rate": rate, "minimum_random_games": n,
             "upper_bound_zero_errors": audit.upper_game_error_bound(0, n, CONFIDENCE),
             "upper_bound_one_fewer_zero_errors": audit.upper_game_error_bound(0, n - 1, CONFIDENCE)}
            for rate in (.01, .05, .10) for n in [minimum_zero_error_games(rate)]],
        "pilot": {"plan_sha256": pilot["plan_sha256"], "selected_games": len(pilot_ids),
                  "random_games": 10, "hypothetical_zero_error_upper_bound": audit.upper_game_error_bound(0, 10, CONFIDENCE),
                  "membership_unchanged": True, "overlap_with_new_random_ids": sorted(pilot_ids & random_ids),
                  "overlap_with_new_union_ids": sorted(pilot_ids & (random_ids | enriched)),
                  "interpretation": "Original 14-game development pilot preserved; overlap is disclosed, with no claim that this frame is an unseen confirmatory evaluation cohort"},
        "selection": {"seed": SEED, "frame_games": len(plan["frame"]),
                      "frame_sha256": plan["frame_sha256"], "plan_sha256": plan["plan_sha256"],
                      "random_games": len(random_ids), "enriched_games": len(enriched),
                      "random_enriched_overlap_ids": sorted(random_ids & enriched),
                      "unique_selected_games": len(plan["games"]),
                      "random_denominator": size, "enriched_reasons": plan["enriched_reasons"]},
        "inputs": {name: {"sha256": sha(value), "bytes": len(value)} for name, value in raw.items()},
        "implementation": {"prepare_design_sha256": sha(Path(__file__).read_bytes()),
                           "code_sha256": CODE_PINS, "parser_version": plan["parser_version"],
                           "python": sys.version.split()[0]},
        "outputs": {"audit_plan.json": {"sha256": sha(plan_raw), "bytes": len(plan_raw)},
                    "selected_games.json": {"sha256": sha(ledger_raw), "bytes": len(ledger_raw)}},
        "reproduce": ".venv/bin/python research/audit_handoff_2026_11_06/prepare_design.py --output output/v2/audit-design-2026-11-06-replay",
        "pending": ["Final protocol and packet hash freeze before annotation starts",
                    "Continuous footage coverage for every selected game",
                    "Two independent full-game annotations and required adjudication",
                    "Actual game-error bounds and gate evaluation; no completed annotations or eligibility created"],
        "freeze": {"frozen": False, "freeze_id": None, "final_protocol_packet_sha256": None,
                   "external_preregistration": None},
    }
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("audit_plan.json", plan_raw), ("selected_games.json", ledger_raw),
                        ("design.json", encoded(design))):
        with (output / name).open("xb") as stream:
            stream.write(value)
    return design


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        design = prepare(args.input, args.output)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"audit design input error: {exc}\n")
    print(json.dumps({"status": design["status"], **design["selection"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
