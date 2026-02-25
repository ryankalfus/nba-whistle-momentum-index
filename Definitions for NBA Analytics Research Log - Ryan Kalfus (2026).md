# Definitions for NBA Analytics Research Log - Ryan Kalfus (2026)

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

## Z-Score Layer (Planned Diagnostic)
- Keep possession-level WMI as the primary metric.
- For each game, compute game-level WMI from possessions in that game.
- Across all games, compute:
  - `mean_game_wmi`
  - `std_game_wmi`
  - `wmi_z_score = (game_wmi - mean_game_wmi) / std_game_wmi`
- Use `wmi_z_score` only as an outlier/flagging metric, not standalone proof of ref bias.

## Controlled WMI Note
- In logistic form: `logit(P(def_foul_t=1)) = a + b*trigger_t + controls`.
- `b` is the isolated trigger effect after controls.
- `exp(b)` is the controlled WMI multiplier:
  - `exp(b) = 1.00` means no trigger effect after controls.
  - `exp(b) > 1.00` means higher foul odds with trigger.
  - `exp(b) < 1.00` means lower foul odds with trigger.

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

## WMI Raw Game Formula (Current)
Use this exact formula:
WMI_rawgame = [ (1 / n1) * ∑_(t: L_t=1) M_t ] / [ (1 / n0) * ∑_(t: L_t=0) M_t ]

Notes:
- This is one whole-game value.
- This is currently raw WMI only (no controls yet).
- `n1` = count of possessions with `L_t = 1`.
- `n0` = count of possessions with `L_t = 0`.
- Current definition supersedes older relevant-team last2/next2 definitions.
