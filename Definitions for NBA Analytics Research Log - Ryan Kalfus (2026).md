# Definitions for NBA Analytics Research Log - Ryan Kalfus (2026)

## Core Possession Rule
- One possession = one team controls the ball in live play.
- A possession ends when control changes to the other team, or the period ends.

## Critical Project Rule (Important)
- **Offensive fouls end possessions.**
- **Offensive fouls do NOT count as defensive fouls for this project.**

## Possession Starts
- Team controls opening tip.
- Team gains control after opponent made FG or final made FT.
- Defensive rebound.
- Steal/turnover that gives control.
- Jump ball won with clear control.
- Start of period when first team gains control.

## Possession Ends
- Made field goal.
- Offensive foul by offense (charge, illegal screen, etc.).
- Offensive turnover/violation by offense.
- Defensive rebound by opponent after miss.
- Opponent wins jump ball control.
- End of period.
- Final free throw sequence where control goes to opponent.

## Possession Continues (No New Possession)
- Defensive foul where offense keeps/retains ball.
- Free throws from defensive fouls.
- Offensive rebound by same offense.
- Timeouts, substitutions, reviews, dead-ball admin (if control does not change).
- Technical FT events that do not change who gets next live-ball control.

## Defensive Foul Metrics

### `defensive_foul_count`
Count only fouls where:
- `actionType == "foul"`
- foul team is defending team for that possession
- `subType` is not `offensive`, `technical`, or `double technical`

### `defensive_foul_teams`
- Team code(s) that committed defensive fouls in that possession.
- Pipe-separated if multiple values appear.

## Code Mapping (Current Parser)
- Ownership anchor: NBA live feed `possession` field.
- One possession row per continuous segment of same `possession` team.
- `start_time`: end time of previous possession (continuous possession timeline across full game).
- `end_time`: final live-ball event in that same possession segment.
- This means after an offensive foul ends possession `t`, possession `t+1` starts immediately at that foul sequence time.
- If multiple events share same clock timestamp, parser adds `+0.001` sequence offsets to preserve event order.

## Current Step Output (Defensive Foul Context Rows)
- File: `def_foul_context_okc_mil.csv`
- Each row is one defensive foul event.
- `last2` / `next2` are global possession windows (team-agnostic):
  - `last2` = previous two possessions in game order.
  - `next2` = next two possessions in game order.
- Columns:
  - `def_foul_num`: sequential defensive foul event number in game order.
  - `offense_team`: offensive team tricode on the foul event row.
  - `defense_team`: defensive team tricode (team committing the defensive foul).
  - `seconds_left_in_game`: game seconds remaining at that foul event.
  - `score_difference`: offensive team score minus defensive team score at that foul event.
  - `def_foul_called_in_last2_possessions`: `1` if at least one of the previous two possessions had a defensive foul.
  - `def_foul_called_in_next2_possessions`: `1` if at least one of the next two possessions has a defensive foul.
  - `L_t`: same value as `def_foul_called_in_last2_possessions`.
  - `F_t`: always `1` in this file (because each row is a defensive foul event).
  - `N_t`: same value as `def_foul_called_in_next2_possessions`.
  - `M_t = F_t + F_t*N_t` (in this file this equals `1 + N_t`, so values are `1` or `2`).

## Z-Score Layer (Planned Diagnostic)
- Keep possession-level `WMI_raw` as the primary current metric.
- For each game, compute game-level `WMI_rawgame` from possessions in that game.
- Across all games, compute:
  - `mean_game_wmi_raw`
  - `std_game_wmi_raw`
  - `wmi_raw_z_score = (game_wmi_raw - mean_game_wmi_raw) / std_game_wmi_raw`
- Use `wmi_raw_z_score` only as an outlier/flagging metric, not standalone proof of ref bias.

## Controlled WMI Note
- Future `WMI` will be controlled (regression-based), not raw.
- Gist: it will adjust for context variables and isolate trigger effect.
- Interpretation target: above `1` means higher adjusted foul odds, below `1` means lower adjusted foul odds.
- Exact final `WMI` equation is not defined yet.

