"""Small synthetic CDN archives test preparation, never independent review."""

import csv
import io
import json
import tarfile

import pytest

from whistle_research.audit import prepare_plan
from whistle_research.review_packet import build_packet
from whistle_research.sources import file_digest


def synthetic_packet(tmp_path):
    """Return (plan, output, manifest) for one two-period synthetic game."""
    game_id = "0022400001"
    fields = ["gameId", "actionNumber", "orderNumber", "timeActual", "clock", "teamId",
              "possession", "period", "actionType", "description"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for n, period, team, kind in [(1, 1, 10, "period"), (2, 1, 20, "foul"),
                                  (3, 2, 10, "period"), (3, 2, 20, "period")]:
        writer.writerow({"gameId": game_id, "actionNumber": n, "orderNumber": n,
                         "period": period, "teamId": team, "possession": 10,
                         "actionType": kind, "description": "synthetic unresolved source event"})
    raw = stream.getvalue().encode()
    source = tmp_path / "fixture.tar.xz"
    with tarfile.open(source, "w:xz") as archive:
        member = tarfile.TarInfo("events.csv")
        member.size = len(raw)
        archive.addfile(member, io.BytesIO(raw))
    size, sha = file_digest(source)
    source_manifest = tmp_path / "sources.json"
    source_manifest.write_text(json.dumps([{"file": source.name, "bytes": size, "sha256": sha}]))
    inventory = {"kind": "game_inventory", "ok": True, "coverage": {
        "status": "schedule_checked", "completeness": "accounted_for",
        "schedule_evidence": {"sha256": "f" * 64, "provenance": "synthetic external schedule"}},
        "games": [{"game_id": game_id, "source_file": source.name, "source_sha256": sha,
                   "source_member": "events.csv", "season": "2024-25", "game_type": "regular_season",
                   "disposition": "observed", "anomalies": []}]}
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory))
    plan = prepare_plan(inventory_path, 1, 42, [game_id], {game_id: "synthetic difficult case"})
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    protocol = tmp_path / "protocol.md"
    protocol.write_text("Synthetic protocol, not scientific review.\n")
    output = tmp_path / "packet"
    manifest = build_packet(plan_path, source_manifest, tmp_path, None, protocol, output)
    return plan, output, manifest


def test_standalone_blinded_kits_preserve_all_raw_rows(tmp_path):
    plan, output, manifest = synthetic_packet(tmp_path)
    assert len(manifest["games"]) == len(plan["games"]) == 1
    assert manifest["games"][0]["access_status"] == "unverified"
    for slot in ("A", "B"):
        kit = output / f"reviewer_{slot}"
        assert (kit / "protocol.md").read_bytes() == (output / "protocol.md").read_bytes()
        kit_manifest = json.loads((kit / "manifest.json").read_text())
        for name in ("frame", "stratum", "enriched_reasons", "inclusion_probability"):
            assert name not in json.dumps(kit_manifest)
        ledger = json.loads((kit / kit_manifest["games"][0]["ledger"]["path"]).read_text())
        assert len(ledger["events"]) == 4
        assert ledger["events"][2]["event_id"] == ledger["events"][3]["event_id"]
        assert len({r["ref"] for r in ledger["events"]}) == 4
        annotation = json.loads(next((kit / "annotations").glob("*.json")).read_text())
        assert annotation["possessions"] == []
        assert annotation["reviewer_id"] is None


def test_no_output_replacement_and_bad_source_fails_before_output(tmp_path):
    _, output, _ = synthetic_packet(tmp_path)
    args = (tmp_path / "plan.json", tmp_path / "sources.json", tmp_path, None, tmp_path / "protocol.md")
    with pytest.raises(FileExistsError):
        build_packet(*args, output)
    (tmp_path / "fixture.tar.xz").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="snapshot"):
        build_packet(*args, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()


def test_empty_templates_explain_independent_prediction_context(tmp_path):
    _, output, _ = synthetic_packet(tmp_path)
    for slot in ("A", "B"):
        kit = output / f"reviewer_{slot}"
        template = json.loads(next((kit / "annotations").glob("*.json")).read_text())
        assert template["possessions"] == []
        guidance = template["_guidance"]
        assert set(guidance["possession_entry"]["prediction_start"]) == {
            "reference_ref", "period", "clock", "score_margin", "score_difference", "home_defense",
            "defense_counted_fouls", "previous_foul_1", "previous_foul_2", "start_type"}
        assert all(isinstance(v, str) for v in guidance["possession_entry"]["prediction_start"].values())
        instructions = (kit / "INSTRUCTIONS.md").read_text()
        assert "REQUIRED by the production candidate comparison" in instructions
        assert "two false human material_discrepancy flags" in instructions
