# WMI: detailed review of the last two hours

Review window: September 12, 2026, 12:42–14:42 Eastern. Prepared from the current working tree, file modification times, project log, statistical result tables and saved verification records. This is a reconstruction of work, not a complete editor-session audit. File modification time shows the latest write, not every intermediate edit. The Git baseline is July 7, so the included tracked diff is not an exact two-hour snapshot. The inventory explicitly includes recently written generated and cache files; a write does not necessarily mean content changed.

## What changed overall

Two substantial, separate research streams were completed. The website/validation stream corrected possession reconstruction, rebuilt game summaries, tested matched foul-prediction models, ran conditional sequence forecasts, stress-tested uncertainty intervals and exposed game explanations in the website. The all-hypotheses stream executed empirical analyses for all 18 supplied questions, including previously unavailable player, bonus, challenge, rule and crew analyses. It generated 77 reported estimates and applied a global Benjamini–Hochberg correction to 55 inferential comparisons.

The public WMI equation remains unchanged: F is current defensive-foul occurrence, L indicates a foul in the previous two global possessions, N indicates a foul in the next two, M=F(1+N), and WMI=mean(M|L=1)/mean(M|L=0). Global windows still cross period boundaries and truncate at game edges. Corrections change which events belong to possessions, so numerical scores can change without changing the equation.

The main scientific conclusion is modest. Recent fouls are associated with slightly lower immediate foul probability and slightly greater continuation conditional on a current foul. The patterns do not establish positive self-excitation, referee intent, call correctness or a simple smooth decay. Small foul-timing prediction gains do not translate into a demonstrated win-probability improvement in the tested model.

## Approximate chronology

- Around 14:04: the all-hypothesis source/research package was being assembled; subsequent stages produced rich event tables and context variables.
- By 14:08–14:12: shared WMI helper changes, dependencies and project scope documentation were written.
- Around 14:15–14:23: event fixtures, website behavior, research tests, initial reports and browser checks were written and refined.
- Around 14:24–14:26: final shared-parser corrections were applied, six possession partitions and 6,084 per-game timelines/game summaries were rebuilt.
- Around 14:28–14:30: forecast/interval/report refinements and validation verification were saved.
- Around 14:34–14:38: the all-hypothesis estimates, final multiple-test correction, full report, provenance, checks and project-log entry were completed.

These are approximate phases inferred from surviving last-write timestamps; they do not establish exact start times or every intermediate operation.

## Data reconstruction and model safeguards

The new shared `wmi_possessions.py` parser explicitly splits at period boundaries, prevents substitutions/reviews/period markers from starting possessions, removes technical-only ownership groups, and handles same-team retained-ball sequences according to whether the previous live segment ended. Regulation quarters use 12 minutes and overtime periods 5. Fractional clock parsing was fixed. Reconstructed starting score/time use the preceding recorded event or the period start. Future overtime duration cannot enter a predictor.

The parser reconstructs pre-possession defending-team foul counts and bonus eligibility, including regulation/OT quotas and the final-two-minute rule. Offensive, technical and double fouls do not consume the normal reconstructed team quota. Player IDs, foul subtype/descriptor/descriptions, free throws and shot/rim outcomes are retained for audits and separate analyses. Missing early-season shot-zone fields are unavailable, not zero.

Current-possession outcomes and future WMI terms are excluded from pre-possession prediction features. The late-strategy sensitivity excludes every possession in a specified time/margin state rather than only possessions where fouls occurred. Empty, one-row and two-row history windows were repaired. Unknown future forecast horizons at the end of a game are excluded, not coded as no-foul.

The website validation dataset contains 6,084 games and 1,208,809 possessions: 6,000 regular-season games from 2020–21 through 2024–25 plus 84 playoff games. Relative to the old parser on the same CDN source, possession counts changed in 4,374 games. Mean absolute WMI change was 0.021651 and the maximum 0.543544. Keeping the old grouping, the overlapping 2024–25 CDN-versus-stored-mobile difference averaged only 0.000652. Thus parser changes account for much more of the change than source substitution in that overlap. Sixteen unassigned foul events remain explicit audit counts. Seventy-two technical-only/admin ownership groups were removed.

The all-hypotheses study uses a separate richer ownership/period parser, retaining 6,080 games and 1,225,902 possession groups after quarantining four backward-clock games: 0022000181, 0022000254, 0022000925 and 0022301177. Its primary 2024–25 sample has 248,456 groups, versus 244,841 in the website validation stream. H9 additionally uses legacy game-level WMI. These samples must not be silently combined or treated as the same reconstruction. The four-game quarantine has not been propagated to the website validation dataset; invalid/unparseable clocks and backward clocks are different checks. A common reconstruction and quarantine policy remains an integration task before treating the two streams as one release.

## Website changes

- Search now overlays 6,084 recalculated summaries onto the original 8,322-row snapshot, giving 8,629 distinct games, including 307 additions.
- Games explicitly identify recalculated parser v2 versus original snapshot awaiting recalculation.
- Recalculated percentiles use the 6,000 recalculated regular-season games. Legacy percentiles retain their separately named original search reference.
- WMI displays three decimals and percentile one decimal followed by a percent sign.
- Game explanations show n1/n0, numerator and denominator means, immediate and continuation ratios, and same-team/opposite-team transition counts.
- Each recalculated game has a team/subtype/description foul timeline, loaded on demand with protection against displaying a previously selected game's delayed response.
- Missing WMI is N/A rather than zero. Compact YYYYMMDD dates display correctly. Legacy rows explicitly state that components and timelines are unavailable.
- The arbitrary 0.95–1.05 neutral classification was replaced with descriptive above/below-one wording. Near one does not establish equivalence. Low group counts have an explicitly unvalidated sample-size notice.
- The original 6,727-game summary remains labeled as an archived snapshot. It is not the new search population. The separate recalculated 6,000-game reference has mean WMI 0.966674 and median 0.917852.
- A Validation navigation link/section exposes held-out model comparisons and report/data downloads. Responsive diagnostic grids and horizontally scrollable tables were added.
- Per-game inferential intervals remain withheld following failed consistency checks in the coverage stress test.

## Forecasting and uncertainty work

`validate_wmi.py` compares identical basketball-context logistic models with and without five global and five same-defense foul lags. Training expands only through earlier seasons, with fixed settings. It saves possession-weighted/equal-game effects, Brier, AUC, average precision, calibration and 1,000 paired whole-game-bootstrap intervals. This supersedes the August report's prediction claims; 2024–25 had already been explored and is a retrospective holdout.

History improves held-out foul log loss by 0.000041 in 2022–23 (interval includes zero), 0.000082 in 2023–24, 0.000055 in 2024–25 and 0.000299 in the playoffs. The latter three intervals exclude zero. Magnitudes are tiny. The two-final-regular-season replication gate passed with no worse Brier, triggering the planned exploratory next-team/time forecasts.

`forecast_foul_sequences.py` uses multinomial three-possession next-team and five-possession first-foul-position outcomes. Both next-team intervals include zero. Time-to-foul log loss improves by 0.000332 in 2023–24 and 0.000233 in 2024–25, with intervals below zero. These are horizon models, not Hawkes or survival fits. Additional forecast comparisons are exploratory and do not use the 18-hypothesis study's global q-values.

