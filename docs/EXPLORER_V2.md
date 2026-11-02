# Research explorer v2

2026-11-02: An additive development notebook at `v2/`; the root explorer remains the legacy public baseline. Its job is to explain the prediction question and show what evidence is still missing, without presenting development diagnostics as a scientific release.

## Design plan

- Palette: notebook white `#ffffff`, cool paper `#f3f6fa`, navy ink `#18304c`, cobalt `#245ac4`, muted slate `#52647a`, evidence amber `#8b5100` on `#fff1d4`.
- Type: Avenir Next for readable research prose, Franklin Gothic Medium for the question and section titles, system fallbacks. Left aligned; short paragraphs.
- Layout: a quiet fixed notebook contents column and a broad evidence column. The memorable device is a connected possession/evidence line, rather than a score dashboard.

```text
Contents | Does foul history improve prediction?
         | [Development complete / scientific gate blocked]
         | Sources — possessions — independent audit — models
         | Data ledger / simulation workbench / audit / provenance
```

Review against the brief: a hero statistic would imply success, so the opening is a question followed by explicit gate status. Cards are reserved for the selected simulation's outputs; the rest uses tables, a process line and expandable evidence. No animated decoration or external fonts.

## Data contract and reproduction

`data.json` uses `research-explorer-v1`: `report` (development research report), `math` (synthetic mathematics summary), `models` (synthetic model demonstration), optional `footage`, and `input_files` with local input byte hashes. No missing values become zero. The exporter reads each input once and hashes the exact bytes parsed; it refuses an existing output directory. The required `math` and `models` roles must match the SHA-256 and byte counts in `report.artifacts`; the exporter resolves and verifies those bound files relative to the report directory before compacting any payload. Copied inputs are accepted only when their raw bytes match the report binding. The input hashes identify bytes, not independent scientific validation.

```sh
.venv/bin/python scripts/export_v2_site.py --report research/RUN/report.json --math research/RUN/synthetic_math.json --models research/RUN/synthetic_models.json --output research/NEW_EXPORT
```

Copy the generated `data.json` to `v2/data.json` only after reviewing the run. Serve the repository with a local HTTP server; direct file opening cannot reliably fetch JSON. All report strings are rendered as text. Links accept HTTPS/HTTP or local relative paths only. Model evaluation row IDs are omitted from the compact browser payload; source artifacts retain the complete record.

## Verification

`node --test tests/test_v2_site.cjs` tests missing values, blocked classification, safe links, SVG coordinates and report-schema rejection. `.venv/bin/python -m ruff check scripts/export_v2_site.py` checks the exporter. The main task also runs the full repository check and a focused browser check. Synthetic simulations/model fits are implementation demonstrations; empirical evaluation remains behind the independent audit gate.
