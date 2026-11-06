"""Synthetic fixtures verify design mechanics, never independent audit evidence."""

import copy
import json
import random

import pytest

from research.audit_handoff_2026_11_06 import prepare_design as design
from whistle_research import audit


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    directory = tmp_path / "inputs"
    directory.mkdir()
    inventory = {
        "kind": "game_inventory", "ok": True, "source_failures": [],
        "coverage": {"status": "schedule_checked", "completeness": "accounted_for",
                     "schedule_evidence": {"sha256": "f" * 64, "provenance": "Synthetic schedule fixture"}},
        "games": [{"game_id": f"00224{i:05d}", "source_file": "fixture.tar.xz",
                   "source_member": "fixture.csv", "source_sha256": "a" * 64,
                   "season": "2024-25", "game_type": "regular_season",
                   "disposition": "observed", "anomalies": []} for i in range(6084)],
    }
    (directory / "inventory.json").write_bytes(design.encoded(inventory))
    ids = [g["game_id"] for g in inventory["games"]]
    # Deliberately nominate a game selected by the new seed to test overlap.
    enriched = sorted(random.Random(design.SEED).sample(ids, 299)[:4])
    pilot = audit.prepare_plan(directory / "inventory.json", 10, 42, enriched,
                               {gid: "Synthetic anomaly fixture" for gid in enriched})
    (directory / "audit_plan.json").write_bytes(design.encoded(pilot))
    report = {"schema_version": "development-research-report-v1",
              "versions": {"parser_version": audit.PARSER_VERSION, "parser_sha256": audit.parser_digest()},
              "artifacts": {"schedule": {"sha256": "f" * 64}}}
    for name, role in (("inventory.json", "inventory"), ("audit_plan.json", "audit_plan")):
        raw = (directory / name).read_bytes()
        report["artifacts"][role] = {"bytes": len(raw), "sha256": design.sha(raw)}
    (directory / "report.json").write_bytes(design.encoded(report))
    raw = {name: (directory / name).read_bytes() for name in design.PINNED}
    monkeypatch.setattr(design, "PINNED", {name: design.sha(value) for name, value in raw.items()})
    return directory, raw


@pytest.mark.parametrize("rate,expected", [(.01, 299), (.05, 59), (.10, 29)])
def test_exact_bound_minimum(rate, expected):
    assert design.minimum_zero_error_games(rate) == expected
    assert audit.upper_game_error_bound(0, expected, .95) <= rate
    assert audit.upper_game_error_bound(0, expected - 1, .95) > rate
    assert audit.upper_game_error_bound(0, 10, .95) == pytest.approx(.2588655508930522)


def test_deterministic_identity_and_overlap(inputs, tmp_path):
    directory, original = inputs
    first, second = tmp_path / "first", tmp_path / "second"
    result = design.prepare(directory, first)
    assert design.prepare(directory, second) == result
    for name in ("audit_plan.json", "selected_games.json", "design.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    plan = json.loads((first / "audit_plan.json").read_bytes())
    ledger = json.loads((first / "selected_games.json").read_bytes())
    assert not audit.validate_plan(plan)
    assert sum(g["in_random_sample"] for g in ledger["games"]) == 299
    assert sum(g["in_enriched_sample"] for g in ledger["games"]) == 4
    assert result["selection"]["unique_selected_games"] == 299
    assert len(result["selection"]["random_enriched_overlap_ids"]) == 4
    assert plan["inventory_sha256"] == design.sha(original["inventory.json"])
    assert result["freeze"]["frozen"] is False
    assert result["audit_gate"] == "BLOCKED"
    for name, binding in result["outputs"].items():
        raw = (first / name).read_bytes()
        assert binding == {"sha256": design.sha(raw), "bytes": len(raw)}
    for name, raw in original.items():
        assert (directory / name).read_bytes() == raw


def test_exclusive_output(inputs, tmp_path):
    directory, _ = inputs
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep"
    marker.write_text("user data")
    with pytest.raises(FileExistsError):
        design.prepare(directory, output)
    assert marker.read_text() == "user data"
    assert list(output.iterdir()) == [marker]


@pytest.mark.parametrize("name", ["inventory.json", "audit_plan.json", "report.json"])
def test_input_byte_drift_refused(inputs, tmp_path, name):
    directory, raw = inputs
    (directory / name).write_bytes(raw[name] + b" ")
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="pinned input drift"):
        design.prepare(directory, output)
    assert not output.exists()


def test_implementation_drift_refused(inputs, tmp_path, monkeypatch):
    directory, _ = inputs
    monkeypatch.setattr(design, "CODE_PINS", {"audit.py": "0" * 64})
    with pytest.raises(ValueError, match="implementation drift"):
        design.prepare(directory, tmp_path / "output")


@pytest.mark.parametrize("mutation", ["role", "parser", "schedule", "unverified", "missing_game", "malformed"])
def test_invalid_semantics_even_when_pins_match(inputs, monkeypatch, mutation):
    _, original = inputs
    raw = copy.copy(original)
    report = json.loads(raw["report.json"])
    inventory = json.loads(raw["inventory.json"])
    if mutation == "role":
        report["artifacts"]["inventory"] = report["artifacts"]["audit_plan"]
    elif mutation == "parser":
        report["versions"]["parser_sha256"] = "b" * 64
    elif mutation == "schedule":
        inventory["coverage"]["status"] = "observed_only"
    elif mutation == "unverified":
        inventory["games"][0]["source_sha256"] = None
    elif mutation == "missing_game":
        inventory["games"].pop()
    else:
        raw["inventory.json"] = b"{invalid"
    if mutation in {"schedule", "unverified", "missing_game"}:
        raw["inventory.json"] = design.encoded(inventory)
        report["artifacts"]["inventory"] = {"sha256": design.sha(raw["inventory.json"]),
                                             "bytes": len(raw["inventory.json"])}
    raw["report.json"] = design.encoded(report)
    monkeypatch.setattr(design, "PINNED", {name: design.sha(value) for name, value in raw.items()})
    with pytest.raises(ValueError):
        design.bind_inputs(raw)


def test_cli_refuses_existing_directory(inputs, tmp_path):
    directory, _ = inputs
    output = tmp_path / "already_exists"
    output.mkdir()
    with pytest.raises(SystemExit) as exc:
        design.main(["--input", str(directory), "--output", str(output)])
    assert exc.value.code == 2
