# Plan-faithful Stage 5 specification (`plan-stage5-v1`)

Date: 2026-11-09. Status: **declared before fitting; implementation and first fit pending in this change.** Not independently validated, not a confirmatory evaluation, not published.

## Why this exists

The user's Google Doc `project_plan` (Crimson Indigo workspace, last edited 2026-10-23) is the staged plan agreed for the paper. Its Stage 5 asks for two directly comparable L2 logistic models on future seasons. The 2026-11-09 `meeting-ab-v1` run was built from a shorter handoff summary and differs from that plan: its context omits both teams' team fouls and penalty state, the squared terms, the late close-game indicator and season type; it tunes each model separately; and it splits one season by date. [MEETING_ALIGNMENT.md](MEETING_ALIGNMENT.md) records that design. This document specifies the version that follows the plan as written, with only the deviations the data force.

The plan was written before either real fit, so following it is not an outcome-driven revision. Every season used here was nevertheless analyzed in earlier project work ([EXPOSURE_INVENTORY.md](EXPOSURE_INVENTORY.md)), so all results stay retrospective development evidence.

## Design

| Plan element | `plan-stage5-v1` |
| --- | --- |
| Target | `F_t`: at least one counted defensive foul in possession `t`; the existing target, recorded calls only |
| Model A | L2 logistic regression on the shared context below |
| Model B | The identical design plus one column `L_t = 1{F_(t-1)=1 or F_(t-2)=1}` |
| History axis | Previous two global possessions in the same game, irrespective of team, crossing period boundaries |
| Paired sample | The first two possessions of each game are excluded from both models, so full history exists |
| Penalty selection | One shared `C` from `{0.1, 1, 10}`: fit Model A on the training season, pick the lowest validation log loss, first grid value on ties; apply unchanged to both models in every test fold |
| Preprocessing | Fit on training rows only: median imputation with fixed missing indicators for every numeric context column, standardization of all numeric columns, one-hot teams with unseen teams encoded as all zeros |
| Class weighting | None |
| Clipping | Both models' probabilities clipped to `[1e-6, 1 - 1e-6]`; the number clipped is reported |
| Base rate | Training prevalence per fold, reported as a sanity check only |

### Shared context (identical in A and B)

- Offense and defense team identity (categorical).
- Offense home indicator.
- Period and period clock in seconds.
- Score margin from the offense perspective (offense score minus defense score).
- Clock squared and margin squared.
- Playoff indicator (1 for a playoff game).
- Defense and offense period team fouls before the possession.
- Defense and offense penalty state before the possession.
- Late close-game indicator: period 4 or overtime, at most 120 seconds left, absolute margin at most 10.

Every value is taken at the existing possession-start reference point. Current outcomes, future windows, `N_t`, `M_t`, WMI, dates and game identifiers never enter the design.

### Team fouls and penalty state

Source: NBA Rule No. 12, Section B.V and related sections, read 2026-11-09 at <https://official.nba.com/rule-no-12-fouls-and-penalties/>.

- **Team fouls** count foul events with subtype `personal`, `shooting`, `loose ball`, `flagrant1`, `flagrant2`, `clear path`, `away from play`, `transition take` or `take`, charged to the fouling team. Loose-ball fouls count for either team (VIII.1.a); flagrant, away-from-the-play and clear-path fouls are included in the team total (V.5).
- **Not team fouls:** `offensive` (VII.1.c), `technical` and `double technical`, and double personal fouls including `personal` with descriptor `double` (VI.2). The rule page is silent on take fouls; they are personal fouls and are counted.
- **Quota:** four team fouls per regulation period, three per overtime period (V.1, V.1.b, V.1.d).
- **Penalty state** for a team before a possession is 1 when its period team fouls are at least the quota, or when the possession starts with at most 120 seconds left and the team has committed at least one team foul in the last two minutes (V.1.c). A foul at exactly 120.0 seconds remaining is treated as a last-two-minutes foul.
- **Timing** mirrors the parser: fouls are counted over the parser's sorted event order strictly before each possession's first event, skipping administrative events. Any game with a flagged possession withholds the states, because only unflagged possessions are guaranteed to match the parser's nullness; an unobserved period start, a memo, an unsupported foul label or a foul without a team all flag a possession. A null count path (imputed with an indicator) remains as a defensive fallback; the preflight found no null counts in the selected cohort.
- **Cross-check:** in every selected game, the derived defense team-foul count must equal the existing research `defense_counted_fouls` value on every row, including nullness. Games with offense-side personal or loose-ball fouls, double fouls, memos or unsupported labels are already excluded by the quality policy, so the two definitions coincide there. Any mismatch withholds the fit.
- These are reconstructed from final corrected play-by-play. They are not official live bonus flags, and overturned or rescinded fouls that remain in the feed are counted.

