# Audit handoff — 2026-11-06

Status: **prepared, not independently validated**. Zero completed human reviews, zero continuously verified full games and zero eligible games. No real model was fit. The parser remains `canonical_candidate_v7`; current saved evidence does not justify another semantic repair.

## Selected design and scoped freeze

The user delegated the tolerance recommendation. The research lead selected a **1% maximum game-level material-error rate at 95% one-sided confidence**, a policy judgment for research credibility. Under the declared binomial game model, the zero-error upper bound is `1 - 0.05**(1/n)`. With 299 random games it is 0.9969%; with 298 it exceeds 1%. See the [NIST exact-binomial reference](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm). This does not treat individual possessions as independent trials.

The reproducible selection has **299 random + 4 separate enriched = 303 unique games**, seed `20261106`, from the unchanged 6,084-game frame. The original fourteen-game development pilot remains intact. One new random game and all four enriched games overlap that pilot; this is disclosed development exposure, not unused confirmatory evaluation data. Do not substitute accessible games, change tolerance after errors or add observations to rescue a failed design.

- [design.json](design.json): immutable selection-stage receipt, still labeled `DESIGN_SELECTED_FREEZE_PENDING` because it predates the later freeze.
- [selected_games.json](selected_games.json): compact selected-game ledger, including coordinator-only strata and rationale.
- [audit_config.frozen.json](audit_config.frozen.json): later scoped freeze at `2026-11-06T16:29:07.465251+00:00`, binding the actual plan, packet manifest and reviewer contract while all 606 forms were empty.
- [audit_gate.blocked.summary.json](audit_gate.blocked.summary.json): compact summary, **not a gate input**; retains the full ignored report's byte descriptor.
- [handoff_summary.json](handoff_summary.json): actual packet counts, hashes, verification and empty-collection receipt.

This local dated freeze is not authenticated external registration. It freezes only the audit sampling/tolerance and actual packet/protocol. Full-study preregistration, meaningful predictive gain and genuinely unused evaluation data remain separate, unresolved requirements.

## Actual local handoff

The complete ignored packets are under these repository-relative paths:

| Packet | Games | Empty forms | Raw events per reviewer |
| --- | ---: | ---: | ---: |
| `output/v2/reviewer-handoff-pilot-2026-11-06/` | 14 | 28 | 7,715 |
| `output/v2/reviewer-handoff-audit-2026-11-06/` | 303 | 606 | 169,300 |

Both delivered A/B manifests, protocols, instructions and raw ledgers were independently hash checked. The 303-game packet's two ledger sets total 670,490,910 bytes. Raw source dictionaries and unique archive-member/CSV-row references are preserved. No parser reconstruction, selection strata, anomaly rationale or fitted score is supplied in either standalone reviewer directory. Original feed ownership fields remain visible, an explicit blinding limitation.

The original dated League Pass observations establish playback access for fourteen pilot games, with only three midpoint seeks. Only **five** games in the larger selection overlap that historical snapshot embedded in the frozen kits. The later [303-game access run](../audit_access_2026_11_06/README.md) now records successful official Full Games opening checks for every selected assignment. Supply its separate [reviewer access addendum](../audit_access_2026_11_06/playback/reviewer_access_addendum.json) to both reviewers alongside their own unchanged kits; the addendum does not change frozen packet bytes or transfer account access. Keep the coordinator catalog, raw snapshot and sampling details separate. No stream was watched continuously for this handoff; no footage download, redistribution or account/session material is included.

## Review and collect

