# Candidate-v6/v7 semantic follow-through

Date: 2026-11-02. Candidate implementation evidence only. All games remain ineligible; independent reconstruction validation has not passed.

Seven raw-source regression tests failed before the initial changes (`7 failed, 67 passed`). The root causes were control normalization and pending-terminal handling, plus foul categories stored in `descriptor` rather than `subType`. The fix preserves source ordering and every raw event. It does not choose a parser to minimize flags or replace missing outcomes with zero.

## Source-backed corrections

| Defect | Exact evidence | Candidate correction |
| --- | --- | --- |
| Recovered jump ball used a stale possession field | `0022000003` 566/571 | Recovery actor establishes gaining team; original source owner remains in the event ledger |
| Delayed defensive foul split a completed FT entitlement | `0022000013` 502/505/500/506 | One exact same-clock, same-offense, matching-total entitlement foul remains with final made FT; preserve its terminal boundary |
| Goaltending companion after awarded FT manufactured a possession | `0022000114` 360–363 | Same-clock opposing goaltending companion remains with made FT; final/nonfinal entitlement behavior retained |
| Dead-ball team rebound switched live control | `0022400921` 62–64; `0022400875` 548–551 | Both exact tokens plus prior same-clock nonfinal/technical/retained FT mark an administrative rebound; ordinary final misses retain control awards |
| Flagrant descriptors bypassed retained entitlement | `0022400875` 544/550/551 | Exact flagrant-type-1/-2 and punching descriptors enter existing retained-ball audit path |
| Personal/double descriptors counted one side as ordinary defense | `0022000071` 437/439 | Both recorded double fouls stay audit-required, with no ordinary defensive foul classification and missing subsequent counts |
| Defensive lane record during known FT entitlement treated as unsupported | `0022000002` 590/608/592/609 | Explicit same-clock defensive lane record retains offense; no invented retry |
| Explicit jump-ball violation unclassified | `0022000248` 7/8; `0022000033` 156/158 | Offensive violator loses entitlement; defensive violator retains explicit source offense |
| Memo source owner manufactured control | `0022000932` 595/596/599 | Memo is non-control with blocking `source_note_requires_audit`; target/history unknown because value can describe officiating omissions |

The companion JSON retains complete raw neighborhoods, CSV rows, archive/member names, source SHA256 and historical home/away metadata. Its label inventory came from one pass through all six hash-verified CDN archives using `verified_snapshot` and `archive_games`. Those archive-wide label counts include quarantined games and must not be equated with issue counts in reconstructed games. The inventory found 812 personal flagrant descriptors, 168 personal/double descriptors and 317 memo records; no unsupported foul label is reinterpreted by guesswork.

## Boundaries and remaining uncertainty

Lane classification requires prior same-clock awarded-foul entitlement or valid made FT. Prior missed/invalid/unknown FT keeps blocking replacement uncertainty. Offensive lane, double-lane and unmatched violations remain blocking. Missing/conflicting actors or source owners, unmatched/repeated companions, ordinary fouls without matching FT-total evidence and all other unresolved control transfers remain explicit audit issues. Retained-ball and away-from-play audit reasons remain blocked; this work does not establish seasonal entitlement completeness. Memo notes are reclassified with a blocking reason, not suppressed.

Adversarial tests cover actor/clock/owner/qualifier mismatches, repeated foul companions, exact qualifier token boundaries, unsupported lane context and nonfinal FT behavior. Raw-event accounting and prior-state prefix invariance run against nine source neighborhoods. Historical release artifacts and v5 reports remain unchanged.

## Primary rule evidence

