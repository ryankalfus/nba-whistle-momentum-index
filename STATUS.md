# Status

## Current work

Research-first v2 rewrite authorized on 2026-11-02. The legacy research release and website remain the public baseline. Implementation is in progress; no new research result has been validated or published.

| Stage | State | Release gate |
| --- | --- | --- |
| 1. Protocol and environment | Implemented; independently reviewed; local checks and Linux CI passed | PR #2 open |
| 2. Source inventory | Implemented; independently reviewed; ten sources verified / 6,084 observed games | Independent expected-game schedule still required |
| 3. Canonical reconstruction | Candidate implemented and independently code-reviewed; all 6,084 games diagnosed | Semantic/clock flags and independent accuracy audit unresolved; zero eligible games |
| 4. Independent audit | Pending | Reviewed sample, uncertainty, critical-error adjudication |
| 5. Descriptive mathematics | Exact legacy components, missingness and exhaustive short-sequence checks implemented | Broader process simulations and uncertainty validation remain pending |
| 6. Stronger matched models | Blocked by audit | Past-only features, matched evaluation design |
| 7. Locked evaluation | Blocked by audit and protocol lock | Unused evaluation cohort and frozen procedure |
| 8. Paper and explorer | Pending | Validated release, generated results, accessible provenance |

## Milestones

- 2026-11-02: Ran canonical-candidate diagnostics across all 6,084 archived games: 5,999 reconstructed and 85 quarantined; 5,029 reconstructions withheld WMI because of ambiguity/incomplete evidence, and 970 had an arithmetic candidate score only. No game is independently validated or eligible for modeling. Matched counts against both historical reconstruction outputs are recorded in the dated reconciliation summary. Review fixes cover paired offensive-foul/turnover records, propagated uncertainty, partial games, unassigned events and explicit CSV failure accounting.
- 2026-11-02: Verified the source ledger against all ten archived inputs and inventoried 6,084 games across six declared cohorts. Source-mutation, malformed-schedule and truncated-archive regressions are covered; 27 focused tests pass. Inventory coverage is explicitly observed-only, not proof of complete seasons. Foundation PR #2 passed Linux CI.
- 2026-11-02: Implemented the pinned Python 3.14.7 environment, package/isolated-wheel checks, active project guide, and development protocol. Independent Sol review corrected unsafe legacy regeneration examples in the README. Local package checks pass; this milestone does not certify the data or scientific results.
- 2026-11-02: Authorized the research-first rewrite. Current inspection verified 6,084 saved validation games / 1,208,809 possession rows, all ten source-file hashes, and the existing website unit checks. The separate hypothesis study reports 6,080 games / 1,225,902 groups; reconciliation remains necessary. Existing intervals and retrospective prediction claims are not promoted into new evidence.
