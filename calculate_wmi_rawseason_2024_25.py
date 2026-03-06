from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pandas as pd
import requests

from nba_pbp_utils import (
    RETRYABLE_PIPELINE_ERRORS,
    build_valid_possessions,
    calculate_context_flags,
    count_defensive_fouls,
    extract_team_context,
    load_game_dataframe,
)

SEASON = "2024-25"
SEASON_GAME_ID_PREFIX = "00224"
REGULAR_SEASON_GAME_COUNT = 1230
OUT_PATH = "wmi_rawseason_2024_25_summary.csv"
MAX_WORKERS = 10


def load_game_dataframe_with_retry(
    session: requests.Session,
    game_id: str,
    timeout: int = 30,
    tries: int = 4,
) -> pd.DataFrame:
    last_error: Exception | None = None
    for i in range(tries):
        try:
            return load_game_dataframe(game_id, session=session, timeout=timeout)
        except RETRYABLE_PIPELINE_ERRORS as error:
            last_error = error
            time.sleep(0.6 * (i + 1))
    if last_error is None:
        raise RuntimeError(f"Failed to load game {game_id}.")
    raise last_error


def build_possession_table_for_game(
    session: requests.Session,
    game_id: str,
) -> pd.DataFrame | None:
    df = load_game_dataframe_with_retry(session, game_id, timeout=30, tries=4)
    if df.empty:
        return None

    _, opponent_id, team_ids = extract_team_context(df)
    valid = build_valid_possessions(df, team_ids)
    if valid.empty:
        return None

    rows = []
    for group_id, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent_id[offense_team_id]
        def_foul_count = count_defensive_fouls(grp, defense_team_id)
        rows.append({"game_id": game_id, "possession_group": int(group_id), "F_t": int(def_foul_count > 0)})

    out = pd.DataFrame(rows).sort_values("possession_group").reset_index(drop=True)
    if out.empty:
        return None

    l_vals, n_vals = calculate_context_flags(out["F_t"].tolist())
    out["L_t"] = l_vals
    out["N_t"] = n_vals
    out["M_t"] = out["F_t"] + (out["F_t"] * out["N_t"])

    return out[["game_id", "L_t", "F_t", "N_t", "M_t"]]


def get_completed_regular_season_game_ids() -> list[str]:
    # NBA regular-season IDs for 2024-25 are sequential: 0022400001 ... 0022401230.
    return [f"{SEASON_GAME_ID_PREFIX}{i:05d}" for i in range(1, REGULAR_SEASON_GAME_COUNT + 1)]


def collect_game_tables(
    session: requests.Session,
    game_ids: list[str],
) -> tuple[list[pd.DataFrame], list[str]]:
    tables, failed_ids = collect_parallel_tables(session, game_ids)
    if failed_ids:
        failed_ids = retry_failed_tables(session, failed_ids, tables)
    return tables, failed_ids


def collect_parallel_tables(
    session: requests.Session,
    game_ids: list[str],
) -> tuple[list[pd.DataFrame], list[str]]:
    tables = []
    failed_ids = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {
            executor.submit(build_possession_table_for_game, session, game_id): game_id
            for game_id in game_ids
        }
        total = len(future_to_id)
        done = 0

        for future in as_completed(future_to_id):
            game_id = future_to_id[future]
            done += 1
            try:
                table = future.result()
                if table is None or table.empty:
                    failed_ids.append(game_id)
                else:
                    tables.append(table)
            except RETRYABLE_PIPELINE_ERRORS:
                failed_ids.append(game_id)

            if done % 100 == 0 or done == total:
                print(f"progress {done}/{total} ok={len(tables)} failed={len(failed_ids)}")

    return tables, failed_ids


def retry_failed_tables(
    session: requests.Session,
    failed_ids: list[str],
    tables: list[pd.DataFrame],
) -> list[str]:
    retry_failed = []
    for game_id in failed_ids:
        try:
            table = build_possession_table_for_game(session, game_id)
            if table is None or table.empty:
                retry_failed.append(game_id)
            else:
                tables.append(table)
        except RETRYABLE_PIPELINE_ERRORS:
            retry_failed.append(game_id)
    return retry_failed


def build_summary(
    game_ids: list[str],
    tables: list[pd.DataFrame],
    failed_ids: list[str],
) -> pd.DataFrame:
    if not tables:
        raise RuntimeError("No possession tables were built.")

    all_possessions = pd.concat(tables, ignore_index=True)

    group_l1 = all_possessions[all_possessions["L_t"] == 1]
    group_l0 = all_possessions[all_possessions["L_t"] == 0]

    n1 = int(len(group_l1))
    n0 = int(len(group_l0))
    sum_m_l1 = float(group_l1["M_t"].sum())
    sum_m_l0 = float(group_l0["M_t"].sum())
    mean_m_l1 = float(sum_m_l1 / n1) if n1 > 0 else None
    mean_m_l0 = float(sum_m_l0 / n0) if n0 > 0 else None
    wmi_raw_season = None
    if mean_m_l1 is not None and mean_m_l0 not in (None, 0.0):
        wmi_raw_season = float(mean_m_l1 / mean_m_l0)

    summary = pd.DataFrame(
        [
            {
                "season": SEASON,
                "as_of_utc_date": datetime.now(UTC).date().isoformat(),
                "games_requested": len(game_ids),
                "games_succeeded": int(all_possessions["game_id"].nunique()),
                "games_failed": len(failed_ids),
                "n1_count_L_t_eq_1": n1,
                "n0_count_L_t_eq_0": n0,
                "mean_M_t_where_L_t_eq_1": mean_m_l1,
                "mean_M_t_where_L_t_eq_0": mean_m_l0,
                "WMI_rawseason_pooled": wmi_raw_season,
            }
        ]
    )
    return summary


def main() -> None:
    session = requests.Session()
    game_ids = get_completed_regular_season_game_ids()
    if not game_ids:
        raise RuntimeError("No completed regular-season games found for this season.")

    print("season", SEASON)
    print("completed_regular_season_games", len(game_ids))

    tables, failed_ids = collect_game_tables(session, game_ids)
    summary = build_summary(game_ids, tables, failed_ids)
    summary.to_csv(OUT_PATH, index=False)

    print("saved", OUT_PATH)
    print(summary.to_string(index=False))
    if failed_ids:
        print("failed_game_ids_sample", failed_ids[:20])


if __name__ == "__main__":
    main()
