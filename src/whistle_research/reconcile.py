"""Offline candidate diagnostics against saved historical counts, never validation."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

from whistle_research.metrics import calculate_wmi
from whistle_research.possessions import PARSER_VERSION, reconstruct
from whistle_research.sources import (
    OFFICIAL_ARCHIVES, canonical_game_id, file_digest, safe_path, verify_sources,
)


@contextmanager
def verified_snapshot(path: Path, expected_size: int, expected_sha256: str):
    """Copy/hash the bytes that will actually be parsed; never reopen the source."""
    digest = hashlib.sha256()
    size = 0
    with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as snapshot:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                snapshot.write(block)
                digest.update(block)
                size += len(block)
        if size != expected_size or digest.hexdigest() != expected_sha256:
            raise ValueError("source snapshot does not match manifest")
        snapshot.seek(0)
        yield snapshot


def archive_games(stream):
    """Yield one contiguous game at a time, retaining original CSV row numbers."""
    seen = set()
    with tarfile.open(fileobj=stream, mode="r|xz") as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith(".csv"):
                continue
            with archive.extractfile(member) as raw:
                # A pipe-mode archive member is not seekable. Decode lines directly.
                reader = csv.DictReader((line.decode("utf-8-sig") for line in raw))
                fields = reader.fieldnames
                if not fields or len(fields) != len(set(fields)) or "gameId" not in fields:
                    raise ValueError("invalid/duplicate event CSV columns")
                current, records, source_rows = None, [], []
                for source_row, row in enumerate(reader, 2):
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError("malformed event CSV row")
                    gid = canonical_game_id(row["gameId"])
                    if current is not None and current != gid:
                        yield current, records, source_rows, member.name
                        seen.add(current)
                        records, source_rows = [], []
                    if gid in seen:
                        raise ValueError("noncontiguous or duplicate game in source")
                    current = gid
                    # Missing values are normalized for parsing, not replaced by zero.
                    records.append({key: (None if value in {"", "NA", "NaN", "nan"} else value)
                                    for key, value in row.items()})
                    source_rows.append(source_row)
                if current is not None:
                    yield current, records, source_rows, member.name
                    seen.add(current)


def metadata_rows(paths: list[Path]):
    result, provenance = {}, []
    for path in paths:
        raw = path.read_bytes()
        provenance.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                           "status": "historical_derived_metadata_not_independent_schedule"})
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("invalid metadata columns")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("malformed metadata row")
            gid = canonical_game_id(row["game_id"])
            if gid in result or not row.get("home") or not row.get("away"):
                raise ValueError("duplicate/incomplete game metadata")
            result[gid] = row
    return result, provenance


def game_diagnostic(actions, game_id, metadata, source_sha256):
    """Compare a complete candidate sequence only; never drop uncertain groups."""
    team_ids = {}
    for action in actions:
        code, tid = action.get("teamTricode"), action.get("teamId")
        if code and tid and str(tid) != "0":
            numeric = float(tid)
            if not numeric.is_integer():
                raise ValueError("noninteger team metadata")
            tid = int(numeric)
            if code in team_ids and team_ids[code] != tid:
                raise ValueError("conflicting source team metadata")
            team_ids[code] = tid
    try:
        home, away = team_ids[metadata["home"]], team_ids[metadata["away"]]
    except KeyError:
        raise ValueError("source teams do not match declared home/away metadata") from None
    result = reconstruct(actions, game_id, home, away, source_sha256)
    uncertain = sum(p.foul_indicator is None or not p.complete for p in result.possessions)
    periods = {event.period for event in result.events}
    period_starts = Counter(event.period for event in result.events
                            if event.kind == "period" and event.subtype == "start")
    period_ends = Counter(event.period for event in result.events
                          if event.kind == "period" and event.subtype == "end")
    terminal = result.events[-1] if result.events else None
    complete_game = bool(
        terminal and terminal.kind == "game" and terminal.subtype == "end"
        and terminal.period >= 4 and terminal.clock == 0
        and periods == set(range(1, terminal.period + 1))
        and all(period_starts[p] == period_ends[p] == 1 for p in periods)
        and terminal.home_score is not None and terminal.away_score is not None
        and terminal.home_score != terminal.away_score
    )
    unassigned_control = any(event.action_number in result.unassigned_action_numbers
                             and event.classification != "administrative"
                             for event in result.events)
    blocking = any(issue.blocking and issue.code != "independent_audit_required"
                   for issue in result.issues)
    # Global windows cannot be computed after deleting ambiguous possessions.
    metric = (calculate_wmi([p.foul_indicator for p in result.possessions], game_id=game_id)
              if result.possessions and complete_game and not uncertain
              and not blocking and not unassigned_control else None)
    issues = Counter(issue.code for issue in result.issues)
    historical_count = int(metadata["possessions"]) if metadata.get("possessions") else None
    diagnostic = {
        "game_id": game_id, "status": "candidate_diagnostic_only", "eligible": False,
        "candidate_possessions": len(result.possessions),
        "historical_hypothesis_groups": historical_count,
        "difference_vs_hypothesis": (len(result.possessions) - historical_count
                                     if historical_count is not None else None),
        "uncertain_possessions": uncertain, "issues": dict(sorted(issues.items())),
        "full_game_markers": complete_game, "unassigned_control_events": unassigned_control,
        "wmi": metric.wmi if metric else None,
        "metric_status": "descriptive_candidate" if metric else "withheld_incomplete_or_ambiguous",
    }
    return diagnostic, result


def reconcile(manifest: Path, cache: Path, metadata: list[Path], output: Path,
              limit_per_source: int = 3, save_games: bool = False):
    if limit_per_source < 0:
        raise ValueError("limit_per_source must be nonnegative; zero means all")
    output.mkdir(parents=True, exist_ok=False)
    verification = verify_sources(manifest, cache)
    rows, failures, issue_counts = [], [], Counter()
    meta, meta_sources = metadata_rows(metadata)
    if save_games:
        (output / "games").mkdir()
    for source in verification["sources"]:
        name = source.get("source_file")
        if source["status"] != "verified" or name not in OFFICIAL_ARCHIVES:
            continue
        try:
            with verified_snapshot(safe_path(cache, name), source["expected_bytes"],
                                   source["expected_sha256"]) as snapshot:
                count = 0
                for gid, actions, source_rows, member in archive_games(snapshot):
                    if limit_per_source and count >= limit_per_source:
                        break
                    count += 1
                    row = {"game_id": gid, "source_file": name,
                           "source_sha256": source["expected_sha256"],
                           "source_member": member, "source_event_count": len(actions)}
                    try:
                        if gid not in meta:
                            raise ValueError("missing declared home/away metadata")
                        diagnostic, result = game_diagnostic(actions, gid, meta[gid],
                                                             source["expected_sha256"])
                        row.update(diagnostic)
                        issue_counts.update(diagnostic["issues"])
                        if save_games:
                            packet = {"reconstruction": asdict(result),
                                      "source_file": name, "source_member": member,
                                      "source_csv_rows": source_rows}
                            with (output / "games" / f"{gid}.json").open("x") as file:
                                json.dump(packet, file, indent=2, sort_keys=True, allow_nan=False)
                    except (ValueError, TypeError, KeyError) as exc:
                        row.update(status="quarantined", eligible=False, error=str(exc), wmi=None)
                    rows.append(row)
        except (ValueError, OSError, EOFError, csv.Error, tarfile.TarError) as exc:
            failures.append({"source_file": name, "error": str(exc)})
            for row in rows:
                if row["source_file"] == name:
                    row.update(status="quarantined", eligible=False, wmi=None,
                               error="source iteration failed; see source_failures")
    report = {
        "schema_version": "candidate-reconciliation-v1", "parser_version": PARSER_VERSION,
        "parser_sha256": file_digest(Path(__file__).with_name("possessions.py"))[1],
        "verification": verification, "metadata": meta_sources,
        "selection": {"method": "first_games_per_archive_diagnostic_not_random",
                      "limit_per_source": limit_per_source},
        "games": rows, "source_failures": failures, "issue_counts": dict(sorted(issue_counts.items())),
        "independent_audit_status": "blocked", "eligible_games": 0,
        "ok": verification["ok"] and not failures and bool(rows),
        "interpretation": "Successful diagnostics are not parser acceptance or scientific validation.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True,
                                                   allow_nan=False) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path, nargs="+")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--limit-per-source", type=int, default=3)
    parser.add_argument("--save-games", action="store_true")
    args = parser.parse_args(argv)
    result = reconcile(args.manifest, args.cache, args.metadata, args.output,
                       args.limit_per_source, args.save_games)
    print(json.dumps({"diagnostic_games": len(result["games"]), "eligible_games": 0,
                      "independent_audit_status": "blocked", "ok": result["ok"]}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
