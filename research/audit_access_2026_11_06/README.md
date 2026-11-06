# Audit access catalog and playback metadata — 2026-11-06

Status: **303 of 303 selected games have dated official Full Games opening-playback observations**, captured in the authenticated in-app browser on 2026-11-06. The complete source and metadata export are saved below. **No continuous full-game coverage, independent human annotation or scientific eligibility has been established.** The frozen audit plan, reviewer kits, protocol and parser remain intact.

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

Checks use official NBA game pages in the authenticated in-app browser. The strict `OPENING_PLAYBACK_VERIFIED` category requires the exact selected game URL, matching page title/date, Full Games UI selection, a finite runtime over 3,000 seconds, positive video position below the duration, unpaused playback, integer ready state 4 and no media error. The 3,000-second runtime screen is a consistency check alongside the official Full Games selection, not proof of complete coverage. Default feed labels stay unidentified where no player header was captured. Named feed catalogs do not prove every listed feed plays.

The run saved separate immutable progress files under `output/v2/audit-access-progress-2026-11-06/`; its final checkpoint was `ui-1793996627272.json`. The exported [source snapshot](playback/observations.json) preserves all 358 reads, including 51 incomplete reads and 307 successful reads covering 303 distinct selected games. The four repeated successful reads do not add games or independent observers. Every selected game passed after any needed follow-up; no game was substituted. Later checks target the actual `video.video-player` element to distinguish separate advertisement videos, and wait for the elapsed-time control to advance. Earlier observations retain their actual recorded method; no stronger evidence is retrospectively invented. These are completed opening-access checks, not a completed scientific audit.

Playback is account-, region- and time-dependent. Opening a stream and seeing a long runtime cannot attest uninterrupted footage, all periods or annotation correctness. No account identifiers, passwords, cookies, media addresses or tokens belong in these artifacts. No footage is downloaded or redistributed.

## Source-bound metadata export

[summarize_playback.py](summarize_playback.py) reads the actual saved observation bytes. It pins the 303-game catalog and initial baseline hashes, requires the first 24 observation dictionaries to remain exactly unchanged, and rejects unknown game IDs, inconsistent success flags, duplicate JSON keys, non-finite numbers, private URLs and sensitive fields. Captured player matchups and any explicit header date must agree with the catalog. Failed reads, repeated checks and successful follow-ups remain separate raw records; the unrelated recovery game is excluded from selected-game counts.

```sh
.venv/bin/python research/audit_access_2026_11_06/summarize_playback.py --observations research/audit_access_2026_11_06/playback/observations.json --output output/v2/NEW_PLAYBACK_SUMMARY
```

The output directory must be new. `observations.json` preserves the consumed source bytes exactly. `summary.json` binds those bytes, the pinned catalog/baseline and implementation bytes with portable paths, byte counts and SHA-256 hashes; it refuses input/code drift during the run. Counts distinguish raw reads, successful reads, unique strict successes, named-team observations, their unique union, attempts and remaining cases. Classification is **METADATA_CONSISTENCY_ONLY**: the program checks recorded fields, not the authenticity of footage or the identity of a human observer. It cannot evaluate scientific eligibility or the audit gate.

Replaying the saved snapshot reproduces the raw bytes, counts, game records and reviewer addendum. Its `inputs.observations.path` records the replay's input location, while the committed summary records the original checkpoint path; this descriptor difference is expected. The consumed bytes and SHA-256 remain identical.

`reviewer_access_addendum.json` is a separate access resource for the same 303 assignments. It exports controlled date/matchup/public-link and typed playback fields, retains unverified cases and marks inferred URL leads separately from actually observed matching pages. It excludes raw method kinds, raw player headers, coordinator input paths, sampling strata, model/parser labels and tolerances. Raw headers remain available in the coordinator snapshot for provenance. The exporter does not modify frozen reviewer kits, packet manifests or protocols, and access rights do not transfer with the links.

### Conditional named-team-stream category

The secondary `named_team_stream_v1` mode handles a possible combined stream menu without a Full Games tab. It requires a healthy long stream with decoded video dimensions, the actual selected team label in the observed menu, matching page/title/header teams and selection timestamp, and explicit recap/condensed alternatives. Generic, mobile, condensed and recap labels cannot qualify. Its status is `TEAM_STREAM_PLAYBACK_OBSERVED`; `full_games_selected` and `full_length_playback_verified` remain false, and `full_game_classification` stays **inferred**. Strict Full Games counts keep their original meaning; the union never double-counts a game observed in both modes. Only synthetic fixtures exercise this secondary category; the completed captured run has zero secondary observations.

