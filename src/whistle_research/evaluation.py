"""Paired held-out scoring with whole-game resampling conditional on fixed fits."""

import numpy as np

from whistle_research.modeling import MODEL_NAMES, validate_rows

EPSILON = 1e-15


def log_losses(outcomes, probabilities):
    """Stable per-row binary log loss; no unknown-target filtering."""
    y, p = np.asarray(outcomes), np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.shape != y.shape or not len(y) or not np.all((y == 0) | (y == 1)):
        raise ValueError("matched nonempty binary outcomes and probabilities required")
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("finite probabilities in [0,1] required")
    p = np.clip(p, EPSILON, 1 - EPSILON)
    return -y * np.log(p) - (1 - y) * np.log1p(-p)


def paired_game_bootstrap(game_sums, game_counts, *, resamples=999, seed=137):
    """Recompute sum(loss differences)/sum(possessions) on selected whole games.

    Game sums are history-minus-context paired losses. Games are resampled with
    equal probability; counts remain attached, preserving possession weighting.
    IID games are assumed; fitted models and development selection are fixed.
    """
    sums, counts = np.asarray(game_sums, dtype=float), np.asarray(game_counts, dtype=float)
    if sums.ndim != 1 or sums.shape != counts.shape or len(sums) < 2:
        raise ValueError("at least two matched game sums and counts required")
    if not np.isfinite(sums).all() or not np.isfinite(counts).all() or np.any(counts <= 0) or np.any(counts != np.floor(counts)):
        raise ValueError("finite sums and positive integer game counts required")
    if type(resamples) is not int or resamples < 2:
        raise ValueError("at least two resamples required")
    rng = np.random.default_rng(seed)
    draws = np.empty(resamples)
    # A loop bounds memory independently of the number of resamples.
    for i in range(resamples):
        selected = rng.integers(len(sums), size=len(sums))
        draws[i] = sums[selected].sum() / counts[selected].sum()
    return {"estimate": float(sums.sum() / counts.sum()),
            "interval": np.quantile(draws, [0.025, 0.975]).tolist(),
            "equal_game_estimate": float((sums / counts).mean()),
            "resamples": resamples, "seed": seed, "confidence": 0.95,
            "target": "expected paired game loss sum divided by expected game possession count",
            "conditions_on_fitted_models": True,
            "assumption": "independent identically distributed whole games with finite moments",
            "limitations": "No training/selection uncertainty or calendar/series dependence correction; percentile coverage is not guaranteed."}


def practical_decision(interval, meaningful_gain=None):
    """Symmetric meaningful band is supplied by a frozen real protocol only."""
    if meaningful_gain is None:
        return {"classification": "NOT_SPECIFIED", "reason": "no frozen meaningful-gain threshold supplied"}
    if (isinstance(meaningful_gain, bool) or not isinstance(meaningful_gain, (int, float))
            or not np.isfinite(meaningful_gain) or meaningful_gain <= 0):
        raise ValueError("positive finite meaningful gain required")
    bounds = np.asarray(interval, dtype=float)
    if bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[0] > bounds[1]:
        raise ValueError("ordered finite interval bounds required")
    low, high = bounds
    if high < -meaningful_gain:
        category = "USEFUL"
    elif low > -meaningful_gain and high < meaningful_gain:
        category = "NEGLIGIBLE_UNDER_DECLARED_BAND"
    elif low > meaningful_gain:
        category = "UNSUPPORTED_HISTORY_HARMFUL"
    else:
        category = "INCONCLUSIVE"
    return {"classification": category, "meaningful_gain": meaningful_gain,
            "rule": "useful if upper<-gain; negligible if interval strictly inside [-gain,+gain]; harmful if lower>+gain; otherwise inconclusive",
            "limitations": "Conditional on interval assumptions and the frozen symmetric practical band; containing zero alone never establishes equivalence."}


def _calibration(y, p):
    bins = np.minimum((p * 10).astype(int), 9)
    return [{"lower": i / 10, "upper": (i + 1) / 10, "count": int((bins == i).sum()),
             "mean_probability": float(p[bins == i].mean()) if np.any(bins == i) else None,
             "observed_fraction": float(y[bins == i].mean()) if np.any(bins == i) else None}
            for i in range(10)]


def _evaluate(rows, predictions, *, meaningful_gain=None):
    validate_rows(rows)
    ids = [[r["game_id"], r["possession_number"]] for r in rows]
    if predictions.get("row_ids") != ids or set(predictions.get("probabilities", {})) != set(MODEL_NAMES):
        raise ValueError("all models must predict the identical ordered evaluation row IDs")
    y = np.array([r["outcome"] for r in rows])
    game_ids = sorted({r["game_id"] for r in rows})
    masks = [np.array([r["game_id"] == game for r in rows]) for game in game_ids]
    if len(game_ids) < 2:
        raise ValueError("paired whole-game uncertainty requires at least two evaluation games")
    losses, metrics = {}, {}
    for name in MODEL_NAMES:
        p = np.asarray(predictions["probabilities"][name], dtype=float)
        loss = log_losses(y, p)
        losses[name] = loss
        metrics[name] = {"rows": len(y), "games": len(game_ids),
                         "possession_logloss": float(loss.mean()),
                         "equal_game_logloss": float(np.mean([loss[m].mean() for m in masks])),
                         "brier": float(np.mean((p - y) ** 2)), "calibration": _calibration(y, p)}
    delta = losses["nonlinear_history"] - losses["nonlinear_context"]
    sums = [delta[m].sum() for m in masks]
    counts = [int(m.sum()) for m in masks]
    interval = paired_game_bootstrap(sums, counts)
    breakdown = {}
    for field in ("season", "game_type"):
        breakdown[field] = {}
        for value in sorted({r[field] for r in rows}):
            mask = np.array([r[field] == value for r in rows])
            group_games = [m & mask for m in masks if np.any(m & mask)]
            breakdown[field][value] = {
                "rows": int(mask.sum()), "games": len(group_games),
                "paired_possession_logloss": float(delta[mask].mean()),
                "paired_equal_game_logloss": float(np.mean([delta[m].mean() for m in group_games])),
                "model_logloss": {name: float(loss[mask].mean()) for name, loss in losses.items()},
                "model_brier": {name: float(np.mean((np.asarray(predictions["probabilities"][name])[mask] - y[mask]) ** 2))
                                for name in MODEL_NAMES},
            }
    return {"primary": "history_minus_context_possession_weighted_logloss; negative favors history",
            "models": metrics, "paired_logloss": interval,
            "paired_brier": float(np.mean((np.asarray(predictions["probabilities"]["nonlinear_history"]) - y) ** 2
                                          - (np.asarray(predictions["probabilities"]["nonlinear_context"]) - y) ** 2)),
            "breakdown": breakdown, "decision": practical_decision(interval["interval"], meaningful_gain),
            "row_ids": ids, "row_count": len(rows), "undefined_or_dropped_targets": 0,
            "probability_clip": EPSILON}


def evaluate_real(rows, *, evidence):
    """Gate, fit, and score fresh matched predictions; external packets forbidden.

    No prediction argument is accepted: source/code/row/fit provenance comes
    from the same gated internal fit, avoiding stale or outcome-derived packets.
    """
    from whistle_research.modeling import fit_real
    return fit_real(rows, evidence=evidence)["evaluation"]
