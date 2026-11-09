"""Plan-faithful Stage 5 comparison `plan-stage5-v1`; see docs/PLAN_STAGE5.md.

Model A: L2 logistic regression on the project plan's shared context. Model B:
the identical design plus L_t = 1{F_(t-1)=1 or F_(t-2)=1}. One shared C is chosen
with Model A on the validation season and frozen; each test season refits both
models on all earlier seasons. No scientific gate is satisfied by this module.
"""

from datetime import date
import hashlib
from pathlib import Path
import warnings

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from whistle_research import evaluation, meeting_ab, modeling, team_fouls

SCHEMA = "plan-stage5-v1"
NUMERIC = ("offense_home", "period", "clock", "offense_margin", "clock_squared", "margin_squared", "playoff",
           "defense_team_fouls", "offense_team_fouls", "defense_in_penalty", "offense_in_penalty", "late_close")
CATEGORICAL = ("offense_team_id", "defense_team_id")
HISTORY = "recent_defensive_foul"
MODELS = ("base_rate", "context_a", "history_b")
C_GRID = (0.1, 1.0, 10.0)
MAX_ITER = 2000
CLIP = 1e-6
RESAMPLES = 2000
SEED = 137
LATE_CLOSE_SECONDS = 120.0
LATE_CLOSE_MARGIN = 10
VALIDATION = {"train": ("2020-21",), "evaluate": "2021-22"}
TEST_FOLDS = (
    {"train": ("2020-21", "2021-22"), "evaluate": "2022-23"},
    {"train": ("2020-21", "2021-22", "2022-23"), "evaluate": "2023-24"},
    {"train": ("2020-21", "2021-22", "2022-23", "2023-24"), "evaluate": "2024-25"},
)
SEASON_PARTITION = {"2020-21": "train", "2021-22": "tune", "2022-23": "test", "2023-24": "test", "2024-25": "test"}
FEATURE_FIELDS = ("game_id", "possession_number", "game_type", "period", "clock", "score_difference",
                  "home_defense", "defense_team_id", "offense_team_id", "defense_counted_fouls",
                  "previous_foul_1", "previous_foul_2")
SOURCES = ("plan_stage5.py", "team_fouls.py", "meeting_ab.py", "modeling.py", "evaluation.py",
           "possessions.py", "features.py", "reconcile.py", "sources.py")


def specification():
    """Canonical declaration bound into plans; hashes every module on the data and model path."""
    return {
        "schema": SCHEMA,
        "source_document": "Google Doc project_plan (Crimson Indigo workspace), sections 3 and 5, last edited 2026-10-23",
        "context_numeric": list(NUMERIC),
        "categorical": list(CATEGORICAL),
        "history": "recent_defensive_foul = 1 if previous_foul_1 == 1 or previous_foul_2 == 1 else 0",
        "paired_rows": "first two possessions of each game excluded from both models (meeting_ab.check_lags)",
        "context_definitions": {
            "offense_home": "1 - home_defense",
            "offense_margin": "-score_difference (offense score minus defense score)",
            "clock_squared": "clock seconds squared", "margin_squared": "offense_margin squared",
            "playoff": "1 if game_type == playoffs",
            "team_fouls_and_penalty": "team_fouls.states: NBA Rule 12 B.V quota 4 regulation / 3 overtime, "
                                      "one free foul in the last two minutes, parser event order",
            "late_close": f"period >= 4 and clock <= {LATE_CLOSE_SECONDS} and abs(offense_margin) <= {LATE_CLOSE_MARGIN}",
        },
        "models": list(MODELS),
        "preprocessing": "training-only median imputation with fixed missing indicators for every numeric context "
                         "column; standardize all numeric columns; one-hot teams, unseen teams all zeros",
        "penalty": "l2", "solver": "lbfgs", "max_iter": MAX_ITER, "class_weight": None,
        "C_grid": list(C_GRID),
        "shared_C": "Model A trained on validation train seasons; lowest validation log loss; first grid value "
                    "breaks ties; applied unchanged to both models in every test fold",
        "folds": {"validation": {"train": list(VALIDATION["train"]), "evaluate": VALIDATION["evaluate"]},
                  "test": [{"train": list(f["train"]), "evaluate": f["evaluate"]} for f in TEST_FOLDS]},
        "season_partition": SEASON_PARTITION,
        "probability_clip": [CLIP, 1 - CLIP],
        "primary": "pooled possession-weighted mean of logloss(history_b) - logloss(context_a); negative favors history",
        "bootstrap": {"resamples": RESAMPLES, "seed": SEED, "confidence": 0.95, "interval": "percentile",
                      "pooled": "rng = numpy default_rng(seed); for each test season in fold order, one call "
                                "rng.integers(n_games, size=(resamples, n_games)) on that season's games sorted by "
                                "game_id; per draw, sum of resampled paired game loss sums over all seasons divided "
                                "by sum of resampled game possession counts; numpy quantile (linear) at 0.025, 0.975",
                      "season": "same procedure on one season with rng = numpy default_rng([seed, k]) for test "
                                "fold k = 1, 2, 3"},
        "secondary": ["model log loss", "relative reduction", "paired Brier", "equal-game difference",
                      "ten fixed calibration bins", "calibration intercept with logit offset", "calibration slope",
                      "games, possessions, counted foul events, prevalence", "game-type breakdown"],
        "meaningful_gain": None,
        "sources": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in SOURCES},
    }


