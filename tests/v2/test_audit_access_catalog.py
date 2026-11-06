"""Synthetic lookup tests; no playback, coverage or human evidence is created."""

import copy
import csv
import io
import json
import os
from pathlib import Path

import pytest

from research.audit_access_2026_11_06 import prepare_catalog as catalog
from whistle_research import audit


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=("game_id", "year", "postseason", "date", "home", "away"))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode()


def bind_fixture(raw, monkeypatch):
    """Rehash synthetic artifacts so semantic tests reach past integrity checks."""
    schedule = json.loads(raw["schedule"])
    inventory = json.loads(raw["inventory"])
    inventory["coverage"]["schedule_evidence"]["sha256"] = catalog.sha(raw["schedule"])
    raw["inventory"] = catalog.encoded(inventory)
    plan = json.loads(raw["plan"])
    plan["inventory_sha256"] = catalog.sha(raw["inventory"])
    plan["inventory_coverage"] = inventory["coverage"]
    plan["plan_sha256"] = audit.plan_digest(plan)
    raw["plan"] = catalog.encoded(plan)
    selection = json.loads(raw["selection"])
    selection["plan_sha256"] = plan["plan_sha256"]
    raw["selection"] = catalog.encoded(selection)
    report = json.loads(raw["report"])
    for role in ("inventory", "schedule", "source_manifest", *(f"historical_metadata_{i}" for i in range(6))):
        report["artifacts"][role].update(bytes=len(raw[role]), sha256=catalog.sha(raw[role]))
    raw["report"] = catalog.encoded(report)
    design = json.loads(raw["design"])
    design["inputs"]["report.json"] = {"sha256": catalog.sha(raw["report"])}
    design["selection"]["plan_sha256"] = plan["plan_sha256"]
    for role, name in (("selection", "selected_games.json"), ("plan", "audit_plan.json")):
        design["outputs"][name] = {"sha256": catalog.sha(raw[role]), "bytes": len(raw[role])}
    raw["design"] = catalog.encoded(design)
    monkeypatch.setattr(catalog, "PINS", {role: catalog.sha(raw[role]) for role in catalog.PINS})
    assert len(schedule["games"]) >= 1
    return raw


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    monkeypatch.setattr(catalog, "EXPECTED_FRAME", 6)
    monkeypatch.setattr(catalog, "EXPECTED_SELECTED", 3)
    monkeypatch.setattr(catalog, "EXPECTED_RANDOM", 2)
    monkeypatch.setattr(catalog, "EXPECTED_ENRICHED", 1)
    games, sources, scheduled, raw = [], [], [], {}
    for i, cohort in enumerate(catalog.COHORTS):
        year = cohort.removeprefix("po_")
        gid = f"00224{i:05d}"
        game = {"game_id": gid, "source_file": f"cdnnba_{cohort}.tar.xz",
                "source_member": f"cdnnba_{cohort}.csv", "source_sha256": str(i + 1) * 64,
                "season": f"{year}-{str(int(year) + 1)[-2:]}",
                "game_type": "playoffs" if cohort.startswith("po_") else "regular_season"}
        games.append({**game, "disposition": "observed", "anomalies": []})
        sources.append({"file": game["source_file"], "sha256": game["source_sha256"], "bytes": 1})
        old_date = f"{int(year) + 1}-01-01"
        scheduled.append({"game_id": gid, "season": game["season"], "game_type": game["game_type"],
                          "home": "MEM", "away": "ATL", "date": old_date,
                          "historical_date": old_date, "date_correction": None})
        raw[f"historical_metadata_{i}"] = csv_bytes([
            {"game_id": gid, "year": year, "postseason": "1" if cohort.startswith("po_") else "0",
             "date": old_date, "home": "MEM", "away": "ATL"}])
    corrected = scheduled[0]
    corrected["date"] = "2021-02-01"
    correction = {k: corrected[k] for k in ("game_id", "home", "away", "date", "historical_date")}
    correction.update(source_sha256="a" * 64, source_file="synthetic.txt", reason="Synthetic corrected date",
                      url=f'https://www.nba.com/game/atl-vs-mem-{corrected["game_id"]}')
    corrected["date_correction"] = correction
    raw["schedule"] = catalog.encoded({"provenance": "Synthetic independent schedule", "games": scheduled})
    raw["corrections"] = catalog.encoded({"kind": "official-NBA-rendered-date-corrections-v1", "corrections": [correction]})
    inventory = {"kind": "game_inventory", "ok": True, "source_failures": [], "games": games,
                 "coverage": {"status": "schedule_checked", "completeness": "accounted_for",
                              "schedule_evidence": {"sha256": catalog.sha(raw["schedule"]),
                                                    "provenance": "Synthetic schedule"}}}
    raw["inventory"] = catalog.encoded(inventory)
    invpath = root / catalog.PATHS["inventory"]
    invpath.parent.mkdir(parents=True)
    invpath.write_bytes(raw["inventory"])
    plan = audit.prepare_plan(invpath, 2, 42, [games[1]["game_id"]],
                              {games[1]["game_id"]: "Synthetic difficult case"})
    raw["plan"] = catalog.encoded(plan)
    raw["selection"] = catalog.encoded({"schema_version": "audit-selected-games-v1", "plan_sha256": plan["plan_sha256"],
                                        "frame_sha256": plan["frame_sha256"], "games": [
        {**g, "in_random_sample": g["stratum"] == "random", "in_enriched_sample": g["game_id"] in plan["enriched_game_ids"],
         "enriched_reason": plan["enriched_reasons"].get(g["game_id"])} for g in plan["games"]]})
    raw["source_manifest"] = catalog.encoded(sources)
    raw["historical_access"] = catalog.encoded({"schema_version": "league-pass-access-observations-v1",
        "checked_on": "2026-11-05", "summary": {"fixed_games": 1, "full_length_playback_verified_games": 1,
                                                "full_coverage_verified_games": 0,
                                                "independent_reviews_completed": 0}, "games": [{
            "game_id": corrected["game_id"], "date": corrected["date"], "matchup": "ATL@MEM",
            "official_url": correction["url"], "full_length_playback_verified": True,
            "stream_label": "Synthetic broadcast", "observations": [{"kind": "opening", "current_time_seconds": 2.0,
                "duration_seconds": 6000.0, "paused": False, "ready_state": 4, "media_error": None}],
            "full_coverage_verified": False, "independent_reviews_completed": 0}]})
    report = {"schema_version": "development-research-report-v1",
              "versions": {"parser_version": plan["parser_version"], "parser_sha256": plan["parser_sha256"]},
              "artifacts": {}}
    for role in ("inventory", "schedule", "source_manifest", *(f"historical_metadata_{i}" for i in range(6))):
        report["artifacts"][role] = {"path": Path(os.path.relpath(catalog.PATHS[role], Path(catalog.PATHS["report"]).parent)).as_posix()}
    raw["report"] = catalog.encoded(report)
    raw["design"] = catalog.encoded({"schema_version": "audit-design-evidence-v1", "outputs": {},
                                     "inputs": {"report.json": {}},
                                     "selection": {"plan_sha256": plan["plan_sha256"], "frame_sha256": plan["frame_sha256"]}})
    bind_fixture(raw, monkeypatch)
    for role, value in raw.items():
        path = root / catalog.PATHS[role]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return root, raw