`validate_wmi_intervals.py` tested raw-sequence circular moving-block bootstrap intervals: six processes, 400 simulated 200-possession games per process, 300 draws, block lengths 5/10/20. Nominal 95% coverage ranged from 81.8% to 100%. No tested block length was consistently adequate. This rejects release of this candidate interval procedure; it does not prove every uncertainty method fails.

The separate H17 win model is a different prediction target: score/time/possession/Elo baseline versus additional foul features. On 1,230 held-out 2024–25 games, added features slightly worsen log loss and Brier, with intervals spanning zero. There is no demonstrated win-prediction gain from that specification.

## Code, outputs and documentation

New implementation: `wmi_possessions.py`, `validate_wmi.py`, `forecast_foul_sequences.py`, `validate_wmi_intervals.py`, and `run_all_wmi_hypotheses.py`. `wmi_utils.py` now delegates reconstruction/clock parsing to the shared parser and fixes short history windows. The August `run_wmi_expansion_analysis.py` predates this window; it must not be presented as newly created today.

New tests: `tests/test_wmi_validation.py`, `tests/test_all_wmi_hypotheses.py`, `tests/test_site.cjs`, and a real NBA opening-event fixture. CI adds Node 22 and website unit checks. Root dependencies add scikit-learn and scipy; the hypothesis package saves its own environment requirements.

`research/validation_2026_09_12/` contains 26 release artifacts, including six compressed possession partitions, model predictions/results, calibration/residuals, sequence results, interval simulation, parser/source comparisons, source/code/environment manifests, protocol/data dictionary, spot checks and verification. `research/hypotheses_2026_09_12/` contains 68 recently written non-cache files, including all hypothesis estimates and supporting coefficients/events, game components at five windows, source locks/manifests, quarantined clocks, report and verification; recently written cache tables are separately inventoried. `site-data/` contains 6,084 timelines plus the summary CSV/JSON. Browser snapshots/screenshots and ordinary tool caches were also written.

README, project scope, formal definitions, plan and project log were updated. The old August expansion report received a superseded-prediction banner; its historical findings were not relabeled as today's results.

The tracked diff covers 11 files, with 216 insertions and 134 deletions. This excludes all new/untracked scripts and generated outputs. The inventory records 6,248 recently written paths totaling 387,527,094 bytes at the review snapshot, including caches and generated data. It is not a count of 6,248 hand-edited source files.

## Verification and remaining limits

Saved records report 38 Python tests passed, 18 targeted hypothesis tests passed, Ruff passed, Git whitespace checks passed and website unit checks passed. Desktop 1440×1000 and mobile 390×844 browser flows were checked, with zero console errors in the recorded verification and no mobile overflow. The hypothesis runner completed all sections with no failed analysis blocks. Its 11 audit checks passed; all ten downloaded sources matched recorded sizes/hashes and final q-values were independently recomputed.

Internal score reconciliation is not the same as independent source validation: only 84 matching local schedule rows had known final scores, and all 84 matched. Automated tests and event-level spot checks do not establish exhaustive possession correctness or video-level accuracy.

Not completed or established: a common parser across both research streams, deployment/commit/push of this work, comprehensive film validation, causal referee behavior, call/noncall correctness, validated lineups/tracking, an optimal keep/bench/return policy, reliable crew rankings, or all ten advanced model architectures in the roadmap. Advanced architectures remain deferred pending stronger opportunity data and prospective evidence. All 18 questions received empirical attempts; several original causal questions remain unresolved.

## Contents of this review package

- `complete_review.md`: this overview followed by the complete 18-hypothesis report (all 77 estimates) and the validation/interval reports.
- `files.json`: every project path with a last-write timestamp in the fixed two-hour window, including size, SHA256, category and Git tracking status.
- `tracked_changes.patch`: the current tracked Git diff, with the baseline limitation stated above.
- `inventory_summary.json`: time boundaries, counts and full-project read accounting.

The appendix reports are preserved as snapshots of the reviewed results. Existing research scripts and estimates were not changed to prepare this review.


---

# Full breakdown of all 17 WMI hypotheses — plus supplied H18

Run date: 2026-09-12 · Research seed: 20260912

## Executive assessment

All H1–H17 were revisited: earlier analyses were rerun, previously unavailable bonus/player/rule/challenge/crew tests were assembled, and crowd and win-prediction analyses were expanded. The attachment actually lists 18 hypotheses, so H18 is included as an additional section. **Every section has an empirical result; not every original causal claim is identifiable.** This is a separate research package, not a change to the website, public WMI formula or production game files.

The central result is modest: measured recent fouls predict slightly lower immediate foul probability, while the continuation component is slightly higher. A simple smooth-decay or makeup-call interpretation is not supported. Substitution after foul trouble and the decline in take-labeled fouls are much clearer than the proposed strategic or officiating mechanisms. Added live foul features do not improve the held-out win model. The coaching-optimality question remains causally unresolved.

## Data and execution coverage

The source inventory contains **6,084 games**, covering five full regular seasons and all 84 games of the 2025 playoffs. After quarantining 4 games with backward source clocks, the rich event study uses **6,080 games and 1,225,902 possession groups**. The primary 2024–25 sample and all 84 playoff games are unaffected. H9 additionally uses stored 2019–20 and selected attendance-linked game WMI.

| Season | Type | Source games | Retained games |
|---|---|---:|---:|
| 2020-21 | Regular season | 1,080 | 1,077 |
| 2021-22 | Regular season | 1,230 | 1,230 |
| 2022-23 | Regular season | 1,230 | 1,230 |
| 2023-24 | Regular season | 1,230 | 1,229 |
| 2024-25 | Regular season | 1,230 | 1,230 |
| 2024-25 | Playoffs | 84 | 84 |

The attachment is a research roadmap, not a preregistration. Specifications and fallback analyses were developed during this run. Formal and exploratory tests are distinguished below; the results should be independently replicated before publication.

Clock quarantine: 0022000181, 0022000254, 0022000925, 0022301177. The source contains replay clock reversals, an end-game memo with an earlier clock, and one inconsistent shot-event ordering. These complete games were excluded from rich-event fits rather than silently repairing their clocks. The raw cached data and anomalies remain available in `quarantined_clock_events.csv`; legacy game-level H9 does not rely on this clock reconstruction.

### Statistical conventions

Odds ratios and rate ratios have a null of 1; additive differences and correlations have a null of 0. An interaction odds ratio is a **ratio of odds ratios**, not a subgroup's standalone foul probability. Main effects in interaction models apply at the reference history state L2=0. Estimates are not percentage points unless explicitly converted: 0.01 probability/share units = 1 percentage point.

Regression uncertainty is clustered by game; count models use heteroskedasticity-robust game-level errors. Before/after and prediction differences use 1,000 whole-game bootstrap draws; their p-values use a normal approximation to the bootstrap standard error. Crew stability resamples crew identities. Benjamini–Hochberg correction is applied jointly across the 55 reported inferential tests, not separately until something becomes significant. The tables show raw p and final q. Pointwise 95% intervals are not multiplicity-adjusted. Rows without p/q are descriptive estimates, not declarations of a passed formal test. Correlated tests and exploratory specification choices limit the certainty implied by q-values.