1. Give actual reviewer A only `reviewer_A/`, and actual reviewer B only `reviewer_B/`. Keep the coordinator manifest, this design/rationale and the other reviewer's labels separate. Follow the frozen [review contract](../../docs/REVIEWER_GUIDE.md) and each kit's `INSTRUCTIONS.md`.
2. Each distinct human independently watches every assigned full game and completes their own original files. Record every raw row as a possession or explicit exclusion, exact foul attribution, full before-event prediction context, period coverage and footage references. Preserve uncertainty, source omissions and failed access; templates and AI output are not human labels.
3. Preserve both original submissions. Any row-level disagreement requires a separate complete `adjudications/<game_id>.json`, with a distinct adjudicator and rationale bound to both original file hashes. A favorable adjudication cannot erase an original material discrepancy.
4. Collect into a **new** directory. This reads files and derives descriptors; it does not create identities, labels, coverage or evaluation timestamps.

```sh
.venv/bin/python -m whistle_research.review_evidence collect --evidence-root output/v2/reviewer-handoff-audit-2026-11-06 --config research/audit_handoff_2026_11_06/audit_config.frozen.json --output output/v2/NEW_REVIEW_COLLECTION
```

Collection writes `reviews.json`, `audit_evidence.json`, `evidence_validation.json` and `collection_report.json`. The bundle declares its evidence root relative to its own file directory. `pipeline promote` resolves that declaration; direct API consumers must resolve it themselves. Originals stay untouched and failed submissions remain explicit.

The actual empty collection at `output/v2/reviewer-handoff-empty-collection-2026-11-06/` returns exit 1, **BLOCKED**, zero completed game entries and 606 failed submissions. Reasons include `explicit_human_reviewer_required` and `metadata_audit_gate_blocked`. The metadata gate separately reports `missing_selected_game_reviews` and `random_error_bound_unavailable`. Missing evidence is not an implementation failure to bypass.

Structural intake alone cannot authorize promotion. Production reparses bound raw sources, verifies the export against that reconstruction, and compares all A/B/adjudicated labels with the candidate: opportunity count/order, nonadministrative grouping, teams, counted-foul references/outcomes and every prediction-start field. Both human files agreeing with each other cannot hide a parser mismatch. Files, hashes and timestamps establish consistency; they do not authenticate people or film truth. [Pipeline requirements](../../docs/PIPELINE.md) also retain full-frame completeness, unresolved-issue and separate real-model protocol gates.

## Reproduction

Existing output directories are never overwritten. Verified cache inputs and the pinned development artifacts must exist; acquisition is described in [DATA_CONTRACT.md](../../docs/DATA_CONTRACT.md).

```sh
.venv/bin/python research/audit_handoff_2026_11_06/prepare_design.py --output output/v2/NEW_AUDIT_DESIGN
```

The actual design replay was byte-identical for `audit_plan.json`, `design.json` and `selected_games.json`. Packet construction verifies the selected immutable source archives before emitting raw ledgers:

```sh
.venv/bin/python -m whistle_research.review_packet --plan output/v2/NEW_AUDIT_DESIGN/audit_plan.json --source-manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --protocol docs/REVIEWER_GUIDE.md --access research/cross_feed_2026_11_05/league_pass_access.json --output output/v2/NEW_REVIEW_PACKET
```

A newly generated packet is a new preparation artifact. The existing freeze binds the existing actual packet's exact bytes, not an arbitrary regenerated packet. Re-version and record any changed instructions, plan or packet before independent work begins; do not relabel the earlier receipt.

## Verification

The Sol independent reviewer closed the earlier actual-file and parser-comparison gaps: 147 focused tests and targeted Ruff passed. A direct production probe with mutually agreeing but wrong human start context was refused. The parent separately verified all delivered actual kits, their blank forms and collector-to-promotion CLI path resolution. `.venv/bin/python scripts/check.py` passed **634 Python tests**, maintained lint, both website suites and wheel build/isolated installation. The design script's separate Ruff check also passed. The local log is `output/v2/reviewer-handoff-final-checks-2026-11-06.log`.

Remaining work is real full-game coverage, **606 independent human submissions**, adjudication and actual error-bound evaluation. Parser repairs discovered by that audit require a new version and fresh applicable validation. Full-study/evaluation decisions and any empirical publication remain blocked.
