# Full breakdown of all 17 WMI hypotheses — plus supplied H18

## Executive assessment

All H1–H17 were revisited: earlier analyses were rerun, previously unavailable bonus/player/rule/challenge/crew tests were assembled, and crowd and win-prediction analyses were expanded. The attachment actually lists 18 hypotheses, so H18 is included as an additional section. **Every section has an empirical result; not every original causal claim is identifiable.** This is a separate research package, not a change to the website, public WMI formula or production game files.

The central result is modest: measured recent fouls predict slightly lower immediate foul probability, while the continuation component is slightly higher. A simple smooth-decay or makeup-call interpretation is not supported. Substitution after foul trouble and the decline in take-labeled fouls are much clearer than the proposed strategic or officiating mechanisms. Added live foul features do not improve the held-out win model. The coaching-optimality question remains causally unresolved.

## Data and execution coverage

The source inventory contains **6,084 games**, covering five full regular seasons and all 84 games of the 2025 playoffs. After quarantining 4 games with backward source clocks, the rich event study uses **6,080 games and 1,225,902 possession groups**. The primary 2024–25 sample and all 84 playoff games are unaffected. H9 additionally uses stored 2019–20 and selected attendance-linked game WMI.

| Season | Type | Source games | Retained games |
|---|---|---:|---:|
| 2020-21 | Regular season | 1,080 | 1,077 |
| 2021-22 | Regular season | 1,230 | 1,230 |
| 2022-23 | Regular season | 1,230 | 1,230 |
| 2023-24 | Regular season | 1,230 | 1,229 |
| 2024-25 | Regular season | 1,230 | 1,230 |
| 2024-25 | Playoffs | 84 | 84 |

The attachment is a research roadmap, not a preregistration. Specifications and fallback analyses were developed during this run. Formal and exploratory tests are distinguished below; the results should be independently replicated before publication.

Clock quarantine: 0022000181, 0022000254, 0022000925, 0022301177. The source contains replay clock reversals, an end-game memo with an earlier clock, and one inconsistent shot-event ordering. These complete games were excluded from rich-event fits rather than silently repairing their clocks. The raw cached data and anomalies remain available in `quarantined_clock_events.csv`; legacy game-level H9 does not rely on this clock reconstruction.

### Statistical conventions

Odds ratios and rate ratios have a null of 1; additive differences and correlations have a null of 0. An interaction odds ratio is a **ratio of odds ratios**, not a subgroup's standalone foul probability. Main effects in interaction models apply at the reference history state L2=0. Estimates are not percentage points unless explicitly converted: 0.01 probability/share units = 1 percentage point.

Regression uncertainty is clustered by game; count models use heteroskedasticity-robust game-level errors. Before/after and prediction differences use 1,000 whole-game bootstrap draws; their p-values use a normal approximation to the bootstrap standard error. Crew stability resamples crew identities. Benjamini–Hochberg correction is applied jointly across the 55 reported inferential tests, not separately until something becomes significant. The tables show raw p and final q. Pointwise 95% intervals are not multiplicity-adjusted. Rows without p/q are descriptive estimates, not declarations of a passed formal test. Correlated tests and exploratory specification choices limit the certainty implied by q-values.

### Reconstruction and leakage safeguards

The foul definition and global last-two/next-two formula are unchanged. This separate parser adds explicit period boundaries to ownership-based grouping, measures score before the group's first event, handles regulation/OT clocks without knowing future overtime, and reconstructs foul/bonus counts before the current event. It remains a public-feed ownership approximation, not independently video-validated live control. Dead-ball ownership tagging, special fouls and overturned-event revisions are residual sources of error.

The parser adds 18,029 boundaries across the study relative to ownership-only grouping. Therefore these research values need not match earlier mobile-feed/ownership-only outputs exactly. All game score totals reconcile internally. Of the matching local schedule rows, only 84 have known final scores; those all match. Missing schedule scores are not counted as validation successes. Home/away matches were checked separately.

Live WMI at the start of possession i includes a historical row only after its future-two window has completed (row ≤i−3). The current outcome, future N_t, final-game WMI and future overtime duration never enter win prediction. Whole games remain in chronological training/validation/test partitions. These checks reduce identifiable leakage, but the use of finalized historical play-by-play cannot guarantee reconstruction of the exact feed visible live at the time.

## Hypothesis-by-hypothesis results

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

**Limits and prior coverage:** Partial implementation of the originally proposed full model: these are team fixed effects and game-clustered errors, plus a game-fixed-effect sensitivity—not hierarchical logistic random effects. No validated five-player lineups, drives, matchup tracking, or current legal-contact opportunities are available. Past shot counts are imperfect style proxies. H1 was previously attempted with fewer controls; it was rerun here.

