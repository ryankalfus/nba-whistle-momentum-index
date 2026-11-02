from itertools import product
from fractions import Fraction

import pytest

from whistle_research.metrics import calculate_wmi


def test_hand_calculated_global_window_and_components():
    result = calculate_wmi([1, 0, 1, 1, 0], game_id="g")
    assert [(r.L_t, r.F_t, r.N_t, r.M_t) for r in result.rows] == [
        (0, 1, 1, 2),
        (1, 0, 1, 0),
        (1, 1, 1, 2),
        (1, 1, 0, 1),
        (1, 0, 0, 0),
    ]
    assert (result.n0, result.n1, result.sum_m0, result.sum_m1) == (1, 4, 2, 3)
    assert result.wmi == 0.375
    assert result.immediate_ratio == 0.5
    assert result.continuation_ratio == 0.75


def test_exhaustive_short_sequences_exact_ratio_and_factorization():
    for length in range(9):
        for f in product((0, 1), repeat=length):
            result = calculate_wmi(f, game_id="g")
            # Independent pair-distance definition: any positive neighbor at
            # distance one/two; no slicing or period/team resetting.
            weighted = {0: [], 1: []}
            for i, value in enumerate(f):
                past = int(any(j < i and i - j <= 2 and f[j] for j in range(length)))
                future = int(any(j > i and j - i <= 2 and f[j] for j in range(length)))
                weighted[past].append(value * (1 + future))
            if weighted[0] and weighted[1] and sum(weighted[0]):
                exact = Fraction(sum(weighted[1]), len(weighted[1])) / Fraction(
                    sum(weighted[0]), len(weighted[0])
                )
                assert result.wmi == float(exact)
                if result.continuation_ratio is not None:
                    assert result.wmi == pytest.approx(
                        result.immediate_ratio * result.continuation_ratio
                    )
            else:
                assert result.wmi is None
                assert result.missing_reasons


def test_zero_numerator_does_not_require_defined_continuation():
    r = calculate_wmi([1, 0, 0], game_id="g")
    assert r.wmi == 0
    assert r.q1 is None
    assert "q1_no_foul_observations" in r.missing_reasons


@pytest.mark.parametrize(
    "f", [[None], [float("nan")], [2], [-1], [0.0], ["1"], [{"game_id": "g"}]]
)
def test_unknown_or_nonbinary_outcomes_are_rejected(f):
    with pytest.raises(ValueError):
        calculate_wmi(f, game_id="g")


def test_game_id_and_empty_group_are_explicit():
    with pytest.raises(ValueError):
        calculate_wmi([0], game_id="")
    assert "empty_L1_group" in calculate_wmi([], game_id="g").missing_reasons
