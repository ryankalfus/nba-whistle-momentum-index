# Plan-faithful Stage 5 — 2026-11-09

This directory declares the first `plan-stage5-v1` fit, the Stage 5 comparison from the agreed project plan document. Model A is L2 logistic regression on the plan's shared context, including both teams' team fouls and penalty state. Model B adds one flag for a counted defensive foul in either of the previous two global possessions. One shared penalty is chosen with Model A on 2021–22, and both models are refit for each test season 2022–23, 2023–24 and 2024–25. The full specification and every deviation are in [PLAN_STAGE5.md](../../docs/PLAN_STAGE5.md).

[specification.json](specification.json) was saved and pushed before any real `plan-stage5-v1` fit. It binds the hashes of the nine modules on the data and model path; any later edit invalidates the plan rather than silently changing it. Every approval flag is false, the meaningful gain is null and every season is previously exposed.

A no-fit preflight on 2026-11-09 loaded the full cohort and derived team fouls for all 3,829 selected games. The derived defense count matched the parser's count on all 759,372 rows, with no unknown counts and no season/partition disagreements. No model was fitted in the preflight.

## Run

Use a new output directory. Inputs are the same verified v7 artifacts as the earlier exploratory runs.

```sh
.venv/bin/python -m whistle_research.exploratory --plan research/plan_stage5_2026_11_09/specification.json --features output/v2/features-v7-reviewed-2026-11-02 --inventory output/v2/source-inventory-independent-2026-11-02/inventory.json --reconciliation output/v2/reconciliation-v7-reviewed-2026-11-02/report.json --source-manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --schedule research/rewrite_completion_2026_11_02/schedule_expected.json --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2021_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2022_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2023_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2024_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --output output/v2/plan-stage5-2026-11-09/analysis
```

Actual results stay in ignored local output.

## Actual execution

The plan and code were committed and pushed at `fd22907` before the fit, and a pre-fit checkpoint hashed the plan, code and every protected input. The fit ran once on 2026-11-09 into `output/v2/plan-stage5-2026-11-09/analysis/`, which holds the plan snapshot, cohort ledger, selected rows, team-foul states, fold-labelled predictions, model result with per-fold coefficients and preprocessing state, and reports.

A separate replay script beside it uses its own context, imputation, scaling and one-hot code. It reproduced the shared penalty choice, refit all three test folds to within a few trillionths in probability, and recomputed every pooled and per-season metric and bootstrap interval exactly. All protected inputs, including both earlier runs, are byte-unchanged after the fit. [execution_receipt.json](execution_receipt.json) records artifact hashes and verification flags without model values. The replay checks software and arithmetic consistency only.
