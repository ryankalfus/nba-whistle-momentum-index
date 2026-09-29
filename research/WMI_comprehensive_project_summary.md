# NBA Whistle Momentum Index: Comprehensive Project Summary

## Project overview

The NBA Whistle Momentum Index project studies whether defensive foul calls exhibit short-term patterns across possessions, how those patterns relate to basketball context, and whether recent foul history provides useful predictive information. Its public product is a searchable collection of game-level WMI scores with comparison percentiles and explanations. Its research layer includes possession reconstruction, statistical validation, sequence forecasts, uncertainty experiments and empirical analyses of all 18 supplied hypotheses.

The project has developed beyond a single descriptive ratio into a broader research system. That system can explain the components of a game score, trace counted fouls back to source events, compare alternative reconstruction methods, evaluate predictions on later seasons, and distinguish completed statistical tests from questions the available data cannot identify.

The central finding is modest: recent fouls are associated with slightly lower immediate foul probability, while continuation conditional on a current foul is slightly higher. There is no simple smooth-decay pattern. Some foul-timing models obtain small predictive gains, but the tested win-probability model does not improve when foul features are added. Stronger findings concern substitution behavior after foul trouble and the decline in take-labeled fouls across the rule-change comparison. These observations do not establish referee intent, call correctness or optimal coaching policy.

This report brings together the metric, data, website, all 18 hypotheses, forecasting results, interval validation, implementation, verification and outstanding research questions. It describes the saved project state and completed analyses; it does not imply that every proposed model architecture or causal investigation has been completed.

## The metric and what it measures

WMI is calculated from a binary defensive-foul indicator for each reconstructed possession:

- **F_t:** at least one counted defensive foul occurs in the current possession.
- **L_t:** at least one counted defensive foul occurs in the preceding two global possessions.
- **N_t:** at least one counted defensive foul occurs in the following two global possessions.
- **M_t = F_t(1 + N_t):** the current foul indicator, receiving an additional unit when followed by a foul within the next two possessions.
- **WMI = mean(M_t | L_t = 1) / mean(M_t | L_t = 0).**

A ratio above one means the observed M_t average is higher after recent fouls; a ratio below one means it is lower. A value close to one describes a small arithmetic difference and does not establish statistical equivalence. The magnitude does not directly express foul volume, foul imbalance, the probability of winning, or the effect of an incorrect call.

Offensive, technical and double-technical foul classifications are excluded from the counted defensive-foul outcome. The two-possession windows run across period boundaries and truncate at game edges. Those equation and window choices are preserved even as the underlying event-to-possession reconstruction is corrected.

Because N_t uses subsequent events, ordinary WMI is retrospective. Any live feature derived from WMI must wait until the relevant future window is complete. The win-prediction study observes this restriction: a historical possession contributes to live WMI only after both following possessions are available.

### Exact decomposition

Let p_l = P(F_t = 1 | L_t = l), and q_l = P(N_t = 1 | F_t = 1, L_t = l). Where the required conditional quantities are defined:

**WMI = (p_1 / p_0) × ((1 + q_1) / (1 + q_0)).**

The first factor is the immediate foul ratio. The second is the continuation ratio. Their product explains how the combined score can conceal components pointing in opposite directions. A component may be undefined when a required count is zero even when some pooled sufficient statistics remain usable. The website therefore exposes the counts and means behind the score rather than displaying the ratio alone.

## Data coverage and possession reconstruction

The core source inventory contains 6,084 games: five regular seasons, 2020–21 through 2024–25, and all 84 games of the 2025 playoffs. The 2020–21 regular season contributes 1,080 games; each of the next four seasons contributes 1,230. Inputs are public archived copies of NBA feeds, pinned to source commits with recorded byte counts and SHA256 hashes. This is reproducible historical archive work, not direct verification of the original live feed at every moment.

### Shared website and validation parser

The shared parser in `wmi_possessions.py` reconstructs ownership on live-event rows and explicitly separates periods. Substitutions, reviews and period markers cannot independently begin possessions. Technical-only ownership segments are removed. Temporary same-team sequences are rejoined or retained separately according to whether the preceding live segment ended with a terminal event such as a made basket or turnover.

Regulation and overtime clocks use their respective 12-minute and 5-minute lengths. Fractional seconds are parsed correctly. Starting score and clock come from the preceding recorded event, with period-start resets. This is a reconstructed reference point that can precede actual live-ball control; it is not a claim of perfectly observed possession-start timing.

The parser reconstructs defending-team foul counts and bonus eligibility before the possession, including regulation/OT quotas and the final-two-minute rule. Offensive, technical and double fouls do not consume the normal reconstructed team-foul quota. Rare rule exceptions and revisions in finalized event records remain limitations.

Player identifiers, foul subtypes, descriptors, descriptions, free throws and shot/rim outcomes are retained for audits and separate analyses. Current-possession outcomes are not used as pre-possession predictors. Unavailable early-season shot-zone fields remain missing rather than being treated as zero. Future overtime duration never enters a predictor. Incomplete future forecast horizons at the end of a game are excluded rather than classified as no-foul outcomes.

The validation reconstruction contains **6,084 games and 1,208,809 possessions**. Compared with the older parser on the same CDN source:

| Reconstruction diagnostic | Result |
|---|---:|
| Games with a changed possession count | 4,374 |
| Mean absolute game WMI change | 0.021651 |
| Maximum absolute game WMI change | 0.543544 |
| Mean absolute overlapping CDN/mobile difference using the old grouping | 0.000652 |
| Explicitly recorded unassigned foul events | 16 |
| Removed technical-only/administrative ownership groups | 72 |

The feed comparison covers the 1,230 overlapping 2024–25 regular-season games. In that overlap, the much smaller feed difference helps distinguish source substitution from the larger consequences of correcting possession boundaries.

### Separate reconstruction used for the hypothesis study

The all-hypotheses runner uses its own rich-event ownership/period reconstruction. It adds 18,029 period boundaries relative to ownership-only grouping and quarantines four games with backward source clocks: 0022000181, 0022000254, 0022000925 and 0022301177. The retained sample contains **6,080 games and 1,225,902 possession groups**. All 1,230 primary 2024–25 regular-season games and all 84 playoff games remain included.

| Research stream | Retained games | Possessions/groups | 2024–25 regular-season groups |
|---|---:|---:|---:|
| Website validation and foul forecasting | 6,084 | 1,208,809 | 244,841 |
| All-18-hypotheses study | 6,080 | 1,225,902 | 248,456 |

These are separate samples and operational reconstructions. H9 additionally uses legacy game-level WMI. The hypothesis study's four-game quarantine has not been propagated to the website validation dataset. An unparseable clock and a backward clock are different checks, so a zero count for invalid timed events in one report does not resolve the other's ordering anomalies.

