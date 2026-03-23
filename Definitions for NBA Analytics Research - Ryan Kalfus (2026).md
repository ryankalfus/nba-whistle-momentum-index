# Definitions for NBA Analytics Research - Ryan Kalfus (2026)

## ***Defined rules/terms/variables/statistics/indexes for this project go here. Add to / change / remove when a something is defined, variable or anything is redefined, or something else happens that should inquire a formal definition***

## *If a variable/stat/anything has a defined formula/equation, make sure to write it in its definition, while also explaining what it means, and any subterms inside such equations must be defined.*

**This is not PURELY a LOG**

## Core Possession Rule
- One possession = one team controls the ball in live play.
- A possession ends when control changes to the other team, or the period ends.

## Critical Project Rule (Important)
- **Offensive fouls end possessions.**
- **Offensive fouls do NOT count as defensive fouls for this project.**

## Possession Starts
- Team controls opening tip.
- Team gains control after opponent made FG or final made FT.
- Defensive rebound.
- Steal/turnover that gives control.
- Jump ball won with clear control.
- Start of period when first team gains control.

## Possession Ends
- Made field goal.
- Offensive foul by offense (charge, illegal screen, etc.).
- Offensive turnover/violation by offense.
- Defensive rebound by opponent after miss.
- Opponent wins jump ball control.
- End of period.
- Final free throw sequence where control goes to opponent.

## Possession Continues (No New Possession)
- Defensive foul where offense keeps/retains ball.
- Free throws from defensive fouls.
- Offensive rebound by same offense.
- Timeouts, substitutions, reviews, dead-ball admin (if control does not change).
- Technical FT events that do not change who gets next live-ball control.

## Defensive Foul Metrics

### `defensive_foul_count`
Count only fouls where:
- `actionType == "foul"`
- foul team is defending team for that possession
- `subType` is not `offensive`, `technical`, or `double technical`

### `defensive_foul_teams`
- Team code(s) that committed defensive fouls in that possession.
- Pipe-separated if multiple values appear.

## Code Mapping (Current Parser)
- Ownership anchor: NBA live feed `possession` field.
- One possession row per continuous segment of same `possession` team.
- `start_time`: end time of previous possession (continuous possession timeline across full game).
- `end_time`: final live-ball event in that same possession segment.
- This means after an offensive foul ends possession `t`, possession `t+1` starts immediately at that foul sequence time.
- If multiple events share same clock timestamp, parser adds `+0.001` sequence offsets to preserve event order.

## Current Step Output (Defensive Foul Context Rows)
- File: `def_foul_context_okc_mil.csv`
- Each row is one defensive foul event.
- `last2` / `next2` are global possession windows (team-agnostic):
  - `last2` = previous two possessions in game order.
  - `next2` = next two possessions in game order.
- Columns:
  - `def_foul_num`: sequential defensive foul event number in game order.
  - `offense_team`: offensive team tricode on the foul event row.
  - `defense_team`: defensive team tricode (team committing the defensive foul).
  - `seconds_left_in_game`: game seconds remaining at that foul event.
  - `score_difference`: offensive team score minus defensive team score at that foul event.
  - `def_foul_called_in_last2_possessions`: `1` if at least one of the previous two possessions had a defensive foul.
  - `def_foul_called_in_next2_possessions`: `1` if at least one of the next two possessions has a defensive foul.
  - `L_t`: same value as `def_foul_called_in_last2_possessions`.
  - `F_t`: always `1` in this file (because each row is a defensive foul event).
  - `N_t`: same value as `def_foul_called_in_next2_possessions`.
  - `M_t = F_t + F_t*N_t` (in this file this equals `1 + N_t`, so values are `1` or `2`).

## Z-Score Layer (Current Diagnostic)
- Keep possession-level `WMI_raw` as the primary current metric.
- For each game, compute game-level `WMI_rawgame` from possessions in that game.
- Across all games, compute:
  - `mean_game_wmi_raw`
  - `std_game_wmi_raw`
  - `wmi_raw_z_score = (game_wmi_raw - mean_game_wmi_raw) / std_game_wmi_raw`
