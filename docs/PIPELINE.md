# Development pipeline and conditional promotion

Date: 2026-11-02. Version: `development-research-report-v1`. A completed diagnostic run is **not** a completed research rewrite, independent reconstruction validation or publication approval.

## One-command development run

The project environment runs the entire development workflow. Paths default to the pinned source manifest/cache, six historical metadata files, and independently cross-checked `research/rewrite_completion_2026_11_02/schedule_expected.json`. No network acquisition or tolerance selection occurs. Output must be a new directory.

```sh
.venv/bin/python -m whistle_research.pipeline --output output/v2/NEW_DEVELOPMENT_RUN
```

Without reuse options, this verifies all source bytes, builds the schedule-bound inventory, runs full current-parser reconciliation, streams the full feature/provenance export, prepares a parser-bound random/enriched audit packet, evaluates the honest empty-review/unfrozen-tolerance gate, executes synthetic mathematical/model demonstrations, and writes the structured report and manuscript draft. Full archive parsing can take substantial time; it is unnecessary when already verified current artifacts exist.

Reuse is explicit, with no silent fallback to stale data:

```sh
.venv/bin/python -m whistle_research.pipeline --output output/v2/NEW_REUSED_DEVELOPMENT_RUN --reuse-inventory output/v2/source-inventory-independent-2026-11-02/inventory.json --reuse-reconciliation output/v2/reconciliation-v7-reviewed-2026-11-02/report.json --reuse-features output/v2/features-v7-reviewed-2026-11-02 --reuse-math research/rewrite_completion_2026_11_02/simulation_summary.json --reuse-models research/rewrite_completion_2026_11_02/model_demo_summary.json
```

Every run rehashes the raw source cache against the pinned manifest, verifies schedule/metadata hashes, complete game frames and current parser/feature hashes, checks reconciliation/source/game identities, and re-reads aligned feature/provenance JSONL streams. It recomputes exact JSONL byte hashes, canonical row-list hash, every per-game row/unknown count and total missing-field counts; group order, row/provenance IDs, metadata and source/action reference structure must agree. Emitted rows and quarantine statuses must also agree with the reconciliation; source-event counts must agree with the inventory. Stream verification uses memory proportional to game count, rather than materializing the million-row export. Synthetic artifacts must match current metric/simulation/model/evaluation source hashes, model specification and the declared seed. A validation failure exits 1 and cannot emit a completed report. Partial new outputs remain diagnostic failure artifacts; existing outputs are never replaced.

These checks establish byte/code/accounting consistency. They do not regenerate every derived fact when reuse is selected, authenticate external evidence, or prove possession/annotation truth. A replay without reuse regenerates the derived artifacts from the verified sources. Preserve both versions and explain any difference.

## Audit and report outputs

Defaults retain seed `20261102`, ten random games and the four previously nominated clock-anomaly cases. Sampling uses the complete unchanged source frame, so parser-bound plans preserve the original random/enriched game selection while acquiring fresh inventory/parser/plan bindings. `--sample-size`, `--seed` and repeated `--enriched-game-id` support an explicitly different diagnostic design; they never invent tolerances. Enriched overlap with random selection remains visible, and the random denominator remains unchanged.

The run writes `verification.json`, `inventory.json`, `feature_manifest.snapshot.json`, `stream_verification.json`, `audit_plan.json`, `audit_reviews.empty.json`, `audit_config.unfrozen.json`, `audit_gate.json`, `audit_readiness.json`, `synthetic_math.json`, `synthetic_models.json`, `report.json`, `report.md`, and `draft_paper.md`. Fresh runs also write full `reconciliation/` and `features/`; reuse references their original artifact paths and hashes. The snapshot manifest is a report snapshot, not a relocated export: rows remain at the cataloged original feature path. There are no invented reviewer identities, completed human records, footage annotations, confidence/tolerance values, meaningful gains or protocol freeze.

An expected `BLOCKED` audit is a successful software diagnostic outcome, not an exception. Thus exit 0 means the requested diagnostic workflow ran consistently; the JSON separately reports:

- `software_status: DEVELOPMENT_RUN_COMPLETE`.
- `scientific_status: BLOCKED`.
- `publication_status: NOT_AUTHORIZED`.

The stable report schema also contains `counts`, parser/feature `versions`, compact actual `audit` results, explicitly `SYNTHETIC_ONLY` mathematical/model summaries, artifact `{path,sha256,bytes}` records, limitations and required next evidence. Catalog paths are relative to the report directory; they may refer to deliberately reused artifacts outside that directory. Hashes bind those exact files. A website exporter must resolve them from that directory and preserve the scientific status. The report does not alter the legacy explorer or authorize public scientific claims.

The draft manuscript has real-methods development prose and explicit **NOT AVAILABLE / NOT EVALUATED / NOT CLASSIFIED** empirical result placeholders. It does not present synthetic output as basketball findings.

## Strict conditional promotion and real fitting

`release.prepare_promotion(...)` is the only adapter that creates a conditionally eligible manifest. It never edits the original provisional manifest. It calls the real `audit.check_gate(plan,reviews,config)`; a caller-provided status or eligibility flag cannot substitute for complete parser-bound evidence. The independent schedule hash and complete source frame must agree with the actual validated schedule IDs, date, season and game type. The canonical schedule loader rejects unknown statuses, duplicate IDs, missing exclusion reasons and absent independent provenance; malformed entries cannot be silently ignored. Raw source bytes, current parser/feature code, schedule/metadata, full rows and aligned provenance bytes are verified again.

