"""Source-verified v5 quarantine evidence; never alter events or run evaluation.

Run from the repository root with .venv/bin/python. --check reproduces the
committed JSON without writing it. The frozen v5 report defines this cohort;
the current reconstruction function is intentionally not executed.
"""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re

from whistle_research.reconcile import archive_games, verified_snapshot
from whistle_research.sources import OFFICIAL_ARCHIVES, safe_path


REPORT = Path("output/v2/reconciliation-semantics-v5-2026-11-02/report.json")
MANIFEST = Path("research/hypotheses_2026_09_12/source_manifest.json")
CACHE = Path("research/hypotheses_2026_09_12/cache")
OUTPUT = Path("research/parser_followthrough_2026_11_02/clock_triage.json")
V5_SHA256 = "6d6b481095e588f5346aeacea8799a7c6984b9f9b07d583c69a5df6a6d80f646"
EXTERNAL_CONTEXT = {
    "game_id": "0022301177",
    "url": "https://abcnews.com/Sports/error-led-extra-time-clock-lakers-win-grizzles/story?id=109211765",
    "author": "Dave McMenamin", "published": "2024-04-13", "accessed": "2026-11-02",
    "evidence_type": "ESPN original reporting republished by ABC, quoting NBA spokesperson Tim Frank",
    "reported_clock_reset": "third quarter 1:14 to 2:20; unnoticed during game; 66 extra seconds",
    "source_match": "actions 470/471/681 at 1:14, then Davis made basket action 473 at 2:06",
    "limit": "No directly hosted NBA statement located; no independent film validation; no clock normalization authorized",
}


def seconds(action):
    match = re.fullmatch(r"PT(\d+)M(\d+(?:\.\d+)?)S", action["clock"])
    if not match:
        raise ValueError("Invalid source clock")
    return int(match[1]) * 60 + float(match[2])


def classify(previous, current):
    """Describe source category only; none is permission to repair the clock."""
    label = (current["actionType"] or "").lower()
    if label == "memo":
        return "unsupported_memo_timestamp"
    if label in {"instantreplay", "replay"}:
        return "replay_timestamp_requires_sequence_review"
    if label in {"substitution", "timeout", "period"}:
        return "administrative_timestamp_without_explicit_clock_restoration"
    if label == "foul" and current["subType"] == "technical":
        return "technical_foul_timestamp_requires_control_review"
    if label == "violation":
        return "violation_timestamp_requires_control_review"
    if label == "turnover":
        return "turnover_timestamp_requires_control_review"
    return "scoring_timestamp_requires_control_review"


def build():
    report_bytes = REPORT.read_bytes()
    report = json.loads(report_bytes)
    if report["parser_sha256"] != V5_SHA256 or report["source_failures"]:
        raise ValueError("Expected source-verified frozen v5 report")
    targets = {r["game_id"]: r for r in report["games"] if r["status"] == "quarantined"}
    if len(targets) != 84:
        raise ValueError("Frozen cohort is not 84 quarantined games")
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    games, verification, all_memos = [], [], []
    seen = set()
    for source in manifest:
        if source["file"] not in OFFICIAL_ARCHIVES:
            continue
        with verified_snapshot(safe_path(CACHE, source["file"]), source["bytes"],
                               source["sha256"]) as snapshot:
            verification.append({"file": source["file"], "bytes": source["bytes"],
                                 "sha256": source["sha256"], "status": "verified_same_snapshot"})
            for gid, actions, rows, member in archive_games(snapshot):
                def ref(index):
                    return {"csv_row": rows[index], "raw": actions[index]}

                for index, action in enumerate(actions):
                    if action["actionType"] == "memo":
                        all_memos.append({"game_id": gid, "source_file": source["file"],
                                          "source_member": member, "event": ref(index)})
                if gid not in targets:
                    continue
                expected = targets[gid]
                if expected["source_sha256"] != source["sha256"]:
                    raise ValueError("Report source mismatch")
                if len(actions) != expected["source_event_count"]:
                    raise ValueError("Report event count mismatch")
                order = sorted(range(len(actions)), key=lambda i: (
                    int(actions[i]["orderNumber"]), int(actions[i]["actionNumber"])))
                if order != list(range(len(actions))):
                    raise ValueError("CSV order differs from canonical source order")
                rises = []
                for i in range(1, len(actions)):
                    previous, current = actions[i - 1:i + 1]
                    if int(current["period"]) < int(previous["period"]):
                        raise ValueError("Unexpected period reversal")
                    if current["period"] != previous["period"] or seconds(current) <= seconds(previous):
                        continue
                    neighborhood = list(range(max(0, i - 3), min(len(actions), i + 4)))
                    rises.append({"entering_action": current["actionNumber"],
                                  "increase_seconds": round(seconds(current) - seconds(previous), 4),
                                  "classification": classify(previous, current),
                                  "previous": ref(i - 1), "current": ref(i),
                                  "neighborhood": [ref(j) for j in neighborhood],
                                  "repair_authorized": False})
                if not rises or expected["error"] != (
                    "clock/period regression at action " + rises[0]["entering_action"]
                ):
                    raise ValueError("First regression differs from frozen report")
                games.append({"game_id": gid, "source_file": source["file"],
                              "source_sha256": source["sha256"], "source_member": member,
                              "reported_error": expected["error"], "rises": rises,
                              "eligible": False})
                seen.add(gid)
    if seen != set(targets):
        raise ValueError("Missing quarantined game")
    counts = Counter(r["classification"] for g in games for r in g["rises"])
    return {"schema_version": "v5-clock-source-triage-v1", "date": "2026-11-02",
            "scope": "Frozen v5 quarantines, source evidence only; no clock repair or film validation",
            "report_file": REPORT.as_posix(),
            "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
            "baseline_parser_sha256": V5_SHA256,
            "manifest_file": MANIFEST.as_posix(),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "source_verification": verification, "quarantined_games": len(games),
            "clock_rises": sum(counts.values()), "classifications": dict(sorted(counts.items())),
            "games": games, "all_archive_memos": all_memos,
            "external_context": [EXTERNAL_CONTEXT],
            "limits": ["No replay label alone proves a clock correction",
                       "Original clocks and source order retained; no event synthesized",
                       "Passing reproduction is implementation evidence, not scientific validation"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.check:
        if OUTPUT.read_text() != payload:
            raise ValueError("Evidence differs from fresh verified reproduction")
    else:
        with OUTPUT.open("x") as stream:
            stream.write(payload)
    print(json.dumps({"ok": True, "games": result["quarantined_games"],
                      "rises": result["clock_rises"], "classifications": result["classifications"]}))


if __name__ == "__main__":
    main()
