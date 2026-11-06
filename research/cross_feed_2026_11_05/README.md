# Pinned cross-feed diagnostic — 2026-11-05

Status: **DIAGNOSTIC_AUDIT_BLOCKED; zero eligible games**. The field comparison reused two verified local archives. No model was fitted and no source or audit label was replaced.

This packet also contains a [separate possession-parser comparison](alternative_parser/README.md) for the original fourteen pilot games. Four additional mobile archives were acquired for that comparison from the same [upstream commit](https://github.com/shufinskiy/nba_data/commit/e829d4678be1e075f99e5d41a1c5f97089be446b). Their sizes, Git blob IDs and SHA256 hashes are in the [diagnostic source ledger](pilot_mobile_sources.json) and [acquisition receipt](pilot_acquisition.json). The ten-file historical release manifest remains unchanged. See [three disputed records in context](CASE_NOTES.md) and the [public footage follow-up](FOOTAGE.md).

The external comparator parsed thirteen games and explicitly failed the fourteenth because it is absent from the verified mobile archive; canonical quarantines stay unavailable. The corrected complete pilot reproduced byte-for-byte in a separate coordinating-process run. Its input fingerprints retain consumed bytes and reject in-run drift.

## Official footage access

After the user obtained League Pass, all fourteen fixed pilot games passed live full-length playback access checks in the in-app browser. [The dated observations](league_pass_access.json) retain exact official game URLs, feed labels, runtimes and positive playback times with readyState 4, paused false and no media error. Three games additionally decoded after midpoint seeks. Mobile and Kiswe feeds retain their observed names rather than being relabeled as a local television broadcast.

The earlier Lakers–Grizzlies attempt showed `DRM_FAILED_LICENSE_REQUEST` and browser-control timeouts. Closing the stalled NBA tab and reopening the exact game visibly restored full-feed playback; the other checks reused that player. A temporary desktop viewport exposed stream controls and was reset afterwards. The cause of the original failure is undetermined. Reproduction: sign into NBA.com, open the listed game, use the hero Play/Start from Beginning control; where necessary, use Condensed Games → Streams → Full Games and select the named broadcast. Recheck playback rather than counting the catalog or condensed clip alone as access.

This is subscription access, not a public copy or a continuous-coverage review. Full-coverage attestations and independent human reviews remain zero; no audit gate or eligibility changes. No credentials, cookies, tokens or stream URLs are included in the record. [NBA troubleshooting](https://support.watch.nba.com/hc/en-us/articles/115003452913-Troubleshooting-Streaming-Issues) recommends a fresh browser session or another browser for persistent issues; the successful recovery here does not prove future access.

The current full candidate-v7 feature manifest selects 431 critical-unresolved games from the pinned 2024–25 regular-season CDN cohort: 429 reconstructed games and two clock-regression quarantines. The corresponding reconciliation report agrees on source hashes, game membership, source-event counts, quarantine status and issue-code counts. The exact read bytes of the feature manifest, reconciliation report and source manifest must match SHA256 and byte sizes under their named artifact roles in the existing v7 development report. Its own hash is retained in the summary. Both evidence runs must bind to the current v7 parser bytes and declare `limit_per_source: 0`; partial, stale-parser, duplicated or cohort-mismatched evidence is rejected. The full CDN source game inventory must equal the declared cohort frame.

The adapter compares every CDN row in these selected games, links blocking issue action numbers and the explicit quarantined clock-regression action number, and retains original paired CSV dictionaries and member/row references in the ignored output. It does not reuse the historical challenge-tag analysis.

## Results

| Selected-game CDN row status | Rows |
| --- | ---: |
| Agreement on known clock, team, offense and period | 169,030 |
| Incomplete paired fields | 3,514 |
| Known-field difference | 30,425 |
| Unmatched mobile event ID | 41,119 |
| Unique ID without corroborated identity | 1 |
| Missing mobile game | 0 |
| Ambiguous ID | 0 |
| Total | 244,089 |

Of 634 distinct rows linked to critical issues or quarantine clocks, 625 agree and nine remain incomplete because offense ownership is unknown. No such row has a corroborated known-field difference. Issue codes overlap on a row; these row counts are not counts of independent defects.

Both quarantine-entering actions agree across feeds in the four paired fields:

| Game | Action | Period | Clock seconds | CDN CSV row | Mobile CSV row |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0022400326 | 585 | 3 | 187 | 183845 | 157760 |
| 0022400334 | 758 | 5 | 25.9 | 188653 | 161859 |

Their clock/period regression quarantines remain in force. Agreement at the flagged action does not independently validate the preceding sequence.

Across all selected-game rows, 30,419 pairs differ in offense, eight in clock and one in team; none differs in period. Categories can overlap. These are field discrepancies, **not confirmed source errors**. In particular, feed ownership conventions and before/after-event timing may differ; this adapter does not infer or correct their semantics.

## Matching and limits

- A row must have a unique `(canonical game ID, integer event/action ID)` in both feeds, plus exact nonempty order-number or timestamp agreement. Failure of either ID uniqueness or corroboration remains explicit. Conflicting corroboration fields remain visible in raw references; one agreeing field suffices.
- CDN ISO clocks and mobile `minutes:seconds` clocks normalize with exact decimal seconds. Zero or absent team/offense/period IDs stay unknown. Two unknown fields are not agreement. A difference can coexist with other unknown fields, retained in `unknown_fields`.
- All CDN rows from the selected games form the comparison axis. Mobile-only events are not enumerated, and no missing counterpart is fabricated. No matching by approximate clock, description or inferred basketball outcome occurs.
- Disk-backed SQLite indexes and verified spooled snapshots avoid holding season-sized event tables in RAM. Input archives are copied and SHA256-verified before parsing; raw archives are never changed. Failure leaves no successful summary.
- This is a targeted unresolved-case diagnostic, not a random audit, season error rate or independent ground truth. Both feeds may share upstream errors. Neither agreement nor disagreement authorizes source substitution, ownership correction, eligibility promotion or confirmatory evaluation.

## Reproduce

From the repository root, choose a new output directory; existing output directories are refused.

```sh
.venv/bin/python -m whistle_research.feed_compare --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --features output/v2/features-v7-reviewed-2026-11-02/manifest.json --report output/v2/reconciliation-v7-reviewed-2026-11-02/report.json --run-report output/v2/development-pipeline-v7-2026-11-02/report.json --output output/v2/cross-feed-v7-bound-2026-11-05
```

The actual run exited 0. `diagnostic_summary.json` is an exact copy of its `summary.json`; full raw pairs remain in `output/v2/cross-feed-v7-bound-2026-11-05/paired_rows.jsonl` (ignored). Copy the freshly generated summary when reproducing in a differently named output directory; paths are not part of the result hash.

```sh
.venv/bin/python -m pytest -q tests/v2/test_feed_compare.py
```

Result: 23 passed. Tests cover known differences, unknown ownership, exact clock normalization, uncorroborated identities, stale/partial/duplicate/cohort-mismatched evidence, archive hash mismatch, raw row provenance, missing games/IDs, duplicate IDs in either feed, quarantine tagging, explicit eligibility/status checks, exact typed development-report artifact bindings and refusal to overwrite outputs.

```sh
.venv/bin/ruff check src/whistle_research/feed_compare.py tests/v2/test_feed_compare.py
```

Result: all checks passed. The coordinating agent runs the project-wide check separately; these focused checks do not establish scientific validity.

Final coordinating verification: `.venv/bin/python scripts/check.py` exited 0 with 527 Python tests, both website suites, maintained lint and package build/isolated installation. The seven external-pilot tests include consumed-input/source mutation refusal. Independent Sol review found and verified the fix for post-consumption fingerprint drift. The separate complete pilot rerun is byte-identical to the saved result (`b1ce1994f8b4c14f55e19b5173eb8a8826fa4a579bc9f743a9c8f46a9e97d2d6`). No visible UI was changed in this PR.

## Hashes

The machine-readable summary retains the complete source entries and input/implementation fingerprints.

| Artifact | SHA256 |
| --- | --- |
| CDN archive | `35a82e6b29821adb22b8474dea8c51e08847d8e00690d1d5ffde7d000e0087d1` |
| Mobile archive | `79f698e66439e3e43bdb6299eb4da7897b5e007985193350da280c8a4ec76e60` |
| Feature manifest | `6b2868d4525b22a51fbc99f424bfc9d17748e75daf1c5c24eb9b3315568f73c6` |
| Reconciliation report | `ac24aacf33cd382f207ef182d94736221cf52580e7a31959f8f60ea7f8818555` |
| v7 parser | `9ee7d5e81b5a99f0b42bf94e617269104bcb90e47f796af02fa4d0bb256d991f` |
| Comparison implementation | `67f85c07477407b9eb2113973801556302398238a2ce02499d5a898c4b5a7a2f` |
| Paired rows JSONL | `f747ee29cf7861625410c7c847725ec98cefac270d844c155b7dbca47719d1ee` |

The development run report SHA256 is `31ed644257686112632bfa6a8235c9d00d0664bd0e8c6e90e14cca3f1ab8cbc8`. The saved diagnostic summary SHA256 is `e046214459406ea66349eb431059d661a003923f10a989112faf52dc536be4c3`.
