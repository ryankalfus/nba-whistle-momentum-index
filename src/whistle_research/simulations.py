"""Synthetic WMI diagnostics, exact references, and declared process uncertainty.

No real-data access or per-game confidence intervals. Components are computed
within games, never across a concatenated game boundary.
"""

import argparse
from fractions import Fraction
import hashlib
from itertools import product
import json
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy.stats import binomtest

from whistle_research import metrics
from whistle_research.metrics import calculate_wmi


COMPONENTS = ("sum_m0", "n0", "sum_m1", "n1")


def _rates(probabilities):
    rates = np.asarray(probabilities, dtype=float)
    if rates.ndim != 1 or not len(rates) or not np.all(np.isfinite(rates)):
        raise ValueError("one nonempty finite probability vector is required")
    if np.any((rates < 0) | (rates > 1)):
        raise ValueError("probabilities must be between zero and one")
    return rates


def game_components(games):
    """Return [sum_m0,n0,sum_m1,n1] for each binary game (equal length)."""
    f = np.asarray(games)
    if f.ndim != 2 or not f.shape[1] or not np.all((f == 0) | (f == 1)):
        raise ValueError("games must be a nonempty-length binary matrix")
    f = f.astype(bool)
    past = np.zeros_like(f)
    future = np.zeros_like(f)
    for distance in (1, 2):
        past[:, distance:] |= f[:, :-distance]
        future[:, :-distance] |= f[:, distance:]
    m = f.astype(int) * (1 + future.astype(int))
    return np.column_stack(
        ((m * ~past).sum(1), (~past).sum(1), (m * past).sum(1), past.sum(1))
    )


