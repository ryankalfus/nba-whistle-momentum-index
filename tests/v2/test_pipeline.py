"""End-to-end synthetic integration and fail-closed promotion paths."""

import json
import shutil

import pytest

from whistle_research import audit, modeling, pipeline, release
from test_release import synthetic_artifacts


def run_args(fixture, output):
    return {"output": output, "source_manifest": fixture["source_manifest"], "cache": fixture["cache"],
            "metadata": fixture["metadata"], "schedule": fixture["schedule"],
            "reuse_inventory": fixture["inventory_path"], "reuse_reconciliation": fixture["reconciliation_path"],
            "reuse_features": fixture["feature_dir"], "reuse_math": fixture["math_path"],
            "reuse_models": fixture["model_path"], "sample_size": 2, "enriched": fixture["enriched"]}


def promotion_args(fixture, output):
    protocol = {key: fixture["plan"][key] for key in ("plan_sha256", "parser_version", "parser_sha256", "frame_sha256")}
    protocol.update(feature_version=fixture["dataset"]["feature_version"], feature_sha256=fixture["dataset"]["feature_sha256"],
                    rows_sha256=fixture["dataset"]["rows_sha256"], frozen=True, freeze_id="synthetic-model-fixture",
                    frozen_at="2029-02-01T00:00:00Z", evaluation_exposure="unseen_at_freeze",
                    exposure_inventory_ref="synthetic exposure fixture", unused_cohort_evidence_ref="synthetic unused fixture",
                    specification_sha256=audit.digest(modeling.specification()), meaningful_gain=.01,
                    split={"train_start": "2030-01-01", "tune_start": "2030-01-04",
                           "test_start": "2030-01-05", "test_end": "2030-01-07"})
    protocol["protocol_sha256"] = audit.digest(protocol)
    return {"feature_dir": fixture["feature_dir"], "audit_evidence": {
                "plan": fixture["plan"], "reviews": fixture["reviews"], "config": fixture["config"],
                "evaluation_started_at": "2031-01-01T00:00:00Z"},
            "protocol": protocol, "output": output, "source_manifest": fixture["source_manifest"],
            "cache": fixture["cache"], "schedule": fixture["schedule"], "metadata": fixture["metadata"]}


def test_explicit_reuse_completes_diagnostics_with_fresh_blocked_audit_and_bound_files(tmp_path):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    output = tmp_path / "run"
    report = pipeline.run_pipeline(**run_args(fixture, output))
    assert report["software_status"] == "DEVELOPMENT_RUN_COMPLETE"
    assert report["scientific_status"] == "BLOCKED"
    assert report["audit"]["status"] == "BLOCKED"
    assert report["counts"]["possession_rows"] == 144
    assert report["counts"]["eligible_games"] == 0
    assert release.read_json(output / "audit_reviews.empty.json")["games"] == []
    assert release.read_json(output / "audit_config.unfrozen.json")["frozen"] is False
    fresh = release.read_json(output / "audit_plan.json")
    assert fresh["parser_sha256"] == audit.parser_digest()
    assert {g["game_id"] for g in fresh["games"] if g["stratum"] == "random"} == {
        g["game_id"] for g in fixture["plan"]["games"] if g["stratum"] == "random"}
    for entry in report["artifacts"].values():
        assert pipeline.sources.file_digest(output / entry["path"]) == (entry["bytes"], entry["sha256"])
    assert "NOT EVALUATED" in (output / "draft_paper.md").read_text()
    with pytest.raises(FileExistsError):
        pipeline.run_pipeline(**run_args(fixture, output))


