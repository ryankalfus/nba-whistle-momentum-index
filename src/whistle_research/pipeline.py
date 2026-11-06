"""One executable development pipeline; scientific release remains evidence-gated."""

import argparse
import json
import os
from pathlib import Path

from whistle_research import audit, features, modeling, reconcile, release, simulations, sources

BASE = Path("research/hypotheses_2026_09_12")
SCHEDULE = Path("research/rewrite_completion_2026_11_02/schedule_expected.json")
METADATA = [BASE / f"cdnnba_{cohort}_games.csv" for cohort in ("2020", "2021", "2022", "2023", "2024", "po_2024")]
ENRICHED = ("0022000181", "0022000254", "0022000925", "0022301177")
ENRICHED_REASON = "Historical backward-clock quarantine; independently inspect event order and corrected source state."


def audit_templates(plan):
    binding = {key: plan[key] for key in ("plan_sha256", "parser_version", "parser_sha256")}
    reviews = {**binding, "games": []}
    config = {**binding, "frozen": False, "freeze_id": None, "frozen_at": None,
              "review_data_status_at_freeze": None, "confidence": None, "max_game_error_rate": None,
              "min_random_games": None, "sample_assumption": None}
    return reviews, config


def run_pipeline(*, output, source_manifest=BASE / "source_manifest.json", cache=BASE / "cache",
                 metadata=METADATA, schedule=SCHEDULE, reuse_inventory=None, reuse_reconciliation=None,
                 reuse_features=None, reuse_math=None, reuse_models=None, seed=20261102,
                 sample_size=10, enriched=ENRICHED):
    """Complete diagnostics or fail on stale inputs; BLOCKED audit is expected.

    Reuse is explicit and validated against current bytes, code and complete
    frames. Feature/provenance streams are re-read without materializing all rows.
    """
    output, source_manifest, cache, schedule = map(Path, (output, source_manifest, cache, schedule))
    metadata = [Path(path) for path in metadata]
    if output.exists():
        raise FileExistsError("output exists; choose a new directory")
    verification = sources.verify_sources(source_manifest, cache)
    release.source_map(verification)
    output.mkdir(parents=True, exist_ok=False)
    release.write_json(output / "verification.json", verification)
    if reuse_inventory is None:
        schedule_packet = release.read_json(schedule)
        inventory = sources.inventory_sources(verification, cache, schedule, schedule_packet["provenance"])
    else:
        inventory = release.read_json(reuse_inventory)
    frame = release.verify_inventory(inventory, verification, schedule)
    release.write_json(output / "inventory.json", inventory)
    if reuse_reconciliation is None:
        reconstruction = reconcile.reconcile(source_manifest, cache, metadata, output / "reconciliation", 0)
        reconstruction_path = output / "reconciliation" / "report.json"
    else:
        reconstruction = release.read_json(reuse_reconciliation)
        reconstruction_path = Path(reuse_reconciliation)
    release.verify_reconciliation(reconstruction, verification, frame, metadata)
    feature_dir = Path(reuse_features) if reuse_features is not None else output / "features"
    if reuse_features is None:
        features.export(source_manifest, cache, metadata, schedule, feature_dir, 0)
    dataset, stream = release.verify_feature_export(feature_dir, verification, schedule, metadata, frame)
    diagnostic_games = {game["game_id"]: game for game in reconstruction["games"]}
    inventory_games = {game["game_id"]: game for game in inventory["games"]}
    for game in dataset["games"]:
        diagnostic = diagnostic_games[game["game_id"]]
        if (game["row_count"] != diagnostic.get("candidate_possessions", 0)
                or game.get("source_event_count") != inventory_games[game["game_id"]]["event_count"]
                or (game["status"] == "quarantined") != (diagnostic["status"] == "quarantined")):
            raise release.ArtifactError("inventory/reconciliation/feature per-game accounting mismatch")
    release.write_json(output / "feature_manifest.snapshot.json", dataset)
    release.write_json(output / "stream_verification.json", stream)
    plan = audit.prepare_plan(output / "inventory.json", sample_size, seed, list(enriched),
                              {gid: ENRICHED_REASON for gid in enriched})
    if plan["frame"] != frame or plan["frame_sha256"] != dataset["frame_sha256"]:
        raise release.ArtifactError("fresh audit plan does not bind the complete feature frame")
    reviews, config = audit_templates(plan)
    gate = audit.check_gate(plan, reviews, config)
    gate.update(selected_games=len(plan["games"]), review_records=0)
    for name, value in (("audit_plan.json", plan), ("audit_reviews.empty.json", reviews),
                        ("audit_config.unfrozen.json", config), ("audit_gate.json", gate)):
        release.write_json(output / name, value)
    readiness = {"status": "ANNOTATIONS_AND_TOLERANCES_REQUIRED", "plan_sha256": plan["plan_sha256"],
                 "selected_game_ids": [game["game_id"] for game in plan["games"]],
                 "random_game_ids": [game["game_id"] for game in plan["games"] if game["stratum"] == "random"],
                 "enriched_game_ids": plan["enriched_game_ids"], "independent_reviews": 0,
                 "tolerances_frozen": False, "protocol_frozen": False,
                 "limitations": "No invented reviewer identities, footage annotations, tolerance values or meaningful-effect threshold."}
    release.write_json(output / "audit_readiness.json", readiness)
    math = simulations.run_study(seed=seed) if reuse_math is None else release.read_json(reuse_math)
    models = modeling.synthetic_demo(seed=seed) if reuse_models is None else release.read_json(reuse_models)
    release.verify_synthetic(math, models)
    if math["seed"] != seed or models["seed"] != seed:
        raise release.ArtifactError("reused synthetic seed differs from declared run seed")
    release.write_json(output / "synthetic_math.json", math)
    release.write_json(output / "synthetic_models.json", models)
    paths = {"source_manifest": source_manifest, "schedule": schedule,
             "source_verification": output / "verification.json", "inventory": output / "inventory.json",
             "reconciliation": reconstruction_path, "feature_manifest": feature_dir / "manifest.json",
             "feature_rows": feature_dir / dataset["rows_file"],
             "feature_provenance": feature_dir / dataset["row_provenance_file"],
             "stream_verification": output / "stream_verification.json",
             "audit_plan": output / "audit_plan.json", "audit_reviews": output / "audit_reviews.empty.json",
             "audit_config": output / "audit_config.unfrozen.json", "audit_gate": output / "audit_gate.json",
             "audit_readiness": output / "audit_readiness.json", "math": output / "synthetic_math.json",
             "models": output / "synthetic_models.json", "pipeline_code": Path(__file__),
             "release_code": Path(release.__file__)}
    paths.update({f"historical_metadata_{index}": path for index, path in enumerate(metadata)})
    catalog = {key: release.artifact(path, output) for key, path in paths.items()}
    report = release.build_report(verification=verification, inventory=inventory,
                                  reconciliation=reconstruction, dataset=dataset, gate=gate,
                                  math=math, models=models, artifacts=catalog)
    release.write_report(output, report)
    return report