## All-Possession Modeling Table (Current)
- File: `possession_model_table_okc_mil.csv`
- Each row is one possession.
- Variables:
  - `L_t`: foul in the last 2 possessions (0/1)
  - `F_t`: foul on current possession (0/1)
  - `N_t`: foul in the next 2 possessions (0/1)
  - `M_t = F_t + F_t*N_t` (values 0/1/2)
- Additional context columns:
  - `seconds_left_in_game`
  - `score_difference`
  - `offense_team`, `defense_team`

## WMI_raw Game Formula (Current)
Use this exact formula:
WMI_rawgame = [ (1 / n1) * ∑_(t: L_t=1) M_t ] / [ (1 / n0) * ∑_(t: L_t=0) M_t ]

Notes:
- This is one whole-game value.
- This is currently raw WMI only (no controls yet).
- `n1` = count of possessions with `L_t = 1`.
- `n0` = count of possessions with `L_t = 0`.
- Current definition supersedes older relevant-team last2/next2 definitions.

## Metric Naming (Current vs Future)
- `WMI_raw` = current implemented metric (equation above).
- `WMI` = future controlled metric from logistic regression, with final equation still TBD.

## Season-Level WMI_raw (Pooled)
- Same formula as game-level raw WMI, but computed on one combined possession table across all season games.
- 03.01.2026: Added 2024-25 season calculator script `calculate_wmi_rawseason_2024_25.py`.
- 03.01.2026: Latest 2024-25 pooled result: `WMI_rawseason_pooled = 0.978645` using `1230` regular-season games.
- 03.01.2026: Added 2025-26 as-of summary file `wmi_rawseason_2025_26_summary_asof_2026_03_01.csv` with `WMI_rawseason_pooled = 0.949847` using `896` completed regular-season games as of 03.01.2026.
- 03.01.2026: Renamed compact tracker file to `wmi-calculations-log.md` for top-line `WMI_raw` values and output-file mapping.
- 03.01.2026: Clarified `WMI_raw` vs future `WMI` distinction in this definitions file.

## Project Naming Update
- 03.01.2026: Folder path is now `/Users/ryankalfus/Downloads/nba-whistle-project` (renamed from `nba_whistle_project`).
- 03.01.2026: Codex workspace root for this project was re-linked to `/Users/ryankalfus/Downloads/nba-whistle-project`.
- 03.01.2026: Recoverable NBA/whistle thread records were normalized to this exact path so they resolve under the current project.
- 03.01.2026: Stale deleted thread IDs were removed from local Codex UI state to prevent false “directory moved or deleted” ghost entries.
- 03.01.2026: Session `.jsonl` metadata for recoverable NBA threads was path-normalized so stored `cwd` now matches this project path.
- 03.01.2026: Codex workspace-state metadata was normalized so the active workspace root is this folder and NBA thread order is prioritized in sidebar state.
- 03.01.2026: Physical project location moved to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`, while `/Users/ryankalfus/Downloads/nba-whistle-project` is now a symlink to preserve existing Codex thread/project path expectations.
- 03.01.2026: Current restore pass re-confirmed metadata normalization to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project` across thread DB rows, workspace root state, and session metadata for recoverable NBA threads.
- 03.01.2026: Final restore pass updated remaining old-path thread metadata in `~/.codex/state_5.sqlite` and workspace roots in `~/.codex/.codex-global-state.json` so all project threads resolve to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`.
- 03.01.2026: Final restore pass used fresh safety backups first: `~/.codex/.codex-global-state.json.pre_restore_move_fix_20260301_171034` and `~/.codex/state_5.sqlite.pre_restore_move_fix_20260301_171034`.
- 03.01.2026: Final compatibility alignment set all project thread `cwd` values to `/Users/ryankalfus/Downloads/nba-whistle-project` (the current Codex project-root string), while that path remains a symlink to `/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project`.