def context(row, state):
    """Plan context for one row at the possession-start reference point."""
    clock = row["clock"]
    margin = None if row["score_difference"] is None else -row["score_difference"]
    home = None if row["home_defense"] is None else 1 - row["home_defense"]
    late_close = (None if clock is None or margin is None
                  else int(row["period"] >= 4 and clock <= LATE_CLOSE_SECONDS and abs(margin) <= LATE_CLOSE_MARGIN))
    values = {
        "offense_home": home, "period": row["period"], "clock": clock, "offense_margin": margin,
        "clock_squared": None if clock is None else clock * clock,
        "margin_squared": None if margin is None else margin * margin,
        "playoff": int(row["game_type"] == "playoffs"),
        **{key: state[key] for key in ("defense_team_fouls", "offense_team_fouls",
                                       "defense_in_penalty", "offense_in_penalty")},
        "late_close": late_close,
    }
    return [np.nan if values[k] is None else float(values[k]) for k in NUMERIC]


def _columns(rows, states):
    numeric = np.array([context(row, state) for row, state in zip(rows, states)], dtype=float)
    teams = np.array([[-1.0 if row[k] is None else float(row[k]) for k in CATEGORICAL] for row in rows], dtype=float)
    history = np.array([float(row["previous_foul_1"] == 1 or row["previous_foul_2"] == 1) for row in rows])
    return numeric, teams, history


def _design(numeric, teams, history, index, *, with_history):
    """[numeric, fixed missing indicators, (history), teams]; B differs from A by exactly one column."""
    block = numeric[index]
    parts = [block, np.isnan(block).astype(float)]
    if with_history:
        parts.append(history[index][:, None])
    parts.append(teams[index])
    return np.hstack(parts)


def feature_names(with_history):
    names = [*NUMERIC, *(f"{k}_missing" for k in NUMERIC)]
    return [*names, HISTORY] if with_history else names


def _pipeline(numeric_count, c):
    numeric = Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scale", StandardScaler())])
    transform = ColumnTransformer([
        ("numeric", numeric, list(range(numeric_count))),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         list(range(numeric_count, numeric_count + len(CATEGORICAL))))])
    return Pipeline([("transform", transform),
                     ("model", LogisticRegression(C=c, solver="lbfgs", max_iter=MAX_ITER, random_state=0))])


def _fit_one(name, x, y, c):
    if len(np.unique(y)) != 2:
        raise ValueError("single-class training data; plan Stage 5 comparison withheld")
    pipe = _pipeline(x.shape[1] - len(CATEGORICAL), c)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        pipe.fit(x, y)
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise ValueError(f"nonconvergence in {name} C={c}; comparison withheld")
    return pipe