### Reconstruction and leakage safeguards

The foul definition and global last-two/next-two formula are unchanged. This separate parser adds explicit period boundaries to ownership-based grouping, measures score before the group's first event, handles regulation/OT clocks without knowing future overtime, and reconstructs foul/bonus counts before the current event. It remains a public-feed ownership approximation, not independently video-validated live control. Dead-ball ownership tagging, special fouls and overturned-event revisions are residual sources of error.

The parser adds 18,029 boundaries across the study relative to ownership-only grouping. Therefore these research values need not match earlier mobile-feed/ownership-only outputs exactly. All game score totals reconcile internally. Of the matching local schedule rows, only 84 have known final scores; those all match. Missing schedule scores are not counted as validation successes. Home/away matches were checked separately.

Live WMI at the start of possession i includes a historical row only after its future-two window has completed (row ≤i−3). The current outcome, future N_t, final-game WMI and future overtime duration never enter win prediction. Whole games remain in chronological training/validation/test partitions. These checks reduce identifiable leakage, but the use of finalized historical play-by-play cannot guarantee reconstruction of the exact feed visible live at the time.

## Hypothesis-by-hypothesis results

### H1. Short-term dependence after context adjustment

**Question:** Does recent foul history still matter after accounting for basketball context?

**Executed analysis:** Fitted a binomial logistic model of current defensive-foul occurrence on the previous-two-possession indicator. Controls are signed score difference, absolute margin, remaining regulation time, quarter/OT, offense and defense team, home offense, reconstructed bonus, and rim attempts, three-point attempts and free throws in the previous five global possessions. Repeated the fit after excluding every possession in the likely intentional-fouling state, whether or not it actually contained a foul. A within-game linear probability sensitivity absorbs fixed game and assigned-crew levels.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| context_adjusted: L2 | 0.95298 | [0.92774, 0.97891] | 0.000438 | 0.00185 | 248,456 / 1,230 | odds ratio |
| standardized probability change | -0.00644 | — | — | — | 248,456 / 1,230 | probability difference |
| exclude_all_late_strategy_possessions: L2 | 0.94636 | [0.92105, 0.97237] | 6.72e-05 | 0.000349 | 246,832 / 1,230 | odds ratio |
| within-game fixed-effect linear probability sensitivity | -0.0082 | [-0.01181, -0.0046] | 8.17e-06 | 4.99e-05 | 248,456 / 1,230 | probability difference |

**Interpretation:** Small negative dependence survives the measured controls: a recent foul is associated with lower, not higher, current foul probability. The standardized probability change is about −0.64 percentage points. This supports dependence, not positive self-excitation or referee bias.

**Limits and prior coverage:** Partial implementation of the originally proposed full model: these are team fixed effects and game-clustered errors, plus a game-fixed-effect sensitivity—not hierarchical logistic random effects. No validated five-player lineups, drives, matchup tracking, or current legal-contact opportunities are available. Past shot counts are imperfect style proxies. H1 was previously attempted with fewer controls; it was rerun here.

### H2. Immediate persistence versus future continuation

**Question:** Is WMI driven by immediate occurrence or by future continuation?

**Executed analysis:** Decomposed the two-possession ratio exactly into immediate persistence p1/p0 and continuation (1+q1)/(1+q0). Resampled complete games 1,000 times to estimate uncertainty. The displayed combined ratio uses pooled sufficient statistics for this research diagnostic, not the average of game WMI and not a replacement public season metric.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| window 2: immediate | 0.96864 | [0.94879, 0.98789] | — | — | 248,456 / 1,230 | ratio |
| window 2: continuation | 1.01136 | [1.00344, 1.01876] | — | — | 248,456 / 1,230 | ratio |
| window 2: WMI | 0.97965 | [0.95776, 0.99913] | — | — | 248,456 / 1,230 | ratio |

**Interpretation:** Immediate persistence is below one, while continuation is slightly above one. The immediate component dominates, putting the combined ratio just below one. Calling all three numbers positive ‘momentum’ would obscure the result.

**Limits and prior coverage:** These are unadjusted descriptive components with pointwise bootstrap intervals, not independently validated causal mechanisms. One game has an undefined conditional continuation component because a required foul count is zero; its sufficient statistics remain usable in the pooled estimate. Previously run; now rerun with the audited period boundaries.

### H3. Decay over possession distance

**Question:** Does the sequence effect fade smoothly with possession distance?

**Executed analysis:** Computed 1-, 2-, 3-, 5-, and 10-possession versions with whole-game bootstrap intervals. Also jointly modeled the five individual foul lags with the H1 context controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| window 1: immediate | 1.00031 | [0.97542, 1.02441] | — | — | 248,456 / 1,230 | ratio |
| window 1: continuation | 0.9959 | [0.98731, 1.00441] | — | — | 248,456 / 1,230 | ratio |
| window 1: WMI | 0.9962 | [0.96992, 1.02039] | — | — | 248,456 / 1,230 | ratio |
| window 3: immediate | 0.99289 | [0.97509, 1.0108] | — | — | 248,456 / 1,230 | ratio |
| window 3: continuation | 1.00086 | [0.99396, 1.00788] | — | — | 248,456 / 1,230 | ratio |
| window 3: WMI | 0.99375 | [0.97467, 1.01368] | — | — | 248,456 / 1,230 | ratio |
| window 5: immediate | 0.9983 | [0.97989, 1.01778] | — | — | 248,456 / 1,230 | ratio |
| window 5: continuation | 1.00116 | [0.99477, 1.00679] | — | — | 248,456 / 1,230 | ratio |
| window 5: WMI | 0.99945 | [0.98016, 1.01927] | — | — | 248,456 / 1,230 | ratio |
| window 10: immediate | 1.0508 | [1.02766, 1.07385] | — | — | 248,456 / 1,230 | ratio |
| window 10: continuation | 1.00602 | [1.0008, 1.01152] | — | — | 248,456 / 1,230 | ratio |
| window 10: WMI | 1.05713 | [1.03261, 1.08162] | — | — | 248,456 / 1,230 | ratio |
| distance_specific: lag1 | 0.9985 | [0.96607, 1.03203] | 0.92919 | 0.94639 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag2 | 0.95464 | [0.92389, 0.98642] | 0.00546 | 0.01672 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag3 | 1.05973 | [1.02482, 1.09583] | 0.000688 | 0.00258 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag4 | 1.00614 | [0.97361, 1.03976] | 0.71502 | 0.7711 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag5 | 1.04176 | [1.00696, 1.07776] | 0.01827 | 0.04785 | 248,456 / 1,230 | odds ratio |

**Interpretation:** The pattern does not decay monotonically. Lag two is negative and lag three positive; the broad ten-possession ratio is elevated. A single simple decay story is not supported.

**Limits and prior coverage:** Longer windows change both recent-history exposure and future continuation. They also mix longer-lasting game conditions. They are not direct estimates of a causal decay kernel. The individual-lag regression, rather than comparisons of overlapping ratio intervals, is the formal adjusted test. Previously run; rerun here.

### H4. Same-team versus opposite-team foul direction

**Question:** Does the next foul tend to return to the same team or move to its opponent?