Promotion requires the **entire** declared frame to be fully selected and reconstructed, with at least one row per game, complete games and row provenance, no unresolved row audit flags, no unresolved critical issues, and all targets known. Every row flag must be a nonblank string; any flag blocks promotion because no independent flag-resolution adapter exists. Game issue records must be explicit and well formed; every blocking issue other than `independent_audit_required` blocks, and `unassigned_control_events` must explicitly be false. The sole audit-required exception is discharged only by the genuine passing independent gate, never a manual ledger toggle. No quarantine, unknown target, missing or pilot-unselected game may be removed to manufacture eligibility. Original manifests must still have `eligible=false`; manually flipped inputs fail. Passing independently reviewed sample evidence remains conditional on truthful outside attestations and the declared sampling assumptions; it is not authenticated ground truth or blanket publication approval.

Only after those conditions pass does the adapter construct a distinct `conditionally-audited-feature-dataset-v1` manifest with eligibility true, exact plan/review/config bindings, original-manifest hash and promotion implementation hash. The parser's original `eligible=false` objects and saved release files remain intact. Every standalone real API and CLI also calls `release.validate_promoted_dataset`: it regenerates the conditional manifest from the actual original provisional files and genuine audit evidence, then requires exact equality. A hand-constructed eligible/promoted dictionary cannot bypass this authoritative path. Original feature/source/schedule/metadata locations are recorded as portable `promotion_inputs`. Existing `modeling.fit_real` then separately enforces frozen feature/model/evaluation code, row hashes, chronological split, genuine unused-cohort/exposure evidence, positive meaningful gain and every remaining protocol rule. Passing the audit cannot lock the protocol automatically.

The separate CLI route accepts externally supplied evidence; it does not create reviews, freeze decisions or infer values:

```sh
.venv/bin/python -m whistle_research.pipeline promote --features output/v2/AUDITED_FULL_EXPORT --audit-evidence research/FROZEN_AUDIT/evidence.json --protocol research/FROZEN_PROTOCOL/protocol.json --output output/v2/NEW_CONDITIONAL_FIT
```

The audit evidence file contains actual `plan`, `reviews`, `config`, and timezone-aware `evaluation_started_at`. The protocol follows [MODELING_CONTRACT.md](MODELING_CONTRACT.md). Source/cache/schedule/metadata options can override the portable defaults. All gates and the actual fit must succeed before any promotion output directory is created. On success, new `promoted_dataset.json`, `evidence.json`, `audit_gate.json` and `model_result.json` retain the complete bindings. On refusal, stdout contains actionable `BLOCKED` JSON and exit status is 1. This is a conditional research fit, not authorization to publish.

The real fitting API currently materializes supplied rows, so future million-row real fitting requires a capacity assessment or a separately reviewed bounded-memory learner. The current blocked dataset does not reach that allocation or model fitting through promotion. The development stream itself remains bounded-memory.

## Actual development result

The dated [pipeline_summary.json](../research/parser_followthrough_2026_11_02/pipeline_summary.json) identifies the current v7 run and hash-bound generated reports. Fresh full reconciliation and feature export used the frozen v7 parser; the final pipeline explicitly reused those outputs and the unchanged, source-bound synthetic summaries. It completed source/stream/accounting verification with:

| Quantity | Count |
| --- | ---: |
| Verified source files | 10 |
| Expected / observed games | 6,084 / 6,084 |
| Provisional reconstructed / quarantined games | 6,036 / 48 |
| Possession rows / unknown outcomes | 1,199,536 / 2,947 |
| Marker-complete games | 6,033 |
| Critical-unresolved games | 2,253 |
| Eligible games | 0 |
| Documented corrected schedule dates | 30 |
| Unresolved transfer / violation flags | 411 / 166 |
| Random / enriched audit cases | 10 / 4 |
| Completed independent reviews | 0 |

The scientific gate is **BLOCKED** with empty reviews and unfrozen tolerances; the model/evaluation protocol remains unlocked. No actual model was fit. Synthetic fixture tests demonstrate the functional positive promotion/fit path using clearly labeled test-only attestations and parameters; they supply no real audit evidence.

Candidate v7 separates source notes from live-state references without removing raw events. One narrow replay restoration and 35 note-only clock cases explain the newly reconstructed games; two notes that concealed actual non-note clock rises still quarantine. All 59 previously note-based references were checked automatically against their preceding source events in the final export. Increased transfer/unknown counts expose unresolved source conflicts under corrected jump/retained-ball semantics; they are not cleared to improve summary counts. The [run comparison](../research/parser_followthrough_2026_11_02/run_comparison.json) preserves v5, initial v6, reviewed v6 and v7 results. Earlier integration artifacts remain unchanged.

Focused checks:

```sh
.venv/bin/python -m pytest tests/v2/test_pipeline.py tests/v2/test_release.py -q
```

```sh
.venv/bin/ruff check src/whistle_research/pipeline.py src/whistle_research/release.py tests/v2/test_pipeline.py tests/v2/test_release.py
```
