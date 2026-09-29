> Historical exploratory report. Prediction claims are superseded by [the September validation study](research/validation_2026_09_12/report.md), which corrects reconstruction and uses matched context/history comparisons.

# NBA Whistle Momentum Index: Executed Expansion Study

Generated: 2026-08-11T21:04:25.275501+00:00<br>
Possession-level study season: **2024-25 regular season**<br>
Random seed: `20260811`

## Executive summary

This report executes every analysis in the expansion brief that the repository's current data can identify without inventing unavailable variables. The possession-level study includes **1,230 games and 244,786 possessions**; **0 requested games failed**. Multi-season comparisons use the stored public result files.

The central result is that the original WMI can be decomposed exactly. In this season the pooled WMI was **0.978** (game-bootstrap 95% CI **0.958-1.001**). Its immediate component was **0.968** (95% CI **0.948-0.989**) and its continuation component was **1.011** (95% CI **1.004-1.019**). The exact product check differs from WMI by only **1.110e-16**.

The cluster-robust context model estimates an odds ratio of **0.909** for a current defensive foul after at least one foul in the previous two possessions (95% CI **0.887-0.931**, p **<0.0001**). This is an association after the controls available here, not proof of an officiating mechanism or intent.

The out-of-sample next-possession model used a chronological, whole-game split (861 train, 184 validation, 185 test games). Its value should be judged primarily by calibration and log loss, not accuracy, because fouls are infrequent.

Taken together, the season shows **slightly lower immediate foul probability after recent fouls**, partly offset by a small continuation effect once a foul occurs. Opposite-team foul transitions occurred more often than a within-game random-mark baseline, but that descriptive result does not isolate officiating from alternating possessions, tactics, or foul opportunities. Predictive lift was weak: the foul model's ROC-AUC was **0.543**, and adding foul dynamics changed live-win log loss only marginally.

## 1. Data and integrity audit

| Dataset | Rows | Rows with WMI | Coverage |
| --- | --- | --- | --- |
| Comparison distribution | 6,727 | 6,727 | 2020-21 to Mar. 2026 snapshot |
| Search dataset | 8,322 | 8,320 | 2019-20 to Mar. 2026 snapshot |

The two headline counts are intentionally different: the comparison distribution contains regular-season comparison games, while the search file also contains 2019-20, playoffs, and play-in games. The search file has **8,322 rows but 8,320 finite/nonmissing WMI values**. The comparison failure log has **503 rows**. This distinction should be stated directly on the website so users do not mistake the headline comparison count for search coverage.

The 2025-26 CDN endpoint returned HTTP 403 during this run. The reproducible possession study therefore uses the latest complete season still available through the NBA mobile feed (2024-25); the stored 2025-26 snapshot remains valid as a game-level comparison artifact.

## 2. Exact WMI decomposition (H2)

| Quantity | Estimate |
| --- | --- |
| P(F=1 \| L=1) | 0.160 |
| P(F=1 \| L=0) | 0.166 |
| Immediate Whistle Persistence Ratio | 0.968 |
| P(N=1 \| F=1, L=1) | 0.304 |
| P(N=1 \| F=1, L=0) | 0.289 |
| Foul Continuation Ratio | 1.011 |
| WMI | 0.978 |
| Factorized product | 0.978 |

Interpretation: the immediate ratio asks whether the current possession contains a defensive foul more often after recent fouls. The continuation ratio asks whether a current foul is followed by another foul within two possessions more often when it was itself preceded by recent fouls. Multiplying them reconstructs WMI exactly.

The **0.978** value here is a pooled possession-level research estimator used for this expansion study, not a new public season-level WMI edition. The active product remains one WMI per game; the mean of the stored 2024-25 game values is **0.953**. A pooled ratio and the arithmetic mean of game ratios are not expected to match.

## 3. Multi-scale decay and empirical time to foul (H3; Model 3 input)

