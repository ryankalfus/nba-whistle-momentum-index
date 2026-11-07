# Alternate footage delivery and temporal feasibility — 2026-11-07

Status: **Claude access and short-sequence delivery work; 0/303 full-game AI reviews completed.** No parser semantics, frozen human evidence, eligibility or scientific approval changed.

## Actual route tests

The owner suggested Claude, authorized full computer control for the research, and approved the macOS authentication prompt. Claude Desktop needed its own Screen Recording entry; the pre-existing lowercase `claude` entry did not grant Desktop access. The temporary change to that other entry was restored. Full control and the authorized Desktop permissions remain enabled. Claude obtained session access to the existing Codex player, displayed as ChatGPT with bundle `com.openai.codex`. No NBA credentials, cookies, browser profiles or signed media addresses were passed to Claude or the Sol agents.

The actual Claude consultation first failed with computer use disabled, then succeeded after setup. Its original visible response and screenshot proof stay in local ignored evidence; the private conversation address is not published. Claude saw ATL @ MEM (`0022000021`, 2020-12-26) at Q2 9:11 and controlled ordinary play/pause. Its initial free-play batches missed a free throw and several seconds of live play. Its later pause/resume test exercised only one boundary. Neither establishes gap-free coverage. Estimated frame cadence in Claude's prose is not an instrumented per-frame measurement.

Claude produced a normal downloadable ZIP, which was saved locally and reopened independently. [claude_export.json](claude_export.json) binds the archive/manifest and all 71 original crops: **70 distinct image hashes**, four batches of 8/20/22/21 images, and 75 verified checksum entries. One full-window screenshot containing the chat/sidebar was excluded from the delivered image packet and remains an explicit exclusion descriptor. Original images were not regenerated or enhanced. Per-frame capture timestamps and instrumented media positions were never recorded and remain null; filenames encode batch storage time, not frame capture time. No audio was captured. Export/build scripts from the ZIP were preserved as outside evidence and were not executed locally.

A separate attempt to acquire the native Codex app for a screen-recording test was denied by the computer-use tool. No native recording was made, and that denial does not diagnose video protection or prove other authorized recording methods impossible. Supported in-app browser captures continued to work. No complete video file has been obtained through the tested routes.

## Local temporal capture and actual paired review

Before each local run, a declaration saved the 20-second duration target, maximum 300 frames and a one-second metadata-gap engineering target. This was a local technical declaration, not external registration or a statistical accuracy threshold. Serial supported browser screenshots were bracketed by public media-metadata reads. Pixel/media synchronization remains unverified.

| Probe | Original images / distinct hashes | Wall run | Media-metadata span | Maximum adjacent midpoint gap | Maximum adjacent metadata bound | Metadata checks |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Initial obstructed | 56 / 56 | 20.174 s | 20.134677 s | 1.388710 s | 2.521063 s | Fail |
| Aligned follow-up | 82 / 82 | 20.049 s | 20.018453 s | 0.373971 s | 0.657812 s | Pass |

The bound is `next post media time - previous pre media time`; it is a bound on the recorded metadata, not an authenticated bound on depicted video time. The initial semantic play click scrolled the page to 278.5 pixels, exposing the player to website-header obstruction. Its 56 originals and post-capture quality note remain intact. The follow-up used the visible native play control without that scroll and checked zero scroll during capture. Controls still obscure the away score in its first two images; zero scroll does not certify readability. Both raw captures, declarations, images and journals remain under ignored `output/v2/full-footage-access-2026-11-07/`.

Two separate `gpt-6.1-sol` agents each opened **all 82** follow-up JPEGs using image-viewing tools. Their original submissions are preserved byte-for-byte in [submissions/A.json](submissions/A.json) and [submissions/B.json](submissions/B.json). Neither saw source events, candidate output, Claude's report or the other's labels before submission. Both received the same ordered, hash-bound packet. Distinct agents using the same model can share errors.

The [literal comparison](reviews_comparison.json) contains 164 frame observations and compares five fields per paired frame: period, normalized clock, away/home scores and apparent ball control. It reports **377 matches, 13 unknowns and 20 disagreements**. All disagreements are control labels; none is automatically cleared. Unknowns do not count as matches. Free-text action and sequence judgments remain in the original submissions. Reviewer A marks 19 frames uncertain and B marks 37; matching labels are not validated truth or an accuracy estimate.

Both saw a stopped-clock baseline setup, Memphis inbound/short paint attempt, then Atlanta baseline restart and advance. They differ over whether a coarse possession can be described. The distinction between a player holding a dead ball and legal live-ball control needs a clearer future annotation contract. Original labels were not rewritten to remove that ambiguity.

## Coordinator source diagnostic after labels were fixed

[source_diagnostic.json](source_diagnostic.json) preserves the four nearby raw records and their bound source identity. The source records a Memphis missed three at 8:47, offensive rebound and out-of-bounds stoppage at 8:44, and made layup at 8:42 changing 36–29 to 36–31. The reviewed sequence begins at 8:44, after the preceding attempt. A baseline inbound alone cannot establish a new or fully observed formal possession. Source consistency is a diagnostic, not independent validation of either the source or the parser. No demonstrated parser defect is established here.

## Reproduce the capture receipts

