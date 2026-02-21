# Definitions for NBA Analytics Research Log - Ryan Kalfus (2026)

_Converted from PDF on 2026-02-21._

Possession start:​
A possession begins when a team gains exclusive control of the ball in live play.​
After a:
- A defensive rebound.
- A made field goal (opposing team inbound).
- A turnover.
- A steal.
- An offensive foul
- The start of a period.
- A jump ball that results in clear possession.
Exceptions:
- Offensive rebounds do NOT start a new possession.
- Technical fouls without change of possession do NOT start a new possession.


Possession end:
A possession ends when the offensive team relinquishes control of the ball in live play.​
After a:​
- A made field goal.
- A defensive rebound by the opposing team.
- A turnover.​
- An offensive foul.
- The end of a period.
Exceptions:
- Missed shots followed by an offensive rebound do NOT end possession.
- Loose-ball fouls that do not change possession do NOT end possession.​

Implementation note in code:
- Possession ownership is taken from NBA live feed field `possession`.
- A possession row starts when this field switches to a team.
- `end_time` is set to the next possession's `start_time` (or last event time for final possession).
​
Possession Outcome—Defensive Fouls in Possession:
For each possession, track:
- `defensive_foul_count`: number of defensive fouls committed by the defending team during that possession.
- `defensive_foul_teams`: team code(s) of the team(s) that committed those defensive fouls.
Rules:
- Include fouls where `actionType = foul` and subtype is not `offensive`.
- Offensive fouls are explicitly excluded.
- A possession can have zero, one, or multiple defensive fouls.


Relevant Prior Possessions:
For each possession Pt, we consider the two most recent possessions where:
- The opposing team was on offense.
- Those possessions were completed prior to Pt
- We examine whether either of those two possessions had at least one defensive foul (`defensive_foul_count > 0`) committed against that team.
Offensive fouls are ignored entirely.
Indicator Variable—Prior Opposite-End Foul:
For each possession Pt:
PriorOppEndFoult = 1
if at least one of the previous two opposing-team possessions had `defensive_foul_count > 0`.​
Otherwise:
PriorOppEndFoult = 0

