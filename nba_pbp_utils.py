from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import pandas as pd
import requests

NBA_PLAYBYPLAY_URL = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
DEFAULT_SINGLE_GAME_ID = "0022500789"
LIVE_BALL_ACTIONS = frozenset(
    {
        "jumpball",
        "2pt",
        "3pt",
        "heave",
        "rebound",
        "turnover",
        "steal",
        "foul",
        "freethrow",
        "violation",
    }
)
EXCLUDED_DEF_FOUL_SUBTYPES = frozenset({"offensive", "technical", "double technical"})
RETRYABLE_PIPELINE_ERRORS = (requests.RequestException, ValueError, TypeError, KeyError)


def playbyplay_url(game_id: str) -> str:
    return NBA_PLAYBYPLAY_URL.format(game_id=game_id)


def clock_to_seconds(clock_str: object) -> float | None:
    if pd.isna(clock_str):
        return None
    match = re.match(r"PT(\d+)M(\d+)\.(\d+)S", str(clock_str))
    if not match:
        return None
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    hundredths = int(match.group(3))
    return minutes * 60 + seconds + (hundredths / 100.0)


def parse_int(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_playbyplay_payload(
    game_id: str,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    if session is None:
        response = requests.get(playbyplay_url(game_id), timeout=timeout)
    else:
        response = session.get(playbyplay_url(game_id), timeout=timeout)
    response.raise_for_status()
    return response.json()


def actions_to_dataframe(actions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    if not actions:
        return pd.DataFrame()

    df = pd.DataFrame(actions).sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df["seconds_remaining_in_period"] = df["clock"].apply(clock_to_seconds)
    df["game_seconds_elapsed"] = (df["period"] - 1) * 720 + (720 - df["seconds_remaining_in_period"])
    df = df[df["game_seconds_elapsed"].notna()].copy()
    if df.empty:
        return df

    df["event_seq_same_clock"] = df.groupby("game_seconds_elapsed").cumcount()
    df["timeline_time"] = df["game_seconds_elapsed"] + (df["event_seq_same_clock"] * 0.001)
    return df


def load_game_dataframe(
    game_id: str,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    payload = fetch_playbyplay_payload(game_id, session=session, timeout=timeout)
    actions = payload.get("game", {}).get("actions", [])
    return actions_to_dataframe(actions)


def extract_team_context(df: pd.DataFrame) -> tuple[dict[int, str], dict[int, int], list[int]]:
    team_rows = df[df["teamTricode"].notna()][["teamId", "teamTricode"]].dropna().drop_duplicates()
    team_id_to_tricode = {int(row.teamId): str(row.teamTricode) for _, row in team_rows.iterrows()}
    team_ids = sorted(team_id_to_tricode.keys())
    if len(team_ids) != 2:
        raise ValueError("Expected exactly 2 team IDs in game data.")

    opponent_id = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}
    return team_id_to_tricode, opponent_id, team_ids


def build_valid_possessions(df: pd.DataFrame, team_ids: Sequence[int]) -> pd.DataFrame:
    valid = df[df["possession"].isin(team_ids)].copy()
    if valid.empty:
        return valid

    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()
    return valid


def count_defensive_fouls(group: pd.DataFrame, defense_team_id: int) -> int:
    subtype_lower = group["subType"].fillna("").astype(str).str.lower()
    return int(
        (
            (group["actionType"] == "foul")
            & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
            & (group["teamId"] == defense_team_id)
        ).sum()
    )


def infer_team_score_side(df: pd.DataFrame, team_ids: Sequence[int]) -> dict[int, str]:
    mapping: dict[int, str] = {}
    prev_home: int | None = None
    prev_away: int | None = None

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
                mapping.setdefault(team_id, side)
                if len(mapping) == 1:
                    known_team_id = next(iter(mapping.keys()))
                    other_team_id = next(tid for tid in team_ids if tid != known_team_id)
                    mapping[other_team_id] = "away" if mapping[known_team_id] == "home" else "home"
                    break

        prev_home = home
        prev_away = away

    return mapping


def calculate_context_flags(values: Sequence[int], window: int = 2) -> tuple[list[int], list[int]]:
    normalized_values = [int(value) for value in values]
    prior_flags: list[int] = []
    next_flags: list[int] = []

    for index, _ in enumerate(normalized_values):
        prior_flags.append(int(any(normalized_values[max(0, index - window) : index])))
        next_flags.append(int(any(normalized_values[index + 1 : index + 1 + window])))

    return prior_flags, next_flags


def format_output_preview(
    game_id: str,
    out_path: str,
    dataframe: pd.DataFrame,
    preview_rows: int = 20,
) -> str:
    preview = dataframe.head(preview_rows).to_string(index=False)
    return "\n".join(
        [
            "OK",
            f"game_id {game_id}",
            f"rows {len(dataframe)}",
            preview,
            f"saved {out_path}",
        ]
    )
