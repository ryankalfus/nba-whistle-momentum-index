"""Offline synthetic UI metadata tests; no human/continuous-footage evidence."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "research/audit_access_2026_11_06/summarize_playback.py"
SPEC = importlib.util.spec_from_file_location("playback_summary", SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def fixtures():
    catalog = {"games": [{"game_id": "0022000021", "date": "2020-12-26", "away": "ATL", "home": "MEM",
                          "candidate_game_url": "https://www.nba.com/game/atl-vs-mem-0022000021"},
                         {"game_id": "0022000045", "date": "2020-12-28", "away": "POR", "home": "LAL",
                          "candidate_game_url": "https://www.nba.com/game/por-vs-lal-0022000045"}]}
    row = {"game_id": "0022000021", "official_url": catalog["games"][0]["candidate_game_url"],
           "final_url": catalog["games"][0]["candidate_game_url"] + "?watchFullGame=true",
           "page_title": "Atlanta Hawks vs Memphis Grizzlies Dec 26, 2020 Game Summary | NBA.com",
           "checked_at": "2026-11-06T17:36:51.976Z", "full_games_selected": True,
           "full_length_playback_verified": True, "status": "OPENING_PLAYBACK_VERIFIED",
           "full_coverage_verified": False, "independent_reviews_completed": 0,
           "playback": {"duration_seconds": 6000, "current_time_seconds": 2,
                        "paused": False, "ready_state": 4, "media_error": None}}
    return {"observations": [row]}, catalog, {"observations": []}


def test_partial_counts_failed_then_pass_and_duplicates():
    source, catalog, baseline = fixtures()
    failed = deepcopy(source["observations"][0])
    failed.update(status="NOT_VERIFIED", full_length_playback_verified=False)
    failed["playback"]["paused"] = True
    source["observations"] = [failed, source["observations"][0], deepcopy(source["observations"][0])]
    summary, addendum = m.summarize(source, catalog, baseline)
    assert summary["status"] == "PARTIAL_ACCESS_CHECK"
    assert summary["counts"]["raw_observations"] == 3
    assert summary["counts"]["successful_reads"] == 2
    assert summary["counts"]["unique_verified_games"] == 1
    assert summary["games"][0]["observation_indices"] == [0, 1, 2]
    assert [x["observation_index"] for x in summary["games"][0]["successful_observations"]] == [1, 2]
    assert len(addendum["games"]) == 2
    assert addendum["games"][1]["url_status"] == "inferred_lead"
    assert addendum["games"][1]["opening_playback_observed"] is False


def test_attempted_and_complete_statuses():
    source, catalog, baseline = fixtures()
    row = {"game_id": "0022000045", "checked_at": "2026-11-06T18:00:00+00:00",
           "status": "NOT_VERIFIED", "reason": "session_reset_incomplete"}
    source["observations"].append(row)
    summary, _ = m.summarize(source, catalog, baseline)
    assert summary["status"] == "ALL_SELECTED_ACCESS_ATTEMPTED"
    assert summary["counts"]["observations_with_unknown_coverage_or_human_fields"] == 1
    row.update(deepcopy(source["observations"][0]))
    row.update(game_id="0022000045", official_url=catalog["games"][1]["candidate_game_url"],
               final_url=catalog["games"][1]["candidate_game_url"],
               page_title="Portland Trail Blazers vs Los Angeles Lakers Dec 28, 2020 Game Summary | NBA.com")
    assert m.summarize(source, catalog, baseline)[0]["status"] == "ALL_SELECTED_OPENINGS_VERIFIED"


@pytest.mark.parametrize("key,value", [("duration_seconds", 2999), ("duration_seconds", True),
                                      ("current_time_seconds", 0), ("current_time_seconds", 6000),
                                      ("paused", True), ("ready_state", True),
                                      ("ready_state", 3), ("media_error", 4),
                                      ("media_error", {"code": 4})])
def test_false_success_player_fields_rejected(key, value):
    source, catalog, baseline = fixtures()
    source["observations"][0]["playback"][key] = value
    with pytest.raises(ValueError, match="status disagrees"):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("key,value", [("full_games_selected", False), ("full_length_playback_verified", False),
                                      ("status", "NOT_VERIFIED"), ("full_coverage_verified", True),
                                      ("independent_reviews_completed", 1), ("independent_reviews_completed", False),
                                      ("game_id", "0022999999"), ("checked_at", "2026-11-06T17:36:51"),
                                      ("page_title", "Atlanta Hawks vs Memphis Grizzlies Dec 25, 2020 Game Summary | NBA.com"),
                                      ("final_url", "https://www.nba.com/game/por-vs-lal-0022000045")])
def test_invalid_claims_identity_and_dates_rejected(key, value):
    source, catalog, baseline = fixtures()
    source["observations"][0][key] = value
    with pytest.raises(ValueError):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("extra", [{"password": "private"}, {"email": "private"}, {"authorization": "private"},
                                   {"currentSrc": "private"}, {"src": "private"}, {"account_id": "private"},
                                   {"nested": {"cookie": "private"}},
                                   {"reason": "https://media.nba.com/secret.m3u8"},
                                   {"final_url": "https://www.nba.com/game/atl-vs-mem-0022000021?token=private"},
                                   {"reason": "data:video/mp4;base64,PRIVATE"}, {"media_url": "https://www.nba.com/game/atl-vs-mem-0022000021"},
                                   {"reason": "person@example.com"}, {"official_url": "https://www.nba.com/account"}])
def test_private_data_rejected_anywhere_including_failures(extra):
    source, catalog, baseline = fixtures()
    source["unused_top_level"] = extra
    with pytest.raises(ValueError):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("data", [b'{"observations": [], "observations": []}',
                                  b'{"nested": {"x": 1, "x": 2}}', b'{"x": NaN}',
                                  b'{"x": Infinity}', b'{"x": -Infinity}'])
def test_strict_json(data):
    with pytest.raises(ValueError):
        m.strict_json(data)


def test_json_exponent_overflow_also_rejected():
    with pytest.raises(ValueError, match="non-finite"):
        m.strict_json(b'{"value": 1e999}')


def test_baseline_exact_and_unknown_or_legacy_queue_rejected():
    source, catalog, _ = fixtures()
    baseline = deepcopy(source)
    source["observations"][0]["kind"] = "invented"
    with pytest.raises(ValueError, match="baseline"):
        m.summarize(source, catalog, baseline)
    source = deepcopy(baseline)
    source["selected_game_ids"] = ["0022000021"]
    with pytest.raises(ValueError, match="complete catalog"):
        m.summarize(source, catalog, baseline)


def test_failed_read_media_error_variations_preserved():
    source, catalog, baseline = fixtures()
    for error in (4, {"code": 4}):
        row = deepcopy(source["observations"][0])
        row.update(status="NOT_VERIFIED", full_length_playback_verified=False)
        row["playback"]["media_error"] = error
        source["observations"].append(row)
    before = deepcopy(source)
    summary, _ = m.summarize(source, catalog, baseline)
    assert summary["counts"]["successful_reads"] == 1
    assert source == before


def test_addendum_allowlist_and_actual_timestamp_kind_only():
    source, catalog, baseline = fixtures()
    catalog["games"][0].update(stratum="SECRET", model_label="SECRET", inclusion_probability=0.5)
    row = source["observations"][0]
    row.pop("checked_at")
    row["observed_at"] = "2026-11-06T19:00:00+00:00"
    row["kind"] = "followup_after_previous_observation"
    row["listed_full_game_feeds"] = ["National Broadcast", "Other Feed"]
    _, addon = m.summarize(source, catalog, baseline)
    assert set(addon) == {"schema_version", "resource_kind", "limits", "games"}
    assert set(addon["games"][0]) == {"game_id", "date", "matchup", "public_url", "url_status",
                                    "opening_playback_observed", "successful_observations", "team_broadcast_observations", "continuous_coverage"}
    success = addon["games"][0]["successful_observations"][0]
    assert success["timestamps"] == {"observed_at": row["observed_at"]}
    assert "kind" not in success
    assert success["timestamp_kind"] == "observed_at"
    assert "player_header" not in success
    assert "SECRET" not in json.dumps(addon)
    assert "listed_full_game_feeds" not in json.dumps(addon)


def test_official_url_alone_does_not_verify_page():
    source, catalog, baseline = fixtures()
    source["observations"][0] = {"game_id": "0022000021", "official_url": catalog["games"][0]["candidate_game_url"],
                                 "status": "NOT_VERIFIED", "reason": "session_reset", "checked_at": "2026-11-06T18:00:00Z"}
    assert m.summarize(source, catalog, baseline)[1]["games"][0]["url_status"] == "inferred_lead"


def test_tracked_baseline_and_pins():
    baseline_bytes = (ROOT / m.BASELINE).read_bytes()
    catalog_bytes = (ROOT / m.CATALOG).read_bytes()
    assert m.sha256(baseline_bytes) == m.BASELINE_SHA256
    assert m.sha256(catalog_bytes) == m.CATALOG_SHA256
    baseline = m.strict_json(baseline_bytes)
    summary, _ = m.summarize(baseline, m.strict_json(catalog_bytes), baseline)
    assert summary["counts"]["raw_observations"] == 24
    assert summary["counts"]["successful_reads"] == 21
    assert summary["counts"]["unique_verified_games"] == 21
    assert summary["counts"]["selected_games"] == 303


def test_export_actual_consumed_bytes_fresh_output_and_drift(tmp_path, monkeypatch):
    # Root remains the actual repository so the implementation has a portable descriptor.
    # Redirect only file reads/output operations into pytest's private fixture root.
    root = tmp_path
    for relative in (m.CATALOG, m.BASELINE, "summarize_playback.py"):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        original = SCRIPT if relative == "summarize_playback.py" else ROOT / relative
        destination.write_bytes(original.read_bytes())
    monkeypatch.setattr(m, "__file__", str(root / "summarize_playback.py"))
    source = root / "source.json"
    source.write_bytes((root / m.BASELINE).read_bytes())
    output = root / "new-output"
    result = m.export(source, output, root)
    assert (output / "observations.json").read_bytes() == source.read_bytes()
    assert result["inputs"]["observations"]["sha256"] == m.sha256(source.read_bytes())
    assert all(not item["path"].startswith("/") for item in result["inputs"].values())
    with pytest.raises(FileExistsError):
        m.export(source, output, root)
    original = m.summarize

    def mutate_after_consumption(*args):
        value = original(*args)
        source.write_bytes(source.read_bytes() + b" ")
        return value

    monkeypatch.setattr(m, "summarize", mutate_after_consumption)
    with pytest.raises(ValueError, match="changed during run"):
        m.export(source, root / "drift-output", root)
    assert not (root / "drift-output").exists()
    (root / m.CATALOG).write_bytes(b"{}")
    with pytest.raises(ValueError, match="pinned"):
        m.export(source, root / "wrong-pin-output", root)


def test_success_missing_required_evidence_limits_and_failure_reason():
    for missing in ("full_length_playback_verified", "full_coverage_verified", "independent_reviews_completed", "playback"):
        source, catalog, baseline = fixtures()
        source["observations"][0].pop(missing)
        with pytest.raises(ValueError):
            m.summarize(source, catalog, baseline)
    source, catalog, baseline = fixtures()
    source["observations"][0] = {"game_id": "0022000021", "status": "NOT_VERIFIED", "checked_at": "2026-11-06T18:00:00Z"}
    with pytest.raises(ValueError, match="reason"):
        m.summarize(source, catalog, baseline)


def test_recovery_does_not_add_selected_attempt_or_human_evidence():
    source, catalog, baseline = fixtures()
    source["recovery"] = {"game_id": "0022999999", "official_url": "https://www.nba.com/game/mia-vs-lac-0022999999"}
    assert m.summarize(source, catalog, baseline)[0]["counts"]["attempted_games"] == 1
    source["recovery"]["independent_reviews_completed"] = 1
    with pytest.raises(ValueError, match="human evidence"):
        m.summarize(source, catalog, baseline)


def test_postwrite_drift_removes_only_new_export(tmp_path, monkeypatch):
    for relative in (m.CATALOG, m.BASELINE, "summarize_playback.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SCRIPT if relative == "summarize_playback.py" else ROOT / relative).read_bytes())
    monkeypatch.setattr(m, "__file__", str(tmp_path / "summarize_playback.py"))
    source = tmp_path / "source.json"
    source.write_bytes((tmp_path / m.BASELINE).read_bytes())
    original = Path.write_text

    def drift_during_write(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == "reviewer_access_addendum.json":
            source.write_bytes(source.read_bytes() + b" ")
        return result

    monkeypatch.setattr(Path, "write_text", drift_during_write)
    output = tmp_path / "new-export"
    with pytest.raises(ValueError, match="changed during run"):
        m.export(source, output, tmp_path)
    assert not output.exists()
    assert source.exists()


def team_fixture():
    source, catalog, baseline = fixtures()
    row = source["observations"][0]
    row.update(status="TEAM_STREAM_PLAYBACK_OBSERVED", full_length_playback_verified=False,
               full_games_selected=False, team_broadcast_playback_observed=True,
               evidence_mode="named_team_stream_v1", full_game_classification="inferred",
               player_header_text="HAWKS @ GRIZZLIES\n\nGrizzlies",
               team_stream_selection={"label": "Grizzlies", "observed_at": "2026-11-06T18:01:00Z",
                                      "menu_options": ["Grizzlies", "Hawks", "Mobile View", "All Possessions",
                                                       "10 Minute Condensed", "Away Condensed", "Game Recap"],
                                      "title_teams": ["Atlanta Hawks", "Memphis Grizzlies"]})
    row["playback"].update(video_width=1280, video_height=720)
    return source, catalog, baseline


def test_secondary_category_preserves_strict_meaning_and_actual_evidence():
    source, catalog, baseline = team_fixture()
    before = deepcopy(source)
    summary, addon = m.summarize(source, catalog, baseline)
    counts = summary["counts"]
    assert counts["strict_verified_games"] == counts["unique_verified_games"] == counts["successful_reads"] == 0
    assert counts["full_game_classification_explicit_games"] == 0
    assert counts["team_broadcast_observed_games"] == counts["unique_playback_observed_games"] == 1
    assert counts["team_broadcast_observed_reads"] == counts["playback_observed_reads"] == 1
    assert summary["games"][0]["successful_observations"] == []
    secondary = addon["games"][0]["team_broadcast_observations"][0]
    assert secondary["evidence_mode"] == "named_team_stream_v1"
    assert secondary["full_game_classification"] == "inferred"
    assert secondary["stream_label"] == "Grizzlies"
    assert secondary["duration_seconds"] == 6000
    assert secondary["stream_selection_observed_at"] == "2026-11-06T18:01:00Z"
    assert addon["games"][0]["opening_playback_observed"] is True
    assert source == before


@pytest.mark.parametrize("mutate", [
    lambda row: row["team_stream_selection"].update(label="Raptors"),
    lambda row: row["team_stream_selection"].update(title_teams=["Atlanta Hawks", "Toronto Raptors"]),
    lambda row: row["team_stream_selection"].update(menu_options=["Hawks", "10 Minute Condensed"]),
    lambda row: row["team_stream_selection"].update(menu_options=["Hawks", "Grizzlies"]),
    lambda row: row["team_stream_selection"].update(observed_at="2026-11-06T18:01:00"),
    lambda row: row["playback"].update(video_width=0),
    lambda row: row["playback"].update(video_height=0),
    lambda row: row["playback"].update(video_width=True),
    lambda row: row["playback"].update(current_time_seconds=0),
    lambda row: row.update(full_length_playback_verified=True),
    lambda row: row.update(full_games_selected=True),
    lambda row: row.update(team_broadcast_playback_observed=False),
    lambda row: row.update(status="OPENING_PLAYBACK_VERIFIED"),
    lambda row: row.update(full_game_classification="explicit"),
    lambda row: row.update(evidence_mode="full_games_tab_v1"),
    lambda row: row.update(player_header_text="HAWKS @ GRIZZLIES\nHawks"),
])
def test_secondary_invalid_declarations_rejected(mutate):
    source, catalog, baseline = team_fixture()
    mutate(source["observations"][0])
    with pytest.raises(ValueError):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("label", ["Grizzlies Condensed", "Game Recap", "All Possessions", "Mobile View",
                                   "Grizzlies Audio", "Grizzlies Radio", "CourtVision Grizzlies", "Generic Grizzlies",
                                   "izzlies", "Memphis", "Gr"])
def test_condensed_mobile_generic_and_partial_names_cannot_pretend_team_stream(label):
    source, catalog, baseline = team_fixture()
    row = source["observations"][0]
    row["team_stream_selection"]["label"] = label
    row["team_stream_selection"]["menu_options"].append(label)
    row["player_header_text"] = "HAWKS @ GRIZZLIES\n" + label
    with pytest.raises(ValueError):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("label", ["Memphis Grizzlies", "Grizzlies", "Atlanta Hawks", "Hawks"])
def test_secondary_full_names_and_word_boundary_suffixes(label):
    source, catalog, baseline = team_fixture()
    row = source["observations"][0]
    row["team_stream_selection"]["label"] = label
    row["team_stream_selection"]["menu_options"].append(label)
    row["player_header_text"] = "HAWKS @ GRIZZLIES\n" + label
    assert m.summarize(source, catalog, baseline)[0]["counts"]["team_broadcast_observed_games"] == 1


def test_secondary_union_complete_overlap_and_failed_old_reads_preserved():
    source, catalog, baseline = team_fixture()
    strict_source, _, _ = fixtures()
    failed = deepcopy(source["observations"][0])
    failed.update(status="NOT_VERIFIED", team_broadcast_playback_observed=False)
    failed["playback"]["paused"] = True
    source["observations"].insert(0, failed)
    strict_second = strict_source["observations"][0]
    strict_second.update(game_id="0022000045", official_url=catalog["games"][1]["candidate_game_url"],
                         final_url=catalog["games"][1]["candidate_game_url"],
                         page_title="Portland Trail Blazers vs Los Angeles Lakers Dec 28, 2020 Game Summary | NBA.com")
    source["observations"].append(strict_second)
    summary, _ = m.summarize(source, catalog, baseline)
    assert summary["status"] == "ALL_SELECTED_REPLAY_ACCESS_OBSERVED"
    assert summary["counts"]["strict_verified_games"] == 1
    assert summary["counts"]["team_broadcast_observed_games"] == 1
    assert summary["counts"]["unique_playback_observed_games"] == 2
    assert summary["counts"]["raw_observations"] == 3
    assert summary["unverified_game_ids"] == ["0022000021"]
    assert summary["playback_unobserved_game_ids"] == []
    # A later strict check for the same game must not double-count the union.
    source["observations"].append(fixtures()[0]["observations"][0])
    summary, _ = m.summarize(source, catalog, baseline)
    assert summary["counts"]["unique_playback_observed_games"] == 2
    assert summary["counts"]["strict_verified_games"] == 2
    assert summary["counts"]["team_broadcast_observed_games"] == 1
    assert summary["status"] == "ALL_SELECTED_OPENINGS_VERIFIED"


def test_secondary_addendum_omits_selection_menu_and_coordinator_information():
    source, catalog, baseline = team_fixture()
    source["observations"][0]["team_stream_selection"]["coordinator_input_path"] = "SECRET"
    catalog["games"][0].update(stratum="SECRET", parser_label="SECRET", tolerance="SECRET")
    _, addon = m.summarize(source, catalog, baseline)
    serialized = json.dumps(addon)
    assert "SECRET" not in serialized
    assert "menu_options" not in serialized
    assert "title_teams" not in serialized
    assert "observation_index" not in serialized


@pytest.mark.parametrize("kind", [{"stratum": "enriched", "model_label": "candidate_v7",
                                   "coordinator_input_path": "output/v2/private-plan.json", "tolerance": 0.01},
                                  "enriched_candidate_v7", 123])
def test_reviewer_metadata_kind_rejects_uncontrolled_values(kind):
    source, catalog, baseline = fixtures()
    source["observations"][0]["kind"] = kind
    with pytest.raises(ValueError, match="kind"):
        m.summarize(source, catalog, baseline)


def test_reviewer_omits_even_controlled_raw_method_kind():
    source, catalog, baseline = fixtures()
    source["observations"][0]["kind"] = "opening_playback_check"
    _, addon = m.summarize(source, catalog, baseline)
    descriptor = addon["games"][0]["successful_observations"][0]
    assert "kind" not in descriptor
    assert descriptor["timestamp_kind"] == "checked_at"


@pytest.mark.parametrize("header", [{"stratum": "enriched"}, ["HAWKS @ GRIZZLIES"]])
def test_untrusted_nested_player_header_not_exported(header):
    source, catalog, baseline = fixtures()
    source["observations"][0]["player_header_text"] = header
    with pytest.raises(ValueError, match="header"):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("secondary", [False, True])
def test_contradictory_captured_matchup_header_rejected(secondary):
    source, catalog, baseline = team_fixture() if secondary else fixtures()
    source["observations"][0]["player_header_text"] = "CELTICS @ 76ERS\n\nGrizzlies"
    with pytest.raises(ValueError, match="header"):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("url", ["HTTPS://media.nba.com/private-stream.m3u8?signature=PRIVATE",
                                 "HtTpS://media.nba.com/private-stream.m3u8",
                                 "BLOB:https://media.nba.com/PRIVATE", "DATA:video/mp4;base64,PRIVATE"])
def test_uppercase_private_url_schemes_rejected(url):
    source, catalog, baseline = fixtures()
    source["observations"][0]["reason"] = url
    with pytest.raises(ValueError):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("header", ["HAWKS @ GRIZZLIES , DEC 26, 2020\n\nGrizzlies",
                                    "atl @ mem\n\nGrizzlies", "Atlanta Hawks @ Memphis Grizzlies\nGrizzlies"])
def test_known_captured_header_formats_keep_secondary_valid(header):
    source, catalog, baseline = team_fixture()
    source["observations"][0]["player_header_text"] = header
    assert m.summarize(source, catalog, baseline)[0]["counts"]["team_broadcast_observed_games"] == 1


@pytest.mark.parametrize("header", ["GRIZZLIES @ HAWKS\nGrizzlies", "ATL @ LAL\nGrizzlies",
                                    "HAWKS @ IZZLIES\nGrizzlies", "Grizzlies"])
def test_header_partial_suffix_wrong_home_or_away_and_missing_matchup_rejected(header):
    source, catalog, baseline = team_fixture()
    source["observations"][0]["player_header_text"] = header
    with pytest.raises(ValueError, match="header"):
        m.summarize(source, catalog, baseline)


def test_all_actual_controlled_kinds_remain_valid_and_blinded():
    assert len(m.OBSERVATION_KINDS) == 6
    for kind in m.OBSERVATION_KINDS:
        source, catalog, baseline = fixtures()
        source["observations"][0]["kind"] = kind
        summary, addon = m.summarize(source, catalog, baseline)
        assert summary["games"][0]["successful_observations"][0]["kind"] == kind
        assert "kind" not in addon["games"][0]["successful_observations"][0]


@pytest.mark.parametrize("secondary", [False, True])
def test_reviewer_never_exports_raw_header_middle_lines(secondary):
    source, catalog, baseline = team_fixture() if secondary else fixtures()
    header = ("HAWKS @ GRIZZLIES\nstratum=enriched\nmodel=candidate_v7\n"
              "tolerance=0.01\ncoordinator_input_path=output/v2/private-plan.json\nGrizzlies")
    source["observations"][0]["player_header_text"] = header
    before = deepcopy(source)
    summary, addon = m.summarize(source, catalog, baseline)
    observations = summary["games"][0]["team_broadcast_observations" if secondary else "successful_observations"]
    assert observations[0]["player_header"] == header
    assert source == before
    serialized = json.dumps(addon)
    assert "player_header" not in serialized
    assert "stratum=enriched" not in serialized
    assert "candidate_v7" not in serialized
    assert "tolerance=0.01" not in serialized
    assert "private-plan.json" not in serialized


@pytest.mark.parametrize("secondary", [False, True])
def test_header_explicit_contradictory_date_refuses(secondary):
    source, catalog, baseline = team_fixture() if secondary else fixtures()
    source["observations"][0]["player_header_text"] = "HAWKS @ GRIZZLIES , DEC 25, 2020\n\nGrizzlies"
    with pytest.raises(ValueError, match="header"):
        m.summarize(source, catalog, baseline)


@pytest.mark.parametrize("secondary", [False, True])
@pytest.mark.parametrize("suffix", ["", " , DEC 26, 2020", ", December 26, 2020", ", 2020-12-26"])
def test_matching_or_missing_captured_header_date_preserves_observation(secondary, suffix):
    source, catalog, baseline = team_fixture() if secondary else fixtures()
    source["observations"][0]["player_header_text"] = "HAWKS @ GRIZZLIES" + suffix + "\n\nGrizzlies"
    summary, _ = m.summarize(source, catalog, baseline)
    assert summary["counts"]["unique_playback_observed_games"] == 1


def test_real_january_17_header_and_baseline_preserved():
    baseline = m.strict_json((ROOT / m.BASELINE).read_bytes())
    catalog = m.strict_json((ROOT / m.CATALOG).read_bytes())
    before = deepcopy(baseline)
    summary, _ = m.summarize(baseline, catalog, baseline)
    assert summary["counts"]["strict_verified_games"] == 21
    assert baseline == before
    game = next(game for game in catalog["games"] if game["game_id"] == "0022000201")
    assert game["date"] == "2021-01-17"
    assert m.header_matches("PELICANS @ KINGS , JAN 17, 2021\n\nLocal Home Broadcast", game)
    assert not m.header_matches("PELICANS @ KINGS , JAN 16, 2021\n\nLocal Home Broadcast", game)
