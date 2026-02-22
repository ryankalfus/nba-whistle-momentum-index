import re
import requests
import pandas as pd

GAME_ID = "0022500789"
OUT_PATH = "def_foul_context_okc_mil.csv"
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


def parse_int(value):
    if pd.isna(value):
        return None
    try:
        return int(value)
    except Exception:
        return None


def infer_team_score_side(df, team_ids):
    # Map each teamId to either "home" (scoreHome) or "away" (scoreAway)
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

            # Only trust rows where exactly one side changed.
            if home_changed ^ away_changed:
                side = "home" if home_changed else "away"
                if team_id not in mapping:
                    mapping[team_id] = side
                if len(mapping) == 1:
                    known_team = next(iter(mapping.keys()))
                    other_team = [tid for tid in team_ids if tid != known_team][0]
                    mapping[other_team] = "away" if mapping[known_team] == "home" else "home"
                    break

        prev_home = home
        prev_away = away

    return mapping


def build_def_foul_context(game_id):
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    df = pd.DataFrame(payload["game"]["actions"]).sort_values(["orderNumber", "actionNumber"]).reset_index(drop=True)
    df["seconds_remaining_in_period"] = df["clock"].apply(clock_to_seconds)
    df["game_seconds_elapsed"] = (df["period"] - 1) * 720 + (720 - df["seconds_remaining_in_period"])
    df["event_seq_same_clock"] = df.groupby("game_seconds_elapsed").cumcount()
    df["timeline_time"] = df["game_seconds_elapsed"] + (df["event_seq_same_clock"] * 0.001)

    team_rows = df[df["teamTricode"].notna()][["teamId", "teamTricode"]].dropna().drop_duplicates()
    team_id_to_tricode = {int(r.teamId): r.teamTricode for _, r in team_rows.iterrows()}
    team_ids = sorted(team_id_to_tricode.keys())
    if len(team_ids) != 2:
        raise ValueError("Expected exactly 2 teams in game.")

    # Possession groups for searching prior/next possessions.
    valid = df[df["possession"].isin(team_ids)].copy()
    valid["is_new_possession"] = valid["possession"] != valid["possession"].shift(1)
    valid["possession_group"] = valid["is_new_possession"].cumsum()

    opponent_id = {team_ids[0]: team_ids[1], team_ids[1]: team_ids[0]}

    # Build possession summary with boolean: did defending team commit a defensive foul in this possession?
    possession_summary_rows = []
    for group_id, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent_id[offense_team_id]
        subtype_lower = grp["subType"].fillna("").astype(str).str.lower()
        has_def_foul = (
            (grp["actionType"] == "foul")
            & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
            & (grp["teamId"] == defense_team_id)
        ).any()
        possession_summary_rows.append(
            {
                "possession_group": int(group_id),
                "offense_team_id": offense_team_id,
                "has_def_foul": int(has_def_foul),
            }
        )
    possession_summary = pd.DataFrame(possession_summary_rows)

    # Defensive foul events only.
    subtype_lower = valid["subType"].fillna("").astype(str).str.lower()
    def_foul_events = valid[
        (valid["actionType"] == "foul")
        & (~subtype_lower.isin(EXCLUDED_DEF_FOUL_SUBTYPES))
        & (valid["teamId"] != valid["possession"])
    ].copy()
    def_foul_events = def_foul_events.sort_values(["timeline_time", "orderNumber", "actionNumber"]).reset_index(drop=True)

    # Infer team -> score side mapping (home/away) from score changes in PBP.
    team_score_side = infer_team_score_side(valid, team_ids)
    total_game_seconds = float(valid["game_seconds_elapsed"].max())

    rows = []
    for i, row in def_foul_events.iterrows():
        offense_team_id = int(row["possession"])
        defense_team_id = int(row["teamId"])
        foul_group = int(row["possession_group"])

        # score_difference = offensive score - defensive score at foul moment.
        score_home = parse_int(row.get("scoreHome"))
        score_away = parse_int(row.get("scoreAway"))
        offense_score = None
        defense_score = None
        if team_score_side.get(offense_team_id) == "home":
            offense_score = score_home
        elif team_score_side.get(offense_team_id) == "away":
            offense_score = score_away
        if team_score_side.get(defense_team_id) == "home":
            defense_score = score_home
        elif team_score_side.get(defense_team_id) == "away":
            defense_score = score_away

        score_difference = None
        if offense_score is not None and defense_score is not None:
            score_difference = offense_score - defense_score

        # Last two times current defensive team had offense BEFORE this foul.
        prior_def_team_possessions = possession_summary[
            (possession_summary["offense_team_id"] == defense_team_id)
            & (possession_summary["possession_group"] < foul_group)
        ].tail(2)
        called_in_last2 = int((prior_def_team_possessions["has_def_foul"] == 1).any())

        # Next two times current defensive team has offense AFTER this foul.
        next_def_team_possessions = possession_summary[
            (possession_summary["offense_team_id"] == defense_team_id)
            & (possession_summary["possession_group"] > foul_group)
        ].head(2)
        called_in_next2 = int((next_def_team_possessions["has_def_foul"] == 1).any())

        rows.append(
            {
                "def_foul_num": i + 1,
                "offense_team": team_id_to_tricode.get(offense_team_id),
                "defense_team": team_id_to_tricode.get(defense_team_id),
                "seconds_left_in_game": round(total_game_seconds - float(row["game_seconds_elapsed"]), 3),
                "score_difference": score_difference,
                "def_foul_called_in_last2_defensive_team_possessions": called_in_last2,
                "def_foul_called_in_next2_defensive_team_possessions": called_in_next2,
            }
        )

    return pd.DataFrame(rows)


def main():
    out_df = build_def_foul_context(GAME_ID)
    out_df.to_csv(OUT_PATH, index=False)
    print("OK")
    print("game_id", GAME_ID)
    print("rows", len(out_df))
    print(out_df.head(20).to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