def promote_and_fit(*, feature_dir, audit_evidence, protocol, output, source_manifest, cache, schedule, metadata):
    """Separate explicit promotion; no caller can flip eligibility in old data.

    All included games must pass full-frame integrity/completeness requirements,
    then the existing model gate separately requires the frozen unused protocol.
    No output is created until every gate and actual fit succeeds.
    """
    output = Path(output)
    if output.exists():
        raise FileExistsError("output exists; choose a new directory")
    promoted, gate = release.prepare_promotion(
        feature_dir, plan=audit_evidence.get("plan"), reviews=audit_evidence.get("reviews"),
        config=audit_evidence.get("config"), source_manifest=source_manifest, cache=cache,
        schedule=schedule, metadata=metadata, evidence_root=audit_evidence.get("evidence_root"))
    original = release.read_json(Path(feature_dir) / "manifest.json")
    rows = modeling._read_rows(sources.safe_path(Path(feature_dir), original["rows_file"]))
    evidence = {"plan": audit_evidence["plan"], "reviews": audit_evidence["reviews"],
                "config": audit_evidence["config"], "dataset": promoted, "protocol": protocol,
                "source_root": os.path.relpath(Path(cache), Path.cwd()),
                "evaluation_started_at": audit_evidence.get("evaluation_started_at")}
    result = modeling.fit_real(rows, evidence=evidence)
    output.mkdir(parents=True, exist_ok=False)
    release.write_json(output / "evidence.json", evidence)
    release.write_json(output / "promoted_dataset.json", promoted)
    release.write_json(output / "audit_gate.json", gate)
    release.write_json(output / "model_result.json", result)
    return result


