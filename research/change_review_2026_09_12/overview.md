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
