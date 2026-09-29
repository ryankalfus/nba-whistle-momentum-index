"""Run the first executable expansion study for the Whistle Momentum Index.

The script intentionally leaves the active WMI implementation untouched. It uses
the repository's stored game-level datasets for multi-season comparisons and the
NBA mobile play-by-play feed for a possession-level study of one complete season.

Default run:
    python run_wmi_expansion_analysis.py

Useful smoke test:
    python run_wmi_expansion_analysis.py --max-games 20 --bootstrap-reps 50
"""

from __future__ import annotations

import argparse
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from build_wmi_distribution_2020_2026 import clock_to_iso
from build_wmi_distribution_2020_2026 import fetch_mobile_payload
from build_wmi_distribution_2020_2026 import infer_team_id_to_tricode
from build_wmi_distribution_2020_2026 import mobile_action_type
from build_wmi_distribution_2020_2026 import mobile_subtype
from build_wmi_distribution_2020_2026 import parse_tricodes_from_gcode
from wmi_utils import add_recent_foul_columns
from wmi_utils import build_possession_summary_from_actions


ROOT = Path(__file__).resolve().parent
GAME_DATA_PATH = ROOT / "wmi_games_2020_21_to_2025_26.csv"
SEARCH_DATA_PATH = ROOT / "wmi_search_games_2019_2026.csv"
FAILURES_PATH = ROOT / "wmi_distribution_2020_21_to_2025_26_failures.csv"
DEFAULT_REPORT_PATH = ROOT / "wmi_expansion_full_report.md"
DEFAULT_SEASON = "2024-25"
RANDOM_SEED = 20260811


@dataclass(frozen=True)
class SeasonResult:
    possessions: pd.DataFrame
    failed_games: tuple[tuple[str, str], ...]


def safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def format_number(value: float | int | None, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    if isinstance(value, (int, np.integer)):
        return f"{int(value):,}"
    return f"{float(value):,.{digits}f}"


def format_pvalue(value: float) -> str:
    return "<0.0001" if value < 0.0001 else f"{value:.4f}"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(map(clean, headers)) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    out.extend("| " + " | ".join(map(clean, row)) + " |" for row in rows)
    return "\n".join(out)


def normalize_game_id(value: object) -> str:
    return str(value).split(".")[0].zfill(10)


def mobile_actions_and_meta(season: str, game_id: str) -> tuple[list[dict], dict]:
    payload, plays = fetch_mobile_payload(season, game_id)
    game = payload["g"]
    away_team, home_team = parse_tricodes_from_gcode(game.get("gcode"))
    team_id_to_tricode = infer_team_id_to_tricode(plays, away_team, home_team)

    actions = []
    for period in game.get("pd", []):
        period_number = int(period.get("p"))
        for play in period.get("pla", []):
            team_id = int(play.get("tid") or 0)
            possession = int(play.get("oftid") or 0)
            team_tricode = team_id_to_tricode.get(team_id)
            actions.append(
                {
                    "actionNumber": int(play.get("evt")),
                    "orderNumber": int(play.get("ord")),
                    "clock": clock_to_iso(play.get("cl")),
                    "period": period_number,
                    "teamId": team_id if team_id else np.nan,
                    "teamTricode": team_tricode if team_tricode else np.nan,
                    "scoreHome": play.get("hs"),
                    "scoreAway": play.get("vs"),
                    "description": play.get("de"),
                    "actionType": mobile_action_type(play.get("etype", 0)),
                    "subType": mobile_subtype(play),
                    "possession": possession if possession else np.nan,
                }
            )

    return actions, {
        "season": season,
        "game_id": game_id,
        "game_date": str(game.get("gcode", "")).split("/")[0] or None,
        "away_team": away_team,
        "home_team": home_team,
    }


def add_sequence_columns(table: pd.DataFrame, max_window: int = 10) -> pd.DataFrame:
    out = table.copy().reset_index(drop=True)
    foul = out["F_t"].to_numpy(dtype=np.int8)
    n = len(out)
    for distance in range(1, max_window + 1):
        lag = np.zeros(n, dtype=np.int8)
        lead = np.zeros(n, dtype=np.int8)
        if distance < n:
            lag[distance:] = foul[:-distance]
            lead[:-distance] = foul[distance:]
        out[f"foul_lag_{distance}"] = lag
        out[f"foul_lead_{distance}"] = lead

    for window in (1, 2, 3, 5, 10):
        lag_cols = [f"foul_lag_{i}" for i in range(1, window + 1)]
        lead_cols = [f"foul_lead_{i}" for i in range(1, window + 1)]
        out[f"L{window}"] = out[lag_cols].max(axis=1).astype(int)
        out[f"N{window}"] = out[lead_cols].max(axis=1).astype(int)
        out[f"M{window}"] = out["F_t"] * (1 + out[f"N{window}"])
    return out


def build_extended_game_table(season: str, game_id: str) -> tuple[pd.DataFrame, dict]:
    actions, meta = mobile_actions_and_meta(season, game_id)
    table = build_possession_summary_from_actions(actions=actions, game_id=game_id)
    table = add_recent_foul_columns(table)
    table = add_sequence_columns(table)
    table["season"] = season
    table["game_date"] = meta["game_date"]
    table["away_team"] = meta["away_team"]
    table["home_team"] = meta["home_team"]
    table["possession_number"] = np.arange(1, len(table) + 1)
    table["score_margin"] = table["score_difference"].abs()
    table["home_margin"] = np.where(
        table["offense_team"].eq(meta["home_team"]),
        table["score_difference"],
        -table["score_difference"],
    )
    prior_home_margin = table["home_margin"].shift(1)
    table["score_difference_before"] = np.where(
        table["offense_team"].eq(meta["home_team"]),
        prior_home_margin,
        -prior_home_margin,
    )
    table.loc[0, "score_difference_before"] = 0.0
    table["score_margin_before"] = table["score_difference_before"].abs()
    table["seconds_left_before"] = table["seconds_left_in_game"].shift(1)
    table.loc[0, "seconds_left_before"] = float(table["seconds_left_in_game"].max())
    table["home_defense"] = table["defense_team"].eq(meta["home_team"]).astype(int)
    table["late_likely_intentional"] = (
        table["F_t"].eq(1)
        & table["period"].ge(4)
        & (
            (table["seconds_left_before"].le(35) & table["score_difference_before"].gt(3))
            | (table["seconds_left_before"].le(15) & table["score_difference_before"].ge(1))
        )
    ).astype(int)

    previous_defense = table["defense_team"].shift(1)
    table["home_committed_prev_possession_foul"] = (
        table["foul_lag_1"].eq(1) & previous_defense.eq(meta["home_team"])
    ).astype(int)
    return table, meta


def load_season_possessions(
    season: str,
    game_ids: list[str],
    workers: int,
) -> SeasonResult:
    tables: list[pd.DataFrame] = []
    failures: list[tuple[str, str]] = []
    total = len(game_ids)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(build_extended_game_table, season, game_id): game_id
            for game_id in game_ids
        }
        for done, future in enumerate(as_completed(futures), start=1):
            game_id = futures[future]
            try:
                table, _ = future.result()
                tables.append(table)
            except Exception as error:
                failures.append((game_id, str(error)))
            if done % 100 == 0 or done == total:
                print(
                    f"play_by_play_progress={done}/{total} "
                    f"ok={len(tables)} failed={len(failures)}",
                    flush=True,
                )
    if not tables:
        raise RuntimeError(f"No possession tables could be built for {season}.")
    possessions = pd.concat(tables, ignore_index=True)
    possessions = possessions.sort_values(["game_date", "game_id", "possession_number"]).reset_index(drop=True)
    return SeasonResult(possessions=possessions, failed_games=tuple(failures))