### H2. Immediate persistence versus future continuation

**Question:** Is WMI driven by immediate occurrence or by future continuation?

**Executed analysis:** Decomposed the two-possession ratio exactly into immediate persistence p1/p0 and continuation (1+q1)/(1+q0). Resampled complete games 1,000 times to estimate uncertainty. The displayed combined ratio uses pooled sufficient statistics for this research diagnostic, not the average of game WMI and not a replacement public season metric.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| window 2: immediate | 0.96864 | [0.94879, 0.98789] | — | — | 248,456 / 1,230 | ratio |
| window 2: continuation | 1.01136 | [1.00344, 1.01876] | — | — | 248,456 / 1,230 | ratio |
| window 2: WMI | 0.97965 | [0.95776, 0.99913] | — | — | 248,456 / 1,230 | ratio |

**Interpretation:** Immediate persistence is below one, while continuation is slightly above one. The immediate component dominates, putting the combined ratio just below one. Calling all three numbers positive ‘momentum’ would obscure the result.

**Limits and prior coverage:** These are unadjusted descriptive components with pointwise bootstrap intervals, not independently validated causal mechanisms. One game has an undefined conditional continuation component because a required foul count is zero; its sufficient statistics remain usable in the pooled estimate. Previously run; now rerun with the audited period boundaries.

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

**Limits and prior coverage:** Longer windows change both recent-history exposure and future continuation. They also mix longer-lasting game conditions. They are not direct estimates of a causal decay kernel. The individual-lag regression, rather than comparisons of overlapping ratio intervals, is the formal adjusted test. Previously run; rerun here.

### H4. Same-team versus opposite-team foul direction

**Question:** Does the next foul tend to return to the same team or move to its opponent?

**Executed analysis:** Compared observed transitions with two baselines: randomly rearranged team marks among foul events, and 500 within-game permutations of foul indicators among each team's actual defensive possession slots. The second preserves each team's foul total and its opportunities. Separately fitted current foul probability on whether the defense committed the last foul, conditioning on gap 1–10 and H1 controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| opportunity_conditioned_direction: same_defense_as_last_foul | 0.98607 | [0.94174, 1.0325] | 0.5502 | 0.68781 | 200,810 / 1,230 | odds ratio |
| opposite-team share above random-mark baseline | 0.04967 | [0.04495, 0.05444] | 4.42e-88 | 1.22e-86 | 1,230 / 1,230 | share difference |
| opposite-team share above within-team opportunity permutation | 0.00826 | [0.00341, 0.0131] | 0.000703 | 0.00258 | 1,230 / 1,230 | share difference |

**Interpretation:** The raw random-mark comparison shows about five percentage points of excess opposite-team transitions. After preserving actual defensive opportunities, the excess is only about 0.83 percentage points, still statistically detectable. The lag-conditioned context model does not show a clear same-team effect. Thus the small residual is baseline-sensitive, not proof of makeup calls.

**Limits and prior coverage:** The opportunity permutation controls defensive slots and team game totals, not changing shot opportunities. The adjusted direction coefficient is identified largely by departures from strict possession alternation; this limits its interpretation. Neither test identifies intentional balancing or call accuracy. Previously run with a simpler baseline; the opportunity-preserving test is new.

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

**Limits and prior coverage:** The intentional-fouling heuristic is Q4/OT with ≤35 seconds and offense ahead by >3, or ≤15 seconds and offense ahead by ≥1. It is a state-based proxy, not a validated intentional-foul label. The main sensitivity excludes all eligible observations rather than selectively deleting only foul outcomes. Previously run; the exclusion design was corrected here.

### H6. Bonus status as a modifier of momentum

**Question:** Does entering the penalty change the effect of recent fouls?

**Executed analysis:** Reconstructed the defending team's pre-event foul quota separately for each period, including the final-two-minute rule and OT quota, then tested L2 × bonus. Offensive, technical, and double-personal fouls do not consume the reconstructed normal quota.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bonus_interaction: bonus | 0.80947 | [0.78051, 0.8395] | 5.72e-30 | 1.05e-28 | 248,456 / 1,230 | odds ratio |
| bonus_interaction: L2:bonus | 1.02681 | [0.97223, 1.08446] | 0.34235 | 0.53376 | 248,456 / 1,230 | odds ratio |

