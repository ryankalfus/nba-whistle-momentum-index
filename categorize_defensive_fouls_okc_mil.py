from __future__ import annotations

import pandas as pd

from nba_pbp_utils import (
    DEFAULT_SINGLE_GAME_ID,
    EXCLUDED_DEF_FOUL_SUBTYPES,
    build_valid_possessions,
    calculate_context_flags,
    count_defensive_fouls,
    extract_team_context,
    format_output_preview,
    infer_team_score_side,
    load_game_dataframe,
    parse_int,
)

OUT_PATH = "def_foul_context_okc_mil.csv"


def build_def_foul_context(game_id: str) -> pd.DataFrame:
    df = load_game_dataframe(game_id)
    team_id_to_tricode, opponent_id, team_ids = extract_team_context(df)
    valid = build_valid_possessions(df, team_ids)

    # Build possession summary with boolean: did defending team commit a defensive foul in this possession?
    possession_summary_rows = []
    for group_id, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent_id[offense_team_id]
        has_def_foul = int(count_defensive_fouls(grp, defense_team_id) > 0)
        possession_summary_rows.append(
            {
                "possession_group": int(group_id),
                "offense_team_id": offense_team_id,
                "has_def_foul": has_def_foul,
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
    possession_flags = possession_summary["has_def_foul"].tolist()
    prior_flags, next_flags = calculate_context_flags(possession_flags)
    group_to_index = {
        int(group_id): index
        for index, group_id in enumerate(possession_summary["possession_group"].tolist())
    }

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

        group_index = group_to_index[foul_group]
        called_in_last2 = prior_flags[group_index]
        called_in_next2 = next_flags[group_index]

        rows.append(
            {
                "def_foul_num": i + 1,
                "offense_team": team_id_to_tricode.get(offense_team_id),
                "defense_team": team_id_to_tricode.get(defense_team_id),
                "seconds_left_in_game": round(total_game_seconds - float(row["game_seconds_elapsed"]), 3),
                "score_difference": score_difference,
                "def_foul_called_in_last2_possessions": called_in_last2,
                "def_foul_called_in_next2_possessions": called_in_next2,
                "L_t": called_in_last2,
                "F_t": 1,
                "N_t": called_in_next2,
                "M_t": 1 + called_in_next2,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    out_df = build_def_foul_context(DEFAULT_SINGLE_GAME_ID)
    out_df.to_csv(OUT_PATH, index=False)
    print(format_output_preview(DEFAULT_SINGLE_GAME_ID, OUT_PATH, out_df))


if __name__ == "__main__":
    main()
