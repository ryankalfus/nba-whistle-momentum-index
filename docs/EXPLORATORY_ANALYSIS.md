# Provisional real-data exploratory analysis

Date: 2026-11-08. Version: `provisional-exploratory-v1`. Scope: user-authorized, retrospective development diagnostics. Not an independent validation, confirmatory evaluation or scientific release.

## Two distinct routes

The user authorized a separate exploratory analysis after discontinuing the large film-review campaign. `whistle_research.exploratory.run_exploratory` can fit verified, explicitly selected provisional rows and write local development results. It does not call a provisional game eligible or generate audit evidence. `modeling.fit_real`, `evaluation.evaluate_real`, conditional promotion and their existing scientific checks remain unchanged. An exploratory result cannot be supplied as a passing audit or promoted dataset.

Every exploratory report/result declares `EXPLORATORY_ONLY_NOT_VALIDATED`, retrospective previously exposed evaluation, `eligible: false`, `scientific_approval: false` and `publication_authorized: false`. The source dataset and every original game remain ineligible. There is no full-game review quota and no 1% game-error claim.

Actual model results, selected rows, predictions, reports and generated explorer data stay in ignored local output. The repository contains implementation, the planned specification, tests and reproducibility instructions. No deployment or new public empirical finding is authorized by this route.

## First declared analysis

[specification.json](../research/exploratory_2026_11_08/specification.json) selects the already-exposed **2024–25 regular season**. This is a retrospective development choice, not unused evaluation data. The local specification is saved before the first real fit and the tested implementation/specification receives a Git checkpoint before that run. Neither action is authenticated external preregistration.

Whole-game date partitions are left-closed/right-open:

| Partition | Start | End |
| --- | --- | --- |
| Training | 2024-10-01 | 2025-01-01 |
| Tuning | 2025-01-01 | 2025-02-15 |
| Evaluation | 2025-02-15 | 2025-04-14 |

Same-date games stay in the same partition. No date boundary, cohort, regularization grid or usefulness threshold is selected after viewing this run's evaluation results. Later changes require a separately identified analysis, preserving the earlier artifacts and exposure history.

## Verified inputs and whole-game selection

Before selection, the loader rehashes all declared raw sources and validates the full independent schedule, inventory, current parser/feature hashes, reconciliation and complete aligned row/provenance streams. It verifies original row/list/file hashes and per-game accounting. These are integrity checks, not proof that recorded events or possession boundaries are true.

Every source-frame game remains in a ledger. Exact season/type/date selection defines the candidate cohort. Within that cohort, exclude a whole game for quarantine/unreconstructed status, incomplete reconstruction, critical or unknown quality, unknown target, flagged/incomplete row provenance or unassigned live control. Unknown metadata is never interpreted as a favorable flag. Preserve all applicable reasons and a separate primary reason; overlapping reason counts are not summed as disjoint games. Report source-frame and candidate unknown-target counts, included/excluded games and rows, and partition-level missing predictors.

Explicit unassigned administrative event references are preserved. They do not by themselves exclude a game when the parser explicitly records `unassigned_control_events: false` and the other quality checks pass. An administrative exclusion is not a new possession. Live-control ambiguity still excludes the game.

Keep every row of each selected game, its original possession number and supplied prior-global history. Never drop an individual unknown target, join across excluded opportunities or recompute history on a shortened axis. Missing predictor/history values remain null in the selected rows. The original dataset retains all its unknown outcomes and flags. Selection for this calculation is distinct from scientific eligibility and can induce selection bias; results concern this quality-selected retrospective subset, not all NBA games.

The loader streams the full source export and only retains selected game rows. A hard 250,000-selected-row ceiling refuses an oversized analysis rather than truncating or silently sampling it. This bounds the existing list-based model learner on the development machine; it is not a general large-data training system.

## Matched models and mathematical interpretation

