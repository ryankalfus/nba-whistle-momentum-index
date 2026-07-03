from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from wmi_game_utils import build_possession_summary_from_actions
from wmi_game_utils import fetch_game_actions
from wmi_game_utils import add_recent_foul_columns


DEFAULT_CONTROLLED_FORMULA = (
    "M_t ~ L_t + seconds_left_in_game + score_difference "
    "+ C(period_bucket) + C(offense_team) + C(defense_team)"
)
DEFAULT_MODEL_ID = "poisson_glm_raw_controls_v2"
DEFAULT_FIT_METHOD = "glm_poisson_log_raw_controls"


def _safe_exp(value):
    with np.errstate(over="ignore", invalid="ignore"):
        out = np.exp(value)
    return float(out)


def default_controlled_table_out_path(game_id):
    return f"possession_model_table_controlled_{game_id}.csv"


def default_controlled_breakdown_out_path(game_id):
    return f"wmi_controlledgame_breakdown_{game_id}.csv"


def period_to_bucket(period):
    period_int = int(period)
    if period_int >= 5:
        return "OT"
    return str(period_int)


def add_controlled_exclusion_columns(df):
    out = df.copy()
    if out.empty:
        out["period_bucket"] = pd.Series(dtype=str)
        out["score_margin_excluded_t"] = pd.Series(dtype=int)
        out["intentional_foul_excluded_t"] = pd.Series(dtype=int)
        out["controlled_excluded_t"] = pd.Series(dtype=int)
        return out

    score_diff = pd.to_numeric(out["score_difference"], errors="coerce")
    seconds_left = pd.to_numeric(out["seconds_left_in_game"], errors="coerce")
    foul_now = pd.to_numeric(out["F_t"], errors="coerce").fillna(0).astype(int)

    out["period_bucket"] = out["period"].map(period_to_bucket)
    out["score_margin_excluded_t"] = (score_diff.abs() >= 15).fillna(False).astype(int)

    late_game_period = out["period"].fillna(0).astype(int) >= 4
    intentional = foul_now.eq(1) & late_game_period & (
        ((seconds_left <= 35) & (score_diff > 3))
        | ((seconds_left <= 15) & (score_diff >= 1))
    )
    out["intentional_foul_excluded_t"] = intentional.fillna(False).astype(int)
    out["controlled_excluded_t"] = (
        (out["score_margin_excluded_t"] == 1) | (out["intentional_foul_excluded_t"] == 1)
    ).astype(int)
    return out


def build_controlled_possession_table_from_actions(actions, game_id):
    out = build_possession_summary_from_actions(actions=actions, game_id=game_id)
    out = add_recent_foul_columns(out, foul_col="foul_called_this_possession")
    out = add_controlled_exclusion_columns(out)
    out["possession_number"] = range(1, len(out) + 1)

    return out[
        [
            "game_id",
            "possession_number",
            "period",
            "period_bucket",
            "offense_team",
            "defense_team",
            "seconds_left_in_game",
            "score_difference",
            "L_t",
            "F_t",
            "N_t",
            "M_t",
            "score_margin_excluded_t",
            "intentional_foul_excluded_t",
            "controlled_excluded_t",
        ]
    ]


def build_controlled_possession_table(game_id, session=None, timeout=30):
    actions = fetch_game_actions(game_id=game_id, session=session, timeout=timeout)
    return build_controlled_possession_table_from_actions(actions=actions, game_id=game_id)


def build_controlled_tables_for_game_ids(game_ids, session=None, timeout=30, max_workers=10):
    if session is None:
        raise ValueError("A requests session is required to build controlled tables in parallel.")

    tables = []
    failed_ids = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(build_controlled_possession_table, gid, session, timeout): gid
            for gid in game_ids
        }
        for future in as_completed(futures):
            gid = futures[future]
            try:
                table = future.result()
                if table.empty:
                    failed_ids.append(gid)
                else:
                    tables.append(table)
            except Exception:
                failed_ids.append(gid)

    return tables, failed_ids


def _build_failure_result(
    df,
    *,
    fit_status,
    formula=DEFAULT_CONTROLLED_FORMULA,
    model_id=DEFAULT_MODEL_ID,
    fit_method=DEFAULT_FIT_METHOD,
    error_message=None,
):
    rows_before_exclusion = int(len(df))
    rows_excluded_score_margin = int(df.get("score_margin_excluded_t", pd.Series(dtype=int)).sum())
    rows_excluded_intentional = int(df.get("intentional_foul_excluded_t", pd.Series(dtype=int)).sum())
    rows_excluded_total = int(df.get("controlled_excluded_t", pd.Series(dtype=int)).sum())
    model_source_df = df.copy()
    rows_before_model = int(len(model_source_df))

    return {
        "model_id": model_id,
        "formula": formula,
        "fit_method": fit_method,
        "fit_status": fit_status,
        "converged": False,
        "rows_before_exclusion": rows_before_exclusion,
        "rows_excluded_score_margin": rows_excluded_score_margin,
        "rows_excluded_intentional": rows_excluded_intentional,
        "rows_excluded_total": rows_excluded_total,
        "rows_before_model": rows_before_model,
        "rows_dropped_missing_controls": 0,
        "rows_used_in_model": 0,
        "n1_count_L_t_eq_1": int(model_source_df["L_t"].eq(1).sum()) if "L_t" in model_source_df.columns else 0,
        "n0_count_L_t_eq_0": int(model_source_df["L_t"].eq(0).sum()) if "L_t" in model_source_df.columns else 0,
        "mean_M_t_where_L_t_eq_1": None,
        "mean_M_t_where_L_t_eq_0": None,
        "adjusted_mean_M_t_if_L_t_eq_1": None,
        "adjusted_mean_M_t_if_L_t_eq_0": None,
        "WMI_controlled": None,
        "beta_L_t": None,
        "irr_L_t": None,
        "std_err_L_t": None,
        "p_value_L_t": None,
        "ci_low_beta_L_t": None,
        "ci_high_beta_L_t": None,
        "ci_low_irr_L_t": None,
        "ci_high_irr_L_t": None,
        "error_message": error_message,
    }