The studies should not be treated as interchangeable versions of one canonical possession table. Establishing a common parser and anomaly policy remains a substantive integration task before presenting the research streams as one unified release.

## Website and game interpretation

The website combines the original 8,322-row search snapshot with 6,084 recalculated summaries, giving **8,629 distinct searchable games**, including 307 additions. Search covers regular-season, playoff and play-in games where the historical project has data; recalculation does not yet cover every legacy season or game type.

Each game identifies its parser version. Recalculated games use a percentile reference of **6,000 recalculated regular-season games from 2020–21 through 2024–25**. Original rows retain a separately named reference drawn from the original mixed search snapshot. Percentiles describe rank within the named population and are not significance tests.

The recalculated regular-season reference has mean WMI **0.966674** and median **0.917852**. The earlier 6,727-game headline summary remains explicitly labeled as an original snapshot; it is not presented as the current search population.

Game explanations provide:

- WMI to three decimals and percentile to one decimal.
- Counts in the recent-foul and other-possession groups, n1 and n0.
- The numerator and denominator means used in the WMI ratio.
- Immediate and continuation components where defined.
- Same-team and opposite-team transitions between consecutive counted foul possessions.
- A foul timeline with possession, period, clock, team, subtype/descriptor and description.
- Explicit notices when components or timelines require source reprocessing and are unavailable for a legacy row.

There are 6,084 per-game timeline files. Timelines load on demand, and a delayed response for a previously selected game is prevented from replacing the current selection. Failure to load a timeline leaves the summary available. Compact dates display correctly, and an empty WMI value displays as N/A rather than being converted into zero. One original search row, game 0042000105, remains without a computed WMI in the merged dataset.

Interpretation uses above/below-one wording rather than an arbitrary 0.95–1.05 neutral band. A group with fewer than 30 possessions receives a sample-size notice explicitly described as an unvalidated threshold. Per-game inferential intervals are withheld because the tested bootstrap procedure did not achieve consistent coverage. The Validation section supplies model comparisons and research downloads, with responsive diagnostic grids and horizontally scrollable tables.

## Research design and interpretation conventions

All 18 supplied hypotheses received empirical analyses. The result ledger contains **77 estimates**, including **55 inferential comparisons** subjected jointly to Benjamini–Hochberg correction. Pointwise 95% intervals are not multiplicity-adjusted. Rows without p-values or q-values are descriptive estimates and should not be read as formally passed tests.

Regression uncertainty is clustered by game; count models use robust game-level errors. Before/after and prediction differences use 1,000 whole-game bootstrap draws. Crew stability resamples crew identities. The adjusted q-values address the reported family of comparisons, but they do not remove uncertainty from exploratory specification choices, imperfect proxies or unmeasured confounding.

Odds and rate ratios have a null of one. Additive differences and correlations have a null of zero. An interaction odds ratio compares odds ratios, rather than providing a subgroup's standalone foul probability. A difference of 0.01 probability or share units equals one percentage point. Statistical detectability and practical predictive usefulness are separate questions.

The roadmap was not an external preregistration. Hypothesis specifications and fallback analyses were developed during the research. The separate validation stream has an internal protocol written before its fits, but 2024–25 exploratory results were already known. Its final-season evaluation is a retrospective holdout, not an untouched prospective trial.

The detailed sections below retain each hypothesis's question, executed method, estimates, intervals, conclusions and identification limits.

## All 18 hypotheses: methods, results and conclusions

### H1. Short-term dependence after context adjustment

**Question:** Does recent foul history still matter after accounting for basketball context?

**Executed analysis:** Fitted a binomial logistic model of current defensive-foul occurrence on the previous-two-possession indicator. Controls are signed score difference, absolute margin, remaining regulation time, quarter/OT, offense and defense team, home offense, reconstructed bonus, and rim attempts, three-point attempts and free throws in the previous five global possessions. Repeated the fit after excluding every possession in the likely intentional-fouling state, whether or not it actually contained a foul. A within-game linear probability sensitivity absorbs fixed game and assigned-crew levels.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| context_adjusted: L2 | 0.95298 | [0.92774, 0.97891] | 0.000438 | 0.00185 | 248,456 / 1,230 | odds ratio |
| standardized probability change | -0.00644 | — | — | — | 248,456 / 1,230 | probability difference |
| exclude_all_late_strategy_possessions: L2 | 0.94636 | [0.92105, 0.97237] | 6.72e-05 | 0.000349 | 246,832 / 1,230 | odds ratio |
| within-game fixed-effect linear probability sensitivity | -0.0082 | [-0.01181, -0.0046] | 8.17e-06 | 4.99e-05 | 248,456 / 1,230 | probability difference |

**Interpretation:** Small negative dependence survives the measured controls: a recent foul is associated with lower, not higher, current foul probability. The standardized probability change is about −0.64 percentage points. This supports dependence, not positive self-excitation or referee bias.

**Limitations and research scope:** Partial implementation of the originally proposed full model: these are team fixed effects and game-clustered errors, plus a game-fixed-effect sensitivity—not hierarchical logistic random effects. No validated five-player lineups, drives, matchup tracking, or current legal-contact opportunities are available. Past shot counts are imperfect style proxies. H1 was previously attempted with fewer controls; it was rerun here.

### H2. Immediate persistence versus future continuation

**Question:** Is WMI driven by immediate occurrence or by future continuation?

**Executed analysis:** Decomposed the two-possession ratio exactly into immediate persistence p1/p0 and continuation (1+q1)/(1+q0). Resampled complete games 1,000 times to estimate uncertainty. The displayed combined ratio uses pooled sufficient statistics for this research diagnostic, not the average of game WMI and not a replacement public season metric.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| window 2: immediate | 0.96864 | [0.94879, 0.98789] | — | — | 248,456 / 1,230 | ratio |
| window 2: continuation | 1.01136 | [1.00344, 1.01876] | — | — | 248,456 / 1,230 | ratio |
| window 2: WMI | 0.97965 | [0.95776, 0.99913] | — | — | 248,456 / 1,230 | ratio |

**Interpretation:** Immediate persistence is below one, while continuation is slightly above one. The immediate component dominates, putting the combined ratio just below one. Calling all three numbers positive ‘momentum’ would obscure the result.

**Limitations and research scope:** These are unadjusted descriptive components with pointwise bootstrap intervals, not independently validated causal mechanisms. One game has an undefined conditional continuation component because a required foul count is zero; its sufficient statistics remain usable in the pooled estimate. Previously run; now rerun with the audited period boundaries.

### H3. Decay over possession distance

**Question:** Does the sequence effect fade smoothly with possession distance?

