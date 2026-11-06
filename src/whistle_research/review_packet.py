"""Blinded preparation only: review-packet-v1, never independent evidence.

manifest.json is coordinator-only. It binds exact plan/protocol bytes, parser and
source hashes, and each reviewer's raw ledger (path/bytes/sha256). reviewer_kits[slot].manifest_file
binds each delivered redacted manifest, which in turn binds its local protocol,
instructions and every ledger. Give each human
only their reviewer_A or reviewer_B directory. Raw ledgers contain original CDN
rows plus unique ``member:row`` refs; no sampling frame, stratum, parser labels or
scores. Source possession/team fields remain visibly raw feed evidence, a blinding
limitation. Annotation templates are intentionally empty and cannot pass validation.

CLI: python -m whistle_research.review_packet --plan ... --source-manifest ...
--cache ... --protocol ... [--access ...] --output NEW_DIRECTORY
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from whistle_research.audit import validate_plan
from whistle_research.feed_compare import stream_rows
from whistle_research.reconcile import verified_snapshot
from whistle_research.sources import file_digest, safe_path

BINDINGS = ("plan_sha256", "parser_version", "parser_sha256")
ANNOTATION_VERSION = "human-full-game-annotation-v1"
PREDICTION_START_GUIDANCE = {
    "reference_ref": "Before-event raw member:row ref; may precede this group; null only for actual period_start without a source-event ref.",
    "period": "Independent period at the declared before-event prediction point.",
    "clock": "Independent clock at that same point; follow the production comparison value representation.",
    "score_margin": "Absolute value of the independent before-event score_difference.",
    "score_difference": "Independent before-event defense score minus offense score.",
    "home_defense": "Integer 0 or 1: whether the defending team is the home team.",
    "defense_counted_fouls": "Independent defense counted-foul total before this event.",
    "previous_foul_1": "Independent preceding-possession counted-foul indicator; explicit null if unavailable.",
    "previous_foul_2": "Independent second-preceding-possession counted-foul indicator; explicit null if unavailable.",
    "start_type": "Independent declared opportunity start classification, including period_start where applicable.",
}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def descriptor(root: Path, path: Path) -> dict:
    size, sha = file_digest(path)
    return {"path": path.relative_to(root).as_posix(), "bytes": size, "sha256": sha}


def build_packet(plan_path: Path, source_manifest: Path, cache: Path,
                 access_path: Path | None, protocol_path: Path, output: Path) -> dict:
    """Verify exact selected sources, then create two separate empty review kits."""
    plan_bytes, protocol_bytes = plan_path.read_bytes(), protocol_path.read_bytes()
    plan = json.loads(plan_bytes)
    reasons = validate_plan(plan)
    if reasons:
        raise ValueError("invalid audit plan: " + ", ".join(reasons))
    entries = json.loads(source_manifest.read_bytes())
    if not isinstance(entries, list) or len({e["file"] for e in entries}) != len(entries):
        raise ValueError("invalid/duplicate source manifest")
    sources = {e["file"]: e for e in entries}
    selected = {g["game_id"]: g for g in plan["games"]}
    events = {gid: [] for gid in selected}
    used_sources = []
    for name in sorted({g["source_file"] for g in selected.values()}):
        entry = sources[name]
        games = {gid: g for gid, g in selected.items() if g["source_file"] == name}
        if any(g["source_sha256"] != entry["sha256"] for g in games.values()):
            raise ValueError("plan source hash differs from manifest")
        with verified_snapshot(safe_path(cache, name), entry["bytes"], entry["sha256"]) as snapshot:
            for gid, aid, row in stream_rows(snapshot):
                if gid in games:
                    if row["member"] != games[gid]["source_member"]:
                        raise ValueError("selected game in unexpected source member")
                    events[gid].append({"ref": f'{row["member"]}:{row["row"]}',
                                        "event_id": aid, **row})
        used_sources.append({"file": name, "bytes": entry["bytes"], "sha256": entry["sha256"]})
    if any(not rows for rows in events.values()):
        raise ValueError("selected game absent from raw source")
    access_bytes = access_path.read_bytes() if access_path is not None else None
    access = json.loads(access_bytes) if access_bytes is not None else {}
    observations = {g["game_id"]: g for g in access.get("games", [])}
    output.mkdir(parents=True, exist_ok=False)
    (output / "plan.json").write_bytes(plan_bytes)
    (output / "protocol.md").write_bytes(protocol_bytes)
    if access_bytes is not None:
        (output / "access.json").write_bytes(access_bytes)
    binding = {k: plan[k] for k in BINDINGS}
    manifest = {"schema_version": "review-packet-v1", "status": "PREPARATION_ONLY",
                **binding, "plan_file": descriptor(output, output / "plan.json"),
                "protocol_file": descriptor(output, output / "protocol.md"),
                "sources": used_sources, "games": [], "reviewer_kits": {},
                "access_file": descriptor(output, output / "access.json") if access_bytes else None}
    for gid, game in selected.items():
        identity = {k: game[k] for k in ("game_id", "source_file", "source_sha256", "source_member")}
        observed_url = observations.get(gid, {}).get("official_url")
        parsed_url = urlsplit(observed_url) if isinstance(observed_url, str) else None
        official_url = observed_url if parsed_url and parsed_url.scheme == "https" and parsed_url.netloc == "www.nba.com" and parsed_url.path.startswith("/game/") and parsed_url.path.endswith(gid) and not parsed_url.query and not parsed_url.fragment else None
        item = {**identity, "official_game_url": official_url or "https://www.nba.com/game/" + gid,
                "official_url_status": "observed" if official_url else "unverified_fallback", "ledgers": {}, "access_status": "opening_playback_observed"
                if observations.get(gid, {}).get("full_length_playback_verified") is True else "unverified",
                "continuous_coverage": "unverified", "review_status": "absent"}
        for slot in ("A", "B"):
            kit = output / f"reviewer_{slot}"
            ledger_path = kit / "raw_events" / f"{gid}.json"
            write_json(ledger_path, {"schema_version": "raw-review-ledger-v1", **identity, "events": events[gid]})
            item["ledgers"][slot] = descriptor(output, ledger_path)
            template = {"schema_version": ANNOTATION_VERSION, **binding, **identity,
                        "reviewer_slot": slot, "reviewer_id": None, "reviewer_kind": None,
                        "started_at": None, "completed_at": None, "evidence_ref": None,
                        "full_game_reviewed": False, "independent": False,
                        "material_discrepancy": None, "critical_unresolved": None,
                        "coverage": None, "possessions": [], "excluded_events": [],
                        "_guidance": {
                            "possession_entry": {
                                "prediction_start": PREDICTION_START_GUIDANCE,
                                "start_context_footage": "Optional {reference,start_seconds,end_seconds} evidence for the before-event point, which may precede this group."},
                            "prediction_start_requirement": "Optional for structural intake; REQUIRED for production candidate comparison. Fill independently; no candidate values are supplied.",
                            "material_discrepancy": "Blinded raw/film discrepancy. Coordinator later computes candidate agreement; any candidate mismatch blocks promotion even if both human flags are false."}}
            write_json(kit / "annotations" / f"{gid}.json", template)
        manifest["games"].append(item)
    instructions = """Independent full-game review