def clip(p):
    p = np.asarray(p, dtype=float)
    return np.clip(p, CLIP, 1 - CLIP), int(np.sum((p < CLIP) | (p > 1 - CLIP)))


def _model_record(pipe, names):
    transform = pipe.named_steps["transform"]
    numeric = transform.named_transformers_["numeric"]
    model = pipe.named_steps["model"]
    categories = transform.named_transformers_["categorical"].categories_
    encoded = [f"{k}={int(v)}" for k, values in zip(CATEGORICAL, categories) for v in values]
    return {"C": float(model.C), "iterations": int(model.n_iter_.max()), "intercept": float(model.intercept_[0]),
            "coefficients": dict(zip([*names, *encoded], model.coef_[0].tolist(), strict=True)),
            "imputer_medians": dict(zip(names, numeric.named_steps["impute"].statistics_.tolist(), strict=True)),
            "scaler_mean": dict(zip(names, numeric.named_steps["scale"].mean_.tolist(), strict=True)),
            "scaler_scale": dict(zip(names, numeric.named_steps["scale"].scale_.tolist(), strict=True))}


def fit(rows, supplement, split):
    """Validate, attach team-foul states, choose the shared C, refit each test fold."""
    modeling.validate_rows(rows)
    reasons = meeting_ab.check_lags(rows)
    states = team_fouls.attach(rows, supplement)
    subsets = modeling.chronological_split(rows, split)
    for part, block in subsets.items():
        if any(SEASON_PARTITION.get(row["season"]) != part for row in block):
            raise ValueError("season and date partition disagree; folds withheld")
    numeric, teams, history = _columns(rows, states)
    y = np.array([row["outcome"] for row in rows])
    season = np.array([row["season"] for row in rows])
    games = np.array([row["game_id"] for row in rows])
    complete = np.array([why is None for why in reasons])
    dates = np.array([date.fromisoformat(row["date"]).toordinal() for row in rows])

    def where(seasons):
        return np.flatnonzero(complete & np.isin(season, list(seasons)))

    diagnostics = {"history_exclusions": {}, "folds": {}, "split_manifest": {}, "base_rate": {"training_rate": {}}}
    for s in sorted(set(season)):
        mask = season == s
        diagnostics["history_exclusions"][s] = {"rows": int(mask.sum()), "paired_rows": int((mask & complete).sum()),
                                                "excluded_game_start_rows": int((mask & ~complete).sum())}

    def check_fold(train, test):
        if not len(train) or not len(test):
            raise ValueError("empty fold; plan Stage 5 comparison withheld")
        if set(games[train]) & set(games[test]) or dates[train].max() >= dates[test].min():
            raise ValueError("fold is not chronologically separated by whole games")

    train, val = where(VALIDATION["train"]), where([VALIDATION["evaluate"]])
    check_fold(train, val)
    x_train = _design(numeric, teams, history, train, with_history=False)
    x_val = _design(numeric, teams, history, val, with_history=False)
    candidates, validation_clipped = [], {}
    for c in C_GRID:
        pipe = _fit_one("context_a validation", x_train, y[train], c)
        p, validation_clipped[str(c)] = clip(pipe.predict_proba(x_val)[:, 1])
        candidates.append((float(evaluation.log_losses(y[val], p).mean()), c))
    best_loss, shared_c = min(candidates, key=lambda item: (item[0], C_GRID.index(item[1])))
    diagnostics["validation"] = {"train_seasons": list(VALIDATION["train"]), "evaluate": VALIDATION["evaluate"],
                                 "training_rows": len(train), "validation_rows": len(val),
                                 "candidate_scores": [{"C": c, "validation_logloss": s} for s, c in candidates],
                                 "shared_C": shared_c, "validation_logloss": best_loss,
                                 "clipped_predictions": validation_clipped}
    diagnostics["split_manifest"]["validation"] = {"train_games": sorted(set(games[train])),
                                                   "evaluate_games": sorted(set(games[val]))}

    test_rows = subsets["test"]
    position = {(r["game_id"], r["possession_number"]): i for i, r in enumerate(rows)}
    test_index = np.array([position[(r["game_id"], r["possession_number"])] for r in test_rows])
    slot = {int(i): k for k, i in enumerate(test_index)}
    probabilities = {name: [None] * len(test_rows) for name in MODELS}
    fold_of = [None] * len(test_rows)
    clipped, pipelines = {}, {}
    for fold in TEST_FOLDS:
        label = fold["evaluate"]
        train, test = where(fold["train"]), where([label])
        check_fold(train, test)
        if not set(test) <= set(slot):
            raise ValueError("test fold rows outside the loader test partition")
        base = float(y[train].mean())
        diagnostics["base_rate"]["training_rate"][label] = base
        diagnostics["split_manifest"][label] = {"train_games": sorted(set(games[train])),
                                                "evaluate_games": sorted(set(games[test]))}
        record = {"train_seasons": list(fold["train"]), "training_rows": len(train), "evaluated_rows": len(test),
                  "C": shared_c, "training_prevalence": base}
        clipped[label] = {}
        predicted = {"base_rate": np.full(len(test), base)}
        for name, with_history in (("context_a", False), ("history_b", True)):
            x_tr = _design(numeric, teams, history, train, with_history=with_history)
            x_te = _design(numeric, teams, history, test, with_history=with_history)
            pipe = _fit_one(f"{name} {label}", x_tr, y[train], shared_c)
            pipelines[f"{label}/{name}"] = pipe
            record[name] = _model_record(pipe, feature_names(with_history))
            predicted[name] = pipe.predict_proba(x_te)[:, 1]
        for name in MODELS:
            values, count = clip(predicted[name])
            clipped[label][name] = count
            for i, value in zip(test, values.tolist()):
                probabilities[name][slot[int(i)]] = value
        for i in test:
            fold_of[slot[int(i)]] = label
        diagnostics["folds"][label] = record
    diagnostics["clipped_predictions"] = clipped
    paired = {part: [r for r, ok in zip(rows, complete) if ok and SEASON_PARTITION[r["season"]] == part]
              for part in ("train", "tune", "test")}
    return {"subsets": subsets, "primary": paired, "pipelines": pipelines, "diagnostics": diagnostics,
            "states": states, "rows": rows,
            "predictions": {"row_ids": [[r["game_id"], r["possession_number"]] for r in test_rows],
                            "probabilities": probabilities, "fold": fold_of}}