**Executed analysis:** Computed 1-, 2-, 3-, 5-, and 10-possession versions with whole-game bootstrap intervals. Also jointly modeled the five individual foul lags with the H1 context controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| window 1: immediate | 1.00031 | [0.97542, 1.02441] | — | — | 248,456 / 1,230 | ratio |
| window 1: continuation | 0.9959 | [0.98731, 1.00441] | — | — | 248,456 / 1,230 | ratio |
| window 1: WMI | 0.9962 | [0.96992, 1.02039] | — | — | 248,456 / 1,230 | ratio |
| window 3: immediate | 0.99289 | [0.97509, 1.0108] | — | — | 248,456 / 1,230 | ratio |
| window 3: continuation | 1.00086 | [0.99396, 1.00788] | — | — | 248,456 / 1,230 | ratio |
| window 3: WMI | 0.99375 | [0.97467, 1.01368] | — | — | 248,456 / 1,230 | ratio |
| window 5: immediate | 0.9983 | [0.97989, 1.01778] | — | — | 248,456 / 1,230 | ratio |
| window 5: continuation | 1.00116 | [0.99477, 1.00679] | — | — | 248,456 / 1,230 | ratio |
| window 5: WMI | 0.99945 | [0.98016, 1.01927] | — | — | 248,456 / 1,230 | ratio |
| window 10: immediate | 1.0508 | [1.02766, 1.07385] | — | — | 248,456 / 1,230 | ratio |
| window 10: continuation | 1.00602 | [1.0008, 1.01152] | — | — | 248,456 / 1,230 | ratio |
| window 10: WMI | 1.05713 | [1.03261, 1.08162] | — | — | 248,456 / 1,230 | ratio |
| distance_specific: lag1 | 0.9985 | [0.96607, 1.03203] | 0.92919 | 0.94639 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag2 | 0.95464 | [0.92389, 0.98642] | 0.00546 | 0.01672 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag3 | 1.05973 | [1.02482, 1.09583] | 0.000688 | 0.00258 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag4 | 1.00614 | [0.97361, 1.03976] | 0.71502 | 0.7711 | 248,456 / 1,230 | odds ratio |
| distance_specific: lag5 | 1.04176 | [1.00696, 1.07776] | 0.01827 | 0.04785 | 248,456 / 1,230 | odds ratio |

**Interpretation:** The pattern does not decay monotonically. Lag two is negative and lag three positive; the broad ten-possession ratio is elevated. A single simple decay story is not supported.

**Limitations and research scope:** Longer windows change both recent-history exposure and future continuation. They also mix longer-lasting game conditions. They are not direct estimates of a causal decay kernel. The individual-lag regression, rather than comparisons of overlapping ratio intervals, is the formal adjusted test. Previously run; rerun here.

### H4. Same-team versus opposite-team foul direction

**Question:** Does the next foul tend to return to the same team or move to its opponent?

**Executed analysis:** Compared observed transitions with two baselines: randomly rearranged team marks among foul events, and 500 within-game permutations of foul indicators among each team's actual defensive possession slots. The second preserves each team's foul total and its opportunities. Separately fitted current foul probability on whether the defense committed the last foul, conditioning on gap 1–10 and H1 controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| opportunity_conditioned_direction: same_defense_as_last_foul | 0.98607 | [0.94174, 1.0325] | 0.5502 | 0.68781 | 200,810 / 1,230 | odds ratio |
| opposite-team share above random-mark baseline | 0.04967 | [0.04495, 0.05444] | 4.42e-88 | 1.22e-86 | 1,230 / 1,230 | share difference |
| opposite-team share above within-team opportunity permutation | 0.00826 | [0.00341, 0.0131] | 0.000703 | 0.00258 | 1,230 / 1,230 | share difference |

**Interpretation:** The raw random-mark comparison shows about five percentage points of excess opposite-team transitions. After preserving actual defensive opportunities, the excess is only about 0.83 percentage points, still statistically detectable. The lag-conditioned context model does not show a clear same-team effect. Thus the small residual is baseline-sensitive, not proof of makeup calls.

**Limitations and research scope:** The opportunity permutation controls defensive slots and team game totals, not changing shot opportunities. The adjusted direction coefficient is identified largely by departures from strict possession alternation; this limits its interpretation. Neither test identifies intentional balancing or call accuracy. Previously run with a simpler baseline; the opportunity-preserving test is new.

### H5. Close games versus blowouts

**Question:** Does sequencing differ in close games versus blowouts?

**Executed analysis:** Defined close as pre-possession margin ≤5 and blowout as ≥15, with margins 6–14 as reference. Tested interactions with L2 both before and after excluding all likely intentional-fouling states. Also summarized close, blowout, fourth-quarter/OT, and masked-intentional-call ratios without compressing the possession axis.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| margin_interaction: L2:close | 1.00278 | [0.95079, 1.05762] | 0.9185 | 0.94639 | 248,456 / 1,230 | odds ratio |
| margin_interaction: L2:blowout | 1.01745 | [0.95674, 1.08203] | 0.58151 | 0.69345 | 248,456 / 1,230 | odds ratio |
| margin_interaction_without_late_strategy: L2:close | 0.9799 | [0.92851, 1.03412] | 0.45992 | 0.61697 | 246,832 / 1,230 | odds ratio |
| margin_interaction_without_late_strategy: L2:blowout | 1.02487 | [0.96361, 1.09002] | 0.43468 | 0.59768 | 246,832 / 1,230 | odds ratio |
| close WMI with original global windows | 1.00488 | — | — | — | 105,282 / 1,230 | ratio |
| blowout WMI with original global windows | 0.94602 | — | — | — | 50,109 / 918 | ratio |
| fourth_or_OT WMI with original global windows | 1.01384 | — | — | — | 61,674 / 1,230 | ratio |
| WMI with suspected intentional calls masked throughout windows | 0.96032 | — | — | — | 248,456 / 1,230 | ratio |

**Interpretation:** The adjusted close-game and blowout interactions do not establish different sequencing effects. Raw subgroup ratios differ, but those differences are not equivalent to a significant adjusted interaction.

**Limitations and research scope:** The intentional-fouling heuristic is Q4/OT with ≤35 seconds and offense ahead by >3, or ≤15 seconds and offense ahead by ≥1. It is a state-based proxy, not a validated intentional-foul label. The main sensitivity excludes all eligible observations rather than selectively deleting only foul outcomes. Previously run; the exclusion design was corrected here.

### H6. Bonus status as a modifier of momentum

**Question:** Does entering the penalty change the effect of recent fouls?

**Executed analysis:** Reconstructed the defending team's pre-event foul quota separately for each period, including the final-two-minute rule and OT quota, then tested L2 × bonus. Offensive, technical, and double-personal fouls do not consume the reconstructed normal quota.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bonus_interaction: bonus | 0.80947 | [0.78051, 0.8395] | 5.72e-30 | 1.05e-28 | 248,456 / 1,230 | odds ratio |
| bonus_interaction: L2:bonus | 1.02681 | [0.97223, 1.08446] | 0.34235 | 0.53376 | 248,456 / 1,230 | odds ratio |

