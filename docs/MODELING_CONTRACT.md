# Matched modeling and evaluation contract

Date: 2026-11-02. Version: `matched-model-v1`. State: implemented and synthetically tested; real research remains blocked by independent audit, eligibility and protocol requirements. No real NBA fits or confirmatory evaluation were executed.

Update 2026-11-08: the gate statements below describe the unchanged strict `fit_real`/`evaluate_real` route and historical synthetic evidence. The user separately authorized an explicitly provisional retrospective exploratory route, specified in [EXPLORATORY_ANALYSIS.md](EXPLORATORY_ANALYSIS.md). It reuses the model/evaluation mathematics on a verified, fully accounted selected cohort, keeps every source/game ineligible, and writes local results with no scientific/publication approval or practical-use classification. It does not relax this strict contract or supply its missing evidence.

## Entry points and scientific gate

`modeling.fit_real(rows, evidence=...)` and `evaluation.evaluate_real(rows, evidence=...)` verify the complete row export before fitting or scoring. They call the existing `audit.check_gate(plan,reviews,config)` and require `PASS_CONDITIONAL`; a caller-supplied passing status is insufficient. Invalid or missing evidence raises `BlockedError` with a machine-readable `BLOCKED` report and next step.

After the audit check, the evidence must contain:

- `plan`, `reviews`, `config`: the complete bound independent-audit evidence, including schedule, reviewer, source, parser and tolerance requirements enforced by the existing gate.
- `dataset`: the conditionally audited adapter manifest produced by `release.prepare_promotion`, including `promotion_inputs` that identify the original provisional export/source/schedule/metadata paths; plus `plan_sha256`, `parser_version`, `parser_sha256`, `frame_sha256`, canonical `rows_sha256`, and exactly one `games` entry for every included game. Every entry must explicitly declare `eligible: true`, `complete: true`, `critical_unresolved: false`, and a `source_sha256` matching the audit frame. Unknown eligibility or completeness is refused; row season/game-type metadata must match the source frame. Every public real entry invokes `release.validate_promoted_dataset`, which regenerates promotion from the actual original files and genuine audit evidence, then requires exact equality. Schema labels and manually flipped eligibility cannot substitute for stream/provenance/source verification. Unknown outcomes, incomplete provenance, any row audit flag, blocking game issues or unassigned control events block promotion.
- Both `dataset` and `protocol` also require `feature_version` and `feature_sha256` matching the local `features.FEATURE_VERSION` and `features.feature_module_sha256()`; an absent or changed feature adapter fails closed.
- `source_root`: the runtime root of portable relative `source_file` paths from the frame. The implementation resolves paths safely and rehashes each distinct source file, comparing actual bytes with the frame. This runtime location is not a hardcoded project path.
- `protocol`: `frozen: true`, nonempty `freeze_id`, timezone-aware `frozen_at`, `evaluation_exposure: "unseen_at_freeze"`, nonempty `exposure_inventory_ref` and `unused_cohort_evidence_ref`; the same parser/plan/frame/row bindings; `specification_sha256`; `split`; and a positive finite `meaningful_gain`. `protocol_sha256` is the canonical digest of all protocol fields except itself.
- `evaluation_started_at`: a timezone-aware timestamp strictly after protocol freeze.

`specification_sha256` binds the canonical output of `modeling.specification()`: feature allowlists, fixed transformations, models, grid, solver/iteration limit, training-only selection rule, loss clipping, bootstrap settings, and SHA-256 hashes of model, evaluation and authoritative promotion-validation implementation files. `rows_sha256` hashes all input fields and their row order through `audit.digest`; no target is silently removed. Frozen bindings are invalidated when rows, parser, frame, specification or source bytes change. The dataset and protocol also bind the local before-event feature implementation.

These checks establish internal consistency, not the truth of outside attestations. In particular, the code cannot establish that an exposure inventory is complete, footage was actually reviewed, a threshold was chosen without outcome knowledge, or supplied rows genuinely came from the claimed reconstruction. An independently audited feature-export adapter and retained provenance remain necessary. A passing conditional audit alone is never publication approval.

The CLI defaults to an internally generated synthetic demonstration. Synthetic mode rejects `--rows` and `--evidence`; it cannot disguise arbitrary supplied data as synthetic. Real mode accepts a JSON array of row objects (`.json`) or one object per nonblank line (`.jsonl`) and a JSON evidence object, routing them through `fit_real` and every gate. JSON rejects nonfinite constants, overflowing floating-point numbers and duplicate fields. An independent-audit preflight runs before opening the target export, so absent audit evidence refuses even a large or protected input without reading its outcomes.

