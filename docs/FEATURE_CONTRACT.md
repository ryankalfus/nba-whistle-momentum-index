# Recorded before-event feature contract

Original date: 2026-11-02. Updated: 2026-11-08. Version: `before_event_v1` (implementation unchanged). Status: provisional adapter, no independently eligible observations. The separately authorized [exploratory route](EXPLORATORY_ANALYSIS.md) does not promote these rows.

`whistle_research.features.build_rows(result, metadata)` returns exactly one row per reconstructed group, including every unknown target. Metadata requires a canonical matching game ID, ISO date, season and explicit regular-season/playoff type. The exporter binds dates to `schedule_expected.json`, including its 30 documented corrections; historical dates are never substituted. The date is a chronology key, not a model predictor.

| Field | Source and meaning |
| --- | --- |
| `game_id`, `date`, `season`, `game_type` | Explicit game identity and bound schedule metadata |
| `possession_number` | Canonical group index; chronology identifier |
| `period`, `clock` | `BeforeState.period` and recorded reference clock |
| `score_margin` | Absolute difference between before-state home and away scores |
| `score_difference` | Before-state defense score minus offense score; negative means the defense trails |
| `defense_team_id`, `offense_team_id`, `home_defense` | Explicit canonical group teams and home-defense indicator |
| `defense_counted_fouls` | Before-state counted defensive research fouls; not official penalty/bonus status |
| `previous_foul_1`, `previous_foul_2` | Last and second-last before-state global group indicators, respectively |
| `start_type` | `BeforeState.reference_kind` |
| `outcome` | Separate current group `foul_indicator`; 0, 1 or null |

Both score fields remain null if either before-state score is missing. Missing counts and unknown historical outcomes remain null. A nonexistent previous group is represented as null rather than fabricated history. Changing the current outcome, ending or future suffix cannot enter an earlier row's before-state feature values. No duration, terminal score, future foul, next-window outcome, final WMI, eventual overtime duration, penalty/bonus claim or other end-state predictor is exported.

Offense identity and boundaries come from retrospective source reconstruction. The reference clock is recorded feed state, including the parser's explicitly flagged source correction, not independently verified live-state timing. This adapter does not establish that group identity or features were observable at a live prediction opportunity.

## Streaming export and provenance

The CLI verifies the source manifest and snapshots exact archive bytes before parsing. It reuses the existing streaming archive reader and current canonical reconstruction, holding one game's events/rows in memory. Every expected schedule game appears in the dataset manifest: reconstructed, quarantined, missing, or explicitly not selected in a pilot. Unknown outcomes are retained; quarantined games have no invented groups. Source iteration failures retain any emitted rows as provisional and mark every affected game unresolved. `ok` reports source verification and observed/expected accounting, not scientific acceptance.

`rows.jsonl` contains only the row schema above. Aligned `row_provenance.jsonl` records game/group IDs, exact source CSV rows and action references, before-state reference action, group completeness and audit flags. Manifest game entries retain source/parser hashes, schedule date/season/type, original reconstruction issues and unassigned action numbers. Source bytes and parser/feature hashes make the rows reproducible without putting future outcomes or audit flags into model columns.

`rows_sha256` hashes the canonical JSON **list** of all rows in exact export order: sorted object keys, compact separators, no NaN, UTF-8, opening/closing brackets and commas. This is identical to `modeling.row_digest(rows)` without retaining the full list in memory. `rows_file_sha256` separately binds JSONL file bytes; the provenance file has its own byte hash. `frame` uses the audit module's sorted `SOURCE_KEYS` records and `frame_sha256` hashes that exact list. `source_map` records verified archive digests. Schedule and historical metadata bytes are separately bound. Correction records must match game/team/original-date/corrected-date bindings; this exporter does not reauthenticate the schedule acquisition's external attestations.

Every game entry has `eligible=false`. `complete` records full-game/period markers and complete groups, while `critical_unresolved` records blocking parser/control/outcome gaps. These fields have separate meanings. The manifest has `status=PROVISIONAL_AUDIT_BLOCKED`, `eligible_games=0` and `plan_sha256=null`: an export is not an audit plan or passing review. Strict `modeling.fit_real` and promotion must still refuse this dataset. There is no switch on those APIs, synthetic audit evidence or filtering of the original target stream. The separate exploratory loader may select whole games under its explicit retrospective quality policy, retaining the full exclusion ledger and original histories; selection is not scientific eligibility.

Existing output directories are refused. A small diagnostic defaults to the first three games per archive; `--limit-per-source 0` exports all observed games. New runs use new output directories. Source/feature/parser changes during export are reported as failures.

## Reproduction

Run from repository root with the project environment. Use a new output path when repeating:

```sh
.venv/bin/python -m whistle_research.features --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv research/hypotheses_2026_09_12/cdnnba_2021_games.csv research/hypotheses_2026_09_12/cdnnba_2022_games.csv research/hypotheses_2026_09_12/cdnnba_2023_games.csv research/hypotheses_2026_09_12/cdnnba_2024_games.csv research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --schedule research/rewrite_completion_2026_11_02/schedule_expected.json --output output/v2/features-candidate-v5-2026-11-02 --limit-per-source 0
```

Focused checks:

```sh
.venv/bin/python -m pytest tests/v2/test_features.py -q
```

```sh
.venv/bin/ruff check src/whistle_research/features.py tests/v2/test_features.py
```

The dated `research/rewrite_completion_2026_11_02/feature_summary.json` records actual pilot/all-game results, hashes and remaining blockers. Independent film validation, verified real-time feature availability, frozen model/evaluation choices and genuinely unused outcomes remain external release prerequisites.

## Observed export (2026-11-02)

The three-games-per-source pilot produced 3,655 rows, including 10 unknown outcomes, from 18 reconstructed games; the other 6,066 schedule games are explicitly `not_selected`. The all-game run accounts for all 6,084 games: 6,000 provisional reconstructions and 84 quarantines. It exports 1,193,032 rows, including all 2,221 unknown outcomes. The ledger records 5,972 marker-complete games and 1,859 games with critical unresolved evidence; these counts describe different properties. Every game remains ineligible.

The full stream was re-read to verify every row/provenance ID alignment, sequential group number, action/CSV reference length, canonical row-list hash and missing/outcome count. Every per-game row count matches the saved candidate-v5 reconciliation, including zero rows for the same 84 quarantines. The feature/parser hashes and JSONL/provenance file hashes match the final manifest. All 30 schedule date corrections remain bound. The actual pilot was passed to the real model API with only its dataset manifest; it returned `BLOCKED` before fitting because independent audit evidence was absent. This refusal is intentional and supplies no synthetic audit attestations.

Final feature implementation SHA256: `8008b45ca51aebefda0dabd6522eb9373dc7b4f2401f8bfa7eb55370809fccc4`. Full row-list SHA256: `d0a9be0334a83cbf4d995f30d03d9aff5bf0449a90923d15257bcfb453253460`. Focused tests: **21 passed**. Ruff: **All checks passed**. Neither result establishes scientific validity or live availability.