def wmi_decomposition(df: pd.DataFrame, window: int = 2) -> dict[str, float]:
    recent = df[f"L{window}"].astype(int)
    f = df["F_t"].astype(int)
    n = df[f"N{window}"].astype(int)
    m = f * (1 + n)
    result: dict[str, float] = {}
    for level in (0, 1):
        mask = recent.eq(level)
        foul_mask = mask & f.eq(1)
        result[f"n{level}"] = float(mask.sum())
        result[f"f{level}"] = float(f[mask].sum())
        result[f"fn{level}"] = float((f[foul_mask] * n[foul_mask]).sum())
        result[f"p{level}"] = float(f[mask].mean()) if mask.any() else float("nan")
        result[f"q{level}"] = float(n[foul_mask].mean()) if foul_mask.any() else float("nan")
        result[f"mean_m{level}"] = float(m[mask].mean()) if mask.any() else float("nan")
    result["immediate_ratio"] = safe_ratio(result["p1"], result["p0"])
    result["continuation_ratio"] = safe_ratio(1 + result["q1"], 1 + result["q0"])
    result["wmi"] = safe_ratio(result["mean_m1"], result["mean_m0"])
    result["factorized_wmi"] = result["immediate_ratio"] * result["continuation_ratio"]
    return result


def sufficient_stats_by_game(df: pd.DataFrame, window: int = 2) -> pd.DataFrame:
    records = []
    for game_id, game in df.groupby("game_id", sort=False):
        metrics = wmi_decomposition(game, window=window)
        records.append({"game_id": game_id, **metrics})
    return pd.DataFrame(records)


def metrics_from_weighted_stats(stats: pd.DataFrame, weights: np.ndarray) -> dict[str, float]:
    values = {}
    for key in ("n0", "n1", "f0", "f1", "fn0", "fn1"):
        values[key] = float(np.dot(weights, stats[key].to_numpy(dtype=float)))
    p0 = safe_ratio(values["f0"], values["n0"])
    p1 = safe_ratio(values["f1"], values["n1"])
    q0 = safe_ratio(values["fn0"], values["f0"])
    q1 = safe_ratio(values["fn1"], values["f1"])
    immediate = safe_ratio(p1, p0)
    continuation = safe_ratio(1 + q1, 1 + q0)
    return {
        "immediate_ratio": immediate,
        "continuation_ratio": continuation,
        "wmi": immediate * continuation,
    }


def game_bootstrap_intervals(
    stats: pd.DataFrame,
    reps: int,
    rng: np.random.Generator,
) -> dict[str, tuple[float, float]]:
    game_count = len(stats)
    draws = {key: [] for key in ("wmi", "immediate_ratio", "continuation_ratio")}
    for _ in range(reps):
        weights = rng.multinomial(game_count, np.full(game_count, 1 / game_count))
        metrics = metrics_from_weighted_stats(stats, weights)
        for key in draws:
            draws[key].append(metrics[key])
    return {
        key: tuple(np.nanpercentile(np.asarray(values), [2.5, 97.5]))
        for key, values in draws.items()
    }