| Window | P(F\|L=1) | P(F\|L=0) | Immediate ratio | Continuation ratio | WMI |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.163 | 0.164 | 0.994 | 0.996 | 0.990 |
| 2 | 0.160 | 0.166 | 0.968 | 1.011 | 0.978 |
| 3 | 0.163 | 0.165 | 0.992 | 1.001 | 0.994 |
| 5 | 0.164 | 0.164 | 1.003 | 1.001 | 1.004 |
| 10 | 0.166 | 0.157 | 1.056 | 1.008 | 1.064 |

Among foul possessions, the empirical probability of at least one later defensive foul within 1/2/3/5/10 possessions was **0.163 / 0.294 / 0.412 / 0.586 / 0.821**. These are descriptive horizons, not a fitted survival model.

## 4. Direction and burstiness (H4; Models 2-4 inputs)

There were **38,943** consecutive foul-to-foul transitions. The next foul was charged to the same team with probability **0.444** and to the opposing team with probability **0.556**. Relative to an exact within-game random permutation of each game's foul-team marks, the Same-Team Repeat Index was **0.898** and the Directional Makeup Index was **1.100**.

The mean gap between foul possessions was **5.86 possessions** (median **4.0**, CV **0.895**, burstiness statistic **-0.056**). These direction indices are descriptive baselines, not context-adjusted proof of makeup calls.

## 5. Game context and sensitivity (H5)

| Context | Possessions | Immediate ratio | Continuation ratio | WMI |
| --- | --- | --- | --- | --- |
| All possessions | 244,786 | 0.968 | 1.011 | 0.978 |
| Likely intentional excluded | 244,247 | 0.949 | 1.011 | 0.959 |
| Close: margin <= 5 | 103,849 | 0.982 | 1.020 | 1.001 |
| Middle: margin 6-14 | 91,580 | 0.956 | 1.011 | 0.966 |
| Blowout: margin >= 15 | 49,357 | 0.952 | 0.994 | 0.947 |
| Fourth quarter / OT | 61,006 | 0.993 | 1.010 | 1.003 |

The intentional-foul rule is a transparent heuristic: a counted fourth-quarter/overtime defensive foul when the offense leads by more than three with <=35 seconds left, or leads by at least one with <=15 seconds left. It is not a validated intentional-foul label.

## 6. Context-adjusted association and decay (H1, H3)

| Term | Odds ratio | Clustered 95% CI | p-value |
| --- | --- | --- | --- |
| Any foul in previous 2 possessions | 0.909 | 0.887-0.931 | <0.0001 |
| Foul exactly 1 possession(s) ago | 0.966 | 0.938-0.995 | 0.0222 |
| Foul exactly 2 possession(s) ago | 0.870 | 0.845-0.895 | <0.0001 |
| Foul exactly 3 possession(s) ago | 1.032 | 1.002-1.062 | 0.0348 |
| Foul exactly 4 possession(s) ago | 0.929 | 0.902-0.956 | <0.0001 |
| Foul exactly 5 possession(s) ago | 1.020 | 0.990-1.050 | 0.1980 |

Both models use a binomial logit link and game-clustered standard errors. Available controls are score difference, absolute margin, seconds remaining, period, offense, defense, and whether the defending team is home. Missing opportunity controls—drives, paint touches, shot type, lineups, bonus, player foul trouble, and crew—mean the coefficient remains associational and potentially confounded.

## 7. Home, postseason, and crowd-era comparisons (H7-H9)

The raw possession foul rate was **0.163** when the home team defended and **0.165** when the away team defended (difference **-0.002**). This measures call frequency, not correctness or favorability.

| Comparison | N | Group A mean | Group B mean | A-B (bootstrap 95% CI) |
| --- | --- | --- | --- | --- |
| Playoffs minus regular season | 503 vs 7,786 | 0.931 | 0.960 | -0.029 (-0.058, -0.001) |
| 2019-20 bubble minus pre-pause | 172 vs 971 | 0.942 | 0.957 | -0.015 (-0.070, 0.040) |

