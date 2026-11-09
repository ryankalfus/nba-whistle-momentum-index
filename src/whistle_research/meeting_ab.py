"""Meeting-aligned two-model comparison `meeting-ab-v1`; see docs/MEETING_ALIGNMENT.md.

Model A: additive L2 logistic shared context. Model B: the identical design plus
one column, H_t = 1{F_(t-1)=1 or F_(t-2)=1}, on the global possession axis.
Rows lacking two observed lags are excluded from both primary models at design
time; the loader and selected-row file keep every row. Sensitivity S1 keeps all
rows, defines H over the observed lags and adds an explicit incomplete-history
indicator to its Model B only. No scientific gate is satisfied by this module.
"""

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

from whistle_research import evaluation, modeling

SCHEMA = "meeting-ab-v1"
CONTEXT_NUMERIC = ("period", "clock", "score_difference", "score_margin", "home_defense")
CATEGORICAL = ("defense_team_id", "offense_team_id")
LAGS = ("previous_foul_1", "previous_foul_2")
PRIMARY = ("base_rate", "context_a", "history_b")
S1 = ("s1_context_a", "s1_history_b")
MODEL_NAMES = (*PRIMARY, *S1)
FEATURE_FIELDS = ("game_id", "possession_number", *CONTEXT_NUMERIC, *CATEGORICAL, *LAGS)
C_GRID = modeling.C_GRID
MAX_ITER = modeling.MAX_ITER
UNKNOWN = modeling.UNKNOWN


def specification():
    """Canonical declaration bound into plans; includes hashes of every reused module."""
    return {
        "schema": SCHEMA,
        "context_numeric": list(CONTEXT_NUMERIC),
        "categorical": list(CATEGORICAL),
        "history_sources": list(LAGS),
        "history": "H = 1 if previous_foul_1 == 1 or previous_foul_2 == 1; H = 0 only if both are observed 0",
        "lag_integrity": "within each game, possession numbers must be 1, 2, 3, ... with no gaps, and "
                         "previous_foul_1/2 must equal the outcomes of the preceding one/two rows; lags at the "
                         "first one/two rows must be null; any mismatch withholds the comparison",
        "primary_rows": "rows with both lags observed; game-start rows excluded from base_rate, context_a and "
                        "history_b at design time and counted per partition; unknown outcomes are refused upstream",
        "models": list(MODEL_NAMES),
        "primary": "history_b_minus_context_a_possession_logloss; negative favors history",
        "sensitivity_s1": "all rows; H = 1 if any observed lag is 1 else 0; s1_history_b adds history_incomplete "
                          "= 1 if either lag is null; s1_context_a is the context design on all rows",
        "C_grid": list(C_GRID), "max_iter": MAX_ITER, "solver": "lbfgs", "penalty": "l2",
        "missing": "context numeric constant zero plus fixed missing indicators; categorical unknown sentinel; "
                   "history columns never imputed and carry no missing indicator",
        "selection": "tune possession logloss; first grid value breaks ties; no train+tune refit",
        "bootstrap_resamples": 999, "bootstrap_seed": 137, "confidence": 0.95,
        "probability_clip": evaluation.EPSILON,
        "sources": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in ("meeting_ab.py", "modeling.py", "evaluation.py")},
    }


def history_flag(row):
    """Return (H, complete). H uses observed lags only; unavailable lags never become observed zero."""
    lags = [row.get(k) for k in LAGS]
    if any(v not in (None, 0, 1) or isinstance(v, bool) for v in lags):
        raise ValueError("history lags must be 0, 1 or null")
    return int(any(v == 1 for v in lags)), all(v is not None for v in lags)


def check_lags(rows):
    """Fail closed unless lags equal the preceding possessions' outcomes in the same game.

    Possession numbers must run 1, 2, 3, ... within each game, so list
    neighbours are the actual previous possessions. Rows carry known binary
    outcomes (validate_rows refuses unknown targets), so a null lag can only
    occur before a game's first rows. Returns `game_start` for those rows and
    None otherwise.
    """
    reasons, histories = [], {}
    for row in rows:
        history = histories.setdefault(row["game_id"], [])
        if row["possession_number"] != len(history) + 1:
            raise ValueError(f"possession numbers in game {row['game_id']} must be contiguous from 1")
        if row["outcome"] not in (0, 1) or isinstance(row["outcome"], bool):
            raise ValueError("known binary outcomes required for lag integrity")
        for k, key in enumerate(LAGS, start=1):
            expected = history[-k] if len(history) >= k else None
            if row.get(key) != expected:
                raise ValueError(f"{key} does not equal the outcome {k} rows earlier in game {row['game_id']}")
        reasons.append("game_start" if len(history) < len(LAGS) else None)
        history.append(row["outcome"])
    return reasons


