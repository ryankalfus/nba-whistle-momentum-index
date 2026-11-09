"""Synthetic real-file contracts; these fixtures confer no scientific validation."""

from collections import Counter
import copy
import json

import pytest

from test_release import synthetic_artifacts
from whistle_research import exploratory_cohort as cohort
from whistle_research import modeling, release, sources


@pytest.fixture
def artifacts(tmp_path):
    fixture = synthetic_artifacts(tmp_path / "fixture")
    # The older release fixture intentionally supplies only the reconciliation
    # fields its own tests need; bind the additional cross-artifact accounting.
    for diagnostic, game in zip(fixture["reconciliation"]["games"], fixture["dataset"]["games"], strict=True):
        diagnostic.update(eligible=False, source_event_count=game["source_event_count"],
                          full_game_markers=True, uncertain_possessions=0,
                          unassigned_control_events=False,
                          issues={"independent_audit_required": 1})
    fixture["plan"] = {"cohort": {"season": "2020-21", "game_type": "regular_season"},
                       "split": {"train_start": "2030-01-01", "tune_start": "2030-01-03",
                                 "test_start": "2030-01-05", "test_end": "2030-01-07"}}
    fixture["traces"] = [json.loads(line) for line in
                         (fixture["feature_dir"] / "row_provenance.jsonl").read_text().splitlines()]
    save(fixture)
    return fixture


def save(fixture):
    dataset, root = fixture["dataset"], fixture["feature_dir"]
    (root / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in fixture["rows"]))
    (root / "row_provenance.jsonl").write_text("".join(json.dumps(row) + "\n" for row in fixture["traces"]))
    dataset.update(rows_sha256=modeling.row_digest(fixture["rows"]),
                   rows_file_sha256=sources.file_digest(root / "rows.jsonl")[1],
                   row_provenance_sha256=sources.file_digest(root / "row_provenance.jsonl")[1],
                   missing_fields=dict(Counter(k for row in fixture["rows"] for k, value in row.items() if value is None)),
                   unknown_outcomes=sum(row["outcome"] is None for row in fixture["rows"]))
    (root / "manifest.json").write_text(json.dumps(dataset))
    fixture["reconciliation_path"].write_text(json.dumps(fixture["reconciliation"]))


def prepare(fixture):
    return cohort.prepare_cohort(**{key: fixture[key] for key in (
        "feature_dir", "inventory_path", "reconciliation_path", "source_manifest",
        "cache", "schedule", "metadata", "plan")})


def test_whole_games_original_rows_and_split_missingness(artifacts):
    original = copy.deepcopy(artifacts["rows"])
    result = prepare(artifacts)
    assert set(result) == {"rows", "report", "inputs", "recheck"}
    assert result["rows"] == original
    report = result["report"]
    assert report["status"] == cohort.STATUS
    assert report["eligible"] is report["scientific_approval"] is False
    assert report["counts"]["included_games"] == 6
    assert report["rows_sha256"] == modeling.row_digest(original)
    assert all(part["included_games"] == 2 for part in report["partitions"].values())
    assert report["partitions"]["train"]["missing_fields"]["previous_foul_1"] > 0
    assert all(game["eligible"] is False for game in report["games"])
    assert all(game["eligible"] is False for game in artifacts["dataset"]["games"])
    assert str(artifacts["root"]) not in json.dumps(report)
    assert any(entry["role"] == "code_exploratory_cohort" for entry in result["inputs"])
    assert all(set(entry) == {"role", "path", "bytes", "sha256"} for entry in result["inputs"])
    result["recheck"]()


