# Audit footage and parser investigation

Checked 2026-11-02. This is development evidence, not an independent reconstruction audit or a new scientific result.

## Footage result

All 14 pilot games have identified official game pages, and all 14 displayed a League Pass activation prompt in the live browser. Two direct archived-video candidates also displayed a League Pass unlock screen. **No full-game replay was obtained or verified.** This establishes an access problem in the session used; it does not establish that footage is unavailable elsewhere or guarantee that buying access will unlock every historical stream.

One public official clip did play: [MIA at NYK, February 2, 2023, Q4 1:22 goaltending review](https://official.nba.com/archive/goaltending-basket-interference-heat-knicks/). The player advanced and basketball footage was visually observed. This is useful for a selected-event check, not complete-game coverage. No media was downloaded.

NBA's [replay help page](https://support.watch.nba.com/hc/en-us/articles/360011802673-Full-Game-Replays-and-Condensed-Game-Availability) describes active League Pass access through game details. A help article, page title, replay label or highlights listing is not proof of playable full-game coverage. Highlight videos omit the ordinary possessions needed by the audit.

| Game ID | Date | Matchup | Pilot stratum | Official route | Live browser result |
| --- | --- | --- | --- | --- | --- |
| 0022000181 | 2021-01-15 | NYK @ CLE | enriched | [NBA game](https://www.nba.com/game/nyk-vs-cle-0022000181) | Activation prompt |
| 0022000254 | 2021-01-24 | ATL @ MIL | enriched | [NBA game](https://www.nba.com/game/atl-vs-mil-0022000254) | Activation prompt |
| 0022000367 | 2021-02-08 | HOU @ CHA | random | [NBA game](https://www.nba.com/game/hou-vs-cha-0022000367) | Activation prompt |
| 0022000544 | 2021-03-03 | ATL @ ORL | random | [NBA game](https://www.nba.com/game/atl-vs-orl-0022000544) | Activation prompt |
| 0022000925 | 2021-04-26 | MEM @ DEN | enriched | [NBA game](https://www.nba.com/game/mem-vs-den-0022000925) | Activation prompt |
| 0022000997 | 2021-05-06 | WAS @ TOR | random | [NBA game](https://www.nba.com/game/was-vs-tor-0022000997) | Activation prompt |
| 0022100226 | 2021-11-18 | LAC @ MEM | random | [NBA game](https://www.nba.com/game/lac-vs-mem-0022100226) | Activation prompt |
| 0022200780 | 2023-02-02 | MIA @ NYK | random | [NBA game](https://www.nba.com/game/mia-vs-nyk-0022200780) | Activation prompt |
| 0022201087 | 2023-03-22 | PHI @ CHI | random | [NBA game](https://www.nba.com/game/phi-vs-chi-0022201087) | Activation prompt |
| 0022301101 | 2024-04-02 | LAC @ SAC | random | [NBA game](https://www.nba.com/game/lac-vs-sac-0022301101) | Activation prompt |
| 0022301177 | 2024-04-12 | LAL @ MEM | enriched | [NBA game](https://www.nba.com/game/lal-vs-mem-0022301177) | Activation prompt |
| 0022400393 | 2024-12-23 | BOS @ ORL | random | [NBA game](https://www.nba.com/game/bos-vs-orl-0022400393) | Activation prompt |
| 0022400481 | 2025-01-04 | UTA @ MIA | random | [NBA game](https://www.nba.com/game/uta-vs-mia-0022400481) | Activation prompt |
| 0022400553 | 2025-01-13 | MIA @ LAC | random | [NBA game](https://www.nba.com/game/mia-vs-lac-0022400553) | Activation prompt |

The ten random games and four enriched nominations are unchanged from the earlier preparatory pilot. Film availability was not used to replace sampled games. The sampling frame is source-observed; independent schedule completeness remains unverified.

## Evidence files

- `early_games.json` and `recent_games.json`: exact-game search queries, official sources, observed evidence and discovery limitations for seven games each. The early file contains metadata plus a `games` array; the recent file is a seven-game array.
- `browser_observations.json`: all 14 live game-page observations, two archived-player access checks and the one successfully played event clip. Discovery and playback are distinct fields.
- `parser_triage.md` and `parser_triage.json`: source-verified breakdown of candidate-v1 flags, exact source references and representative event neighborhoods. Those counts describe the pre-fix parser, not a fresh independently validated dataset.

## Candidate-v2 correction and full rerun

The triage demonstrated a duplicate boundary: a made shot and its same-clock defensive-goaltending companion were split into two groups. Candidate v2 pairs exactly one corroborated companion, preserving the violation audit flag and all source rows. Unknown/mismatched cases remain unresolved. See [the possession contract](../../docs/POSSESSION_CONTRACT.md).

Both versions used the same verified sources, metadata and 6,084 game IDs:

| Diagnostic | Candidate v1 | Candidate v2 |
| --- | ---: | ---: |
| Reconstructed games | 5,999 | 5,999 |
| Quarantined games | 85 | 85 |
| Candidate possession groups | 1,196,161 | 1,193,332 |
| Unexplained-transfer flags | 2,780 | 227 |
| Violation audit flags | 10,347 | 10,347 |
| WMI withheld among reconstructions | 5,029 | 5,029 |
| Arithmetic candidate scores | 970 | 970 |
| Independently validated/model-eligible games | 0 | 0 |

Grouping changed in 2,219 games. Only group counts, their historical count differences, unexplained-transfer counts and uncertain-group counts changed in the per-game diagnostic records. The 2,553 removed transfer flags are a before/after implementation result, not a measured accuracy gain. The triage's 2,540 goaltending-adjacent flags describe a different quantity: immediate raw-label adjacency before the fix.

`reconciliation_v2_summary.json` records both report/parser hashes, verified source hashes, denominators and the exact delta. The full v2 report is gitignored at `output/v2/reconciliation-goaltending-2026-11-02/report.json`; reproduce it with the all-game command in [REPRODUCE_V2.md](../../docs/REPRODUCE_V2.md), using a fresh output directory and `--limit-per-source 0`.

A fresh v2-bound pilot retains the same 14 selected games. Its compact record is `audit_pilot_v2_summary.json`; its deliberately empty reviews and unlocked configuration are `audit_reviews.empty.json` and `audit_config.draft.json`. `audit_gate_v2.json` records the actual BLOCKED result with zero completed reviews. No v1 annotation was rebound to v2. The browser observations retain their original pilot provenance; their game URLs also apply to the unchanged v2 sample.

Local verification: `.venv/bin/python scripts/check.py` passed 219 tests, maintained lint, website unit checks and wheel build/isolated installation. The full log is `output/v2/footage-access-checks-2026-11-02.log`. These are implementation checks, not scientific validation.

## Remaining audit requirements

Obtain authorized full-game access for the fixed sample and verify all regulation/overtime coverage. If an account is used later, verify the specific streams before assuming archive entitlement; no account purchase or subscription was made here. Record viewing references and completeness separately from a download permission.

Two independent reviewers must then produce their own full-game annotations under frozen definitions and pre-review tolerances. Disagreements require adjudication. No review records were invented, and the audit gate stays BLOCKED. Parser changes require a new parser-bound plan and fresh evidence; the old empty pilot and historical reports remain preserved.

The source and parser work can continue while footage and reviewers are unresolved. It cannot substitute for the independent audit or authorize confirmatory model evaluation.
