# Event-level spot checks

Reviewed directly against the commit-pinned CDN event descriptions. This is source-event adjudication, not video review or a complete independent audit of all games.

## ATL at BOS, 0022400001 (2024–25)

- Opening events 4–44: manually traced 14 possession starts at actions 4, 11, 13, 15, 16, 18, 20, 23, 24, 30, 32, 37, 39, 41. Counted foul possessions are 9 and 14.
- Offensive rebounds at actions 9 and 35 retain the current possession. The action-16/18/20 steals mark changes of ownership.
- Action 24: Brown shooting personal foul against Atlanta; Capela's attempts at actions 27 and 29 belong to the same possession. The defensive rebound at action 30 starts Boston's possession.
- First-quarter end actions 178–180: Atlanta shot/rebound/period end. Quarter-two substitutions at actions 181–186 retain a stale Atlanta ownership value. They must not independently create a possession.
- Second-quarter end action 358 changes ownership on a period-end row. Quarter-three substitutions 359–362 retain Atlanta ownership, while the period-start/action-364 Boston shot has Boston ownership. Administrative rows must not create an Atlanta possession in quarter three.
- Offensive fouls at actions 151, 206, 494 and 588 are excluded from defensive-foul counts.

The opening raw events are saved as a regression fixture with manually specified boundaries and foul indicators. Synthetic regressions cover same-owner period transitions, administrative ghost groups, overtime future-information invariance, bonus thresholds and outcome-independent filtering.

Remaining limits: retained-ball exceptions, overturned/edited feed events and source omissions need broader adjudication. These checks establish the reviewed cases, not exhaustive possession validity.

## MIA at DET, 0022400002 (overtime)

- Action 711: Detroit made basket. Action 713: Miami team technical foul. Action 714: Detroit technical free throw. Action 719: Miami take foul with Detroit possession.
- The technical-only Miami ownership segment is not a live-ball possession. Detroit's post-basket retained-ball segment remains separate because the preceding Detroit live segment ended in a made basket.
- Regression tests distinguish this retained-ball case from a temporary technical ownership switch during an ongoing possession, which must rejoin the original segment.
