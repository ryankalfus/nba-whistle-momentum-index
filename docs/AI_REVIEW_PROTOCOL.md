# AI visual review protocol

Date: 2026-11-06. Version: `ai-sampled-frames-v1`. Status: development, not a full-game validation or scientific release.

## Authorization and evidence boundary

The user requested AI subagents in place of the proposed human review work. This development track records genuine AI observations without changing or relabeling the earlier frozen human packet. AI submissions use `reviewer_kind: ai`. They cannot satisfy the existing human collector, confer eligibility, authorize model fitting or support the proposed 1% game-error bound.

The first task is to establish a usable visual handoff. The parent chat can operate the authenticated in-app browser; the tested subagent sessions cannot see that tab or create their own in-app tabs. The parent therefore captures visible, paused game screenshots into local files. Agents receive byte-verified copies, not credentials, cookies, media URLs or browser profiles. No streams are downloaded and no captured images are committed or redistributed.

## Pilot selection and coverage

The development pilot is the currently open selected game `0022401195` and the first two games in the existing access catalog, `0022000021` and `0022000045`. This is a convenience and technical-feasibility sample, not a new random audit sample. The 303-game design remains intact; games without actual AI submissions remain explicitly unreviewed in this track.

Target eight paused screenshots per initial packet, using the visible player controls to advance approximately ten media seconds between samples. Retain repeated positions, failed capture attempts and access failures separately. If these show pregame material or advertising, preserve that packet and both original submissions; locate game action and issue a new follow-up packet with the additional evidence. Larger timeline jumps are explicitly discontinuous. Before each later capture, align the full player to reduce website-header obstruction; earlier obstructed images remain unchanged. Readiness and media position are checked before recording; screenshots are bracketed by metadata reads at an unchanged paused position. Metadata does not authenticate the depicted game or guarantee exact compositor/video-time synchronization.

These are isolated sampled frames. The time between first and last samples is not a continuously reviewed interval. No audio, complete possession sequence, full period or complete game is attested. Count frame records, distinct image hashes and distinct video positions separately. A repeated position is not additional temporal coverage.

## Source-bound preparation

Use the isolated `whistle_research.ai_review` CLI. It verifies the pinned 303-game catalog, exact game/date/public URL, aware capture timestamps, media metadata, image byte counts and SHA-256 hashes. It decodes actual JPEG/PNG content rather than trusting a filename extension. Preserve original screenshot bytes; do not enhance, reconstruct or generate evidence images.

Preparation copies verified images into a new portable packet. Reviewer fields contain public identity, frame IDs, capture/video timestamps, actual image format/dimensions and byte hashes. Candidate reconstructions, source-event labels, sampling strata/rationales, model predictions, coordinator paths and the other agent's labels are withheld. Provenance remains coordinator-only.

The caller must supply a new output directory. Input/code drift and malformed or conflicting evidence fail closed. The installed CLI can take an explicit `--catalog` path; its required hash remains unchanged.

## Separate AI observations

Give each Sol agent only the packet, its own empty template and all packet images. Each agent must inspect every image using an image-viewing tool. Keep A and B submissions separate until both have finished. Both agents use the same model; separate agent IDs and withheld labels do not establish statistical independence or eliminate shared errors.

For every frame, independently record:

- Visible period and game clock, or null when unreadable.
- Away and home scores from the in-video scorebug, or null. Ignore unrelated website score cards.
- Apparent ball control: away, home, dead ball or unclear.
- Visible action category, or unclear. A pose, raised arm or isolated scoreboard cannot establish an unseen foul, turnover or possession boundary.
- An uncertainty flag and notes separating visible details from inference.

Use actual agent/model identity and aware start/completion timestamps. Do not copy fields from play-by-play, the parser or another reviewer. Unknowns are valid observations; inventing labels to complete a template is not. A completed sampled-frame submission means every supplied image received a record, not that every event is resolved or a game was watched.

## Comparison and follow-through

Comparison reopens and verifies the actual packet images and both original submission files. It requires the correct slots, exact packet hashes, canonical distinct agent IDs and valid typed observations. It retains original clock strings and compares `M:SS`/`MM:SS` values with optional tenths using integer tenths of a second.

