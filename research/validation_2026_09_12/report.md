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

A raw-sequence circular block bootstrap was stress-tested on six specified processes, with 400 simulated games per process and 300 draws per interval. Empirical coverage for nominal 95% intervals ranged from 81.8% to 100.0%. No tested block length gave consistently adequate coverage across all scenarios. Per-game intervals therefore remain withheld; sample counts and denominator diagnostics are displayed instead. See [the coverage study](interval_validation.md) and [simulation results](interval_coverage.csv). This tests one candidate method, not every possible uncertainty estimator.
