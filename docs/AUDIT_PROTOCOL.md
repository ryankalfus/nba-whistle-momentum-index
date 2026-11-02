# Independent reconstruction audit

Date: 2026-11-02. Status: proposed sampling design; release approval is CLOSED until the specified evidence exists.

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

The user/research lead must freeze the maximum tolerated game-level material-error rate, confidence level and required random sample size before annotation evaluation. These values remain unset in the initial protocol. No invented threshold or missing review can yield a pass. Enriched cases must all have complete adjudicated reviews and no unresolved critical issue.

Passing this gate is necessary but not sufficient for confirmatory evaluation: feature timing, exposure inventory, model-selection protocol and meaningful-effect thresholds have separate gates.

## Current missing evidence

Verified footage access, independent completed annotations, adjudication, and a frozen sample size/error tolerance are not present in the initial rewrite. The repository's hand-reviewed opening fixture is valuable regression evidence, but not a population-level independent audit. Tooling may generate a review packet and explicitly blocked gate report while these requirements remain missing.