**Executed analysis:** Compared observed transitions with two baselines: randomly rearranged team marks among foul events, and 500 within-game permutations of foul indicators among each team's actual defensive possession slots. The second preserves each team's foul total and its opportunities. Separately fitted current foul probability on whether the defense committed the last foul, conditioning on gap 1–10 and H1 controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| opportunity_conditioned_direction: same_defense_as_last_foul | 0.98607 | [0.94174, 1.0325] | 0.5502 | 0.68781 | 200,810 / 1,230 | odds ratio |
| opposite-team share above random-mark baseline | 0.04967 | [0.04495, 0.05444] | 4.42e-88 | 1.22e-86 | 1,230 / 1,230 | share difference |
| opposite-team share above within-team opportunity permutation | 0.00826 | [0.00341, 0.0131] | 0.000703 | 0.00258 | 1,230 / 1,230 | share difference |

**Interpretation:** The raw random-mark comparison shows about five percentage points of excess opposite-team transitions. After preserving actual defensive opportunities, the excess is only about 0.83 percentage points, still statistically detectable. The lag-conditioned context model does not show a clear same-team effect. Thus the small residual is baseline-sensitive, not proof of makeup calls.

**Limits and prior coverage:** The opportunity permutation controls defensive slots and team game totals, not changing shot opportunities. The adjusted direction coefficient is identified largely by departures from strict possession alternation; this limits its interpretation. Neither test identifies intentional balancing or call accuracy. Previously run with a simpler baseline; the opportunity-preserving test is new.

### H5. Close games versus blowouts

**Question:** Does sequencing differ in close games versus blowouts?

**Executed analysis:** Defined close as pre-possession margin ≤5 and blowout as ≥15, with margins 6–14 as reference. Tested interactions with L2 both before and after excluding all likely intentional-fouling states. Also summarized close, blowout, fourth-quarter/OT, and masked-intentional-call ratios without compressing the possession axis.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| margin_interaction: L2:close | 1.00278 | [0.95079, 1.05762] | 0.9185 | 0.94639 | 248,456 / 1,230 | odds ratio |
| margin_interaction: L2:blowout | 1.01745 | [0.95674, 1.08203] | 0.58151 | 0.69345 | 248,456 / 1,230 | odds ratio |
| margin_interaction_without_late_strategy: L2:close | 0.9799 | [0.92851, 1.03412] | 0.45992 | 0.61697 | 246,832 / 1,230 | odds ratio |
| margin_interaction_without_late_strategy: L2:blowout | 1.02487 | [0.96361, 1.09002] | 0.43468 | 0.59768 | 246,832 / 1,230 | odds ratio |
| close WMI with original global windows | 1.00488 | — | — | — | 105,282 / 1,230 | ratio |
| blowout WMI with original global windows | 0.94602 | — | — | — | 50,109 / 918 | ratio |
| fourth_or_OT WMI with original global windows | 1.01384 | — | — | — | 61,674 / 1,230 | ratio |
| WMI with suspected intentional calls masked throughout windows | 0.96032 | — | — | — | 248,456 / 1,230 | ratio |

**Interpretation:** The adjusted close-game and blowout interactions do not establish different sequencing effects. Raw subgroup ratios differ, but those differences are not equivalent to a significant adjusted interaction.

**Limits and prior coverage:** The intentional-fouling heuristic is Q4/OT with ≤35 seconds and offense ahead by >3, or ≤15 seconds and offense ahead by ≥1. It is a state-based proxy, not a validated intentional-foul label. The main sensitivity excludes all eligible observations rather than selectively deleting only foul outcomes. Previously run; the exclusion design was corrected here.

### H6. Bonus status as a modifier of momentum

**Question:** Does entering the penalty change the effect of recent fouls?

**Executed analysis:** Reconstructed the defending team's pre-event foul quota separately for each period, including the final-two-minute rule and OT quota, then tested L2 × bonus. Offensive, technical, and double-personal fouls do not consume the reconstructed normal quota.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bonus_interaction: bonus | 0.80947 | [0.78051, 0.8395] | 5.72e-30 | 1.05e-28 | 248,456 / 1,230 | odds ratio |
| bonus_interaction: L2:bonus | 1.02681 | [0.97223, 1.08446] | 0.34235 | 0.53376 | 248,456 / 1,230 | odds ratio |

**Interpretation:** Bonus status is associated with a lower baseline foul probability in the fitted model, but the bonus-by-history interaction does not establish modified momentum. A baseline bonus association is not evidence for the interaction hypothesis.

**Limits and prior coverage:** Bonus is endogenous to earlier fouls and game behavior. Public foul classifications can miss special-case penalties. This is a reconstruction, not a feed of official live penalty flags, and cannot isolate defender restraint from offensive strategy or whistle thresholds. Newly executed.

### H7. Playoffs versus regular season

**Question:** Do playoff whistle dynamics differ?

**Executed analysis:** Compared all 84 archived 2025 playoff games with 1,230 regular-season games. Fitted postseason differences and sequence interactions for any defensive foul, shooting-foul possessions, and nonshooting-only foul possessions. Added a directional interaction and a close-game × postseason × recent-history interaction.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| playoff_interaction: postseason | 1.21314 | [1.14714, 1.28294] | 1.29e-11 | 8.89e-11 | 264,883 / 1,314 | odds ratio |
| playoff_interaction: L2:postseason | 0.95625 | [0.87595, 1.04391] | 0.31745 | 0.52908 | 264,883 / 1,314 | odds ratio |
| shooting_foul_playoff_interaction: postseason | 1.07823 | [0.99858, 1.16422] | 0.0544 | 0.12466 | 264,883 / 1,314 | odds ratio |
| shooting_foul_playoff_interaction: L2:postseason | 0.97653 | [0.87641, 1.08808] | 0.66697 | 0.73366 | 264,883 / 1,314 | odds ratio |
| nonshooting_only_playoff_interaction: postseason | 1.35158 | [1.25779, 1.45236] | 2.2e-16 | 2.42e-15 | 264,883 / 1,314 | odds ratio |
| nonshooting_only_playoff_interaction: L2:postseason | 0.93994 | [0.82558, 1.07014] | 0.34937 | 0.53376 | 264,883 / 1,314 | odds ratio |
| direction_playoff_interaction: same_defense_as_last_foul:postseason | 0.94771 | [0.87233, 1.02959] | 0.204 | 0.37401 | 214,764 / 1,314 | odds ratio |
| close_game_playoff_sequence_interaction: L2:postseason:close | 1.06883 | [0.91384, 1.2501] | 0.40497 | 0.57111 | 264,883 / 1,314 | odds ratio |

**Interpretation:** The postseason baseline foul odds are higher in this comparison, especially for nonshooting-only fouls. The immediate-history, directional, shooting/nonshooting sequence, and close-game sequence interactions do not establish a different playoff momentum mechanism.

**Limits and prior coverage:** One postseason is not a universal playoff effect. Playoff team selection, matchups, tactical adjustments and series dependence remain; errors are clustered by game, not by series. Close margin is only a leverage proxy. The last 18 playoff home/date assignments came from the existing project schedule because the separate referee-assignment archive ends earlier. No officials were invented. Previously analyzed at game level; the possession-level comparisons are new.

### H8. Home-court effects on foul direction

