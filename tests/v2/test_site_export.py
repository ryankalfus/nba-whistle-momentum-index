"""The notebook must display the exact synthetic artifacts bound by its report."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from scripts.export_v2_site import export


def write_json(path, value):
    path.write_text(json.dumps(value) + "\n")
    raw = path.read_bytes()
    return {"path": path.name, "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


@pytest.fixture
def run_files(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    math = run / "math.json"
    models = run / "models.json"
    report = run / "report.json"
    artifacts = {
        "math": write_json(math, {"schema_version": "synthetic-mathematics-v1"}),
        "models": write_json(models, {"schema": "synthetic-model-demo-v1", "evaluation": {
            "paired_logloss": {"estimate": -0.002}, "row_ids": [["synthetic", 1]]}}),
    }
    write_json(report, {"schema_version": "development-research-report-v1", "artifacts": artifacts})
    return report, math, models, tmp_path / "export"


def test_export_verifies_report_roles_before_compacting(run_files):
    report, math, models, output = run_files
    result = json.loads(export(report, math, models, output).read_text())
    assert "row_ids" not in result["models"]["evaluation"]
    assert result["models"]["evaluation"]["paired_logloss"]["estimate"] == -0.002
    assert [item["role"] for item in result["input_files"]] == ["report", "math", "models"]
    for item in result["input_files"][1:]:
        assert item["report_binding"] == f"{item['role']}.json"


@pytest.mark.parametrize("role", ["math", "models"])
def test_modified_supplied_copy_is_rejected(run_files, role):
    report, math, models, output = run_files
    original = math if role == "math" else models
    supplied = output.parent / f"changed-{role}.json"
    data = json.loads(original.read_text())
    if role == "models":
        data["evaluation"]["paired_logloss"]["estimate"] = -999
    else:
        data["tampered_result"] = -999
    write_json(supplied, data)
    with pytest.raises(ValueError, match="does not match report binding"):
        export(report, supplied if role == "math" else math,
               supplied if role == "models" else models, output)
    assert not output.exists()


def test_modified_bound_file_is_rejected_even_with_original_supplied_copy(run_files):
    report, math, models, output = run_files
    supplied = output.parent / "original-models.json"
    supplied.write_bytes(models.read_bytes())
    data = json.loads(models.read_text())
    data["evaluation"]["paired_logloss"]["estimate"] = -999
    write_json(models, data)
    with pytest.raises(ValueError, match="bound artifact does not match"):
        export(report, math, supplied, output)
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["missing", "wrong_hash", "wrong_bytes", "absolute_path", "swapped_roles", "bool_bytes"])
def test_invalid_role_catalog_fails_closed(run_files, mutation):
    report, math, models, output = run_files
    data = json.loads(report.read_text())
    artifacts = deepcopy(data["artifacts"])
    if mutation == "missing":
        artifacts.pop("models")
    elif mutation == "wrong_hash":
        artifacts["models"]["sha256"] = "0" * 64
    elif mutation == "wrong_bytes":
        artifacts["models"]["bytes"] += 1
    elif mutation == "absolute_path":
        artifacts["models"]["path"] = str(models.resolve())
    elif mutation == "bool_bytes":
        artifacts["models"]["bytes"] = True
    else:
        artifacts["math"], artifacts["models"] = artifacts["models"], artifacts["math"]
    data["artifacts"] = artifacts
    write_json(report, data)
    with pytest.raises(ValueError):
        export(report, math, models, output)
    assert not output.exists()


def test_identical_copy_is_accepted_and_hashes_remain_raw(run_files):
    report, math, models, output = run_files
    supplied = output.parent / "copied-models.json"
    supplied.write_bytes(models.read_bytes())
    result = json.loads(export(report, math, supplied, output).read_text())
    evidence = next(item for item in result["input_files"] if item["role"] == "models")
    assert evidence["sha256"] == sha256(models.read_bytes()).hexdigest()
    assert evidence["bytes"] == len(models.read_bytes())
    assert "row_ids" not in result["models"]["evaluation"]
