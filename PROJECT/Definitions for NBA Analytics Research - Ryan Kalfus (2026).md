# Definitions for NBA Analytics Research - Ryan Kalfus (2026)

## Purpose
- This file defines project rules, terms, variables, statistics, indexes, and formulas.
- This file is not a log.
- This file should not list saved outputs, scripts, or calculation files.
- If a variable or statistic has a formula, the formula must be shown here.

## Most Important Rules
- One possession means one team controls the ball in live play.
- Offensive fouls end possessions.
- Offensive fouls do not count as defensive fouls for this project.
- `last2` and `next2` always use global game possession order.
- `last2` and `next2` do not filter by offense team or defense team.

## Metric Map
- `WMI`: the direct ratio formula using `M_t`.
- WMI is presented game-by-game.
- Completed-game comparison sets may be used for game percentiles and distribution context.

## Possession Definition
- A possession starts when a team gains live-ball control.
- A possession ends when control changes to the other team or the period ends.

## Possession Starts
- Opening tip control.
- Possession after opponent made field goal.
- Possession after final made free throw when control changes.
- Defensive rebound.
- Steal or turnover that gives control.
- Jump ball won with clear control.
- Start of a period when a team first gains control.

## Possession Ends
- Made field goal.
- Offensive foul.
- Offensive turnover or violation.
- Defensive rebound by the opponent after a missed shot.
- Opponent wins jump-ball control.
- Final free throw sequence where control goes to the opponent.
- End of period.

## Possession Continues
- Defensive foul where the offense keeps the ball.
- Free throws from defensive fouls.
- Offensive rebound by the same offense.
- Timeout, substitution, review, or other dead-ball admin event if control does not change.
- Technical free throw if it does not change who gets the next live-ball possession.

## Defensive Foul Definition
A defensive foul counts only when all of these are true:
- `actionType == "foul"`
- the foul is committed by the defending team for that possession
- `subType` is not `offensive`
- `subType` is not `technical`
- `subType` is not `double technical`

## Shared Variables

### `t`
- The current possession number in game order.

### `F_t`
- Foul indicator for possession `t`.
- `F_t = 1` if there is at least one counted defensive foul on possession `t`.
- `F_t = 0` otherwise.

### `L_t`
- Recent-foul indicator before possession `t`.
- `L_t = 1` if at least one of the previous two possessions had `F_t = 1`.
- `L_t = 0` otherwise.
- This is global possession history, not team-specific history.

### `N_t`
- Follow-up foul indicator after possession `t`.
- `N_t = 1` if at least one of the next two possessions has `F_t = 1`.
- `N_t = 0` otherwise.
- This is global possession order, not team-specific order.

### `M_t`
- Momentum score for possession `t`.
- Formula:

`M_t = F_t + F_t*N_t`

Meaning:
- `M_t = 0` when there is no foul on the current possession.
- `M_t = 1` when there is a foul on the current possession, but no counted foul in the next two possessions.
- `M_t = 2` when there is a foul on the current possession and at least one counted foul in the next two possessions.

### `n1`
- Number of possessions where `L_t = 1`.

### `n0`
- Number of possessions where `L_t = 0`.

## Context Variables

### `seconds_left_in_game`
- Seconds remaining in the game at the possession reference point.
- Larger values mean earlier in the game.
- Smaller values mean later in the game.

### `score_difference`
- Offensive team score minus defensive team score.
- Positive value means the offense is leading.
- Negative value means the offense is trailing.
- Example: `score_difference = 5` means the offense is ahead by 5.

### `score_margin`
- Absolute value of `score_difference`.
- Formula:

`score_margin = abs(score_difference)`

Meaning:
- measures how far apart the teams are, ignoring who is ahead.

### `period`
- Game period number.
- `1`, `2`, `3`, and `4` are regulation quarters.
- `5+` means overtime.

### `period_bucket`
- Simplified period label.
- `period_bucket = "1"` for period 1.
- `period_bucket = "2"` for period 2.
- `period_bucket = "3"` for period 3.
- `period_bucket = "4"` for period 4.
- `period_bucket = "OT"` for period 5 or later.

### `offense_team`
- Team with the ball on the current possession.

### `defense_team`
- Team defending on the current possession.

## WMI

### Definition
- `WMI` is the direct, unadjusted Whistle Momentum Index.
- It compares average `M_t` after recent foul history to average `M_t` without recent foul history.

### Formula
Use this exact formula:

`WMI = [(1 / n1) * sum(M_t where L_t = 1)] / [(1 / n0) * sum(M_t where L_t = 0)]`

Equivalent wording:
- numerator = average `M_t` for possessions where `L_t = 1`
- denominator = average `M_t` for possessions where `L_t = 0`
- `WMI = numerator / denominator`

### Interpretation
- `WMI > 1`: more whistle momentum after recent fouls.
- `WMI = 1`: no WMI difference.
- `WMI < 1`: less whistle momentum after recent fouls.

### Important Notes
- `WMI` does not adjust for score, time, period, team, or intentional-foul situations.
- `WMI` is useful as a simple first look.
- `WMI` should not be treated as proof by itself.

## Diagnostic Terms

### Game-Level WMI
- A game-level WMI value is one `WMI` value calculated from possessions in one game.
- Public labels should call the metric `WMI`.

### Game Comparison Terms
- A completed-game comparison set is a table with one WMI value per completed game.
- `wmi_percentile` ranks one game's WMI within the completed-game WMI distribution.
- Comparison sets are support context for game interpretation.
- Comparison sets are not a separate pooled season-level WMI edition.

## Interpretation Guardrails
- WMI measures whistle-pattern behavior, not referee intent.
- WMI can suggest patterns that deserve review.
- WMI cannot prove bias by itself.
- Definitions should stay stable unless the project intentionally changes the metric.
