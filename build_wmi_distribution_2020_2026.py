import time
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

from wmi_utils import build_possession_model_table_from_actions
from wmi_utils import calculate_wmi


SEASON_CONFIGS = [
    {"season": "2020-21", "prefix": "00220", "regular_season_games": 1080},
    {"season": "2021-22", "prefix": "00221", "regular_season_games": 1230},
    {"season": "2022-23", "prefix": "00222", "regular_season_games": 1230},
    {"season": "2023-24", "prefix": "00223", "regular_season_games": 1230},
    {"season": "2024-25", "prefix": "00224", "regular_season_games": 1230},
]
MAX_WORKERS = 4
DATE_STAMP = "2020_21_to_2025_26"
WMI_OUT_PATH = Path(f"wmi_games_{DATE_STAMP}.csv")
SUMMARY_OUT_PATH = Path(f"wmi_distribution_{DATE_STAMP}_summary.csv")
FAILURES_OUT_PATH = Path(f"wmi_distribution_{DATE_STAMP}_failures.csv")
WMI_PLOT_OUT_PATH = Path(f"wmi_distribution_{DATE_STAMP}.png")
LOCAL_2025_WMI_PATH = Path("wmi_games_2025_26_asof_2026_03_23.csv")
CHECKPOINT_EVERY = 50


def game_id(prefix, number):
    return f"{prefix}{number:05d}"


def retry_call(fn, tries=4):
    last_error = None
    for i in range(tries):
        try:
            return fn()
        except Exception as error:
            last_error = error
            time.sleep(0.6 * (i + 1))
    raise last_error


def mobile_pbp_url(season_start_year, gid):
    return (
        "https://data.nba.com/data/v2015/json/mobile_teams/nba/"
        f"{season_start_year}/scores/pbp/{gid}_full_pbp.json"
    )


def clock_to_iso(clock_value):
    minutes, seconds = str(clock_value).split(":")
    seconds_float = float(seconds)
    whole_seconds = int(seconds_float)
    hundredths = int(round((seconds_float - whole_seconds) * 100))
    return f"PT{int(minutes)}M{whole_seconds}.{hundredths:02d}S"


def mobile_action_type(etype):
    return {
        1: "made shot",
        2: "missed shot",
        3: "free throw",
        4: "rebound",
        5: "turnover",
        6: "foul",
        8: "substitution",
        9: "timeout",
        10: "jump ball",
        12: "period",
        13: "instant replay",
    }.get(int(etype), "unknown")


def mobile_subtype(play):
    description = str(play.get("de") or "").lower()
    action_type = mobile_action_type(play.get("etype", 0))
    if action_type == "foul":
        if "double technical" in description:
            return "double technical"
        if "technical" in description:
            return "technical"
        if "offensive" in description or "off.foul" in description:
            return "offensive"
        if "shooting" in description or "s.foul" in description:
            return "shooting"
        return "personal"
    return str(play.get("mtype") or "")


def parse_tricodes_from_gcode(gcode):
    matchup = str(gcode).split("/")[-1]
    if len(matchup) >= 6:
        return matchup[:3], matchup[3:6]
    return None, None


def infer_team_id_to_tricode(plays, away_team, home_team):
    mapping = {}
    for play in plays:
        tid = int(play.get("tid") or 0)
        description = str(play.get("de") or "")
        if tid == 0:
            continue
        if away_team and f"[{away_team}]" in description:
            mapping[tid] = away_team
        elif home_team and f"[{home_team}]" in description:
            mapping[tid] = home_team
    return mapping