Use the project environment and [versioned feasibility protocol](../../docs/AI_REVIEW_PROTOCOL.md). The offline tool verifies pinned catalog identity, exact source/image bytes, actual formats/dimensions, chronological typed metadata, declaration consistency and in-run drift. It accepts only the pinned catalog game URL or that exact URL plus `?watchFullGame=true`; both URLs and the rule are retained. No other query or game substitution is allowed.

```sh
.venv/bin/python research/ai_temporal_2026_11_07/summarize_probe.py --capture output/v2/full-footage-access-2026-11-07/local-temporal-aligned/capture.json --declaration output/v2/full-footage-access-2026-11-07/local-temporal-aligned/declared-test.json --catalog research/audit_access_2026_11_06/catalog.json --output output/v2/NEW_ALIGNED_RECEIPT
```

```sh
.venv/bin/python research/ai_temporal_2026_11_07/summarize_probe.py --capture output/v2/full-footage-access-2026-11-07/local-temporal-probe/capture.json --declaration output/v2/full-footage-access-2026-11-07/local-temporal-probe/declared-test.json --catalog research/audit_access_2026_11_06/catalog.json --output output/v2/NEW_OBSTRUCTED_RECEIPT
```

Reproduction requires the local original captures/images; they are not committed or redistributed. A fresh clone has metadata/annotations, not the footage needed to independently verify visual claims. The committed [aligned](probes/aligned/summary.json) and [obstructed](probes/obstructed/summary.json) receipts retain every frame and consumed-input/code hashes without absolute coordinator roots. Their scope is always temporal feasibility. A run with no media-time advancement fails metadata checks even if the player reports unpaused/ready; progress only after collection cannot rescue it. Short stationary brackets and repeated images remain valid evidence rather than automatic failures. Metadata checks, wall-duration targets, complete-possession evidence, pixel synchronization and scientific approval have separate fields; the latter three remain false. New output directories are required and failed publication preserves previous evidence.

For the literal comparison, reopen the bound packet and original A/B files, verify their hashes and exact ordered frame IDs, and compare the five declared fields in order. Null/`unclear` is unknown; normalize clocks with `whistle_research.ai_review.clock_ticks`; otherwise compare typed values literally. Count every paired field once and preserve uncertainty and original prose. No sequence verdict is automatically adjudicated.

## Scope and remaining work

The [receipt](receipt.json) accounts for the unchanged 303 selected game IDs. This one technical sequence supplies no complete formal possession, period, full-game AI review, human submission, error-rate estimate, model fit or publication approval. The earlier [three-game sampled-frame pilot](../ai_review_2026_11_06/README.md) remains separate. All **303 full-game AI reviews remain incomplete**, and the frozen human route still has its 606 empty forms.

[listed_durations.json](listed_durations.json) sums the first strict successful opening runtime for each exact selected game: **549.722 listed hours**, median 107.548 minutes. This is a capacity estimate for one normal-speed playback pass, not proof that the broadcasts contain complete uninterrupted game action. The existing access evidence is dated; it does not guarantee future account/region access.

Current alternatives have not supplied a bulk file route. NBA documents archived full-game playback, while its offline downloads are a Premium mobile/tablet feature with expiry; that does not establish a desktop file export. Claude documents still-image input and screenshot-based computer use, not native complete-video analysis in this tested session. The installed NBA extractor listing was marked broken, and a metadata-only probe of an older public player failed; that player was outside this fixed sample. No game was substituted, no new subscription/account link was created, and no new API billing was started. Sources checked 2026-11-07: [NBA League Pass](https://support.watch.nba.com/hc/en-us/articles/115000585974-NBA-League-Pass), [NBA offline downloads](https://support.watch.nba.com/hc/en-us/articles/24939268210455-Download-for-Offline-Viewing), [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision), [Claude computer use](https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork).

Full-game work still needs complete source delivery or an actually sustained capture/segment-review run, a formal temporal annotation contract, explicit gaps and uncertainty, and a verified whole-game pilot before scaling. The current short evidence cannot fill that ledger. The NBA player was left paused at media 2065.911745 seconds in ATL @ MEM; verify live state before resuming and do not treat earlier unobserved intervals as reviewed. Full-study lock, meaningful predictive gain and unused evaluation evidence remain separate unresolved requirements.

## Verification

Parent verification passes **44 focused tests**, scoped Ruff, and the complete project check: **873 Python tests**, maintained lint, both website suites, wheel build and isolated installation. Commands: `.venv/bin/python -m pytest tests/v2/test_temporal_probe.py -q`, `.venv/bin/ruff check research/ai_temporal_2026_11_07/summarize_probe.py tests/v2/test_temporal_probe.py`, and `.venv/bin/python scripts/check.py`. Full log: `output/v2/temporal-feasibility-final-checks-2026-11-07.log`. The receipt tests cover false source/URL identity, invalid timing, corruption, path escapes, input drift, obstruction and stalled-player false passes. No website UI changed, so no website browser sweep was required.

Independent Sol implementation review reproduced both final receipts byte-for-byte, checked 23 descriptors and packet/image/original-submission bindings, replayed the five-field counts, verified the Claude export checksums, recomputed all 303 listed durations and reproduced parser group 66. It confirmed unchanged frozen hashes, 606 blank human forms and all 303 full-game AI reviews incomplete. Review exposed and rechecked the stalled-player false pass and removal of the private consultation URL. The parent independently reran the key tests, both actual receipts, source group and full checks. These are implementation/provenance checks, not independent visual truth, full temporal coverage or scientific completion.