Report literal matches, disagreements and unknowns by field. Unknowns do not count as matches. Retain frame-level uncertainty and all original notes; matching uncertain labels are not validated truth or an accuracy estimate. No automated adjudication clears a disagreement or critical parser issue.

Any later comparison with source events is a separately labeled diagnostic. It must retain ambiguous clock mappings and cannot treat samples as complete possession coverage. A parser repair needs an observed, specific defect and appropriate regression evidence. Full-game AI review would require a separately versioned temporal evidence contract and actual coverage; this sampled-frame protocol cannot be silently promoted into it.

The frozen human audit, full-study lock, meaningful-gain decision and unused evaluation requirements remain separate. This protocol makes no confirmatory NBA finding.

## Temporal feasibility extension — 2026-11-07

Version: `ai-temporal-feasibility-v1`. Scope: a short technical capture/review test, not a full-game audit contract. The earlier sampled-frame protocol and frozen human packet remain unchanged.

The user authorized Claude computer use, including full control, for this research. A real access test must show the existing NBA player and actual game pixels. Permission settings, a connected-device label or an AI statement of capability alone do not demonstrate playback. The tested Claude route exported original cropped images; its absent per-frame capture/media timestamps remain null. Preserve free-play gaps, duplicate images, missed events and the original report. One apparently continuous pause/resume boundary does not establish that the method is gap-free.

For the separate parent capture test, save a local declaration before collection: target 20 wall seconds, at most 300 frames, serial screenshots as fast as the supported API permits, and a one-second adjacent-media-gap engineering target. This target tests collection feasibility; it is not a validated observation rate for possession boundaries or fouls and is unrelated to the 1% game-error policy. The local declaration is not an authenticated external registration.

Record screenshot request/return times, public game URL, video metadata before and after each screenshot, visible slider readings, actual image bytes/hash/dimensions and any failure. Keep native JPEG bytes unchanged. A metadata bracket does not authenticate the exact media position of displayed pixels. Report midpoint spacing and the conservative `next post - previous pre` metadata bound separately. Visible slider values can lag actual media metadata and are descriptive rather than a replacement timing source. No audio is captured.

Align the complete player before collection and check alignment during it. Preserve the first obstructed run and its later quality note; do not rewrite the declaration or relabel those frames as unobstructed. Zero scroll and healthy video metadata do not prove every pixel is readable: player controls can still cover a score. A run with no captured media-time advancement fails metadata checks even if the player reports unpaused/ready; later progress outside collection does not rescue it. Do not reject individual zero-width brackets or repeated images solely for being stationary. Engineering metadata checks and the wall-duration target receive separate results. Neither result establishes continuous footage or scientific validity.

The offline receipt tool binds the existing 303-game catalog and accepts only its exact public game URL or that URL followed by the literal `?watchFullGame=true` player-control suffix. Preserve the catalog and captured URLs separately. No other query, fragment, account data or game substitution is accepted. Recheck consumed capture, declaration, image and implementation bytes before publishing into a new directory.

Give separate Sol reviewers every original image in sequence, its hash-bound metadata packet and their own template. Withhold the other review, source events and candidate output until both original submissions are fixed. Each reviewer must visually inspect every image and retain frame-level unknowns and sequence uncertainty. Compare period, normalized clock, away/home scores and apparent ball-control labels literally; retain free-text action/sequence judgments without automated adjudication. Same-model agreement remains susceptible to shared errors. In particular, physical possession of a ball during a stoppage and legal live-ball control need an explicit distinction before any future formal annotation design; do not repair that ambiguity by overwriting these submissions.

The resulting evidence is a short sequence. Its first/last timestamps, many frames or two completed submissions cannot become a complete game, complete formal possession, counted-foul outcome, error bound or eligibility attestation. A later source comparison is a coordinator diagnostic after labels are fixed. A baseline inbound alone does not prove a new possession: the preceding opportunity may continue after an offensive rebound or out-of-bounds stoppage. A full-game route still requires a separately specified temporal reconstruction contract, actual coverage of every required period/interval, explicit gaps and uncertainty, and defensible reference labels. No current feasibility receipt passes the scientific gate.