| Season | Games | Mean game WMI | Median game WMI |
| --- | --- | --- | --- |
| 2020-21 | 1,080 | 0.978 | 0.925 |
| 2021-22 | 923 | 0.933 | 0.874 |
| 2022-23 | 1,230 | 0.985 | 0.942 |
| 2023-24 | 1,230 | 0.972 | 0.920 |
| 2024-25 | 1,230 | 0.953 | 0.903 |
| 2025-26 | 1,034 | 0.934 | 0.881 |

The bubble comparison is an era contrast, not a causal estimate: team composition, game type, restart selection, and scheduling also changed. The playoff comparison is at the game-WMI level and does not adjust possession context.

## 8. Reliability and ratio instability

In the 2024-25 possession sample, **3 of 1,230 games** had `n1 < 30` or `n0 < 30`. Approximate 10-possession circular moving-block intervals were available for **1,230 games**; their median width was **1.269**, and **85.0%** contained 1. These intervals resample derived possession rows in blocks; a production release should bootstrap raw games/events and pre-register the reliability threshold.

Across the stored comparison distribution, the Spearman correlation between WMI and the share of possessions with `L_t=1` was **-0.088**. The correlation between `|log(WMI)|` and `n1` was **-0.107**; a negative value is consistent with more extreme ratios when the recent-foul group is smaller. The website should show `n1`, `n0`, both component means, and an interval/reliability flag alongside every game value.

## 9. Next-possession foul prediction (Model 1)

| Model | ROC-AUC | PR-AUC | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- | --- |
| Historical-rate baseline | 0.500 | 0.159 | 0.1329 | 0.4360 | 0.0053 |
| Context + foul history | 0.543 | 0.174 | 0.1326 | 0.4347 | 0.0053 |

The split is chronological and keeps every possession from a game in one partition. The test set contains **185 games and 36,562 possessions**. The full model uses only information available at or before the current possession plus current game state; it does not use `N_t`, final WMI, or future outcomes.

### Expected-foul residual examples from the held-out test games

| Direction | Game ID | Date | Observed | Expected | Residual |
| --- | --- | --- | --- | --- | --- |
| More than expected | 0022401102 | 20250401 | 48.0 | 28.6 | 19.4 |
| More than expected | 0022401083 | 20250330 | 47.0 | 32.4 | 14.6 |
| More than expected | 0022401067 | 20250328 | 48.0 | 34.0 | 14.0 |
| More than expected | 0022401072 | 20250328 | 41.0 | 29.3 | 11.7 |
| More than expected | 0022401163 | 20250409 | 40.0 | 28.9 | 11.1 |
| Fewer than expected | 0022401186 | 20250413 | 19.0 | 36.7 | -17.7 |
| Fewer than expected | 0022401156 | 20250409 | 14.0 | 31.4 | -17.4 |
| Fewer than expected | 0022401182 | 20250411 | 15.0 | 30.4 | -15.4 |
| Fewer than expected | 0022401200 | 20250413 | 15.0 | 30.0 | -15.0 |
| Fewer than expected | 0022401087 | 20250330 | 24.0 | 38.8 | -14.8 |

These are model residuals, not evidence of officiating error. They rank games where foul volume differed from this limited model's expectation and are appropriate leads for deeper review.

## 10. Exploratory live win prediction (H17; Model 6)

| Model | ROC-AUC | Brier | Log loss | ECE |
| --- | --- | --- | --- | --- |
| Game state only | 0.863 | 0.1528 | 0.4518 | 0.0456 |
| Game state + foul dynamics | 0.863 | 0.1527 | 0.4513 | 0.0448 |

This is a diagnostic comparison, not a deployable win-probability model. It omits pregame team strength and uses repeated possession snapshots within held-out games. Any incremental gain from foul features must be validated across seasons before it can support the claim that foul dynamics add information beyond ordinary game state.

## 11. Hypothesis execution ledger

