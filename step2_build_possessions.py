import re
import requests
import pandas as pd

GAME_ID = "0022500789"
OUT_PATH = "possessions_step2_sample.csv"


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

        # Count defensive fouls committed by the defending team during this possession.
        def_fouls = grp[
            (grp["actionType"] == "foul")
            & (grp["subType"].astype(str).str.lower() != "offensive")
            & (grp["teamId"] == opponent_id[offense_team_id])
        ]

        foul_teams = (
            def_fouls["teamTricode"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        possession_chunks.append(
            {
                "game_id": GAME_ID,
                "offense_team": offense_team,
                "defense_team": defense_team,
                "start_time": float(grp["game_seconds_elapsed"].min()),
                "last_event_time": float(grp["game_seconds_elapsed"].max()),
                "defensive_foul_count": int(len(def_fouls)),
                "defensive_foul_teams": "|".join(foul_teams),
            }
        )

    # Use next possession start as end_time for realistic possession windows.
    possessions = []
    for i, row in enumerate(possession_chunks):
        next_start = None
        if i + 1 < len(possession_chunks):
            next_start = possession_chunks[i + 1]["start_time"]
        end_time = next_start if next_start is not None else row["last_event_time"]
        possessions.append(
            {
                "game_id": row["game_id"],
                "offense_team": row["offense_team"],
                "defense_team": row["defense_team"],
                "start_time": row["start_time"],
                "end_time": float(end_time),
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
    pbp_df["is_def_foul"] = (pbp_df["actionType"] == "foul") & (pbp_df["subType"] != "offensive")

    possession_df = parse_possessions(pbp_df)
    possession_df.to_csv(OUT_PATH, index=False)

    print("OK")
    print("game_id", GAME_ID)
    print("rows", len(possession_df))
    print(possession_df.head(10).to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