def test_deterministic_lookup_preserves_dates_and_evidence_boundaries(fixture, tmp_path):
    root, raw = fixture
    first = catalog.prepare(root, tmp_path / "first")
    second = catalog.prepare(root, tmp_path / "second")
    assert first == second
    assert (tmp_path / "first/catalog.json").read_bytes() == (tmp_path / "second/catalog.json").read_bytes()
    assert first["counts"] == {"selected_games": 3, "metadata_matched_games": 3, "corrected_date_games": 1,
                               "games_with_historical_playback_observations": 1,
                               "games_without_historical_playback_observations": 2,
                               "continuous_coverage_verified_games": 0, "independent_reviews_completed": 0}
    corrected = first["games"][0]
    assert corrected["date"] == "2021-02-01"
    assert corrected["historical_metadata_date"] == "2021-01-01"
    assert [v["kind"] for v in corrected["historical_page_observations"]] == [
        "historical_playback_observation", "historical_official_date_page_observation"]
    assert corrected["historical_page_observations"][0]["record"]["matchup"] == "ATL@MEM"
    assert all(g["candidate_url_status"] == "inferred_from_pinned_matchup_not_individually_verified" for g in first["games"])
    assert all(g["continuous_coverage"] == "unverified" and g["independent_reviews_completed"] == 0 for g in first["games"])
    for role, binding in first["inputs"].items():
        assert binding == {"path": catalog.PATHS[role], "bytes": len(raw[role]), "sha256": catalog.sha(raw[role])}
        assert (root / catalog.PATHS[role]).read_bytes() == raw[role]
    assert first["implementation"]["sha256"] == catalog.sha(catalog.IMPLEMENTATION.read_bytes())


def test_existing_output_is_preserved(fixture, tmp_path):
    root, _ = fixture
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep").write_text("user data")
    with pytest.raises(FileExistsError):
        catalog.prepare(root, output)
    assert [p.name for p in output.iterdir()] == ["keep"]
    assert (output / "keep").read_text() == "user data"


