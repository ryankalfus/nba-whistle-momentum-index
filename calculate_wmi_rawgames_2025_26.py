import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pandas as pd
import requests

from wmi_rawgame_utils import build_possession_model_table
from wmi_rawgame_utils import calculate_wmi_rawgame


SEASON = "2025-26"
SEASON_GAME_ID_PREFIX = "00225"
REGULAR_SEASON_GAME_COUNT = 1230
MAX_WORKERS = 10


def game_id(number):
    return f"{SEASON_GAME_ID_PREFIX}{number:05d}"


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


def fetch_status(session, gid, timeout=30):
    url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json"
    response = session.get(url, timeout=timeout)
    return response.status_code


def game_exists(session, number):
    gid = game_id(number)
    for _ in range(2):
        try:
            status = fetch_status(session, gid, timeout=20)
            if status == 200:
                return True
            if status in (403, 404):
                return False
        except Exception:
            time.sleep(0.4)
    return False


def find_max_existing_game_number(session):
    if not game_exists(session, 1):
        return 0

    lo, hi = 1, REGULAR_SEASON_GAME_COUNT
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if game_exists(session, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def build_game_row(session, gid):
    boxscore_url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json"
    boxscore_payload = fetch_json_with_retry(session, boxscore_url, timeout=30, tries=4)
    game = boxscore_payload.get("game", {})

    game_status = game.get("gameStatus")
    game_status_text = game.get("gameStatusText")
    if game_status != 3 and str(game_status_text).lower() != "final":
        return {"status": "skip_not_final", "game_id": gid}

    table_df = build_possession_model_table(gid, session=session)
    result = calculate_wmi_rawgame(table_df)

    away_team = game.get("awayTeam", {}).get("teamTricode")
    home_team = game.get("homeTeam", {}).get("teamTricode")
    matchup = None
    if away_team and home_team:
        matchup = f"{away_team} @ {home_team}"

    return {
        "status": "ok",
        "season": SEASON,
        "game_id": gid,
        "game_date_et": game.get("gameEt"),
        "game_status": game_status,
        "game_status_text": game_status_text,
        "away_team": away_team,
        "home_team": home_team,
        "matchup": matchup,
        "possessions": int(len(table_df)),
        "n1_count_L_t_eq_1": result["n1_count_L_t_eq_1"],
        "n0_count_L_t_eq_0": result["n0_count_L_t_eq_0"],
        "mean_M_t_where_L_t_eq_1": result["mean_M_t_where_L_t_eq_1"],
        "mean_M_t_where_L_t_eq_0": result["mean_M_t_where_L_t_eq_0"],
        "WMI_rawgame": result["WMI_rawgame"],
    }


def add_z_scores(df):
    out = df.copy()
    if out.empty:
        out["wmi_rawgame_z_score"] = pd.Series(dtype=float)
        return out, None, None

    mean_wmi = float(out["WMI_rawgame"].mean())
    std_wmi = float(out["WMI_rawgame"].std(ddof=0))
    if std_wmi == 0.0:
        out["wmi_rawgame_z_score"] = None
    else:
        out["wmi_rawgame_z_score"] = (out["WMI_rawgame"] - mean_wmi) / std_wmi
    return out, mean_wmi, std_wmi


def main():
    session = requests.Session()
    as_of_date = datetime.now(UTC).date().isoformat()
    out_path = f"wmi_rawgames_2025_26_asof_{as_of_date.replace('-', '_')}.csv"

    max_existing = find_max_existing_game_number(session)
    if max_existing == 0:
        raise RuntimeError("No existing 2025-26 regular-season game IDs found.")

    game_ids = [game_id(i) for i in range(1, max_existing + 1)]
    print("season", SEASON)
    print("max_existing_game_number", max_existing)
    print("game_ids_checked", len(game_ids))

    rows = []
    skipped_not_final = []
    failed_ids = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(build_game_row, session, gid): gid for gid in game_ids}
        total = len(future_to_id)
        done = 0

        for future in as_completed(future_to_id):
            gid = future_to_id[future]
            done += 1
            try:
                result = future.result()
                status = result["status"]
                if status == "ok":
                    rows.append(result)
                elif status == "skip_not_final":
                    skipped_not_final.append(gid)
                else:
                    failed_ids.append(gid)
            except Exception:
                failed_ids.append(gid)

            if done % 100 == 0 or done == total:
                print(
                    f"progress {done}/{total} ok={len(rows)} "
                    f"not_final={len(skipped_not_final)} failed={len(failed_ids)}"
                )

    if failed_ids:
        retry_failed = []
        for gid in failed_ids:
            try:
                result = build_game_row(session, gid)
                status = result["status"]
                if status == "ok":
                    rows.append(result)
                elif status == "skip_not_final":
                    skipped_not_final.append(gid)
                else:
                    retry_failed.append(gid)
            except Exception:
                retry_failed.append(gid)
        failed_ids = retry_failed

    if not rows:
        raise RuntimeError("No completed games were successfully processed.")

    out_df = pd.DataFrame(rows).drop(columns=["status"]).sort_values("game_id").reset_index(drop=True)
    out_df, mean_wmi, std_wmi = add_z_scores(out_df)
    out_df.insert(1, "as_of_utc_date", as_of_date)
    out_df.to_csv(out_path, index=False)

    print("saved", out_path)
    print("games_succeeded", len(out_df))
    print("games_not_final", len(set(skipped_not_final)))
    print("games_failed", len(set(failed_ids)))
    print("mean_game_wmi_raw", mean_wmi)
    print("std_game_wmi_raw", std_wmi)
    print(out_df.head(10).to_string(index=False))
    if failed_ids:
        print("failed_game_ids_sample", sorted(set(failed_ids))[:20])


if __name__ == "__main__":
    main()