**Interpretation:** Bonus status is associated with a lower baseline foul probability in the fitted model, but the bonus-by-history interaction does not establish modified momentum. A baseline bonus association is not evidence for the interaction hypothesis.

**Limitations and research scope:** Bonus is endogenous to earlier fouls and game behavior. Public foul classifications can miss special-case penalties. This is a reconstruction, not a feed of official live penalty flags, and cannot isolate defender restraint from offensive strategy or whistle thresholds. Newly executed.

### H7. Playoffs versus regular season

**Question:** Do playoff whistle dynamics differ?

**Executed analysis:** Compared all 84 archived 2025 playoff games with 1,230 regular-season games. Fitted postseason differences and sequence interactions for any defensive foul, shooting-foul possessions, and nonshooting-only foul possessions. Added a directional interaction and a close-game × postseason × recent-history interaction.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| playoff_interaction: postseason | 1.21314 | [1.14714, 1.28294] | 1.29e-11 | 8.89e-11 | 264,883 / 1,314 | odds ratio |
| playoff_interaction: L2:postseason | 0.95625 | [0.87595, 1.04391] | 0.31745 | 0.52908 | 264,883 / 1,314 | odds ratio |
| shooting_foul_playoff_interaction: postseason | 1.07823 | [0.99858, 1.16422] | 0.0544 | 0.12466 | 264,883 / 1,314 | odds ratio |
| shooting_foul_playoff_interaction: L2:postseason | 0.97653 | [0.87641, 1.08808] | 0.66697 | 0.73366 | 264,883 / 1,314 | odds ratio |
| nonshooting_only_playoff_interaction: postseason | 1.35158 | [1.25779, 1.45236] | 2.2e-16 | 2.42e-15 | 264,883 / 1,314 | odds ratio |
| nonshooting_only_playoff_interaction: L2:postseason | 0.93994 | [0.82558, 1.07014] | 0.34937 | 0.53376 | 264,883 / 1,314 | odds ratio |
| direction_playoff_interaction: same_defense_as_last_foul:postseason | 0.94771 | [0.87233, 1.02959] | 0.204 | 0.37401 | 214,764 / 1,314 | odds ratio |
| close_game_playoff_sequence_interaction: L2:postseason:close | 1.06883 | [0.91384, 1.2501] | 0.40497 | 0.57111 | 264,883 / 1,314 | odds ratio |

**Interpretation:** The postseason baseline foul odds are higher in this comparison, especially for nonshooting-only fouls. The immediate-history, directional, shooting/nonshooting sequence, and close-game sequence interactions do not establish a different playoff momentum mechanism.

**Limitations and research scope:** One postseason is not a universal playoff effect. Playoff team selection, matchups, tactical adjustments and series dependence remain; errors are clustered by game, not by series. Close margin is only a leverage proxy. The last 18 playoff home/date assignments came from the existing project schedule because the separate referee-assignment archive ends earlier. No officials were invented. Previously analyzed at game level; the possession-level comparisons are new.

### H8. Home-court effects on foul direction

**Question:** Do home teams have more favorable dynamic foul patterns or call accuracy?

**Executed analysis:** Modeled defensive-foul probability when the offense is home, its interaction with recent history, and the same effects in close games. Included regular season/playoffs and H1 context controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| home_direction_interaction: home_offense | 1.02862 | [1.00533, 1.05245] | 0.01575 | 0.04558 | 264,883 / 1,314 | odds ratio |
| home_direction_interaction: L2:home_offense | 0.97934 | [0.93498, 1.0258] | 0.37733 | 0.54614 | 264,883 / 1,314 | odds ratio |
| home_in_close_games: home_offense | 1.02649 | [0.99079, 1.06349] | 0.14774 | 0.28019 | 111,974 / 1,314 | odds ratio |
| home_in_close_games: L2:home_offense | 0.99654 | [0.92471, 1.07395] | 0.92765 | 0.94639 | 111,974 / 1,314 | odds ratio |

**Interpretation:** The home-offense baseline association is small (odds ratio about 1.029) and survives the global q<0.05 threshold. However, there is no clear home-specific sequence interaction or strengthened close-game effect. A small baseline drawing-fouls association is different from dynamic home whistle momentum.

**Limitations and research scope:** This measures receiving a counted defensive foul, not whether that foul was correct. A home team drawing more fouls may reflect play style. No correctness/noncall labels were joined, and this is not a complete directional-residual or accuracy study. Previously partial; now expanded with context-adjusted sequence interactions.

### H9. Crowd presence and foul sequencing

**Question:** Does crowd presence change sequencing?

**Executed analysis:** Used stored game-level WMI for 88 bubble and 971 pre-bubble regular-season games in 2019–20, adjusting for home and away team identities. Separately regressed stored WMI on recorded attendance per 10,000 spectators with season/game-type controls in the box-score archive's 2,111 matched games.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bubble_same_season_regular_games: bubble | 0.02238 | [-0.05067, 0.09544] | 0.54814 | 0.68781 | 1,059 / 1,059 | coefficient |
| recorded_attendance_selected_close_game_archive: attendance_10k | -0.03811 | [-0.11961, 0.04339] | 0.35941 | 0.53426 | 2,111 / 2,111 | coefficient |

**Interpretation:** Neither comparison establishes an attendance or bubble sequencing association. The uncertainty leaves room for effects in either direction.

**Limitations and research scope:** This is partial: there is no reliable three-way normal/restricted/no-crowd classification. Missing attendance was never set to zero. The attendance archive disproportionately covers L2M-qualifying close games. Bubble selection, neutral courts, schedule restart and different teams confound a causal crowd claim. This section uses legacy stored WMI and therefore does not share the rich-CDN research parser used by most other sections. The prior bubble comparison was rerun; the recorded-attendance analysis is new.

### H10. Defender foul trouble and opponent strategy

**Question:** Does foul trouble for an important defender change opponent strategy?

**Executed analysis:** Predefined 30 high-defensive-activity players using prior-season blocks plus steals per event-observed appearance, requiring at least 40 appearances. Examined early second/third fouls, fourth fouls through Q3, and fifth fouls, all with >2 minutes left in the period. Tested immediate substitutions after third versus second early fouls and before/after opponent rim share and points per possession over five opponent possessions.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| substitution_after_third_vs_second_early_foul: threshold | 15.32693 | [7.82327, 30.02771] | 1.79e-15 | 1.64e-14 | 388 / 301 | odds ratio |
| rim-attempt share after minus before trouble | -0.000567 | [-0.03686, 0.03576] | 0.97534 | 0.97534 | 245 / 169 | share difference |
| opponent points per possession after minus before trouble | 0.08245 | [-0.02655, 0.18721] | 0.1151 | 0.2261 | 245 / 169 | points per possession |