**Interpretation:** Bonus status is associated with a lower baseline foul probability in the fitted model, but the bonus-by-history interaction does not establish modified momentum. A baseline bonus association is not evidence for the interaction hypothesis.

**Limits and prior coverage:** Bonus is endogenous to earlier fouls and game behavior. Public foul classifications can miss special-case penalties. This is a reconstruction, not a feed of official live penalty flags, and cannot isolate defender restraint from offensive strategy or whistle thresholds. Newly executed.

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

**Limits and prior coverage:** One postseason is not a universal playoff effect. Playoff team selection, matchups, tactical adjustments and series dependence remain; errors are clustered by game, not by series. Close margin is only a leverage proxy. The last 18 playoff home/date assignments came from the existing project schedule because the separate referee-assignment archive ends earlier. No officials were invented. Previously analyzed at game level; the possession-level comparisons are new.

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

**Limits and prior coverage:** This measures receiving a counted defensive foul, not whether that foul was correct. A home team drawing more fouls may reflect play style. No correctness/noncall labels were joined, and this is not a complete directional-residual or accuracy study. Previously partial; now expanded with context-adjusted sequence interactions.

### H9. Crowd presence and foul sequencing

**Question:** Does crowd presence change sequencing?

**Executed analysis:** Used stored game-level WMI for 88 bubble and 971 pre-bubble regular-season games in 2019–20, adjusting for home and away team identities. Separately regressed stored WMI on recorded attendance per 10,000 spectators with season/game-type controls in the box-score archive's 2,111 matched games.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| bubble_same_season_regular_games: bubble | 0.02238 | [-0.05067, 0.09544] | 0.54814 | 0.68781 | 1,059 / 1,059 | coefficient |
| recorded_attendance_selected_close_game_archive: attendance_10k | -0.03811 | [-0.11961, 0.04339] | 0.35941 | 0.53426 | 2,111 / 2,111 | coefficient |

**Interpretation:** Neither comparison establishes an attendance or bubble sequencing association. The uncertainty leaves room for effects in either direction.

**Limits and prior coverage:** This is partial: there is no reliable three-way normal/restricted/no-crowd classification. Missing attendance was never set to zero. The attendance archive disproportionately covers L2M-qualifying close games. Bubble selection, neutral courts, schedule restart and different teams confound a causal crowd claim. This section uses legacy stored WMI and therefore does not share the rich-CDN research parser used by most other sections. The prior bubble comparison was rerun; the recorded-attendance analysis is new.

### H10. Defender foul trouble and opponent strategy

**Question:** Does foul trouble for an important defender change opponent strategy?

**Executed analysis:** Predefined 30 high-defensive-activity players using prior-season blocks plus steals per event-observed appearance, requiring at least 40 appearances. Examined early second/third fouls, fourth fouls through Q3, and fifth fouls, all with >2 minutes left in the period. Tested immediate substitutions after third versus second early fouls and before/after opponent rim share and points per possession over five opponent possessions.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| substitution_after_third_vs_second_early_foul: threshold | 15.32693 | [7.82327, 30.02771] | 1.79e-15 | 1.64e-14 | 388 / 301 | odds ratio |
| rim-attempt share after minus before trouble | -0.000567 | [-0.03686, 0.03576] | 0.97534 | 0.97534 | 245 / 169 | share difference |
| opponent points per possession after minus before trouble | 0.08245 | [-0.02655, 0.18721] | 0.1151 | 0.2261 | 245 / 169 | points per possession |

**Interpretation:** Coaches are much more likely to substitute after an early third foul than a second. The observed rim-attempt share does not clearly change; the opponent scoring estimate is imprecise. Thus substitution response is supported, but the proposed attack-the-defender mechanism is not established.

**Limits and prior coverage:** Blocks/steals activity is a reproducible proxy, not a validated list of stars or defensive impact. No drives, contests or matchup-level targeting were measured. The rim/efficiency comparison is before/after without matched no-trouble controls, and substitutions change who is on the floor. Newly executed.

### H11. Whether coaches bench foul-troubled players too conservatively

**Question:** Are coaches systematically too conservative in benching foul-troubled players?

**Executed analysis:** Compared keeping versus immediately benching the predefined defenders after qualifying third/fourth/fifth fouls. Modeled the player's team net points over the next five global possessions with player, personal-foul-count and period indicators plus score/time controls.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| observational_keep_vs_bench: keep | -0.17886 | [-0.97355, 0.61583] | 0.65913 | 0.73366 | 245 / 169 | coefficient |

**Interpretation:** The keep-versus-bench estimate is imprecise and does not demonstrate that either policy is better. This analysis cannot determine whether coaches are too conservative.

