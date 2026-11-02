from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from whistle_research import features
from whistle_research.audit import digest
from whistle_research.possessions import reconstruct

GID = "0022000001"
META = {
    "game_id": GID,
    "date": "2020-12-22",
    "season": "2020-21",
    "game_type": "regular_season",
}


def event(n, kind="turnover", team=100, owner=100, clock="PT11M00S", sub="", **kw):
    return {
        "actionNumber": n,
        "orderNumber": n,
        "actionType": kind,
        "subType": sub,
        "teamId": team,
        "teamTricode": "HOM" if team == 100 else "AWY",
        "possession": owner,
        "period": 1,
        "clock": clock,
        "scoreHome": 12,
        "scoreAway": 9,
        **kw,
    }


def reconstruction():
    actions = [
        event(0, "period", None, None, "PT12M00S", "start"),
        event(1),
        event(2, team=200, owner=200, clock="PT10M50S"),
        event(3, clock="PT10M40S"),
        event(4, "period", None, None, "PT00M00S", "end"),
    ]
    return reconstruct(actions, GID, 100, 200)


@pytest.mark.parametrize("note_period", [4, 7])
def test_postgame_source_note_does_not_replace_complete_game_markers(note_period):
    actions = []
    for period in range(1, 5):
        actions.extend([
            event(period * 10, "period", None, None, "PT12M00S", "start", period=period),
            event(period * 10 + 1, period=period),
            event(period * 10 + 2, "period", None, None, "PT00M00S", "end", period=period),
        ])
    actions.append(event(50, "game", None, None, "PT00M00S", "end", period=4))
    actions.append(event(51, "memo", None, None, "PT00M00S", period=note_period,
                         value="Source note requiring review", scoreHome=99))
    result = reconstruct(actions, GID, 100, 200)
    status = features.game_status(result)
    assert status["complete"] is True
    assert status["critical_unresolved"] is True
    assert result.eligible is False
    assert result.events[-1].kind == "memo" and result.events[-1].home_score == 99


def test_features_use_before_state_and_correct_score_orientation():
    result = reconstruction()
    rows = features.build_rows(result, META)
    assert len(rows) == len(result.possessions) == 3
    assert [row["outcome"] for row in rows] == [
        p.foul_indicator for p in result.possessions
    ]
    assert rows[0]["score_margin"] == 3
    assert rows[0]["score_difference"] == -3  # Away defense trails.
    assert rows[1]["score_difference"] == 3  # Home defense leads.
    assert rows[0]["home_defense"] == 0 and rows[1]["home_defense"] == 1
    assert rows[1]["clock"] == result.possessions[1].start_state.clock == 660
    assert rows[0]["previous_foul_1"] is None
    assert rows[2]["previous_foul_1"] == rows[2]["previous_foul_2"] == 0
    assert rows[0]["start_type"] == "before_control_event"


def test_missing_context_and_unknown_outcomes_are_retained():
    result = reconstruction()
    before = replace(
        result.possessions[1].start_state,
        home_score=None,
        defense_counted_fouls=None,
        previous_foul_indicators=(None, 1),
    )
    possession = replace(result.possessions[1], start_state=before, foul_indicator=None)
    changed = replace(
        result, possessions=(result.possessions[0], possession, result.possessions[2])
    )
    rows = features.build_rows(changed, META)
    assert len(rows) == 3 and rows[1]["outcome"] is None
    assert rows[1]["score_margin"] is rows[1]["score_difference"] is None
    assert rows[1]["defense_counted_fouls"] is None
    assert rows[1]["previous_foul_1"] == 1 and rows[1]["previous_foul_2"] is None


def test_current_outcome_and_ending_do_not_enter_context():
    result = reconstruction()
    rows = features.build_rows(result, META)
    changed = replace(
        result,
        possessions=tuple(
            replace(
                p,
                foul_indicator=1,
                boundary_reason="changed",
                complete=False,
                counted_foul_action_numbers=(999,),
            )
            for p in result.possessions
        ),
    )
    alternative = features.build_rows(changed, META)
    assert [{k: v for k, v in row.items() if k != "outcome"} for row in rows] == [
        {k: v for k, v in row.items() if k != "outcome"} for row in alternative
    ]
    assert all(row["outcome"] == 1 for row in alternative)
    assert not any(
        key in rows[0]
        for key in ("duration", "end_score", "next_foul", "boundary_reason", "complete")
    )


def test_appended_future_suffix_leaves_earlier_feature_rows_unchanged():
    actions = [
        event(0, "period", None, None, "PT12M00S", "start"),
        event(1),
        event(2, team=200, owner=200, clock="PT10M50S"),
    ]
    prefix = features.build_rows(reconstruct(actions, GID, 100, 200), META)
    actions += [
        event(3, "foul", 200, 100, "PT10M40S", "personal"),
        event(4, "period", None, None, "PT00M00S", "end"),
    ]
    longer = features.build_rows(reconstruct(actions, GID, 100, 200), META)
    assert prefix[0] == longer[0]
    assert {k: v for k, v in prefix[1].items() if k != "outcome"} == {
        k: v for k, v in longer[1].items() if k != "outcome"
    }


@pytest.mark.parametrize(
    "change",
    [
        {"game_id": "1"},
        {"game_id": "0022000002"},
        {"date": "2020-1-2"},
        {"date": None},
        {"season": "2020-22"},
        {"game_type": "unknown"},
    ],
)
def test_build_rows_rejects_malformed_or_mismatched_metadata(change):
    with pytest.raises((ValueError, TypeError)):
        features.build_rows(reconstruction(), {**META, **change})


