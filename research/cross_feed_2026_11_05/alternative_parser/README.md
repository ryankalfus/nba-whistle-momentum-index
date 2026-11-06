# Versioned alternative-parser pilot — 2026-11-05

This bounded development comparison runs the published **pbpstats 1.3.11** mobile-feed possession loader on all fourteen games already in the fixed pilot. It uses no footage, evaluation outcomes, annotations, eligibility changes or event overrides. The independent scientific audit remains **BLOCKED**.

13 of the fixed 14 games parsed offline; no games were substituted. Game `0022301177` is absent from the pinned mobile archive and is explicitly failed. Canonical quarantines remain unavailable, never zero. The first three-game 2024–25 run was extended to this full fixed pilot after verifying older archives from the same immutable upstream commit.

| Game | Date | pbpstats / v7 | Shared | v7-only | pbp-only | Uncomparable v7 / pbp |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0022000181 | 2021-01-15 | 189 / unavailable | — | — | — | — |
| 0022000254 | 2021-01-24 | 197 / 196 | 123 | 59 | 71 | 14 / 3 |
| 0022000367 | 2021-02-08 | 196 / 194 | 107 | 74 | 87 | 13 / 2 |
| 0022000544 | 2021-03-03 | 197 / 194 | 101 | 73 | 96 | 20 / 0 |
| 0022000925 | 2021-04-26 | 208 / 210 | 112 | 85 | 92 | 13 / 4 |
| 0022000997 | 2021-05-06 | 221 / 223 | 125 | 76 | 94 | 22 / 2 |
| 0022100226 | 2021-11-18 | 193 / 191 | 112 | 63 | 80 | 16 / 1 |
| 0022200780 | 2023-02-02 | 189 / 188 | 105 | 74 | 84 | 9 / 0 |
| 0022201087 | 2023-03-22 | 190 / 188 | 110 | 62 | 80 | 16 / 0 |
| 0022301101 | 2024-04-02 | 188 / 185 | 102 | 73 | 86 | 10 / 0 |
| 0022301177 | 2024-04-12 | failed / unavailable | — | — | — | — |
| 0022400393 | 2024-12-23 | 209 / 208 | 123 | 68 | 86 | 17 / 0 |
| 0022400481 | 2025-01-04 | 207 / 204 | 119 | 70 | 88 | 15 / 0 |
| 0022400553 | 2025-01-13 | 202 / 199 | 106 | 81 | 96 | 12 / 0 |

These are **last-assigned-event agreement** counts, not counts of basketball-control errors. Administrative attachments and rebound conventions can change literal endpoints. Unique IDs are corroborated by order/timestamp plus numerical clock/period. Uncomparable endpoints are kept separate. This is a development diagnostic, not a population error estimate.

One concrete discrepancy or unilateral result per game:

