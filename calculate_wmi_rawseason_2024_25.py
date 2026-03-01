import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pandas as pd
import requests

SEASON = "2024-25"
SEASON_GAME_ID_PREFIX = "00224"
REGULAR_SEASON_GAME_COUNT = 1230
OUT_PATH = "wmi_rawseason_2024_25_summary.csv"
EXCLUDED_DEF_FOUL_SUBTYPES = {"offensive", "technical", "double technical"}
MAX_WORKERS = 10


def clock_to_seconds(clock_str):
    if pd.isna(clock_str):
        return None
    match = re.match(r"PT(\d+)M(\d+)\.(\d+)S", str(clock_str))
    if not match:
        return None
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    hundredths = int(match.group(3))
    return minutes * 60 + seconds + (hundredths / 100.0)


def fetch_json_with_retry(session, url, timeout=30, tries=4):
    last_error = None
    for i in range(tries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            time.sleep(0.6 * (i + 1))
    raise last_error


def build_possession_table_for_game(session, game_id):
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    payload = fetch_json_with_retry(session, url, timeout=30, tries=4)
    actions = payload.get("game", {}).get("actions", [])
    if not actions:
        return None

    df = pd.DataFrame(actions).sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df["seconds_remaining_in_period"] = df["clock"].apply(clock_to_seconds)
    df["game_seconds_elapsed"] = (df["period"] - 1) * 720 + (720 - df["seconds_remaining_in_period"])
    df = df[df["game_seconds_elapsed"].notna()].copy()
    if df.empty:
        return None

    team_rows = df[df["teamTricode"].notna()][["teamId", "teamTricode"]].dropna().drop_duplicates()
    team_ids = sorted(int(row.teamId) for _, row in team_rows.iterrows())
    if len(team_ids) != 2:
        return None

    opponent_id = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}
    valid = df[df["possession"].isin(team_ids)].copy()
    if valid.empty:
        return None

    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()

    rows = []
    for group_id, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent_id[offense_team_id]

        subtype_lower = grp["subType"].fillna("").astype(str).str.lower()
        def_foul_count = int(
            (
                (grp["actionType"] == "foul")
                & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
                & (grp["teamId"] == defense_team_id)
            ).sum()
        )
        rows.append({"game_id": game_id, "possession_group": int(group_id), "F_t": int(def_foul_count > 0)})

    out = pd.DataFrame(rows).sort_values("possession_group").reset_index(drop=True)
    if out.empty:
        return None

    l_vals = []
    n_vals = []
    for i in range(len(out)):
        prior = out.iloc[max(0, i - 2) : i]
        next_rows = out.iloc[i + 1 : i + 3]
        l_vals.append(int((prior["F_t"] == 1).any()))
        n_vals.append(int((next_rows["F_t"] == 1).any()))

    out["L_t"] = l_vals
    out["N_t"] = n_vals
    out["M_t"] = out["F_t"] + (out["F_t"] * out["N_t"])

    return out[["game_id", "L_t", "F_t", "N_t", "M_t"]]


def get_completed_regular_season_game_ids():
    # NBA regular-season IDs for 2024-25 are sequential: 0022400001 ... 0022401230.
    return [f"{SEASON_GAME_ID_PREFIX}{i:05d}" for i in range(1, REGULAR_SEASON_GAME_COUNT + 1)]


def main():
    session = requests.Session()
    game_ids = get_completed_regular_season_game_ids()
    if not game_ids:
        raise RuntimeError("No completed regular-season games found for this season.")

    print("season", SEASON)
    print("completed_regular_season_games", len(game_ids))

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
            except Exception:
                failed_ids.append(game_id)

            if done % 100 == 0 or done == total:
                print(f"progress {done}/{total} ok={len(tables)} failed={len(failed_ids)}")

    if failed_ids:
        retry_failed = []
        for game_id in failed_ids:
            try:
                table = build_possession_table_for_game(session, game_id)
                if table is None or table.empty:
                    retry_failed.append(game_id)
                else:
                    tables.append(table)
            except Exception:
                retry_failed.append(game_id)
        failed_ids = retry_failed

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
    summary.to_csv(OUT_PATH, index=False)

    print("saved", OUT_PATH)
    print(summary.to_string(index=False))
    if failed_ids:
        print("failed_game_ids_sample", failed_ids[:20])


if __name__ == "__main__":
    main()
