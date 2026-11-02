# Candidate parser semantic changes

Date: 2026-11-02. Final parser: `canonical_candidate_v5`. Implementation diagnostics only. All games remain ineligible and independently unaudited.

The parser preserves original source order, clocks, labels, action numbers and raw JSON. It now distinguishes explicitly attributed kicked-ball violations, team delay records and corroborated awarded-basket companions. Nonblocking reason records explain supported categories; unresolved violations remain blocking. Exact personal-foul descriptors `clear-path` and `transition take` enter the existing retained-ball audit path. A later-clock ordinary defensive foul clears that prior entitlement.

`away-from-play` is audit-only: game `0022000018` actions 9/11/15/16 demonstrate that the archive uses this descriptor after an early-period made basket. Its spelling alone does not prove the formal special penalty. Game `0022000045` actions 323–332 exposed retained state incorrectly persisting into a later ordinary shooting-foul/free-throw sequence. Both regressions failed before correction and pass in v4/v5. No unrecorded free throw is created.

One source clock restoration is admitted conservatively: traveling at zero immediately followed by a supported replay request with exact raw value `Travel with time on the clock`, same period and opposite source offense. Game `0022000925` actions 337–339 records this pattern. Both recorded clocks remain unchanged; the blocking `source_clock_correction_requires_audit` reason identifies the earlier action and clocks. Before-state time remains a recorded reference, not independently verified live time. Other replay labels and administrative clock rises do not bypass quarantine.

## Primary evidence and limits

- [Official 2020–21 NBA rulebook](https://ak-static.cms.nba.com/wp-content/uploads/sites/25/2021/01/2020-2021-NBA-Rule-Book.pdf): Rule 10 IV distinguishes offense/defense kicks; Rule 11 supports awarded-basket procedure; Rule 12A II covers delay records; Rule 4 IV(h) limits formal away-from-the-play classification; Rule 5 III(a)(2) permits adding time when the whistle preceded zero. Retrieved bytes: 1,573,518; SHA256 `4b4ab0658bdb1c9f1cd589c8fcf87e81f3fa26ad2b890333dea53983aae6b65a`.
- [Official 2023–24 NBA rulebook](https://official.nba.com/wp-content/uploads/sites/4/2023/10/2023-24-NBA-Season-Official-Playing-Rules.pdf): Rule 12B X–XI distinguishes special foul categories, including transition take. Read through web PDF extraction; direct byte retrieval returned HTTP 403, so no byte hash is claimed.
- Immutable archived CDN event bytes and exact CSV-row references are bound by the diagnostic reports and companion JSON. Source descriptors are evidence of recorded categories, not independent rule adjudication.

These historical editions support narrow candidate distinctions. They do not establish every intervening season's rule edition, correct officiating, real-time feed availability, independent film accuracy or a scientific error rate. No confirmatory evaluation or public scientific claim is authorized by these changes.

## Diagnostic runs

The initial v3 all-game diagnostic exposed an overbroad off-ball descriptor mapping and persistent retained entitlement. V4 corrected those defects; v5 adds the narrow auditable source-clock pattern. Each report is retained in a distinct output directory; none overwrites a historical release. An interrupted pre-format attempt produced no report and is retained separately. The companion JSON records exact hashes, count deltas, remaining issue references and final verification.

## Final all-game result

Final report: `output/v2/reconciliation-semantics-v5-2026-11-02/report.json`. Parser SHA256: `6d6b481095e588f5346aeacea8799a7c6984b9f9b07d583c69a5df6a6d80f646`. Report hash and source/metadata bindings are in the JSON.

| Diagnostic | V2 | Final V5 | Change |
| --- | ---: | ---: | ---: |
| Observed games | 6,084 | 6,084 | 0 |
| Reconstructed | 5,999 | 6,000 | +1 |
| Quarantined | 85 | 84 | −1 |
| Candidate groups, all reconstructed | 1,193,332 | 1,193,032 | −300 |
| Candidate groups, common 5,999 games | 1,193,332 | 1,192,822 | −510 |
| Generic violation flags | 10,347 | 373 | −9,974 |
| Unexplained-transfer flags | 227 | 257 | +30 |
| Unknown-ownership flags | 116 | 83 | −33 |
| Eligible games | 0 | 0 | 0 |

The newly reconstructed game `0022000925` adds 210 candidate groups, retaining the blocking source-clock correction issue. Thus the all-game group change and common-game group change use different reconstructed denominators. V5 records 2,514 administrative delay reasons, 4,665 classified kick reasons, and 2,831 corroborated goaltending companions. These are category counts, not validated accuracy estimates. It retains 674 special retained-ball audit flags and 465 off-ball descriptor audit flags. The increased transfer count is reported without selecting a parser to minimize flags.

The 373 unresolved violation flags comprise lane, double-lane, jump-ball and unmatched goaltending rows. Remaining transfers include source actor/owner conflicts, same-clock foul/free-throw source-order contradictions, unpaired special outcomes and jump/rebound control questions. Exact action/CSV-row references and representative neighborhoods are retained in the JSON. No event is synthesized to fill these gaps. All remaining quarantines still fail closed on their recorded clock rises.

## Verification

The focused possession/reconciliation suite passed 76 tests. Ruff passed for the owned Python files. Regression tests cover retained raw events, exact accounting, supported and adversarial violations, special-descriptor uncertainty, later ordinary entitlements, previous-history missingness and before-state suffix invariance, plus supported/unsupported replay-clock patterns. Full project checks and independent implementation review are handled by the coordinating agent. No browser check is needed because no UI changed.

```sh
.venv/bin/python -m pytest tests/v2/test_possessions.py tests/v2/test_reconcile.py -q
```

Result: `76 passed`.

```sh
.venv/bin/ruff check src/whistle_research/possessions.py tests/v2/test_possessions.py
```

Result: `All checks passed!`.

```sh
.venv/bin/python -m whistle_research.reconcile --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv research/hypotheses_2026_09_12/cdnnba_2021_games.csv research/hypotheses_2026_09_12/cdnnba_2022_games.csv research/hypotheses_2026_09_12/cdnnba_2023_games.csv research/hypotheses_2026_09_12/cdnnba_2024_games.csv research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --output output/v2/reconciliation-semantics-v5-2026-11-02 --limit-per-source 0
```

Result: `{"diagnostic_games": 6084, "eligible_games": 0, "independent_audit_status": "blocked", "ok": true}`. Use a new output directory to repeat.
