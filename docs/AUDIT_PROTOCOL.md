# Independent reconstruction audit

Original date: 2026-11-02. Updated: 2026-11-07. Status: larger frozen design INACTIVE at the user's request; independent evidence absent and release approval CLOSED.

## Active scope — 2026-11-07

The user discontinued the 303-game campaign. Do not treat its 606 empty submissions or 1% game-error target as an active software-rewrite checklist. The original fourteen-game pool supports bounded development diagnostics when needed; there is no replacement requirement to review fourteen complete games. These diagnostics carry explicit uncertainty and cannot establish a population error bound or pass the frozen audit.

The design, methods and dated evidence below are preserved for interpretation and reproducibility. Frozen configuration, packet, reviewer protocol, original forms and recorded gate result remain unchanged. Discontinuing the campaign does not turn a blocked audit into a pass or make any game eligible. Any future confirmatory validation needs its own explicitly specified scope and supporting evidence; its sample size is not automatically 303. No such future design is selected here.

## What the audit establishes

The audit tests whether recorded events have been assigned to the intended possession opportunities and counted-foul outcomes. It does not establish whether every foul/non-call was correctly officiated or whether the event feed reflects real-time availability.

Use independently accessible game footage and official event logs. A parser comparison is useful for locating discrepancies but is not independent annotation. Never create human-review records from model output or let synthetic fixtures stand in for footage review.

## Two samples

1. Simple random sample of complete games from the declared target cohort. Review all eligible events in each sampled game. This supports estimating the probability that a game contains a material reconstruction discrepancy. It does not directly estimate per-possession error.
2. Enriched sample of games with parser disagreements, unusual retained-ball/free-throw sequences, overtime, clock anomalies, or source corrections. This diagnoses failure modes and is not pooled into population error estimates.

Use a reproducible seed and record the sorted sampling frame digest, cohort/parser/source versions, selection method, game IDs, and sample strata. Determine sample size and tolerances BEFORE seeing annotation error results. A small pilot may inform the final design but is then development evidence, not the protected validation sample.

## Annotation and adjudication

Two distinct reviewers independently label the full game using evidence references and the fixed definitions. Keep their original records. Capture possession start/end source-event references, offense/defense, counted-foul event attribution, uncertain events, and material discrepancies. Do not show model scores, fitted history effects, or desired results to reviewers. Record any necessary visible parser information as a blinding limitation.

Require reviewer identity, evidence reference, full-game coverage attestation and a record of review completion. Disagreements require documented adjudication by a named reviewer with evidence, preserving both original judgments. All critical discrepancies must be resolved with an updated parser and separately evaluated audit evidence; fixing cases and reusing them alone is not fresh independent validation.

## Gate and uncertainty

The automated gate checks completeness and provenance, not the truthfulness of a human attestation. For the random sample, calculate an upper one-sided binomial confidence bound for the fraction of games with any material discrepancy (a full-game cluster outcome), reporting method/confidence/sample count. This design deliberately avoids treating possessions from the same game as independent trials. It assumes the random game sample represents the declared cohort; transfer to another season/source/parser requires new evidence.

The user/research lead must freeze the maximum tolerated game-level material-error rate, confidence level and required random sample size before annotation evaluation. These values were unset in the initial protocol; the dated decision below supersedes that initial state. No invented threshold or missing review can yield a pass. Enriched cases must all have complete adjudicated reviews and no unresolved critical issue.

Passing this gate is necessary but not sufficient for confirmatory evaluation: feature timing, exposure inventory, model-selection protocol and meaningful-effect thresholds have separate gates.

## Initial missing evidence (2026-11-02)

Verified footage access, independent completed annotations, adjudication, and a frozen sample size/error tolerance are not present in the initial rewrite. The repository's hand-reviewed opening fixture is valuable regression evidence, but not a population-level independent audit. Tooling may generate a review packet and explicitly blocked gate report while these requirements remain missing.

## Development comparison of archived feeds (2026-11-05)

The [2024–25 diagnostic](../research/cross_feed_2026_11_05/README.md) compares the pinned CDN and mobile event archives for the games already flagged in the v7 run. For a unique game/event ID, require equal nonempty order number or timestamp before comparing period, clock, event team and offense. A missing team is unknown; an unmatched row stays unmatched. These are different representations of NBA records, potentially with common upstream errors. This targeted comparison cannot estimate the error rate of the fixed random audit or replace independent observation. See the [clock and foul cases](../research/cross_feed_2026_11_05/CASE_NOTES.md) for why isolated matches do not establish a possession boundary.

The [versioned external-parser pilot](../research/cross_feed_2026_11_05/alternative_parser/README.md) retains all fourteen fixed games: thirteen parsed, one explicit missing-source failure. Literal last-assigned event agreement is a diagnostic, with unavailable/uncomparable cases explicit; it is not an adjudicated possession-error rate.

## Subscription footage access (2026-11-05)

The [League Pass access observations](../research/cross_feed_2026_11_05/league_pass_access.json) document official full-length playback for all fourteen fixed games, with midpoint seek observations for three. They retain feed labels and observed player metadata without credentials or session URLs. No entire stream was reviewed or attested continuously; full coverage and independent annotations remain absent. Reviewers must independently check coverage and preserve their own labels under the protocol above. This access milestone leaves the audit gate BLOCKED.

## Frozen audit handoff (2026-11-06)

After the user delegated the recommendation, the research lead selected a maximum 1% game-level material-error rate with 95% one-sided confidence. This is a policy choice for research credibility, not an external standard. With zero observed errors the exact binomial upper bound is `1 - 0.05**(1/n)`: 299 random games give 0.9969%, while 298 give 1.00024%. The [NIST exact-binomial reference](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm) describes the confidence-bound method. The declared binomial game model is explicit; no independence of within-game possessions or finite-population correction is claimed.

The deterministic new selection has 299 random games and four separate enriched games from the unchanged 6,084-game frame. Preserve the original fourteen-game development pilot. Five games overlap the larger union; disclose prior exposure rather than presenting it as untouched model-evaluation data. Do not replace unavailable games, add observations after inspecting errors, or change tolerance to obtain a pass.

The [handoff](../research/audit_handoff_2026_11_06/README.md) retains the earlier selection-stage receipt and a later scoped freeze binding the actual plan, packet manifest and [review contract](REVIEWER_GUIDE.md). Both reviewer kits contain source-verified raw rows and empty forms; their delivered instructions/protocol/ledgers are hash checked. Only five of the 303 selected games have earlier playback observations, and continuous coverage is unverified for all games. No reviewer identities or completed human labels exist.

The metadata gate alone is insufficient. Production promotion requires the real evidence directory, structurally complete hash-bound A/B annotations, adjudication of row-level disagreements and a parser-versus-human comparison. The comparison reparses frozen raw rows and verifies that the export matches; it checks opportunity counts, nonadministrative grouping/order, teams, exact counted-foul references, targets and all declared prediction-start fields. Both human files agreeing with each other cannot hide disagreement with the parser. Missing comparison evidence or any mismatch blocks promotion. Structural validation authenticates neither people nor footage truth.

The actual gate remains BLOCKED for missing reviews and an unavailable error bound. Full-study preregistration, meaningful predictive gain and genuinely unused evaluation evidence remain unfrozen separate gates. No empirical model fitting or publication follows from this scoped audit freeze.
