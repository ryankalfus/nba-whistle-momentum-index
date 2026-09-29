"""Coverage stress test for raw-sequence circular block WMI intervals.

Targets the ratio of expected sufficient statistics for a length-200 game under
specified processes. Synthetic coverage is not proof of validity in real games.
"""

import itertools

import numpy as np
import pandas as pd

from validate_wmi import OUT, SEED


BITS = np.asarray(list(itertools.product([0, 1], repeat=5)))


def ratio(f):
    f = np.asarray(f)
    recent = np.zeros_like(f)
    future = np.zeros_like(f)
    for lag in (1, 2):
        recent[..., lag:] |= f[..., :-lag]
        future[..., :-lag] |= f[..., lag:]
    m = f * (1 + future)
    n1 = recent.sum(axis=-1)
    n0 = f.shape[-1] - n1
    s1 = (m * recent).sum(axis=-1)
    s0 = (m * (1 - recent)).sum(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (s1 / n1) / (s0 / n0)


def oracle(n, p01, p11, rates=None):
    totals = np.zeros(4)
    stationary = p01 / (1 - p11 + p01)
    for t in range(n):
        valid = [j for j in range(5) if 0 <= t + j - 2 < n]
        probability = np.ones(32)
        for j in range(5):
            if j not in valid:
                probability *= BITS[:, j] == 0
            else:
                if rates is not None:
                    p = rates[t + j - 2]
                elif j == valid[0]:
                    p = stationary
                else:
                    p = np.where(BITS[:, j - 1], p11, p01)
                probability *= np.where(BITS[:, j], p, 1 - p)
        recent = BITS[:, :2].max(axis=1)
        m = BITS[:, 2] * (1 + BITS[:, 3:].max(axis=1))
        totals += [
            probability @ recent,
            probability @ (1 - recent),
            probability @ (m * recent),
            probability @ (m * (1 - recent)),
        ]
    return (totals[2] / totals[0]) / (totals[3] / totals[1])


def run(simulations=400, bootstrap_reps=300):
    rng = np.random.default_rng(SEED)
    n = 200
    scenarios = [
        ("independent_low", 0.08, 0.08, None),
        ("independent_typical", 0.16, 0.16, None),
        ("positive_dependence", 0.12, 0.32, None),
        ("strong_dependence", 0.08, 0.50, None),
        ("negative_dependence", 0.23, 0.05, None),
        ("rate_shift", 0.16, 0.16, np.r_[np.full(100, 0.05), np.full(100, 0.35)]),
    ]
    rows = []
    for name, p01, p11, rates in scenarios:
        truth = oracle(n, p01, p11, rates)
        samples = np.zeros((simulations, n), dtype=np.int8)
        for t in range(n):
            p = (
                rates[t]
                if rates is not None
                else (
                    p01 / (1 - p11 + p01)
                    if t == 0
                    else np.where(samples[:, t - 1], p11, p01)
                )
            )
            samples[:, t] = rng.random(simulations) < p
        for block in [5, 10, 20]:
            covered = 0
            valid = 0
            widths = []
            for f in samples:
                starts = rng.integers(0, n, (bootstrap_reps, int(np.ceil(n / block))))
                indices = ((starts[:, :, None] + np.arange(block)) % n).reshape(
                    bootstrap_reps, -1
                )[:, :n]
                values = ratio(f[indices])
                values = values[np.isfinite(values)]
                if len(values) < bootstrap_reps * 0.95:
                    continue
                lo, hi = np.percentile(values, [2.5, 97.5])
                valid += 1
                covered += lo <= truth <= hi
                widths.append(hi - lo)
            rows.append(
                dict(
                    scenario=name,
                    block_length=block,
                    simulations=simulations,
                    valid_intervals=valid,
                    oracle_wmi=truth,
                    coverage=covered / valid if valid else None,
                    median_width=float(np.median(widths)),
                )
            )
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "interval_coverage.csv", index=False)
    text = """# Per-game interval coverage stress test

Candidate: circular moving-block bootstrap of the raw foul indicator, recomputing all WMI windows after concatenation. Game length 200, 400 synthetic games per scenario, 300 bootstrap draws per interval, seed 20260912. Blocks of 5/10/20 possessions are compared. The oracle is the ratio of expected sufficient statistics for each specified finite-length process, computed by enumerating local five-possession patterns. This is an inferential process parameter, not uncertainty about an already observed arithmetic game score.

| Scenario | Block | Valid / 400 | Coverage | Median width |
| --- | --- | --- | --- | --- |
"""
    for r in result.itertuples():
        text += f"| {r.scenario} | {r.block_length} | {r.valid_intervals} | {r.coverage:.1%} | {r.median_width:.3f} |\n"
    text += """
Nominal coverage is 95%; sampling error for 400 simulations is about 1.1 percentage points at nominal coverage. Circular joins can create artificial foul sequences, particularly when foul probability changes within a game. Finite denominators also make intervals unstable. No interval is released on the website from this experiment: the tested method must demonstrate acceptable coverage across plausible nonstationary basketball contexts, and the inferential target/assumptions must be explained to users. Other bootstrap constructions may behave differently. This is a stress test of one candidate, not evidence that all uncertainty methods fail.
"""
    (OUT / "interval_validation.md").write_text(text)
    report = OUT / "report.md"
    if report.exists():
        content = report.read_text().split("\n## Interval coverage validation")[0]
        content += f"\n## Interval coverage validation\n\nA raw-sequence circular block bootstrap was stress-tested on six specified processes, with 400 simulated games per process and 300 draws per interval. Empirical coverage for nominal 95% intervals ranged from {result.coverage.min():.1%} to {result.coverage.max():.1%}. No tested block length gave consistently adequate coverage across all scenarios. Per-game intervals therefore remain withheld; sample counts and denominator diagnostics are displayed instead. See [the coverage study](interval_validation.md) and [simulation results](interval_coverage.csv). This tests one candidate method, not every possible uncertainty estimator.\n"
        report.write_text(content)
    print(result.to_string(index=False))


if __name__ == "__main__":
    run()
