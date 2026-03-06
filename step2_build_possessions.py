from __future__ import annotations

import pandas as pd

from nba_pbp_utils import (
    DEFAULT_SINGLE_GAME_ID,
    EXCLUDED_DEF_FOUL_SUBTYPES,
    LIVE_BALL_ACTIONS,
    build_valid_possessions,
    count_defensive_fouls,
    extract_team_context,
    format_output_preview,
    load_game_dataframe,
)

OUT_PATH = "possessions_step2_sample.csv"


def is_team_value(value: object) -> bool:
    return pd.notna(value) and str(value).strip() != ""


def parse_possessions(pbp_df: pd.DataFrame, game_id: str = DEFAULT_SINGLE_GAME_ID) -> pd.DataFrame:
    df = pbp_df.copy().sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df = df[df["game_seconds_elapsed"].notna()].copy()
    df["event_seq_same_clock"] = df.groupby("game_seconds_elapsed").cumcount()
    # Tiny sequence offset preserves event order when multiple events share the same clock time.
    df["timeline_time"] = df["game_seconds_elapsed"] + (df["event_seq_same_clock"] * 0.001)

    team_id_to_tricode, opponent_id, team_ids = extract_team_context(df[df["teamTricode"].apply(is_team_value)].copy())
    valid = build_valid_possessions(df, team_ids)

    possession_chunks = []
    for _, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        offense_team = team_id_to_tricode[offense_team_id]
        defense_team = team_id_to_tricode[opponent_id[offense_team_id]]
        defense_team_id = opponent_id[offense_team_id]

        grp_live = grp[grp["actionType"].isin(LIVE_BALL_ACTIONS)]
        start_time = float(grp_live["timeline_time"].min()) if not grp_live.empty else float(grp["timeline_time"].min())
        last_event_time = float(grp_live["timeline_time"].max()) if not grp_live.empty else float(grp["timeline_time"].max())

        # Count only true defensive fouls by defense team (exclude offensive/technical types).
        def_foul_count = count_defensive_fouls(grp, defense_team_id)
        subtype_lower = grp["subType"].fillna("").astype(str).str.lower()
        def_fouls = grp[
            (grp["actionType"] == "foul")
            & (grp["teamId"] == defense_team_id)
            & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
        ]

        foul_teams = def_fouls["teamTricode"].dropna().astype(str).unique().tolist()

        possession_chunks.append(
            {
                "game_id": game_id,
                "offense_team": offense_team,
                "defense_team": defense_team,
                "start_time": start_time,
                "last_event_time": last_event_time,
                "defensive_foul_count": def_foul_count,
                "defensive_foul_teams": "|".join(foul_teams),
            }
        )

    # End each possession at its own final live-ball event.
    # Start each possession from prior possession end to create continuous game time.
    possessions = []
    for i, row in enumerate(possession_chunks):
        end_time = row["last_event_time"]
        if i == 0:
            start_time = row["start_time"]
        else:
            start_time = possessions[i - 1]["end_time"]

        if end_time < start_time:
            end_time = start_time
        possessions.append(
            {
                "game_id": row["game_id"],
                "offense_team": row["offense_team"],
                "defense_team": row["defense_team"],
                "start_time": round(float(start_time), 3),
                "end_time": round(float(end_time), 3),
                "defensive_foul_count": row["defensive_foul_count"],
                "defensive_foul_teams": row["defensive_foul_teams"],
            }
        )

    possession_df = pd.DataFrame(possessions)
    possession_df["possession_number"] = range(1, len(possession_df) + 1)
    return possession_df[
        [
            "game_id",
            "possession_number",
            "offense_team",
            "defense_team",
            "start_time",
            "end_time",
            "defensive_foul_count",
            "defensive_foul_teams",
        ]
    ]


def main() -> None:
    pbp_df = load_game_dataframe(DEFAULT_SINGLE_GAME_ID)
    possession_df = parse_possessions(pbp_df, game_id=DEFAULT_SINGLE_GAME_ID)
    possession_df.to_csv(OUT_PATH, index=False)
    print(format_output_preview(DEFAULT_SINGLE_GAME_ID, OUT_PATH, possession_df, preview_rows=10))


if __name__ == "__main__":
    main()
