# AI sampled-frame review — 2026-11-06

Status: **working visual handoff and paired AI pilot; zero completed full-game reviews**. The user requested an AI route instead of arranging two humans. The frozen human packet remains historical and unchanged; this separate development track makes no human-validation, eligibility, 1% error-bound or model-approval claim.

## Actual completed work

Two separate Sol agents inspected every supplied image and wrote their own original annotations without seeing source play-by-play, parser output or each other's labels. Both used `gpt-6.1-sol`; this does not establish statistically independent errors. No observer was invented and no template was counted as a submission.

| Game | Latest images | Distinct video positions | Matching fields | Unknown fields |
| --- | ---: | ---: | ---: | ---: |
| `0022401195`, UTA @ MIN, 2025-04-13 | 8 | 7 | 35 | 13 |
| `0022000021`, ATL @ MEM, 2020-12-26 | 16 | 16 | 41 | 55 |
| `0022000045`, POR @ LAL, 2020-12-28 | 8 | 8 | 28 | 20 |
| Latest-packet totals | 32 | 31 | 104 | 88 |

There are zero typed-field disagreements, but **all 64 latest paired frame observations carry uncertainty**. Matches are literal label comparisons, not an accuracy estimate. Unknowns are not matches. No full possession, counted defensive-foul outcome, continuous interval, complete period or full game has been independently reconstructed from these samples.

The original ATL @ MEM packet showed studio/pregame material. Both agents left its period, game clock and scores unknown. Those submissions and their original report remain preserved. A follow-up retained those eight images and added eight later images showing second-quarter action, including a free-throw setup/attempt. The POR @ LAL packet includes presenters, a holiday bumper and six later court views. Website overlays, blur, close-ups and covered score digits remain limitations, not repaired pixels or inferred labels.

The convenience pilot uses the previously open selected game and the first two catalog games. It does not estimate the random sample's error rate. The [receipt](receipt.json) accounts for all 303 fixed assignments: three have paired sampled-frame passes, 300 have no AI frame review, and **all 303 lack completed full-game AI review**. Eight original submission files are preserved across current and historical packet versions; six belong to the latest packets. Historical observations are excluded from latest totals to avoid double-counting.

## Evidence and access fix

The tested subagents could not access this chat's in-app tab or create their own in-app tabs. The parent recovered the stalled authenticated player through the supported in-app UI, then handed off captured images through shared local files. No credentials, cookies, signed media addresses or browser profiles were shared.

The initial screenshot crop mixed document and viewport coordinates. That failed probe was excluded before reviewers received a packet and is recorded in [capture_exclusions.json](capture_exclusions.json). Later captures align the full player. The transport returns JPEG bytes even when an initial filename ends in `.png`; preparation detects the real format and copies the bytes unchanged into correctly named packet files. No generated, enhanced or reconstructed image is evidence.

Complete temporal footage remains unavailable to the agent workflow. The supported observed-asset inventory exposed zero video-file assets, and the supported media-download call returned no local video file. The sanitized [export probe](media_export_probe.json) records that result. This does not diagnose DRM or prove no other authorized route exists. It establishes that this supported route yielded no recording. The current handoff supplies still images, not continuous video or audio to the agents.

Original captures, images, packets and full provenance remain local under `output/v2/ai-footage-2026-11-06/`. Images are ignored and are not committed or redistributed. This directory commits AI annotations, descriptive reports, compact hash receipts and the coverage ledger. Annotations do not substitute for their images when independently verifying visual claims.

## Reproduce metadata preparation and comparison

Use the pinned environment and [AI review protocol](../../docs/AI_REVIEW_PROTOCOL.md). The isolated CLI never invokes promotion or changes human audit records. The explicit catalog option supports an installed package; its required hash stays pinned.

```sh
.venv/bin/python -m whistle_research.ai_review prepare --capture output/v2/ai-footage-2026-11-06/0022000021/capture-016.json --catalog research/audit_access_2026_11_06/catalog.json --output output/v2/NEW_AI_PACKET
```

Preparation verifies capture/image bytes, identity/date, media fields and timestamps. It produces byte-preserved images, a controlled portable packet and two empty AI templates. For immutable captures, new packet/image bytes match; coordinator provenance records actual locations and implementation versions. Final packets were prepared again after the development fixes, with exact packet-byte equality checked for unchanged earlier packets. Earlier receipts remain intact.

```sh
.venv/bin/python -m whistle_research.ai_review compare --packet output/v2/NEW_AI_PACKET/packet.json --review-a research/ai_review_2026_11_06/submissions/A/0022000021.followup.json --review-b research/ai_review_2026_11_06/submissions/B/0022000021.followup.json --catalog research/audit_access_2026_11_06/catalog.json --output output/v2/NEW_AI_COMPARISON
```

Comparison consumes original submission bytes. Clock strings such as `9:54`, `09:54` and `9:54.0` compare using integer tenths while originals remain unchanged. Unsafe paths, malformed types, wrong hashes, duplicate/missing frames, forged human/coverage claims and cross-packet submissions fail closed. Failed publication removes only its new output and preserves existing evidence.

## Verification and remaining work

The 45 focused contract tests and scoped Ruff pass. The final parent full check passed 829 Python tests, maintained lint, both website suites and package build/isolated installation; log: `output/v2/ai-review-final-checks-2026-11-06.log`. Independent Sol review reproduced all three latest packet/report pairs and the historical pregame report byte-for-byte, verified all 61 receipt/exclusion descriptors and the preserved submissions, and found no remaining actionable issue in code, data or docs. The parent separately replayed all three latest reports from the tracked original submissions. Frozen human manifest/protocol/parser hashes remain unchanged and all 606 forms are blank. These checks establish provenance and comparison behavior, not visual truth or temporal coverage.

Full-game AI review still needs a separately specified temporal evidence method and actual complete footage observation. These frame packets cannot be relabeled as full games. No current observation demonstrates a parser defect warranting semantic repair, and no reconstruction flag is cleared. Full-study protocol, meaningful predictive gain and unused evaluation requirements also remain unresolved; see [STATUS.md](../../STATUS.md).
