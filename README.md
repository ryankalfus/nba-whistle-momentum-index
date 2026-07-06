# NBA Whistle Momentum Index

NBA Whistle Momentum Index is a possession-level basketball analytics project that asks a simple question:

> After recent defensive foul calls, do NBA games show short-term changes in foul-call momentum?

The current public version is intentionally narrow. It uses one active metric, `WMI`, calculated game by game.

![WMI distribution](wmi_distribution_2020_21_to_2025_26.png)

## What WMI Measures

`WMI` compares whistle momentum after recent defensive fouls to whistle momentum without recent defensive fouls.

Core variables:

- `L_t`: equals `1` if at least one of the previous two possessions had a counted defensive foul.
- `F_t`: equals `1` if the current possession had a counted defensive foul.
- `N_t`: equals `1` if at least one of the next two possessions had a counted defensive foul.
- `M_t`: possession momentum score, defined as `F_t + F_t*N_t`.

Formula:

```text
WMI =
average(M_t where L_t = 1) / average(M_t where L_t = 0)
```

Interpretation:

- `WMI > 1`: more whistle momentum after recent fouls.
- `WMI ~= 1`: little or no difference.
- `WMI < 1`: less whistle momentum after recent fouls.

WMI is a pattern metric. It is not proof of referee intent, bias, or misconduct.

## Current Results

The active comparison dataset covers 2020-21 through the available 2025-26 snapshot.

- Games with WMI: `6,727`
- Mean `WMI`: `0.960619`
- Median `WMI`: `0.909180`
- Percentiles are stored as `wmi_percentile`

Main outputs:

- `wmi_games_2020_21_to_2025_26.csv`
- `wmi_distribution_2020_21_to_2025_26_summary.csv`
- `wmi_distribution_2020_21_to_2025_26_failures.csv`
- `wmi_distribution_2020_21_to_2025_26.png`

## Quick Start

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run checks:

```bash
ruff check .
pytest -q
```

Calculate one game:

```bash
python calculate_wmi_any_game.py --game-id 0022500802
```

Build a smoke-test distribution:

```bash
python build_wmi_distribution_2020_2026.py --max-games-per-season 2
```

Plot the 2025-26 snapshot:

```bash
python plot_wmi_distribution_2025_26.py
```

## MVP Website

The static MVP website is in `index.html` and `styles.css`. It is designed to run directly from the repository root and can be served by GitHub Pages.

Preview locally:

```bash
python -m http.server 8000
```

## Project Structure

- `wmi_utils.py`: shared possession parsing and WMI calculation logic.
- `calculate_wmi_any_game.py`: one-game WMI runner.
- `calculate_wmi_games_2025_26.py`: 2025-26 completed-game runner.
- `build_wmi_distribution_2020_2026.py`: multi-season WMI distribution builder.
- `tests/`: active test suite.
- `index.html` and `styles.css`: static MVP website.
- `PROJECT/`: formal definitions, project guide, and project history.
- `archive/controlled_experiments/`: paused controlled-WMI experiments, kept only as research history.

## Data Notes

The project uses publicly available NBA play-by-play data endpoints. Some game IDs are unavailable or incomplete through those endpoints; failures are logged explicitly in `wmi_distribution_2020_21_to_2025_26_failures.csv`.

The active product is game-by-game WMI. Completed-game lists are comparison context for percentiles and distribution plots, not a separate pooled season edition.

## Status

This is a v1 research release. The metric is intentionally simple, explainable, and scoped to completed games.
