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
- The core question is whether recent defensive fouls connect to current and near-future foul patterns.
- The project separates raw WMI from controlled WMI.
- Raw WMI is the direct first-look metric.
- Controlled WMI is the context-aware version of the same whistle-momentum idea.
- WMI should show whistle-pattern behavior. It should not be presented as proof of referee intent by itself.

## Current Project Stage
- Current stage: `WMI_raw` plus `WMI_controlled`.
- Current work includes game-level and season-level versions of both raw and controlled WMI.
- Current documentation priority: keep definitions, project guidance, and logs organized and separate.

## Core Project Rules
- Offensive fouls end possessions.
- Offensive fouls do not count as defensive fouls for this project.
- Last-two and next-two windows use global possession order.
- Last-two and next-two windows are not filtered by team.
- Raw and controlled WMI must stay clearly separated.

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
- `WMI_raw`: direct, unadjusted Whistle Momentum Index.
- `WMI_controlled`: context-aware Whistle Momentum Index.
- `WMI_rawgame`: one raw WMI value for one game.
- `WMI_controlledgame`: one controlled WMI value for one game.
- `WMI_rawseason`: one raw WMI value across a season or season sample.
- `WMI_controlledseason`: one controlled WMI value across a season or season sample.

## WMI_raw
- `WMI_raw` uses the direct ratio formula from the definitions document.
- It compares average `M_t` when `L_t = 1` to average `M_t` when `L_t = 0`.
- It does not adjust for score, time, teams, period, or intentional-foul situations.
- It is useful as a simple first look.
- It should not be treated as proof by itself.

## WMI_rawgame
- `WMI_rawgame` is `WMI_raw` calculated on possessions from one game.
- It uses the same formula as `WMI_raw`.
- It should be labeled as game-level raw WMI.

## WMI_rawseason
- `WMI_rawseason` is `WMI_raw` calculated on possessions across a season or season sample.
- It uses the same formula as `WMI_raw`.
- It should be labeled as season-level raw WMI.

## WMI_controlled
- `WMI_controlled` keeps the same whistle-momentum idea as `WMI_raw`.
- It should account for game context that can affect foul patterns.
- It should consider score difference, score margin, time left, period, offense team, defense team, and intentional-foul situations.
- It should not be changed only to make it closer to `WMI_raw`.
- If controlled WMI is lower than raw WMI, that can mean some raw pattern was explained by game context.
- The definitions document currently defines the controlled concept and exclusions, but it does not lock the project to one final statistical model forever.

## WMI_controlledgame
- `WMI_controlledgame` is `WMI_controlled` calculated for one game.
- It should be labeled as game-level controlled WMI.
- It should be kept separate from `WMI_rawgame`.

## WMI_controlledseason
- `WMI_controlledseason` is `WMI_controlled` calculated across a season or season sample.
- It should be labeled as season-level controlled WMI.
- It should be kept separate from `WMI_rawseason`.

## Controlled Exclusions
- Controlled WMI should exclude large-margin situations as defined in the definitions document.
- Controlled WMI should exclude likely intentional late-game fouls as defined in the definitions document.
- Do not change exclusion rules unless the user clearly asks.
- If an exclusion rule changes, update the definitions document and this file.

## Interpretation Rules
- A WMI value above `1` means more whistle momentum after recent fouls.
- A WMI value near `1` means little or no difference.
- A WMI value below `1` means less whistle momentum after recent fouls.
- Raw and controlled WMI answer related but different questions.
- Raw WMI is easier to explain.
- Controlled WMI is more careful about game context.

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
- Edit the definitions document when a controlled exclusion rule changes.
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

## Guardrails
- Do not change `WMI_raw` unless the user clearly asks.
- Do not change controlled assumptions or exclusions unless the user clearly asks.
- Do not edit definitions just to match a result.
- Do not force controlled WMI to look closer to raw WMI.
- If a result does not match the current definitions, say that clearly.

## Starting From Scratch With Only This Folder
1. Read `PROJECT.md`.
2. Read `Definitions for NBA Analytics Research - Ryan Kalfus (2026).md`.
3. Read `nba-whistle-project-log.md`.
4. Use the definitions document as the source of truth for formulas and variable meanings.
5. Use `PROJECT.md` as the source of truth for workflow and documentation rules.
6. Keep raw and controlled WMI separate in all notes, results, and explanations.
