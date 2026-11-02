"""Independent ESPN schedule acquisition and conservative archive cross-check.

Raw HTTP response bodies are retained, gzip-compressed without modification.
This module never treats archive-derived game identifiers as independent evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import parse_qsl, urlsplit

from whistle_research.sources import canonical_game_id

import requests

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
VERSION = "espn-schedule-crosscheck-v1"
TEAM_NAMES = {'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers', 'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns', 'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'}
COHORTS = [(year, 2) for year in range(2021, 2026)] + [(2025, 3)]
ALIASES = {"GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def acquire(output: Path) -> list[dict]:
    """Acquire 181 bounded responses with at most two concurrent requests."""
    output.mkdir(parents=True, exist_ok=False)

    def fetch(spec):
        name, url, query = spec
        row = {"file": name + ".json.gz", "url": url, "query": query,
               "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            with requests.get(url, params=query, timeout=(15, 90), stream=True) as response:
                row.update(http_status=response.status_code, response_url=response.url)
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > 8 * 1024 * 1024:
                        raise ValueError("response exceeds 8 MiB")
                raw = bytes(body)
            row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            with (output / row["file"]).open("xb") as stream:
                stream.write(gzip.compress(raw, mtime=0))
            row["status"] = "acquired"
        except (requests.RequestException, ValueError) as exc:
            row.update(status="failed", reason=str(exc))
        return row

    teams = fetch(("teams", BASE + "/teams", {"limit": 100}))
    rows = [teams]
    write_json(output / "teams_manifest.json", teams)
    if teams["status"] != "acquired":
        write_json(output / "manifest.json", rows)
        return rows
    data = json.loads(gzip.decompress((output / teams["file"]).read_bytes()))
    ids = [t["team"]["id"] for t in data["sports"][0]["leagues"][0]["teams"]]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise ValueError("expected 30 unique NBA teams")
    specs = [(f"schedule_{year}_{kind}_{team}", f"{BASE}/teams/{team}/schedule",
              {"season": year, "seasontype": kind})
             for year, kind in COHORTS for team in sorted(ids, key=int)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(fetch, specs):
            rows.append(row)
    write_json(output / "manifest.json", rows)
    return rows


def normalize(event: dict, year: int, kind: int) -> dict:
    if event["season"]["year"] != year or event["seasonType"]["type"] != kind:
        raise ValueError("event season/type mismatch")
    competitions = event["competitions"]
    if len(competitions) != 1:
        raise ValueError("expected one competition")
    comp = competitions[0]
    teams = {}
    for competitor in comp["competitors"]:
        code = competitor["team"]["abbreviation"]
        side = competitor["homeAway"]
        if side in teams or side not in {"home", "away"}:
            raise ValueError("invalid home/away teams")
        teams[side] = ALIASES.get(code, code)
    if set(teams) != {"home", "away"} or teams["home"] == teams["away"]:
        raise ValueError("missing/distinct home/away teams required")
    timestamp = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("event date needs timezone")
    status = comp["status"]["type"]
    notes = [n.get("headline", "") for n in comp.get("notes", [])]
    cup = any(n in {"NBA Cup Championship", "NBA In-Season Tournament Championship"} for n in notes)
    final = status.get("completed") is True and status.get("name") == "STATUS_FINAL"
    disposition = "excluded_cup_championship" if cup else "completed" if final else "not_completed"
    return {"espn_event_id": event["id"], "season": f"{year-1}-{str(year)[-2:]}",
            "game_type": "regular_season" if kind == 2 else "playoffs",
            "date": timestamp.astimezone(ZoneInfo("America/New_York")).date().isoformat(),
            **teams, "disposition": disposition, "source_status": status,
            "notes": notes}


def match_key(row):
    return tuple(row[k] for k in ("season", "game_type", "date", "home", "away"))


def validate_corrections(path: Path | None, raw_root: Path) -> dict:
    """Require preserved primary NBA title evidence for every date amendment."""
    if path is None:
        return {}
    rows = json.loads(path.read_text())["corrections"]
    result = {}
    for row in rows:
        game_id = row["game_id"]
        if (row["home_name"], row["away_name"]) != (TEAM_NAMES[row["home"]], TEAM_NAMES[row["away"]]):
            raise ValueError("correction team names mismatch")
        if row["historical_date"] == row["date"]:
            raise ValueError("date correction must amend date")
        source = row["source_file"]
        if Path(source).name != source:
            raise ValueError("unsafe correction source path")
        body = (raw_root / source).read_bytes()
        if hashlib.sha256(body).hexdigest() != row["source_sha256"]:
            raise ValueError("correction source hash mismatch")
        expected = row["source_title"] + " (" + row["url"] + ")"
        if expected not in body.decode().splitlines():
            raise ValueError("correction title absent from preserved primary evidence")
        if not re.fullmatch(r"https://www\.nba\.com/game/" + row["away"].lower() + "-vs-" + row["home"].lower() + "-" + game_id + r"(?:/box-score)?", row["url"]):
            raise ValueError("correction NBA ID/team URL mismatch")
        match = re.fullmatch(re.escape(row["away_name"]) + r" vs " + re.escape(row["home_name"]) + r" ([A-Z][a-z]{2} \d{1,2}, \d{4}) (?:Game Summary|Box Scores) \| NBA\.com", row["source_title"])
        if match is None or datetime.strptime(match[1], "%b %d, %Y").date().isoformat() != row["date"]:
            raise ValueError("correction date inconsistent with NBA title")
        if game_id in result:
            raise ValueError("duplicate correction game")
        result[game_id] = row
    return result


def compare(raw_root: Path, metadata: Path, correction_path: Path | None = None) -> dict:
    corrections = validate_corrections(correction_path, raw_root)
    used_corrections = set()
    manifest_path = raw_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    errors, events, occurrences, requests_seen = [], {}, defaultdict(set), Counter()
    teams = None
    for source in manifest:
        try:
            if source["status"] != "acquired" or type(source.get("http_status")) is not int or source["http_status"] != 200:
                raise ValueError("request requires acquired HTTP 200")
            query = source["query"]
            if source["file"] == "teams.json.gz":
                if source["url"] != BASE + "/teams" or query != {"limit": 100}:
                    raise ValueError("unapproved ESPN teams request")
            elif (not re.fullmatch(re.escape(BASE) + r"/teams/[0-9]+/schedule", source["url"])
                  or set(query) != {"season", "seasontype"}
                  or any(type(value) is not int for value in query.values())
                  or (query["season"], query["seasontype"]) not in COHORTS):
                raise ValueError("unapproved ESPN schedule request")
            response_url = urlsplit(source["response_url"])
            if (response_url._replace(query="").geturl() != source["url"]
                    or sorted(parse_qsl(response_url.query, strict_parsing=True)) != sorted((key, str(value)) for key, value in query.items())):
                raise ValueError("response URL differs from approved ESPN request; redirects rejected")
            raw = gzip.decompress((raw_root / source["file"]).read_bytes())
            if len(raw) != source["bytes"] or hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError("raw response hash mismatch")
            data = json.loads(raw)
            if source["file"] == "teams.json.gz":
                teams = {str(t["team"]["id"]) for t in data["sports"][0]["leagues"][0]["teams"]}
                if len(teams) != 30:
                    raise ValueError("expected 30 teams")
                continue
            year, kind = source["query"]["season"], source["query"]["seasontype"]
            if (year, kind) not in COHORTS:
                raise ValueError("undeclared schedule cohort")
            team = str(data["team"]["id"])
            code = data["team"]["abbreviation"]
            code = ALIASES.get(code, code)
            if source["url"] != f"{BASE}/teams/{team}/schedule":
                raise ValueError("requested/returned team mismatch")
            requests_seen[(year, kind, team)] += 1
            if "requestedSeason" in data and (data["requestedSeason"]["year"], data["requestedSeason"]["type"]) != (year, kind):
                raise ValueError("requestedSeason mismatch")
            # Unknown pagination controls fail closed instead of silently truncating.
            if any(data.get(key) for key in ("next", "nextPage", "pagination")):
                raise ValueError("unresolved pagination")
            local_ids = set()
            for event in data["events"]:
                row = normalize(event, year, kind)
                eid = row["espn_event_id"]
                if code not in (row["home"], row["away"]):
                    raise ValueError("response contains unrelated team event")
                if eid in local_ids:
                    raise ValueError("duplicate event within team response")
                local_ids.add(eid)
                if eid in events and events[eid] != row:
                    raise ValueError(f"conflicting duplicate event {eid}")
                events[eid] = row
                occurrences[eid].add(team)
        except (KeyError, ValueError, TypeError, OSError) as exc:
            errors.append({"source": source.get("file"), "reason": str(exc)})
    if teams is None:
        errors.append({"reason": "missing verified team frame"})
        teams = set()
    for year, kind in COHORTS:
        for team in teams:
            if requests_seen[(year, kind, team)] != 1:
                errors.append({"year": year, "type": kind, "team": team, "reason": "missing/duplicate team request"})
    for eid, row in events.items():
        if len(occurrences[eid]) != 2:
            errors.append({"espn_event_id": eid, "reason": "event not corroborated by two team responses"})
    completed = [r for r in events.values() if r["disposition"] == "completed"]
    counts = Counter((r["season"], r["game_type"], team) for r in completed for team in (r["home"], r["away"]))
    for year, kind in COHORTS:
        if kind != 2:
            continue
        season = f"{year-1}-{str(year)[-2:]}"
        observed = [count for (s, k, _), count in counts.items() if (s, k) == (season, "regular_season")]
        expected = 72 if year == 2021 else 82
        if len(observed) != 30 or any(n != expected for n in observed):
            errors.append({"season": season, "reason": "incomplete/unexpected regular-season team totals", "counts": observed})
    playoff_series = Counter(tuple(sorted((r["home"], r["away"]))) for r in completed if r["game_type"] == "playoffs")
    if len(playoff_series) != 15 or any(not 4 <= n <= 7 for n in playoff_series.values()):
        errors.append({"reason": "incomplete/unexpected playoff series frame"})
    historical = []
    historical_ids = set()
    metadata_sources = []
    for year, kind in COHORTS:
        name = f"cdnnba_{'po_' if kind == 3 else ''}{year-1}_games.csv"
        path = metadata / name
        raw = path.read_bytes()
        metadata_sources.append({"file": name, "sha256": hashlib.sha256(raw).hexdigest()})
        with path.open(newline="") as stream:
            for row in csv.DictReader(stream):
                game_id = canonical_game_id(row["game_id"])
                if game_id != row["game_id"]:
                    raise ValueError("metadata game ID must use canonical ten-digit format")
                if game_id in historical_ids:
                    raise ValueError(f"duplicate metadata NBA game ID: {game_id}")
                historical_ids.add(game_id)
                correction = corrections.get(row["game_id"])
                historical_date = row["date"]
                if correction:
                    if (correction["historical_date"], correction["home"], correction["away"]) != (row["date"], row["home"], row["away"]):
                        raise ValueError("correction historical identity mismatch")
                    row["date"] = correction["date"]
                    used_corrections.add(row["game_id"])
                historical.append({"historical_date": historical_date, "date_correction": correction, "game_id": row["game_id"], "season": f"{year-1}-{str(year)[-2:]}", "game_type": "regular_season" if kind == 2 else "playoffs", "date": row["date"], "home": row["home"], "away": row["away"]})
    if used_corrections != set(corrections):
        raise ValueError("unused date correction")
    left, right = defaultdict(list), defaultdict(list)
    for row in completed:
        left[match_key(row)].append(row)
    for row in historical:
        right[match_key(row)].append(row)
    matched, unmatched_espn, unmatched_archive = [], [], []
    for key in sorted(left.keys() | right.keys()):
        if len(left[key]) == len(right[key]) == 1:
            matched.append({**right[key][0], "espn_event_id": left[key][0]["espn_event_id"]})
        else:
            unmatched_espn.extend(left[key])
            unmatched_archive.extend(right[key])
    ok = not errors and not unmatched_espn and not unmatched_archive and bool(matched)
    return {"schema_version": VERSION, "status": "exact_independent_crosscheck" if ok else "unverified",
            "raw_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "metadata_sources": metadata_sources, "errors": errors,
            "date_corrections": list(corrections.values()),
            "request_count": len(requests_seen), "completed_count": len(completed),
            "response_manifest": manifest,
            "matched_count": len(matched), "unmatched_espn": unmatched_espn,
            "unmatched_archive": unmatched_archive, "noncompleted_or_excluded": [r for r in events.values() if r["disposition"] != "completed"],
            "cohort_counts": [{"season": s, "game_type": k, "completed": sum(r["season"] == s and r["game_type"] == k for r in completed), "matched": sum(r["season"] == s and r["game_type"] == k for r in matched)} for s, k in sorted({(r["season"], r["game_type"]) for r in historical})],
            "playoff_series": [{"teams": list(pair), "completed_games": n} for pair, n in sorted(playoff_series.items())],
            "team_completed_counts": [{"season": s, "game_type": k, "team": t, "count": n} for (s, k, t), n in sorted(counts.items())],
            "games": matched}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--corrections", type=Path)
    args = parser.parse_args()
    if args.acquire:
        acquire(args.raw)
    report = compare(args.raw, args.metadata, args.corrections)
    write_json(args.report, report)
    if args.schedule and report["status"] == "exact_independent_crosscheck":
        write_json(args.schedule, {"provenance": "Independent ESPN team schedules; all 30 team responses in each of six cohorts verified against preserved raw response SHA256s, duplicate events corroborated by both teams, exact regular-season per-team totals after explicit Cup championship exclusions. Thirty historical dates are explicitly amended through preserved official NBA game-page title/ID/team evidence; original dates and correction-source hashes retained. NBA game IDs are mapped through unique season/type/America-New_York-date/home/away joins to historical metadata; independent ESPN IDs retained. This is a schedule cross-check, not independent possession validation or proof beyond the endpoint's coverage. Report manifest SHA256: " + report["raw_manifest_sha256"], "games": report["games"]})
    print(json.dumps({k: report[k] for k in ("status", "request_count", "completed_count", "matched_count", "cohort_counts")}))
    return 0 if report["status"] == "exact_independent_crosscheck" else 1


if __name__ == "__main__":
    raise SystemExit(main())
