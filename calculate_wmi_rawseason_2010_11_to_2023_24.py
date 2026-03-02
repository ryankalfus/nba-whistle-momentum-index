import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests

START_PREFIX = 10  # 2010-11
END_PREFIX = 23    # 2023-24
MAX_GAME_NUMBER = 1300
MAX_WORKERS = 8
OUT_PATH = "wmi_rawseason_2010_11_to_2023_24.csv"
EXCLUDED_DEF_FOUL_SUBTYPES = {"offensive", "technical", "double technical"}


def season_label(prefix):
    start_year = 2000 + prefix
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def game_id(prefix, number):
    return f"002{prefix:02d}{number:05d}"


def fetch_status(session, gid, timeout=30):
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{gid}.json"
    response = session.get(url, timeout=timeout)
    return response.status_code, response


def season_exists(session, prefix):
    gid = game_id(prefix, 1)
    try:
        status, _ = fetch_status(session, gid, timeout=20)
        return status == 200
    except Exception:
        return False


def game_exists(session, prefix, number):
    gid = game_id(prefix, number)
    for _ in range(2):
        try:
            status, _ = fetch_status(session, gid, timeout=20)
            if status == 200:
                return True
            if status in (403, 404):
                return False
        except Exception:
            time.sleep(0.4)
    return False


def find_max_existing_game_number(session, prefix):
    if not game_exists(session, prefix, 1):
        return 0

    lo, hi = 1, MAX_GAME_NUMBER
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if game_exists(session, prefix, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def fetch_game_json_with_retry(session, gid, tries=5):
    for i in range(tries):
        try:
            status, response = fetch_status(session, gid, timeout=30)
            if status == 200:
                return "ok", response.json()
            if status in (403, 404):
                # Could be real missing OR temporary edge denial; retry a few times.
                time.sleep(0.6 * (i + 1))
                continue
            if status in (429, 500, 502, 503, 504):
                time.sleep(0.6 * (i + 1))
                continue
            return "missing", None
        except Exception:
            time.sleep(0.6 * (i + 1))
    return "missing", None


def build_foul_vector(actions):
    if not actions:
        return None

    df = pd.DataFrame(actions)
    needed = {"orderNumber", "actionNumber", "teamTricode", "teamId", "possession", "actionType", "subType"}
    if not needed.issubset(df.columns):
        return None

    df = df.sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    team_rows = df[df["teamTricode"].notna()][["teamId", "teamTricode"]].dropna().drop_duplicates()
    if team_rows.empty:
        return None

    team_ids = sorted(int(row.teamId) for _, row in team_rows.iterrows())
    if len(team_ids) != 2:
        return None
    opponent = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}

    valid = df[df["possession"].isin(team_ids)].copy()
    if valid.empty:
        return None

    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()

    f_vals = []
    for _, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent[offense_team_id]
        subtype_lower = grp["subType"].fillna("").astype(str).str.lower()

        has_def_foul = (
            (grp["actionType"] == "foul")
            & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
            & (grp["teamId"] == defense_team_id)
        ).any()
        f_vals.append(1 if has_def_foul else 0)

    if not f_vals:
        return None
    return np.array(f_vals, dtype=np.int8)


def game_wmi_components(actions):
    f = build_foul_vector(actions)
    if f is None:
        return None

    prev1 = np.concatenate(([0], f[:-1]))
    prev2 = np.concatenate(([0, 0], f[:-2]))
    l = ((prev1 + prev2) > 0).astype(np.int8)

    next1 = np.concatenate((f[1:], [0]))
    next2 = np.concatenate((f[2:], [0, 0]))
    n = ((next1 + next2) > 0).astype(np.int8)

    m = f + (f * n)

    mask_l1 = l == 1
    mask_l0 = l == 0
    n1 = int(mask_l1.sum())
    n0 = int(mask_l0.sum())
    sum_m_l1 = float(m[mask_l1].sum()) if n1 > 0 else 0.0
    sum_m_l0 = float(m[mask_l0].sum()) if n0 > 0 else 0.0
    return n1, n0, sum_m_l1, sum_m_l0


