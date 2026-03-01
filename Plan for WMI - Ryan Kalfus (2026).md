# Plan for WMI - Ryan Kalfus (2026)

_Overview file (single source of truth for project plan)._ 

## Goal
- Measure whether NBA whistles show short-term momentum across possessions.
- Build a clear possession-level framework that avoids overlap/double-counting.
- Current stage: raw WMI first, controlled model second.

## Core Question
- If there is a defensive foul on a possession, how does that connect to nearby foul patterns?
- Is there measurable whistle dependence across possessions?

## Scope
- Season target: 2025-26 regular season.
- Current implementation: one-game prototype (OKC vs MIL), then scale.
- Unit of analysis: possession.

## Data and Tools
### Data Source
- Official NBA live play-by-play JSON (NBA CDN).

### Tools
- Python
- pandas
- NumPy
- statsmodels (planned for controlled stage)

## Possession Workflow
1. Build possession-level rows from play-by-play.
2. Identify defensive foul occurrence by possession.
3. Create WMI variables `L_t`, `F_t`, `N_t`, `M_t`.
4. Compute game-level raw WMI.
5. Later add controlled model and compare raw vs controlled.

## Variable Definitions (Current)
- `L_t = 1`: at least one defensive foul in the last 2 possessions, else `0`.
- `F_t = 1`: defensive foul on current possession, else `0`.
- `N_t = 1`: at least one defensive foul in the next 2 possessions, else `0`.
- `M_t = F_t(1 + N_t)`.

## Last/Next Window Rule (Current)
- `last2` and `next2` are global possession windows.
- No offense/defense-team filtering for these windows.
- Windows are based only on game possession order.

## Unified Raw WMI Equation
- `WMI_rawgame = [ (1 / n1) * ∑_(t: L_t=1) M_t ] / [ (1 / n0) * ∑_(t: L_t=0) M_t ]`
- `n1`: number of possessions where `L_t = 1`.
- `n0`: number of possessions where `L_t = 0`.

## Controlled WMI (Planned)
- Logistic form: `logit(P(def_foul_t=1)) = a + b*trigger_t + controls`.
- Controlled index: `WMI_controlled = exp(b)`.
- Planned controls include game context (time left, score difference, etc.).

## Diagnostic Layer (Planned)
- Compute one game-level WMI value per game.
- Across games, compute z-scores to flag outlier games.
- Use z-scores as diagnostics, not stand-alone proof.

## Current Output Files
- `possession_model_table_okc_mil.csv`
- `def_foul_context_okc_mil.csv`
- `wmi_rawgame_breakdown_okc_mil.csv`

## Project Naming Update
- 03.01.2026: Project folder renamed to `nba-whistle-project` and path checks passed.
- 03.01.2026: Codex project path mapping was updated to the renamed folder `/Users/ryankalfus/Downloads/nba-whistle-project`.
- 03.01.2026: Recoverable NBA/whistle chats were re-mapped to this folder path in local Codex state.
- 03.01.2026: Local ghost thread references (deleted IDs) were cleaned so only real loadable threads remain in the sidebar state.
- 03.01.2026: Recoverable NBA thread session files were patched so their embedded `cwd` points to this folder path (hyphen version).
- 03.01.2026: Codex active workspace root and thread ordering state were reset to prioritize this project and its recoverable thread IDs.
- 03.01.2026: Project folder moved to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project` and old path `/Users/ryankalfus/Downloads/nba-whistle-project` kept as a symlink so existing Codex threads remain attached to this project path.
- 03.01.2026: Re-ran chat-restore metadata sync so whistle project thread records, workspace roots, and recoverable session metadata all resolve to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`.
- 03.01.2026: Final restore pass updated Codex local workspace roots and remaining thread `cwd` values so all whistle threads resolve to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`.
- 03.01.2026: Final restore pass safety backups were created first: `~/.codex/.codex-global-state.json.pre_restore_move_fix_20260301_171034` and `~/.codex/state_5.sqlite.pre_restore_move_fix_20260301_171034`.
- 03.01.2026: Final compatibility alignment set all whistle thread `cwd` values to Codex’s current project-root string `/Users/ryankalfus/Downloads/nba-whistle-project` (symlink target remains `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`).
