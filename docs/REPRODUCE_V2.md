# Reproduce the v2 development diagnostics

Date: 2026-11-02. These commands produce implementation diagnostics, not a validated research release. Run from the repository root after the locked environment is installed. Each output directory must be new; use another name when repeating a run. All paths below are portable repository-relative paths.

## Environment and checks

Use Python 3.14.7. Set `PYTHON` to a suitable interpreter when the default `python3.14` resolves to another version.

```bash
bash scripts/bootstrap.sh
```

```bash
.venv/bin/python scripts/check.py
```

The check command covers maintained lint, all Python tests, website unit checks, wheel building and installation outside the source tree. No website redesign is included in this stack, so no browser sweep is needed.

## Immutable source inputs

The historical source manifest is tracked; its raw cache is gitignored. A fresh checkout must acquire the exact declared bytes. Use the new explicit acquisition command, which checks existing files, verifies downloads before publishing them, and does not regenerate the manifest:

```bash
.venv/bin/python -m whistle_research.fetch --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --output output/v2/fetch-check
```

This is the only network step. Existing matching cache files are reused. Mismatched existing inputs are refused; preserve and investigate them instead of replacing evidence automatically. Do not run the old hypothesis runner's fetch path against a historical release because it regenerates that release's manifest.

```bash
.venv/bin/python -m whistle_research.sources inventory --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --output output/v2/source-inventory
```

Without an independent schedule, the result is `observed_only` / `unverified` even when every file verifies. `--schedule` and the format in `DATA_CONTRACT.md` provide explicit expected-game accounting; supplied schedule provenance still requires independent review.

## Candidate reconstruction and historical comparison

```bash
.venv/bin/python -m whistle_research.reconcile --manifest research/hypotheses_2026_09_12/source_manifest.json --cache research/hypotheses_2026_09_12/cache --metadata research/hypotheses_2026_09_12/cdnnba_2020_games.csv research/hypotheses_2026_09_12/cdnnba_2021_games.csv research/hypotheses_2026_09_12/cdnnba_2022_games.csv research/hypotheses_2026_09_12/cdnnba_2023_games.csv research/hypotheses_2026_09_12/cdnnba_2024_games.csv research/hypotheses_2026_09_12/cdnnba_po_2024_games.csv --output output/v2/reconciliation-pilot --save-games
```

The default selects the first three games per archive for diagnostics, not a random inferential sample. `--save-games` retains normalized events, groups, issues and CSV-row mappings for inspection. For all archived games, use another output directory and `--limit-per-source 0`; omitting `--save-games` avoids duplicating every event. Historical home/away metadata and possession counts are comparison inputs, not independent ground truth.

All results retain `eligible=false`. A descriptive candidate WMI requires explicit full-game markers, complete known outcomes, no unresolved control events and no blocking parser issues apart from the independent-audit requirement. Incomplete or ambiguous groups are not dropped to compute a score. Structural failures are quarantined with reasons. Clock corrections can be legitimate feed revisions, so a strict-clock quarantine does not prove corrupted data.

The dated `research/rewrite_2026_11_02/reconciliation_summary.json` also joins counts to the saved validation comparison on exactly the same successfully reconstructed game IDs. Source, parser, metadata, report and validation-reference hashes are included. Count changes do not establish greater accuracy.

## Manual audit pilot and blocked gate

```bash
.venv/bin/python -m whistle_research.audit plan --inventory output/v2/source-inventory/inventory.json --output output/v2/manual-audit-pilot --sample-size 10 --seed 20261102 --enriched-game-id 0022000181 --enriched-game-id 0022000254 --enriched-game-id 0022000925 --enriched-game-id 0022301177 --enriched-reason 'Historical study quarantined these source games for backward-clock anomalies; inspect source order and event corrections independently.'
```

This is a preparatory pilot, not a frozen final audit sample. The complete plan contains the sampling frame, source/parser hashes, 10 random games and four diagnostic nominations with reasons. The compact tracked summary is not a substitute for the full plan at gate evaluation. Frame/sample ordering is deterministic. Source changes, parser-code changes or plan changes require corresponding new evidence; do not rebind old annotations to new hashes.

The tracked `audit_config.draft.json` and `audit_reviews.empty.json` contain deliberately unset tolerances and no annotations. Their bindings match the dated pilot. An exact rerun on unchanged inputs produces the same plan hash. If it does not, retain the mismatch as a blocker rather than editing evidence to match silently.

```bash
.venv/bin/python -m whistle_research.audit gate --plan output/v2/manual-audit-pilot/plan.json --reviews research/rewrite_2026_11_02/audit_reviews.empty.json --config research/rewrite_2026_11_02/audit_config.draft.json --output output/v2/manual-audit-gate
```

Expected result now: exit status 1 and `gate.json` with `status=BLOCKED`. This is an intentional scientific gate outcome, not a failed implementation check. It lists missing independent schedule evidence, frozen tolerances/assumptions and reviews. Footage and reviewers are not arranged, as confirmed by the user on 2026-11-02.

Before collecting protected audit labels, choose sample size/error tolerances and record a genuine pre-review freeze. Two independent full-game reviewers provide evidence/annotation references, source bindings, start/completion timestamps and discrepancy labels. Agreeing labels need no third reviewer; disagreements require a distinct adjudicator, and any supplied adjudication is validated. Original labels are preserved. The exact game-level one-sided bound uses only the random stratum, not enriched cases. A conditional pass checks the evidence structure and declared assumptions; it does not authenticate external attestations or authorize model/publication gates automatically. See `AUDIT_PROTOCOL.md` and the `audit` module schema.