**Interpretation:** Coaches are much more likely to substitute after an early third foul than a second. The observed rim-attempt share does not clearly change; the opponent scoring estimate is imprecise. Thus substitution response is supported, but the proposed attack-the-defender mechanism is not established.

**Limitations and research scope:** Blocks/steals activity is a reproducible proxy, not a validated list of stars or defensive impact. No drives, contests or matchup-level targeting were measured. The rim/efficiency comparison is before/after without matched no-trouble controls, and substitutions change who is on the floor. Newly executed.

### H11. Whether coaches bench foul-troubled players too conservatively

**Question:** Are coaches systematically too conservative in benching foul-troubled players?

**Executed analysis:** Compared keeping versus immediately benching the predefined defenders after qualifying third/fourth/fifth fouls. Modeled the player's team net points over the next five global possessions with player, personal-foul-count and period indicators plus score/time controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| observational_keep_vs_bench: keep | -0.17886 | [-0.97355, 0.61583] | 0.65913 | 0.73366 | 245 / 169 | coefficient |

**Interpretation:** The keep-versus-bench estimate is imprecise and does not demonstrate that either policy is better. This analysis cannot determine whether coaches are too conservative.

**Limitations and research scope:** This is an executed observational comparison, not an optimal-policy test. Coach knowledge, injuries, matchup, replacement quality and lineups confound the decision; later returns were not modeled. A credible causal answer requires validated lineup histories and a defensible policy-identification design. Newly executed, with causal identification explicitly unresolved.

### H12. Player behavior after drawing a foul

**Question:** Do offensive players change behavior after drawing a foul?

**Executed analysis:** For identified foul-drawing players, compared the next and previous five team offensive possessions, excluding the triggering possession. Measured player shot counts, repeat foul draws, rim share and three-point share, with game-cluster bootstrap uncertainty. Shot-mix comparisons require the player to shoot in both windows.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| shot_count_change next vs previous five offensive possessions | -0.01783 | [-0.03002, -0.00498] | 0.00547 | 0.01672 | 38,296 / 1,230 | difference |
| repeat_draw_change next vs previous five offensive possessions | 0.00642 | [0.00514, 0.0078] | 6.35e-22 | 8.73e-21 | 38,296 / 1,230 | difference |
| rim_share_change next vs previous five offensive possessions | 0.00819 | [-0.00196, 0.01801] | 0.10156 | 0.20689 | 12,604 / 1,230 | difference |
| three_share_change next vs previous five offensive possessions | 0.00617 | [-0.00436, 0.01662] | 0.24815 | 0.44026 | 12,604 / 1,230 | difference |

**Interpretation:** There is a tiny decrease in shot counts and a tiny increase in subsequent repeated foul draws. The shot-location shifts are not clearly established. This is not strong evidence of a large behavioral momentum mechanism.

**Limitations and research scope:** No drives, disputed noncalls, unfavorable rulings or legal-contact judgments were inferred. Fatigue, substitutions and selection into a foul event can create before/after differences. The 12,604 shot-mix events are a selected subset of the 38,296 draw events, not all player possessions. Newly executed.

### H13. The 2022 transition-take-foul rule

**Question:** Did the 2022 transition-take-foul rule change frequency and value?

**Executed analysis:** Compared 2021–22 with 2022–23 using the common descriptor containing ‘take’, excluding the last two minutes of Q4/OT. Estimated a Poisson rate ratio with possession exposure and a segmented time-trend sensitivity at October 18, 2022. Also reported points scored on the labeled take-foul possessions.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| 2021-22 own points on take-foul possessions | 1.15655 | — | — | — | 1,961 / 943 | points |
| 2022-23 own points on take-foul possessions | 1.36872 | — | — | — | 358 / 298 | points |
| post/pre common take-label rate per possession | 0.18031 | [0.1596, 0.20372] | 1.24e-166 | 6.81e-165 | 2,460 / 2,460 | rate ratio |
| segmented trend rule-date level ratio | 0.25272 | [0.17753, 0.35973] | 2.26e-14 | 1.77e-13 | 2,460 / 2,460 | rate ratio |

**Interpretation:** Take-labeled defensive fouls declined sharply after the rule change. Observed points on those possessions were higher afterward. The frequency result is strong as a descriptive pre/post association; causal value is not identified.

**Limitations and research scope:** The denominator is all possessions, not transition opportunities. The common label includes more than perfectly classified transition-take events; documentation or classification could change. Two seasons and an offseason gap, with no unaffected comparison group, cannot isolate the rule from concurrent changes. The points comparison is not expected points conceded relative to a no-foul counterfactual, and retained-possession tagging can affect aggregation. Newly executed.

### H14. Whistle patterns after successful challenges

**Question:** Does a successful challenge change the next whistle pattern?

**Executed analysis:** Identified explicit Challenge replay decisions in the mobile feed, aligned them to the rich-CDN game clock, and compared foul rates in ten possessions before/after. The reviewed possession was excluded. Matched no-challenge windows within the same game/period on margin, remaining time and recent foul history, excluding nearby challenges. Tested successful-challenge difference-in-differences and successful versus unsuccessful challenges.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| successful challenge versus matched no-challenge change | -0.02114 | [-0.03903, -0.00474] | 0.01668 | 0.04588 | 809 / 638 | foul probability difference |
| successful_vs_unsuccessful_challenges: success | 0.02621 | [-0.00472, 0.05714] | 0.09668 | 0.20451 | 1,213 / 870 | coefficient |

**Interpretation:** Successful challenges are followed by lower foul rates relative to the selected no-challenge windows, but the success-versus-failure contrast does not clearly separate successful challenges from challenges generally. Treat the result as suggestive and design-sensitive.

**Limitations and research scope:** All reviewed call types are included, not only foul calls. Matching is approximate and challenge timing is strategic. The pre-window can include the disputed incident, encouraging regression to the mean. Windows may overlap; game bootstrap accounts for within-game dependence but does not solve selection or matching bias. Newly executed.

### H15. Stability of referee-crew sequencing profiles

**Question:** Do exact referee crews have stable sequencing profiles across seasons?

**Executed analysis:** Built unordered triples of assigned officials and each crew-season's mean log immediate-persistence component. Matched exact triples in adjacent seasons and measured Spearman correlation, bootstrapping complete crew identities to preserve repeated years.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / crews | Unit |
|---|---:|---|---:|---:|---:|---|
| same assigned crew year-to-year log-immediate correlation | 0.0801 | [-0.06616, 0.22404] | 0.28194 | 0.48458 | 176 / 172 | Spearman correlation |

**Interpretation:** The cross-season correlation is about 0.08, with an interval spanning zero. This does not establish observable stability. Because crew-season estimates are extremely noisy, it also cannot support a dependable ranking or rule out stable latent differences.

