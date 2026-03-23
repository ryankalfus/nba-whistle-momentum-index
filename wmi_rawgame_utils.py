import re

import numpy as np
import pandas as pd
import requests


EXCLUDED_DEF_FOUL_SUBTYPES = {"offensive", "technical", "double technical"}


def default_possession_table_out_path(game_id):
    return f"possession_model_table_{game_id}.csv"


def default_wmi_breakdown_out_path(game_id):
    return f"wmi_rawgame_breakdown_{game_id}.csv"


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


def parse_int(value):
    if pd.isna(value):
        return None
    try:
        return int(value)
    except Exception:
        return None


def infer_team_score_side(df, team_ids):
    mapping = {}
    prev_home = None
    prev_away = None

    for _, row in df.iterrows():
        home = parse_int(row.get("scoreHome"))
        away = parse_int(row.get("scoreAway"))
        team_id = parse_int(row.get("teamId"))

        if home is None or away is None:
            continue

        if prev_home is not None and prev_away is not None and team_id in team_ids:
            home_changed = home != prev_home
            away_changed = away != prev_away
            if home_changed ^ away_changed:
                side = "home" if home_changed else "away"
                if team_id not in mapping:
                    mapping[team_id] = side
                if len(mapping) == 1:
                    known = next(iter(mapping.keys()))
                    other = [tid for tid in team_ids if tid != known][0]
                    mapping[other] = "away" if mapping[known] == "home" else "home"
                    break

        prev_home = home
        prev_away = away

    return mapping


def fetch_game_actions(game_id, session=None, timeout=30):
    session = session or requests.Session()
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    actions = payload.get("game", {}).get("actions", [])
    if not actions:
        raise ValueError(f"No play-by-play actions found for game_id {game_id}.")
    return actions


def add_recent_foul_columns(df, foul_col="foul_called_this_possession"):
    if foul_col not in df.columns:
        raise ValueError(f"Missing required foul column: {foul_col}")

    out = df.copy().reset_index(drop=True)
    if out.empty:
        out["L_t"] = pd.Series(dtype=int)
        out["L_count_t"] = pd.Series(dtype=int)
        out["F_t"] = pd.Series(dtype=int)
        out["N_t"] = pd.Series(dtype=int)
        out["M_t"] = pd.Series(dtype=int)
        return out

    f = out[foul_col].fillna(0).astype(int).to_numpy(dtype=np.int16)

    prev1 = np.concatenate((np.array([0], dtype=np.int16), f[:-1]))
    prev2 = np.concatenate((np.array([0, 0], dtype=np.int16), f[:-2]))
    l_count = prev1 + prev2
    l_vals = (l_count > 0).astype(np.int16)

    next1 = np.concatenate((f[1:], np.array([0], dtype=np.int16)))
    next2 = np.concatenate((f[2:], np.array([0, 0], dtype=np.int16)))
    n_vals = ((next1 + next2) > 0).astype(np.int16)

    out["L_t"] = l_vals.astype(int)
    out["L_count_t"] = l_count.astype(int)
    out["F_t"] = f.astype(int)
    out["N_t"] = n_vals.astype(int)
    out["M_t"] = out["F_t"] + (out["F_t"] * out["N_t"])
    return out