def _design(rows, *, history, incomplete=False):
    """Fixed allowlist. Context columns are identical across A and B; B appends history only."""
    names = [*CONTEXT_NUMERIC, *(f"{k}_missing" for k in CONTEXT_NUMERIC)]
    if history:
        names.append("recent_defensive_foul")
    if incomplete:
        names.append("history_incomplete")
    matrix = []
    for row in rows:
        numeric = [np.nan if row.get(k) is None else row[k] for k in CONTEXT_NUMERIC]
        values = [*numeric, *(float(np.isnan(v)) for v in numeric)]
        if history:
            flag, complete = history_flag(row)
            values.append(flag)
            if incomplete:
                values.append(float(not complete))
        categories = [UNKNOWN if row.get(k) is None else f"value:{row[k]}" for k in CATEGORICAL]
        matrix.append([*values, *categories])
    return np.array(matrix, dtype=object), names


def _pipeline(numeric_count, c):
    numeric = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True)),
                        ("scale", StandardScaler())])
    transform = ColumnTransformer([
        ("numeric", numeric, list(range(numeric_count))),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False),
         list(range(numeric_count, numeric_count + len(CATEGORICAL))))])
    return Pipeline([("transform", transform),
                     ("model", LogisticRegression(C=c, solver="lbfgs", max_iter=MAX_ITER, random_state=0))])


def _select(name, subsets, *, history, incomplete=False):
    """Tune C on the tuning partition only; abort on any convergence warning."""
    y_train = np.array([r["outcome"] for r in subsets["train"]])
    y_tune = np.array([r["outcome"] for r in subsets["tune"]])
    if len(np.unique(y_train)) != 2:
        raise ValueError("single-class training data; meeting A/B comparison withheld")
    train, names = _design(subsets["train"], history=history, incomplete=incomplete)
    tune, _ = _design(subsets["tune"], history=history, incomplete=incomplete)
    test, _ = _design(subsets["test"], history=history, incomplete=incomplete)
    candidates = []
    for c in C_GRID:
        pipe = _pipeline(len(names), c)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            pipe.fit(train, y_train)
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            raise ValueError(f"nonconvergence in {name} C={c}; comparison withheld")
        score = float(evaluation.log_losses(y_tune, pipe.predict_proba(tune)[:, 1]).mean())
        candidates.append((score, c, pipe))
    best, c, selected = min(candidates, key=lambda item: (item[0], C_GRID.index(item[1])))
    diagnostics = {"selected_C": c, "tune_logloss": best, "tuning_candidates": len(C_GRID),
                   "training_rows": len(train), "numeric_features": names,
                   "iterations": int(selected.named_steps["model"].n_iter_.max()),
                   "candidate_scores": [{"C": c, "tune_logloss": s} for s, c, _ in candidates]}
    return selected, selected.predict_proba(test)[:, 1].tolist(), diagnostics


def fit(rows, split):
    """Fit primary A/B (complete-history rows) and S1 (all rows) on the same chronological partitions."""
    modeling.validate_rows(rows)
    reasons = check_lags(rows)
    reason_of = {(r["game_id"], r["possession_number"]): why for r, why in zip(rows, reasons)}
    subsets = modeling.chronological_split(rows, split)
    primary = {}
    exclusions = {}
    for part, block in subsets.items():
        kept = [r for r in block if reason_of[(r["game_id"], r["possession_number"])] is None]
        counts = {}
        for r in block:
            why = reason_of[(r["game_id"], r["possession_number"])]
            if why is not None:
                counts[why] = counts.get(why, 0) + 1
        exclusions[part] = {"rows": len(block), "primary_rows": len(kept), "excluded_rows": len(block) - len(kept),
                            "excluded_by_reason": counts}
        primary[part] = kept
    if any(not primary[part] for part in primary):
        raise ValueError("empty primary partition after history-availability exclusion")
    base = float(np.mean([r["outcome"] for r in primary["train"]]))
    pipelines, diagnostics = {}, {"base_rate": {"training_rate": base, "tuning_candidates": 0},
                                  "history_exclusions": exclusions}
    probabilities = {}
    primary_ids = {(r["game_id"], r["possession_number"]) for r in primary["test"]}
    test_ids = [[r["game_id"], r["possession_number"]] for r in subsets["test"]]
    specs = (("context_a", primary, False, False), ("history_b", primary, True, False),
             ("s1_context_a", subsets, False, False), ("s1_history_b", subsets, True, True))
    for name, data, history, incomplete in specs:
        pipe, predicted, diagnostics[name] = _select(name, data, history=history, incomplete=incomplete)
        pipelines[name] = pipe
        if data is primary:
            values = iter(predicted)
            probabilities[name] = [next(values) if tuple(i) in primary_ids else None for i in test_ids]
        else:
            probabilities[name] = predicted
    probabilities["base_rate"] = [base if tuple(i) in primary_ids else None for i in test_ids]
    return {"subsets": subsets, "primary": primary, "pipelines": pipelines, "diagnostics": diagnostics,
            "predictions": {"row_ids": test_ids, "probabilities": {k: probabilities[k] for k in MODEL_NAMES}}}