def _logit(p):
    return np.log(p) - np.log1p(-p)


def calibration_intercept(y, p):
    """Solve sum(y - sigmoid(a + logit p)) = 0 by Newton steps; diagnostic only."""
    offset, a = _logit(p), 0.0
    for _ in range(100):
        q = 1 / (1 + np.exp(-(a + offset)))
        step = np.sum(y - q) / np.sum(q * (1 - q))
        a += step
        if abs(step) < 1e-12:
            return float(a)
    raise ValueError("calibration intercept did not converge")


def calibration_slope(y, p):
    """Unpenalized logistic regression of y on logit(p) by IRLS; returns (intercept, slope)."""
    x = np.column_stack([np.ones_like(p), _logit(p)])
    beta = np.zeros(2)
    for _ in range(100):
        q = 1 / (1 + np.exp(-(x @ beta)))
        w = q * (1 - q)
        step = np.linalg.solve(x.T @ (x * w[:, None]), x.T @ (y - q))
        beta += step
        if np.max(np.abs(step)) < 1e-12:
            return float(beta[0]), float(beta[1])
    raise ValueError("calibration slope did not converge")


def _game_sums(games, values):
    order = sorted(set(games))
    index = {g: i for i, g in enumerate(order)}
    codes = np.array([index[g] for g in games])
    return np.bincount(codes, weights=values, minlength=len(order)), np.bincount(codes, minlength=len(order)).astype(float)