**Question:** Do home teams have more favorable dynamic foul patterns or call accuracy?

**Executed analysis:** Modeled defensive-foul probability when the offense is home, its interaction with recent history, and the same effects in close games. Included regular season/playoffs and H1 context controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| home_direction_interaction: home_offense | 1.02862 | [1.00533, 1.05245] | 0.01575 | 0.04558 | 264,883 / 1,314 | odds ratio |
| home_direction_interaction: L2:home_offense | 0.97934 | [0.93498, 1.0258] | 0.37733 | 0.54614 | 264,883 / 1,314 | odds ratio |
| home_in_close_games: home_offense | 1.02649 | [0.99079, 1.06349] | 0.14774 | 0.28019 | 111,974 / 1,314 | odds ratio |
| home_in_close_games: L2:home_offense | 0.99654 | [0.92471, 1.07395] | 0.92765 | 0.94639 | 111,974 / 1,314 | odds ratio |

**Interpretation:** The home-offense baseline association is small (odds ratio about 1.029) and survives the global q<0.05 threshold. However, there is no clear home-specific sequence interaction or strengthened close-game effect. A small baseline drawing-fouls association is different from dynamic home whistle momentum.

**Limits and prior coverage:** This measures receiving a counted defensive foul, not whether that foul was correct. A home team drawing more fouls may reflect play style. No correctness/noncall labels were joined, and this is not a complete directional-residual or accuracy study. Previously partial; now expanded with context-adjusted sequence interactions.

### H9. Crowd presence and foul sequencing

**Question:** Does crowd presence change sequencing?

**Executed analysis:** Used stored game-level WMI for 88 bubble and 971 pre-bubble regular-season games in 2019–20, adjusting for home and away team identities. Separately regressed stored WMI on recorded attendance per 10,000 spectators with season/game-type controls in the box-score archive's 2,111 matched games.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bubble_same_season_regular_games: bubble | 0.02238 | [-0.05067, 0.09544] | 0.54814 | 0.68781 | 1,059 / 1,059 | coefficient |
| recorded_attendance_selected_close_game_archive: attendance_10k | -0.03811 | [-0.11961, 0.04339] | 0.35941 | 0.53426 | 2,111 / 2,111 | coefficient |

**Interpretation:** Neither comparison establishes an attendance or bubble sequencing association. The uncertainty leaves room for effects in either direction.

**Limits and prior coverage:** This is partial: there is no reliable three-way normal/restricted/no-crowd classification. Missing attendance was never set to zero. The attendance archive disproportionately covers L2M-qualifying close games. Bubble selection, neutral courts, schedule restart and different teams confound a causal crowd claim. This section uses legacy stored WMI and therefore does not share the rich-CDN research parser used by most other sections. The prior bubble comparison was rerun; the recorded-attendance analysis is new.

### H10. Defender foul trouble and opponent strategy

**Question:** Does foul trouble for an important defender change opponent strategy?

**Executed analysis:** Predefined 30 high-defensive-activity players using prior-season blocks plus steals per event-observed appearance, requiring at least 40 appearances. Examined early second/third fouls, fourth fouls through Q3, and fifth fouls, all with >2 minutes left in the period. Tested immediate substitutions after third versus second early fouls and before/after opponent rim share and points per possession over five opponent possessions.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| substitution_after_third_vs_second_early_foul: threshold | 15.32693 | [7.82327, 30.02771] | 1.79e-15 | 1.64e-14 | 388 / 301 | odds ratio |
| rim-attempt share after minus before trouble | -0.000567 | [-0.03686, 0.03576] | 0.97534 | 0.97534 | 245 / 169 | share difference |
| opponent points per possession after minus before trouble | 0.08245 | [-0.02655, 0.18721] | 0.1151 | 0.2261 | 245 / 169 | points per possession |

**Interpretation:** Coaches are much more likely to substitute after an early third foul than a second. The observed rim-attempt share does not clearly change; the opponent scoring estimate is imprecise. Thus substitution response is supported, but the proposed attack-the-defender mechanism is not established.

**Limits and prior coverage:** Blocks/steals activity is a reproducible proxy, not a validated list of stars or defensive impact. No drives, contests or matchup-level targeting were measured. The rim/efficiency comparison is before/after without matched no-trouble controls, and substitutions change who is on the floor. Newly executed.

### H11. Whether coaches bench foul-troubled players too conservatively

**Question:** Are coaches systematically too conservative in benching foul-troubled players?

**Executed analysis:** Compared keeping versus immediately benching the predefined defenders after qualifying third/fourth/fifth fouls. Modeled the player's team net points over the next five global possessions with player, personal-foul-count and period indicators plus score/time controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| observational_keep_vs_bench: keep | -0.17886 | [-0.97355, 0.61583] | 0.65913 | 0.73366 | 245 / 169 | coefficient |

**Interpretation:** The keep-versus-bench estimate is imprecise and does not demonstrate that either policy is better. This analysis cannot determine whether coaches are too conservative.

**Limits and prior coverage:** This is an executed observational comparison, not an optimal-policy test. Coach knowledge, injuries, matchup, replacement quality and lineups confound the decision; later returns were not modeled. A credible causal answer requires validated lineup histories and a defensible policy-identification design. Newly executed, with causal identification explicitly unresolved.

### H12. Player behavior after drawing a foul

**Question:** Do offensive players change behavior after drawing a foul?

**Executed analysis:** For identified foul-drawing players, compared the next and previous five team offensive possessions, excluding the triggering possession. Measured player shot counts, repeat foul draws, rim share and three-point share, with game-cluster bootstrap uncertainty. Shot-mix comparisons require the player to shoot in both windows.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| shot_count_change next vs previous five offensive possessions | -0.01783 | [-0.03002, -0.00498] | 0.00547 | 0.01672 | 38,296 / 1,230 | difference |
| repeat_draw_change next vs previous five offensive possessions | 0.00642 | [0.00514, 0.0078] | 6.35e-22 | 8.73e-21 | 38,296 / 1,230 | difference |
| rim_share_change next vs previous five offensive possessions | 0.00819 | [-0.00196, 0.01801] | 0.10156 | 0.20689 | 12,604 / 1,230 | difference |
| three_share_change next vs previous five offensive possessions | 0.00617 | [-0.00436, 0.01662] | 0.24815 | 0.44026 | 12,604 / 1,230 | difference |

**Interpretation:** There is a tiny decrease in shot counts and a tiny increase in subsequent repeated foul draws. The shot-location shifts are not clearly established. This is not strong evidence of a large behavioral momentum mechanism.

**Limits and prior coverage:** No drives, disputed noncalls, unfavorable rulings or legal-contact judgments were inferred. Fatigue, substitutions and selection into a foul event can create before/after differences. The 12,604 shot-mix events are a selected subset of the 38,296 draw events, not all player possessions. Newly executed.

### H13. The 2022 transition-take-foul rule

**Question:** Did the 2022 transition-take-foul rule change frequency and value?

