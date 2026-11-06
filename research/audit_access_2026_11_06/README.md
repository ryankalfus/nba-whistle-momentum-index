# Audit access catalog — 2026-11-06

Status: coordinator lookup implemented and checked; individual playback checks are in progress. **No continuous full-game coverage, independent human annotation or scientific eligibility has been established.** The frozen audit plan, reviewer kits, protocol and parser remain intact.

## Catalog

[catalog.json](catalog.json) accounts for all 303 selected games against the exact pinned design, full frame, independent schedule, six historical metadata CSVs and source manifest. It preserves archive declarations and exact input byte descriptors. It does not consume/reverify the raw archives or retrieve the external correction pages.

Two selected games have stale historical CSV dates: `0022000166` and `0022000199`. Both historical dates and the corrected schedule dates/provenance are retained. All home/away identities agree with the schedule. Each `candidate_game_url` is explicitly inferred from that pinned matchup; generating it does not verify a page, replay listing or playback.

Five selected games have historical playback observations from the original fourteen-game pilot. The other 298 had none in that dated snapshot. Historical playback, historical date-page evidence, inferred candidates, continuous coverage and actual human review remain different fields.

```sh
.venv/bin/python research/audit_access_2026_11_06/prepare_catalog.py --output output/v2/NEW_ACCESS_CATALOG
```

Output must be new. Input/code drift, malformed or conflicting identities, missing games and unsupported source/correction mappings fail closed. The actual build and independent agent/parent replays were byte-identical.

## Fresh in-app observations

[first_batch_observations.json](first_batch_observations.json) preserves the initial 24 observations for 21 distinct successful selected games, including three incomplete initial reads and their successful follow-ups. The raw failed reads remain visible. A separate recovery observation for the previous Miami–Clippers pilot game is not counted as another selected game.

Checks use official NBA game pages in the authenticated in-app browser. A successful observation requires the Full Games UI selection, a finite long runtime, positive video position, unpaused playback, ready state 4 and no media error. The 3,000-second runtime screen is a consistency check alongside the official Full Games selection, not proof of complete coverage. Default feed labels stay unidentified where no player header was captured. Named feed catalogs do not prove every listed feed plays.

The continuing run saves separate dated progress files under `output/v2/audit-access-progress-2026-11-06/`. These remain incomplete observations rather than a completed 303-game audit. Later checks target the actual `video.video-player` element to distinguish separate advertisement videos, and wait for the elapsed-time control to advance. Earlier observations retain their actual recorded method; no stronger evidence is retrospectively invented. Slow loads, incomplete reads and successful follow-ups are separate records.

Playback is account-, region- and time-dependent. Opening a stream and seeing a long runtime cannot attest uninterrupted footage, all periods or annotation correctness. No account identifiers, passwords, cookies, media addresses or tokens belong in these artifacts. No footage is downloaded or redistributed.

## Parser evidence and verification

[JUMP_BALL_REVIEW.md](JUMP_BALL_REVIEW.md) records the primary-source investigation and pinned-code comparison. No inspected NBA statistical instruction resolves the residual actor mismatches. The broader stats-feed jump heuristic is present in the pinned comparator distribution, but the earlier pilot exercised its mobile feed path. Neither implementation precedent nor source agreement supplies independent film truth or an automatic repair.

The catalog's 34 focused tests and scoped Ruff passed. Independent Sol review found no actionable issue and reproduced the exact catalog. The parent separately verified the replay and four pinned parser-source hashes. `.venv/bin/python scripts/check.py` passed **668 Python tests**, maintained lint, both website suites and wheel build/isolated installation; log: `output/v2/audit-access-final-checks-2026-11-06.log`.

PR #10's reviewed audit-promotion changes were merged at `5a8891e58fd8a52170b2a0806d32a6a2c2fcd436` after CI success for head `bc25afaf69e4920fe106ebc6fe168a8a1b5254ac`. Local tree equality was checked before this new branch. No deployment or scientific release followed.

Remaining audit requirements are in the [handoff](../audit_handoff_2026_11_06/README.md): full continuous footage, two actual independent reviewers, 606 full-game submissions and adjudication, plus separate full-study/evaluation gates. Current individual playback checks do not discharge those requirements.
