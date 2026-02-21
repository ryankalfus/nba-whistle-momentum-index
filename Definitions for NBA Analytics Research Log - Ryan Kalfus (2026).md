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
