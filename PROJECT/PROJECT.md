# PROJECT.md

## Purpose
- This is the main formal guide for the NBA Whistle Momentum Index project.
- This file merges the project plan, project-documentation rules, and agent working instructions into one place.
- Someone should be able to read only this `PROJECT` folder and understand the project scope, metric names, documentation rules, and working process.
- Files inside this `PROJECT` folder should not name files outside this folder.

## Before Any Action
- Read every file in the `PROJECT` folder before doing any project work.
- Start with `PROJECT.md`.
- Then read `Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`.
- Then read `nba-whistle-project-log.md`.
- If another file remains in this folder, read it too.
- Do not rely only on chat history or memory.
- If a request depends on formulas, metric meanings, or exclusions, re-check the definitions document before answering or editing.
- If a request depends on current project status, re-check this file and the project log before answering or editing.

## Current Scope
- The project studies whether NBA defensive foul calls show short-term whistle momentum.
- The unit of analysis is a possession.
- The user-facing unit is one NBA game.
- The core question is whether recent defensive fouls inside a game connect to current and near-future foul patterns.
- The active project uses WMI only.
- Completed-game lists are only comparison context for percentiles and distribution plots.
- The project no longer has a separate pooled season-level edition.
- WMI should show whistle-pattern behavior. It should not be presented as proof of referee intent by itself.

## Current Project Stage
- Current stage: game-level `WMI`.
- Current work centers on game-level WMI.
- League-wide completed-game outputs support game comparison, not pooled season claims.
- Current documentation priority: keep definitions, project guidance, and logs organized and separate.

## Core Project Rules
- Offensive fouls end possessions.
- Offensive fouls do not count as defensive fouls for this project.
- Last-two and next-two windows use global possession order.
- Last-two and next-two windows are not filtered by team.

## Key Variables
- `L_t`: equals `1` when at least one of the previous two possessions had a counted defensive foul.
- `F_t`: equals `1` when the current possession had a counted defensive foul.
- `N_t`: equals `1` when at least one of the next two possessions had a counted defensive foul.
- `M_t`: possession momentum score.
- `seconds_left_in_game`: seconds remaining in the game.
- `score_difference`: offense score minus defense score.
- `score_margin`: absolute value of `score_difference`.
- `period_bucket`: simplified period label.
- `offense_team`: team with the ball.
- `defense_team`: team defending.

## Metric Names
- `WMI`: direct, unadjusted Whistle Momentum Index.
- `wmi_percentile`: where one game’s WMI ranks versus the completed-game comparison set.

## WMI
- `WMI` uses the direct ratio formula from the definitions document.
- It compares average `M_t` when `L_t = 1` to average `M_t` when `L_t = 0`.
- It does not adjust for score, time, teams, period, or intentional-foul situations.
- It is useful as a simple first look.
- It should not be treated as proof by itself.

## Game-Level Use
- Each game gets one `WMI` value calculated from that game’s possessions.
- Completed-game datasets provide percentile and distribution context.
- Public labels should call the metric `WMI`.

## Interpretation Rules
- A WMI value above `1` means more whistle momentum after recent fouls.
- A WMI value near `1` means little or no difference.
- A WMI value below `1` means less whistle momentum after recent fouls.
- WMI is easier to explain.
- Percentiles and distribution plots compare one game against other completed games.
- Completed-game comparison outputs should not be presented as a separate season-level WMI edition.

## Files In The `PROJECT` Folder
- `PROJECT.md`: main formal guide, current scope, workflow, metric naming, and documentation rules.
- `Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`: formal definitions, variables, formulas, exclusions, and interpretation guardrails.
- `nba-whistle-project-log.md`: short chronological project history.
- `README.md`: folder-level orientation note.
- `CODEX.md`: legacy agent-instruction note now merged into `PROJECT.md`.
- `Plan for WMI - Ryan Kalfus (2026).md`: legacy plan note now merged into `PROJECT.md`.

## Where Information Belongs
- Put formal terms, variables, equations, exclusions, and interpretation rules in `Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`.
- Put project scope, workflow, metric naming, and documentation rules in `PROJECT.md`.
- Put short chronological history in `nba-whistle-project-log.md`.
- Keep `README.md`, `CODEX.md`, and `Plan for WMI - Ryan Kalfus (2026).md` short because their main guidance has been merged here.

## When To Edit `PROJECT.md`
- Edit `PROJECT.md` when project scope changes.
- Edit `PROJECT.md` when workflow rules change.
- Edit `PROJECT.md` when metric naming rules change.
- Edit `PROJECT.md` when documentation rules change.
- Edit `PROJECT.md` when instructions for future project work change.

## When To Edit The Definitions Document
- Edit the definitions document when a term is added, removed, or redefined.
- Edit the definitions document when a formula changes.
- Edit the definitions document when a variable changes meaning.
- Edit the definitions document when interpretation guardrails change.
- Do not use the definitions document as a routine log.

## When To Edit The Project Log
- Edit `nba-whistle-project-log.md` after meaningful project changes.
- Keep entries short.
- Use `mm.dd.yyyy: change` format.
- Do not put full calculations in the project log.
- The project log may name files outside the `PROJECT` folder when needed for historical accuracy.

## When To Edit `README.md`
- Edit `README.md` only when the folder-level reading order changes.
- Keep it short.
- Do not put formulas, logs, outside filenames, or detailed workflow rules there.

## When To Edit `CODEX.md`
- Edit `CODEX.md` only if the folder-local pointer needs to change.
- Keep the real agent/project instructions in `PROJECT.md`.
- Do not put outside filenames there.

## When To Edit `Plan for WMI - Ryan Kalfus (2026).md`
- Edit this file only if its folder-local pointer status changes.
- Keep the real active plan in `PROJECT.md`.
- Do not put outside filenames there.

## Folder Reference Rule
- Files inside `PROJECT` may name files inside `PROJECT`.
- Files inside `PROJECT` should not name files outside `PROJECT`.
- Exception: `nba-whistle-project-log.md` may name files outside `PROJECT` when needed for historical accuracy.
- If outside implementation files, data outputs, scripts, or calculation files matter, describe them generally without naming them.
- Example: say "working code" instead of naming a specific code file outside this folder.
- Example: say "saved calculation output" instead of naming a specific output file outside this folder.

## After A Formula Or Definition Change
- Update the definitions document first.
- Update `PROJECT.md` if scope, workflow, or naming changed.
- Add a short note to the project log.
- Re-check every file in the `PROJECT` folder for consistency.

## After A Calculation Run
- Do not put detailed calculation results in `PROJECT.md`.
- Do not put detailed calculation results in the definitions document.
- Add a short note to the project log only if the run changes project history or status.
- Keep detailed calculation tracking outside this `PROJECT` folder unless the user asks otherwise.
- Completed-game comparison runs may be logged as comparison context.

## Guardrails
- Do not change `WMI` unless the user clearly asks.
- Do not edit definitions just to match a result.
- If a result does not match the current definitions, say that clearly.

## Starting From Scratch With Only This Folder
1. Read `PROJECT.md`.
2. Read `Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`.
3. Read `nba-whistle-project-log.md`.
4. Use the definitions document as the source of truth for formulas and variable meanings.
5. Use `PROJECT.md` as the source of truth for workflow and documentation rules.
6. Keep the active product WMI-only unless the project intentionally reopens adjusted modeling.
7. Keep the main presentation game-by-game; use league-wide completed-game outputs only as comparison context.