def stratified_bootstrap(strata, rng, resamples=RESAMPLES):
    """Percentile interval of sum(D)/sum(n), resampling games within each stratum in order."""
    total_d, total_n = np.zeros(resamples), np.zeros(resamples)
    for sums, counts in strata:
        if len(sums) < 2:
            raise ValueError("at least two games per stratum required")
        draw = rng.integers(len(sums), size=(resamples, len(sums)))
        total_d += sums[draw].sum(axis=1)
        total_n += counts[draw].sum(axis=1)
    return np.quantile(total_d / total_n, [0.025, 0.975]).tolist()


def _summary(y, p, games, events, rng_strata):
    losses = {name: evaluation.log_losses(y, p[name]) for name in MODELS}
    delta = losses["history_b"] - losses["context_a"]
    strata, equal_game = [], []
    for stratum in rng_strata:
        sums, counts = _game_sums(games[stratum], delta[stratum])
        strata.append((sums, counts))
        equal_game.extend((sums / counts).tolist())
    models = {}
    for name in MODELS:
        loss_sums, loss_counts = _game_sums(games, losses[name])
        record = {"logloss": float(losses[name].mean()), "brier": float(np.mean((p[name] - y) ** 2)),
                  "equal_game_logloss": float(np.mean(loss_sums / loss_counts)),
                  "calibration_bins": evaluation._calibration(y, p[name])}
        if name != "base_rate":
            record["calibration_intercept"] = calibration_intercept(y, p[name])
            record["calibration_intercept_slope_fit"], record["calibration_slope"] = calibration_slope(y, p[name])
        models[name] = record
    estimate = float(delta.mean())
    return {"rows": int(len(y)), "games": int(len(set(games))), "foul_possessions": int(y.sum()),
            "counted_foul_events": int(events.sum()), "prevalence": float(y.mean()), "models": models,
            "paired_logloss": {"estimate": estimate, "equal_game_estimate": float(np.mean(equal_game)),
                               "relative_reduction": estimate / models["context_a"]["logloss"]},
            "paired_brier": float(np.mean((p["history_b"] - y) ** 2 - (p["context_a"] - y) ** 2)),
            "_strata": strata}


def evaluate(fitted):
    """Pooled and per-season paired comparison with whole-game bootstrap intervals; never classifies usefulness."""
    rows, states = fitted["rows"], fitted["states"]
    lookup = {(r["game_id"], r["possession_number"]): (r, s) for r, s in zip(rows, states)}
    ids, folds = fitted["predictions"]["row_ids"], fitted["predictions"]["fold"]
    probabilities = fitted["predictions"]["probabilities"]
    keep = [i for i, fold in enumerate(folds) if fold is not None]
    for name in MODELS:
        if any((probabilities[name][i] is None) != (folds[i] is None) for i in range(len(ids))):
            raise ValueError("every model must predict exactly the paired evaluation rows")
    picked = [lookup[tuple(ids[i])] for i in keep]
    y = np.array([r["outcome"] for r, _ in picked], dtype=float)
    games = np.array([r["game_id"] for r, _ in picked])
    events = np.array([s["counted_foul_events"] for _, s in picked], dtype=float)
    season = np.array([folds[i] for i in keep])
    game_type = np.array([r["game_type"] for r, _ in picked])
    p = {name: np.array([probabilities[name][i] for i in keep], dtype=float) for name in MODELS}
    labels = [f["evaluate"] for f in TEST_FOLDS]
    strata = [np.flatnonzero(season == label) for label in labels]
    pooled = _summary(y, p, games, events, strata)
    pooled["paired_logloss"]["interval"] = stratified_bootstrap(pooled.pop("_strata"), np.random.default_rng(SEED))
    seasons = {}
    for k, (label, index) in enumerate(zip(labels, strata), start=1):
        sub = {name: values[index] for name, values in p.items()}
        result = _summary(y[index], sub, games[index], events[index], [np.arange(len(index))])
        result["paired_logloss"]["interval"] = stratified_bootstrap(result.pop("_strata"),
                                                                    np.random.default_rng([SEED, k]))
        seasons[label] = result
    breakdown = {}
    for value in sorted(set(game_type)):
        mask = game_type == value
        loss = {name: evaluation.log_losses(y[mask], p[name][mask]) for name in MODELS}
        breakdown[str(value)] = {"rows": int(mask.sum()), "games": int(len(set(games[mask]))),
                            "prevalence": float(y[mask].mean()), "counted_foul_events": int(events[mask].sum()),
                            "model_logloss": {name: float(v.mean()) for name, v in loss.items()},
                            "model_brier": {name: float(np.mean((p[name][mask] - y[mask]) ** 2)) for name in MODELS},
                            "paired_logloss": float((loss["history_b"] - loss["context_a"]).mean())}
    return {"primary": "pooled history_b minus context_a possession-weighted log loss; negative favors history",
            "paired_label": "Model B (context + L_t) minus Model A (context)",
            "shared_C": fitted["diagnostics"]["validation"]["shared_C"],
            "pooled": pooled, "seasons": seasons, "game_type_breakdown": breakdown,
            "history_exclusions": fitted["diagnostics"]["history_exclusions"],
            "clipped_predictions": fitted["diagnostics"]["clipped_predictions"],
            "bootstrap": {"resamples": RESAMPLES, "seed": SEED, "confidence": 0.95,
                          "conditions_on_fitted_models": True,
                          "assumption": "independent identically distributed whole games within each test season",
                          "limitations": "No refitting, selection or calendar/series dependence uncertainty; "
                                         "percentile coverage is not guaranteed."},
            "decision": evaluation.practical_decision(pooled["paired_logloss"]["interval"], None),
            "row_ids": [ids[i] for i in keep], "row_count": len(keep), "undefined_or_dropped_targets": 0,
            "game_start_rows_excluded_from_test": len(ids) - len(keep),
            "probability_clip": [CLIP, 1 - CLIP]}