def schedule_row():
    return {
        **META,
        "historical_date": META["date"],
        "date_correction": None,
        "home": "HOM",
        "away": "AWY",
        "espn_event_id": "123",
    }


def historical():
    return {
        GID: {
            "home": "HOM",
            "away": "AWY",
            "year": "2020",
            "postseason": "0",
            "date": META["date"],
        }
    }


def write_schedule(path, rows):
    path.write_text(
        json.dumps(
            {"games": rows, "provenance": "Synthetic independent schedule fixture"}
        )
    )


def test_corrected_date_has_exact_game_team_and_original_date_binding(tmp_path):
    row = schedule_row()
    row["date"] = "2020-12-23"
    row["date_correction"] = {
        k: row[k] for k in ("game_id", "date", "historical_date", "home", "away")
    }
    row["date_correction"]["source_sha256"] = "a" * 64
    path = tmp_path / "schedule.json"
    write_schedule(path, [row])
    bound, proof = features.load_schedule(path, historical())
    assert bound[GID]["date"] == "2020-12-23" and proof["corrected_dates"] == 1
    assert features.build_rows(reconstruction(), bound[GID])[0]["date"] == "2020-12-23"
    row["date_correction"]["game_id"] = "0022000002"
    write_schedule(path, [row])
    with pytest.raises(ValueError, match="correction binding"):
        features.load_schedule(path, historical())


@pytest.mark.parametrize(
    "case",
    ["duplicate", "missing", "unbound", "teams", "cohort", "uncorrected", "original"],
)
def test_bad_schedule_binding_fails_closed(tmp_path, case):
    row = schedule_row()
    rows = [row]
    if case == "duplicate":
        rows.append(dict(row))
    elif case == "missing":
        rows = []
    elif case == "unbound":
        row["game_id"] = "0022000002"
    elif case == "teams":
        row["home"] = "WRONG"
    elif case == "cohort":
        row["season"] = "2021-22"
    elif case == "uncorrected":
        row["date"] = "2020-12-23"
    else:
        row["historical_date"] = "2020-12-21"
    path = tmp_path / "schedule.json"
    write_schedule(path, rows)
    with pytest.raises(ValueError):
        features.load_schedule(path, historical())


def export_fixture(tmp_path):
    actions = [
        event(0, "period", None, None, "PT12M00S", "start"),
        event(1),
        event(2, "foul", 100, 200, "PT10M50S", "unrecognized"),
        event(3, "substitution", 200, 200, "PT10M50S", "out"),
        event(4, "period", None, None, "PT00M00S", "end"),
    ]
    columns = list(actions[0]) + ["gameId"]
    import csv

    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=columns)
    writer.writeheader()
    writer.writerows({**row, "gameId": GID} for row in actions)
    raw = text.getvalue().encode()
    archive_path = tmp_path / "cdnnba_2020.tar.xz"
    with tarfile.open(archive_path, "w:xz") as archive:
        member = tarfile.TarInfo("events.csv")
        member.size = len(raw)
        archive.addfile(member, io.BytesIO(raw))
    manifest = tmp_path / "sources.json"
    data = archive_path.read_bytes()
    manifest.write_text(
        json.dumps(
            [
                {
                    "file": archive_path.name,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            ]
        )
    )
    metadata = tmp_path / "metadata.csv"
    metadata.write_text(
        "game_id,year,postseason,date,home,away\n0022000001,2020,0,2020-12-22,HOM,AWY\n"
    )
    schedule = tmp_path / "schedule.json"
    write_schedule(schedule, [schedule_row()])
    return manifest, tmp_path, [metadata], schedule


def test_stream_export_keeps_unknown_rows_provenance_and_exact_list_digest(tmp_path):
    args = export_fixture(tmp_path)
    output = tmp_path / "out"
    packet = features.export(*args, output, limit_per_source=0)
    rows = [
        json.loads(line) for line in (output / "rows.jsonl").read_text().splitlines()
    ]
    provenance = [
        json.loads(line)
        for line in (output / "row_provenance.jsonl").read_text().splitlines()
    ]
    assert packet["ok"] and packet["row_count"] == len(rows) == len(provenance) == 2
    assert packet["rows_sha256"] == digest(rows)
    assert (
        packet["unknown_outcomes"] == sum(row["outcome"] is None for row in rows) == 1
    )
    assert packet["games"][0]["critical_unresolved"] is True
    assert packet["games"][0]["complete"] is False
    assert packet["games"][0]["eligible"] is False
    assert packet["plan_sha256"] is None
    assert packet["feature_sha256"] == features.feature_module_sha256()
    assert provenance[0]["source_rows"] == [3]
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        features.export(*args, output, limit_per_source=0)
    assert (output / "manifest.json").read_bytes() == before


def test_unverified_source_emits_no_rows_and_accounts_for_expected_game(tmp_path):
    args = export_fixture(tmp_path)
    (tmp_path / "cdnnba_2020.tar.xz").write_bytes(b"changed")
    packet = features.export(*args, tmp_path / "bad", limit_per_source=0)
    assert not packet["ok"] and packet["row_count"] == 0
    assert (
        len(packet["games"]) == 1
        and packet["games"][0]["status"] == "missing_source_game"
    )
    assert packet["source_failures"] and packet["eligible_games"] == 0


def test_feature_module_hash_binds_exact_bytes():
    assert (
        features.feature_module_sha256()
        == hashlib.sha256(Path(features.__file__).read_bytes()).hexdigest()
    )