**Limitations and research scope:** No exact crew had at least two games in BOTH matched years, so the originally attempted three-game minimum yielded zero pairs. The fallback includes all repeated triples and was chosen after inspecting coverage. Noise attenuates correlations; team/matchup assignment is not randomized. These are crew-game associations, never attribution of another official's calls or evidence about intent. Newly executed with weak measurement reliability.

Matched sample: 176 crew-year pairs, 172 distinct crews; no repeated pair meets a two-game-per-year minimum.

### H16. Foul sequences and subsequent scoring

**Question:** Does recent foul history predict short-term scoring or style changes?

**Executed analysis:** Used past-only L2 at possession start to model net points, combined free-throw attempts, turnovers, rim attempts and elapsed game-clock seconds over t+1 through t+5. Included H1 controls and game-clustered uncertainty. Censored the final five possessions instead of filling unknown outcomes with zeros.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| future_net5: L2 | -0.03303 | [-0.04933, -0.01673] | 7.13e-05 | 0.000349 | 242,306 / 1,230 | coefficient |
| future_fta5: L2 | -0.00773 | [-0.02337, 0.00791] | 0.33285 | 0.53376 | 242,306 / 1,230 | coefficient |
| future_turnovers5: L2 | 0.00987 | [0.00122, 0.01853] | 0.02529 | 0.06323 | 242,306 / 1,230 | coefficient |
| future_rim5: L2 | 0.01354 | [0.00157, 0.02551] | 0.0266 | 0.06361 | 242,306 / 1,230 | coefficient |
| future_clock_seconds5: L2 | -0.34917 | [-0.52215, -0.17619] | 7.61e-05 | 0.000349 | 242,306 / 1,230 | coefficient |

**Interpretation:** Recent foul history is associated with roughly 0.033 fewer next-five net points from the current offense's perspective and about 0.35 fewer game-clock seconds over that window. Both are tiny. Free throws show no clear change; turnover and rim-attempt associations do not survive the global q<0.05 threshold. Statistical detectability should not be mistaken for useful forecasting magnitude.

**Limitations and research scope:** This is an in-sample conditional-association analysis, not an out-of-sample scoring forecast. Five global possessions give unequal offensive opportunities; net points are oriented to the offense at t. FTA, turnovers and rim attempts pool both teams. Game-clock time is a pace proxy, not real elapsed time. Current F_t, future N_t and final WMI are not predictors. Previously not run; newly executed here.

### H17. Live foul features and win prediction

**Question:** Do live foul-history features improve win-probability predictions?

**Executed analysis:** Trained standardized logistic models on 2020–21 through 2022–23, selected regularization using 2023–24, refit on all training/validation games, and evaluated on held-out 2024–25 games. Sampled up to 16 regulation states per game. The baseline uses score, time, possession and past-updated Elo strength; the augmented model adds L2, recent foul count, bonus/team fouls and a smoothed cumulative WMI using only completed next-two windows.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| added foul features: held-out log loss change | 6.29e-05 | [-0.00016, 0.00029] | 0.59258 | 0.69345 | 19,680 / 1,230 | loss change; negative improves |
| added foul features: held-out Brier change | 2.1e-05 | [-7.28e-05, 0.000112] | 0.65361 | 0.73366 | 19,680 / 1,230 | loss change; negative improves |

**Interpretation:** The augmented model does not improve held-out log loss or Brier score. Both point changes are slightly worse and their game-bootstrap intervals include zero. There is no demonstrated predictive benefit from this feature set and model.

**Limitations and research scope:** This is a real chronological test of this specification, not a proof that no richer model can benefit. No tracking, active lineups, player foul trouble or advanced sequence architecture was included. Elo starts at 1500, uses K=20 and 65 home-rating points, and shrinks 25% toward 1500 each offseason. Validation chooses C from 0.1, 1 and 10; test games do not choose it. Prior reports had only within-season splits; this test is stronger.

| Model | ROC-AUC | Average precision | Log loss | Brier | 10-bin ECE |
|---|---:|---:|---:|---:|---:|
| state_and_strength | 0.847276 | 0.872262 | 0.471362 | 0.158473 | 0.012496 |
| state_strength_and_fouls | 0.847241 | 0.872207 | 0.471425 | 0.158494 | 0.012305 |

ROC-AUC/average precision: higher is better. Log loss/Brier/ECE: lower is better. Average precision uses tie-aware scoring; ECE depends on binning and is secondary.

### H18. WMI versus foul volume and consequences (additional hypothesis)

**Question:** Does high WMI necessarily imply a large officiating impact? (Additional supplied hypothesis.)

**Executed analysis:** Compared full-game research WMI with counted foul volume, absolute foul differential, absolute free-throw differential and summed absolute baseline win-model movement through foul possessions. These comparison quantities use regulation only, matching the win model's domain. Bootstrapped games for Spearman intervals.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| WMI versus foul_volume | 0.08817 | [0.03306, 0.1429] | 0.00197 | 0.00677 | 1,230 / 1,230 | Spearman correlation |
| WMI versus abs_foul_difference | 0.0162 | [-0.04551, 0.07373] | 0.57031 | 0.69345 | 1,230 / 1,230 | Spearman correlation |
| WMI versus abs_fta_difference | 0.04807 | [-0.00692, 0.10333] | 0.09198 | 0.20236 | 1,230 / 1,230 | Spearman correlation |
| WMI versus foul_wp_movement | 0.01705 | [-0.04133, 0.07547] | 0.55025 | 0.68781 | 1,230 / 1,230 | Spearman correlation |

**Interpretation:** WMI has only a weak volume relationship and little relationship to the measured differentials or foul-associated win-probability movement. It is not interchangeable with foul volume or consequence magnitude.

**Limitations and research scope:** Win-probability movement includes the score/clock/possession changes occurring during a foul possession and assumes a possession switch at its end. It is not the counterfactual causal effect of a call and says nothing about whether a call was correct. Full-game WMI versus regulation consequences is a stated scope mismatch in OT games. Previously attempted; rerun with a chronologically trained state model.

## Foul prediction and conditional sequence forecasts

The foul-prediction study asks whether recent history improves predictions of a foul beyond the same basketball-context model. This differs from H17, which predicts the game winner. Evidence for one target does not establish useful information for the other.

`validate_wmi.py` uses fixed logistic regression settings. Its baseline includes offense/defense teams, home defense, period, reconstructed score/time, defending-team foul counts, bonus and late-strategy context. The history model adds five global foul lags and five same-defending-team foul lags. Training expands only through earlier seasons. All possessions are included in the primary comparison; the late-strategy sensitivity excludes every possession satisfying the pre-specified state, regardless of whether a foul occurred.

### Matched foul-occurrence prediction

Both models use exactly the same games and basketball-context variables. The history model adds five global foul lags and five same-defending-team foul lags. Training expands only through earlier seasons, with fixed logistic regression settings and no hyperparameter search. All possessions are included in the primary analysis. A separate sensitivity excludes all pre-specified late-strategy contexts, regardless of whether a foul happened.