def test_fresh_path_orchestrates_all_full_selection_apis(tmp_path, monkeypatch):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    calls = []
    def inventory(*args):
        calls.append("inventory")
        return fixture["inventory"]
    def reconcile(manifest, cache, metadata, output, limit):
        assert limit == 0
        calls.append("reconcile")
        output.mkdir()
        release.write_json(output / "report.json", fixture["reconciliation"])
        return fixture["reconciliation"]
    def export(manifest, cache, metadata, schedule, output, limit):
        assert limit == 0
        calls.append("features")
        shutil.copytree(fixture["feature_dir"], output)
        return fixture["dataset"]
    monkeypatch.setattr(pipeline.sources, "inventory_sources", inventory)
    monkeypatch.setattr(pipeline.reconcile, "reconcile", reconcile)
    monkeypatch.setattr(pipeline.features, "export", export)
    arguments = run_args(fixture, tmp_path / "fresh")
    for name in ("reuse_inventory", "reuse_reconciliation", "reuse_features"):
        arguments[name] = None
    assert pipeline.run_pipeline(**arguments)["scientific_status"] == "BLOCKED"
    assert calls == ["inventory", "reconcile", "features"]


@pytest.mark.parametrize("change", ["source", "inventory", "reconciliation", "models", "math", "schedule"])
def test_reuse_refuses_stale_or_doctored_artifacts(tmp_path, change):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    if change == "source":
        (fixture["cache"] / "cdnnba_2020.tar.xz").write_bytes(b"changed")
    elif change == "inventory":
        packet = fixture["inventory"]
        packet["coverage"]["schedule_evidence"]["sha256"] = "0" * 64
        fixture["inventory_path"].write_text(json.dumps(packet))
    elif change == "reconciliation":
        packet = fixture["reconciliation"]
        packet["games"][0]["candidate_possessions"] += 1
        fixture["reconciliation_path"].write_text(json.dumps(packet))
    elif change == "models":
        packet = fixture["models"]
        packet["specification"]["sources"]["modeling.py"] = "0" * 64
        fixture["model_path"].write_text(json.dumps(packet))
    elif change == "math":
        packet = fixture["math"]
        packet["versions"]["metric_source_sha256"] = "0" * 64
        fixture["math_path"].write_text(json.dumps(packet))
    else:
        fixture["schedule"].write_text('{"games":[],"provenance":"changed"}')
    with pytest.raises(release.ArtifactError):
        pipeline.run_pipeline(**run_args(fixture, tmp_path / "bad-run"))
    assert not (tmp_path / "bad-run" / "report.json").exists()


def test_positive_synthetic_promotion_and_real_protocol_path_writes_distinct_evidence(tmp_path):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    output = tmp_path / "promoted"
    result = pipeline.promote_and_fit(**promotion_args(fixture, output))
    assert result["status"] == "GATED_EXPLORATORY_RESULT_NOT_PUBLICATION_APPROVAL"
    assert result["evaluation"]["row_count"] == 48
    promoted = release.read_json(output / "promoted_dataset.json")
    assert promoted["eligible_games"] == 6
    assert release.read_json(fixture["feature_dir"] / "manifest.json")["eligible_games"] == 0
    assert release.read_json(output / "model_result.json") == result
    with pytest.raises(FileExistsError):
        pipeline.promote_and_fit(**promotion_args(fixture, output))


def test_passed_audit_does_not_substitute_for_locked_model_protocol(tmp_path, monkeypatch):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    arguments = promotion_args(fixture, tmp_path / "refused")
    arguments["protocol"] = {}
    def forbidden(*args, **kwargs):
        pytest.fail("model fit ran without frozen protocol")
    monkeypatch.setattr(modeling, "_fit", forbidden)
    with pytest.raises(modeling.BlockedError):
        pipeline.promote_and_fit(**arguments)
    assert not arguments["output"].exists()


def test_claimed_gate_status_cannot_read_rows_promote_or_fit(tmp_path, monkeypatch):
    fixture = synthetic_artifacts(tmp_path / "inputs")
    arguments = promotion_args(fixture, tmp_path / "refused")
    arguments["audit_evidence"] = {"status": "PASS_CONDITIONAL"}
    def forbidden(*args, **kwargs):
        pytest.fail("data stream opened before real audit acceptance")
    monkeypatch.setattr(release, "verify_feature_export", forbidden)
    with pytest.raises(modeling.BlockedError):
        pipeline.promote_and_fit(**arguments)
    assert not arguments["output"].exists()
