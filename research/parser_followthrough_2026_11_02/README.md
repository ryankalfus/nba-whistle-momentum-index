# Parser and public-footage follow-through — 2026-11-02

PRs #6 and #7 were merged at the user's request. This packet records the subsequent candidate-v7 parser work and public-only access search. No game is independently validated or eligible for confirmatory modeling.

| Evidence | Files |
| --- | --- |
| Reviewed-head merge receipts | `merge_receipt.json` |
| Raw semantic neighborhoods and adversarial corrections | `semantic_changes.json`, `semantic_changes.md` |
| Every previously quarantined clock rise and source-note inventory | `clock_triage.py`, `clock_triage.json`, `clock_triage.md` |
| Source-note state leakage and hidden genuine clock rises | `memo_clock_assessment.json`, `memo_clock_assessment.md` |
| All 59 corrected references in the final exported streams | `memo_export_verification.json` |
| Remaining transfer/free-throw/label evidence | `residual_triage.py`, `residual_triage.json`, `residual_triage.md` |
| Additional public catalog search and exclusions | `public_search.json`, `public_search.md` |
| Subsequent live player observations | `browser_observations.json` |
| Cumulative fixed-pilot access record | `public_replays.json` |
| Preserved run comparisons and current pipeline bindings | `run_comparison.json`, `pipeline_summary.json` |
| Generated report and manuscript copies | `development_report.md`, `draft_paper.md` |
| Automated, independent code-review and browser checks | `verification.json` |

Final v7 accounting: **6,036 reconstructed / 48 quarantined** of 6,084 games; **1,199,536 rows / 2,947 unknown targets**; 6,033 marker-complete games; 2,253 critical-unresolved games; **zero eligible games**. There are 411 unresolved transfer and 166 violation flags. More explicit uncertainty can increase these counts; diagnostic success is not scientific acceptance.

The source-note assessment is bound to the frozen v6 code it diagnosed. Its filtered shadow runs are diagnostic experiments, not shipped reconstructions: the v7 implementation preserves original source indexes and every raw event. In 35 of the 37 memo-rise cases, comparing the actual non-note sequence removes the apparent regression. Two still have real clock rises hidden behind notes and must remain quarantined. Notes retain blocking uncertainty rather than silently asserting a foul target or team-foul count.

The initial v6 full run exposed an overbroad dead-ball interpretation and duplicate loss after a recovered jump. The reviewed corrections retain ordinary final-miss rebound control and require exact lost-jumper attribution for a single held-ball loss companion. All intermediate reports remain in their separate output directories. Source-backed implementation tests and code review do not establish independent basketball truth.

The footage search added six Tencent alternatives after 64 indexed queries. Live checks subsequently found the same regional copyright barrier on all six. The primary ATL–MIL catalog lists four Mandarin quarters marked VIP, whereas its third-party listing exposed only Q1/Q2. The MIA–NYK catalog lists 2:00:53; it did not play. These observations are kept distinct in the cumulative record. Filemoon now reports an unavailable source. The search-only artifact preserves its earlier knowledge; `browser_observations.json` records the later checks.

The fixed fourteen games and two previous playback observations are unchanged. Thirteen exact catalog leads are not thirteen accessible full games. Continuous coverage, uploader authorization and two independent reviews remain unverified. No accounts, subscriptions, VPN, challenge bypass, media download or redistribution were used. Negative searches document the routes checked; they do not prove a recording does not exist.

Reproduce the full development workflow using `../../docs/PIPELINE.md`, always in a new output directory. Raw source snapshots and full feature/provenance streams remain in ignored cache/output directories with recorded hashes. The scientific audit, frozen tolerances, model protocol and genuinely unused evaluation cohort remain outstanding; no empirical results are manufactured to close those gates.