def fetch_mobile_payload(season, gid):
    season_start_year = season.split("-")[0]
    response = requests.get(
        mobile_pbp_url(season_start_year, gid),
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    periods = payload.get("g", {}).get("pd", [])
    plays = [play for period in periods for play in period.get("pla", [])]
    if not plays:
        raise ValueError(f"No mobile play-by-play rows found for game_id {gid}.")
    return payload, plays


def build_mobile_wmi_table(season, gid):
    payload, plays = retry_call(lambda: fetch_mobile_payload(season, gid), tries=2)
    game = payload["g"]
    away_team, home_team = parse_tricodes_from_gcode(game.get("gcode"))
    team_id_to_tricode = infer_team_id_to_tricode(plays, away_team, home_team)

    actions = []
    for period in game.get("pd", []):
        period_number = int(period.get("p"))
        for play in period.get("pla", []):
            team_id = int(play.get("tid") or 0)
            possession = int(play.get("oftid") or 0)
            team_tricode = team_id_to_tricode.get(team_id)
            actions.append(
                {
                    "actionNumber": int(play.get("evt")),
                    "orderNumber": int(play.get("ord")),
                    "clock": clock_to_iso(play.get("cl")),
                    "period": period_number,
                    "teamId": team_id if team_id else np.nan,
                    "teamTricode": team_tricode if team_tricode else np.nan,
                    "scoreHome": play.get("hs"),
                    "scoreAway": play.get("vs"),
                    "description": play.get("de"),
                    "actionType": mobile_action_type(play.get("etype", 0)),
                    "subType": mobile_subtype(play),
                    "possession": possession if possession else np.nan,
                }
            )

    table_df = build_possession_model_table_from_actions(actions=actions, game_id=gid)
    meta = {
        "game_date_et": str(game.get("gcode", "")).split("/")[0] or None,
        "away_team": away_team,
        "home_team": home_team,
    }
    return table_df, meta


def build_game_row(season, gid):
    try:
        table_df, meta = build_mobile_wmi_table(season, gid)
        wmi_result = calculate_wmi(table_df)

        away_team = meta.get("away_team")
        home_team = meta.get("home_team")
        matchup = f"{away_team} @ {home_team}" if away_team and home_team else None
        return (
            {
                "season": season,
                "game_id": gid,
                "game_date_et": meta.get("game_date_et"),
                "away_team": away_team,
                "home_team": home_team,
                "matchup": matchup,
                "source": "data.nba.com mobile_teams v2015 play-by-play",
                "possessions": int(len(table_df)),
                "n1_count_L_t_eq_1": wmi_result["n1_count_L_t_eq_1"],
                "n0_count_L_t_eq_0": wmi_result["n0_count_L_t_eq_0"],
                "mean_M_t_where_L_t_eq_1": wmi_result["mean_M_t_where_L_t_eq_1"],
                "mean_M_t_where_L_t_eq_0": wmi_result["mean_M_t_where_L_t_eq_0"],
                "WMI": wmi_result["WMI"],
            },
            None,
        )
    except Exception as error:
        return None, {"season": season, "game_id": gid, "status": "failed", "error_message": str(error)}


def normalize_game_id(value):
    return str(value).zfill(10)


def load_local_2025_rows():
    wmi_df = pd.read_csv(LOCAL_2025_WMI_PATH)
    wmi_df = wmi_df.copy()
    wmi_df["game_id"] = wmi_df["game_id"].map(normalize_game_id)
    wmi_df["source"] = f"local {LOCAL_2025_WMI_PATH.name}"
    wmi_df = wmi_df.drop(columns=["wmi_percentile"], errors="ignore")
    return wmi_df.to_dict("records")


def add_percentiles(df, value_col, out_col):
    out = df.copy()
    values = pd.to_numeric(out[value_col], errors="coerce")
    finite = values.notna() & np.isfinite(values)
    out[out_col] = np.nan
    if finite.sum() == 1:
        out.loc[finite, out_col] = 50.0
    elif finite.sum() > 1:
        out.loc[finite, out_col] = values[finite].rank(method="average", pct=True) * 100.0
    return out


def gaussian_kde_curve(values, grid_points=400):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("No finite WMI values found.")

    std = np.std(values, ddof=1) if values.size > 1 else 0.0
    if values.size == 1 or std == 0.0:
        x_grid = np.linspace(values[0] - 0.5, values[0] + 0.5, grid_points)
        density = np.zeros_like(x_grid)
        density[np.argmin(np.abs(x_grid - values[0]))] = 1.0
        return x_grid, density

    bandwidth = 1.06 * std * (values.size ** (-1.0 / 5.0))
    if bandwidth <= 0:
        bandwidth = 0.1

    xmin = min(0.0, values.min() - (3 * bandwidth))
    xmax = values.max() + (3 * bandwidth)
    x_grid = np.linspace(xmin, xmax, grid_points)
    scaled = (x_grid[:, None] - values[None, :]) / bandwidth
    kernel = np.exp(-0.5 * (scaled**2)) / np.sqrt(2 * np.pi)
    density = kernel.mean(axis=1) / bandwidth
    return x_grid, density


def season_label(df):
    if "season" not in df or df.empty:
        return "none"
    seasons = list(dict.fromkeys(df["season"].dropna().astype(str).tolist()))
    if len(seasons) > 2:
        return f"{seasons[0]} to {seasons[-1]}"
    return ", ".join(seasons)


def build_distribution_plot(df, value_col, title, output_path):
    values = pd.to_numeric(df[value_col], errors="coerce").dropna().to_numpy(dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        fig, ax = plt.subplots(figsize=(11, 7))
        ax.text(0.5, 0.5, f"No finite values found for {value_col}.", ha="center", va="center")
        ax.set_axis_off()
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return

    x_grid, density = gaussian_kde_curve(values)
    mean_wmi = float(values.mean())
    median_wmi = float(np.median(values))

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.hist(
        values,
        bins=45,
        density=True,
        color="#9ecae1",
        edgecolor="#2b5d7d",
        alpha=0.75,
        label="Histogram (density)",
    )
    ax.plot(x_grid, density, color="#c23b22", linewidth=2.5, label="Smoothed density curve")
    ax.axvline(mean_wmi, color="#1d3557", linestyle="--", linewidth=2, label=f"Mean = {mean_wmi:.3f}")
    ax.axvline(median_wmi, color="#2a9d8f", linestyle=":", linewidth=2, label=f"Median = {median_wmi:.3f}")
    ax.set_title(title, fontsize=17, pad=14)
    ax.set_xlabel(value_col, fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.text(
        0.99,
        0.97,
        f"Seasons: {season_label(df)}\nGames: {values.size}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    ax.legend(frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_summary(wmi_df, failures):
    wmi_values = pd.to_numeric(wmi_df["WMI"], errors="coerce").dropna()
    return pd.DataFrame(
        [
            {
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "seasons": "2020-21 through 2025-26",
                "comparison_seasons": season_label(wmi_df),
                "games": int(len(wmi_df)),
                "games_with_wmi": int(len(wmi_values)),
                "mean_wmi": float(wmi_values.mean()) if not wmi_values.empty else None,
                "median_wmi": float(wmi_values.median()) if not wmi_values.empty else None,
                "failures": int(len(failures)),
                "wmi_sources": "; ".join(sorted(wmi_df["source"].dropna().unique())),
            }
        ]
    )


def finalize_dataframe(wmi_rows):
    wmi_df = pd.DataFrame(wmi_rows)
    if not wmi_df.empty:
        wmi_df = wmi_df.sort_values(["season", "game_id"]).reset_index(drop=True)
        wmi_df = add_percentiles(wmi_df, "WMI", "wmi_percentile")
    return wmi_df


def save_outputs(wmi_rows, failures, write_plot=False):
    wmi_df = finalize_dataframe(wmi_rows)
    wmi_df.to_csv(WMI_OUT_PATH, index=False)
    pd.DataFrame(failures).to_csv(FAILURES_OUT_PATH, index=False)
    summary_df = build_summary(wmi_df, failures)
    summary_df.to_csv(SUMMARY_OUT_PATH, index=False)

    if write_plot:
        build_distribution_plot(
            wmi_df,
            "WMI",
            "NBA WMI Distribution (2020-21 to 2025-26)",
            WMI_PLOT_OUT_PATH,
        )

    return wmi_df, summary_df


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "--max-games-per-season",
        type=int,
        default=None,
        help="Optional smoke-test cap. Omit for the complete distribution.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    game_jobs = []
    for config in SEASON_CONFIGS:
        game_count = config["regular_season_games"]
        if args.max_games_per_season is not None:
            game_count = min(game_count, args.max_games_per_season)
        game_jobs.extend(
            (config["season"], game_id(config["prefix"], number))
            for number in range(1, game_count + 1)
        )
    print("games_requested", len(game_jobs), flush=True)

    wmi_rows = []
    failures = []
    total = len(game_jobs)
    done = 0

    for config in SEASON_CONFIGS:
        season_jobs = [(season, gid) for season, gid in game_jobs if season == config["season"]]
        if not season_jobs:
            continue
        print(f"season_start {config['season']} games={len(season_jobs)}", flush=True)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_game = {
                executor.submit(build_game_row, season, gid): (season, gid)
                for season, gid in season_jobs
            }
            for future in as_completed(future_to_game):
                done += 1
                wmi_row, failure = future.result()
                if wmi_row is not None:
                    wmi_rows.append(wmi_row)
                if failure is not None:
                    failures.append(failure)
                if done % CHECKPOINT_EVERY == 0 or done == total:
                    save_outputs(wmi_rows, failures)
                    print(
                        f"progress {done}/{total} wmi={len(wmi_rows)} failures={len(failures)}",
                        flush=True,
                    )

    local_wmi_rows = load_local_2025_rows()
    wmi_rows.extend(local_wmi_rows)
    expected_2025_game_ids = {game_id("00225", number) for number in range(1, 1231)}
    wmi_2025_ids = {row["game_id"] for row in local_wmi_rows}
    failures.extend(
        {
            "season": "2025-26",
            "game_id": gid,
            "dataset": "wmi",
            "status": "not_in_local_2025_26_snapshot",
        }
        for gid in sorted(expected_2025_game_ids - wmi_2025_ids)
    )
    save_outputs(wmi_rows, failures)
    print(
        f"loaded_local_2025 wmi={len(local_wmi_rows)} "
        f"missing_wmi={len(expected_2025_game_ids - wmi_2025_ids)}",
        flush=True,
    )

    _, summary_df = save_outputs(wmi_rows, failures, write_plot=True)

    print("saved_wmi_csv", WMI_OUT_PATH)
    print("saved_summary_csv", SUMMARY_OUT_PATH)
    print("saved_failures_csv", FAILURES_OUT_PATH)
    print("saved_wmi_plot", WMI_PLOT_OUT_PATH)
    print(summary_df.to_string(index=False))
    if failures:
        print("failure_sample", failures[:20])


if __name__ == "__main__":
    main()