```sh
.venv/bin/python -m whistle_research.modeling real --rows output/AUDITED_EXPORT/rows.jsonl --evidence research/FROZEN_RUN/evidence.json --output research/NEW_REAL_RUN/result.json
```

No unvalidated-data override exists on the strict real-fit route. Missing input/evidence, failed gates, malformed files and model-input failures return actionable `BLOCKED` JSON and exit 1. With `--output`, that blocked report is written exclusively to the requested new file; without it, the report goes to stdout. Successful gated results exit 0. Existing outputs are never overwritten; attempted collisions report `BLOCKED` to stdout before reading inputs or fitting. Relative source paths in the evidence resolve under its explicitly supplied runtime `source_root`. Strict real CLI use does not fabricate audit reviews, freeze the protocol or supply a meaningful-effect threshold.

## Row and split contracts

Rows contain `game_id,date,season,game_type,possession_number,period,clock,score_margin,score_difference,defense_team_id,offense_team_id,home_defense,defense_counted_fouls,previous_foul_1,previous_foul_2,start_type,outcome`. Only the declared context/history fields enter the design matrix. Game/date/season/type metadata and identifiers never enter predictors. Unrecognized extra fields, including future outcomes and final WMI, never enter predictors. Every target must be a known binary integer; unknown targets cause refusal rather than complete-case filtering. This implementation predicts recorded counted calls and does not estimate call correctness, intent, or causal effects.

Game metadata must be consistent within game; possession numbers must be unique positive integers in increasing within-game input order. Dates use `YYYY-MM-DD`. Numeric missing values are `None`; nonfinite values are rejected. Missing context and histories remain explicit model inputs. `home_defense` and supplied history values are binary or missing. Clock/period bounds and nonnegative absolute margin/counts are checked. Signed `score_difference` is the before-event defense score minus offense score; both signs are allowed, and missing scores remain missing. The research counted-foul feature is **not** asserted to be official bonus state.

The frozen `split` contains four strictly increasing dates: `train_start,tune_start,test_start,test_end`. Intervals are `[train_start,tune_start)`, `[tune_start,test_start)`, and `[test_start,test_end)`. Entire games are assigned by their consistent game date; same-day games cannot cross boundaries. Rows outside this range, overlapping/reversed dates, or empty partitions cause refusal. No random possession split or train/test game overlap is permitted. The exporter must preserve the original possession axis and prove past-only availability; filtering/reindexing possessions based on their current target is prohibited.

## Matched model ladder

The training base rate uses only the training target mean. All logistic candidates use the same train/tune/test partitions:

1. Additive context: numeric `period,clock,score_margin,home_defense,defense_counted_fouls`; categorical `defense_team_id,offense_team_id,start_type`.
2. Nonlinear context: identical context plus signed `score_difference` and four fixed terms: `(clock/720)^2`, `(score_margin/30)^2`, `(score_margin/30)*(clock/720)`, and `home_defense*(score_margin/30)`.
3. Nonlinear history: exactly that nonlinear context design plus the supplied immediately previous and second-previous global possession foul indicators. The terms involving current context do not change when history is added.

This additive model follows the declared v2 input contract; it is not asserted to reproduce every historical legacy covariate or numerical result. No official bonus feature is inferred from research counted fouls, and no unverified tracking/lineup input is introduced.

All numeric columns have fixed missing indicators, including columns that happen to be completely observed during training. A constant-zero imputer and standard scaler fit only training rows; the missing flag distinguishes an imputed zero from an observed zero. Categorical missingness uses a reserved `__UNKNOWN__` token; observed values have a `value:` prefix, preventing sentinel collisions. One-hot encoding learns training categories only, and unseen categories yield all-zero encoding. No tuning/test values influence imputer/scaler/category fitting. Numeric interactions are fixed row-local formulas and use no target or future information.

Each logistic model evaluates the same `C={0.1,1,10}` grid, L2 regularization, deterministic `lbfgs`, and 2,000-iteration cap. Lowest tuning possession-weighted log loss selects the candidate; the first grid value breaks ties. Selected pipelines remain fitted to training rows only; no train+tune refit occurs. The base rate has no tunable parameters and therefore no invented grid budget. All candidates and tuning scores are reported. Any convergence warning aborts the comparison; candidates are never silently dropped. Single-class training data explicitly withholds the matched logistic comparison instead of manufacturing a fit or silently substituting a different model.

## Held-out endpoints and uncertainty