- Use `wmi_raw_z_score` only as an outlier/flagging metric, not standalone proof of ref bias.
- Current game-list output:
  - `wmi_rawgames_2025_26_asof_2026_03_23.csv` with one row per completed 2025-26 regular-season game so far, including `WMI_rawgame` and `wmi_rawgame_z_score`.

## Controlled WMI Note
- Current headline controlled model is regression-based `WMI`, separate from `WMI_raw`.
- Main current controlled trigger: `L_count_t`.
- Main current interpretation target:
  - odds ratio above `1` = higher adjusted odds of a defensive foul on the current possession
  - odds ratio below `1` = lower adjusted odds of a defensive foul on the current possession

## All-Possession Modeling Table (Current)
- File: `possession_model_table_okc_mil.csv`
- Each row is one possession.
- Variables:
  - `L_t`: foul in the last 2 possessions (0/1)
  - `F_t`: foul on current possession (0/1)
  - `N_t`: foul in the next 2 possessions (0/1)
  - `M_t = F_t + F_t*N_t` (values 0/1/2)
- Additional context columns:
  - `seconds_left_in_game`
  - `score_difference`
  - `offense_team`, `defense_team`

## Controlled Modeling Table (Current)
- File: `wmi_controlled_table_2025_26_asof_2026_03_23.csv`
- Each row is one possession from a completed 2025-26 regular-season game.
- Current columns:
  - `game_id`
  - `game_date_et`
  - `offense_team`
  - `defense_team`
  - `period`
  - `period_bucket`
  - `seconds_left_in_game`
  - `score_difference`
  - `L_t`
  - `L_count_t`
  - `F_t`
  - `N_t`
  - `M_t`
  - `intentional_foul_excluded_t`

## Controlled Variable Definitions (Current)
- `L_count_t`:
  - count of possessions with a defensive foul in the last 2 possessions
  - possible values: `0`, `1`, `2`
- `period_bucket`:
  - periods `1`, `2`, `3`, `4` stay as their own buckets
  - periods `5+` are grouped as `OT`
- `intentional_foul_excluded_t`:
  - equals `1` when the possession is excluded from the headline controlled model
  - current rule:
    - `F_t == 1`
    - `period_bucket` is `4` or `OT`
    - `seconds_left_in_game <= 45`
    - `score_difference >= 3`
  - otherwise equals `0`

## WMI_raw Game Formula (Current)
Use this exact formula:
WMI_rawgame = [ (1 / n1) * ∑_(t: L_t=1) M_t ] / [ (1 / n0) * ∑_(t: L_t=0) M_t ]

Notes:
- This is one whole-game value.
- This is currently raw WMI only (no controls yet).
- `n1` = count of possessions with `L_t = 1`.
- `n0` = count of possessions with `L_t = 0`.
- Current definition supersedes older relevant-team last2/next2 definitions.

## Metric Naming (Current vs Future)
- `WMI_raw` = current implemented metric (equation above).
- `WMI` = current controlled metric from logistic regression.

## Controlled WMI Formula (Current v1)
- Main model formula:
  - `F_t ~ L_count_t + seconds_left_in_game + score_difference + C(period_bucket) + C(offense_team) + C(defense_team)`
- Headline reported controlled value:
  - `odds_ratio_trigger = exp(beta_L_count_t)`
- Interpretation:
  - each `+1` increase in `L_count_t` changes the odds of `F_t = 1` by the multiplier `odds_ratio_trigger`, holding listed controls fixed

## Season-Level WMI_raw (Pooled)
- Same formula as game-level raw WMI, but computed on one combined possession table across all season games.
- Current season summary outputs:
  - `wmi_rawseason_2024_25_summary.csv` with `WMI_rawseason_pooled = 0.978645`.
  - `wmi_rawseason_2025_26_summary_asof_2026_03_01.csv` with `WMI_rawseason_pooled = 0.949847`.
  - `wmi_rawseason_2010_11_to_2023_24.csv` with pooled season values for available seasons in requested range (`2020-21` to `2023-24` in current source).
  - `wmi-calculations-log.md` for top-line `WMI_raw` values.
- Requested seasons `2010-11` to `2018-19` are currently unavailable in this CDN play-by-play source used by this project run.