**Executed analysis:** Compared 2021–22 with 2022–23 using the common descriptor containing ‘take’, excluding the last two minutes of Q4/OT. Estimated a Poisson rate ratio with possession exposure and a segmented time-trend sensitivity at October 18, 2022. Also reported points scored on the labeled take-foul possessions.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| 2021-22 own points on take-foul possessions | 1.15655 | — | — | — | 1,961 / 943 | points |
| 2022-23 own points on take-foul possessions | 1.36872 | — | — | — | 358 / 298 | points |
| post/pre common take-label rate per possession | 0.18031 | [0.1596, 0.20372] | 1.24e-166 | 6.81e-165 | 2,460 / 2,460 | rate ratio |
| segmented trend rule-date level ratio | 0.25272 | [0.17753, 0.35973] | 2.26e-14 | 1.77e-13 | 2,460 / 2,460 | rate ratio |

**Interpretation:** Take-labeled defensive fouls declined sharply after the rule change. Observed points on those possessions were higher afterward. The frequency result is strong as a descriptive pre/post association; causal value is not identified.

**Limits and prior coverage:** The denominator is all possessions, not transition opportunities. The common label includes more than perfectly classified transition-take events; documentation or classification could change. Two seasons and an offseason gap, with no unaffected comparison group, cannot isolate the rule from concurrent changes. The points comparison is not expected points conceded relative to a no-foul counterfactual, and retained-possession tagging can affect aggregation. Newly executed.

### H14. Whistle patterns after successful challenges

**Question:** Does a successful challenge change the next whistle pattern?

**Executed analysis:** Identified explicit Challenge replay decisions in the mobile feed, aligned them to the rich-CDN game clock, and compared foul rates in ten possessions before/after. The reviewed possession was excluded. Matched no-challenge windows within the same game/period on margin, remaining time and recent foul history, excluding nearby challenges. Tested successful-challenge difference-in-differences and successful versus unsuccessful challenges.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| successful challenge versus matched no-challenge change | -0.02114 | [-0.03903, -0.00474] | 0.01668 | 0.04588 | 809 / 638 | foul probability difference |
| successful_vs_unsuccessful_challenges: success | 0.02621 | [-0.00472, 0.05714] | 0.09668 | 0.20451 | 1,213 / 870 | coefficient |

**Interpretation:** Successful challenges are followed by lower foul rates relative to the selected no-challenge windows, but the success-versus-failure contrast does not clearly separate successful challenges from challenges generally. Treat the result as suggestive and design-sensitive.

**Limits and prior coverage:** All reviewed call types are included, not only foul calls. Matching is approximate and challenge timing is strategic. The pre-window can include the disputed incident, encouraging regression to the mean. Windows may overlap; game bootstrap accounts for within-game dependence but does not solve selection or matching bias. Newly executed.

### H15. Stability of referee-crew sequencing profiles

**Question:** Do exact referee crews have stable sequencing profiles across seasons?

**Executed analysis:** Built unordered triples of assigned officials and each crew-season's mean log immediate-persistence component. Matched exact triples in adjacent seasons and measured Spearman correlation, bootstrapping complete crew identities to preserve repeated years.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / crews | Unit |
|---|---:|---|---:|---:|---:|---|
| same assigned crew year-to-year log-immediate correlation | 0.0801 | [-0.06616, 0.22404] | 0.28194 | 0.48458 | 176 / 172 | Spearman correlation |

**Interpretation:** The cross-season correlation is about 0.08, with an interval spanning zero. This does not establish observable stability. Because crew-season estimates are extremely noisy, it also cannot support a dependable ranking or rule out stable latent differences.

**Limits and prior coverage:** No exact crew had at least two games in BOTH matched years, so the originally attempted three-game minimum yielded zero pairs. The fallback includes all repeated triples and was chosen after inspecting coverage. Noise attenuates correlations; team/matchup assignment is not randomized. These are crew-game associations, never attribution of another official's calls or evidence about intent. Newly executed with weak measurement reliability.

Matched sample: 176 crew-year pairs, 172 distinct crews; no repeated pair meets a two-game-per-year minimum.

### H16. Foul sequences and subsequent scoring

**Question:** Does recent foul history predict short-term scoring or style changes?

**Executed analysis:** Used past-only L2 at possession start to model net points, combined free-throw attempts, turnovers, rim attempts and elapsed game-clock seconds over t+1 through t+5. Included H1 controls and game-clustered uncertainty. Censored the final five possessions instead of filling unknown outcomes with zeros.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| future_net5: L2 | -0.03303 | [-0.04933, -0.01673] | 7.13e-05 | 0.000349 | 242,306 / 1,230 | coefficient |
| future_fta5: L2 | -0.00773 | [-0.02337, 0.00791] | 0.33285 | 0.53376 | 242,306 / 1,230 | coefficient |
| future_turnovers5: L2 | 0.00987 | [0.00122, 0.01853] | 0.02529 | 0.06323 | 242,306 / 1,230 | coefficient |
| future_rim5: L2 | 0.01354 | [0.00157, 0.02551] | 0.0266 | 0.06361 | 242,306 / 1,230 | coefficient |
| future_clock_seconds5: L2 | -0.34917 | [-0.52215, -0.17619] | 7.61e-05 | 0.000349 | 242,306 / 1,230 | coefficient |

**Interpretation:** Recent foul history is associated with roughly 0.033 fewer next-five net points from the current offense's perspective and about 0.35 fewer game-clock seconds over that window. Both are tiny. Free throws show no clear change; turnover and rim-attempt associations do not survive the global q<0.05 threshold. Statistical detectability should not be mistaken for useful forecasting magnitude.

**Limits and prior coverage:** This is an in-sample conditional-association analysis, not an out-of-sample scoring forecast. Five global possessions give unequal offensive opportunities; net points are oriented to the offense at t. FTA, turnovers and rim attempts pool both teams. Game-clock time is a pace proxy, not real elapsed time. Current F_t, future N_t and final WMI are not predictors. Previously not run; newly executed here.

### H17. Live foul features and win prediction

**Question:** Do live foul-history features improve win-probability predictions?

**Executed analysis:** Trained standardized logistic models on 2020–21 through 2022–23, selected regularization using 2023–24, refit on all training/validation games, and evaluated on held-out 2024–25 games. Sampled up to 16 regulation states per game. The baseline uses score, time, possession and past-updated Elo strength; the augmented model adds L2, recent foul count, bonus/team fouls and a smoothed cumulative WMI using only completed next-two windows.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| added foul features: held-out log loss change | 6.29e-05 | [-0.00016, 0.00029] | 0.59258 | 0.69345 | 19,680 / 1,230 | loss change; negative improves |
| added foul features: held-out Brier change | 2.1e-05 | [-7.28e-05, 0.000112] | 0.65361 | 0.73366 | 19,680 / 1,230 | loss change; negative improves |

**Interpretation:** The augmented model does not improve held-out log loss or Brier score. Both point changes are slightly worse and their game-bootstrap intervals include zero. There is no demonstrated predictive benefit from this feature set and model.

**Limits and prior coverage:** This is a real chronological test of this specification, not a proof that no richer model can benefit. No tracking, active lineups, player foul trouble or advanced sequence architecture was included. Elo starts at 1500, uses K=20 and 65 home-rating points, and shrinks 25% toward 1500 each offseason. Validation chooses C from 0.1, 1 and 10; test games do not choose it. Prior reports had only within-season splits; this test is stronger.

