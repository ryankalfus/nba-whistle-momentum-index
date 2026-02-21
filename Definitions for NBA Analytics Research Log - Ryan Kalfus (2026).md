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
​
Possession Outcome—Ended in Defensive Foul:​
A possession is classified as “ended in defensive foul” if:
- The final live-ball event of the possession is a defensive foul committed by the defending team.
- The foul is not classified as offensive.
- The foul results in free throws or stoppage.
Offensive fouls are explicitly excluded from this classification.


Relevant Prior Possessions:
For each possession Pt, we consider the two most recent possessions where:
- The opposing team was on offense.
- Those possessions were completed prior to Pt
- We examine whether either of those two possessions ended in a defensive foul committed against that -
team.
Offensive fouls are ignored entirely.
Indicator Variable—Prior Opposite-End Foul:
For each possession Pt:
PriorOppEndFoult = 1
if at least one of the previous two opposing-team possessions ended in a defensive foul.​
Otherwise:
PriorOppEndFoult = 0