def process_game(session, gid):
    status, payload = fetch_game_json_with_retry(session, gid)
    if status != "ok":
        return {"status": "missing", "game_id": gid}

    actions = payload.get("game", {}).get("actions", [])
    comps = game_wmi_components(actions)
    if comps is None:
        return {"status": "error", "game_id": gid}

    n1, n0, sum_m_l1, sum_m_l0 = comps
    return {
        "status": "ok",
        "game_id": gid,
        "n1": n1,
        "n0": n0,
        "sum_m_l1": sum_m_l1,
        "sum_m_l0": sum_m_l0,
    }


def compute_season(session, prefix):
    season = season_label(prefix)
    max_num = find_max_existing_game_number(session, prefix)
    if max_num == 0:
        return {
            "season": season,
            "season_prefix": f"002{prefix:02d}",
            "as_of_utc_date": datetime.now(UTC).date().isoformat(),
            "max_existing_game_number": 0,
            "games_succeeded": 0,
            "games_missing": 0,
            "games_failed": 0,
            "n1_count_L_t_eq_1": 0,
            "n0_count_L_t_eq_0": 0,
            "sum_M_t_where_L_t_eq_1": 0.0,
            "sum_M_t_where_L_t_eq_0": 0.0,
            "mean_M_t_where_L_t_eq_1": None,
            "mean_M_t_where_L_t_eq_0": None,
            "WMI_rawseason_pooled": None,
        }

    gids = [game_id(prefix, i) for i in range(1, max_num + 1)]
    print(f"{season}: checking 1..{max_num} game IDs")

    ok = 0
    missing = 0
    error = 0
    n1_total = 0
    n0_total = 0
    sum_m_l1_total = 0.0
    sum_m_l0_total = 0.0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_game, session, gid): gid for gid in gids}
        done = 0
        total = len(futures)
        for future in as_completed(futures):
            done += 1
            result = future.result()
            status = result["status"]
            if status == "ok":
                ok += 1
                n1_total += result["n1"]
                n0_total += result["n0"]
                sum_m_l1_total += result["sum_m_l1"]
                sum_m_l0_total += result["sum_m_l0"]
            elif status == "missing":
                missing += 1
            else:
                error += 1

            if done % 200 == 0 or done == total:
                print(f"{season} progress {done}/{total} ok={ok} missing={missing} error={error}")

    mean_m_l1 = float(sum_m_l1_total / n1_total) if n1_total > 0 else None
    mean_m_l0 = float(sum_m_l0_total / n0_total) if n0_total > 0 else None
    wmi = None
    if mean_m_l1 is not None and mean_m_l0 not in (None, 0.0):
        wmi = float(mean_m_l1 / mean_m_l0)

    return {
        "season": season,
        "season_prefix": f"002{prefix:02d}",
        "as_of_utc_date": datetime.now(UTC).date().isoformat(),
        "max_existing_game_number": max_num,
        "games_succeeded": ok,
        "games_missing": missing,
        "games_failed": error,
        "n1_count_L_t_eq_1": n1_total,
        "n0_count_L_t_eq_0": n0_total,
        "sum_M_t_where_L_t_eq_1": sum_m_l1_total,
        "sum_M_t_where_L_t_eq_0": sum_m_l0_total,
        "mean_M_t_where_L_t_eq_1": mean_m_l1,
        "mean_M_t_where_L_t_eq_0": mean_m_l0,
        "WMI_rawseason_pooled": wmi,
    }


def main():
    session = requests.Session()

    requested = [season_label(p) for p in range(START_PREFIX, END_PREFIX + 1)]
    available = [p for p in range(START_PREFIX, END_PREFIX + 1) if season_exists(session, p)]
    unavailable = [p for p in range(START_PREFIX, END_PREFIX + 1) if p not in available]

    print("requested_seasons", requested)
    print("available_seasons", [season_label(p) for p in available])
    print("unavailable_seasons", [season_label(p) for p in unavailable])

    rows = []
    for prefix in available:
        print(f"--- computing {season_label(prefix)} ---")
        rows.append(compute_season(session, prefix))
        # Small cool-down helps avoid edge throttling across seasons.
        time.sleep(1.5)

    out_df = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    out_df.to_csv(OUT_PATH, index=False)
    print("saved", OUT_PATH)
    print(out_df[["season", "max_existing_game_number", "games_succeeded", "games_missing", "WMI_rawseason_pooled"]].to_string(index=False))


if __name__ == "__main__":
    main()