This is an EMPTY preparation kit, not completed evidence. Review the entire game
independently using continuous footage in first broadcast order (not replay clips) and raw official events under protocol.md. Do not use
parser output, model scores, or another reviewer's labels. Original raw feed team
and possession fields are visible and may be wrong; record uncertainty explicitly.
Fill your own annotation file following human-full-game-annotation-v1 in the
review_evidence module documentation. Preserve every raw event: assign it once to
a possession range or explicitly exclude it with evidence and a reason. Do not
repair source rows. An unresolved or uncertain case blocks promotion. Record your
identity, human kind, timestamps, coverage and footage references yourself. Never
copy templates into completed reviews. Access observations are not full coverage.
Template _guidance describes each prediction_start field without supplying labels.
Production comparison requires independently filled before-event prediction_start
for every possession. Structural intake alone does not confer acceptance.
Your blinded material_discrepancy flags describe raw/film discrepancies. The
coordinator later compares your original annotations with the candidate; any
candidate mismatch blocks promotion even when both human flags are false.
"""
    for slot in ("A", "B"):
        kit = output / f"reviewer_{slot}"
        (kit / "protocol.md").write_bytes(protocol_bytes)
        from whistle_research.review_evidence import __doc__ as schema_instructions
        (kit / "INSTRUCTIONS.md").write_text(instructions + "\n" + schema_instructions)
        write_json(kit / "manifest.json", {
            "schema_version": "blinded-review-kit-v1", "reviewer_slot": slot,
            "status": "PREPARATION_ONLY", **binding,
            "protocol_file": descriptor(kit, kit / "protocol.md"),
            "instructions_file": descriptor(kit, kit / "INSTRUCTIONS.md"),
            "games": [{"game_id": g["game_id"], "source_file": g["source_file"],
                       "source_sha256": g["source_sha256"], "source_member": g["source_member"],
                       "official_game_url": g["official_game_url"], "official_url_status": g["official_url_status"],
                       "access_status": g["access_status"], "continuous_coverage": "unverified",
                       "ledger": {**g["ledgers"][slot],
                                  "path": "raw_events/" + g["game_id"] + ".json"},
                       "annotation_path": "annotations/" + g["game_id"] + ".json"}
                      for g in manifest["games"]]})
        manifest["reviewer_kits"][slot] = {"manifest_file": descriptor(output, kit / "manifest.json")}
    write_json(output / "manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "source-manifest", "cache", "protocol", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--access", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_packet(args.plan, args.source_manifest, args.cache, args.access, args.protocol, args.output)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"review packet error: {exc}\n")
    print(json.dumps({"status": result["status"], "games": len(result["games"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
