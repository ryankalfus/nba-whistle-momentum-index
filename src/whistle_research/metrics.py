"""Exact per-game retrospective legacy WMI; no inference or imputation."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True)
class MetricRow:
    L_t: int
    F_t: int
    N_t: int
    M_t: int


@dataclass(frozen=True)
class MetricResult:
    game_id: str
    rows: tuple[MetricRow, ...]
    n0: int
    n1: int
    sum_m0: int
    sum_m1: int
    foul_count0: int
    foul_count1: int
    followup_count0: int
    followup_count1: int
    mean_m0: float | None
    mean_m1: float | None
    p0: float | None
    p1: float | None
    q0: float | None
    q1: float | None
    immediate_ratio: float | None
    continuation_ratio: float | None
    wmi: float | None
    missing_reasons: tuple[str, ...]


def calculate_wmi(fouls: Iterable[int], *, game_id: str) -> MetricResult:
    """Input must be one game's globally ordered binary sequence, across periods.

    The required game identifier prevents an implicit pooled edition. Callers own
    provenance and must not concatenate games under a fabricated identifier.
    """
    if not isinstance(game_id, str) or not game_id.strip():
        raise ValueError("one nonempty game_id is required")
    f = tuple(fouls)
    if any(type(v) not in (int, bool) or v not in (0, 1) for v in f):
        raise ValueError("fouls must contain only known binary integers")
    rows = tuple(
        MetricRow(
            int(any(f[max(0, i - 2) : i])),
            int(v),
            int(any(f[i + 1 : i + 3])),
            int(v) * (1 + int(any(f[i + 1 : i + 3]))),
        )
        for i, v in enumerate(f)
    )
    groups = [[r for r in rows if r.L_t == level] for level in (0, 1)]
    counts = [len(g) for g in groups]
    sums = [sum(r.M_t for r in g) for g in groups]
    positives = [sum(r.F_t for r in g) for g in groups]
    followups = [sum(r.F_t * r.N_t for r in g) for g in groups]
    reasons = []

    def ratio(a, b, reason):
        if b == 0:
            reasons.append(reason)
            return None
        return Fraction(a, b)

    means = [
        ratio(sums[level], counts[level], f"empty_L{level}_group") for level in (0, 1)
    ]
    ps = [
        ratio(positives[level], counts[level], f"p{level}_empty_group")
        for level in (0, 1)
    ]
    qs = [
        ratio(followups[level], positives[level], f"q{level}_no_foul_observations")
        for level in (0, 1)
    ]
    immediate = None
    if all(p is not None for p in ps):
        immediate = ratio(ps[1], ps[0], "immediate_zero_p0")
    continuation = (1 + qs[1]) / (1 + qs[0]) if all(q is not None for q in qs) else None
    wmi = None
    if all(m is not None for m in means):
        wmi = ratio(means[1], means[0], "wmi_zero_mean_L0")

    def convert(v):
        return None if v is None else float(v)

    return MetricResult(
        game_id,
        rows,
        counts[0],
        counts[1],
        sums[0],
        sums[1],
        positives[0],
        positives[1],
        followups[0],
        followups[1],
        *map(convert, [*means, *ps, *qs, immediate, continuation, wmi]),
        tuple(reasons),
    )
