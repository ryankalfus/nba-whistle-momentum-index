# Fixed-sample full-game access search — 2026-11-02

This initial search pass verified no additional playable broadcast. A subsequent browser pass located twelve exact-game listings and verified playback of two long broadcasts; see [current public replay evidence](public_replays.json). Neither has verified continuous full-game coverage or independent annotations. The fixed fourteen games remain unchanged; the search produced no duration or completeness evidence and no independent annotations.

## What changed from the first search

- Queried Internet Archive's public advanced-search API for every matchup title pair, restricted to movies. All results were inspected (0–6 per pair); none identified the exact sampled date. These are search failures, not proof of absence. Compilation titles, abbreviated names and missing metadata remain gaps.
- Searched exact dates, alternate date formats, full replay/full match, and official NBA/team YouTube results. Every returned highlight was excluded from full-game candidates.
- Checked Prime Video exact-date searches for recent games. A general Celtics catalog was rejected because it did not establish the required date.
- Investigated Basketball-video's actual season indexes for 2020–21, 2023–24 and 2024–25. The public indexes resolve through web extraction, but exact-date search found no items; onsite-search/deep-pagination routes failed in this tool, and an ordinary HTTP request returned 403. No exact game, stream duration, rights authorization or playback was established. nbafullhd's homepage was inaccessible. These are documented per-route barriers; neither service is presented as an authorized source.

## Legitimate subscription route

NBA Help updated **2026-10-13** explicitly advertises full-game archives from **2012–13 to present** for League Pass. Standard League Pass is the lowest general-audience archive plan identified; an existing authorized subscriber is the cheapest access route if one is available. This remains a route candidate: neither policy nor payment proves the availability of all fourteen streams. [NBA archive policy](https://support.watch.nba.com/hc/en-us/articles/115000585974-NBA-League-Pass?hidenav=true)

The NBA purchase index lists standard **$16.99/month**; direct open showed **$109.99/season**. A later browser pass verified the monthly checkout price at $16.99 plus tax. The user selected public-source searches; no subscription was purchased. [NBA purchase page](https://www.nba.com/league-pass-purchase?sr=nba+official+basketball)

Premium adds concurrent devices, downloads and in-arena breaks; those extras do not establish better historical stream coverage. Student discounts require eligibility verification and country-specific terms; eligibility is not assumed. [NBA plan comparison](https://support.watch.nba.com/hc/en-us/articles/115000585974-NBA-League-Pass?hidenav=true), [student terms](https://support.watch.nba.com/hc/en-us/articles/9382586457623-NBA-League-Pass-Student-Discount?hidenav=true)

Two exact-game official archive items remain the strongest concrete catalog leads: [ATL@ORL 2021-03-03](https://www.nba.com/watch/video/hawks-magic-03-03-2021-a) and [LAC@MEM 2021-11-18](https://www.nba.com/watch/video/clippers-grizzlies-11-18-2021-kiswe). Both previously showed entitlement prompts; duration is unknown.

## Per-game archive checks

| Game | Date | Internet Archive matchup-title hits | Exact sample found | Full game verified |
| --- | --- | ---: | --- | --- |
| 0022000181 NYK @ CLE | 2021-01-15 | 4 | No | No |
| 0022000254 ATL @ MIL | 2021-01-24 | 6 | No | No |
| 0022000367 HOU @ CHA | 2021-02-08 | 1 | No | No |
| 0022000544 ATL @ ORL | 2021-03-03 | 3 | No | No |
| 0022000925 MEM @ DEN | 2021-04-26 | 0 | No | No |
| 0022000997 WAS @ TOR | 2021-05-06 | 3 | No | No |
| 0022100226 LAC @ MEM | 2021-11-18 | 2 | No | No |
| 0022200780 MIA@NYK | 2023-02-02 | 2 | No | No |
| 0022201087 PHI@CHI | 2023-03-22 | 5 | No | No |
| 0022301101 LAC@SAC | 2024-04-02 | 1 | No | No |
| 0022301177 LAL@MEM | 2024-04-12 | 5 | No | No |
| 0022400393 BOS@ORL | 2024-12-23 | 5 | No | No |
| 0022400481 UTA@MIA | 2025-01-04 | 0 | No | No |
| 0022400553 MIA@LAC | 2025-01-13 | 1 | No | No |

Each exact API URL, inherited official browser barrier and candidate status is preserved in `full_game_access.json`. Inherited browser evidence comes from `research/footage_2026_11_02/browser_observations.json`; it was not newly observed by this researcher.

Before treating any route as obtained footage, an authorized viewer must record the exact broadcast and duration, inspect the start/end and every period, identify gaps/cuts, and establish readable game/shot clocks. Full coverage cannot be inferred from a title, replay label or occasional successful seek. If an entitled session cannot expose those streams, a concrete NBA support inquiry should identify all fourteen game IDs; no message was sent here. The fixed sample must remain fixed.

## Sources and References

1. [NBA League Pass official archive and plan policy](https://support.watch.nba.com/hc/en-us/articles/115000585974-NBA-League-Pass?hidenav=true) — current archive scope, plan differences, region restrictions.
2. [NBA official purchase page](https://www.nba.com/league-pass-purchase?sr=nba+official+basketball) — current plan catalog; indexed monthly price distinguished from directly opened season price.
3. [NBA full-replay instructions](https://support.watch.nba.com/hc/en-us/articles/360011802673-Full-Game-Replays-and-Condensed-Game-Availability) — authorized viewing route; no exact-game guarantee.
4. [Internet Archive advanced search](https://archive.org/advancedsearch.php) — public metadata API; fourteen exact query URLs in JSON.
5. [Basketball-video 2020–21 catalog](https://basketball-video.com/videos/nba_full_game_replays/nba_regular_season_2020_21/5), [2023–24 catalog](https://basketball-video.com/2023-24), [2024–25 catalog](https://basketball-video.com/2024-25) — third-party listings only; authorization, exact sample content and playback unverified.
6. [Toronto official game page](https://www.nba.com/raptors/game/0022000997), [Boston official game page](https://www.nba.com/celtics/game/0022400393-celtics-vs-magic-orlando-fl-12-23-2024) — additional matching replay labels; no playback evidence.

## Verification

JSON syntax and fourteen unique unchanged IDs were checked with project Python. No source code or scientific records were changed; the project-wide code suite was not run for this evidence-only artifact. No account creation, purchase, large-media download, bypass, reviewer attestation or independent film validation occurred.
