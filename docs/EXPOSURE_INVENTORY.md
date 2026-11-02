# Evaluation exposure inventory

Date: 2026-11-02. Status: development evidence; no unused evaluation cohort verified.

The existing analyzed seasons cannot be relabeled as untouched confirmatory data. All five 2020–21 through 2024–25 regular seasons and the 2024–25 playoffs have development exposure. The stored 2025–26 snapshot also has exposure, even though a later possession-level acquisition failed. Reconstructing these sources with a new parser does not undo prior outcome exposure.

| Cohort | Recorded exposure | Evaluation status |
| --- | --- | --- |
| 2020–21 regular season | Included in the hypothesis inventory and earlier-season model training | Development |
| 2021–22 regular season | Included in the hypothesis inventory and earlier-season model training | Development |
| 2022–23 regular season | Training in the hypothesis study; evaluated in the matched validation comparison | Development |
| 2023–24 regular season | Regularization selection, matched validation and exploratory sequence forecasts | Development |
| 2024–25 regular season | Expansion study, hypothesis evaluation, matched validation and sequence forecasts | Development; retrospective holdout is not untouched prospective evidence |
| 2024–25 playoffs | All 84 games analyzed in the hypothesis and matched validation reports | Development |
| 2025–26 stored regular-season snapshot | 1,034 games in expansion summary; game-level distribution artifacts recorded on 2026-06-20 | Development; partial snapshot, not a verified complete season |

## Source evidence

- [Hypothesis report](../research/hypotheses_2026_09_12/full_hypothesis_report.md), lines 11–20: inventory of five regular seasons and 84 playoff games. Line 11 also records stored 2019–20 and selected attendance-linked WMI exposure; this inventory does not certify those additional rows as unused.
- The same report, lines 161–176: executed playoff comparisons. Lines 327–334: training on 2020–21 through 2022–23, regularization selection on 2023–24 and evaluation on 2024–25.
- [Validation source manifest](../research/validation_2026_09_12/dataset_manifest.json), lines 43–76: possession artifacts, game counts and hashes for those six cohorts. This establishes artifact identity, not absence of exposure.
- [Validation report](../research/validation_2026_09_12/report.md), lines 17–28: matched predictions for 2022–23, 2023–24, 2024–25 and the playoffs; explicitly calls 2024–25 a retrospective holdout. Lines 54–65: further exploratory sequence forecasts on 2023–24 and 2024–25.
- [Expansion report](../wmi_expansion_full_report.md), lines 1–42: exploratory 2024–25 study and stored comparison snapshots. Lines 102–109: 2025–26 snapshot of 1,034 games. The acquisition failure in this report does not erase existing game-level analysis.
- [Project log](../PROJECT/nba-whistle-project-log.md), lines 11–12: 2025–26 acquisition activity; line 117: 2026-06-20 distribution analysis using existing March 2026 snapshots.

## What remains unresolved

A bounded prior search found no 2026–27 analysis. That absence is not proof that the cohort is unseen; no 2026–27 holdout is designated here. This is a source-backed exposure inventory, not a claim to have exhaustively reconstructed every earlier analysis or private inspection.

The [current protocol](RESEARCH_PROTOCOL.md), lines 3, 41, 45 and 55–60, remains unlocked and requires a genuinely unused cohort, a meaningful-gain threshold and a frozen evaluation procedure. No freeze date, threshold or unused cohort is supplied by this inventory. A prospective cohort must begin after the actual protocol freeze, with its date boundary and prior exposure independently documented. Independent reconstruction audit requirements remain separate and unresolved.

The machine-readable companion is `research/rewrite_completion_2026_11_02/exposure_inventory.json`. The inventory records prior exposure only; it does not endorse the older scientific conclusions.
