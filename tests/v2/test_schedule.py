"""Offline independent-schedule fail-closed tests."""
import gzip
import hashlib
import json
from urllib.parse import urlencode

import pytest

from whistle_research.schedule import BASE, compare, normalize


def event(eid="1", date="2024-10-24T02:30Z", status="STATUS_FINAL", notes=None):
    return {"id": eid, "date": date, "season": {"year": 2025},
            "seasonType": {"type": 2}, "competitions": [{
                "competitors": [{"homeAway": "home", "team": {"abbreviation": "GS"}},
                                {"homeAway": "away", "team": {"abbreviation": "NY"}}],
                "status": {"type": {"name": status, "completed": status == "STATUS_FINAL"}},
                "notes": notes or []}]}


def test_timezone_and_team_aliases():
    row = normalize(event(), 2025, 2)
    assert (row["date"], row["home"], row["away"]) == ("2024-10-23", "GSW", "NYK")


def test_postponed_and_explicit_cup_final():
    assert normalize(event(status="STATUS_POSTPONED"), 2025, 2)["disposition"] == "not_completed"
    assert normalize(event(notes=[{"headline": "NBA Cup Championship"}]), 2025, 2)["disposition"] == "excluded_cup_championship"
    assert normalize(event(notes=[{"headline": "NBA In-Season Tournament Championship"}]), 2025, 2)["disposition"] == "excluded_cup_championship"
    assert normalize(event(notes=[{"headline": "NBA Cup Group Play"}]), 2025, 2)["disposition"] == "completed"


def test_wrong_season_and_ambiguous_teams():
    with pytest.raises(ValueError, match="season/type"):
        normalize(event(), 2024, 2)
    row = event()
    row["competitions"][0]["competitors"][1]["homeAway"] = "home"
    with pytest.raises(ValueError, match="home/away"):
        normalize(row, 2025, 2)


def fixture(tmp_path, responses):
    raw = tmp_path / "raw"
    raw.mkdir()
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    for year in range(2020, 2025):
        (metadata / f"cdnnba_{year}_games.csv").write_text("game_id,date,home,away\n" + ("0022400001,2024-10-23,GSW,NYK\n0022400002,2024-10-24,LAL,BOS\n" if year == 2024 else ""))
    (metadata / "cdnnba_po_2024_games.csv").write_text("game_id,date,home,away\n")
    manifest = []
    for name, data, query, url in responses:
        body = json.dumps(data).encode()
        (raw / name).write_bytes(gzip.compress(body))
        manifest.append({"file": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "query": query, "url": url, "status": "acquired", "http_status": 200, "response_url": url + "?" + urlencode(query)})
    (raw / "manifest.json").write_text(json.dumps(manifest))
    return raw, metadata


def response(team, events):
    return (f"team{team}.json.gz", {"team": {"id": team, "abbreviation": "GS" if team == "1" else "NY"}, "events": events}, {"season": 2025, "seasontype": 2}, f"{BASE}/teams/{team}/schedule")


def test_missing_requests_and_unmatched_both_sides(tmp_path):
    extra = event("2", "2024-10-25T02:30Z")
    teams = ("teams.json.gz", {"sports": [{"leagues": [{"teams": [{"team": {"id": str(i)}} for i in range(1, 31)]}]}]}, {"limit": 100}, BASE + "/teams")
    raw, metadata = fixture(tmp_path, [teams, response("1", [event(), extra])])
    result = compare(raw, metadata)
    assert result["status"] == "unverified"
    assert any(e["reason"] == "missing/duplicate team request" for e in result["errors"])
    assert len(result["unmatched_archive"]) == len(result["unmatched_espn"]) == 1
    assert result["matched_count"] == 1


def test_conflicting_duplicates(tmp_path):
    raw, metadata = fixture(tmp_path, [response("1", [event()]), response("2", [event(date="2024-10-25T02:30Z")])])
    result = compare(raw, metadata)
    assert result["status"] == "unverified"
    assert any("conflicting duplicate" in e["reason"] for e in result["errors"])


