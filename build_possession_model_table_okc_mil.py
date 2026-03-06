from __future__ import annotations

import pandas as pd

from nba_pbp_utils import (
    DEFAULT_SINGLE_GAME_ID,
    build_valid_possessions,
    calculate_context_flags,
    count_defensive_fouls,
    extract_team_context,
    format_output_preview,
    infer_team_score_side,
    load_game_dataframe,
    parse_int,
)

OUT_PATH = "possession_model_table_okc_mil.csv"


def build_table(game_id: str) -> pd.DataFrame:
    df = load_game_dataframe(game_id)
    team_id_to_tricode, opponent_id, team_ids = extract_team_context(df)
    valid = build_valid_possessions(df, team_ids)
    total_game_seconds = float(valid["game_seconds_elapsed"].max())
    score_side = infer_team_score_side(valid, team_ids)

    rows = []
    for group_id, grp in valid.groupby("possession_group", sort=True):
        offense_team_id = int(grp["possession"].iloc[0])
        defense_team_id = opponent_id[offense_team_id]
        def_foul_count = count_defensive_fouls(grp, defense_team_id)
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

    out = pd.DataFrame(rows).sort_values("possession_group").reset_index(drop=True)
    out["possession_number"] = range(1, len(out) + 1)

    l_vals, n_vals = calculate_context_flags(out["foul_called_this_possession"].tolist())

    out["L_t"] = l_vals
    out["F_t"] = out["foul_called_this_possession"].astype(int)
    out["N_t"] = n_vals
    out["M_t"] = out["F_t"] + (out["F_t"] * out["N_t"])

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


def main() -> None:
    out_df = build_table(DEFAULT_SINGLE_GAME_ID)
    out_df.to_csv(OUT_PATH, index=False)
    print(format_output_preview(DEFAULT_SINGLE_GAME_ID, OUT_PATH, out_df))


if __name__ == "__main__":
    main()
