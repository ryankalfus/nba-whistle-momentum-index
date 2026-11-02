# Independent schedule cross-check

Date: 2026-11-02. Implementation: `espn-schedule-crosscheck-v1`.

The preserved ESPN schedule evidence accounts for 6,084 completed games across the six declared cohorts. All 180 team/cohort requests succeeded, every event appeared consistently in both participant schedules, every regular-season team has 72 or 82 completed counted games, and the playoff frame contains 15 series of four to seven games. This checks the observed inventory against independently sourced schedules; it does not validate possessions or pass the independent reconstruction audit.

| Cohort | ESPN completed games | Exact archive matches after documented date amendments |
| --- | ---: | ---: |
| 2020-21 regular season | 1,080 | 1,080 |
| 2021-22 regular season | 1,230 | 1,230 |
| 2022-23 regular season | 1,230 | 1,230 |
| 2023-24 regular season | 1,230 | 1,230 |
| 2024-25 regular season | 1,230 | 1,230 |
| 2024-25 playoffs | 84 | 84 |

## Evidence and identity

The independent source is ESPN's public [NBA teams endpoint](https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams?limit=100) and each team's `/teams/{id}/schedule?season=YEAR&seasontype=TYPE` response. Years 2021–2025 represent seasons 2020-21–2024-25; type 2 is regular season and type 3 is playoffs. The current top-level season field is unsuitable for historical validation: event season/type and optional `requestedSeason` are checked instead. Empty non-playoff team responses remain explicitly acquired observations.

Acquisition uses two workers, an 8 MiB response limit, timeouts, and an exclusive new directory. All 181 original response bodies (team frame plus schedules, 214,686,642 uncompressed bytes) are retained as gzip snapshots under gitignored `output/v2/independent-schedule-2026-11-02/`. Its manifest records source URL, query, retrieval time, HTTP result, original byte count and SHA256. The tracked comparison embeds that manifest and its hash. Reverification decompresses and hashes original bytes. No existing source files are edited.

Only final completed games enter the expected frame. The response evidence separately records 51 postponed entries and two final Cup championship exclusions: ESPN IDs `401607495` and `401734908`, explicitly labeled “NBA In-Season Tournament Championship” and “NBA Cup Championship” in competition notes. Group/knockout Cup games are not excluded. All remaining events and exceptions stay visible; unresolved pagination, failed requests, inconsistent duplicates, incomplete per-team totals, or unmatched games keep the comparison unverified.

ESPN IDs remain the independent identities. NBA IDs are attached by unique `(season, game_type, America/New_York date, home, away)` joins to historical metadata. The initial strict join matched 6,054 games and left 30 games on each side unmatched. The historical dates differed from the official NBA displayed game dates in 24 games in 2020-21, one in 2022-23, and five in 2024-25. These dates often align with postponed ESPN entries; the observed mismatch is established, while that historical-date origin is an interpretation.

Every amendment has separate official NBA page evidence tied to its exact NBA ID and both full team names. Direct NBA CDN boxscore and nba.com HTTP requests returned 403. The fallback retrieved official NBA game-page rendered titles through the web tool: 29 pages opened successfully; the final Chicago/Toronto page was available as a primary NBA search result after direct opens timed out. Twenty-one grouped web retrieval snapshots are retained alongside the raw ESPN evidence. Their SHA256s, titles, URLs, original dates and amended dates are recorded in `research/rewrite_completion_2026_11_02/schedule_date_corrections.json`. These are web-tool evidence snapshots, **not original NBA HTTP response bytes**. NBA UTC timestamps were not acquired; the displayed NBA game date agrees with the independently converted ESPN UTC timestamp. Historical CSVs remain unchanged.

The schedule records both `historical_date` and explicit `date_correction` evidence. Downstream chronology and train/test split work must use the corroborated actual date and preserve the correction flag; unamended historical dates are unsuitable for silently ordering these 30 games.

## Reproduction and limits

Run on a fresh output/report destination with the project virtual environment:

```sh
.venv/bin/python -m whistle_research.schedule --acquire --raw NEW_RAW_DIRECTORY --metadata research/hypotheses_2026_09_12 --report NEW_INITIAL_REPORT
```

The official date evidence requires its preserved web snapshots and reviewed correction file; acquisition does not silently infer rescheduling. To rerun the accepted comparison offline:

```sh
.venv/bin/python -m whistle_research.schedule --raw output/v2/independent-schedule-2026-11-02 --metadata research/hypotheses_2026_09_12 --corrections research/rewrite_completion_2026_11_02/schedule_date_corrections.json --report NEW_REPORT --schedule NEW_SCHEDULE
```

The initial diagnostic report is `schedule_comparison_v3.json`; the accepted corrected report is `schedule_comparison_corrected.json`; the source-inventory input is `schedule_expected.json`, all in `research/rewrite_completion_2026_11_02/`. The correction extraction script preserves how the 30 primary titles were normalized; it refuses existing output. No schedule is emitted when comparison is unverified.

Exact agreement, two-team corroboration, team totals and bracket counts substantially strengthen coverage evidence but do not prove the endpoint cannot omit or misclassify an event. Playoff series counts are a structural check, not independent film evidence. All six archive cohorts being schedule-accounted does not mean their events are correctly reconstructed, audit-eligible, or scientifically validated.