The [2020–21 NBA rulebook](https://ak-static.cms.nba.com/wp-content/uploads/sites/25/2021/01/2020-2021-NBA-Rule-Book.pdf), Rules 6, 9, 10 V and 12B II/IV/VI, supports the jump/dead-ball/free-throw and foul distinctions. Current official [Rule 6](https://official.nba.com/rule-no-6-putting-ball-in-play-live-dead-ball/), [Rule 9](https://official.nba.com/rule-no-9-free-throws-and-penalties/) and [Rule 10](https://official.nba.com/rule-no-10-violations-and-penalties/) corroborate those category rules. These sources support the implementation hypothesis; they do not establish correct calls, independent film validation or every intervening season's rule adjudication.

## Verification

Initial non-clock parser SHA256: `0f117f64c682bcf61b116537f231133e74f77a09445f881b29621808f9358b18`.

```sh
.venv/bin/python -m pytest tests/v2/test_possessions.py tests/v2/test_reconcile.py tests/v2/test_features.py -q
```

Initial non-clock result: `123 passed in 1.63s`. After nine raw-accounting/prefix regressions and two clock adversaries: `134 passed, 1 deselected in 1.81s`; the positive zero-clock restoration regression was intentionally failing at that intermediate investigative stage, before its coordinated correction.

```sh
.venv/bin/ruff check src/whistle_research/possessions.py tests/v2/test_possessions.py
```

Result before clock decision: `All checks passed!`.

The initial all-game v6 diagnostic exposed overbroad dead-ball normalization and a jump/turnover duplicate-loss boundary. Ordinary final-miss defensive team rebounds now retain control (`0022300470`, 652–654). Exact recovered heldball/lost-jumper turnover companions (`0022000005`, 111/114/115; `0022000003`, 298/301/302) keep one control gain. Different clocks add blocking timing uncertainty; mismatched actors/labels and duplicate/intervening rows do not pair. A technical FT cannot be skipped to corroborate an earlier ordinary FT goaltending companion. These review failures were reproduced before the narrowed correction.

One additional source clock review is recognized from prior evidence only: missed offensive shot at0, same-offense team offensive rebound at0 linked by shotActionNumber, then supported replay/request with exact foul-before-expiration value. Positive `0022100865` 176–179 preserves source0→0.6 and stays audit-required. Reused text in `0022100206` and `0022101229` does not qualify. Other clock quarantines including the recorded actual extended-game anomaly remain unchanged.

Intermediate v6 parser SHA256: `42d8af799859e5513410250c395c294e265f0e54f3e92f36954b12ee87d3eac5`. Its focused checks passed 147 tests and Ruff. Initial v6 diagnostics are preserved as investigative evidence, not the final parser result.

The coordinating agent owns the fresh all-game rerun, final report/parser bindings, full project checks and independent review. No scientific eligibility, model fit, commit, merge or deployment follows from focused tests.


## V7 source-note state and chronology correction

V6's administrative memo branch still set `prior=memo`, allowing out-of-band note timestamps and scores to become possession-start features. Verified `0022000035`, rows 20581–20583, showed shot 556 at 11:42 → memo 558 at 11:34 → shot 559 at 11:19; the next start reference incorrectly named memo 558. Verified postgame `0022000254` note 661 at 1:11 followed actual game end at 0:00, showing note time is metadata rather than a live-clock update. Two nonsynthetic and three synthetic regressions failed before correction.

V7 retains all raw note events and source indexes, blocks them with `source_note_requires_audit`, and propagates unknown counts to active and raw note periods. Notes cannot set prior/reference state or change live period/control. Clock validation walks the non-memo chain after checking all-row structural and ordering constraints; every other administrative type remains subject to strict chronology. Exact replay exceptions use the effective chain without crossing another non-memo event. Raw clocks/scores are never rewritten.

Adversarial source `0022100750` replay 452 at 5:50 → note 455 → substitution 456 at 5:51 and `0022100954` timeout 664 at 44.3 → notes 665/666 → substitution 667 at 46.3 remain quarantined. Thus excluding note timestamps does not mask actual clock rises. The verified assessment in `memo_clock_assessment.json` found 42 note rises across 37 games, with 35 shadow reconstructions and 2 remaining actual non-memo rises, plus 59 existing memo-based group references (6 changed clock values, 0 observed score/period differences). These are implementation diagnostics; final all-game counts and all scientific claims remain gated.

V7 parser SHA256: `9ee7d5e81b5a99f0b42bf94e617269104bcb90e47f796af02fa4d0bb256d991f`. Final focused verification is recorded in the companion JSON. Complementary non-memo completion-marker selection is owned by the coordinating agent in reconciliation/features.


Final v7 verification: 161 focused possession/reconciliation/features tests pass; the owned possession suite alone passes 126 tests. Ruff and `git diff --check` pass. Independent review repeated the focused suite and checked 225 synthetic memo insertions across source-neighborhood gaps, confirming preserved grouping, offense, terminal reason, completeness and before-state references/clock/scores while all notes remain blocking. Those insertions are adversarial implementation checks, not independent source or film validation. The coordinating agent's non-memo completion-marker fixes are integrated; full-game reruns and global checks remain separately recorded by that agent.