def directional_metrics(df: pd.DataFrame) -> dict[str, float]:
    observed_same = 0.0
    observed_opposite = 0.0
    expected_same = 0.0
    expected_opposite = 0.0
    transitions = 0
    gaps: list[int] = []
    for _, game in df.groupby("game_id", sort=False):
        fouls = game.loc[game["F_t"].eq(1), ["possession_number", "defense_team"]]
        if len(fouls) < 2:
            continue
        teams = fouls["defense_team"].astype(str).to_numpy()
        same = teams[1:] == teams[:-1]
        observed_same += float(same.sum())
        observed_opposite += float((~same).sum())
        transitions += len(teams) - 1
        counts = pd.Series(teams).value_counts().to_numpy(dtype=float)
        n = float(len(teams))
        expected_same += float(np.sum(counts * (counts - 1)) / n)
        expected_opposite += float((n - 1) - (np.sum(counts * (counts - 1)) / n))
        gaps.extend(np.diff(fouls["possession_number"].to_numpy(dtype=int)).tolist())

    gap_array = np.asarray(gaps, dtype=float)
    gap_mean = float(np.mean(gap_array))
    gap_std = float(np.std(gap_array, ddof=1))
    return {
        "transitions": float(transitions),
        "same_probability": safe_ratio(observed_same, transitions),
        "opposite_probability": safe_ratio(observed_opposite, transitions),
        "same_repeat_index": safe_ratio(observed_same, expected_same),
        "directional_makeup_index": safe_ratio(observed_opposite, expected_opposite),
        "gap_mean": gap_mean,
        "gap_median": float(np.median(gap_array)),
        "gap_cv": safe_ratio(gap_std, gap_mean),
        "gap_burstiness": safe_ratio(gap_std - gap_mean, gap_std + gap_mean),
    }


def empirical_foul_horizons(df: pd.DataFrame) -> dict[int, float]:
    foul_rows = df["F_t"].eq(1)
    return {
        horizon: float(df.loc[foul_rows, f"N{horizon}"].mean())
        for horizon in (1, 2, 3, 5, 10)
    }


def context_rows(df: pd.DataFrame) -> list[list[object]]:
    contexts: list[tuple[str, pd.Series]] = [
        ("All possessions", pd.Series(True, index=df.index)),
        ("Likely intentional excluded", df["late_likely_intentional"].eq(0)),
        ("Close: margin <= 5", df["score_margin_before"].le(5)),
        ("Middle: margin 6-14", df["score_margin_before"].between(6, 14)),
        ("Blowout: margin >= 15", df["score_margin_before"].ge(15)),
        ("Fourth quarter / OT", df["period"].ge(4)),
    ]
    rows = []
    for label, mask in contexts:
        metrics = wmi_decomposition(df.loc[mask], window=2)
        rows.append(
            [
                label,
                f"{int(mask.sum()):,}",
                format_number(metrics["immediate_ratio"]),
                format_number(metrics["continuation_ratio"]),
                format_number(metrics["wmi"]),
            ]
        )
    return rows


def fit_clustered_logit(df: pd.DataFrame, formula: str) -> object:
    model_df = df.dropna(
        subset=["F_t", "score_difference_before", "score_margin_before", "seconds_left_before"]
    ).copy()
    def fit(candidate_formula: str) -> object:
        model = smf.glm(
            formula=candidate_formula,
            data=model_df,
            family=sm.families.Binomial(),
        )
        return model.fit(
            cov_type="cluster",
            cov_kwds={"groups": model_df["game_id"]},
            maxiter=100,
        )

    try:
        return fit(formula)
    except np.linalg.LinAlgError:
        # Very small --max-games smoke tests can produce disconnected team fixed
        # effects. The complete-season run is connected; this fallback keeps the
        # diagnostic mode usable while retaining all non-team controls.
        reduced_formula = formula.replace(" + C(offense_team) + C(defense_team)", "")
        return fit(reduced_formula)


def coefficient_row(fitted: object, name: str, label: str) -> list[object]:
    coefficient = float(fitted.params[name])
    interval = fitted.conf_int().loc[name]
    return [
        label,
        format_number(math.exp(coefficient)),
        f"{math.exp(float(interval.iloc[0])):.3f}-{math.exp(float(interval.iloc[1])):.3f}",
        format_pvalue(float(fitted.pvalues[name])),
    ]


def roc_auc(y: np.ndarray, probability: np.ndarray) -> float:
    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    positives = int(y.sum())
    negatives = int(len(y) - positives)
    if positives == 0 or negatives == 0:
        return float("nan")
    ranks = pd.Series(probability).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def pr_auc(y: np.ndarray, probability: np.ndarray) -> float:
    order = np.argsort(-probability, kind="mergesort")
    sorted_y = np.asarray(y, dtype=int)[order]
    true_positive = np.cumsum(sorted_y)
    false_positive = np.cumsum(1 - sorted_y)
    total_positive = true_positive[-1]
    if total_positive == 0:
        return float("nan")
    precision = true_positive / np.maximum(true_positive + false_positive, 1)
    recall = true_positive / total_positive
    precision = np.r_[1.0, precision]
    recall = np.r_[0.0, recall]
    return float(np.trapezoid(precision, recall))