def _scores(rows, predictions, names, minuend, subtrahend):
    """Per-model metrics and the paired whole-game bootstrap for minuend minus subtrahend."""
    y = np.array([r["outcome"] for r in rows])
    game_ids = sorted({r["game_id"] for r in rows})
    if len(game_ids) < 2:
        raise ValueError("paired whole-game uncertainty requires at least two evaluation games")
    masks = [np.array([r["game_id"] == g for r in rows]) for g in game_ids]
    losses, metrics, probs = {}, {}, {}
    for name in names:
        p = np.asarray(predictions[name], dtype=float)
        if p.shape != y.shape:
            raise ValueError("all compared models must predict the identical ordered rows")
        probs[name], losses[name] = p, evaluation.log_losses(y, p)
        metrics[name] = {"rows": len(y), "games": len(game_ids),
                         "possession_logloss": float(losses[name].mean()),
                         "equal_game_logloss": float(np.mean([losses[name][m].mean() for m in masks])),
                         "brier": float(np.mean((p - y) ** 2)), "calibration": evaluation._calibration(y, p)}
    delta = losses[minuend] - losses[subtrahend]
    interval = evaluation.paired_game_bootstrap([delta[m].sum() for m in masks], [int(m.sum()) for m in masks])
    breakdown = {}
    for field in ("season", "game_type"):
        breakdown[field] = {}
        for value in sorted({r[field] for r in rows}):
            mask = np.array([r[field] == value for r in rows])
            groups = [m & mask for m in masks if np.any(m & mask)]
            breakdown[field][value] = {
                "rows": int(mask.sum()), "games": len(groups),
                "paired_possession_logloss": float(delta[mask].mean()),
                "paired_equal_game_logloss": float(np.mean([delta[m].mean() for m in groups])),
                "model_logloss": {n: float(losses[n][mask].mean()) for n in names},
                "model_brier": {n: float(np.mean((probs[n][mask] - y[mask]) ** 2)) for n in names}}
    return {"models": metrics, "paired_logloss": interval,
            "paired_brier": float(np.mean((probs[minuend] - y) ** 2 - (probs[subtrahend] - y) ** 2)),
            "breakdown": breakdown, "row_count": len(rows),
            "row_ids": [[r["game_id"], r["possession_number"]] for r in rows]}


def evaluate(fitted):
    """Score the primary A/B comparison and sensitivity S1; never classifies usefulness."""
    test, kept = fitted["subsets"]["test"], fitted["primary"]["test"]
    ids = fitted["predictions"]["row_ids"]
    if ids != [[r["game_id"], r["possession_number"]] for r in test]:
        raise ValueError("prediction rows must equal the ordered evaluation partition")
    probabilities = fitted["predictions"]["probabilities"]
    keep = [i for i, p in enumerate(probabilities["context_a"]) if p is not None]
    keep_set = set(keep)
    if ([test[i] for i in keep] != kept
            or any((probabilities[n][i] is None) != (i not in keep_set) for n in PRIMARY for i in range(len(test)))):
        raise ValueError("primary models must predict exactly the complete-history evaluation rows")
    primary = _scores(kept, {n: [probabilities[n][i] for i in keep] for n in PRIMARY},
                      PRIMARY, "history_b", "context_a")
    s1 = _scores(test, probabilities, S1, "s1_history_b", "s1_context_a")
    return {"primary": "history_b_minus_context_a_possession_weighted_logloss; negative favors history",
            "paired_label": "Model B (context + H) minus Model A (context)",
            **primary,
            "sensitivities": {"s1_all_rows_incomplete_indicator": {
                "label": "S1: all rows, Model B adds H over observed lags plus history_incomplete", **s1}},
            "history_exclusions": fitted["diagnostics"]["history_exclusions"],
            "decision": evaluation.practical_decision(primary["paired_logloss"]["interval"], None),
            "undefined_or_dropped_targets": 0, "probability_clip": evaluation.EPSILON}


def synthetic_rows(seed, games=90, possessions=36):
    """Synthetic rows with real lag structure: null lags at each game's first two rows."""
    rows = modeling._synthetic_rows(seed, games=games, possessions=possessions)
    for row in rows:
        if row["possession_number"] == 1:
            row["previous_foul_1"] = row["previous_foul_2"] = None
        elif row["possession_number"] == 2:
            row["previous_foul_2"] = None
    return rows