def markdown_lines(result):
    """Human-readable report lines for the exploratory runner."""
    ev = result["evaluation"]
    lines = ["# PROVISIONAL plan-faithful Stage 5 fit (`plan-stage5-v1`)", "", "EXPLORATORY_ONLY_NOT_VALIDATED", "",
             "Real recorded-call data on previously exposed seasons; reconstruction and scientific validity remain "
             "unvalidated. No publication authorization or meaningful-gain classification.", "",
             f"Shared C chosen with Model A on {VALIDATION['evaluate']}: {ev['shared_C']}", "",
             "| Test set | Games | Possessions | Base rate | Model A | Model B | B − A | 95% interval |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for label, block in [("Pooled", ev["pooled"]), *ev["seasons"].items()]:
        m, d = block["models"], block["paired_logloss"]
        lines.append(f"| {label} | {block['games']} | {block['rows']} | {m['base_rate']['logloss']:.6f} | "
                     f"{m['context_a']['logloss']:.6f} | {m['history_b']['logloss']:.6f} | {d['estimate']:+.7f} | "
                     f"[{d['interval'][0]:+.7f}, {d['interval'][1]:+.7f}] |")
    lines += ["", "Negative values favor history. Intervals condition on the fitted models and assume IID games "
              "within season; they are not a usefulness decision.", "",
              "| Game type | Possessions | Model A | Model B | B − A |", "| --- | ---: | ---: | ---: | ---: |"]
    for value, block in ev["game_type_breakdown"].items():
        lines.append(f"| {value} | {block['rows']} | {block['model_logloss']['context_a']:.6f} | "
                     f"{block['model_logloss']['history_b']:.6f} | {block['paired_logloss']:+.7f} |")
    lines += ["", "| Test set | Model | Brier | Calibration intercept | Calibration slope |",
              "| --- | --- | ---: | ---: | ---: |"]
    for label, block in [("Pooled", ev["pooled"]), *ev["seasons"].items()]:
        for name in ("context_a", "history_b"):
            m = block["models"][name]
            lines.append(f"| {label} | {name} | {m['brier']:.6f} | {m['calibration_intercept']:+.4f} | "
                         f"{m['calibration_slope']:.4f} |")
    return lines
