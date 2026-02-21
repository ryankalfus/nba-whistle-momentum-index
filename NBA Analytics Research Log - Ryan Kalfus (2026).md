# NBA Analytics Research Log - Ryan Kalfus (2026)

## Change History
- 21.02.2026: Created this Markdown log by transferring content from `NBA Analytics Research Log - Ryan Kalfus (2026).pdf`.
- 21.02.2026: Deleted the old PDF after transfer.
- 21.02.2026: Removed blank `2026-02-19` entry and added a full `2026-02-21` progress entry.
- 21.02.2026: Standardized Change History format to `- dd.mm.yyyy: change`.
- 21.02.2026: Converted `Definitions for NBA Analytics Research Log - Ryan Kalfus (2026).pdf` and `Plan for NBA Analytics Research Log - Ryan Kalfus (2026).pdf` to Markdown and deleted the PDFs.

## Log Entries

### 2026-02-17
**Goal for Day:**
Come up with a project idea.

**What I did:**
Came up with one singular project idea involving research on NBA analytics to develop a new statistic/index.

**Key Idea Learned:**
For this to really work, I need to do something truly niche and original, developing something that is not usually tracked. Also, I will need extensive access to datasets and clients such as `pbpstats` and `nba_api`.

**Results:**
- **Whistle Momentum (ref bias)**
  - Question: Do foul calls have a memory within a game (make-up calls / whistle tightening), after controlling for game context?
  - Idea: model probability of a foul at time `t` given:
    - time/score margin
    - recent foul history (last `<180` seconds)
    - recent timeouts, challenges, momentum shifts
  - Output: with modeling with data, define a variable that shows how much more/less likely a foul is to be called in a specific setting after a recent foul is called

**Problems / confusion:**
No clue where to get data, limited experience with Python, limited math work in probability/data.

**Next steps:**
Find data sets, come up with a scope, or a general idea of what data to gather from where, what to code, what to log here and in Python, and what to execute.

### 2026-02-18
**Goal for Day:**
Set up coding environment, access official NBA play-by-play data for the 2025-26 season.

**What I did:**
- Installed Anaconda and set up Jupyter Notebook.
- Installed and imported pandas for data manipulation.
- Installed `nba_api` and tested it successfully.
- Pulled 2025-26 NBA season game data using `LeagueGameFinder`.
- Filtered to regular season games only (`GAME_ID` starting with `002`).
- Retrieved live play-by-play data directly from the NBA CDN endpoint for one 2025-26 regular season game.

**Key Idea Learned:**
The biggest shift today was moving from conceptual modeling to data structure thinking. I realized that before building any statistic like WMI, I need to construct clean time variables (game seconds elapsed) and clearly define event windows (e.g., "foul in last 90 seconds"). Also learned that official NBA live JSON endpoints are more reliable for current seasons than Kaggle datasets.

**Results:**
Successfully accessed and structured real 2025-26 play-by-play data.

**Problems / confusion:**
- Understanding how to get specific foul data.
- How to calculate variables with data retrieved.

**Next steps:**
- Finalize clean `game_seconds_elapsed` variable.
- Implement correct rolling window logic.
- Compute initial raw WMI estimate for one game.

### 2026-02-21
**Goal for Day:**
Keep the research log organized and keep building possession-level data for the Whistle Momentum project.

**What I did:**
- Replaced the old PDF research log with this Markdown version so updates are easier.
- Added a running Change History section so every change is recorded.
- Built/updated step 2 possession code in `step2_build_possessions.py`.
- Generated sample possession output in `possessions_step2_sample.csv`.

**Key Idea Learned:**
Clean possession boundaries are required before calculating any whistle momentum metric. If boundaries are wrong, the metric will be noisy.

**Results:**
- Active project files now include:
  - `01_setup_and_exploration.ipynb`
  - `step2_build_possessions.py`
  - `possessions_step2_sample.csv`
- Research log is now in Markdown for easier tracking and updates.

**Problems / confusion:**
- Possession parsing still has edge cases around fouls and dead-ball events.

**Next steps:**
- Validate possession logic across more games.
- Start computing foul-after-foul windows for early WMI checks.
- Keep recording each new change in this log.

## Update Rule (Use Going Forward)
Add one bullet under **Change History** every time we make a project change or add something new.
Use this exact format: `- dd.mm.yyyy: change description`.
If one update includes multiple important changes, split into multiple bullet lines.