| Model | ROC-AUC | Average precision | Log loss | Brier | 10-bin ECE |
|---|---:|---:|---:|---:|---:|
| state_and_strength | 0.847276 | 0.872262 | 0.471362 | 0.158473 | 0.012496 |
| state_strength_and_fouls | 0.847241 | 0.872207 | 0.471425 | 0.158494 | 0.012305 |

ROC-AUC/average precision: higher is better. Log loss/Brier/ECE: lower is better. Average precision uses tie-aware scoring; ECE depends on binning and is secondary.

### H18. WMI versus foul volume and consequences (additional hypothesis)

**Question:** Does high WMI necessarily imply a large officiating impact? (Additional supplied hypothesis.)

**Executed analysis:** Compared full-game research WMI with counted foul volume, absolute foul differential, absolute free-throw differential and summed absolute baseline win-model movement through foul possessions. These comparison quantities use regulation only, matching the win model's domain. Bootstrapped games for Spearman intervals.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| WMI versus foul_volume | 0.08817 | [0.03306, 0.1429] | 0.00197 | 0.00677 | 1,230 / 1,230 | Spearman correlation |
| WMI versus abs_foul_difference | 0.0162 | [-0.04551, 0.07373] | 0.57031 | 0.69345 | 1,230 / 1,230 | Spearman correlation |
| WMI versus abs_fta_difference | 0.04807 | [-0.00692, 0.10333] | 0.09198 | 0.20236 | 1,230 / 1,230 | Spearman correlation |
| WMI versus foul_wp_movement | 0.01705 | [-0.04133, 0.07547] | 0.55025 | 0.68781 | 1,230 / 1,230 | Spearman correlation |

**Interpretation:** WMI has only a weak volume relationship and little relationship to the measured differentials or foul-associated win-probability movement. It is not interchangeable with foul volume or consequence magnitude.

**Limits and prior coverage:** Win-probability movement includes the score/clock/possession changes occurring during a foul possession and assumes a possession switch at its end. It is not the counterfactual causal effect of a call and says nothing about whether a call was correct. Full-game WMI versus regulation consequences is a stated scope mismatch in OT games. Previously attempted; rerun with a chronologically trained state model.

## What has and has not been completed

Completed: re-execution of the existing hypotheses, new empirical attempts for all previously unrun H1–H17 sections, supplemental H18, explicit sample sizes and effects, uncertainty and global multiple-test correction, new public-data joins, complete playoff coverage, a chronological win-prediction comparison, reproducible code and machine-readable outputs.

Still not established: causality of referee behavior, call accuracy, the optimum keep/bench/return policy, a reliable restricted-attendance natural experiment, video-level attack/contest changes, transition-opportunity-adjusted causal rule impact, or precise stable crew rankings. These are identification/data limits, not analyses that were silently skipped. The ten separate advanced model architectures elsewhere in the attachment—such as Hawkes processes, transformers and offline reinforcement learning—are not all implemented by this hypothesis-focused run.

## Reproduction and audit trail

From the project root, run `OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python run_all_wmi_hypotheses.py`. The runner downloads commit-pinned public archives into an ignored cache, builds separate tables, executes the hypotheses and regenerates this report. `--fetch-only` and `--prepare-only` stop at those stages. `--report-only` rebuilds the report from already executed results. Run `pytest -q tests/test_all_wmi_hypotheses.py` for the new targeted guards.

Files in this research folder: `all_hypothesis_results.csv` contains every reported estimate, interval, p and q; `analysis_details.json` contains formulas, sample details and prediction features; `run_audit.json` records automated coverage/scoring checks and hashes; `source_lock.json` and `source_manifest.json` pin the raw sources; `analysis_failures.json` lists failed analysis blocks. Section-specific CSVs retain model coefficients, matched events, crew pairs, component denominators and held-out predictions. The ignored `cache/` contains rich event and possession Parquet tables. Existing public datasets, earlier research outputs and unrelated working-tree changes were not overwritten by this runner.

Automated run audit: PASS. Each check is independently listed in `run_audit.json`. The tests validate targeted invariants, not every basketball interpretation or causal assumption.

## Sources and provenance