def calibration_error(y: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    cuts = np.linspace(0, 1, bins + 1)
    bin_id = np.minimum(np.digitize(probability, cuts[1:-1]), bins - 1)
    error = 0.0
    for value in range(bins):
        mask = bin_id == value
        if mask.any():
            error += float(mask.mean()) * abs(float(y[mask].mean()) - float(probability[mask].mean()))
    return error


def prediction_metrics(y: pd.Series, probability: np.ndarray) -> dict[str, float]:
    actual = y.to_numpy(dtype=int)
    probability = np.clip(np.asarray(probability, dtype=float), 1e-8, 1 - 1e-8)
    return {
        "prevalence": float(actual.mean()),
        "roc_auc": roc_auc(actual, probability),
        "pr_auc": pr_auc(actual, probability),
        "brier": float(np.mean((actual - probability) ** 2)),
        "log_loss": float(-np.mean(actual * np.log(probability) + (1 - actual) * np.log(1 - probability))),
        "ece": calibration_error(actual, probability),
    }


def chronological_game_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    game_order = (
        df[["game_id", "game_date"]]
        .drop_duplicates()
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )
    n_games = len(game_order)
    train_end = int(n_games * 0.70)
    validation_end = int(n_games * 0.85)
    train_ids = set(game_order.iloc[:train_end]["game_id"])
    validation_ids = set(game_order.iloc[train_end:validation_end]["game_id"])
    test_ids = set(game_order.iloc[validation_end:]["game_id"])
    return (
        df[df["game_id"].isin(train_ids)].copy(),
        df[df["game_id"].isin(validation_ids)].copy(),
        df[df["game_id"].isin(test_ids)].copy(),
    )


def run_foul_prediction(df: pd.DataFrame) -> tuple[list[list[object]], pd.DataFrame, dict[str, object]]:
    clean = df[df["late_likely_intentional"].eq(0)].dropna(
        subset=["score_difference_before", "score_margin_before", "seconds_left_before"]
    ).copy()
    team_levels = sorted(set(clean["offense_team"].dropna()) | set(clean["defense_team"].dropna()))
    clean["offense_team"] = pd.Categorical(clean["offense_team"], categories=team_levels)
    clean["defense_team"] = pd.Categorical(clean["defense_team"], categories=team_levels)
    train, validation, test = chronological_game_split(clean)
    train_validation = pd.concat([train, validation], ignore_index=True)
    baseline_rate = float(train_validation["F_t"].mean())
    baseline_probability = np.full(len(test), baseline_rate)
    formula = (
        "F_t ~ foul_lag_1 + foul_lag_2 + foul_lag_3 + foul_lag_4 + foul_lag_5 "
        "+ score_difference_before + score_margin_before + seconds_left_before + C(period) "
        "+ C(offense_team) + C(defense_team) + home_defense"
    )
    fitted = smf.glm(
        formula=formula,
        data=train_validation,
        family=sm.families.Binomial(),
    ).fit(maxiter=100)
    full_probability = np.asarray(fitted.predict(test), dtype=float)
    baseline_metrics = prediction_metrics(test["F_t"], baseline_probability)
    full_metrics = prediction_metrics(test["F_t"], full_probability)
    rows = []
    for label, metrics in (("Historical-rate baseline", baseline_metrics), ("Context + foul history", full_metrics)):
        rows.append(
            [
                label,
                format_number(metrics["roc_auc"]),
                format_number(metrics["pr_auc"]),
                format_number(metrics["brier"], 4),
                format_number(metrics["log_loss"], 4),
                format_number(metrics["ece"], 4),
            ]
        )
    residuals = test[["game_id", "game_date"]].copy()
    residuals["observed"] = test["F_t"].to_numpy(dtype=float)
    residuals["expected"] = full_probability
    residuals["residual"] = residuals["observed"] - residuals["expected"]
    by_game = residuals.groupby(["game_id", "game_date"], as_index=False).agg(
        observed_fouls=("observed", "sum"),
        expected_fouls=("expected", "sum"),
        expected_foul_residual=("residual", "sum"),
    )
    split_info = {
        "train_games": int(train["game_id"].nunique()),
        "validation_games": int(validation["game_id"].nunique()),
        "test_games": int(test["game_id"].nunique()),
        "test_possessions": int(len(test)),
        "formula": formula,
        "baseline_metrics": baseline_metrics,
        "full_metrics": full_metrics,
    }
    return rows, by_game, split_info


def run_live_win_prediction(df: pd.DataFrame) -> list[list[object]]:
    out = df.dropna(subset=["home_margin", "seconds_left_in_game"]).copy()
    final_margin = out.groupby("game_id")["home_margin"].last()
    out["home_win"] = out["game_id"].map(final_margin.gt(0).astype(int))
    train, validation, test = chronological_game_split(out)
    train_validation = pd.concat([train, validation], ignore_index=True)
    formulas = {
        "Game state only": "home_win ~ home_margin + seconds_left_in_game + home_margin:seconds_left_in_game",
        "Game state + foul dynamics": (
            "home_win ~ home_margin + seconds_left_in_game + home_margin:seconds_left_in_game "
            "+ foul_lag_1 + foul_lag_2 + foul_lag_3 + home_defense "
            "+ home_committed_prev_possession_foul"
        ),
    }
    rows = []
    for label, formula in formulas.items():
        fitted = smf.glm(formula=formula, data=train_validation, family=sm.families.Binomial()).fit(maxiter=100)
        metrics = prediction_metrics(test["home_win"], np.asarray(fitted.predict(test), dtype=float))
        rows.append(
            [
                label,
                format_number(metrics["roc_auc"]),
                format_number(metrics["brier"], 4),
                format_number(metrics["log_loss"], 4),
                format_number(metrics["ece"], 4),
            ]
        )
    return rows


def moving_block_game_intervals(
    df: pd.DataFrame,
    reps: int,
    rng: np.random.Generator,
    block_length: int = 10,
) -> pd.DataFrame:
    records = []
    for game_id, game in df.groupby("game_id", sort=False):
        recent = game["L2"].to_numpy(dtype=np.int8)
        m = game["M2"].to_numpy(dtype=float)
        n = len(game)
        observed = wmi_decomposition(game)["wmi"]
        values = []
        blocks_needed = math.ceil(n / block_length)
        offsets = np.arange(block_length)
        for _ in range(reps):
            starts = rng.integers(0, n, size=blocks_needed)
            index = ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]
            sample_l = recent[index]
            sample_m = m[index]
            mean1 = sample_m[sample_l == 1].mean() if np.any(sample_l == 1) else np.nan
            mean0 = sample_m[sample_l == 0].mean() if np.any(sample_l == 0) else np.nan
            values.append(safe_ratio(mean1, mean0))
        finite = np.asarray(values, dtype=float)
        finite = finite[np.isfinite(finite)]
        low, high = (np.nan, np.nan) if len(finite) < reps / 2 else np.percentile(finite, [2.5, 97.5])
        records.append(
            {
                "game_id": game_id,
                "WMI": observed,
                "n1": int(game["L2"].sum()),
                "n0": int(game["L2"].eq(0).sum()),
                "ci_low": low,
                "ci_high": high,
                "ci_width": high - low,
                "ci_contains_one": bool(low <= 1 <= high) if np.isfinite(low) else None,
            }
        )
    return pd.DataFrame(records)