**Limits and prior coverage:** This is an executed observational comparison, not an optimal-policy test. Coach knowledge, injuries, matchup, replacement quality and lineups confound the decision; later returns were not modeled. A credible causal answer requires validated lineup histories and a defensible policy-identification design. Newly executed, with causal identification explicitly unresolved.

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

**Limits and prior coverage:** No drives, disputed noncalls, unfavorable rulings or legal-contact judgments were inferred. Fatigue, substitutions and selection into a foul event can create before/after differences. The 12,604 shot-mix events are a selected subset of the 38,296 draw events, not all player possessions. Newly executed.

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

**Limits and prior coverage:** The denominator is all possessions, not transition opportunities. The common label includes more than perfectly classified transition-take events; documentation or classification could change. Two seasons and an offseason gap, with no unaffected comparison group, cannot isolate the rule from concurrent changes. The points comparison is not expected points conceded relative to a no-foul counterfactual, and retained-possession tagging can affect aggregation. Newly executed.

### H14. Whistle patterns after successful challenges

**Question:** Does a successful challenge change the next whistle pattern?

**Executed analysis:** Identified explicit Challenge replay decisions in the mobile feed, aligned them to the rich-CDN game clock, and compared foul rates in ten possessions before/after. The reviewed possession was excluded. Matched no-challenge windows within the same game/period on margin, remaining time and recent foul history, excluding nearby challenges. Tested successful-challenge difference-in-differences and successful versus unsuccessful challenges.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| successful challenge versus matched no-challenge change | -0.02114 | [-0.03903, -0.00474] | 0.01668 | 0.04588 | 809 / 638 | foul probability difference |
| successful_vs_unsuccessful_challenges: success | 0.02621 | [-0.00472, 0.05714] | 0.09668 | 0.20451 | 1,213 / 870 | coefficient |

**Interpretation:** Successful challenges are followed by lower foul rates relative to the selected no-challenge windows, but the success-versus-failure contrast does not clearly separate successful challenges from challenges generally. Treat the result as suggestive and design-sensitive.

**Limits and prior coverage:** All reviewed call types are included, not only foul calls. Matching is approximate and challenge timing is strategic. The pre-window can include the disputed incident, encouraging regression to the mean. Windows may overlap; game bootstrap accounts for within-game dependence but does not solve selection or matching bias. Newly executed.

### H15. Stability of referee-crew sequencing profiles

**Question:** Do exact referee crews have stable sequencing profiles across seasons?

**Executed analysis:** Built unordered triples of assigned officials and each crew-season's mean log immediate-persistence component. Matched exact triples in adjacent seasons and measured Spearman correlation, bootstrapping complete crew identities to preserve repeated years.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / crews | Unit |
|---|---:|---|---:|---:|---:|---|
| same assigned crew year-to-year log-immediate correlation | 0.0801 | [-0.06616, 0.22404] | 0.28194 | 0.48458 | 176 / 172 | Spearman correlation |

**Interpretation:** The cross-season correlation is about 0.08, with an interval spanning zero. This does not establish observable stability. Because crew-season estimates are extremely noisy, it also cannot support a dependable ranking or rule out stable latent differences.

**Limits and prior coverage:** No exact crew had at least two games in BOTH matched years, so the originally attempted three-game minimum yielded zero pairs. The fallback includes all repeated triples and was chosen after inspecting coverage. Noise attenuates correlations; team/matchup assignment is not randomized. These are crew-game associations, never attribution of another official's calls or evidence about intent. Newly executed with weak measurement reliability.

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

**Limits and prior coverage:** This is an in-sample conditional-association analysis, not an out-of-sample scoring forecast. Five global possessions give unequal offensive opportunities; net points are oriented to the offense at t. FTA, turnovers and rim attempts pool both teams. Game-clock time is a pace proxy, not real elapsed time. Current F_t, future N_t and final WMI are not predictors. Previously not run; newly executed here.

### H17. Live foul features and win prediction

**Question:** Do live foul-history features improve win-probability predictions?

**Executed analysis:** Trained standardized logistic models on 2020–21 through 2022–23, selected regularization using 2023–24, refit on all training/validation games, and evaluated on held-out 2024–25 games. Sampled up to 16 regulation states per game. The baseline uses score, time, possession and past-updated Elo strength; the augmented model adds L2, recent foul count, bonus/team fouls and a smoothed cumulative WMI using only completed next-two windows.

