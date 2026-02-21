# NBA Analytics Research Log - Ryan Kalfus (2026)

- 02.17.2026: Chose project idea for Whistle Momentum Index (WMI) focused on whether foul calls have short-term memory.
- 02.17.2026: Defined early model inputs (time, score margin, recent foul history, timeouts/challenges/momentum shifts).
- 02.18.2026: Set up Anaconda and Jupyter notebook environment.
- 02.18.2026: Installed and tested `pandas` and `nba_api`.
- 02.18.2026: Pulled 2025-26 game data and filtered to regular season (`GAME_ID` starts with `002`).
- 02.18.2026: Pulled live NBA CDN play-by-play JSON for a sample game.
- 02.21.2026: Converted research/definitions/plan PDFs to Markdown files.
- 02.21.2026: Built step-2 possession parser in `step2_build_possessions.py`.
- 02.21.2026: Created sample possession output file `possessions_step2_sample.csv`.
- 02.21.2026: Fixed parser over-splitting issues around foul + turnover and dead-ball sequences.
- 02.21.2026: Changed possession foul output from boolean `ended_in_def_foul` to `defensive_foul_count`.
- 02.21.2026: Added `defensive_foul_teams` to track which team committed defensive fouls in each possession.
- 02.21.2026: Changed log format to bullet-only list using `mm.dd.yyyy: change`.
- 02.21.2026: Rebuilt parser to use NBA `possession` field for possession ownership (instead of inferred transitions).
- 02.21.2026: Updated possession time logic so `end_time` is next possession `start_time`, reducing zero-second artifacts.
