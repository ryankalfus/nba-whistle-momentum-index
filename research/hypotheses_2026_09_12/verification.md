# Verification record — September 12, 2026

- Full statistical runner completed with exit code 0 after the four clock-anomaly
  games were quarantined. No hypothesis block failed.
- All H1–H17 and supplemental H18 have results: 77 reported estimates, including
  55 inferential comparisons with global Benjamini–Hochberg correction.
- Source inventory: 6,084 games. Retained: 6,080 games / 1,225,902 possession groups.
  The primary sample retains all 1,230 regular-season games from 2024–25 and all
  84 playoff games. Quarantined source records remain available.
- All 11 checks in `run_audit.json` passed, including complete source schedules,
  unique possession keys, internal score reconciliation, and no remaining
  negative scoring deltas or possession durations.
- All 10 downloaded source files match their recorded byte counts and SHA256s.
- `pytest -q tests/test_all_wmi_hypotheses.py`: 18 passed.
- `pytest -q`: 38 passed.
- Targeted Ruff checks passed.
- Every reported result appears in the full report, all 18 hypothesis headings
  are present, and the final BH q-values were independently recomputed and matched.

The final report-only pass clarified prior coverage, units and the crew-cluster
label without changing fitted results. `report_provenance.json` preserves both
the analysis-runner hash and report-generator hash.

These checks do not validate causal identification, exact real-time feed state,
player-tracking proxies, or every public-feed ownership classification. Those
limitations are stated in the full report.
