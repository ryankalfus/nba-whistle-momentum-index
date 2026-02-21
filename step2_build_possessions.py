import re
import requests
import pandas as pd

GAME_ID = "0022500789"
OUT_PATH = "possessions_step2_sample.csv"
LIVE_BALL_ACTIONS = {
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
EXCLUDED_DEF_FOUL_SUBTYPES = {"offensive", "technical", "double technical"}


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


def is_team_value(value):
    return pd.notna(value) and str(value).strip() != ""


def parse_possessions(pbp_df):
    df = pbp_df.copy().sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df = df[df["game_seconds_elapsed"].notna()].copy()
    df["event_seq_same_clock"] = df.groupby("game_seconds_elapsed").cumcount()
    # Tiny sequence offset preserves event order when multiple events share the same clock time.
    df["timeline_time"] = df["game_seconds_elapsed"] + (df["event_seq_same_clock"] * 0.001)

    team_rows = df[df["teamTricode"].apply(is_team_value)][["teamId", "teamTricode"]].dropna().drop_duplicates()
    team_id_to_tricode = {int(r.teamId): r.teamTricode for _, r in team_rows.iterrows()}
    team_ids = sorted(team_id_to_tricode.keys())
    if len(team_ids) != 2:
        raise ValueError("Expected exactly 2 team IDs in game data.")

    opponent_id = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}

    # Keep only events where possession points to an actual team.
    valid = df[df["possession"].isin(team_ids)].copy()
    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()

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
        subtype_lower = grp["subType"].fillna("").astype(str).str.lower()
        def_fouls = grp[
            (grp["actionType"] == "foul")
            & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
            & (grp["teamId"] == defense_team_id)
        ]

        foul_teams = def_fouls["teamTricode"].dropna().astype(str).unique().tolist()

        possession_chunks.append(
            {
                "game_id": GAME_ID,
                "offense_team": offense_team,
                "defense_team": defense_team,
                "start_time": start_time,
                "last_event_time": last_event_time,
                "defensive_foul_count": int(len(def_fouls)),
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


def main():
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{GAME_ID}.json"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    pbp_df = pd.DataFrame(response.json()["game"]["actions"])
    pbp_df["seconds_remaining_in_period"] = pbp_df["clock"].apply(clock_to_seconds)
    pbp_df["game_seconds_elapsed"] = (pbp_df["period"] - 1) * 720 + (720 - pbp_df["seconds_remaining_in_period"])

    possession_df = parse_possessions(pbp_df)
    possession_df.to_csv(OUT_PATH, index=False)

    print("OK")
    print("game_id", GAME_ID)
    print("rows", len(possession_df))
    print(possession_df.head(10).to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
