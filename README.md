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
- Current reusable raw-WMI helper module: `wmi_rawgame_utils.py`
- Current reusable controlled-WMI helper module: `wmi_controlled_utils.py`

## Reusable Single-Game WMI_raw Scripts
- Build any-game possession table:
  - `python build_possession_model_table_game.py --game-id 0022500802`
- Build + calculate any-game raw WMI:
  - `python calculate_wmi_rawgame_any_game.py --game-id 0022500802`
- Old fixed-game OKC/MIL scripts are still kept as wrappers for the saved example outputs.

## 2025-26 Game List Script
- Build the completed-game list for the season so far, with one `WMI_rawgame` per game plus z-scores:
  - `python calculate_wmi_rawgames_2025_26.py`

## 2025-26 Controlled WMI Script
- Build the pooled controlled table for completed 2025-26 regular-season games and fit the main controlled model:
  - `python calculate_wmi_controlled_2025_26.py`
- Main controlled model:
  - `F_t ~ L_count_t + seconds_left_in_game + score_difference + C(period_bucket) + C(offense_team) + C(defense_team)`
- Headline trigger:
  - `L_count_t` = number of foul possessions in the last 2 possessions (`0`, `1`, or `2`)
- Main intentional-foul exclusion rule:
  - exclude possession rows where `F_t == 1`, `period_bucket` is `4` or `OT`, `seconds_left_in_game <= 45`, and `score_difference >= 3`
