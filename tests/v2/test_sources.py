"""Offline source integrity, archive safety, and coverage contracts."""

import hashlib
import io
import json
import tarfile

import pytest

from whistle_research.sources import (
    canonical_game_id,
    inventory_sources,
    main,
    read_schedule,
    verify_sources,
    write_artifact,
)


def fixture_source(tmp_path, rows=None, member="events.csv", duplicate_member=False):
    root = tmp_path / "raw"
    root.mkdir()
    archive = root / "cdnnba_2024.tar.xz"
    content = "gameId,actionNumber,orderNumber\n" + (rows or "22400001,1,10000\n22400001,2,20000\n")
    with tarfile.open(archive, "w:xz") as tar:
        for _ in range(2 if duplicate_member else 1):
            info = tarfile.TarInfo(member)
            data = content.encode()
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    data = archive.read_bytes()
    entries = [{"file": archive.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "url": "https://example.test/immutable"}]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(entries))
    return root, manifest, entries


def schedule_file(tmp_path, games):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"provenance": "independent fixture schedule", "games": games}))
    return path


def expected(game_id="0022400001", **extra):
    return {"game_id": game_id, "season": "2024-25", "game_type": "regular_season", **extra}


def test_verification_streams_and_reports_tampered_missing(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    assert verify_sources(manifest, root)["ok"]
    (root / entries[0]["file"]).write_bytes(b"tampered")
    assert verify_sources(manifest, root)["sources"][0]["status"] == "hash_mismatch"
    (root / entries[0]["file"]).unlink()
    assert verify_sources(manifest, root)["sources"][0]["status"] == "missing"
    assert main(["verify", "--manifest", str(manifest), "--source-root", str(root), "--output", str(tmp_path / "failed")]) == 1


@pytest.mark.parametrize("filename", ["../escape", "/absolute", "a/../b", "a\\b"])
def test_manifest_traversal_rejected(tmp_path, filename):
    root, manifest, entries = fixture_source(tmp_path)
    entries[0]["file"] = filename
    manifest.write_text(json.dumps(entries))
    result = verify_sources(manifest, root)
    assert not result["ok"]
    assert result["sources"][0]["status"] == "invalid_manifest"


def test_duplicate_manifest_and_symlink_escape(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    manifest.write_text(json.dumps(entries * 2))
    assert all(r["status"] == "invalid_manifest" for r in verify_sources(manifest, root)["sources"])
    outside = tmp_path / "outside"
    outside.write_text("secret")
    (root / "link").symlink_to(outside)
    entries[0]["file"] = "link"
    manifest.write_text(json.dumps(entries))
    assert not verify_sources(manifest, root)["ok"]


def test_inventory_is_deterministic_observed_only_and_traceable(tmp_path):
    root, manifest, _ = fixture_source(tmp_path)
    verified = verify_sources(manifest, root)
    result = inventory_sources(verified, root)
    assert result == inventory_sources(verified, root)
    assert result["ok"]
    assert result["coverage"]["status"] == "observed_only"
    assert result["coverage"]["completeness"] == "unverified"
    game = result["games"][0]
    assert game["game_id"] == "0022400001"
    assert game["event_count"] == 2
    assert game["source_sha256"] == verified["sources"][0]["source_sha256"]
    assert (game["first_source_row"], game["last_source_row"]) == (2, 3)
    first, second = tmp_path / "first", tmp_path / "second"
    write_artifact(first, "inventory.json", result)
    write_artifact(second, "inventory.json", result)
    assert (first / "inventory.json").read_bytes() == (second / "inventory.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_artifact(first, "inventory.json", result)


def test_missing_and_extra_schedule_games_fail_coverage(tmp_path):
    root, manifest, _ = fixture_source(tmp_path)
    schedule = schedule_file(tmp_path, [expected("0022400002")])
    result = inventory_sources(verify_sources(manifest, root), root, schedule)
    assert not result["ok"]
    assert result["coverage"]["status"] == "schedule_checked"
    assert {r["observation"] for r in result["coverage"]["games"]} == {"missing", "unexpected"}
    assert result["games"][0]["disposition"] == "quarantined"


def test_explicit_unavailable_excluded_and_failed_separate_from_missing(tmp_path):
    root, manifest, _ = fixture_source(tmp_path)
    schedule = schedule_file(tmp_path, [expected(status="excluded", reason="declared policy"),
        expected("0022400002", status="unavailable", reason="feed absent"),
        expected("0022400003", status="failed", reason="download failed")])
    result = inventory_sources(verify_sources(manifest, root), root, schedule)
    assert result["coverage"]["completeness"] == "accounted_for"
    assert result["games"][0]["disposition"] == "excluded"
    assert {r["observation"] for r in result["coverage"]["games"]} == {"excluded", "unavailable", "failed"}


@pytest.mark.parametrize("games", [[expected(), expected()], [expected(status="excluded")]])
def test_invalid_schedule_rejected(tmp_path, games):
    with pytest.raises(ValueError):
        read_schedule(schedule_file(tmp_path, games))


def test_schedule_provenance_required_and_metadata_mismatch(tmp_path):
    root, manifest, _ = fixture_source(tmp_path)
    path = tmp_path / "empty_provenance.json"
    path.write_text(json.dumps({"games": [expected()]}))
    with pytest.raises(ValueError, match="provenance"):
        read_schedule(path)
    schedule = schedule_file(tmp_path, [expected(season="2023-24")])
    result = inventory_sources(verify_sources(manifest, root), root, schedule)
    assert not result["ok"]
    assert result["coverage"]["games"][0]["observation"] == "metadata_mismatch"


@pytest.mark.parametrize("member,duplicate", [("../escape.csv", False), ("events.csv", True)])
def test_archive_traversal_and_duplicate_members_fail(tmp_path, member, duplicate):
    root, manifest, _ = fixture_source(tmp_path, member=member, duplicate_member=duplicate)
    result = inventory_sources(verify_sources(manifest, root), root)
    assert not result["ok"]
    assert result["source_failures"]
    assert not (tmp_path / "escape.csv").exists()


def test_duplicate_events_invalid_order_and_game_ids_quarantined(tmp_path):
    root, manifest, _ = fixture_source(tmp_path, "22400001,1,20000\n22400001,1,10000\nbad,3,NaN\n22400001,4,NaN\n")
    result = inventory_sources(verify_sources(manifest, root), root)
    assert not result["ok"]
    assert result["games"][0]["disposition"] == "quarantined"
    assert result["games"][0]["anomalies"] == ["invalid_event_order", "missing_or_duplicate_event_id", "nonincreasing_event_order", "source_archive_has_failures"]
    assert result["source_failures"][0]["reason"] == "invalid_game_id"


def test_stale_verification_cannot_authorize_changed_bytes(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    result = verify_sources(manifest, root)
    (root / entries[0]["file"]).write_bytes(b"tampered")
    inventory = inventory_sources(result, root)
    assert not inventory["ok"]
    assert inventory["source_failures"][0]["reason"] == "source_changed_after_verification"


def test_canonical_game_id_does_not_accept_float_or_guess_type():
    assert canonical_game_id("22400001") == "0022400001"
    with pytest.raises(ValueError):
        canonical_game_id("22400001.0")


def test_duplicate_game_across_archives_is_not_silently_merged(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    original = root / entries[0]["file"]
    other = root / "cdnnba_2023.tar.xz"
    other.write_bytes(original.read_bytes())
    entries.append({**entries[0], "file": other.name})
    manifest.write_text(json.dumps(entries))
    result = inventory_sources(verify_sources(manifest, root), root)
    assert not result["ok"]
    assert len(result["games"]) == 2
    assert all("duplicate_game_across_sources_or_members" in g["anomalies"] for g in result["games"])


def test_csv_schedule_and_cli_no_overwrite(tmp_path):
    root, manifest, _ = fixture_source(tmp_path)
    schedule = tmp_path / "schedule.csv"
    schedule.write_text("game_id,season,game_type\n22400001,2024-25,regular_season\n")
    with pytest.raises(ValueError, match="provenance"):
        read_schedule(schedule)
    assert read_schedule(schedule, "external schedule")[0][0]["game_id"] == "0022400001"
    output = tmp_path / "output"
    args = ["inventory", "--manifest", str(manifest), "--cache", str(root), "--output", str(output), "--schedule", str(schedule), "--schedule-provenance", "external schedule"]
    assert main(args) == 0
    saved = (output / "inventory.json").read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert (output / "inventory.json").read_bytes() == saved


def test_malformed_csv_row_is_explicit_and_blocks_archive(tmp_path):
    root, manifest, _ = fixture_source(tmp_path, "22400001,1,10000\n22400001,2\n")
    result = inventory_sources(verify_sources(manifest, root), root)
    assert not result["ok"]
    assert result["source_failures"][0]["reason"] == "malformed_csv_row"
    assert result["games"][0]["disposition"] == "quarantined"


@pytest.mark.parametrize("change", ["replace", "in_place"])
def test_archive_mutation_between_hash_and_parse_is_rejected(tmp_path, monkeypatch, change):
    root, manifest, entries = fixture_source(tmp_path)
    verified = verify_sources(manifest, root)
    replacement = tmp_path / "replacement.tar.xz"
    with tarfile.open(replacement, "w:xz") as tar:
        data = b"gameId,actionNumber,orderNumber\n22400002,1,10000\n"
        info = tarfile.TarInfo("events.csv")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    original_open = tarfile.open
    source_path = root / entries[0]["file"]
    def mutate_before_parse(*args, **kwargs):
        if change == "replace":
            replacement.replace(source_path)
        else:
            source_path.write_bytes(replacement.read_bytes())
        return original_open(*args, **kwargs)
    monkeypatch.setattr(tarfile, "open", mutate_before_parse)
    result = inventory_sources(verified, root)
    assert not result["ok"]
    assert result["source_failures"]
    assert all(game["disposition"] == "quarantined" for game in result["games"])


@pytest.mark.parametrize("content", [
    "game_id,game_id,season,game_type\n22400001,22400002,2024-25,regular_season\n",
    "game_id,season,game_type\n22400001,2024-25,regular_season,extra\n",
    "game_id,season,game_type,reason\n22400001,2024-25,regular_season\n",
])
def test_schedule_duplicate_headers_and_malformed_rows_rejected(tmp_path, content):
    path = tmp_path / "schedule.csv"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_schedule(path, "external schedule")


def test_truncated_matching_hash_archive_produces_failed_artifact(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    archive = root / entries[0]["file"]
    data = archive.read_bytes()[:-20]
    archive.write_bytes(data)
    entries[0].update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    manifest.write_text(json.dumps(entries))
    output = tmp_path / "failed_truncated"
    assert main(["inventory", "--manifest", str(manifest), "--cache", str(root), "--output", str(output)]) == 1
    result = json.loads((output / "inventory.json").read_text())
    assert not result["ok"]
    assert result["source_failures"]
    assert all(game["disposition"] == "quarantined" for game in result["games"])


def test_inventory_rehashes_declared_expectations_not_only_supplied_actuals(tmp_path):
    root, manifest, entries = fixture_source(tmp_path)
    verified = verify_sources(manifest, root)
    archive = root / entries[0]["file"]
    archive.write_bytes(archive.read_bytes() + b"changed")
    data = archive.read_bytes()
    # A caller cannot authorize replacement bytes merely by editing observed fields.
    verified["sources"][0].update(actual_bytes=len(data), source_sha256=hashlib.sha256(data).hexdigest())
    result = inventory_sources(verified, root)
    assert not result["ok"]
    assert result["source_failures"][0]["reason"] == "source_changed_after_verification"
