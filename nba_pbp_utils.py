"""Helpers for historical single-game examples; these tables are descriptive."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd
import requests

from wmi_possessions import clock_seconds as clock_to_seconds, elapsed_seconds
from wmi_utils import (
    EXCLUDED_DEF_FOUL_SUBTYPES as EXCLUDED_DEF_FOUL_SUBTYPES,
    fetch_game_actions,
    infer_team_score_side as infer_team_score_side,
    parse_int as parse_int,
)

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


def playbyplay_url(game_id: str) -> str:
    return NBA_PLAYBYPLAY_URL.format(game_id=game_id)


def actions_to_dataframe(actions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    if not actions:
        return pd.DataFrame()

    df = pd.DataFrame(actions).sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df["seconds_remaining_in_period"] = df["clock"].apply(clock_to_seconds)
    df = df.dropna(subset=["period", "seconds_remaining_in_period"]).copy()
    df["game_seconds_elapsed"] = [
        elapsed_seconds(period, clock)
        for period, clock in zip(df["period"], df["seconds_remaining_in_period"], strict=True)
    ]
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
    return actions_to_dataframe(fetch_game_actions(game_id, session=session, timeout=timeout))


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