Reuse the unchanged four-model ladder in [MODELING_CONTRACT.md](MODELING_CONTRACT.md): training base rate, additive context, nonlinear context, and identical nonlinear context plus the two supplied past global foul indicators. Fixed predictor allowlists exclude current outcomes, future windows, terminal scores, final WMI and date/game identifiers. Preprocessing is learned on training rows only. History missingness indicators are part of the declared history feature bundle; any loss difference cannot be attributed solely to dependence between observed foul values.

Each logistic model uses the same declared `C={0.1,1,10}` grid, training data, tuning loss rule and convergence requirements. The tuning partition selects regularization. There is no training-plus-tuning refit or evaluation-driven retry. Single-class training, convergence warnings, malformed rows, unknown included targets and altered source/code bytes withhold the comparison.

For evaluation game `g`, let `D_g` be the sum of history-minus-context binary log-loss differences and `n_g` its scored possession count. The primary descriptive difference is `sum(D_g) / sum(n_g)`. Negative values mean lower observed loss for the history model on these selected evaluation rows. Also report equal-game loss, Brier scores, calibration and the existing cohort breakdowns. All models must predict the identical ordered evaluation row IDs.

The nominal 95% whole-game percentile interval uses 999 resamples and seed 137, resampling each game's paired loss sum and count together. It conditions on fitted, development-selected models and this selected cohort, assumes independent identically distributed games, omits training/selection uncertainty and calendar/series dependence, and has no demonstrated coverage guarantee here. It is not an independently validated population interval. No meaningful-gain threshold is invented: `meaningful_gain` is null and classification remains `NOT_SPECIFIED`. Neither a negative estimate nor an interval excluding zero establishes usefulness, causality, referee intent or call correctness.

## Reproduce the local run

Use the pinned project environment and a **new** output directory. These explicit inputs reuse the current verified v7 artifacts; there is no parser/cohort fallback or network acquisition.

```sh
.venv/bin/python -m whistle_research.exploratory --plan research/exploratory_2026_11_08/specification.json --features output/v2/features-v7-reviewed-2026-11-02 --inventory output/v2/source-inventory-independent-2026-11-02/inventory.json --reconciliation output/v2/reconciliation-v7-reviewed-2026-11-02/report.json --source-manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --schedule research/rewrite_completion_2026_11_02/schedule_expected.json --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2021_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2022_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2023_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2024_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --output output/v2/NEW_EXPLORATORY_RUN
```

The run writes a byte-preserved plan snapshot, full cohort ledger, selected-row JSONL, aligned prediction JSONL, model result, report JSON and human-readable report. The report's artifact catalog binds exact file bytes. Result provenance binds the selected/partition rows, test features, actual inputs, current implementation, model specification and fitted preprocessing/coefficients. Inputs and code are rechecked before fitting and before/after publication. Failures preserve existing inputs/outputs and do not leave a successful-looking new report.

Generate a local notebook with the existing development/synthetic evidence and the new exploratory result. This does not replace repository `v2/data.json` or publish results:

```sh
.venv/bin/python scripts/export_v2_site.py --report output/v2/development-pipeline-v7-2026-11-02/report.json --math output/v2/development-pipeline-v7-2026-11-02/synthetic_math.json --models output/v2/development-pipeline-v7-2026-11-02/synthetic_models.json --exploratory output/v2/NEW_EXPLORATORY_RUN/report.json --output output/v2/NEW_EXPLORATORY_NOTEBOOK --bundle
```

The exporter verifies exploratory artifact bytes, roles, schemas, plan identity and false approval flags before compaction. Supply the exact raw files named by the base report's artifact bindings; a JSON-equivalent file with different serialization is refused. The notebook labels the real-data section provisional and retains the separate synthetic demonstration and closed scientific-release gate. The local bundle includes the notebook assets and linked methods documents. Serve the repository over HTTP and open the generated notebook directory; do not deploy it as a scientific release.

Actual execution paths, opaque artifact hashes and software/browser verification are recorded in [the run handoff](../research/exploratory_2026_11_08/README.md). A clone without the ignored source cache/exports cannot reproduce or independently inspect the real-data result until those verified inputs are supplied.
