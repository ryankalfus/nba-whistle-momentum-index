"""Immutable byte verification and streaming, source-observed game inventories."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tarfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

SCHEMA_VERSION = "source-ledger-v1"
# These are declared archive identities, not an inference from game ID prefixes.
OFFICIAL_ARCHIVES = {
    **{f"cdnnba_{year}.tar.xz": (f"{year}-{str(year + 1)[-2:]}", "regular_season")
       for year in range(2020, 2025)},
    "cdnnba_po_2024.tar.xz": ("2024-25", "playoffs"),
}


def canonical_game_id(value: str) -> str:
    """Accept integer-shaped NBA IDs only; retain the canonical ten digits."""
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", value):
        raise ValueError(f"invalid game ID: {value!r}")
    return value.zfill(10)


def stream_digest(stream) -> tuple[int, str]:
    """Hash from the current position without closing the caller's descriptor."""
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def file_digest(path: Path) -> tuple[int, str]:
    with path.open("rb") as stream:
        return stream_digest(stream)


def file_identity(stat) -> tuple:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def safe_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("invalid relative source path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or relative.as_posix() != name or any(p in ("..", ".") for p in name.split("/")):
        raise ValueError("source path must be relative without traversal")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("source path escapes input directory")
    return path


def verify_sources(manifest: Path, root: Path) -> dict:
    """Hash every declared file; represent failures rather than using bad bytes."""
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("source manifest must be a list")
    names = [e.get("file") for e in entries if isinstance(e, dict)]
    duplicates = {n for n, count in Counter(n for n in names if isinstance(n, str)).items() if count > 1}
    rows = []
    for index, entry in enumerate(entries):
        row = {"manifest_index": index, "status": "invalid_manifest"}
        try:
            if not isinstance(entry, dict):
                raise ValueError("source entry must be an object")
            name = entry.get("file")
            row.update(source_file=name, source_url=entry.get("url"),
                       expected_bytes=entry.get("bytes"), expected_sha256=entry.get("sha256"))
            path = safe_path(root, name)
            if name in duplicates:
                raise ValueError("duplicate source path")
            size, sha = entry.get("bytes"), entry.get("sha256")
            if type(size) is not int or size < 0 or not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
                raise ValueError("expected nonnegative bytes and lowercase SHA256")
            if not path.exists():
                row["status"] = "missing"
            elif not path.is_file():
                row.update(status="invalid_source", reason="not a regular file")
            else:
                actual_size, actual_sha = file_digest(path)
                row.update(actual_bytes=actual_size, source_sha256=actual_sha)
                row["status"] = "verified" if (size, sha) == (actual_size, actual_sha) else "hash_mismatch"
        except OSError as exc:
            row.update(status="invalid_source", reason=exc.strerror or type(exc).__name__)
        except (ValueError, TypeError) as exc:
            row["reason"] = str(exc)
        rows.append(row)
    return {"schema_version": SCHEMA_VERSION, "kind": "verification",
            "manifest_sha256": file_digest(manifest)[1], "sources": rows,
            "ok": bool(rows) and all(r["status"] == "verified" for r in rows)}


def read_schedule(path: Path, provenance: str | None = None) -> tuple[list[dict], dict]:
    """Read an explicit independently supplied expected-game frame."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream, strict=True)
            headers = reader.fieldnames or []
            if not headers or len(headers) != len(set(headers)) or any(not h for h in headers):
                raise ValueError("invalid or duplicate schedule CSV columns")
            if not {"game_id", "season", "game_type"}.issubset(headers):
                raise ValueError("missing schedule CSV columns")
            rows = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("malformed schedule CSV row")
                rows.append(row)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows, provenance = data["games"], data.get("provenance", provenance)
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("schedule needs explicit independent provenance")
    result, seen = [], set()
    for row in rows:
        game_id = canonical_game_id(row["game_id"])
        if game_id in seen:
            raise ValueError(f"duplicate schedule game: {game_id}")
        seen.add(game_id)
        status = row.get("status", "expected")
        if status not in {"expected", "unavailable", "excluded", "failed"}:
            raise ValueError("unknown schedule status")
        if status != "expected" and not row.get("reason"):
            raise ValueError("non-expected schedule rows require a reason")
        if not row.get("season") or not row.get("game_type"):
            raise ValueError("schedule rows require season and game_type")
        result.append({**row, "game_id": game_id, "status": status})
    if not result:
        raise ValueError("schedule must contain games")
    return result, {"sha256": file_digest(path)[1], "provenance": provenance}


def inventory_sources(verification: dict, root: Path, schedule: Path | None = None,
                      schedule_provenance: str | None = None) -> dict:
    """Stream verified official CSV members without extracting archives to disk."""
    games, anomalies, skipped = {}, [], []
    for source in verification["sources"]:
        name = source.get("source_file")
        if source["status"] != "verified" or name not in OFFICIAL_ARCHIVES:
            skipped.append({"source_file": name, "reason": source["status"] if source["status"] != "verified" else "not_declared_official_event_archive"})
            continue
        # Bind hashes and parsing to one descriptor, then check it again after parsing.
        path = safe_path(root, name)
        season, game_type = OFFICIAL_ARCHIVES[name]
        member_names, csv_count = set(), 0
        try:
            with path.open("rb") as source_stream:
                before = file_identity(os.fstat(source_stream.fileno()))
                digest = stream_digest(source_stream)
                if digest != (source["actual_bytes"], source["source_sha256"]) or digest != (source["expected_bytes"], source["expected_sha256"]):
                    raise ValueError("source_changed_after_verification")
                source_stream.seek(0)
                with tarfile.open(fileobj=source_stream, mode="r:xz") as archive:
                    for member in archive:
                        safe_path(root, member.name)
                        if member.name in member_names:
                            raise ValueError("duplicate archive member")
                        member_names.add(member.name)
                        if not member.isfile() or not member.name.endswith(".csv"):
                            raise ValueError("unsupported archive member")
                        csv_count += 1
                        with io.TextIOWrapper(archive.extractfile(member), encoding="utf-8-sig", newline="") as stream:
                            reader = csv.DictReader(stream)
                            required = {"gameId", "actionNumber", "orderNumber"}
                            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
                                raise ValueError("duplicate CSV column names")
                            if not required.issubset(reader.fieldnames or []):
                                raise ValueError("missing official event columns")
                            for row_number, row in enumerate(reader, start=2):
                                if None in row or any(row.get(column) is None for column in required):
                                    anomalies.append({"source_file": name, "source_member": member.name,
                                                      "row": row_number, "reason": "malformed_csv_row"})
                                    continue
                                try:
                                    game_id = canonical_game_id(row["gameId"])
                                except ValueError:
                                    anomalies.append({"source_file": name, "source_member": member.name,
                                                      "row": row_number, "reason": "invalid_game_id"})
                                    continue
                                key = (name, member.name, game_id)
                                game = games.setdefault(key, {"game_id": game_id, "source_file": name,
                                    "source_sha256": source["source_sha256"], "source_member": member.name,
                                    "season": season, "game_type": game_type, "event_count": 0,
                                    "first_source_row": row_number, "last_source_row": row_number,
                                    "anomalies": [], "_ids": set(), "_last_order": None})
                                game["event_count"] += 1
                                game["last_source_row"] = row_number
                                event_id = row["actionNumber"]
                                if not event_id or event_id in game["_ids"]:
                                    game["anomalies"].append("missing_or_duplicate_event_id")
                                game["_ids"].add(event_id)
                                try:
                                    # Decimal avoids rounding event ordering from feed text.
                                    order = Decimal(row["orderNumber"])
                                    if not order.is_finite():
                                        raise InvalidOperation
                                    if game["_last_order"] is not None and order <= game["_last_order"]:
                                        game["anomalies"].append("nonincreasing_event_order")
                                    game["_last_order"] = order
                                except (InvalidOperation, TypeError, ValueError):
                                    game["anomalies"].append("invalid_event_order")
                    for _ in iter(lambda: archive.fileobj.read(1024 * 1024), b""):
                        pass
                source_stream.seek(0)
                if (stream_digest(source_stream) != digest
                        or file_identity(os.fstat(source_stream.fileno())) != before
                        or file_identity(path.stat()) != before):
                    raise ValueError("source_changed_during_inventory")
            if csv_count == 0:
                raise ValueError("no event CSV members")
        except (ValueError, OSError, EOFError, tarfile.TarError, csv.Error, UnicodeError) as exc:
            anomalies.append({"source_file": name, "reason": str(exc)})
    rows = []
    ids = Counter(g["game_id"] for g in games.values())
    failed_sources = {a["source_file"] for a in anomalies}
    for key in sorted(games):
        game = games[key]
        del game["_ids"], game["_last_order"]
        if game["source_file"] in failed_sources:
            game["anomalies"].append("source_archive_has_failures")
        if ids[game["game_id"]] > 1:
            game["anomalies"].append("duplicate_game_across_sources_or_members")
        game["anomalies"] = sorted(set(game["anomalies"]))
        game["disposition"] = "quarantined" if game["anomalies"] else "observed"
        rows.append(game)
    coverage = {"status": "observed_only", "schedule_evidence": None,
                "completeness": "unverified", "games": []}
    if schedule is not None:
        expected, evidence = read_schedule(schedule, schedule_provenance)
        observed = {r["game_id"]: r for r in rows}
        coverage.update(status="schedule_checked", schedule_evidence=evidence)
        for entry in sorted(expected, key=lambda e: e["game_id"]):
            game = observed.get(entry["game_id"])
            state = "observed" if game else "missing"
            if entry["status"] != "expected":
                state = entry["status"]
                if game:
                    game["disposition"] = "excluded" if state == "excluded" else "quarantined"
            elif game and (game["season"], game["game_type"]) != (entry["season"], entry["game_type"]):
                state = "metadata_mismatch"
                game["disposition"] = "quarantined"
            coverage["games"].append({**entry, "observation": state, "observed": game is not None})
        expected_ids = {e["game_id"] for e in expected}
        for game_id in sorted(set(observed) - expected_ids):
            coverage["games"].append({"game_id": game_id, "observation": "unexpected", "observed": True})
            observed[game_id]["disposition"] = "quarantined"
        coverage["completeness"] = "accounted_for" if all(e["observation"] not in {"missing", "unexpected", "metadata_mismatch"} for e in coverage["games"]) else "incomplete"
    return {"schema_version": SCHEMA_VERSION, "kind": "game_inventory",
            "manifest_sha256": verification["manifest_sha256"], "games": rows,
            "source_failures": anomalies, "skipped_sources": skipped, "coverage": coverage,
            "ok": verification["ok"] and not anomalies and bool(rows)
                  and all(not r["anomalies"] for r in rows)
                  and coverage["completeness"] != "incomplete"}


def write_artifact(output: Path, filename: str, data: dict) -> None:
    """An exclusive directory prevents accidental replacement of release artifacts."""
    output.mkdir(parents=True, exist_ok=False)
    with (output / filename).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "inventory"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-root", "--cache", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--schedule-provenance")
    args = parser.parse_args(argv)
    try:
        result = verify_sources(args.manifest, args.source_root)
        if args.command == "inventory":
            result = inventory_sources(result, args.source_root, args.schedule, args.schedule_provenance)
        write_artifact(args.output, f"{args.command}.json", result)
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        parser.exit(2, f"source ledger error: {exc}\n")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
