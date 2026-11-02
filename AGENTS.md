# NBA whistle research

## Product and scope

Python research pipeline and a static HTML/CSS/JavaScript game explorer. The v2 rewrite prioritizes a defensible recorded-foul prediction study, one traceable dataset, and an independently audited possession reconstruction. The existing WMI release remains a retrospective descriptive benchmark.

## Read first

Read this file, `STATUS.md`, and the task-relevant sections of `docs/RESEARCH_PROTOCOL.md` and `docs/REWRITE_PLAN.md`. For legacy formula or interpretation work, read `PROJECT/Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`. Read only the implementation and tests needed for the task. This reading order supersedes the older requirement to reread every PROJECT file before every action.

## Layout

- `src/whistle_research/`: versioned v2 library and command-line tools.
- `tests/v2/`: offline contract, reconstruction, provenance, and mathematical tests.
- `scripts/`: reproducible setup/check commands.
- `docs/`: research protocol, decisions, data contracts, and rewrite gates.
- `PROJECT/`: historical formal definitions and project log; its folder-local naming rules still apply.
- Root Python scripts and `research/`: legacy analyses and releases, preserved for comparison.
- `index.html`, `site.js`, `styles.css`, `site-data/`: current public explorer.

## Work and verification

- Work on `codex/` branches, open small PRs, and do not merge or deploy without a user request.
- Preserve user changes and historical release artifacts. New runs use a new output directory and never overwrite existing release files.
- Keep paths portable. No embedded home directories, `/tmp`, secrets, paid-service assumptions, or large new frameworks.
- Use the project `.venv`. Pin dependencies and record environment/source/parser versions with results.
- Run `.venv/bin/python scripts/check.py` before committing a completed change. It must cover maintained Python lint, all Python tests, website unit tests, and package build. Run targeted checks while developing.
- Visible UI changes additionally require one focused browser check. No UI change means no browser sweep.
- Report commands, results, and unverified work. Passing implementation tests does not establish scientific validity.

## Scientific rules

- Keep raw events immutable, with hashes and provenance. Record missing, excluded, ambiguous, and failed observations explicitly.
- Never silently substitute a parser, cohort, missing outcome, corrected feed, or percentile reference set.
- Preserve the legacy WMI equation and global truncated windows. Any alternative definition has its own version and specification.
- Prediction features must be available at the declared possession start. Current outcomes and future windows are prohibited as predictors.
- Predict recorded calls. Do not infer call correctness, referee intent, or causality from play-by-play associations.
- No confirmatory model evaluation or new public scientific claims until the independent reconstruction audit gate passes. Synthetic fixtures and parser agreement are not independent film validation.
- Tests and review must fail closed on unverified source hashes, unknown eligibility, unresolved critical parsing problems, or incomplete required audit evidence.
- Do not choose meaningful-effect thresholds or revise analysis specifications after examining protected evaluation outcomes.

## Subagents

Use Sol implementers for scoped code and Sol default agents for independent review; use Luna scouts only for bounded read-only inventory. Do not use Astra outside the main chat. Give each agent exclusive file ownership, applicable checks, and return requirements. Agents are not alone in the codebase and must preserve others' edits. Wait for all agents and independently verify a key check before reporting their work complete.

## Documentation

Record changed decisions with date and reason in `docs/DECISIONS.md`. Update `STATUS.md` at milestones, not routine fixes. Keep the rewrite gates honest: implemented, automated-verified, independently validated, and published are different states.