def calculate_wmi_controlled(
    df,
    formula=DEFAULT_CONTROLLED_FORMULA,
    model_id=DEFAULT_MODEL_ID,
):
    required = {
        "period_bucket",
        "offense_team",
        "defense_team",
        "seconds_left_in_game",
        "score_difference",
        "L_t",
        "M_t",
        "score_margin_excluded_t",
        "intentional_foul_excluded_t",
        "controlled_excluded_t",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    rows_before_exclusion = int(len(df))
    rows_excluded_score_margin = int(df["score_margin_excluded_t"].fillna(0).astype(int).sum())
    rows_excluded_intentional = int(df["intentional_foul_excluded_t"].fillna(0).astype(int).sum())
    rows_excluded_total = int(df["controlled_excluded_t"].fillna(0).astype(int).sum())

    model_source_df = df.copy()
    rows_before_model = int(len(model_source_df))
    if model_source_df.empty:
        return _build_failure_result(
            df,
            fit_status="no_rows",
            formula=formula,
            model_id=model_id,
            fit_method=DEFAULT_FIT_METHOD,
        )

    model_df = model_source_df[
        [
            "M_t",
            "L_t",
            "seconds_left_in_game",
            "score_difference",
            "period_bucket",
            "offense_team",
            "defense_team",
        ]
    ].copy()
    model_df = model_df.dropna().reset_index(drop=True)

    rows_dropped_missing_controls = rows_before_model - int(len(model_df))
    if model_df.empty:
        return _build_failure_result(
            df,
            fit_status="no_rows_after_missing_drop",
            formula=formula,
            model_id=model_id,
            fit_method=DEFAULT_FIT_METHOD,
        )

    if model_df["L_t"].nunique() < 2:
        return _build_failure_result(
            df,
            fit_status="no_l_t_variation",
            formula=formula,
            model_id=model_id,
            fit_method=DEFAULT_FIT_METHOD,
        )

    observed_l1 = model_df[model_df["L_t"] == 1]["M_t"]
    observed_l0 = model_df[model_df["L_t"] == 0]["M_t"]
    mean_m_l1 = float(observed_l1.mean()) if not observed_l1.empty else None
    mean_m_l0 = float(observed_l0.mean()) if not observed_l0.empty else None

    try:
        fitted = smf.glm(
            formula=formula,
            data=model_df,
            family=sm.families.Poisson(),
        ).fit()
    except Exception as error:
        return _build_failure_result(
            df,
            fit_status="model_fit_failed",
            formula=formula,
            model_id=model_id,
            fit_method=DEFAULT_FIT_METHOD,
            error_message=str(error),
        )

    if "L_t" not in fitted.params.index:
        return _build_failure_result(
            df,
            fit_status="missing_l_t_coefficient",
            formula=formula,
            model_id=model_id,
            fit_method=DEFAULT_FIT_METHOD,
        )

    pred_l1 = model_df.copy()
    pred_l1["L_t"] = 1
    pred_l0 = model_df.copy()
    pred_l0["L_t"] = 0

    adjusted_mean_l1 = float(np.mean(fitted.predict(pred_l1)))
    adjusted_mean_l0 = float(np.mean(fitted.predict(pred_l0)))
    beta = float(fitted.params["L_t"])
    irr = _safe_exp(beta)
    ci = fitted.conf_int().loc["L_t"]
    ci_low_beta = float(ci.iloc[0])
    ci_high_beta = float(ci.iloc[1])

    result = {
        "model_id": model_id,
        "formula": formula,
        "fit_method": DEFAULT_FIT_METHOD,
        "fit_status": "ok",
        "converged": bool(getattr(fitted, "converged", False)),
        "rows_before_exclusion": rows_before_exclusion,
        "rows_excluded_score_margin": rows_excluded_score_margin,
        "rows_excluded_intentional": rows_excluded_intentional,
        "rows_excluded_total": rows_excluded_total,
        "rows_before_model": rows_before_model,
        "rows_dropped_missing_controls": rows_dropped_missing_controls,
        "rows_used_in_model": int(len(model_df)),
        "n1_count_L_t_eq_1": int((model_df["L_t"] == 1).sum()),
        "n0_count_L_t_eq_0": int((model_df["L_t"] == 0).sum()),
        "mean_M_t_where_L_t_eq_1": mean_m_l1,
        "mean_M_t_where_L_t_eq_0": mean_m_l0,
        "adjusted_mean_M_t_if_L_t_eq_1": adjusted_mean_l1,
        "adjusted_mean_M_t_if_L_t_eq_0": adjusted_mean_l0,
        "WMI_controlled": irr,
        "beta_L_t": beta,
        "irr_L_t": irr,
        "std_err_L_t": float(fitted.bse["L_t"]),
        "p_value_L_t": float(fitted.pvalues["L_t"]),
        "ci_low_beta_L_t": ci_low_beta,
        "ci_high_beta_L_t": ci_high_beta,
        "ci_low_irr_L_t": _safe_exp(ci_low_beta),
        "ci_high_irr_L_t": _safe_exp(ci_high_beta),
        "error_message": None,
    }
    return result