- `0022000181`: v7 is quarantined; pbpstats alone emits 189 groups, first ending at event `9` (11:32, period 1). No paired discrepancy is calculated.
- `0022000254`: v7 last-assigned event `8` ([ATL] Rondo 3pt Shot: Missed); the pbpstats group containing it ends at `9` (11:22, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022000367`: v7 last-assigned event `9` ([CHA] Hayward 3pt Shot: Missed); the pbpstats group containing it ends at `10` (11:10, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022000544`: v7 last-assigned event `9` ([ATL] Collins 3pt Shot: Missed); the pbpstats group containing it ends at `10` (11:25, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022000925`: v7 last-assigned event `13` ([MEM] Morant 3pt Shot: Missed); the pbpstats group containing it ends at `14` (11:15, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022000997`: v7 last-assigned event `19` ([TOR] Birch Jump Shot: Missed); the pbpstats group containing it ends at `20` (10:40, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022100226`: v7 last-assigned event `9` ([LAC] Jackson Pullup Jump shot: Missed); the pbpstats group containing it ends at `10` (11:19, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022200780`: v7 last-assigned event `10` ([MIA] Herro Pullup Jump shot: Missed); the pbpstats group containing it ends at `11` (10:51, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022201087`: v7 last-assigned event `18` ([CHI] Vucevic Driving Layup Shot: Missed); the pbpstats group containing it ends at `19` (11:05, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022301101`: v7 last-assigned event `9` ([SAC] Murray Fadeaway Jump Shot: Missed); the pbpstats group containing it ends at `10` (11:24, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022301177`: no mobile input rows in the verified season archive; explicit failure `Missing pilot game in pinned archive`. v7 is also quarantined; neither count nor a paired discrepancy is invented.
- `0022400393`: v7 last-assigned event `7` ([BOS] Holiday Driving Layup Shot: Missed); the pbpstats group containing it ends at `8` (11:34, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022400481`: v7 last-assigned event `9` ([MIA] Adebayo Pullup Jump shot: Missed); the pbpstats group containing it ends at `10` (11:29, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.
- `0022400553`: v7 last-assigned event `11` ([MIA] Highsmith 3pt Shot: Missed); the pbpstats group containing it ends at `12` (11:06, period 1). This demonstrates an endpoint disagreement, not an adjudicated error.

## Inputs and package identity

- Fixed sample: `research/parser_followthrough_2026_11_02/public_replays.json`, checked for exact membership against the genuine v7 `audit_plan.json`. Every planned season/source is checked against the canonical frame.
- Additional immutable mobile sources: `research/cross_feed_2026_11_05/pilot_mobile_sources.json`, acquired by the parent workflow and independently size/SHA256-verified by this runner. Consumed source entries and hashes appear in `result.json`; the historical source manifest is unchanged.
- Mobile archive: `research/hypotheses_2026_09_12/cache/datanba_2024.tar.xz`, member `datanba_2024.csv`, SHA256 `79f698e66439e3e43bdb6299eb4da7897b5e007985193350da280c8a4ec76e60`.
- [Immutable source archive](https://raw.githubusercontent.com/shufinskiy/nba_data/e829d4678be1e075f99e5d41a1c5f97089be446b/datasets/datanba_2024.tar.xz), as pinned in the historical source manifest; no new feed is fetched.
- Candidate: `output/v2/features-v7-reviewed-2026-11-02/row_provenance.jsonl` and its `manifest.json`. Both consumed streams are verified against the typed feature roles in `output/v2/development-pipeline-v7-2026-11-02/report.json`, including exact sizes/hashes. The feature manifest also must bind the provenance hash. The audit plan and historical source manifest are verified against their typed report roles. The runner parses verified snapshots rather than reopening mutable source files. Fingerprints are retained from the actual consumed bytes or authenticated snapshots, never reconstructed by reopening live paths at report time. Project source bytes are captured before helper import/use; the runner rejects subsequent input/source drift and repeats exact package verification before writing evidence. Their retained hashes and the sample/source-manifest hashes are recorded in the result. Candidate groups are not recomputed or made eligible.
- [PyPI release metadata](https://pypi.org/pypi/pbpstats/1.3.11/json) identifies the [published wheel](https://files.pythonhosted.org/packages/68/81/2c9ae466029bfa26bf2112c9c2ff5156334f49a2575a457c1115d2b74bdd/pbpstats-1.3.11-py3-none-any.whl), SHA256 `bf25d508e0956f8b5c5055e85b2d35d9259677e2b62410ce1121eb4d0f6683a0`. The package is not added to project dependencies. The inspected wheel requires only requests, already present in the project environment; the runtime version is recorded.
- Exact executable source is the verified wheel, not mutable GitHub main. `result.json` includes SHA256 for every package Python source, and the runner verifies all unpacked Python files against the wheel before import. The ignored isolated location is `output/alternative-parser-pbpstats-1.3.11/`.

## Adapter and definitions

The archived schemas contain all mobile-event fields consumed by `DataEnhancedPbpItem`, including `evt`, `cl`, `de`, `opt1`, `opt2`, `mtype`, `etype`, player/team IDs and `oftid`. `pilot.py` groups contiguous CSV records into `g.pd[].{p,pla}` using the existing `PERIOD`; it preserves archive row order and every field, including empty values. Only `etype` is restored from its CSV decimal string to an exactly round-trippable integer because the factory dispatches on integer event type. `GAME_ID` is zero-padded only for game selection/loader identity. No event fact, missing ID, starter, clock, score, or offensive-control field is filled or corrected. The parser itself performs its published event-class conversions and period-starter inference.

The published `DataEnhancedPbpItem.is_possession_ending_event` ends a group when its next event has another nonzero `oftid`, except start-period transitions, and at a terminal event. `NbaPossessionLoader` groups events at those flags. Period starters are inferred by the unmodified loader. Its possible HTTP fallback is blocked; such a fallback would be recorded as a failed game with full exception/traceback, not patched with invented starters. `file_directory=None` disables starter and possession-change override files. HTTP requests and socket connections are blocked during parsing. Any fallback or parsing failure appears in the authoritative per-game results, without suppressing its exception. Absent boxscore/lineup metadata is never invented. No package code is patched; file overrides are disabled strictly rather than accepted as hidden corrections. The runner checks raw dictionaries remain unchanged, input event IDs are unique and the entire flattened assigned event-ID sequence exactly equals the original sequence. Dropped, duplicated, injected or reordered events fail closed.

`alternative_boundaries` records each group's period, period-local number, clocks, first/last raw event number and full ordered event-number list. `canonical_boundaries` records candidate group number, reference/last action numbers, completion and flags directly from its provenance. Counts include all groups each implementation emits, including end-of-period/dead-ball bookkeeping; no minimum-duration or other harmonization filter is applied. Boundary comparisons require an event ID unique in both feeds, equal nonempty order number or wall timestamp, and equal known period and numerical clock. Other IDs remain explicitly uncomparable. The runner uses the source-hashed `feed_compare.compare_pair` helper; it records shared, canonical-only, alternative-only and each side’s uncomparable boundary counts, with all discrepancy IDs and exact paired identity/description field excerpts (full raw events stay in their immutable archives). It does not align possession numbers or equate a conventional boundary discrepancy with an error. Group counts and boundaries may differ because both the implementation and feed differ: this is not an isolated same-feed parser-effect estimate. Agreement would still not establish truth.

Primary source orientation: [pbpstats quickstart](https://github.com/dblackrun/pbpstats/blob/main/docs/quickstart.rst), [mobile enhanced loader](https://github.com/dblackrun/pbpstats/blob/main/pbpstats/data_loader/data_nba/enhanced_pbp/loader.py), [mobile event boundary implementation](https://github.com/dblackrun/pbpstats/blob/main/pbpstats/resources/enhanced_pbp/data_nba/enhanced_pbp_item.py). For exact versioned behavior, inspect the wheel source hashes recorded with the result.

## Reproduction

Retrieve the exact published wheel above into an ignored isolated package directory, verify its SHA256 before unpacking it into that directory's `unpacked/` subfolder, then run with the project environment. The runner never downloads anything and refuses existing result paths. Use a new ignored result location for repeat runs:

```sh
.venv/bin/python research/cross_feed_2026_11_05/alternative_parser/pilot.py --package-dir output/alternative-parser-pbpstats-1.3.11 --output output/alternative-parser-repeat/result.json
```

```sh
.venv/bin/python -m pytest tests/v2/test_alternative_parser_pilot.py -q
```

```sh
.venv/bin/ruff check research/cross_feed_2026_11_05/alternative_parser/pilot.py tests/v2/test_alternative_parser_pilot.py
```

Checks cover lossless wrapper invariants, exact event assignment, corroborated boundary identity, fail-closed wheel/network verification and simulated in-run edits to both input and source files. The mutation tests confirm consumed fingerprints stay fixed and changed live paths prevent evidence publication. Add `--mobile-cache PATH` to locate the four added mobile archives elsewhere; all legacy pinned archives still use the historical cache. The ledger can be passed to the existing acquisition tooling; this runner itself does no fetching. They do not establish scientific validity. Validation: the authoritative offline run reports 14 selected, 13 parsed, 1 failed; seven focused tests pass and Ruff passes. No full suite, build or browser check was requested for this isolated evidence task.

2026-11-05 review correction: regenerated the actual fourteen-game packet at `output/alternative-parser-full14-consumed-binding/result.json` after correcting report-time fingerprint reopening. Scientific status and game selection are unchanged.