def build_possession_summary_from_actions(actions, game_id):
    df = pd.DataFrame(actions).sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No actions available to build possession summary for game_id {game_id}.")

    df["seconds_remaining_in_period"] = df["clock"].apply(clock_to_seconds)
    df["game_seconds_elapsed"] = (df["period"] - 1) * 720 + (720 - df["seconds_remaining_in_period"])
    df = df[df["game_seconds_elapsed"].notna()].copy()
    if df.empty:
        raise ValueError(f"No valid timed actions found for game_id {game_id}.")

    df["event_seq_same_clock"] = df.groupby("game_seconds_elapsed").cumcount()
    df["timeline_time"] = df["game_seconds_elapsed"] + (df["event_seq_same_clock"] * 0.001)

    team_rows = df[df["teamTricode"].notna()][["teamId", "teamTricode"]].dropna().drop_duplicates()
    team_id_to_tricode = {int(r.teamId): r.teamTricode for _, r in team_rows.iterrows()}
    team_ids = sorted(team_id_to_tricode.keys())
    if len(team_ids) != 2:
        raise ValueError(f"Expected exactly 2 teams in game_id {game_id}.")

    opponent_id = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}
    valid = df[df["possession"].isin(team_ids)].copy()
    if valid.empty:
        raise ValueError(f"No valid possession rows found for game_id {game_id}.")

    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()
    total_game_seconds = float(valid["game_seconds_elapsed"].max())
    score_side = infer_team_score_side(valid, team_ids)

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
        has_def_foul = int(def_foul_count > 0)

        end_time = float(grp["timeline_time"].max())
        score_row = grp[grp["scoreHome"].notna() & grp["scoreAway"].notna()].tail(1)
        score_difference = None
        if len(score_row) == 1:
            sr = score_row.iloc[0]
            sh = parse_int(sr.get("scoreHome"))
            sa = parse_int(sr.get("scoreAway"))
            offense_score = sh if score_side.get(offense_team_id) == "home" else sa
            defense_score = sh if score_side.get(defense_team_id) == "home" else sa
            if offense_score is not None and defense_score is not None:
                score_difference = offense_score - defense_score

        rows.append(
            {
                "game_id": game_id,
                "possession_group": int(group_id),
                "period": int(grp["period"].iloc[-1]),
                "offense_team_id": offense_team_id,
                "defense_team_id": defense_team_id,
                "offense_team": team_id_to_tricode[offense_team_id],
                "defense_team": team_id_to_tricode[defense_team_id],
                "seconds_left_in_game": round(total_game_seconds - end_time, 3),
                "score_difference": score_difference,
                "foul_called_this_possession": has_def_foul,
                "defensive_foul_count": def_foul_count,
            }
        )

    return pd.DataFrame(rows).sort_values("possession_group").reset_index(drop=True)


def build_possession_model_table_from_actions(actions, game_id):
    out = build_possession_summary_from_actions(actions=actions, game_id=game_id)
    out = add_recent_foul_columns(out, foul_col="foul_called_this_possession")
    out["possession_number"] = range(1, len(out) + 1)

    return out[
        [
            "game_id",
            "possession_number",
            "offense_team",
            "defense_team",
            "seconds_left_in_game",
            "score_difference",
            "L_t",
            "F_t",
            "N_t",
            "M_t",
        ]
    ]


def build_possession_model_table(game_id, session=None, timeout=30):
    actions = fetch_game_actions(game_id=game_id, session=session, timeout=timeout)
    return build_possession_model_table_from_actions(actions=actions, game_id=game_id)


def calculate_wmi_rawgame(df):
    required = {"L_t", "F_t", "N_t"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    l = df["L_t"].astype(float)
    f = df["F_t"].astype(float)
    n = df["N_t"].astype(float)
    m = f + (f * n)

    group_l1 = m[l == 1.0]
    group_l0 = m[l == 0.0]

    n1 = int(group_l1.shape[0])
    n0 = int(group_l0.shape[0])
    sum_m_l1 = float(group_l1.sum())
    sum_m_l0 = float(group_l0.sum())

    mean_m_l1 = float(sum_m_l1 / n1) if n1 > 0 else None
    mean_m_l0 = float(sum_m_l0 / n0) if n0 > 0 else None

    wmi_rawgame = None
    if mean_m_l1 is not None and mean_m_l0 not in (None, 0.0):
        wmi_rawgame = float(mean_m_l1 / mean_m_l0)

    return {
        "n1_count_L_t_eq_1": n1,
        "n0_count_L_t_eq_0": n0,
        "sum_M_t_where_L_t_eq_1": sum_m_l1,
        "sum_M_t_where_L_t_eq_0": sum_m_l0,
        "mean_M_t_where_L_t_eq_1": mean_m_l1,
        "mean_M_t_where_L_t_eq_0": mean_m_l0,
        "WMI_rawgame": wmi_rawgame,
    }