@pytest.mark.parametrize("field,value,reason", [
    ("critical_unresolved", True, "critical_unresolved"),
    ("critical_unresolved", 0, "unknown_quality_metadata"),
    ("complete", 1, "unknown_quality_metadata"),
    ("unassigned_control_events", 0, "unknown_quality_metadata"),
    ("issues", None, "undocumented_issues"),
    ("issues", [{"code": "mystery", "blocking": 0}], "undocumented_issues"),
])
def test_malformed_or_bad_quality_excludes_entire_game(artifacts, field, value, reason):
    artifacts["dataset"]["games"][0][field] = value
    save(artifacts)
    result = prepare(artifacts)
    first = result["report"]["games"][0]
    assert reason in first["reasons"]
    assert first["selected_for_exploration"] is False
    assert not any(row["game_id"] == first["game_id"] for row in result["rows"])
    assert len(result["rows"]) == len(artifacts["rows"]) - 24


@pytest.mark.parametrize("kind", ["unknown_target", "flagged", "incomplete"])
def test_late_bad_row_removes_whole_game_preserving_other_histories(artifacts, kind):
    index = 23
    game, diagnostic = artifacts["dataset"]["games"][0], artifacts["reconciliation"]["games"][0]
    if kind == "unknown_target":
        artifacts["rows"][index]["outcome"] = None
        game["unknown_outcomes"] = 1
        diagnostic["uncertain_possessions"] = 1
    elif kind == "flagged":
        artifacts["traces"][index]["audit_flags"] = ["uncertain_control"]
    else:
        artifacts["traces"][index]["complete"] = False
        game["complete"] = False
        diagnostic["uncertain_possessions"] = 1
    save(artifacts)
    result = prepare(artifacts)
    assert result["report"]["counts"]["included_games"] == 5
    if kind == "unknown_target":
        assert result["report"]["counts"]["full_frame_unknown_outcomes"] == 1
        assert result["report"]["counts"]["candidate_unknown_outcomes"] == 1
        assert result["report"]["counts"]["excluded_rows"] == 24
    assert result["rows"] == artifacts["rows"][24:]


def test_administrative_unassigned_references_are_explicit(artifacts):
    artifacts["dataset"]["games"][0]["unassigned_action_numbers"] = [1, 4]
    save(artifacts)
    report = prepare(artifacts)["report"]
    assert report["games"][0]["unassigned_action_numbers"] == [1, 4]
    assert report["games"][0]["selected_for_exploration"] is True
    assert "administrative" in report["unassigned_event_policy"]


def test_source_frame_outside_date_range_is_not_candidate_exclusion(artifacts):
    artifacts["plan"]["split"]["train_start"] = "2030-01-02"
    report = prepare(artifacts)["report"]
    assert report["counts"]["full_frame_games"] == 6
    assert report["counts"]["candidate_games"] == 5
    assert report["counts"]["excluded_games"] == 0
    assert report["source_frame"]["out_of_cohort_game_ids"] == [artifacts["frame"][0]["game_id"]]
    assert report["games"][0]["reasons"] == ["outside_date_range"]


def test_test_end_is_exclusive_and_numeric_nulls_remain_missing(artifacts):
    artifacts["plan"]["split"]["test_end"] = "2030-01-06"
    artifacts["rows"][0]["score_margin"] = None
    save(artifacts)
    result = prepare(artifacts)
    assert result["report"]["counts"]["included_games"] == 5
    assert result["rows"][0]["score_margin"] is None
    assert result["report"]["partitions"]["train"]["missing_fields"]["score_margin"] == 1


def test_quarantine_never_becomes_eligible(artifacts):
    artifacts["dataset"]["games"][0].update(status="quarantined", complete=False, critical_unresolved=True)
    artifacts["reconciliation"]["games"][0]["status"] = "quarantined"
    save(artifacts)
    result = prepare(artifacts)
    assert result["report"]["games"][0]["selected_for_exploration"] is False
    assert "not_reconstructed" in result["report"]["games"][0]["reasons"]
    assert result["report"]["counts"]["included_games"] == 5


