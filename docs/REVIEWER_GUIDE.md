# Full-game reconstruction review contract

Version: `review-contract-2026-11-06-v1`. Status: audit preparation; not a completed audit or a locked confirmatory study.

## Purpose

Review the assignment of recorded NBA events to possession opportunities and counted defensive-foul outcomes. Do not judge whether contact deserved a call, referee intent or causality.

The coordinator records the sampling and acceptance design separately so reviewers do not receive selection strata, anomaly rationales or a desired passing result. Every assigned game requires independent full-game reconstruction. Do not change the assignment to a more convenient game. Parser repairs require a new version and fresh audit evidence rather than declaring repaired development cases validated.

## What counts as a material discrepancy

Record a material discrepancy when a reconstruction error changes at least one eligible possession opportunity, its ordering, offense/defense assignment, counted defensive-foul outcome or attribution, or a declared pre-possession prediction input. Apply the recorded-foul definition: offensive, technical and double-technical fouls are excluded from the legacy counted-foul outcome; supported defensive types must be attributed explicitly. Team-penalty accounting is a separate classification.

A different administrative-event attachment alone is nonmaterial only when it changes none of those quantities. Record the difference and the rationale. Literal agreement on source rows, parser counts or two feeds does not establish basketball truth. Record clock/score/identity discrepancies at their reported precision; do not silently correct the source, fill missing ownership, invent foul types or sort away a clock reversal. Uncertain or unresolved events retain their uncertainty and block promotion. A missing event visible on film must be reported as a critical source omission with its footage reference, not given an invented source-row ID.

In the blinded first phase, record your own reconstruction and any source-versus-footage discrepancies; you cannot judge an unseen candidate's output. After submissions are fixed, a coordinator compares the actual candidate with the independent labels. Source/film flags alone are not the candidate's measured error count. The production comparison reparses the bound raw source with the pinned parser, checks the export against that reconstruction, and compares possession opportunities, ordering/grouping, teams, counted-foul attribution, outcomes and prediction-start context with the human files. Any mismatch or missing comparison evidence blocks promotion, even if both first-pass game-summary flags were false. Preserve the original files and the separate comparison receipt; never rewrite human flags to make a comparison pass.

## Independent review

The coordinator gives reviewer A only `reviewer_A/` and reviewer B only `reviewer_B/`. Each folder is standalone. Do not distribute the coordinator manifest, full sampling frame, strata/rationales, parser reconstructions, model scores or the other reviewer's labels. Raw official source ownership fields remain visible; disclose this limit on blinding. Raw source records are evidence that may themselves be wrong.

Each actual human records their identity, `reviewer_kind: human`, independent status, start/completion times and footage references. These fields are attestations; software cannot establish that two identifiers represent two different people. Reviewers must work separately and preserve original submissions. AI output and generated templates are not human-review records. No reviewer names, completed reviews or coverage attestations have been created by packet generation.

Watch the entire available full-game recording, including every regulation and overtime period. Opening playback, runtime and isolated seeks are access checks. They cannot establish continuous coverage. Use one identified continuous recording and first broadcast occurrences when recording evidence times; do not substitute condensed clips or replay snippets. Keep gaps, edits and unavailable portions explicit. A source feed containing four periods does not prove the footage contains all four without gaps.

## Annotation files

Use `human-full-game-annotation-v1`, specified in each kit's `INSTRUCTIONS.md`. The empty JSON files are entry templates and intentionally fail validation.

1. Preserve exact game/source/parser/plan identities and the unique raw `member:row` references. Event action IDs can repeat and are not unique references.
2. Label possession ranges in source order with distinct offense/defense IDs, counted-foul references, footage times, uncertainty and material-discrepancy judgments. Ranges are inclusive, disjoint and confined to one period. The schema uses an explicit partition; it cannot express one raw row assigned to two possessions.
3. Assign every remaining raw row an explicit administrative/no-possession exclusion with evidence, uncertainty and material judgment. Do not omit a problematic row to obtain completeness.
4. Provide continuous full-game coverage attestations with each source period's first/last references and chronological, nonoverlapping footage ranges. Possession/exclusion times must lie in their period. Document any justified overlap in adjacent possession evidence.
5. Preserve incomplete/critical submissions. An importer may return BLOCKED; this is a reviewable result, not permission to alter the original labels.

Every possession also needs independent `prediction_start` fields for production comparison: `reference_ref`, `period`, `clock`, `score_margin`, `score_difference`, `home_defense`, `defense_counted_fouls`, `previous_foul_1`, `previous_foul_2`, and `start_type`. Record context immediately before the declared reference event; it may precede the rows assigned to the possession. `score_difference` is defense score minus offense score, margin is its absolute value, and `home_defense` is 0 or 1. Clock is seconds remaining; history indicators use prior reconstructed opportunities and truncate at the game boundary. A genuinely unavailable prior indicator is explicit null. `start_type` identifies the reference event/start kind. A null `reference_ref` is supported only for a genuine period start without a source-event reference. Do not copy candidate values. Structural intake can inspect an incomplete first-pass file, but absent prediction-start evidence cannot pass production comparison.

The coordinator records exact annotation-file byte sizes and SHA256 hashes alongside each review's metadata. A third adjudicator, when needed, supplies a separate complete annotation and a rationale bound to both original annotation hashes. Row-level disagreements require adjudication even when reviewers' game-level verdicts match. A favorable adjudication cannot erase a material error recorded in either original review.

## Freeze and promotion

Bind the accepted audit settings to the exact plan, coordinator packet manifest and this protocol's bytes before reviewers start. Preserve the dated freeze and its Git receipt. A timestamp in JSON is not an authenticated external registration. Reviewer-start and completion times must follow that freeze. Any changed instructions or source/annotation bytes require explicit re-versioning and fresh applicable evidence.

The metadata-only `audit.check_gate` remains a conditional attestation check. Production promotion additionally requires the actual evidence directory, successful structural validation of its frozen files and the bound parser-versus-human comparison. Promotion and real-fit re-entry repeat those checks. Neither a passing JSON flag nor a reference string can substitute for files or compared labels.

Full study preregistration, the meaningful predictive-gain threshold and genuinely unused evaluation evidence are separate requirements. The audit freeze does not authorize model fitting, publication or a claim that the scientific rewrite is complete. Identity, footage authenticity and the truth of human labels remain external evidence requirements even after structural checks pass.
