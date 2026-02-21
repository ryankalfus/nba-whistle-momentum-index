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
    return minutes * 60 + seconds


def is_team_value(value):
    return pd.notna(value) and str(value).strip() != ""


def parse_possessions(pbp_df):
    possessions = []
    current = None
    possession_number = 0
    last_closed = None

    # Dead-ball events should not start a new possession.
    live_ball_actions = {"2pt", "3pt", "turnover", "rebound", "steal", "foul", "jumpball", "freethrow"}

    teams = [t for t in pbp_df["teamTricode"].dropna().unique().tolist() if isinstance(t, str)]
    opponent = {}
    if len(teams) == 2:
        opponent = {teams[0]: teams[1], teams[1]: teams[0]}

    def infer_offense_team(row):
        action_type = row.get("actionType")
        subtype = str(row.get("subType", "")).lower()
        team = row.get("teamTricode")

        if not is_team_value(team):
            return None

        # Defensive events: team on row is defense, offense is opponent.
        if action_type == "foul" and subtype != "offensive" and team in opponent:
            return opponent[team]
        if action_type == "steal" and team in opponent:
            return opponent[team]

        # Offensive events or possession-gain events.
        return team

    for _, row in pbp_df.iterrows():
        action_type = row.get("actionType")
        subtype = str(row.get("subType", "")).lower()
        team = row.get("teamTricode")
        has_team = is_team_value(team)

        # Start possession only on live-ball team events.
        if (
            current is None
            and has_team
            and action_type in live_ball_actions
            and not (action_type == "rebound" and subtype == "offensive")
        ):
            offense_team = infer_offense_team(row)
            if not is_team_value(offense_team):
                continue
            current = {
                "game_id": GAME_ID,
                "possession_number": None,
                "offense_team": offense_team,
                "defense_team": None,
                "start_time": row.get("game_seconds_elapsed"),
                "end_time": None,
                "defensive_foul_count": 0,
                "defensive_foul_teams": [],
            }

        if current is None:
            continue

        # Defensive foul during this possession: foul by non-offense team.
        if action_type == "foul" and subtype != "offensive" and has_team and team != current["offense_team"]:
            current["defensive_foul_count"] += 1
            if team not in current["defensive_foul_teams"]:
                current["defensive_foul_teams"].append(team)

        end_now = False
        if action_type in ("2pt", "3pt"):
            if str(row.get("shotResult", "")).lower() == "made":
                end_now = True
        elif action_type == "rebound" and subtype == "defensive":
            end_now = True
        elif action_type == "turnover":
            end_now = True
        elif action_type == "period" and subtype == "end":
            end_now = True

        if end_now:
            # Protect against duplicate closing rows at same moment for same offense team.
            # Common case: offensive foul + offensive foul turnover sequence.
            moment = (
                current.get("offense_team"),
                row.get("game_seconds_elapsed"),
                row.get("period"),
            )
            if last_closed == moment:
                current = None
                continue

            current["end_time"] = row.get("game_seconds_elapsed")
            possession_number += 1
            current["possession_number"] = possession_number
            possessions.append(current)
            last_closed = moment
            current = None

    # If a possession is still open at end of file, close it at its own start time.
    if current is not None:
        possession_number += 1
        current["possession_number"] = possession_number
        current["end_time"] = current["start_time"]
        possessions.append(current)

    possession_df = pd.DataFrame(possessions)
    if len(teams) == 2:
        possession_df["defense_team"] = possession_df["offense_team"].map({teams[0]: teams[1], teams[1]: teams[0]})

    possession_df = possession_df[
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

    # Cleanup: merge adjacent rows with the same offense team.
    # NBA logs can split a single possession into several micro segments around fouls.
    collapsed = []
    for _, row in possession_df.iterrows():
        record = row.to_dict()
        if not collapsed:
            collapsed.append(record)
            continue

        prev = collapsed[-1]
        if record["offense_team"] == prev["offense_team"]:
            prev["end_time"] = record["end_time"]
            prev["defensive_foul_count"] += record["defensive_foul_count"]
            for foul_team in record["defensive_foul_teams"]:
                if foul_team not in prev["defensive_foul_teams"]:
                    prev["defensive_foul_teams"].append(foul_team)
        else:
            collapsed.append(record)

    collapsed_df = pd.DataFrame(collapsed)
    collapsed_df["possession_number"] = range(1, len(collapsed_df) + 1)
    collapsed_df["defensive_foul_teams"] = collapsed_df["defensive_foul_teams"].apply(lambda teams: "|".join(teams))
    return collapsed_df


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
