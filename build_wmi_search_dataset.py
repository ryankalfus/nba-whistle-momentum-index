from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from build_wmi_distribution_2020_2026 import build_mobile_wmi_table
from build_wmi_distribution_2020_2026 import retry_call
from wmi_utils import calculate_wmi


SEASON_START_YEARS = range(2019, 2025)
PRECOMPUTED_REGULAR_WMI_PATH = Path("wmi_games_2020_21_to_2025_26.csv")
OUT_PATH = Path("wmi_search_games_2019_2026.csv")
FAILURES_OUT_PATH = Path("wmi_search_games_2019_2026_failures.csv")
SUMMARY_OUT_PATH = Path("wmi_search_games_2019_2026_summary.csv")
MAX_WORKERS = 8
CHECKPOINT_EVERY = 100
GAME_TYPES = {
    "002": "Regular Season",
    "004": "Playoffs",
    "005": "Play-In",
}


def season_label(start_year):
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def schedule_url(start_year):
    return (
        "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/"
        f"{start_year}/league/00_full_schedule.json"
    )


def fetch_schedule(start_year):
    def _request():
        response = requests.get(
            schedule_url(start_year),
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    return retry_call(_request, tries=4)


def schedule_games(start_year):
    season = season_label(start_year)
    payload = fetch_schedule(start_year)
    rows = []
    for month in payload.get("lscd", []):
        for game in month.get("mscd", {}).get("g", []):
            game_id = str(game.get("gid", ""))
            game_type = GAME_TYPES.get(game_id[:3])
            if game_type is None or game.get("stt") != "Final":
                continue
            away_team = game.get("v", {}).get("ta")
            home_team = game.get("h", {}).get("ta")
            matchup = f"{away_team} @ {home_team}" if away_team and home_team else None
            rows.append(
                {
                    "season": season,
                    "season_start_year": start_year,
                    "season_type": game_type,
                    "game_id": game_id,
                    "game_date_et": game.get("gdte"),
                    "away_team": away_team,
                    "home_team": home_team,
                    "matchup": matchup,
                    "away_score": game.get("v", {}).get("s"),
                    "home_score": game.get("h", {}).get("s"),
                    "series": game.get("seri"),
                }
            )
    return rows


def build_row(game):
    try:
        table_df, meta = build_mobile_wmi_table(game["season"], game["game_id"])
        result = calculate_wmi(table_df)
        row = {
            **game,
            "possessions": int(len(table_df)),
            "n1_count_L_t_eq_1": result["n1_count_L_t_eq_1"],
            "n0_count_L_t_eq_0": result["n0_count_L_t_eq_0"],
            "mean_M_t_where_L_t_eq_1": result["mean_M_t_where_L_t_eq_1"],
            "mean_M_t_where_L_t_eq_0": result["mean_M_t_where_L_t_eq_0"],
            "WMI": result["WMI"],
            "source": "data.nba.com mobile_teams v2015 play-by-play",
        }
        if not row["game_date_et"]:
            row["game_date_et"] = meta.get("game_date_et")
        return row, None
    except Exception as error:
        return None, {**game, "error_message": str(error)}


def load_precomputed_regular_rows():
    if not PRECOMPUTED_REGULAR_WMI_PATH.exists():
        return []
    df = pd.read_csv(PRECOMPUTED_REGULAR_WMI_PATH, dtype={"game_id": str})
    df["game_id"] = df["game_id"].str.zfill(10)
    df["season_start_year"] = df["season"].str.slice(0, 4).astype(int)
    df["season_type"] = "Regular Season"
    df["away_score"] = pd.NA
    df["home_score"] = pd.NA
    df["series"] = pd.NA
    df["source"] = df["source"].fillna(f"local {PRECOMPUTED_REGULAR_WMI_PATH.name}")
    keep = [
        "season",
        "season_start_year",
        "season_type",
        "game_id",
        "game_date_et",
        "away_team",
        "home_team",
        "matchup",
        "away_score",
        "home_score",
        "series",
        "possessions",
        "n1_count_L_t_eq_1",
        "n0_count_L_t_eq_0",
        "mean_M_t_where_L_t_eq_1",
        "mean_M_t_where_L_t_eq_0",
        "WMI",
        "source",
    ]
    return df[keep].to_dict("records")


def add_percentiles(df):
    out = df.copy()
    values = pd.to_numeric(out["WMI"], errors="coerce")
    finite = values.notna() & np.isfinite(values)
    out["wmi_percentile"] = np.nan
    if finite.sum() == 1:
        out.loc[finite, "wmi_percentile"] = 50.0
    elif finite.sum() > 1:
        out.loc[finite, "wmi_percentile"] = values[finite].rank(method="average", pct=True) * 100.0
    return out


def save_outputs(rows, failures):
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["game_date_et", "game_id"]).reset_index(drop=True)
        df = add_percentiles(df)
    df.to_csv(OUT_PATH, index=False)
    pd.DataFrame(failures).to_csv(FAILURES_OUT_PATH, index=False)

    values = pd.to_numeric(df.get("WMI", pd.Series(dtype=float)), errors="coerce").dropna()
    summary = pd.DataFrame(
        [
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "seasons": "2019-20 through available 2025-26 snapshot",
                "games": int(len(df)),
                "games_with_wmi": int(len(values)),
                "regular_season_games": int((df.get("season_type") == "Regular Season").sum()) if not df.empty else 0,
                "playoff_games": int((df.get("season_type") == "Playoffs").sum()) if not df.empty else 0,
                "play_in_games": int((df.get("season_type") == "Play-In").sum()) if not df.empty else 0,
                "mean_wmi": float(values.mean()) if not values.empty else None,
                "median_wmi": float(values.median()) if not values.empty else None,
                "failures": int(len(failures)),
            }
        ]
    )
    summary.to_csv(SUMMARY_OUT_PATH, index=False)
    return df, summary


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--max-games", type=int, default=None, help="Optional smoke-test cap.")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    return parser.parse_args()


def main():
    args = parse_args()
    precomputed_rows = load_precomputed_regular_rows()
    precomputed_game_ids = {row["game_id"] for row in precomputed_rows}
    games = []
    for start_year in SEASON_START_YEARS:
        season_games = schedule_games(start_year)
        print(f"schedule {season_label(start_year)} games={len(season_games)}", flush=True)
        games.extend(game for game in season_games if game["game_id"] not in precomputed_game_ids)
    if args.max_games is not None:
        games = games[: args.max_games]
    print(f"precomputed_regular_games={len(precomputed_rows)} games_to_compute={len(games)}", flush=True)

    rows = []
    failures = []
    total = len(games)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_game = {executor.submit(build_row, game): game for game in games}
        for done, future in enumerate(as_completed(future_to_game), start=1):
            row, failure = future.result()
            if row is not None:
                rows.append(row)
            if failure is not None:
                failures.append(failure)
            if done % CHECKPOINT_EVERY == 0 or done == total:
                save_outputs(precomputed_rows + rows, failures)
                print(f"progress {done}/{total} ok={len(rows)} failures={len(failures)}", flush=True)

    df, summary = save_outputs(precomputed_rows + rows, failures)
    print("saved", OUT_PATH, len(df))
    print("saved", FAILURES_OUT_PATH, len(failures))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
