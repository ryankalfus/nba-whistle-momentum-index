# Retrospective exploratory run — 2026-11-08

The user authorized a provisional cohort, a separate exploratory model route and an updated local report/explorer. The declared [specification](specification.json) is saved before the first real fit. It uses already-exposed 2024–25 regular-season data, whole-game quality exclusions and fixed chronological partitions. No independent validation, eligibility, unused-cohort status, meaningful-gain threshold or public scientific finding is claimed.

Implementation and the planned specification are versioned. Actual selected rows, predictions, empirical metrics, reports and generated notebook data remain in ignored local output. Nothing is deployed and repository `v2/data.json` remains the earlier development payload. The strict promotion/real-fit APIs, parser, raw source archives, frozen historical audit and original AI annotations are unchanged.

See [EXPLORATORY_ANALYSIS.md](../../docs/EXPLORATORY_ANALYSIS.md) for the exact statistical, cohort, input-integrity and reproduction contract. This is not a revival of the 303-game campaign or a replacement full-game review quota. The plan is a local development declaration, not external preregistration.

## Actual execution

Tested implementation and the raw plan were checkpointed at `0a87c5596e83260cc830fb49953e17266d7a0cda` before the first actual fit. A cohort-only preflight and the later fitted run produced identical cohort ledgers. The run completed under `EXPLORATORY_ONLY_NOT_VALIDATED`; all original eligibility and approval flags remain false and the meaningful-gain classification remains `NOT_SPECIFIED`.

Local evidence, relative to repository root:

- `output/v2/exploratory-2026-11-08/before-first-fit.json`: timestamped code/plan/environment checkpoint and protected input hashes.
- `output/v2/exploratory-2026-11-08/preflight/cohort.json`: source-verified cohort ledger before fitting.
- `output/v2/exploratory-2026-11-08/analysis/`: unchanged first-fit plan snapshot, full cohort accounting, selected rows, aligned predictions, model result, report and artifact bindings.
- `output/v2/exploratory-2026-11-08/arithmetic-verification.json`: parent independent numerical replay and protected-byte check.
- `output/v2/exploratory-2026-11-08/notebook-complete/`: local notebook with the actual provisional result and final methods/handoff documentation.

[execution_receipt.json](execution_receipt.json) records opaque local artifact hashes and verification metadata, not empirical model-result values. The historical source/parser/feature exports, frozen audit and original annotations remain unchanged. The 303-game campaign remains inactive.

## Verification and limits

Independent Sol implementation review checked input/code/artifact bindings, every selected row against the original export, prediction identity/order, tuning-grid selection and all false approval flags. A separate NumPy replay reproduced losses, calibration and whole-game bootstrap arithmetic within `1e-14`. The parent separately replayed losses/Brier/bootstrap and verified protected bytes. Neither review retrained models independently or established reconstruction truth, interval coverage or scientific validity.

The first notebook export correctly refused JSON-equivalent synthetic inputs whose raw bytes differed from the base report's binding. The successful command uses the report's exact `synthetic_math.json` and `synthetic_models.json` files; no model was refit or parameter changed. Earlier bundles remain local history; `notebook-complete` includes the final handoff text, methods/navigation and readable comparison layout.

Final checks pass 955 Python tests, all 12 v2 website tests, legacy website checks, maintained lint, dependency integrity and the wheel build/isolated installation. The focused in-app check verified the provisional notice, model comparison, expanded cohort/partition/exclusion/unknown accounting, no horizontal page overflow and no console errors at 1280 × 720. Saved screenshots and browser observations remain local. The browser client blocked opening the linked Markdown methods document; all eleven bundle files, including that saved document, separately returned HTTP 200 with exact local bytes. This does not establish readable Markdown navigation in that browser.

The execution receipt records hashes for these artifacts and checks without model-result values. Actual outputs require the ignored original inputs; a fresh clone contains neither the fitted results nor their underlying local data. No model-result values are committed in this directory.
