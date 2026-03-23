import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from wmi_rawgame_utils import add_recent_foul_columns
from wmi_rawgame_utils import build_possession_summary_from_actions
from wmi_rawgame_utils import fetch_game_actions


CONTROLLED_MODEL_ID = "count_L_count_t"
CONTROLLED_TRIGGER_VARIABLE = "L_count_t"
CONTROLLED_FORMULA = (
    "F_t ~ L_count_t + seconds_left_in_game + score_difference + "
    "C(period_bucket) + C(offense_team) + C(defense_team)"
)


def period_bucket_for_period(period):
    if pd.isna(period):
        return None
    period = int(period)
    if period <= 4:
        return period
    return "OT"


def add_controlled_context_columns(df):
    required = {
        "game_id",
        "period",
        "offense_team",
        "defense_team",
        "seconds_left_in_game",
        "score_difference",
        "foul_called_this_possession",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    if "possession_group" in out.columns:
        out = out.sort_values("possession_group")
    elif "possession_number" in out.columns:
        out = out.sort_values("possession_number")
    out = out.reset_index(drop=True)

    out = add_recent_foul_columns(out, foul_col="foul_called_this_possession")
    out["period_bucket"] = out["period"].apply(period_bucket_for_period)
    out["intentional_foul_excluded_t"] = (
        (out["F_t"] == 1)
        & (out["period_bucket"].isin([4, "OT"]))
        & (out["seconds_left_in_game"] <= 45)
        & (out["score_difference"] >= 3)
    ).astype(int)

    return out[
        [
            "game_id",
            "offense_team",
            "defense_team",
            "period",
            "period_bucket",
            "seconds_left_in_game",
            "score_difference",
            "L_t",
            "L_count_t",
            "F_t",
            "N_t",
            "M_t",
            "intentional_foul_excluded_t",
        ]
    ]


def build_controlled_possession_table_from_actions(actions, game_id):
    summary_df = build_possession_summary_from_actions(actions=actions, game_id=game_id)
    return add_controlled_context_columns(summary_df)


def build_controlled_possession_table(game_id, session=None, timeout=30):
    actions = fetch_game_actions(game_id=game_id, session=session, timeout=timeout)
    return build_controlled_possession_table_from_actions(actions=actions, game_id=game_id)


def fit_wmi_controlled_model(df):
    required = {
        "L_count_t",
        "F_t",
        "seconds_left_in_game",
        "score_difference",
        "period_bucket",
        "offense_team",
        "defense_team",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    model_df = df.copy()
    model_df = model_df.dropna(
        subset=[
            "L_count_t",
            "F_t",
            "seconds_left_in_game",
            "score_difference",
            "period_bucket",
            "offense_team",
            "defense_team",
        ]
    ).copy()
    if model_df.empty:
        raise ValueError("No usable rows remained for the controlled model.")

    model_df["period_bucket"] = model_df["period_bucket"].astype(str)
    result = smf.logit(CONTROLLED_FORMULA, data=model_df).fit(disp=False, maxiter=100)

    beta = float(result.params[CONTROLLED_TRIGGER_VARIABLE])
    std_err = float(result.bse[CONTROLLED_TRIGGER_VARIABLE])
    p_value = float(result.pvalues[CONTROLLED_TRIGGER_VARIABLE])
    ci = result.conf_int().loc[CONTROLLED_TRIGGER_VARIABLE]
    ci_low_beta = float(ci[0])
    ci_high_beta = float(ci[1])

    odds_ratio = float(np.exp(beta))
    ci_low_odds_ratio = float(np.exp(ci_low_beta))
    ci_high_odds_ratio = float(np.exp(ci_high_beta))
    converged = bool(getattr(result, "converged", result.mle_retvals.get("converged", False)))

    return {
        "model_id": CONTROLLED_MODEL_ID,
        "trigger_variable": CONTROLLED_TRIGGER_VARIABLE,
        "formula": CONTROLLED_FORMULA,
        "fit_method": "logit",
        "converged": converged,
        "rows_used_in_model": int(len(model_df)),
        "beta_trigger": beta,
        "odds_ratio_trigger": odds_ratio,
        "std_err_trigger": std_err,
        "p_value_trigger": p_value,
        "ci_low_beta": ci_low_beta,
        "ci_high_beta": ci_high_beta,
        "ci_low_odds_ratio": ci_low_odds_ratio,
        "ci_high_odds_ratio": ci_high_odds_ratio,
    }