| Hypothesis | Status | What this run establishes |
| --- | --- | --- |
| H1 | Completed, limited controls | Cluster-robust logistic model with score, time, period, teams, and game state. |
| H2 | Completed | Exact immediate/continuation decomposition. |
| H3 | Completed | Lag effects at possession distances 1-5 plus multi-scale WMI. |
| H4 | Completed descriptively | Same-team and opposite-team transition indices against shuffled-mark expectation. |
| H5 | Completed descriptively | Close/middle/blowout and intentional-foul sensitivity. |
| H6 | Not identified | Bonus and team-foul state are absent. |
| H7 | Completed at game level | Regular-season/playoff WMI comparison; no possession-level playoff controls. |
| H8 | Partial | Home-defense foul rate is available; call accuracy is not. |
| H9 | Partial | Bubble/pre-pause game-level comparison without attendance counts. |
| H10-H12 | Not identified | Player, lineup, drive, contest, and substitution features are absent. |
| H13 | Not identified | Transition opportunities and validated take-foul labels are absent. |
| H14 | Not identified | Challenge outcomes are not assembled. |
| H15 | Not identified | Officiating crew identifiers are absent. |
| H16 | Not run | Possession scoring outcomes need a dedicated outcome table and temporal design. |
| H17 | Exploratory completion | Past-only foul features added to a chronological live win model. |
| H18 | Partial | WMI is compared with foul exposure and game length, but not win-probability leverage. |

## 12. Predictive-model execution ledger

| Model | Status | Result |
| --- | --- | --- |
| 1. Next-possession foul | Completed | Chronological baseline vs logistic context/history model. |
| 2. Next foul team | Partial | Observed marked transitions; no fitted multiclass model. |
| 3. Time to next foul | Partial | Empirical possession-gap distribution; no survival regression. |
| 4. Marked Hawkes | Not fit | Mark transitions and decay horizons establish inputs, not a Hawkes estimate. |
| 5. High-WMI game | Not fit | Pregame team, rest, crew, and matchup features are absent. |
| 6. Live outcome | Exploratory | Game-state model compared with a past-only foul-feature model. |
| 7-8. Foul-out/policy | Not fit | Player state and substitution actions are absent. |
| 9. L2M correctness | Not fit | L2M labels are absent and selected, not population-representative. |
| 10. Challenge outcome | Not fit | Challenge labels and outcomes are absent. |

## 13. What the current data cannot answer

The brief's player residuals, foul-trouble strategy, bonus pressure, foul consequence value, L2M accuracy, challenge response, take-foul policy, crew stability, player foul-out prediction, optimal substitution policy, and full Hawkes/survival models require variables not present in the current analysis table. Running those models now would substitute proxies for their stated targets and create false precision.

The next data build should add, in order: (1) foul-committing and fouled-player IDs plus validated subtype/free-throw consequences; (2) team foul and bonus state; (3) action-level outcomes and possession points; (4) lineups and player foul counts; (5) crew IDs; (6) challenge/review outcomes; (7) L2M labels; and (8) opportunity measures such as drives, paint touches, transition, and shot zone.

## 14. Recommended product changes

1. Keep original WMI unchanged, but display it to three decimals with percentile, `n1`, `n0`, numerator, denominator, and an interval/reliability label.
2. Add the Immediate Whistle Persistence Ratio and Foul Continuation Ratio beside WMI; they explain *why* a game scored as it did.
3. Add same-team/opposite-team foul transitions and a possession timeline, clearly labeled descriptive.
4. Add 1/2/3/5/10-possession windows as an analysis view, not five new headline metrics.
5. State prominently that final-game WMI is retrospective because `N_t` uses future possessions. A live feature must be past-only.
6. Explain the comparison/search coverage mismatch and surface logged source-data failures.
7. Do not label an Expected-Foul Residual Index "adjusted" until opportunity variables and external validation are included.

## 15. Bottom line

This run validates the algebraic decomposition, quantifies scale and direction, tests a limited context-adjusted association, and performs leakage-safe chronological prediction. It does **not** establish referee bias, call correctness, conscious makeup behavior, or a causal officiating effect. The scientifically strongest next phase is a richer possession table followed by a pre-registered multi-season expected-foul model, with game-clustered or game-bootstrap inference and a fully held-out season.