The internal fitted-model path must produce probabilities for the same exact ordered `(game_id,possession_number)` list, with no unknown targets, missing models, row drops, or mismatched array lengths. Probabilities must be finite in `[0,1]`. Log loss clips probabilities to `[1e-15,1-1e-15]` for numerical evaluation; Brier scores use supplied probabilities.

The primary estimate is possession-weighted paired held-out log loss, history minus nonlinear context. Negative favors history. Reports also contain each model's log loss, Brier score, fixed ten-bin observed-versus-predicted calibration table (including empty-bin counts), equal-game mean log loss, paired Brier difference, and season/game-type breakdowns. Playoff rows remain separately identifiable. Calibration tables are descriptive and do not claim perfect calibration or substitute for a prespecified recalibration study.

For each game `g`, let `D_g` sum the paired log-loss differences and `n_g` count evaluation possessions. The main estimate is `sum D_g / sum n_g`; the separate equal-game estimate is `mean(D_g/n_g)`. The whole-game paired bootstrap resamples game indices with replacement, keeping both models' loss difference and each game's count attached. Each draw recomputes the ratio of summed losses to summed counts, preserving possession weighting; it does not average game means unless reporting the explicitly equal-game endpoint.

The reported 95% percentile interval uses 999 draws and seed 137. Its population target is `E[D_g]/E[n_g]` for independently identically distributed evaluation games from the declared population, **conditional on the fitted and development-selected models**. At least two games are required for computation; this minimum does not imply adequate empirical coverage. Training, tuning, selection variability and calendar/series dependence are not included. No calendar-block sensitivity is implemented. Public `evaluate_real` does not accept prediction packets: it invokes the gated matched fitting procedure and scores only that procedure's fresh predictions. `fit_real` calls the private scorer directly, avoiding a recursive or duplicate fit. Caller-supplied stale or outcome-derived prediction packets cannot enter either public real-data path. Private `_evaluate` is reserved for internal scoring and synthetic arithmetic tests; it confers no scientific approval.

Returned real artifacts bind protocol and full/partition row hashes, exact ordered test row IDs, selected test-feature hash, model specification and implementation hashes, parser/feature hashes, source hashes, audit-plan/review/config hashes, promoted/original-manifest and row/provenance-file hashes, and deterministic digests of fitted coefficients and preprocessing state. These bindings document the internal fit, while outside evidence still requires independent authentication. Cluster bootstrap coverage is not guaranteed by passing arithmetic tests; population validity, sufficient support and dependence diagnostics remain required before real inference.

A real frozen protocol must explicitly provide the meaningful log-loss gain and accept the implementation's frozen symmetric practical band. For paired delta interval `[lo,hi]` and gain `g>0`: useful requires `hi<-g`; negligible under the declared band requires `lo>-g` and `hi<g`; unsupported/harmful requires `lo>g`; all other cases are inconclusive, including touching a boundary. Merely containing zero never establishes equivalence. No real threshold is invented by the synthetic demonstration: its decision is `NOT_SPECIFIED`.

## Reproduction and observed synthetic demonstration

Choose a new output file; existing files are refused:

```sh
.venv/bin/python -m whistle_research.modeling synthetic --seed 20261102 --output research/NEW_MODEL_DEMO/model_demo_summary.json
```

The saved [model_demo_summary.json](../research/rewrite_completion_2026_11_02/model_demo_summary.json) uses 90 synthetic games with 36 possessions each, a fixed known logistic transition with immediate/second-previous foul terms, and chronological partitions of 54/18/18 games. Team/start/count fields are synthetic inputs, not simulated NBA rule validation. The report records software versions, seed, row hash, source hashes/specification, split game IDs, all candidate scores and held-out metrics. There is no network or archive read in the demo.

Observed held-out log losses are base rate **0.4338450**, additive context **0.4283188**, nonlinear context **0.4284423**, and nonlinear history **0.4260396**. Paired delta is **-0.0024027**, with conditional whole-game percentile interval **[-0.0086265,0.0033135]**. These are reproducibility diagnostics of this generator, not an empirical conclusion. The interval crosses zero; no meaningful threshold or usefulness conclusion is supplied. Label-permutation tests evaluate all seeds 0–9 and show improvements of both signs rather than guaranteeing that history wins.

Focused tests cover whole-game chronology, target refusal, source/hash/eligibility/freeze failures before fitting, train-only preprocessing, unseen categories and missing context, outcome/future-column exclusion, unchanged selection after test-label perturbation, matched grids/rows, explicit convergence/single-class failure, loss/cluster weighting, practical rules and deterministic replay. Passing these tests does not authorize a real fit, unlock the protocol, independently validate the parser, or approve scientific publication.