### Cohort and folds

The archive covers the 2020–21 through 2024–25 regular seasons and the 2024–25 playoffs, so the plan's 2018–19 start is not available. The plan allows a contiguous covered span if declared before evaluation. Whole-game quality policy `whole_game_quality_filter_v1` is unchanged.

| Fold | Training seasons | Evaluated on |
| --- | --- | --- |
| Validation (choose `C`) | 2020–21 | 2021–22 |
| Test 1 | 2020–21, 2021–22 | 2022–23 |
| Test 2 | 2020–21 through 2022–23 | 2023–24 |
| Test 3 | 2020–21 through 2023–24 | 2024–25 regular season and playoffs |

Each test fold refits both models on all earlier included seasons with the frozen `C`. Whole games stay in one partition; no test season or later season is ever used for training. Loader date partitions are training from 2020-12-01, tuning from 2021-07-01, test from 2022-07-01 to 2025-07-01, and every row's season must agree with its date partition.

The playoff indicator is constant (zero) in every training fold because only the 2024–25 playoffs are archived. It is kept because the plan lists it, but its coefficient cannot be learned; playoff rows are reported separately.

### Metrics

- **Primary:** `ΔLL = mean[logloss(B) - logloss(A)]` over identical held-out possessions, pooled across the three test seasons, natural log. Negative favors history.
- **Uncertainty:** 2,000 paired whole-game bootstrap resamples, seed 137, percentile 95% intervals conditional on the fitted models. The pooled interval resamples games within each test season and recomputes the possession-weighted pooled difference. Its generator is `numpy.random.default_rng(137)`, drawn with one `integers(n_games, size=(2000, n_games))` call per test season in fold order over that season's games sorted by game ID. Each season's own interval uses the same procedure with `default_rng([137, k])` for test fold `k`.
- **Secondary:** each model's log loss, relative reduction `ΔLL / logloss(A)`, paired Brier difference, equal-game difference, ten fixed calibration bins with counts, calibration intercept with a `logit(p)` offset and calibration slope (diagnostic only, never used to recalibrate), games, possessions, counted foul events and prevalence, all pooled and per season, plus regular-season and playoff breakdowns.
- **Decision:** the primary hypothesis is no improvement in expected held-out log loss. An interval entirely below zero supports improvement; an interval containing zero is reported without claiming equivalence. No meaningful-gain threshold is declared, so the usefulness classification is `NOT_SPECIFIED`.

## Deviations from the plan

- Seasons start at 2020–21, so training is shorter and the validation season is 2021–22.
- The playoff indicator cannot be learned; playoffs are evaluated separately in the last fold only.
- Team fouls come from the existing parser's events, not a new parser; possession boundaries and targets are the existing `canonical_candidate_v7` reconstruction.
- Outputs follow the project's bound-artifact format: the plan's `split_manifest.csv`, `feature_spec.json`, saved models and `heldout_predictions` are recorded as fields and JSONL files of the run, with hashes.
- Stage 6 sensitivities (late-strategy exclusion, within-period history, common-parser sample, two-lag ablation) are not part of this change.

## Process

The specification, its plan file and the implementation are committed and pushed before the first real fit, following the first exploratory run's precedent. The fit writes only to a new ignored output directory. A separate replay script refits the models with its own design code. Nothing is merged or deployed without the user's request.
