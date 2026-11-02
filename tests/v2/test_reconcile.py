import csv
import hashlib
import io
import json
import tarfile

import pytest

from whistle_research.reconcile import archive_games, game_diagnostic, reconcile, verified_snapshot


def test_snapshot_rejects_changed_bytes_before_parsing(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"old")
    digest = hashlib.sha256(b"old").hexdigest()
    path.write_bytes(b"new")
    with pytest.raises(ValueError, match="does not match"):
        with verified_snapshot(path, 3, digest):
            pytest.fail("tampered bytes yielded")


def test_snapshot_remains_bound_if_original_is_replaced(tmp_path):
    path = tmp_path / "data"
    path.write_bytes(b"old")
    with verified_snapshot(path, 3, hashlib.sha256(b"old").hexdigest()) as stream:
        path.write_bytes(b"new")
        assert stream.read() == b"old"


def tar_bytes(csv_text):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:xz") as archive:
        encoded = csv_text.encode()
        member = tarfile.TarInfo("events.csv")
        member.size = len(encoded)
        archive.addfile(member, io.BytesIO(encoded))
    stream.seek(0)
    return stream


def test_archive_groups_keep_original_row_mapping_and_missingness():
    groups = list(archive_games(tar_bytes("gameId,actionNumber,scoreHome\n1,8,\n1,9,2\n2,1,0\n")))
    assert [g[0] for g in groups] == ["0000000001", "0000000002"]
    assert groups[0][2] == [2, 3]
    assert groups[0][1][0]["scoreHome"] is None


def test_noncontiguous_games_are_not_silently_split():
    with pytest.raises(ValueError, match="noncontiguous"):
        list(archive_games(tar_bytes("gameId\n1\n2\n1\n")))


def event(n, kind, sub, team, owner, clock="PT11M00S", **kwargs):
    return dict(actionNumber=n, orderNumber=n, period=1, actionType=kind, subType=sub,
                teamId=team, teamTricode="HOM" if team == 100 else "AWY",
                possession=owner, clock=clock, scoreHome=0, scoreAway=0, **kwargs)


def test_reconciliation_never_drops_unknown_groups_to_make_wmi():
    actions = [event(1, "jumpball", "recovered", 100, 100),
               event(2, "foul", "unrecognized", 200, 100),
               event(3, "period", "end", 200, None, "PT00M00S")]
    diagnostic, _ = game_diagnostic(actions, "g", {"home": "HOM", "away": "AWY", "possessions": "1"}, "a"*64)
    assert diagnostic["uncertain_possessions"] == 1
    assert diagnostic["wmi"] is None
    assert diagnostic["eligible"] is False


def test_failed_sources_produce_a_blocked_diagnostic_report(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"file": "cdnnba_2024.tar.xz", "bytes": 1, "sha256": "a"*64}]))
    metadata = tmp_path / "metadata.csv"
    metadata.write_text("game_id,home,away,possessions\n0022400001,HOM,AWY,1\n")
    output = tmp_path / "out"
    result = reconcile(manifest, tmp_path, [metadata], output)
    assert result["ok"] is False
    assert result["eligible_games"] == 0
    assert json.loads((output / "report.json").read_text())["verification"]["sources"][0]["status"] == "missing"
    with pytest.raises(FileExistsError):
        reconcile(manifest, tmp_path, [metadata], output)


def incomplete_or_orphan_actions(orphan=False):
    actions = [event(1, "period", "start", 100, None, "PT12M00S")]
    if orphan:
        actions.append(event(2, "foul", "personal", 200, None, "PT12M00S"))
    actions += [event(3, "jumpball", "recovered", 100, 100),
                event(4, "foul", "personal", 200, 100),
                event(5, "turnover", "bad pass", 100, 100),
                event(6, "turnover", "bad pass", 200, 200),
                event(7, "period", "end", 200, None, "PT00M00S")]
    if orphan:
        for period in (2, 3, 4):
            actions += [dict(event(10*period, "period", "start", 100, None, "PT12M00S"), period=period),
                        dict(event(10*period+1, "turnover", "bad pass", 100, 100), period=period),
                        dict(event(10*period+2, "period", "end", 200, None, "PT00M00S"), period=period)]
        actions.append(dict(event(99, "game", "end", 200, None, "PT00M00S"), period=4, scoreHome=1))
    return actions


@pytest.mark.parametrize("orphan", [False, True])
def test_game_wmi_requires_complete_coverage_and_no_unassigned_fouls(orphan):
    diagnostic, _ = game_diagnostic(incomplete_or_orphan_actions(orphan), "g",
                                    {"home": "HOM", "away": "AWY"}, "a"*64)
    assert diagnostic["wmi"] is None
    assert diagnostic["metric_status"] == "withheld_incomplete_or_ambiguous"


def test_csv_parse_failure_still_writes_failed_diagnostic(tmp_path):
    raw = tar_bytes("gameId,description\n22400001," + "x" * (csv.field_size_limit()+1) + "\n").getvalue()
    archive = tmp_path / "cdnnba_2024.tar.xz"
    archive.write_bytes(raw)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"file": archive.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]))
    metadata = tmp_path / "metadata.csv"
    metadata.write_text("game_id,home,away\n0022400001,HOM,AWY\n")
    output = tmp_path / "out"
    result = reconcile(manifest, tmp_path, [metadata], output)
    assert result["source_failures"]
    assert result["ok"] is False
    assert (output / "report.json").exists()