def test_hash_mutation_and_unresolved_pagination(tmp_path):
    row = response("1", [event()])
    row[1]["pagination"] = {"next": "unknown"}
    raw, metadata = fixture(tmp_path, [row])
    assert any("pagination" in e["reason"] for e in compare(raw, metadata)["errors"])
    (raw / "team1.json.gz").write_bytes(gzip.compress(b"{}"))
    assert any("hash mismatch" in e["reason"] for e in compare(raw, metadata)["errors"])


def test_primary_date_correction_requires_id_teams_date_and_hash(tmp_path):
    from whistle_research.schedule import validate_corrections
    title = "New York Knicks vs Golden State Warriors Oct 23, 2024 Game Summary | NBA.com"
    url = "https://www.nba.com/game/nyk-vs-gsw-0022400001"
    source = tmp_path / "nba_web.txt"
    body = (title + " (" + url + ")\n").encode()
    source.write_bytes(body)
    row = {"game_id": "0022400001", "home": "GSW", "away": "NYK", "home_name": "Golden State Warriors", "away_name": "New York Knicks", "date": "2024-10-23", "historical_date": "2024-10-22", "source_file": source.name, "source_title": title, "url": url, "source_sha256": hashlib.sha256(body).hexdigest()}
    path = tmp_path / "corrections.json"

    def save():
        path.write_text(json.dumps({"corrections": [row]}))

    save()
    assert validate_corrections(path, tmp_path)["0022400001"]["date"] == "2024-10-23"
    row["date"] = "2024-10-24"
    save()
    with pytest.raises(ValueError, match="date inconsistent"):
        validate_corrections(path, tmp_path)
    row["date"] = "2024-10-23"
    row["home_name"] = "Los Angeles Lakers"
    save()
    with pytest.raises(ValueError, match="team names"):
        validate_corrections(path, tmp_path)
    row["home_name"] = "Golden State Warriors"
    row["game_id"] = "0022400002"
    save()
    with pytest.raises(ValueError, match="ID/team URL"):
        validate_corrections(path, tmp_path)
    row["game_id"] = "0022400001"
    save()
    source.write_bytes(b"mutated")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_corrections(path, tmp_path)


@pytest.mark.parametrize('field,value', [
    ('http_status', 403),
    ('http_status', '200'),
    ('response_url', 'https://example.invalid/untrusted'),
    ('response_url', BASE + '/teams/1/schedule?season=2024&seasontype=2'),
    ('response_url', BASE + '/teams/1/schedule?season=2025&seasontype=2&season=2025'),
    ('url', 'https://example.invalid/teams/1/schedule'),
])
def test_manifest_rejects_failed_or_redirected_source_identity(tmp_path, field, value):
    raw, metadata = fixture(tmp_path, [response('1', [event()])])
    path = raw / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest[0][field] = value
    path.write_text(json.dumps(manifest))
    result = compare(raw, metadata)
    assert result['status'] == 'unverified'
    assert result['completed_count'] == 0
    assert result['errors'][0]['source'] == 'team1.json.gz'


@pytest.mark.parametrize('game_id', ['224000001', '-002240001', '00224000.1', 'not-a-game'])
def test_metadata_requires_canonical_nba_game_ids(tmp_path, game_id):
    raw, metadata = fixture(tmp_path, [])
    path = metadata / 'cdnnba_2024_games.csv'
    path.write_text(path.read_text().replace('0022400001', game_id))
    with pytest.raises(ValueError, match='game ID'):
        compare(raw, metadata)


def test_duplicate_nba_id_across_different_metadata_cohorts_rejected(tmp_path):
    raw, metadata = fixture(tmp_path, [])
    (metadata / 'cdnnba_2021_games.csv').write_text('game_id,date,home,away\n0022400001,2021-10-25,LAL,BOS\n')
    with pytest.raises(ValueError, match='duplicate metadata NBA game ID'):
        compare(raw, metadata)