@pytest.mark.parametrize("change", [
    {"cohort": {"season": "2020-21", "game_type": "unknown"}},
    {"cohort": {"season": "2020-22", "game_type": "regular_season"}},
    {"split": {"train_start": "2030-1-01"}},
    {"split": {"train_start": "2030-01-01", "tune_start": "2030-01-01",
               "test_start": "2030-02-01", "test_end": "2030-03-01"}},
])
def test_invalid_selection_refused_before_input_reads(artifacts, change):
    artifacts["plan"].update(change)
    artifacts["source_manifest"].unlink()
    with pytest.raises(ValueError):
        prepare(artifacts)


@pytest.mark.parametrize("field", ["candidate_possessions", "source_event_count", "uncertain_possessions", "issues"])
def test_cross_artifact_accounting_mismatch_refused(artifacts, field):
    artifacts["reconciliation"]["games"][0][field] = {} if field == "issues" else 999
    save(artifacts)
    with pytest.raises(release.ArtifactError, match="accounting mismatch"):
        prepare(artifacts)


def test_full_frame_integrity_checked_even_outside_selection(artifacts):
    artifacts["plan"]["split"]["train_start"] = "2030-01-02"
    artifacts["rows"][0]["season"] = "2021-22"
    save(artifacts)
    with pytest.raises(release.ArtifactError, match="metadata mismatch"):
        prepare(artifacts)


@pytest.mark.parametrize("target", ["metadata", "source", "stream"])
def test_recheck_detects_drift_without_retaining_source_bytes(artifacts, target):
    result = prepare(artifacts)
    path = {"metadata": artifacts["metadata"][0], "source": next(artifacts["cache"].glob("*.xz")),
            "stream": artifacts["feature_dir"] / "rows.jsonl"}[target]
    with path.open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(release.ArtifactError, match="changed"):
        result["recheck"]()


def test_mutation_during_verification_refused(artifacts, monkeypatch):
    original = release.verify_feature_export
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        with artifacts["metadata"][0].open("a") as stream:
            stream.write("\n")
        return result
    monkeypatch.setattr(release, "verify_feature_export", mutate)
    with pytest.raises(release.ArtifactError, match="changed"):
        prepare(artifacts)


def test_capacity_refuses_never_truncates(artifacts, monkeypatch):
    monkeypatch.setattr(cohort, "MAX_ROWS", 25)
    with pytest.raises(release.ArtifactError, match="capacity exceeded"):
        prepare(artifacts)


@pytest.mark.parametrize("name", ["../rows.jsonl", "/private/rows.jsonl"])
def test_unsafe_stream_path_refused(artifacts, name):
    artifacts["dataset"]["rows_file"] = name
    save(artifacts)
    with pytest.raises(ValueError, match="relative"):
        prepare(artifacts)


def test_missing_source_bytes_refused(artifacts):
    next(artifacts["cache"].glob("*.xz")).unlink()
    with pytest.raises(FileNotFoundError):
        prepare(artifacts)


def test_plan_declared_row_ceiling_is_enforced(artifacts):
    artifacts["plan"]["max_selected_rows"] = 25
    with pytest.raises(release.ArtifactError, match="capacity exceeded"):
        prepare(artifacts)
    artifacts["plan"]["max_selected_rows"] = 300_000
    assert prepare(artifacts)["report"]["counts"]["included_rows"] > 25


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, 1_500_001])
def test_invalid_row_ceiling_refused_before_input_reads(artifacts, limit):
    artifacts["plan"]["max_selected_rows"] = limit
    artifacts["source_manifest"].unlink()
    with pytest.raises(ValueError, match="row ceiling"):
        prepare(artifacts)


def test_list_cohort_selects_multiple_cohorts(artifacts):
    single = prepare(artifacts)["report"]["counts"]["included_games"]
    artifacts["plan"]["cohort"] = [{"season": "2020-21", "game_type": "regular_season"},
                                   {"season": "2021-22", "game_type": "regular_season"}]
    report = prepare(artifacts)["report"]
    assert report["counts"]["included_games"] == single
    assert report["cohort"] == artifacts["plan"]["cohort"]