NBA's [replay instructions](https://support.watch.nba.com/hc/en-us/articles/360011802673-Full-Game-Replays-and-Condensed-Game-Availability), updated 2026-10-07, direct viewers through Game Details to a desired stream; those instructions do not require a particular tab. The [League Pass description](https://support.watch.nba.com/hc/en-us/articles/115000585974-NBA-League-Pass), updated 2026-10-13, lists home, away, mobile and alternative feeds, full-game archives starting in 2012–13, and separate condensed formats. The [2024-10-15 NBA release](https://pr.nba.com/nba-app-launches-new-digital-features-highlighted-by-multiview-ahead-of-the-2024-25-season/) identifies All Possessions and 10-Minute Condensed as recap versions. These sources support keeping feed and recap categories distinct; they do not establish that a bare team-name menu label is officially mapped to a full-game replay. The secondary full-game interpretation therefore remains an inference.

### Completed access receipt

The [metadata summary](playback/summary.json) reports `ALL_SELECTED_OPENINGS_VERIFIED`. The separate [reviewer access addendum](playback/reviewer_access_addendum.json) supplies dated observed links for all 303 existing assignments. Give it to both reviewers alongside their own unchanged kits; do not give them this coordinator README, catalog or raw snapshot.

| Receipt field | Final captured value |
| --- | --- |
| Fixed selected assignments | 303 |
| Distinct strict opening-playback successes | 303 |
| Successful reads / incomplete reads | 307 / 51 |
| Preserved raw observation records, including failed reads/rechecks | 358 |
| Unattempted / still unverified assignments | 0 / 0 |
| Secondary named-team-stream observations | 0 |
| Source snapshot, summary and reviewer addendum directory | `research/audit_access_2026_11_06/playback/` |
| Verified continuous full-game coverage | 0 |
| Completed independent human submissions | 0 of 606 |

The exact source snapshot is 413,041 bytes with SHA-256 `a275cfb9e8ab667363777b9c202280af9a08dd9b97ba618a7da465c5ee224ab8`. The summary records all consumed input and implementation descriptors. All 303 access observations remain account-, region- and time-dependent; no continuous-coverage attestations or human labels were created.

## Parser evidence and verification

[JUMP_BALL_REVIEW.md](JUMP_BALL_REVIEW.md) records the primary-source investigation and pinned-code comparison. No inspected NBA statistical instruction resolves the residual actor mismatches. The broader stats-feed jump heuristic is present in the pinned comparator distribution, but the earlier pilot exercised its mobile feed path. Neither implementation precedent nor source agreement supplies independent film truth or an automatic repair.

The catalog's 34 focused tests and scoped Ruff passed. Independent Sol review found no actionable issue and reproduced the exact catalog. The parent separately verified the replay and four pinned parser-source hashes. `.venv/bin/python scripts/check.py` passed **668 Python tests**, maintained lint, both website suites and wheel build/isolated installation; log: `output/v2/audit-access-final-checks-2026-11-06.log`.

The metadata exporter has **116 focused offline tests** and scoped Ruff passing. Independent review of the exporter code closed its findings, including reviewer-field blinding, explicit header-date checks and case-insensitive private-URL rejection. The final parent full project check passed **784 Python tests**, maintained lint, both website suites and wheel build/isolated installation; log: `output/v2/audit-playback-final-checks-2026-11-06.log`. This verifies software behavior, including synthetic secondary-mode fixtures, rather than footage coverage or human evidence.

Final independent Sol review reproduced all three complete playback artifacts byte-for-byte, checked every observation index and the first 24 baseline records, verified consumed hashes and confirmed that all 358 distinct reads across 363 immutable checkpoints survive in the final snapshot. The parent separately replayed from the tracked source copy, matching all fields except the declared input-location descriptor. The reviewer confirmed the frozen packet/protocol hashes and all 606 blank forms. Fresh collection still exited 1 / **BLOCKED**, zero completed games and 606 failed submissions; report: `output/v2/audit-access-independent-full-review-collection-exitcheck-1793996627272/collection_report.json`. No actionable issue remained in the final code, data or four updated docs.

PR #11 merged the earlier catalog/access work at `10c4fb7`. PR #10's reviewed audit-promotion changes were merged at `5a8891e58fd8a52170b2a0806d32a6a2c2fcd436` after CI success for head `bc25afaf69e4920fe106ebc6fe168a8a1b5254ac`. Local tree equality was checked before this new branch. No deployment or scientific release followed.

Remaining audit requirements are in the [handoff](../audit_handoff_2026_11_06/README.md): full continuous footage, two actual independent reviewers, 606 full-game submissions and adjudication, plus a full-study protocol freeze, a verified unused evaluation cohort and a predeclared meaningful-gain threshold. Current individual playback checks do not discharge those requirements.