| Season / cohort | Games | Context log loss | History log loss | Change (95% game-bootstrap CI) | Brier change |
| --- | --- | --- | --- | --- | --- |
| 2022-23 Regular Season | 1230 | 0.455264 | 0.455223 | -0.000041 (-0.000094, +0.000015) | -0.000008 |
| 2023-24 Regular Season | 1230 | 0.444665 | 0.444583 | -0.000082 (-0.000133, -0.000030) | -0.000022 |
| 2024-25 Regular Season | 1230 | 0.443315 | 0.443260 | -0.000055 (-0.000107, -0.000007) | -0.000010 |
| 2024-25 Playoffs | 84 | 0.481052 | 0.480753 | -0.000299 (-0.000519, -0.000109) | -0.000076 |

Negative change favors adding history. Confidence intervals resample entire games (1,000 draws). Full metrics, equal-game loss changes and late-strategy sensitivity are in prediction_results.csv. Calibration bins and intercept/slope are in calibration.csv; these describe held-out predictions and do not recalibrate test predictions. Historical 2024–25 exploratory results were already known, so the final season is a retrospective holdout rather than an untouched prospective test.

### Conditional next-team and time-to-foul forecasts

The primary replication gate passed, so the pre-specified exploratory follow-up was executed. Team labels are 0=no foul in three possessions, 1=away commits first, 2=home commits first. Time labels are 0=no foul in five possessions or 1–5 for the first foul position, counting the current possession as position 1. Incomplete game-ending horizons are excluded. These are multinomial horizon forecasts; they are not fitted Hawkes or survival models.

| Target | Season | Context log loss | History log loss | Change (paired 95% CI) |
| --- | --- | --- | --- | --- |
| team, 3 possessions | 2023-24 | 0.941639 | 0.941629 | -0.000010 (-0.000054, +0.000033) |
| team, 3 possessions | 2024-25 | 0.940404 | 0.940366 | -0.000038 (-0.000085, +0.000009) |
| time, 5 possessions | 2023-24 | 1.610040 | 1.609708 | -0.000332 (-0.000481, -0.000193) |
| time, 5 possessions | 2024-25 | 1.608651 | 1.608418 | -0.000233 (-0.000397, -0.000077) |

The follow-up uses the same fixed models and earlier-season training rule. These additional outcomes are exploratory, without multiple-comparison-adjusted claims. Statistical improvements can be small in practical terms.

### What the prediction results imply

The improvements in foul prediction are small. The pre-specified resource-allocation rule required paired log-loss intervals below zero in both final regular-season evaluations with no worse Brier score. That condition was met, and the conditional next-team/time follow-up was executed. Passing this rule justifies additional investigation; it does not establish an officiating mechanism or practical deployment value.

The next-team comparisons remain inconclusive. Time-to-foul comparisons show small gains in both evaluated seasons. Those additional outcomes are exploratory and do not inherit the all-hypothesis study's global q-values. The models are multinomial horizon forecasts, not Hawkes processes or survival models.

Calibration bins and intercepts/slopes are saved separately. These diagnostics describe held-out predictions and do not recalibrate test predictions. Calibration is imperfect; lower loss alone should not be described as fully calibrated forecasting. The use of finalized historical feeds also limits conclusions about exact real-time performance.

The H17 win comparison is less encouraging: adding live foul features slightly worsens both log loss and Brier, with intervals spanning zero. The project therefore has evidence of small foul-timing information and no demonstrated win-model benefit from the tested feature set.

## Per-game uncertainty and interval validation

WMI is exactly calculable for an observed sequence, subject to the reconstruction and denominator being defined. An inferential interval requires a separate target and assumptions about the process that generated the game. The uncertainty experiment therefore evaluates coverage for a specified process parameter rather than pretending the observed arithmetic ratio is itself unknown.

Candidate: circular moving-block bootstrap of the raw foul indicator, recomputing all WMI windows after concatenation. Game length 200, 400 synthetic games per scenario, 300 bootstrap draws per interval, seed 20260912. Blocks of 5/10/20 possessions are compared. The oracle is the ratio of expected sufficient statistics for each specified finite-length process, computed by enumerating local five-possession patterns. This is an inferential process parameter, not uncertainty about an already observed arithmetic game score.

| Scenario | Block | Valid / 400 | Coverage | Median width |
| --- | --- | --- | --- | --- |
| independent_low | 5 | 400 | 98.0% | 2.292 |
| independent_low | 10 | 400 | 89.2% | 2.046 |
| independent_low | 20 | 400 | 81.8% | 1.825 |
| independent_typical | 5 | 400 | 98.2% | 1.435 |
| independent_typical | 10 | 400 | 95.8% | 1.355 |
| independent_typical | 20 | 400 | 92.5% | 1.286 |
| positive_dependence | 5 | 400 | 92.5% | 2.557 |
| positive_dependence | 10 | 400 | 90.5% | 2.649 |
| positive_dependence | 20 | 400 | 87.0% | 2.598 |
| strong_dependence | 5 | 400 | 85.0% | 4.959 |
| strong_dependence | 10 | 400 | 89.2% | 5.770 |
| strong_dependence | 20 | 400 | 89.2% | 6.171 |
| negative_dependence | 5 | 400 | 100.0% | 0.830 |
| negative_dependence | 10 | 400 | 97.8% | 0.763 |
| negative_dependence | 20 | 400 | 92.2% | 0.706 |
| rate_shift | 5 | 400 | 89.8% | 2.121 |
| rate_shift | 10 | 400 | 93.2% | 2.627 |
| rate_shift | 20 | 400 | 95.0% | 3.039 |

Nominal coverage is 95%; sampling error for 400 simulations is about 1.1 percentage points at nominal coverage. Circular joins can create artificial foul sequences, particularly when foul probability changes within a game. Finite denominators also make intervals unstable. No interval is released on the website from this experiment: the tested method must demonstrate acceptable coverage across plausible nonstationary basketball contexts, and the inferential target/assumptions must be explained to users. Other bootstrap constructions may behave differently. This is a stress test of one candidate, not evidence that all uncertainty methods fail.

## Verification and reproducibility

Saved verification records report **38 Python tests passed**, including **18 targeted all-hypothesis tests**. Ruff, Git whitespace checks and website unit checks passed. The recorded browser verification covered 1440×1000 desktop and 390×844 mobile views, game search, missing values, parser/reference labels, components, timelines, model tables and mobile overflow. It reported zero browser console errors.

The hypothesis runner completed all 18 sections without a failed analysis block. All 11 checks in its run audit passed, including source schedule coverage, unique possession keys, internal score reconciliation, no remaining negative scoring deltas/durations and finite tested estimates/intervals. All ten downloaded source files matched their recorded byte counts and SHA256 hashes. Final Benjamini–Hochberg q-values were independently recomputed and matched.