@pytest.mark.parametrize("role", ["selection", "plan", "report", "historical_metadata_0", "historical_access"])
def test_changed_input_bytes_fail_before_output(fixture, tmp_path, role):
    root, raw = fixture
    (root / catalog.PATHS[role]).write_bytes(raw[role] + b" ")
    with pytest.raises(ValueError, match="drift|binding mismatch"):
        catalog.prepare(root, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("mutation", ["missing_metadata", "duplicate_metadata", "malformed_csv", "teams", "old_date",
    "duplicate_schedule", "status", "cohort", "correction", "wrong_url", "selection", "archive", "parser", "role_path", "coverage",
    "access_identity", "access_missing_opening", "access_playback_false", "access_wrong_url_matchup"])
def test_semantic_conflicts_fail_even_with_rehashed_snapshots(fixture, monkeypatch, mutation):
    _, original = fixture
    raw = copy.copy(original)
    if mutation in {"missing_metadata", "duplicate_metadata", "malformed_csv", "teams", "old_date"}:
        role = "historical_metadata_0"
        rows = list(csv.DictReader(io.StringIO(raw[role].decode())))
        if mutation == "missing_metadata":
            rows = []
        elif mutation == "duplicate_metadata":
            rows *= 2
        elif mutation == "teams":
            rows[0]["home"] = "NYK"
        elif mutation == "old_date":
            rows[0]["date"] = "2021-01-02"
        raw[role] = csv_bytes(rows)
        if mutation == "malformed_csv":
            raw[role] = raw[role].replace(b"MEM,ATL", b"MEM,ATL,EXTRA")
    else:
        role = {"duplicate_schedule": "schedule", "status": "schedule", "cohort": "schedule", "correction": "corrections",
                "wrong_url": "schedule", "selection": "selection", "archive": "source_manifest", "parser": "plan",
                "role_path": "report", "coverage": "historical_access", "access_identity": "historical_access",
                "access_missing_opening": "historical_access", "access_playback_false": "historical_access",
                "access_wrong_url_matchup": "historical_access"}[mutation]
        value = json.loads(raw[role])
        if mutation == "duplicate_schedule":
            value["games"].append(value["games"][0])
        elif mutation == "status":
            value["games"][0]["status"] = "excluded"
        elif mutation == "cohort":
            value["games"][0]["season"] = "unknown"
        elif mutation == "correction":
            value["corrections"] = []
        elif mutation == "wrong_url":
            value["games"][0]["date_correction"]["url"] = "https://www.nba.com/game/atl-vs-mem-0022400001"
            correction = json.loads(raw["corrections"])
            correction["corrections"][0] = value["games"][0]["date_correction"]
            raw["corrections"] = catalog.encoded(correction)
        elif mutation == "selection":
            value["games"].pop()
        elif mutation == "archive":
            value[0]["sha256"] = "b" * 64
        elif mutation == "parser":
            value["parser_sha256"] = "b" * 64
        elif mutation == "role_path":
            value["artifacts"]["schedule"]["path"] = value["artifacts"]["inventory"]["path"]
        elif mutation == "access_identity":
            value["games"][0]["matchup"] = "MEM@ATL"
        elif mutation == "access_missing_opening":
            value["games"][0]["observations"] = []
        elif mutation == "access_playback_false":
            value["games"][0]["full_length_playback_verified"] = False
        elif mutation == "access_wrong_url_matchup":
            value["games"][0]["official_url"] = value["games"][0]["official_url"].replace("atl-vs-mem", "mem-vs-atl")
        else:
            value["summary"]["full_coverage_verified_games"] = 1
        raw[role] = catalog.encoded(value)
    bind_fixture(raw, monkeypatch)
    with pytest.raises(ValueError):
        catalog.build_catalog(raw)


@pytest.mark.parametrize("kind", ["input", "implementation"])
def test_in_run_drift_is_refused(fixture, monkeypatch, tmp_path, kind):
    root, _ = fixture
    implementation = tmp_path / "implementation.py"
    implementation.write_bytes(catalog.IMPLEMENTATION.read_bytes())
    monkeypatch.setattr(catalog, "IMPLEMENTATION", implementation)
    original = catalog.build_catalog

    def drifting(raw):
        result = original(raw)
        path = root / catalog.PATHS["schedule"] if kind == "input" else implementation
        path.write_bytes(path.read_bytes() + b" ")
        return result

    monkeypatch.setattr(catalog, "build_catalog", drifting)
    with pytest.raises(ValueError, match="changed during run"):
        catalog.prepare(root, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_input_symlink_cannot_escape_root(fixture, tmp_path):
    root, raw = fixture
    external = tmp_path / "external.json"
    external.write_bytes(raw["selection"])
    path = root / catalog.PATHS["selection"]
    path.unlink()
    path.symlink_to(external)
    with pytest.raises(ValueError, match="escapes root"):
        catalog.prepare(root, tmp_path / "output")


@pytest.mark.parametrize("header", [b"game_id,year,postseason,date,home,home", b"game_id,year,postseason,date,home,away,"])
def test_invalid_metadata_headers_fail_even_when_rehashed(fixture, monkeypatch, header):
    _, original = fixture
    raw = copy.copy(original)
    raw["historical_metadata_0"] = header + b"\n"
    bind_fixture(raw, monkeypatch)
    with pytest.raises(ValueError, match="metadata CSV header"):
        catalog.build_catalog(raw)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'])
def test_ambiguous_json_refused(raw):
    with pytest.raises(ValueError):
        catalog.load_json(raw)
