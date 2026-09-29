# All-hypothesis research run

Start with **full_hypothesis_report.md**. It gives a question, executed method,
every estimate and interval, interpretation, and limitations for H1–H17 plus H18
(the supplied roadmap contains 18 hypotheses).

This package is separate from the public WMI product and the previous expansion
report. It does not deploy anything or modify production game outputs.

## Reproduce

From the project root, using the versions in this folder's `requirements.txt`:

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python run_all_wmi_hypotheses.py
pytest -q tests/test_all_wmi_hypotheses.py
```

The single runner handles downloads, parsing, hypothesis tests, audits and report
generation. `--fetch-only`, `--prepare-only` and `--report-only` are also available.
It reuses cached research tables after checking schedule coverage; to rebuild
from raw sources in a clean environment, start with an empty research cache.
The raw archives are pinned to Git commits and SHA256 hashes are recorded.

## Files

- `all_hypothesis_results.csv`: all results, including sample sizes, 95% intervals,
  raw p-values and jointly corrected Benjamini–Hochberg q-values.
- `analysis_details.json`: model formulas, cohort choices and inference limits.
- `run_audit.json`: coverage, scoring, key uniqueness and source/code hashes.
- `source_lock.json`, `source_manifest.json`: exact remote sources and hashes.
- `analysis_failures.json`: errors, if any; an empty array means no failed blocks.
- `H*_*.csv`: coefficients, event samples, matched challenge windows, crew pairs,
  win predictions and supporting diagnostics.
- `game_components_window_*.csv`: game-level denominators and decomposition.
- `cdnnba*_games.csv`: processed game inventory for each season/type.
- `cache/`: ignored downloaded archives and derived event/possession Parquet files.

## Interpretation

An executed test is not proof that its hypothesis is true or causally identified.
H11 cannot establish optimal coaching policy; H9 lacks a validated restricted-crowd
classification; H10/H12 lack player tracking and noncall judgments; H15 has sparse
exact-crew recurrence. The report explicitly separates these limitations from
the analyses that were successfully executed.