1. [NBA-data public archive](https://github.com/shufinskiy/nba_data): rich NBA CDN event archives for regular seasons 2020–21 through 2024–25, 2025 playoffs, and the 2024–25 mobile archive for replay decisions. These are third-party archived copies of NBA feeds, not a claim of direct live NBA API verification. Exact commits, URLs, byte counts and SHA256 values are saved locally.

2. [L2M research data archive](https://github.com/atlhawksfanatic/L2M): referee assignments and selected box/attendance data. Its close-game selection limits representativeness, and its assignment coverage stops before the final rounds of the 2025 playoffs.

3. [NBA Rule 12 — Fouls and Penalties](https://official.nba.com/rule-no-12-fouls-and-penalties/): basis for regulation/OT team-foul quotas and late-period penalty reconstruction.

4. [NBA transition-take-foul rule explanation](https://official.nba.com/video-transition-take-fouls/): policy context for the 2022–23 comparison; the archive's labels are an imperfect operational measure of the rule's targeted events.

5. Existing local project game-search data: home/date fallback for 18 playoff games and stored WMI for H9. Its content hash is recorded in `run_audit.json`. The user's supplied roadmap defines the hypothesis questions, not the empirical findings.


---

# WMI validation and replication

This report supersedes the prediction claims in the August exploratory report. WMI's formula is unchanged. Parser version: `period_start_v2`. Seed: 20260912. This is retrospective validation using final corrected play-by-play, not a prospective live-data trial.

## Dataset and parser audit

Processed 6,084 games and 1,208,809 possessions from commit-pinned archives. The source manifest records checksums; compressed possession partitions preserve all model inputs, outcomes, foul/player IDs and event descriptions. Reconstruction uses source possession ownership on live-event rows plus explicit period boundaries; substitutions, reviews and period markers cannot create possessions.

- 4,374 games change possession count versus the old parser on the SAME CDN source.
- Mean absolute game WMI change from the period/admin correction: 0.021651; maximum: 0.543544.
- On 1,230 overlapping 2024–25 regular-season games, mean absolute CDN-versus-stored-mobile WMI difference using the old grouping is 0.000652. This separates feed differences from the parser correction.
- Unassigned foul events across games: 16. These are retained as audit counts, not silently assigned to a team possession.
- Invalid timed events: 0. See failures.csv for game-level failures.

The start clock and score are taken from the preceding recorded event, resetting at period boundaries. This is a reconstructed reference point and can precede actual live-ball control. Regulation and overtime durations are handled separately; future overtime never enters predictors. Team-foul/bonus reconstruction includes regulation/OT thresholds and the last-two-minute rule, and excludes offensive, technical and double fouls from the team count. Rare rule exceptions and retrospective source edits remain limitations.

## Matched prediction comparison

Both models use exactly the same games and basketball-context variables. The history model adds five global foul lags and five same-defending-team foul lags. Training expands only through earlier seasons, with fixed logistic regression settings and no hyperparameter search. All possessions are included in the primary analysis. A separate sensitivity excludes all pre-specified late-strategy contexts, regardless of whether a foul happened.

| Season / cohort | Games | Context log loss | History log loss | Change (95% game-bootstrap CI) | Brier change |
| --- | --- | --- | --- | --- | --- |
| 2022-23 Regular Season | 1230 | 0.455264 | 0.455223 | -0.000041 (-0.000094, +0.000015) | -0.000008 |
| 2023-24 Regular Season | 1230 | 0.444665 | 0.444583 | -0.000082 (-0.000133, -0.000030) | -0.000022 |
| 2024-25 Regular Season | 1230 | 0.443315 | 0.443260 | -0.000055 (-0.000107, -0.000007) | -0.000010 |
| 2024-25 Playoffs | 84 | 0.481052 | 0.480753 | -0.000299 (-0.000519, -0.000109) | -0.000076 |

Negative change favors adding history. Confidence intervals resample entire games (1,000 draws). Full metrics, equal-game loss changes and late-strategy sensitivity are in prediction_results.csv. Calibration bins and intercept/slope are in calibration.csv; these describe held-out predictions and do not recalibrate test predictions. Historical 2024–25 exploratory results were already known, so the final season is a retrospective holdout rather than an untouched prospective test.

## Expansion decision

The replication gate passed. A directional forecasting follow-up is warranted.

The gate requires the upper paired loss interval to be below zero in both final regular-season evaluations, with no worse Brier score. It is a resource-allocation criterion, not proof of an officiating mechanism.

## Public interpretation and uncertainty

The site retains original snapshot rows for games without recalculated data, labels parser versions, and uses separate explicitly named percentile cohorts. Recalculated games expose the exact WMI decomposition, group sizes, both means and a team-labeled foul timeline. Same-team/opposite-team transitions are descriptive counts. No random-mark baseline is interpreted as evidence of makeup calls.

Per-game confidence intervals are withheld because the tested circular block method does not provide consistent coverage across the simulation scenarios; see the interval coverage study. Counts and denominator warnings are descriptive support diagnostics, not a validated reliability classifier. A percentile does not establish statistical significance, and a confidence interval containing one would not establish equivalence.

## Limits and next evidence

The dataset stores current-possession shot/rim attempts and free throws as outcomes, never as pre-possession predictors. It does not identify drives, paint touches, validated lineups, all player foul-trouble states or the official responsible for each call. Bonus status is reconstructed from feed labels; rare exceptions need additional adjudication. Observed-minus-expected foul volume is a context-model residual, not adjusted WMI or evidence of call error. Published final feeds may differ from what a live observer originally saw.

The original equation uses global windows across period boundaries and truncated windows at game edges. Those choices are preserved. Source ownership can still disagree with live-ball control in unusual administrative/retained-ball sequences; automated invariants and event-level spot checks do not replace comprehensive film review.

## Reproduce

Run `python validate_wmi.py` after the pinned inputs have been acquired by the existing fetch script. Use `--evaluate-only` to refit from saved partitions. `--max-games` is a development option and must use a separate output directory via `--output`; it must not overwrite full-release artifacts.

Sources: [NBA foul/penalty rules](https://official.nba.com/rule-no-12-fouls-and-penalties/), [NBA timing rules](https://official.nba.com/rule-no-5-scoring-and-timing/), [leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). Raw archive URLs and hashes are in dataset_manifest.json.

## Conditional sequence forecasts

The primary replication gate passed, so the pre-specified exploratory follow-up was executed. Team labels are 0=no foul in three possessions, 1=away commits first, 2=home commits first. Time labels are 0=no foul in five possessions or 1–5 for the first foul position, counting the current possession as position 1. Incomplete game-ending horizons are excluded. These are multinomial horizon forecasts; they are not fitted Hawkes or survival models.

| Target | Season | Context log loss | History log loss | Change (paired 95% CI) |
| --- | --- | --- | --- | --- |
| team, 3 possessions | 2023-24 | 0.941639 | 0.941629 | -0.000010 (-0.000054, +0.000033) |
| team, 3 possessions | 2024-25 | 0.940404 | 0.940366 | -0.000038 (-0.000085, +0.000009) |
| time, 5 possessions | 2023-24 | 1.610040 | 1.609708 | -0.000332 (-0.000481, -0.000193) |
| time, 5 possessions | 2024-25 | 1.608651 | 1.608418 | -0.000233 (-0.000397, -0.000077) |

The follow-up uses the same fixed models and earlier-season training rule. These additional outcomes are exploratory, without multiple-comparison-adjusted claims. Statistical improvements can be small in practical terms.

## Interval coverage validation

A raw-sequence circular block bootstrap was stress-tested on six specified processes, with 400 simulated games per process and 300 draws per interval. Empirical coverage for nominal 95% intervals ranged from 81.8% to 100.0%. No tested block length gave consistently adequate coverage across all scenarios. Per-game intervals therefore remain withheld; sample counts and denominator diagnostics are displayed instead. See [the coverage study](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/validation_2026_09_12/interval_validation.md) and [simulation results](interval_coverage.csv). This tests one candidate method, not every possible uncertainty estimator.


---

# Per-game interval coverage stress test

Candidate: circular moving-block bootstrap of the raw foul indicator, recomputing all WMI windows after concatenation. Game length 200, 400 synthetic games per scenario, 300 bootstrap draws per interval, seed 20260912. Blocks of 5/10/20 possessions are compared. The oracle is the ratio of expected sufficient statistics for each specified finite-length process, computed by enumerating local five-possession patterns. This is an inferential process parameter, not uncertainty about an already observed arithmetic game score.

| Scenario | Block | Valid / 400 | Coverage | Median width |
| --- | --- | --- | --- | --- |
| independent_low | 5 | 400 | 98.0% | 2.292 |
| independent_low | 10 | 400 | 89.2% | 2.046 |
| independent_low | 20 | 400 | 81.8% | 1.825 |
| independent_typical | 5 | 400 | 98.2% | 1.435 |
| independent_typical | 10 | 400 | 95.8% | 1.355 |
| independent_typical | 20 | 400 | 92.5% | 1.286 |
| positive_dependence | 5 | 400 | 92.5% | 2.557 |
| positive_dependence | 10 | 400 | 90.5% | 2.649 |
| positive_dependence | 20 | 400 | 87.0% | 2.598 |
| strong_dependence | 5 | 400 | 85.0% | 4.959 |
| strong_dependence | 10 | 400 | 89.2% | 5.770 |
| strong_dependence | 20 | 400 | 89.2% | 6.171 |
| negative_dependence | 5 | 400 | 100.0% | 0.830 |
| negative_dependence | 10 | 400 | 97.8% | 0.763 |
| negative_dependence | 20 | 400 | 92.2% | 0.706 |
| rate_shift | 5 | 400 | 89.8% | 2.121 |
| rate_shift | 10 | 400 | 93.2% | 2.627 |
| rate_shift | 20 | 400 | 95.0% | 3.039 |

Nominal coverage is 95%; sampling error for 400 simulations is about 1.1 percentage points at nominal coverage. Circular joins can create artificial foul sequences, particularly when foul probability changes within a game. Finite denominators also make intervals unstable. No interval is released on the website from this experiment: the tested method must demonstrate acceptable coverage across plausible nonstationary basketball contexts, and the inferential target/assumptions must be explained to users. Other bootstrap constructions may behave differently. This is a stress test of one candidate, not evidence that all uncertainty methods fail.
