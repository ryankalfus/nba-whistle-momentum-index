import numpy as np
import pandas as pd
import requests


EXCLUDED_DEF_FOUL_SUBTYPES = {"offensive", "technical", "double technical"}


def default_possession_table_out_path(game_id):
    return f"possession_model_table_{game_id}.csv"


def default_wmi_breakdown_out_path(game_id):
    return f"wmi_breakdown_{game_id}.csv"


def clock_to_seconds(clock_str):
    from wmi_possessions import clock_seconds
    return clock_seconds(clock_str)


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
        out["F_t"] = pd.Series(dtype=int)
        out["N_t"] = pd.Series(dtype=int)
        out["M_t"] = pd.Series(dtype=int)
        return out

    f = out[foul_col].fillna(0).astype(int).to_numpy(dtype=np.int16)

    l_vals = np.zeros(len(f), dtype=np.int16)
    n_vals = np.zeros(len(f), dtype=np.int16)
    for distance in (1, 2):
        if distance < len(f):
            l_vals[distance:] |= (f[:-distance] > 0)
            n_vals[:-distance] |= (f[distance:] > 0)

    out["L_t"] = l_vals.astype(int)
    out["F_t"] = f.astype(int)
    out["N_t"] = n_vals.astype(int)
    out["M_t"] = out["F_t"] + (out["F_t"] * out["N_t"])
    return out


def build_possession_summary_from_actions(actions, game_id):
    from wmi_possessions import reconstruct
    return reconstruct(actions, game_id)


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


def calculate_wmi(df):
    required = {"L_t", "F_t", "N_t"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    recent_foul = df["L_t"].astype(float)
    f = df["F_t"].astype(float)
    n = df["N_t"].astype(float)
    m = f + (f * n)

    group_l1 = m[recent_foul == 1.0]
    group_l0 = m[recent_foul == 0.0]

    n1 = int(group_l1.shape[0])
    n0 = int(group_l0.shape[0])
    sum_m_l1 = float(group_l1.sum())
    sum_m_l0 = float(group_l0.sum())

    mean_m_l1 = float(sum_m_l1 / n1) if n1 > 0 else None
    mean_m_l0 = float(sum_m_l0 / n0) if n0 > 0 else None

    wmi = None
    if mean_m_l1 is not None and mean_m_l0 not in (None, 0.0):
        wmi = float(mean_m_l1 / mean_m_l0)

    return {
        "n1_count_L_t_eq_1": n1,
        "n0_count_L_t_eq_0": n0,
        "sum_M_t_where_L_t_eq_1": sum_m_l1,
        "sum_M_t_where_L_t_eq_0": sum_m_l0,
        "mean_M_t_where_L_t_eq_1": mean_m_l1,
        "mean_M_t_where_L_t_eq_0": mean_m_l0,
        "WMI": wmi,
    }
