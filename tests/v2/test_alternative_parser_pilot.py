"""Focused invariants for the isolated external-parser evidence runner."""

import importlib.util
from pathlib import Path

import pytest


PATH = Path(__file__).resolve().parents[2] / "research/cross_feed_2026_11_05/alternative_parser/pilot.py"
SPEC = importlib.util.spec_from_file_location("alternative_parser_pilot", PATH)
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


def test_wrapper_preserves_missing_fields_and_order_without_inventing_values():
    rows = [{"PERIOD": "1", "etype": "12", "evt": "2", "pid": "", "cl": "12:00"},
            {"PERIOD": "1", "etype": "1", "evt": "7", "pid": "123", "cl": "11:12.3"},
            {"PERIOD": "2", "etype": "12", "evt": "90", "pid": "", "cl": "12:00"}]
    wrapped = PILOT.wrap_rows(rows)
    restored = [dict(event, etype=str(event["etype"]))
                for period in wrapped["g"]["pd"] for event in period["pla"]]
    assert restored == rows
    assert [p["p"] for p in wrapped["g"]["pd"]] == [1, 2]
    assert rows[0]["etype"] == "12"
    assert "oftid" not in wrapped["g"]["pd"][0]["pla"][0]


def test_wrapper_rejects_period_reordering_and_nonlossless_event_type():
    with pytest.raises(ValueError, match="Noncontiguous"):
        PILOT.wrap_rows([{"PERIOD": str(p), "etype": "12"} for p in [1, 2, 1]])
    with pytest.raises(ValueError, match="Non-lossless"):
        PILOT.wrap_rows([{"PERIOD": "1", "etype": "01"}])


def test_unverified_wheel_and_network_fail_closed(tmp_path):
    wheel = tmp_path / "wrong.whl"
    wheel.write_bytes(b"not the pinned wheel")
    with pytest.raises(ValueError, match="Unverified"):
        PILOT.verify_wheel(wheel, tmp_path)
    with pytest.raises(RuntimeError, match="OFFLINE_POLICY"):
        PILOT.blocked_network("https://example.invalid")


def test_exact_assignment_rejects_duplicates_injection_and_reordering():
    rows = [{"evt": "2"}, {"evt": "7"}, {"evt": "9"}]
    PILOT.verify_assignment(rows, [{"event_nums": [2, 7]}, {"event_nums": [9]}])
    for bad in [[2, 7, 7], [2, 7, 9, 10], [7, 2, 9]]:
        with pytest.raises(ValueError, match="dropped, duplicated, injected or reordered"):
            PILOT.verify_assignment(rows, [{"event_nums": bad}])
    with pytest.raises(ValueError, match="Duplicate source"):
        PILOT.verify_assignment([{"evt": "2"}, {"evt": "2"}], [{"event_nums": [2, 2]}])


def test_boundary_identity_needs_corroboration_and_known_equal_clock():
    cdn = [{"actionNumber": "2", "orderNumber": "20000", "period": "1", "clock": "PT03M07.00S"},
           {"actionNumber": "3", "orderNumber": "30000", "period": "1", "clock": "PT11M00S"}]
    mobile = [{"evt": "2", "ord": "20000", "PERIOD": "1", "cl": "3:07"},
              {"evt": "3", "ord": "99999", "PERIOD": "1", "cl": "11:00"}]
    result = PILOT.boundary_comparison(cdn, mobile,
                                      [{"last_action_number": 2}, {"last_action_number": 3}],
                                      [{"last_event_num": 2}])
    assert result["event_ids"]["shared"] == [2]
    assert result["event_ids"]["canonical_uncomparable"] == [3]
    assert result["counts"]["canonical_only"] == 0


@pytest.mark.parametrize("name", ["ledger.json", "comparison_source.py"])
def test_in_run_mutation_cannot_relabel_consumed_bytes(tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"original consumed bytes")
    consumed = path.read_bytes()
    fingerprints = {}
    PILOT.record_consumed(fingerprints, path, consumed)
    original_hash = fingerprints[path]
    PILOT.verify_no_drift(fingerprints)
    # Simulate an edit after parsing/import but before producing the packet.
    path.write_bytes(b"replacement live bytes")
    assert fingerprints[path] == original_hash
    assert fingerprints[path] != PILOT.digest(path)
    with pytest.raises(ValueError, match="changed during run"):
        PILOT.verify_no_drift(fingerprints)
