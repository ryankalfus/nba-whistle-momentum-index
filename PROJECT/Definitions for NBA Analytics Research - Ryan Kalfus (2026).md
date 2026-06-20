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
- `WMI_raw`: the direct ratio formula using `M_t`.
- `WMI_controlled`: the controlled version of the same whistle-momentum idea.
- `WMI_controlled` should use the same core variables as `WMI_raw`, but should account for game context such as score margin, time left, period, offense team, defense team, and intentional-foul situations.
- This definitions file does not lock `WMI_controlled` to one statistical model. A specific model should be defined separately only when the project intentionally chooses one as final.

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

## WMI_raw

### Definition
- `WMI_raw` is the direct, unadjusted Whistle Momentum Index.
- It compares average `M_t` after recent foul history to average `M_t` without recent foul history.

### Formula
Use this exact formula:

`WMI_rawgame = [(1 / n1) * sum(M_t where L_t = 1)] / [(1 / n0) * sum(M_t where L_t = 0)]`

Equivalent wording:
- numerator = average `M_t` for possessions where `L_t = 1`
- denominator = average `M_t` for possessions where `L_t = 0`
- `WMI_rawgame = numerator / denominator`

### Interpretation
- `WMI_rawgame > 1`: more whistle momentum after recent fouls.
- `WMI_rawgame = 1`: no raw difference.
- `WMI_rawgame < 1`: less whistle momentum after recent fouls.

### Important Notes
- `WMI_raw` does not adjust for score, time, period, team, or intentional-foul situations.
- `WMI_raw` is useful as a simple first look.
- `WMI_raw` should not be treated as proof by itself.

## WMI_controlled

### Definition
- `WMI_controlled` is the context-aware version of Whistle Momentum Index.
- It should keep the same whistle-momentum idea as `WMI_raw`.
- It should account for game context that can affect foul patterns.

### Required Core Variables
Any `WMI_controlled` version should keep these raw variables:
- `L_t`
- `F_t`
- `N_t`
- `M_t`

### Required Context Variables
Any `WMI_controlled` version should consider:
- `seconds_left_in_game`
- `score_difference`
- `period_bucket`
- `offense_team`
- `defense_team`

### Score-Margin Exclusion
- Possessions with `score_margin >= 15` should be excluded from controlled WMI.
- Reason: large-margin situations can change how teams play and how fouls happen.

### Intentional-Foul Exclusion
A foul should be treated as likely intentional and excluded from controlled WMI when:
- `F_t = 1`
- the possession is in period 4 or overtime
- and either of these is true:
  - `seconds_left_in_game <= 35` and `score_difference > 3`
  - `seconds_left_in_game <= 15` and `score_difference >= 1`

Meaning:
- late-game fouls by a trailing defense can be strategy, not normal whistle momentum.

### Controlled-WMI Notes
- `WMI_controlled` should not be changed just to make it closer to `WMI_raw`.
- If `WMI_controlled` is lower than `WMI_raw`, that can mean some raw pattern was explained by game context.
- If the final controlled method uses a model, that model should be documented clearly where the project records implementation choices.
- This file defines what controlled WMI must account for, but it does not require one final model type.

## Diagnostic Terms

### Game-Level WMI
- A game-level WMI value is one WMI value calculated from possessions in one game.
  - Raw WMI: WMI_rawgame
  - Controlled WMI: WMI_controlledgame

### Season-Level WMI
- A season-level WMI value is one WMI value calculated from possessions across a season or season sample.
  - Raw WMI: WMI_rawseason
  - Controlled WMI: WMI_controlledseason

## Interpretation Guardrails
- WMI measures whistle-pattern behavior, not referee intent.
- WMI can suggest patterns that deserve review.
- WMI cannot prove bias by itself.
- Raw and controlled WMI answer related but different questions.
- Definitions should stay stable unless the project intentionally changes the metric.