Independent score comparison has narrower coverage than internal reconciliation: only 84 matching local schedule rows had known final scores, and all 84 matched. Missing schedule scores were not counted as successful independent checks. Neither automated invariants nor source-event spot checks establish exhaustive possession validity, call correctness or causal identification.

### Event-level checks

The real opening-event fixture for ATL at BOS, game 0022400001, manually specifies 14 possession starts at actions 4, 11, 13, 15, 16, 18, 20, 23, 24, 30, 32, 37, 39 and 41. Counted foul possessions are 9 and 14. It checks offensive-rebound retention, steals, shooting fouls and free-throw grouping. Additional source inspection examines administrative ownership at quarter boundaries and exclusion of offensive fouls.

A MIA at DET overtime sequence checks the distinction between a technical-only ownership segment and a separate retained-ball possession following a made basket. Synthetic tests cover period boundaries, future-overtime invariance, bonus timing, foul exclusions, short history arrays, administrative groups, technical switches, same-team retained possessions and incomplete future horizons.

These are targeted source-event checks, not comprehensive film review.

### Implementation and research artifacts

| File or directory | Role |
|---|---|
| `wmi_possessions.py` | Shared possession reconstruction, clock handling and contextual fields |
| `wmi_utils.py` | WMI helpers, short history-window handling and delegation to the shared parser |
| `validate_wmi.py` | Pinned-source verification, possession datasets, audit comparisons and matched foul prediction |
| `forecast_foul_sequences.py` | Conditional next-team and first-foul-position models |
| `validate_wmi_intervals.py` | Simulation-based interval coverage evaluation |
| `run_all_wmi_hypotheses.py` | Separate rich-event reconstruction, all 18 analyses, audits and report generation |
| `run_wmi_expansion_analysis.py` | Earlier exploratory analysis retained as historical work |
| `research/validation_2026_09_12/` | Six compressed possession partitions, predictions, calibration, residuals, comparisons, forecasts, interval results, protocol, dictionaries, manifests and verification |
| `research/hypotheses_2026_09_12/` | All 77 estimates, coefficients, event samples, challenge matches, crew pairs, window components, held-out predictions, source locks and audit records |
| `site-data/` | Recalculated game summaries, reference summary and 6,084 foul timelines |
| `tests/` | Parser, statistical and website guards, including the real opening-event fixture |
| `index.html`, `site.js`, `styles.css` | Search, game explanations, validation presentation and responsive layouts |
| `.github/workflows/ci.yml` | Python checks and Node 22 website checks |
| `README.md`, `PROJECT/` | Scope, definitions, workflow and project history |

Root dependencies include scikit-learn and scipy alongside the existing scientific stack. The hypothesis package records its own environment requirements. Source/partition/code hashes, environment versions, sample inventories and failures are retained so a numerical result can be traced to inputs and implementation. Earlier prediction claims in the August exploratory report are explicitly superseded by the matched context/history validation.

From the project root, the hypothesis runner supports complete execution and `--fetch-only`, `--prepare-only` and `--report-only` modes:

```bash
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python run_all_wmi_hypotheses.py
python validate_wmi.py
python forecast_foul_sequences.py
python validate_wmi_intervals.py
python -m pytest -q
node tests/test_site.cjs
```

The validation study verifies pinned input hashes. Its `--evaluate-only` option uses saved possession partitions. Small development builds must use a separate output directory so they cannot overwrite full research artifacts. The hypothesis runner reuses cached research tables; a clean reconstruction from raw inputs requires an empty research cache. Neither automated reproduction nor passing tests substitutes for independent replication of the scientific interpretation.

## Overall assessment and outstanding work

The project supports a useful descriptive question: how do defensive-foul sequences differ across reconstructed possessions and games? It now supplies clearer game explanations, broader empirical coverage and more disciplined separation of inputs, outcomes, uncertainty and interpretation.

The evidence is strongest for small conditional sequence associations, a substantial substitution response to early foul trouble, and a sharp descriptive decline in take-labeled fouls across the rule comparison. Other findings are weaker or more design-sensitive. The immediate and continuation components point in opposite directions; team alternation is highly sensitive to defensive-opportunity controls; close-game, bonus and playoff sequence interactions are not clearly established. Crowd effects, stable crew profiles and optimal benching policy remain unresolved. WMI has only a weak association with foul volume and little association with the measured consequences.

Prediction results set a practical boundary. Recent history produces small gains in some foul-occurrence and foul-timing comparisons, but next-team forecasts remain inconclusive and the tested win model does not improve. A statistically detectable association is not automatically a useful forecasting product. The interval experiment also provides an explicit reason to withhold the tested per-game uncertainty procedure.

The following work remains necessary or unresolved:

1. **Unify reconstruction and anomaly treatment.** Reconcile the two parsers, their possession counts, and the four-game backward-clock quarantine before treating the analyses as one canonical release.
2. **Broaden independent possession validation.** Expand event adjudication and film checks for retained-ball cases, administrative sequences, special penalties and revised events.
3. **Improve opportunity measurement.** Validated lineups, drives, paint touches, contests and matchup information are needed to separate foul opportunities from whistle behavior more credibly.
4. **Validate predictions prospectively.** Evaluate on genuinely unseen games with information available at the prediction time, rather than only finalized historical feeds.
5. **Develop and validate a suitable uncertainty method.** Clarify the inferential target and demonstrate reliable coverage under plausible nonstationary game conditions before displaying per-game intervals.
6. **Use defensible causal designs for strategic claims.** Keep/bench/return policy, challenge effects, crowd effects and rule consequences need stronger identification than the current observational comparisons provide.
7. **Treat advanced architectures as proposals until evaluated.** The roadmap's Hawkes processes, transformers, survival approaches and offline reinforcement-learning policies are not all implemented. Their value remains unestablished.

The research and website work described here remain local and uncommitted in the reviewed project state; deployment is not established by this report. All 18 hypotheses have empirical results, but that completion status should never be interpreted as proof that all 18 original claims are true or causally answered.

## Source reports and evidence

The numerical findings are drawn from the project's saved result tables and reports. Public input provenance and source limitations are documented in the hypothesis report and its locked manifests.

- [All 18 hypotheses: complete methods and results](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/hypotheses_2026_09_12/full_hypothesis_report.md)
- [All 77 reported estimates](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/hypotheses_2026_09_12/all_hypothesis_results.csv)
- [Hypothesis run audit](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/hypotheses_2026_09_12/run_audit.json)
- [Validation and forecasting report](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/validation_2026_09_12/report.md)
- [Interval coverage results](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/validation_2026_09_12/interval_coverage.csv)
- [Event-level spot checks](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/validation_2026_09_12/spot_checks.md)
- [Validation verification record](/Users/ryankalfus/Downloads/codex-projects/nba-whistle-project/research/validation_2026_09_12/verification.json)
