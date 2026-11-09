# Meeting-aligned exploratory plan — 2026-11-09

This directory declares the first `meeting-ab-v1` fit, the two-model comparison chosen in [MEETING_ALIGNMENT.md](../../docs/MEETING_ALIGNMENT.md). Model A is additive L2 logistic shared context. Model B is the identical design plus one flag for a counted defensive foul in either of the previous two global possessions. The method contract is in [EXPLORATORY_ANALYSIS.md](../../docs/EXPLORATORY_ANALYSIS.md).

[specification.json](specification.json) was saved before any real `meeting-ab-v1` fit. It reuses the cohort, whole-game quality policy and date partitions of `2024-25-regular-retrospective-v1`, so only the model specification differs. It binds the hashes of `meeting_ab.py`, `modeling.py` and `evaluation.py`; any later edit to those files invalidates this plan rather than silently changing it. Every approval flag is false, the meaningful gain is null and the evaluation partition is previously exposed.

## State

- Implemented and synthetically tested.
- Not fitted on real data. The alignment decision states that no fit runs before that decision is merged.
- Not independently validated and not published.

## Run, once authorized

Use a new output directory. Inputs are the same verified v7 artifacts as the first exploratory run.

```sh
.venv/bin/python -m whistle_research.exploratory --plan research/exploratory_meeting_ab_2026_11_09/specification.json --features output/v2/features-v7-reviewed-2026-11-02 --inventory output/v2/source-inventory-independent-2026-11-02/inventory.json --reconciliation output/v2/reconciliation-v7-reviewed-2026-11-02/report.json --source-manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --schedule research/rewrite_completion_2026_11_02/schedule_expected.json --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2021_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2022_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2023_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_2024_games.csv --metadata research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --output output/v2/exploratory-meeting-ab-2026-11-09/analysis
```

Actual results stay in ignored local output. A later commit records an execution receipt with artifact hashes and no empirical model values.
