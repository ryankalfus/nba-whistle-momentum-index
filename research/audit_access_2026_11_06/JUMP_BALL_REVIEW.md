# Jump-ball source review — 2026-11-06

No inspected public NBA statistical instruction resolves the delayed jump-ball turnover **actor mismatch**. NBA playing rules and a pinned pbpstats implementation support investigating companion records, but do not establish the actual sequence in the 153 residual cases or justify automatically repairing them. The independent reconstruction audit remains blocked.

## NBA evidence and limits

- The **2025–26** playing rules, Rule 6 VI (printed p. 27), require a held-ball jump between the involved players, subject to injury, ejection and concussion exceptions. Rule 7 II (p. 28) distinguishes obtaining possession after a jump from the tap itself. Rule 10 IX (p. 36) distinguishes a jump-ball touch from control. These are playing rules, not instructions for attributing a statistical turnover or ordering feed records. This review did not establish their exact applicability throughout the historical 2020–25 study seasons.
- NBA Video Rulebook statistical examples charge a misdirected-pass turnover to the passer and can credit a controlled-deflection steal to a defender who never controls the ball. They support separating statistical attribution from final recovery. They do **not** specifically explain a turnover charged to a teammate of the losing held-ball jumper. An earlier bad pass causing the eventual loss is a possible interpretation, not a verified NBA held-ball scoring rule or a finding about these games.
- Searches of official NBA rules, statistical examples, glossary and public manual references found no authoritative NBA statistical mismatch instruction. This is a bounded search result, not proof that no internal instruction exists. FIBA/NCAA examples returned by searches were not treated as NBA authority.

## Exact pbpstats comparison

The [alternative-parser pilot README](../cross_feed_2026_11_05/alternative_parser/README.md) identifies the saved **pbpstats 1.3.11** wheel at `output/alternative-parser-pbpstats-1.3.11/pbpstats-1.3.11-py3-none-any.whl`. Its recomputed SHA256 is `bf25d508e0956f8b5c5055e85b2d35d9259677e2b62410ce1121eb4d0f6683a0`, matching that README and the [recorded result](../cross_feed_2026_11_05/alternative_parser/result.json).

Locations below are within the wheel and its `unpacked/` directory; line numbers refer to the verified wheel source. Every listed unpacked file matched the wheel bytes and its recorded `package_source_sha256` entry.

| Source path under `pbpstats/resources/enhanced_pbp/` | SHA256 | Inspected behavior |
| --- | --- | --- |
| `stats_nba/enhanced_pbp_item.py` | `f3854bb9b9757baf56bc97ca6e791c2f42d09298c511b18f6ee238fe56871a76` | `StatsEnhancedPbpItem._is_jump_ball_possession_ending_event`, lines 261–322: an adjacent same-clock non-`NoTurnover` record suppresses the jump possession end; no loser-actor identity requirement. |
| `stats_nba/jump_ball.py` | `bb9e8361abf0f30bc739427438de7b77f0d7ae67dcd93ebeeb12c434ec6a239d` | `StatsJumpBall.get_offense_team_id`, lines 17–36: uses the following same-clock turnover's team, with a separate same-clock foul/turnover branch. |
| `data_nba/enhanced_pbp_item.py` | `a451982df0080d7f3557052cef48c5b9225fba1ce6a161bbcd01ec5e3e17601a` | `DataEnhancedPbpItem.is_possession_ending_event`, lines 84–102: follows changes between nonzero source offense-team IDs, except start-period transitions, and terminates at a final event. |
| `data_nba/jump_ball.py` | `e0d7062bf96c528b306d879e38c217ad10e06eef2e366e5eb82008c053e052a2` | `DataJumpBall`, lines 7–15: inherits the mobile boundary behavior; no corresponding stats-feed jump override. |