def component_ratio(components):
    """Diagnostic functional (E S1 / E N1)/(E S0 / E N0).

    Applied to per-game components this is exact legacy WMI. Applied to mean
    components it is a separately named process target, not a new WMI edition.
    Undefined outputs are NaN, including absent groups or a zero baseline.
    """
    c = np.asarray(components, dtype=float)
    if c.shape[-1:] != (4,) or not np.all(np.isfinite(c)) or np.any(c < 0):
        raise ValueError("four finite nonnegative components are required")
    s0, n0, s1, n1 = np.moveaxis(c, -1, 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where((s0 > 0) & (n0 > 0) & (n1 > 0), s1 * n0 / (s0 * n1), np.nan)


def expected_independent_components(probabilities):
    """Analytic component expectations under independent, nonidentical Bernoulli.

    L, current F and N use disjoint coordinates and are independent at a fixed
    position; summing over positions does not make their pooled mixture IID.
    """
    p = _rates(probabilities)
    expected = np.zeros(4)
    for t, current in enumerate(p):
        a = 1 - np.prod(1 - p[max(0, t - 2):t])
        b = 1 - np.prod(1 - p[t + 1:t + 3])
        expected += [(1 - a) * current * (1 + b), 1 - a,
                     a * current * (1 + b), a]
    return expected


def exact_independent_reference(probabilities):
    """Enumerate every sequence using rational probabilities, capped at n=16.

    WMI distribution includes an explicit undefined atom. The conditional mean
    conditions on defined WMI; no unconditional expected ratio exists when the
    undefined atom has positive mass. Component expectations remain defined.
    """
    rates = _rates(probabilities)
    if len(rates) > 16:
        raise ValueError("exact enumeration is capped at 16 possessions")
    rational = [Fraction(str(float(p))) for p in rates]
    masses = {}
    undefined = Fraction(0)
    expected = [Fraction(0) for _ in COMPONENTS]
    for sequence in product((0, 1), repeat=len(rates)):
        mass = Fraction(1)
        for outcome, p in zip(sequence, rational, strict=True):
            mass *= p if outcome else 1 - p
        if not mass:
            continue
        metric = calculate_wmi(sequence, game_id="synthetic-exact")
        values = (metric.sum_m0, metric.n0, metric.sum_m1, metric.n1)
        for i, value in enumerate(values):
            expected[i] += mass * value
        if metric.wmi is None:
            undefined += mass
        else:
            ratio = Fraction(metric.sum_m1 * metric.n0, metric.n1 * metric.sum_m0)
            masses[ratio] = masses.get(ratio, Fraction(0)) + mass
    defined = 1 - undefined
    conditional = sum((w * p for w, p in masses.items()), Fraction(0)) / defined if defined else None
    expectation = list(map(float, expected))
    target = float(component_ratio(expectation))
    return {
        "probabilities": rates.tolist(),
        "undefined_probability": float(undefined),
        "conditional_mean_wmi_given_defined": float(conditional) if conditional is not None else None,
        "expected_components": dict(zip(COMPONENTS, expectation, strict=True)),
        "ratio_of_expected_components": target if np.isfinite(target) else None,
        "distribution": [
            {"wmi": float(w), "wmi_fraction": str(w), "probability": float(p)}
            for w, p in sorted(masses.items())
        ],
    }


def simulate_games(rng, probabilities, count, *, history_delta=0.0):
    """P(F_t=1 | past)=clip(p_t + delta*any(previous two F),0,1)."""
    rates = _rates(probabilities)
    if type(count) is not int or count < 1 or not np.isfinite(history_delta):
        raise ValueError("positive integer count and finite history delta required")
    draws = rng.random((count, len(rates)))
    f = np.zeros(draws.shape, dtype=int)
    for t, p in enumerate(rates):
        history = f[:, max(0, t - 2):t].any(axis=1)
        f[:, t] = draws[:, t] < np.clip(p + history_delta * history, 0, 1)
    return f


def distribution_summary(games):
    values = component_ratio(game_components(games))
    finite = values[np.isfinite(values)]
    return {
        "games": len(values),
        "undefined_count": int((~np.isfinite(values)).sum()),
        "undefined_fraction": float((~np.isfinite(values)).mean()),
        "conditional_mean_wmi_given_defined": float(finite.mean()) if len(finite) else None,
        "conditional_quantiles_given_defined": dict(zip(
            ("0.025", "0.5", "0.975"), np.quantile(finite, [0.025, 0.5, 0.975]).tolist(), strict=True
        )) if len(finite) else None,
        "fraction_above_one_among_all_games": float((values > 1).mean()),
    }


def whole_game_interval(components, rng, *, resamples=399, confidence=0.95):
    """Percentile bootstrap of the ratio of expected game components.

    Assumes IID sampled games, finite component moments and nonzero population
    denominators. Conditions on the game-generating process, not fitted models.
    Every component of each selected game is resampled together. If ANY draw is
    undefined, withhold the entire interval rather than drop bootstrap draws.
    """
    c = np.asarray(components, dtype=float)
    if c.ndim != 2 or len(c) < 2 or c.shape[1] != 4:
        raise ValueError("at least two games with four components required")
    component_ratio(c)  # validate even if the observed pooled ratio is defined
    if type(resamples) is not int or resamples < 2 or not 0 < confidence < 1:
        raise ValueError("at least two resamples and confidence in (0,1) required")
    estimate = float(component_ratio(c.mean(0)))
    indices = rng.integers(len(c), size=(resamples, len(c)))
    draws = component_ratio(c[indices].mean(1))
    undefined = int((~np.isfinite(draws)).sum())
    interval = None
    if np.isfinite(estimate) and not undefined:
        alpha = (1 - confidence) / 2
        interval = np.quantile(draws, [alpha, 1 - alpha]).tolist()
    return {"estimate": estimate if np.isfinite(estimate) else None,
            "interval": interval, "undefined_resamples": undefined, "resamples": resamples}


def coverage_experiment(rng, *, trials=200, games_per_trial=120, resamples=399,
                        shared_latent=False):
    """Coverage for a fixed equal mixture of low/high independent game rates.

    IID case: each game's latent rate is independent. Failure case: one latent
    rate is shared by all games in a trial, violating the IID-game assumption.
    The population target is the same mixture functional in both cases.
    """
    if type(trials) is not int or trials < 2:
        raise ValueError("at least two coverage trials required")
    rates = [np.full(8, p) for p in (0.1, 0.7)]
    expectations = [list(exact_independent_reference(p)["expected_components"].values()) for p in rates]
    target = float(component_ratio(np.mean(expectations, axis=0)))
    covered = available = 0
    for _ in range(trials):
        latent = rng.integers(2, size=1 if shared_latent else games_per_trial)
        probabilities = np.array([rates[i] for i in latent])
        if shared_latent:
            probabilities = np.repeat(probabilities, games_per_trial, axis=0)
        games = (rng.random(probabilities.shape) < probabilities).astype(int)
        result = whole_game_interval(game_components(games), rng, resamples=resamples)
        interval = result["interval"]
        if interval is not None:
            available += 1
            covered += interval[0] <= target <= interval[1]
    coverage = covered / trials
    mc_interval = binomtest(int(covered), trials).proportion_ci(confidence_level=0.95)
    return {"target": target, "target_definition": "ratio_of_expected_game_components",
            "nominal_coverage": 0.95, "trials": trials, "games_per_trial": games_per_trial,
            "resamples": resamples, "shared_latent_between_games": shared_latent,
            "covered_trials": int(covered), "available_intervals": available,
            "unavailable_fraction": 1 - available / trials,
            "coverage_counting_unavailable_as_missed": coverage,
            "coverage_monte_carlo_se": float(np.sqrt(coverage * (1 - coverage) / trials)),
            "coverage_monte_carlo_binomial_95_interval": [mc_interval.low, mc_interval.high]}


def run_study(*, seed=20261102, games=4000, trials=200, resamples=399):
    """Deterministic synthetic-only study; one sequential NumPy PCG64 stream."""
    rng = np.random.default_rng(seed)
    n = 200
    scenarios = {
        "independent_constant": (np.full(n, 0.2), 0.0),
        "independent_step": (np.repeat([0.05, 0.5], n // 2), 0.0),
        "independent_smooth": (np.linspace(0.03, 0.6, n), 0.0),
        "independent_alternating": (np.tile([0.05, 0.5], n // 2), 0.0),
        "history_excitation": (np.full(n, 0.1), 0.3),
        "history_inhibition": (np.full(n, 0.3), -0.25),
        "independent_rare": (np.full(n, 0.002), 0.0),
    }
    summaries = {}
    for name, (rates, delta) in scenarios.items():
        summaries[name] = {
            "probabilities": rates.tolist(), "history_delta": delta,
            **distribution_summary(simulate_games(rng, rates, games, history_delta=delta)),
        }
    probabilities = [0.1, 0.15, 0.2, 0.25, 0.6, 0.65, 0.7, 0.75]
    exact = exact_independent_reference(probabilities)
    sample = simulate_games(rng, probabilities, max(games, 20000))
    values = component_ratio(game_components(sample))
    defined = values[np.isfinite(values)]
    mass_errors = [abs(float((values == row["wmi"]).mean()) - row["probability"])
                   for row in exact["distribution"]]
    return {
        "schema_version": "synthetic-mathematics-v1", "seed": seed,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "scipy": scipy.__version__, "generator": "PCG64",
                     "metric": "legacy-global-truncated-two-neighbor",
                     "parser": "none; generated binary sequences",
                     "simulation_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     "metric_source_sha256": hashlib.sha256(Path(metrics.__file__).read_bytes()).hexdigest()},
        "scientific_status": "synthetic diagnostics only; not independent reconstruction validation",
        "scenarios": summaries,
        "exact_nonstationary_reference": exact,
        "reference_monte_carlo": {
            **distribution_summary(sample),
            "conditional_mean_monte_carlo_se": float(defined.std(ddof=1) / np.sqrt(len(defined))),
            "undefined_fraction_monte_carlo_se": float(np.sqrt(
                exact["undefined_probability"] * (1 - exact["undefined_probability"]) / len(values))),
            "max_absolute_distribution_mass_error": max(mass_errors),
        },
        "coverage": {
            "iid_games": coverage_experiment(rng, trials=trials, resamples=resamples),
            "sparse_games": coverage_experiment(rng, trials=trials, games_per_trial=8, resamples=resamples),
            "dependent_games_failure": coverage_experiment(rng, trials=trials, resamples=resamples,
                                                          shared_latent=True),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory; never overwritten")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--games", type=int, default=4000)
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--resamples", type=int, default=399)
    args = parser.parse_args()
    if args.games < 2 or args.trials < 2 or args.resamples < 2:
        parser.error("games, trials and resamples must each be at least two")
    if args.output.exists():
        parser.error("output directory already exists; choose a new directory")
    result = run_study(seed=args.seed, games=args.games, trials=args.trials, resamples=args.resamples)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "simulation_summary.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