def _promotion_main(argv):
    parser = argparse.ArgumentParser(description="Strict conditional promotion and frozen-protocol real fit")
    for name in ("features", "audit-evidence", "protocol", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--source-manifest", type=Path, default=BASE / "source_manifest.json")
    parser.add_argument("--cache", type=Path, default=BASE / "cache")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE)
    parser.add_argument("--metadata", nargs="+", type=Path, default=METADATA)
    args = parser.parse_args(argv)
    try:
        audit_evidence = release.read_json(args.audit_evidence)
        if not isinstance(audit_evidence, dict):
            raise ValueError("audit evidence object required")
        path_base = audit_evidence.get("evidence_root_relative_to")
        if path_base not in (None, "audit_evidence_file"):
            raise ValueError("unknown annotation evidence path base")
        if path_base == "audit_evidence_file":
            root = Path(audit_evidence["evidence_root"])
            if not root.is_absolute():
                root = args.audit_evidence.parent / root
            audit_evidence["evidence_root"] = str(root.resolve())
        result = promote_and_fit(feature_dir=args.features, audit_evidence=audit_evidence,
                                 protocol=release.read_json(args.protocol), output=args.output,
                                 source_manifest=args.source_manifest, cache=args.cache,
                                 schedule=args.schedule, metadata=args.metadata)
    except (modeling.BlockedError, OSError, ValueError, TypeError, KeyError) as error:
        result = error.report if isinstance(error, modeling.BlockedError) else modeling.BlockedError([str(error)]).report
        print(json.dumps(result, indent=2, allow_nan=False))
        return 1
    print(json.dumps({"status": result["status"], "output": str(args.output)}, indent=2))
    return 0


def main(argv=None):
    import sys
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "promote":
        return _promotion_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-manifest", type=Path, default=BASE / "source_manifest.json")
    parser.add_argument("--cache", type=Path, default=BASE / "cache")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE)
    parser.add_argument("--metadata", nargs="+", type=Path, default=METADATA)
    for name in ("inventory", "reconciliation", "features", "math", "models"):
        parser.add_argument("--reuse-" + name, type=Path)
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument("--enriched-game-id", action="append")
    args = parser.parse_args(argv)
    try:
        report = run_pipeline(output=args.output, source_manifest=args.source_manifest, cache=args.cache,
                              schedule=args.schedule, metadata=args.metadata, seed=args.seed,
                              sample_size=args.sample_size,
                              enriched=args.enriched_game_id if args.enriched_game_id is not None else ENRICHED,
                              **{f"reuse_{name}": getattr(args, f"reuse_{name}")
                                 for name in ("inventory", "reconciliation", "features", "math", "models")})
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"software_status": "FAILED", "scientific_status": "BLOCKED", "reason": str(error)}, indent=2))
        return 1
    print(json.dumps({key: report[key] for key in ("software_status", "scientific_status", "counts")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