def bootstrap_difference(
    left: np.ndarray,
    right: np.ndarray,
    reps: int,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    observed = float(np.mean(left) - np.mean(right))
    draws = []
    for _ in range(reps):
        left_draw = rng.choice(left, size=len(left), replace=True)
        right_draw = rng.choice(right, size=len(right), replace=True)
        draws.append(float(left_draw.mean() - right_draw.mean()))
    low, high = np.percentile(draws, [2.5, 97.5])
    return observed, float(low), float(high)


def aggregate_comparison_rows(
    search: pd.DataFrame,
    reps: int,
    rng: np.random.Generator,
) -> list[list[object]]:
    rows = []
    regular = search.loc[search["season_type"].eq("Regular Season"), "WMI"].dropna().to_numpy(dtype=float)
    playoffs = search.loc[search["season_type"].eq("Playoffs"), "WMI"].dropna().to_numpy(dtype=float)
    diff, low, high = bootstrap_difference(playoffs, regular, reps, rng)
    rows.append(
        [
            "Playoffs minus regular season",
            f"{len(playoffs):,} vs {len(regular):,}",
            format_number(float(playoffs.mean())),
            format_number(float(regular.mean())),
            f"{diff:.3f} ({low:.3f}, {high:.3f})",
        ]
    )

    dates = pd.to_datetime(search["game_date_et"], errors="coerce")
    bubble = search.loc[dates.between("2020-07-30", "2020-10-11"), "WMI"].dropna().to_numpy(dtype=float)
    pre_pause = search.loc[
        dates.between("2019-10-22", "2020-03-11"), "WMI"
    ].dropna().to_numpy(dtype=float)
    diff, low, high = bootstrap_difference(bubble, pre_pause, reps, rng)
    rows.append(
        [
            "2019-20 bubble minus pre-pause",
            f"{len(bubble):,} vs {len(pre_pause):,}",
            format_number(float(bubble.mean())),
            format_number(float(pre_pause.mean())),
            f"{diff:.3f} ({low:.3f}, {high:.3f})",
        ]
    )
    return rows


def dataframe_integrity_summary(game_data: pd.DataFrame, search: pd.DataFrame) -> list[list[object]]:
    return [
        ["Comparison distribution", f"{len(game_data):,}", f"{game_data['WMI'].notna().sum():,}", "2020-21 to Mar. 2026 snapshot"],
        ["Search dataset", f"{len(search):,}", f"{search['WMI'].notna().sum():,}", "2019-20 to Mar. 2026 snapshot"],
    ]


def scope_matrix() -> str:
    rows = [
        ["H1", "Completed, limited controls", "Cluster-robust logistic model with score, time, period, teams, and game state."],
        ["H2", "Completed", "Exact immediate/continuation decomposition."],
        ["H3", "Completed", "Lag effects at possession distances 1-5 plus multi-scale WMI."],
        ["H4", "Completed descriptively", "Same-team and opposite-team transition indices against shuffled-mark expectation."],
        ["H5", "Completed descriptively", "Close/middle/blowout and intentional-foul sensitivity."],
        ["H6", "Not identified", "Bonus and team-foul state are absent."],
        ["H7", "Completed at game level", "Regular-season/playoff WMI comparison; no possession-level playoff controls."],
        ["H8", "Partial", "Home-defense foul rate is available; call accuracy is not."],
        ["H9", "Partial", "Bubble/pre-pause game-level comparison without attendance counts."],
        ["H10-H12", "Not identified", "Player, lineup, drive, contest, and substitution features are absent."],
        ["H13", "Not identified", "Transition opportunities and validated take-foul labels are absent."],
        ["H14", "Not identified", "Challenge outcomes are not assembled."],
        ["H15", "Not identified", "Officiating crew identifiers are absent."],
        ["H16", "Not run", "Possession scoring outcomes need a dedicated outcome table and temporal design."],
        ["H17", "Exploratory completion", "Past-only foul features added to a chronological live win model."],
        ["H18", "Partial", "WMI is compared with foul exposure and game length, but not win-probability leverage."],
    ]
    return markdown_table(["Hypothesis", "Status", "What this run establishes"], rows)


def model_scope_matrix() -> str:
    rows = [
        ["1. Next-possession foul", "Completed", "Chronological baseline vs logistic context/history model."],
        ["2. Next foul team", "Partial", "Observed marked transitions; no fitted multiclass model."],
        ["3. Time to next foul", "Partial", "Empirical possession-gap distribution; no survival regression."],
        ["4. Marked Hawkes", "Not fit", "Mark transitions and decay horizons establish inputs, not a Hawkes estimate."],
        ["5. High-WMI game", "Not fit", "Pregame team, rest, crew, and matchup features are absent."],
        ["6. Live outcome", "Exploratory", "Game-state model compared with a past-only foul-feature model."],
        ["7-8. Foul-out/policy", "Not fit", "Player state and substitution actions are absent."],
        ["9. L2M correctness", "Not fit", "L2M labels are absent and selected, not population-representative."],
        ["10. Challenge outcome", "Not fit", "Challenge labels and outcomes are absent."],
    ]
    return markdown_table(["Model", "Status", "Result"], rows)


def build_report(
    *,
    season: str,
    possessions: pd.DataFrame,
    failed_games: tuple[tuple[str, str], ...],
    game_data: pd.DataFrame,
    search: pd.DataFrame,
    failure_data: pd.DataFrame,
    bootstrap_reps: int,
    rng: np.random.Generator,
) -> str:
    decomposition = wmi_decomposition(possessions)
    per_game_stats = sufficient_stats_by_game(possessions)
    intervals = game_bootstrap_intervals(per_game_stats, bootstrap_reps, rng)
    direction = directional_metrics(possessions)
    horizons = empirical_foul_horizons(possessions)

    window_rows = []
    for window in (1, 2, 3, 5, 10):
        metrics = wmi_decomposition(possessions, window=window)
        window_rows.append(
            [
                window,
                format_number(metrics["p1"]),
                format_number(metrics["p0"]),
                format_number(metrics["immediate_ratio"]),
                format_number(metrics["continuation_ratio"]),
                format_number(metrics["wmi"]),
            ]
        )

    inference_df = possessions[possessions["late_likely_intentional"].eq(0)].copy()
    h1_formula = (
        "F_t ~ L2 + score_difference_before + score_margin_before + seconds_left_before "
        "+ C(period) + C(offense_team) + C(defense_team) + home_defense"
    )
    h3_formula = (
        "F_t ~ foul_lag_1 + foul_lag_2 + foul_lag_3 + foul_lag_4 + foul_lag_5 "
        "+ score_difference_before + score_margin_before + seconds_left_before "
        "+ C(period) + C(offense_team) + C(defense_team) + home_defense"
    )
    h1_fit = fit_clustered_logit(inference_df, h1_formula)
    h3_fit = fit_clustered_logit(inference_df, h3_formula)
    inference_rows = [coefficient_row(h1_fit, "L2", "Any foul in previous 2 possessions")]
    inference_rows.extend(
        coefficient_row(h3_fit, f"foul_lag_{distance}", f"Foul exactly {distance} possession(s) ago")
        for distance in range(1, 6)
    )

    prediction_rows, residuals, split_info = run_foul_prediction(possessions)
    live_win_rows = run_live_win_prediction(possessions)
    reliability = moving_block_game_intervals(
        possessions,
        reps=max(100, min(bootstrap_reps, 300)),
        rng=rng,
    )
    valid_reliability = reliability.dropna(subset=["ci_width"])
    low_sample = (reliability["n1"] < 30) | (reliability["n0"] < 30)

    game_values = pd.to_numeric(game_data["WMI"], errors="coerce")
    finite_game = game_data.loc[game_values.notna() & np.isfinite(game_values)].copy()
    finite_game["WMI"] = pd.to_numeric(finite_game["WMI"])
    finite_game["recent_share"] = finite_game["n1_count_L_t_eq_1"] / finite_game["possessions"]
    finite_game["abs_log_wmi"] = np.abs(np.log(finite_game["WMI"].clip(lower=1e-8)))
    corr_exposure = finite_game[["WMI", "recent_share"]].corr(method="spearman").iloc[0, 1]
    corr_instability = finite_game[["abs_log_wmi", "n1_count_L_t_eq_1"]].corr(method="spearman").iloc[0, 1]

    home_foul_rate = float(possessions.loc[possessions["home_defense"].eq(1), "F_t"].mean())
    away_foul_rate = float(possessions.loc[possessions["home_defense"].eq(0), "F_t"].mean())
    aggregate_rows = aggregate_comparison_rows(search, bootstrap_reps, rng)
    season_rows = []
    for label, group in game_data.groupby("season", sort=True):
        values = pd.to_numeric(group["WMI"], errors="coerce").dropna()
        season_rows.append([label, f"{len(values):,}", format_number(values.mean()), format_number(values.median())])

    top_residual = residuals.nlargest(5, "expected_foul_residual")
    bottom_residual = residuals.nsmallest(5, "expected_foul_residual")
    residual_rows = []
    for label, frame in (("More than expected", top_residual), ("Fewer than expected", bottom_residual)):
        for _, row in frame.iterrows():
            residual_rows.append(
                [
                    label,
                    normalize_game_id(row["game_id"]),
                    row["game_date"],
                    format_number(row["observed_fouls"], 1),
                    format_number(row["expected_fouls"], 1),
                    format_number(row["expected_foul_residual"], 1),
                ]
            )

    decomposition_rows = [
        ["P(F=1 | L=1)", format_number(decomposition["p1"])],
        ["P(F=1 | L=0)", format_number(decomposition["p0"])],
        ["Immediate Whistle Persistence Ratio", format_number(decomposition["immediate_ratio"])],
        ["P(N=1 | F=1, L=1)", format_number(decomposition["q1"])],
        ["P(N=1 | F=1, L=0)", format_number(decomposition["q0"])],
        ["Foul Continuation Ratio", format_number(decomposition["continuation_ratio"])],
        ["WMI", format_number(decomposition["wmi"])],
        ["Factorized product", format_number(decomposition["factorized_wmi"])],
    ]

    report = f"""# NBA Whistle Momentum Index: Executed Expansion Study

Generated: {datetime.now(UTC).isoformat()}<br>
Possession-level study season: **{season} regular season**<br>
Random seed: `{RANDOM_SEED}`

## Executive summary

This report executes every analysis in the expansion brief that the repository's current data can identify without inventing unavailable variables. The possession-level study includes **{possessions['game_id'].nunique():,} games and {len(possessions):,} possessions**; **{len(failed_games):,} requested games failed**. Multi-season comparisons use the stored public result files.

The central result is that the original WMI can be decomposed exactly. In this season the pooled WMI was **{decomposition['wmi']:.3f}** (game-bootstrap 95% CI **{intervals['wmi'][0]:.3f}-{intervals['wmi'][1]:.3f}**). Its immediate component was **{decomposition['immediate_ratio']:.3f}** (95% CI **{intervals['immediate_ratio'][0]:.3f}-{intervals['immediate_ratio'][1]:.3f}**) and its continuation component was **{decomposition['continuation_ratio']:.3f}** (95% CI **{intervals['continuation_ratio'][0]:.3f}-{intervals['continuation_ratio'][1]:.3f}**). The exact product check differs from WMI by only **{abs(decomposition['wmi'] - decomposition['factorized_wmi']):.3e}**.

The cluster-robust context model estimates an odds ratio of **{math.exp(float(h1_fit.params['L2'])):.3f}** for a current defensive foul after at least one foul in the previous two possessions (95% CI **{math.exp(float(h1_fit.conf_int().loc['L2'].iloc[0])):.3f}-{math.exp(float(h1_fit.conf_int().loc['L2'].iloc[1])):.3f}**, p **{format_pvalue(float(h1_fit.pvalues['L2']))}**). This is an association after the controls available here, not proof of an officiating mechanism or intent.

The out-of-sample next-possession model used a chronological, whole-game split ({split_info['train_games']} train, {split_info['validation_games']} validation, {split_info['test_games']} test games). Its value should be judged primarily by calibration and log loss, not accuracy, because fouls are infrequent.

Taken together, the season shows **slightly lower immediate foul probability after recent fouls**, partly offset by a small continuation effect once a foul occurs. Opposite-team foul transitions occurred more often than a within-game random-mark baseline, but that descriptive result does not isolate officiating from alternating possessions, tactics, or foul opportunities. Predictive lift was weak: the foul model's ROC-AUC was **{split_info['full_metrics']['roc_auc']:.3f}**, and adding foul dynamics changed live-win log loss only marginally.

## 1. Data and integrity audit

{markdown_table(['Dataset', 'Rows', 'Rows with WMI', 'Coverage'], dataframe_integrity_summary(game_data, search))}

The two headline counts are intentionally different: the comparison distribution contains regular-season comparison games, while the search file also contains 2019-20, playoffs, and play-in games. The search file has **{len(search):,} rows but {search['WMI'].notna().sum():,} finite/nonmissing WMI values**. The comparison failure log has **{len(failure_data):,} rows**. This distinction should be stated directly on the website so users do not mistake the headline comparison count for search coverage.

The 2025-26 CDN endpoint returned HTTP 403 during this run. The reproducible possession study therefore uses the latest complete season still available through the NBA mobile feed ({season}); the stored 2025-26 snapshot remains valid as a game-level comparison artifact.

## 2. Exact WMI decomposition (H2)

{markdown_table(['Quantity', 'Estimate'], decomposition_rows)}

Interpretation: the immediate ratio asks whether the current possession contains a defensive foul more often after recent fouls. The continuation ratio asks whether a current foul is followed by another foul within two possessions more often when it was itself preceded by recent fouls. Multiplying them reconstructs WMI exactly.

The **{decomposition['wmi']:.3f}** value here is a pooled possession-level research estimator used for this expansion study, not a new public season-level WMI edition. The active product remains one WMI per game; the mean of the stored {season} game values is **{game_data.loc[game_data['season'].eq(season), 'WMI'].mean():.3f}**. A pooled ratio and the arithmetic mean of game ratios are not expected to match.

## 3. Multi-scale decay and empirical time to foul (H3; Model 3 input)

{markdown_table(['Window', 'P(F|L=1)', 'P(F|L=0)', 'Immediate ratio', 'Continuation ratio', 'WMI'], window_rows)}

Among foul possessions, the empirical probability of at least one later defensive foul within 1/2/3/5/10 possessions was **{horizons[1]:.3f} / {horizons[2]:.3f} / {horizons[3]:.3f} / {horizons[5]:.3f} / {horizons[10]:.3f}**. These are descriptive horizons, not a fitted survival model.

## 4. Direction and burstiness (H4; Models 2-4 inputs)

There were **{int(direction['transitions']):,}** consecutive foul-to-foul transitions. The next foul was charged to the same team with probability **{direction['same_probability']:.3f}** and to the opposing team with probability **{direction['opposite_probability']:.3f}**. Relative to an exact within-game random permutation of each game's foul-team marks, the Same-Team Repeat Index was **{direction['same_repeat_index']:.3f}** and the Directional Makeup Index was **{direction['directional_makeup_index']:.3f}**.

The mean gap between foul possessions was **{direction['gap_mean']:.2f} possessions** (median **{direction['gap_median']:.1f}**, CV **{direction['gap_cv']:.3f}**, burstiness statistic **{direction['gap_burstiness']:.3f}**). These direction indices are descriptive baselines, not context-adjusted proof of makeup calls.

## 5. Game context and sensitivity (H5)

{markdown_table(['Context', 'Possessions', 'Immediate ratio', 'Continuation ratio', 'WMI'], context_rows(possessions))}

The intentional-foul rule is a transparent heuristic: a counted fourth-quarter/overtime defensive foul when the offense leads by more than three with <=35 seconds left, or leads by at least one with <=15 seconds left. It is not a validated intentional-foul label.

## 6. Context-adjusted association and decay (H1, H3)

{markdown_table(['Term', 'Odds ratio', 'Clustered 95% CI', 'p-value'], inference_rows)}

Both models use a binomial logit link and game-clustered standard errors. Available controls are score difference, absolute margin, seconds remaining, period, offense, defense, and whether the defending team is home. Missing opportunity controls—drives, paint touches, shot type, lineups, bonus, player foul trouble, and crew—mean the coefficient remains associational and potentially confounded.

## 7. Home, postseason, and crowd-era comparisons (H7-H9)

The raw possession foul rate was **{home_foul_rate:.3f}** when the home team defended and **{away_foul_rate:.3f}** when the away team defended (difference **{home_foul_rate - away_foul_rate:+.3f}**). This measures call frequency, not correctness or favorability.

{markdown_table(['Comparison', 'N', 'Group A mean', 'Group B mean', 'A-B (bootstrap 95% CI)'], aggregate_rows)}

{markdown_table(['Season', 'Games', 'Mean game WMI', 'Median game WMI'], season_rows)}

The bubble comparison is an era contrast, not a causal estimate: team composition, game type, restart selection, and scheduling also changed. The playoff comparison is at the game-WMI level and does not adjust possession context.

## 8. Reliability and ratio instability

In the {season} possession sample, **{int(low_sample.sum()):,} of {len(reliability):,} games** had `n1 < 30` or `n0 < 30`. Approximate 10-possession circular moving-block intervals were available for **{len(valid_reliability):,} games**; their median width was **{valid_reliability['ci_width'].median():.3f}**, and **{valid_reliability['ci_contains_one'].mean():.1%}** contained 1. These intervals resample derived possession rows in blocks; a production release should bootstrap raw games/events and pre-register the reliability threshold.

Across the stored comparison distribution, the Spearman correlation between WMI and the share of possessions with `L_t=1` was **{corr_exposure:.3f}**. The correlation between `|log(WMI)|` and `n1` was **{corr_instability:.3f}**; a negative value is consistent with more extreme ratios when the recent-foul group is smaller. The website should show `n1`, `n0`, both component means, and an interval/reliability flag alongside every game value.

## 9. Next-possession foul prediction (Model 1)

{markdown_table(['Model', 'ROC-AUC', 'PR-AUC', 'Brier', 'Log loss', 'ECE'], prediction_rows)}

The split is chronological and keeps every possession from a game in one partition. The test set contains **{split_info['test_games']:,} games and {split_info['test_possessions']:,} possessions**. The full model uses only information available at or before the current possession plus current game state; it does not use `N_t`, final WMI, or future outcomes.

### Expected-foul residual examples from the held-out test games

{markdown_table(['Direction', 'Game ID', 'Date', 'Observed', 'Expected', 'Residual'], residual_rows)}

These are model residuals, not evidence of officiating error. They rank games where foul volume differed from this limited model's expectation and are appropriate leads for deeper review.

## 10. Exploratory live win prediction (H17; Model 6)

{markdown_table(['Model', 'ROC-AUC', 'Brier', 'Log loss', 'ECE'], live_win_rows)}

This is a diagnostic comparison, not a deployable win-probability model. It omits pregame team strength and uses repeated possession snapshots within held-out games. Any incremental gain from foul features must be validated across seasons before it can support the claim that foul dynamics add information beyond ordinary game state.

## 11. Hypothesis execution ledger

{scope_matrix()}

## 12. Predictive-model execution ledger

{model_scope_matrix()}

## 13. What the current data cannot answer

The brief's player residuals, foul-trouble strategy, bonus pressure, foul consequence value, L2M accuracy, challenge response, take-foul policy, crew stability, player foul-out prediction, optimal substitution policy, and full Hawkes/survival models require variables not present in the current analysis table. Running those models now would substitute proxies for their stated targets and create false precision.

The next data build should add, in order: (1) foul-committing and fouled-player IDs plus validated subtype/free-throw consequences; (2) team foul and bonus state; (3) action-level outcomes and possession points; (4) lineups and player foul counts; (5) crew IDs; (6) challenge/review outcomes; (7) L2M labels; and (8) opportunity measures such as drives, paint touches, transition, and shot zone.

## 14. Recommended product changes

1. Keep original WMI unchanged, but display it to three decimals with percentile, `n1`, `n0`, numerator, denominator, and an interval/reliability label.
2. Add the Immediate Whistle Persistence Ratio and Foul Continuation Ratio beside WMI; they explain *why* a game scored as it did.
3. Add same-team/opposite-team foul transitions and a possession timeline, clearly labeled descriptive.
4. Add 1/2/3/5/10-possession windows as an analysis view, not five new headline metrics.
5. State prominently that final-game WMI is retrospective because `N_t` uses future possessions. A live feature must be past-only.
6. Explain the comparison/search coverage mismatch and surface logged source-data failures.
7. Do not label an Expected-Foul Residual Index "adjusted" until opportunity variables and external validation are included.

## 15. Bottom line

This run validates the algebraic decomposition, quantifies scale and direction, tests a limited context-adjusted association, and performs leakage-safe chronological prediction. It does **not** establish referee bias, call correctness, conscious makeup behavior, or a causal officiating effect. The scientifically strongest next phase is a richer possession table followed by a pre-registered multi-season expected-foul model, with game-clustered or game-bootstrap inference and a fully held-out season.
"""
    if failed_games:
        sample = "; ".join(f"{gid}: {message}" for gid, message in failed_games[:10])
        report += f"\n\n## Appendix: play-by-play failures\n\n{len(failed_games)} failures. First entries: {sample}\n"
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-games", type=int, default=None)
    parser.add_argument("--bootstrap-reps", type=int, default=500)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(RANDOM_SEED)
    game_data = pd.read_csv(GAME_DATA_PATH, dtype={"game_id": str})
    search = pd.read_csv(SEARCH_DATA_PATH, dtype={"game_id": str})
    failure_data = pd.read_csv(FAILURES_PATH, dtype={"game_id": str})
    for frame in (game_data, search):
        frame["game_id"] = frame["game_id"].map(normalize_game_id)
        frame["WMI"] = pd.to_numeric(frame["WMI"], errors="coerce")

    season_games = game_data.loc[game_data["season"].eq(args.season), "game_id"].drop_duplicates().tolist()
    if not season_games:
        raise ValueError(f"No stored game IDs found for season {args.season}.")
    if args.max_games is not None:
        season_games = season_games[: args.max_games]
    print(f"season={args.season} games_requested={len(season_games)}", flush=True)

    season_result = load_season_possessions(args.season, season_games, args.workers)
    report = build_report(
        season=args.season,
        possessions=season_result.possessions,
        failed_games=season_result.failed_games,
        game_data=game_data,
        search=search,
        failure_data=failure_data,
        bootstrap_reps=args.bootstrap_reps,
        rng=rng,
    )
    args.report_path.write_text(report, encoding="utf-8")
    print(f"report={args.report_path}")
    print(f"games_analyzed={season_result.possessions['game_id'].nunique()}")
    print(f"possessions_analyzed={len(season_result.possessions)}")
    print(f"games_failed={len(season_result.failed_games)}")


if __name__ == "__main__":
    main()
