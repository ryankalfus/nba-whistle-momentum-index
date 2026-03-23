# nba-whistle-momentum-index

## Current Status
- Possession builder script: `step2_build_possessions.py`
- Current sample output: `possessions_step2_sample.csv`
- Possession model is now "Film-Aligned v2" (rewritten definitions).
- Parser uses NBA `possession` field for ownership anchor, then live-ball event timing for windows.
- `end_time` now uses the possession's own final live-ball event (not next possession start).
- `start_time` is now chained from previous possession `end_time` across all possessions.
- Possession foul fields now are:
  - `defensive_foul_count`
  - `defensive_foul_teams`

## Reusable Single-Game WMI_raw Scripts
- Build any-game possession table:
  - `python build_possession_model_table_game.py --game-id 0022500802`
- Build + calculate any-game raw WMI:
  - `python calculate_wmi_rawgame_any_game.py --game-id 0022500802`
- Old fixed-game OKC/MIL scripts are still kept as wrappers for the saved example outputs.
