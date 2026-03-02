# Plan for WMI - Ryan Kalfus (2026)

**This is not PURELY a LOG, do not use as a log to log each response**

## Goal
- Measure whether NBA whistles show short-term momentum across possessions.
- Build a clear possession-level framework that avoids overlap/double-counting.
- Current stage: `WMI_raw` first, future `WMI` (controlled logistic-regression version) second.

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
3. Create `WMI_raw` variables `L_t`, `F_t`, `N_t`, `M_t`.
4. Compute game-level `WMI_rawgame`.
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

## Metric Naming (Important)
- `WMI_raw` = current implemented metric (equation above).
- `WMI` = future controlled metric from logistic regression; exact final equation is not defined yet.

## Controlled WMI (Planned)
- Future `WMI` will come from a logistic-regression model with trigger + controls.
- Interpretation gist: higher than `1` means higher adjusted foul odds, lower than `1` means lower adjusted foul odds.
- Final exact `WMI` equation is still TBD.
- Planned controls include game context (time left, score difference, etc.).

## Diagnostic Layer (Planned)
- Compute one game-level `WMI_rawgame` value per game.
- Across games, compute z-scores to flag outlier games.
- Use z-scores as diagnostics, not stand-alone proof.

## Current Output Files
- `possession_model_table_okc_mil.csv`
- `def_foul_context_okc_mil.csv`
- `wmi_rawgame_breakdown_okc_mil.csv`
- `wmi_rawseason_2024_25_summary.csv`
- `wmi_rawseason_2025_26_summary_asof_2026_03_01.csv`
- `wmi_rawseason_2010_11_to_2023_24.csv`
- `wmi_rawseason_2019_20_recovery.csv`
- `wmi-calculations-log.md`

## Historical Season Coverage (Current Source)
- Requested historical range run: `2010-11` through `2023-24`.
- Oldest available season in this current NBA CDN play-by-play source for that range: `2019-20`.
- Computed seasons in that run: `2019-20`, `2020-21`, `2021-22`, `2022-23`, `2023-24`.
- 2019-20 note: current CDN endpoint returns unavailable status for many higher game IDs (for example `0021900668+`), so this source currently under-covers known played-game totals for that season.
- 2019-20 broader scan note: scanning full ID range `1..1230` in current source recovered `718` games; using played-game baseline `1059`, this is `games_missing = 341`.
- 03.02.2026 update: `wmi_rawseason_2010_11_to_2023_24.csv` was aligned to this same 2019-20 baseline (`games_succeeded=718`, `games_missing=341`).
