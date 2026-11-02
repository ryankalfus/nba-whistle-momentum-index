"""Independent mathematical contracts for the synthetic study."""

from itertools import product

import numpy as np
import pytest

from whistle_research.metrics import calculate_wmi
from whistle_research.simulations import (
    component_ratio,
    coverage_experiment,
    distribution_summary,
    exact_independent_reference,
    expected_independent_components,
    game_components,
    run_study,
    simulate_games,
    whole_game_interval,
)


def test_vector_components_match_exact_metric_exhaustively():
    for length in range(1, 9):
        games = np.array(list(product((0, 1), repeat=length)))
        components = game_components(games)
        values = component_ratio(components)
        for f, c, value in zip(games, components, values, strict=True):
            result = calculate_wmi(f.tolist(), game_id="synthetic")
            assert c.tolist() == [result.sum_m0, result.n0, result.sum_m1, result.n1]
            if result.wmi is None:
                assert np.isnan(value)
            else:
                assert value == pytest.approx(result.wmi)


def test_exact_two_possession_distribution_hand_calculated():
    # Only 11 has positive WMI: M=(2,1), L=(0,1), WMI=1/2.
    # 10 is defined with zero WMI; 00 and 01 have no L1 group.
    result = exact_independent_reference([0.25, 0.75])
    assert result["undefined_probability"] == 0.75
    assert result["distribution"] == [
        {"wmi": 0.0, "wmi_fraction": "0", "probability": 0.0625},
        {"wmi": 0.5, "wmi_fraction": "1/2", "probability": 0.1875},
    ]
    assert result["conditional_mean_wmi_given_defined"] == 0.375
    # E S0 = p1(1+p2)+(1-p1)p2; E N0=2-p1;
    # E S1=p1*p2; E N1=p1.
    expected = [1.0, 1.75, 0.1875, 0.25]
    assert list(result["expected_components"].values()) == expected
    assert result["ratio_of_expected_components"] == 1.3125
    assert result["ratio_of_expected_components"] != result["conditional_mean_wmi_given_defined"]


def test_exact_nonstationary_distribution_matches_seeded_monte_carlo():
    probabilities = [0.1, 0.4, 0.8, 0.2, 0.7]
    exact = exact_independent_reference(probabilities)
    games = simulate_games(np.random.default_rng(451), probabilities, 100000)
    values = component_ratio(game_components(games))
    assert abs(np.isnan(values).mean() - exact["undefined_probability"]) < 0.006
    for row in exact["distribution"]:
        # 0.006 exceeds six maximal binomial MC standard errors at n=100000.
        assert abs((values == row["wmi"]).mean() - row["probability"]) < 0.006
    assert sum(row["probability"] for row in exact["distribution"]) + exact["undefined_probability"] == pytest.approx(1)


def test_history_process_is_past_only_and_has_declared_transition():
    # Probability 0.2 on empty history and exactly 1 on a positive history.
    games = simulate_games(np.random.default_rng(99), [0.2] * 10, 10000, history_delta=0.8)
    for game in games:
        if game.any():
            first = np.argmax(game)
            assert game[first:].all()
    full = simulate_games(np.random.default_rng(11), [0.2] * 8, 20, history_delta=0.3)
    # Changing future rates cannot alter earlier outcomes with same draws/shape.
    changed = simulate_games(np.random.default_rng(11), [0.2] * 4 + [0.9] * 4, 20, history_delta=0.3)
    assert np.array_equal(full[:, :4], changed[:, :4])


def test_undefined_games_remain_in_distribution_and_bootstrap_accounting():
    games = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    summary = distribution_summary(games)
    assert summary["games"] == 4
    assert summary["undefined_count"] == 2
    assert summary["undefined_fraction"] == 0.5
    assert summary["conditional_mean_wmi_given_defined"] == 0.25
    result = whole_game_interval(game_components(games), np.random.default_rng(1), resamples=500)
    assert result["undefined_resamples"] > 0
    assert result["interval"] is None


def test_resampling_preserves_joint_whole_game_components():
    # All games have different exposures, identical within-game ratio 2.
    # Joint resampling must give a point interval at 2, not artificial variance.
    components = np.array([[1, 2, 2, 2], [3, 6, 6, 6], [7, 14, 14, 14]])
    result = whole_game_interval(components, np.random.default_rng(77), resamples=100)
    assert result["estimate"] == 2
    assert result["interval"] == [2, 2]
    assert result["undefined_resamples"] == 0


def test_coverage_retains_failed_intervals_and_reports_mc_error():
    result = coverage_experiment(np.random.default_rng(981), trials=20, games_per_trial=2, resamples=50)
    assert result["available_intervals"] < result["trials"]
    p = result["covered_trials"] / 20
    assert result["coverage_counting_unavailable_as_missed"] == p
    assert result["coverage_monte_carlo_se"] == pytest.approx(np.sqrt(p * (1 - p) / 20))


@pytest.mark.parametrize("rates", [[], [np.nan], [1.1], [-0.1], [[0.2]], [0.2] * 17])
def test_exact_reference_rejects_invalid_or_unbounded_enumeration(rates):
    with pytest.raises(ValueError):
        exact_independent_reference(rates)


@pytest.mark.parametrize("games", [[[0, 2]], [[np.nan]], [], [0, 1]])
def test_components_reject_unknown_or_nonmatrix_outcomes(games):
    with pytest.raises(ValueError):
        game_components(games)


def test_study_reproducible_and_covers_all_required_processes():
    first = run_study(seed=4, games=20, trials=2, resamples=10)
    second = run_study(seed=4, games=20, trials=2, resamples=10)
    assert first == second
    assert set(first["scenarios"]) == {
        "independent_constant", "independent_step", "independent_smooth",
        "independent_alternating", "history_excitation", "history_inhibition", "independent_rare",
    }
    assert set(first["coverage"]) == {"iid_games", "sparse_games", "dependent_games_failure"}


@pytest.mark.parametrize("rates", [[0.25, 0.75], [0.1] * 8, [0, 1, 0, 1],
                                   [0.1, 0.2, 0.7, 0.6, 0.2]])
def test_analytic_disjoint_window_expectations_match_exact_enumeration(rates):
    exact = exact_independent_reference(rates)
    assert expected_independent_components(rates) == pytest.approx(
        list(exact["expected_components"].values())
    )


def test_cli_refuses_existing_output_without_touching_it(tmp_path, monkeypatch):
    from whistle_research.simulations import main

    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "simulation_summary.json"
    sentinel.write_text("existing scientific artifact\n")
    monkeypatch.setattr("sys.argv", ["simulations", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert sentinel.read_text() == "existing scientific artifact\n"


def test_zero_rate_reference_keeps_all_undefined_mass():
    result = exact_independent_reference([0, 0, 0])
    assert result["undefined_probability"] == 1
    assert result["conditional_mean_wmi_given_defined"] is None
    assert result["ratio_of_expected_components"] is None
    assert result["distribution"] == []