| Test | Estimate | 95% CI | Raw p | BH q | Observations / games | Unit |
|---|---:|---|---:|---:|---:|---|
| added foul features: held-out log loss change | 6.29e-05 | [-0.00016, 0.00029] | 0.59258 | 0.69345 | 19,680 / 1,230 | loss change; negative improves |
| added foul features: held-out Brier change | 2.1e-05 | [-7.28e-05, 0.000112] | 0.65361 | 0.73366 | 19,680 / 1,230 | loss change; negative improves |

**Interpretation:** The augmented model does not improve held-out log loss or Brier score. Both point changes are slightly worse and their game-bootstrap intervals include zero. There is no demonstrated predictive benefit from this feature set and model.

**Limits and prior coverage:** This is a real chronological test of this specification, not a proof that no richer model can benefit. No tracking, active lineups, player foul trouble or advanced sequence architecture was included. Elo starts at 1500, uses K=20 and 65 home-rating points, and shrinks 25% toward 1500 each offseason. Validation chooses C from 0.1, 1 and 10; test games do not choose it. Prior reports had only within-season splits; this test is stronger.

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

**Limits and prior coverage:** Win-probability movement includes the score/clock/possession changes occurring during a foul possession and assumes a possession switch at its end. It is not the counterfactual causal effect of a call and says nothing about whether a call was correct. Full-game WMI versus regulation consequences is a stated scope mismatch in OT games. Previously attempted; rerun with a chronologically trained state model.

## What has and has not been completed

Completed: re-execution of the existing hypotheses, new empirical attempts for all previously unrun H1–H17 sections, supplemental H18, explicit sample sizes and effects, uncertainty and global multiple-test correction, new public-data joins, complete playoff coverage, a chronological win-prediction comparison, reproducible code and machine-readable outputs.

Still not established: causality of referee behavior, call accuracy, the optimum keep/bench/return policy, a reliable restricted-attendance natural experiment, video-level attack/contest changes, transition-opportunity-adjusted causal rule impact, or precise stable crew rankings. These are identification/data limits, not analyses that were silently skipped. The ten separate advanced model architectures elsewhere in the attachment—such as Hawkes processes, transformers and offline reinforcement learning—are not all implemented by this hypothesis-focused run.

## Reproduction and audit trail

From the project root, run `OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python run_all_wmi_hypotheses.py`. The runner downloads commit-pinned public archives into an ignored cache, builds separate tables, executes the hypotheses and regenerates this report. `--fetch-only` and `--prepare-only` stop at those stages. `--report-only` rebuilds the report from already executed results. Run `pytest -q tests/test_all_wmi_hypotheses.py` for the new targeted guards.

Files in this research folder: `all_hypothesis_results.csv` contains every reported estimate, interval, p and q; `analysis_details.json` contains formulas, sample details and prediction features; `run_audit.json` records automated coverage/scoring checks and hashes; `source_lock.json` and `source_manifest.json` pin the raw sources; `analysis_failures.json` lists failed analysis blocks. Section-specific CSVs retain model coefficients, matched events, crew pairs, component denominators and held-out predictions. The ignored `cache/` contains rich event and possession Parquet tables. Existing public datasets, earlier research outputs and unrelated working-tree changes were not overwritten by this runner.

Automated run audit: PASS. Each check is independently listed in `run_audit.json`. The tests validate targeted invariants, not every basketball interpretation or causal assumption.

## Sources and provenance

1. [NBA-data public archive](https://github.com/shufinskiy/nba_data): rich NBA CDN event archives for regular seasons 2020–21 through 2024–25, 2025 playoffs, and the 2024–25 mobile archive for replay decisions. These are third-party archived copies of NBA feeds, not a claim of direct live NBA API verification. Exact commits, URLs, byte counts and SHA256 values are saved locally.

2. [L2M research data archive](https://github.com/atlhawksfanatic/L2M): referee assignments and selected box/attendance data. Its close-game selection limits representativeness, and its assignment coverage stops before the final rounds of the 2025 playoffs.

3. [NBA Rule 12 — Fouls and Penalties](https://official.nba.com/rule-no-12-fouls-and-penalties/): basis for regulation/OT team-foul quotas and late-period penalty reconstruction.

4. [NBA transition-take-foul rule explanation](https://official.nba.com/video-transition-take-fouls/): policy context for the 2022–23 comparison; the archive's labels are an imperfect operational measure of the rule's targeted events.

5. Existing local project game-search data: home/date fallback for 18 playoff games and stored WMI for H9. Its content hash is recorded in `run_audit.json`. The user's supplied roadmap defines the hypothesis questions, not the empirical findings.