The two cited mutable GitHub `master` stats-feed files were fetched on 2026-11-06 and were **byte-identical** to the pinned wheel files above. The finding therefore has pinned package evidence, not merely mutable-source evidence. **The existing fourteen-game pilot used the mobile `data_nba` path, not this `stats_nba` heuristic.** Its results do not test that heuristic or independently corroborate actor-mismatch repairs.

The maintainer's 2019 wiki documents a Cauley-Stein/Ingles jump followed by an Ingles turnover/Cauley-Stein steal with a one-second clock discrepancy. It recommends aligning the time so the steal handles the possession change. That example matches the losing jumper's identity; it supplies no mismatch-specific rule or independent film evidence.

## Consequence for the residual cases

The [existing triage](../parser_followthrough_2026_11_02/residual_triage.md#jump-loss-records-evidence-and-limit) reports 153 added unpaired turnovers, including 101 same-clock winning-jumper steals and an 81-case held-ball/lost-ball-or-bad-pass subset. Those are development diagnostics. Matching team, clock and steal actor does not establish whether a turnover is a companion, an intervening gain occurred, a correction was misplaced, or an attribution is erroneous. In `0022000041`, the public rules do not establish why Young rather than Fernando receives the turnover.

A proposed development test should freeze a narrow predicate before assessing effects: explicit held-ball description, same period/clock, contiguous jump/turnover/steal records, turnover team equal to the prior source owner, and steal actor equal to the recovering team's winning jumper. Preserve all original actors and raw hashes. Include negative fixtures for different clocks, intervening live events, incompatible teams, absent steals, other jump reasons and ambiguous identities. Report every affected record and retain uncertainty; passing fixtures demonstrates implementation behavior only. This predicate is a candidate test, not an approved correction rule.

Resolving actual cases requires continuous footage covering the preceding action, held-ball decision, jump and ensuing control, with source identity checks and the protocol's independent annotation/adjudication evidence. No footage was reviewed, no annotations were created, no parser was changed, and no cases became scientifically validated through this review.

## Sources and references

1. [NBA 2025–26 playing rules](https://cdn.nba.com/manage/2026/01/Official-2025-26-NBA-Playing-Rules.pdf) — playing-rule scope only; printed pp. 27–28 and 36.
2. [NBA bad-pass turnover example](https://videorulebook.nba.com/archive/turnover-bad-pass-by-offensive-player/) — passer attribution, not a held-ball mismatch example.
3. [NBA controlled-deflection steal example](https://videorulebook.nba.com/archive/steal-credited-to-defender-who-deflects-the-ball-away-from-opponent-2/) — steal attribution without the defender controlling the ball.
4. [PyPI 1.3.11 release metadata](https://pypi.org/pypi/pbpstats/1.3.11/json) and [published wheel](https://files.pythonhosted.org/packages/68/81/2c9ae466029bfa26bf2112c9c2ff5156334f49a2575a457c1115d2b74bdd/pbpstats-1.3.11-py3-none-any.whl) — pinned distribution identity.
5. [Stats-feed possession implementation](https://raw.githubusercontent.com/dblackrun/pbpstats/master/pbpstats/resources/enhanced_pbp/stats_nba/enhanced_pbp_item.py) and [jump attribution](https://raw.githubusercontent.com/dblackrun/pbpstats/master/pbpstats/resources/enhanced_pbp/stats_nba/jump_ball.py) — mutable links, byte-compared to the pinned files above on the review date.
6. [Maintainer's raw-play-by-play correction wiki](https://github.com/dblackrun/pbpstats/wiki/Fixing-issues-with-raw-play-by-play#time-needs-to-be-fixed) — historical identity-matched example, last edited 2019-10-16.

Methods: generated varied official-rule, statistical-manual, held-ball/steal and parser queries; inspected primary-source text and published code; read wheel members with Python's standard-library `zipfile`; compared SHA256 and bytes against the saved distribution, unpacked files, recorded result and fetched master sources. No package code was imported/executed, dependencies installed, protected outcomes inspected, or accounts/browser controls used. Source/hash checks passed; project test/build checks were not run for this documentation-only review.
