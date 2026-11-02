"""Compare immutable v5/v6 provenance and inspect raw flagged source windows.

No reconstruction, model fitting, eligibility change or current-parser binding.
"""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path

from whistle_research.reconcile import archive_games, verified_snapshot
from whistle_research.sources import OFFICIAL_ARCHIVES, safe_path


ROOT = Path("research/hypotheses_2026_09_12")
OUT = Path("research/parser_followthrough_2026_11_02/residual_triage.json")
VERSIONS = {
    "v5": ("output/v2/reconciliation-semantics-v5-2026-11-02/report.json",
           "output/v2/features-candidate-v5-2026-11-02"),
    "v6": ("output/v2/reconciliation-v6-reviewed-2026-11-02/report.json",
           "output/v2/features-v6-reviewed-2026-11-02"),
}
ADMIN = {"substitution", "timeout", "instantreplay", "replay", "game", "period",
         "stoppage", "block", "ejection", "memo"}
FOULS = {"personal", "shooting", "loose ball", "offensive", "technical", "double technical",
         "double personal", "flagrant1", "flagrant2", "clear path", "away from play",
         "transition take", "take"}


def controls(action):
    if action["actionType"] in ADMIN:
        return False
    if action["actionType"] == "foul" and action["subType"] in {"technical", "double technical"}:
        return False
    return True


