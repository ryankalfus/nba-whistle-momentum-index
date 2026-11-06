# Additional public footage search — 2026-11-02

This follow-up found six new exact-date replay listings linking Tencent Video, including a two-quarter ATL@MIL listing. It verified no new playback or continuous coverage. Root's browser subsequently found an explicit regional copyright barrier on the LAL@MEM original-audio player; that observation is attributed to root, not the metadata researcher.

The fixed fourteen-game pilot remains unchanged. Independent reviews remain zero. Earlier two-game playback evidence stays in `research/rewrite_completion_2026_11_02/public_replays.json`; this artifact does not promote it to complete film evidence.

## New candidate links

Chinese catalog dates are one calendar day after the US game date. All labels below were read from the linked third-party listing's ordinary public HTML. A Tencent URL, HTTP 200 response or listing title does not establish playable free access or uploader authorization.

| Fixed game | Public listing | Original-audio candidate | Observed limit |
| --- | --- | --- | --- |
| 2021-01-24 ATL @ MIL | [Listing](https://www.724zbw.com/nba/39023.html) | [Tencent](https://v.qq.com/x/cover/mzc00200xyvuxgw/t0035px18id.html) | Q1/Q2 only; Q3/Q4 missing from inspected listing |
| 2023-02-02 MIA@NYK | [Listing](https://www.724zbw.com/nba/75371.html) | [Tencent](https://v.qq.com/x/cover/mzc002009zhkejw/e0045hc6hrf.html) | Playback/free access/coverage unverified |
| 2023-03-22 PHI@CHI | [Listing](https://www.724zbw.com/nba/76393.html) | [Tencent](https://v.qq.com/x/cover/mzc002001efqbei/a0045x80ue2.html) | Playback/free access/coverage unverified |
| 2024-04-02 LAC@SAC | [Listing](https://www.724zbw.com/nba/82957.html) | [Tencent](https://v.qq.com/x/cover/mzc00200zosdhi4/e0048759q40.html) | Playback/free access/coverage unverified |
| 2024-04-12 LAL@MEM | [Listing](https://www.724zbw.com/nba/83157.html) | [Tencent](https://v.qq.com/x/cover/mzc00200lfnmesb/i4100o04gtw.html) | Root browser: region rights unavailable, error 70013080.1 |
| 2025-01-04 UTA@MIA | [Listing](https://www.724zbw.com/nba/87657.html) | [Tencent](https://v.qq.com/x/cover/mzc00200279h4jl/p4100msrnvv.html) | Playback/free access/coverage unverified |

The JSON retains every observed full-game and quarter label/URL, listing HTML SHA-256, all 64 indexed queries, the fixed IDs, excluded condensed matches and route failures. The two ordinary Tencent HTTP probes returned generic Tencent Video HTML without exact game title/duration; they cannot establish video availability.

## Excluded and unsuccessful routes

- **NYK@CLE 2021-01-15:** [exact Chinese-date listing](https://www.724zbw.com/nba/37916.html) links a Weibo item explicitly labeled condensed highlights (`全场精华回放`), excluded from full-game candidates. No new full replay found in the recorded English, Chinese or Russian searches.
- **HOU@CHA, ATL@ORL, MEM@DEN and WAS@TOR in 2021:** exact Chinese-date listings similarly provide condensed Weibo highlights only; URLs and labels are retained as exclusions in JSON. They cannot replace continuous broadcasts.
- **LAC@MEM 2021-11-18:** both inspected team catalog sections returned the same recap/highlight item, not a full-game listing. Prior inert Basketball-video links were not reclassified.
- **SBS:** an indexed historical schedule lists ATL@MIL live on Jan 25 AEDT, but no surviving exact public replay was found. A historical broadcast slot proves scheduling only.
- **NBA and team archives:** indexed results were exact highlights or known replay/League Pass labels; no new free full broadcast was observed. Highlights were excluded.
- **nba-replay.org:** oldest exposed page 137 shows May 2025 games, later than the fixed sample. Search URLs failed in web extraction and ordinary HTTP returned 403; no bypass attempted.
- **Basketballreplays.net:** exposed links cover 2025-26/2026-27; final pagination link `?page236=` repeated the homepage. No exact sample item established.
- **Grinding Tape:** read all 130 game titles exposed on pages 140–145, spanning 2011–Nov 2025; none matched the fixed games. Featured earlier pages and incomplete metadata remain gaps; this is not a complete archive-absence proof.
- **Fishkernba:** public homepage fetch returned 502; exact-date indexed queries returned no candidate.
- **nbareplay.net:** inaccessible in web extraction.
- **nbafullhd:** web extraction was inaccessible. Root separately reported a fake MacOS Security Center alert after a browser redirect and closed the route. No repeat or bypass attempted.

Negative searches are bounded. None establishes that a recording does not exist. The new Tencent candidates require ordinary playback/access checks; regional restrictions, paywalls, missing uploads or incomplete coverage must remain explicit. No VPN, account creation, paid subscription, CAPTCHA completion, media download or redistribution occurred.

## Sources and References

1. [724zbw Cavaliers catalog](https://www.724zbw.com/shipin/qishi/index_7.html) and [Hawks catalog](https://www.724zbw.com/shipin/laoying/index_6.html) — exact early dates; condensed exclusion vs two-quarter listing.
2. [724zbw LAL@MEM listing](https://www.724zbw.com/nba/83157.html), [PHI@CHI listing](https://www.724zbw.com/nba/76393.html), [LAC@SAC listing](https://www.724zbw.com/nba/82957.html), [UTA@MIA listing](https://www.724zbw.com/nba/87657.html), [MIA@NYK listing](https://www.724zbw.com/nba/75371.html) — observed Tencent replay/quarter links; third-party labels only.
3. [SBS historical schedule](https://tvtonight.com.au/wp-content/uploads/SBS-VICELAND-GUIDE-Week-5-January-24-January-30-EASTERN-STATES-NSW-VIC-TAS-ACT.pdf) and [SBS broadcaster article](https://www.sbs.com.au/sport/article/how-to-watch-nba-live-on-sbs/mbdx7wa0o) — scheduling/broadcaster context, no current exact replay.
4. [nba-replay final page](https://www.nba-replay.org/page/137/), [Basketballreplays](https://basketballreplays.net/), [Grinding Tape last archive page](https://grindingtape.com/legends?page=145) — directly read public catalog bounds.
5. [NBA free classic-game policy](https://support.watch.nba.com/hc/en-us/articles/28006218859415-Classic-Games-and-Original-NBA-Content?hidenav=true) — general free NBA ID catalog route; no exact fixed game found, no account created.

## Verification

Validated JSON syntax, fourteen unchanged unique fixed IDs, six replay-candidate listings, five explicitly excluded condensed listings, false coverage/playback flags and zero independent reviews using project Python. This is evidence-only research; project-wide implementation checks belong to the main change and were not run by this researcher. No source events, parser code, protected outcomes, cohort or audit evidence were altered.
