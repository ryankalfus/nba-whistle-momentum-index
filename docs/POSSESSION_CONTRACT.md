# Canonical candidate possession contract

Date: 2026-11-02. Version: `canonical_candidate_v1`. Status: implemented candidate, not independently validated. This contract is separate from the historical `period_start_v2` parser and changes no legacy release.

## API and provenance

`whistle_research.possessions.reconstruct(actions, game_id, home_team_id, away_team_id, source_sha256=None)` returns frozen dataclasses, serializable with `dataclasses.asdict`. Explicit home/away metadata is mandatory. The input mappings are not changed. Each normalized event retains its original zero-based source row, action ID, source ordering value, labels, source possession/team, scores and complete canonical JSON mapping. Sorting uses source order, not source row position; references preserve both.

A supplied SHA256 must have 64 lowercase hexadecimal characters. `provenance_status=declared_unverified` means the caller supplied a digest, not that this parser verified source bytes. Without a digest it is `missing`. A source ledger must verify the exact source bytes and provenance separately. `eligible` always remains false; `audit_status=blocked_pending_independent_audit` cannot be overridden by synthetic tests or parser agreement.

Malformed clocks, invalid numeric fields, clock/period regressions, repeated action IDs (including identical copies), repeated ordering values and non-game teams raise `ValueError`. Unsupported semantic labels remain in the event ledger with explicit blocking `ParseIssue` records. No semantic error is replaced by a negative foul target.

## Candidate control and boundaries

Possessions group explicit source control with observed terminal state. A made field goal, offensive foul, turnover or ordinary final made free throw can end a group, even when the next legal group has the same source owner. A same-clock defensive foul/free throw after a made field goal can continue an and-one. A missed final free throw continues until a subsequent observed control event. Defensive rebounds belong to the gaining team's new group; offensive rebounds continue the old group. Jump control can transfer ownership. Period end closes a group regardless of owner.

A terminal event stays pending until another control event or period-end evidence, allowing intervening administrative events and an and-one continuation. An offensive foul followed by one same-clock, same-actor/source-owner turnover explicitly labeled `offensive foul` is one possession loss, preserving both source rows and the offensive-foul boundary. Other turnover labels or later clocks do not qualify for this pairing. Timeout, substitution, replay, block and technical foul/free throw rows cannot create groups or transfer live control. They remain attached to the active group; rows outside any group appear explicitly in `unassigned_action_numbers`. Every normalized event occurs exactly once in a group or that list. `boundary_reason` documents why the group closed. A period change without an explicit end row closes the previous group with `missing_period_end` audit uncertainty.

Recognized ordinary defensive personal/shooting/loose-ball labels count only when the actor is the defense. Offensive and technical fouls do not count. Double-personal fouls require audit. Special foul labels (clear path, flagrant, away from play and take/transition take) preserve the foul event and retained-ball sequence, but mark the group for audit because seasonal rule/entitlement adjudication is not implemented. Unknown foul, shot-result, rebound and free-throw labels, unclear ownership, unsupported violations and unexplained transfers similarly create blocking audit flags. A defensive-rebound actor/source-owner conflict quarantines both adjacent control groups; unresolved foul actor/defense attribution and rebound control conflicts also make subsequent affected cumulative counts missing. Their missing targets propagate through subsequent history windows. These groups have `foul_indicator=None`; `counted_foul_action_numbers` remains an inspectable provisional event classification. `defense_counted_fouls` tracks this research classification, not official team-penalty state or bonus eligibility.

End of input does not establish end of game. Without a period-end marker, the final group has `complete=False`, `boundary_reason=input_exhausted`, `provisional_final_possession` and a missing target, even when its last row is a made shot. An appended and-one or continuation could change that group. A period-end marker establishes only the observed period boundary, not whole-game completeness or schedule coverage.

## Feature availability

`start_action_number` is the first retrospective member of a group. It is distinct from `start_state.reference_action_number`, which names the prior recorded event. The start state snapshots scores and counted-foul history before processing the new group's event; at a period transition its clock is the regulation/OT period length. Missing initial scores stay missing. Missing period-start evidence or an unresolved foul classification makes affected cumulative counts missing, rather than zero; unknown classifications propagate into later history. The previous two indicators use global completed group order across periods.

This is a recorded-feed, before-event reference, not proof of a live prediction opportunity: offense identity and eventual boundaries derive from source events, and corrected feeds are retrospective. It does not assert that source control was observable before the reference event. No model eligibility follows from these snapshots. Unknown history remains missing, and before-state prefix values do not change when future suffix events are appended. Actual live-control timing and real-time source availability require separate evidence.

## Exact descriptive metric

`whistle_research.metrics.calculate_wmi(fouls, game_id=...)` requires a single explicitly identified game's binary integer sequence. Missing, nonbinary or floating-point inputs raise `ValueError`. Callers must establish completeness, eligible outcomes and single-game provenance; this function cannot detect concatenation hidden under a fabricated ID.

The metric uses global two-group past/future windows, crosses period and team boundaries and truncates at game edges: `L=any(previous two F)`, `N=any(next two F)`, `M=F*(1+N)`. The result retains row values, exact integer group counts, sums, foul counts and follow-up counts. Rational arithmetic computes ratios before float serialization. Empty groups, zero baseline and empty conditional foul support produce missing values with specific reason codes. WMI can equal zero even when the continuation conditional is undefined. No imputation, smoothing, pseudocount or uncertainty interval is applied. Future `N` is retrospective and cannot be a predictor.

## Evidence and remaining gate

Handwritten tests cover rebounds, and-one, ordinary and retained-ball free throws, offensive fouls, technical ownership, jump control, periods, exact event accounting, future suffix invariance and a saved opening-feed fixture. Exhaustive binary sequences through length eight verify the legacy windows and factorization. These checks establish implementation behavior only. Independent footage audit, season-specific special-rule adjudication, full-game coverage verification and the research protocol's release gates remain outstanding.

Review correction (2026-11-02): paired offensive-foul/turnover rows represent one loss, and attribution/control conflicts must propagate uncertainty beyond the row where detected. Three failing regressions established these defects before correction.