def trace_provenance(report_path, directory):
    report_bytes = Path(report_path).read_bytes()
    report = json.loads(report_bytes)
    directory = Path(directory)
    manifest_bytes = (directory / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["parser_sha256"] != report["parser_sha256"]:
        raise ValueError("Feature and reconciliation parser mismatch")
    pending, traces, special = None, [], []
    digest = hashlib.sha256()
    count = 0
    with (directory / manifest["row_provenance_file"]).open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            row = json.loads(raw)
            count += 1
            if pending is not None:
                if row["game_id"] != pending["game_id"]:
                    raise ValueError("Transfer flag has no next possession in game")
                traces.append({"game_id": row["game_id"],
                               "entering_action": row["event_action_numbers"][0],
                               "previous_group": pending, "next_group": row})
            pending = row if "unexplained_control_transfer" in row["audit_flags"] else None
            if any(flag in row["audit_flags"] for flag in ("unsupported_label", "unsupported_free_throw")):
                special.append(row)
    if pending is not None or digest.hexdigest() != manifest["row_provenance_sha256"]:
        raise ValueError("Incomplete/unverified provenance")
    if count != manifest["row_count"] or len(traces) != report["issue_counts"]["unexplained_control_transfer"]:
        raise ValueError("Derived provenance count mismatch")
    binding = {"report_file": report_path, "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
               "manifest_file": (directory / "manifest.json").as_posix(),
               "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
               "provenance_sha256": digest.hexdigest(), "parser_sha256": report["parser_sha256"],
               "provenance_rows": count, "transfer_flags": len(traces)}
    return traces, special, binding, report


def category(previous, current, group_controls):
    jump = next((a for a in reversed(group_controls) if a["actionType"] == "jumpball"
                 and a["subType"] == "recovered"), None)
    if jump is not None:
        if previous["actionType"] == "jumpball":
            if current["actionType"] == "turnover":
                return "recovered_jump_then_unpaired_turnover"
            return "recovered_jump_then_source_owner_reversion"
        if previous["actionType"] == "turnover":
            return "jump_loss_companion_then_source_owner_reversion"
        return "jump_within_previous_group_other_transfer"
    if previous["actionType"] == "freethrow":
        return "free_throw_then_unexplained_transfer"
    if previous["actionType"] == "foul":
        return "foul_then_unexplained_transfer"
    if previous["actionType"] == "violation":
        return "violation_then_unexplained_transfer"
    if previous["actionType"] == "rebound":
        return "rebound_then_unexplained_transfer"
    return "other_unexplained_transfer"


def add_assessment(result):
    added = [t for t in result["transfer_traces"] if t["comparison"] == "added_in_v6"]
    triples = []
    for trace in added:
        if trace["category"] != "recovered_jump_then_unpaired_turnover":
            continue
        jump, turnover = trace["last_control_in_flagged_group"]["raw"], trace["current"]["raw"]
        rows = trace["neighborhood"]
        index = next(i for i, r in enumerate(rows) if r["raw"]["actionNumber"] == turnover["actionNumber"])
        following = rows[index + 1]["raw"] if index + 1 < len(rows) else {}
        if (jump["clock"] == turnover["clock"] == following.get("clock")
                and following.get("actionType") == "steal"
                and following.get("teamId") == jump["teamId"]
                and following.get("personId") == jump.get("jumpBallWonPersonId")):
            triples.append({"game_id": trace["game_id"], "jump_action": jump["actionNumber"],
                            "turnover_action": turnover["actionNumber"], "steal_action": following["actionNumber"],
                            "jump_descriptor": jump["descriptor"], "turnover_subtype": turnover["subType"]})
    retained = [t for t in added if t["category"] == "free_throw_then_unexplained_transfer"]
    result["assessment"] = {
        "same_clock_jump_turnover_winning_jumper_steal": triples,
        "same_clock_triple_count": len(triples),
        "triple_is_independent_control_validation": False,
        "triple_limit": "Mutually consistent statistical records do not exclude intervening gain or source-order error; mismatched loser identity remains unresolved",
        "all_39_free_throw_cases_have_retained_audit": len(retained) == 39 and all(
            "retained_ball_requires_audit" in t["previous_group"]["audit_flags"] for t in retained),
        "all_39_last_control_free_throws_flagrant": len(retained) == 39 and all(
            t["last_control_in_flagged_group"]["raw"].get("descriptor") == "flagrant" for t in retained),
        "safe_additional_parser_fix_demonstrated": False,
    }
    path = Path("output/v2/reconciliation-v7-reviewed-2026-11-02/report.json")
    raw = path.read_bytes()
    followup = json.loads(raw)
    result["followup_v7_reconciliation"] = {
        "file": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
        "parser_sha256": followup["parser_sha256"],
        "reconstructed": sum(g["status"] != "quarantined" for g in followup["games"]),
        "quarantined": sum(g["status"] == "quarantined" for g in followup["games"]),
        "issues": followup["issue_counts"],
        "limit": "Followup aggregate only; transfer source-pattern denominators in this packet remain frozen v6",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    versioned, special_groups, bindings, reports = {}, {}, {}, {}
    for version, (report, features) in VERSIONS.items():
        versioned[version], special_groups[version], bindings[version], reports[version] = trace_provenance(report, features)
    previous = {(t["game_id"], t["entering_action"]) for t in versioned["v5"]}
    current = {(t["game_id"], t["entering_action"]) for t in versioned["v6"]}
    for trace in versioned["v6"]:
        trace["comparison"] = "persistent" if (trace["game_id"], trace["entering_action"]) in previous else "added_in_v6"
    targets = {}
    for trace in versioned["v6"]:
        targets.setdefault(trace["game_id"], []).append(trace)
    special_games = {r["game_id"] for r in reports["v6"]["games"]
                     if any(flag in r.get("issues", {}) for flag in ("unsupported_label", "unsupported_free_throw"))}
    verification, details, unsupported = [], [], []
    manifest_bytes = (ROOT / "source_manifest.json").read_bytes()
    for source in json.loads(manifest_bytes):
        if source["file"] not in OFFICIAL_ARCHIVES:
            continue
        with verified_snapshot(safe_path(ROOT / "cache", source["file"]), source["bytes"], source["sha256"]) as snapshot:
            verification.append({"file": source["file"], "bytes": source["bytes"], "sha256": source["sha256"]})
            for gid, actions, rows, member in archive_games(snapshot):
                if gid not in targets and gid not in special_games:
                    continue
                index = {int(a["actionNumber"]): i for i, a in enumerate(actions)}
                def ref(i):
                    return {"csv_row": rows[i], "raw": actions[i]}
                def neighborhood(i):
                    return [ref(j) for j in range(max(0, i - 4), min(len(actions), i + 5))]
                for trace in targets.get(gid, []):
                    i = index[trace["entering_action"]]
                    controls_in_group = [actions[index[n]] for n in trace["previous_group"]["event_action_numbers"]
                                         if controls(actions[index[n]])]
                    if not controls_in_group:
                        raise ValueError("Flagged possession has no nonadministrative event")
                    prev = controls_in_group[-1]
                    row = {**trace, "source_file": source["file"], "source_sha256": source["sha256"],
                           "source_member": member, "current": ref(i),
                           "last_control_in_flagged_group": ref(index[int(prev["actionNumber"])]),
                           "previous_group_raw": [ref(index[n]) for n in trace["previous_group"]["event_action_numbers"]],
                           "neighborhood": neighborhood(i),
                           "category": category(prev, actions[i], controls_in_group), "eligible": False}
                    details.append(row)
                if gid in special_games:
                    flagged_numbers = {int(a["actionNumber"]) for a in actions}
                    for n in sorted(flagged_numbers):
                        a = actions[index[n]]
                        invalid_ft = a["actionType"] == "freethrow" and a["subType"] not in {
                            "1 of 1", "1 of 2", "2 of 2", "1 of 3", "2 of 3", "3 of 3"}
                        invalid_label = (
                            (a["actionType"] == "foul" and a["subType"] not in FOULS)
                            or a["actionType"] not in ADMIN | {
                                "foul", "freethrow", "2pt", "3pt", "rebound", "turnover", "steal", "jumpball", "violation"}
                        )
                        if invalid_ft or invalid_label:
                            unsupported.append({"game_id": gid, "source_file": source["file"],
                                                "source_sha256": source["sha256"], "source_member": member,
                                                "kind": "unsupported_free_throw" if invalid_ft else "unsupported_label",
                                                "event": ref(index[n]), "neighborhood": neighborhood(index[n])})
    if len(details) != 410:
        raise ValueError("Incomplete transfer trace inventory")
    counts = Counter(x["kind"] for x in unsupported)
    if counts != {"unsupported_free_throw": 3, "unsupported_label": 1}:
        raise ValueError(f"Unsupported label extraction incomplete: {counts}")
    categories = {comparison: dict(sorted(Counter(t["category"] for t in details if t["comparison"] == comparison).items()))
                  for comparison in ("added_in_v6", "persistent")}
    report_deltas = {key: reports["v6"]["issue_counts"].get(key, 0) - reports["v5"]["issue_counts"].get(key, 0)
                     for key in sorted(set(reports["v5"]["issue_counts"]) | set(reports["v6"]["issue_counts"]))}
    result = {"schema_version": "v5-v6-residual-source-triage-v1", "date": "2026-11-02",
              "bindings": bindings, "source_verification": verification,
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "summary": {"v5_transfers": len(previous), "v6_transfers": len(current),
                          "added_transfer_actions": len(current - previous), "removed_transfer_actions": len(previous - current),
                          "persistent_transfer_actions": len(previous & current), "category_counts": categories,
                          "unsupported_counts": dict(counts)}, "report_issue_deltas": report_deltas,
              "removed_v5_transfer_actions": [{"game_id": gid, "entering_action": action} for gid, action in sorted(previous - current)],
              "transfer_traces": details, "unsupported_records": unsupported,
              "limitations": ["Source-pattern categories do not adjudicate actual control or officiating",
                              "Transfer trigger recovered from hash-verified adjacent possession provenance; no current parser executed",
                              "Counts compare event identities, not merely per-game net differences"]}
    add_assessment(result)
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.check:
        if OUT.read_text() != payload:
            raise ValueError("Packet differs from fresh reproduction")
    else:
        with OUT.open("x") as stream:
            stream.write(payload)
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
