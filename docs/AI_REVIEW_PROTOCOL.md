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
