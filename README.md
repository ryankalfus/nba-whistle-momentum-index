# NBA Whistle Momentum Index

This project studies whether NBA defensive foul calls show short-term whistle momentum at the possession level.

The current work includes:
- `WMI_raw`: direct possession-window ratio using `L_t`, `F_t`, `N_t`, and `M_t`.
- `WMI_controlled`: context-aware version using score, time, period, offense, defense, and controlled exclusions.
- Game-level, season-level, and completed-game-list outputs.

Start with the project guide in `PROJECT/PROJECT.md`, then the definitions document in `PROJECT/Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`.

Useful checks:

```bash
pytest -q
ruff check .
```

Useful examples:

```bash
python calculate_wmi_rawgame_any_game.py --game-id 0022500802
python calculate_wmi_controlledgame_any_game.py --game-id 0022500802
python plot_wmi_rawgame_distribution_2025_26.py
```

WMI should be interpreted as whistle-pattern behavior, not proof of referee intent.

