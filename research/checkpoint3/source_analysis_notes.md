# Source analysis notes

Prepared with AI assistance. These notes distinguish paper findings from implications for WMI. Read the cited pages to check and discuss the argument.

## Source 1: Anderson, K. J., & Pierce, D. A. (2009). Officiating bias: The effect of foul differential on foul calls in NCAA basketball. Journal of Sports Sciences, 27(7), 687–694. https://doi.org/10.1080/02640410902729733

Access: Author manuscript downloaded and methods, results, discussion read; manuscript pagination differs from published article.

Methods and sample: Observational analysis of 365 NCAA men’s games in 2004–05: 272 conference home games and 93 neutral games. First-half fouls only to reduce intentional-fouling confounding. Binomial-independence comparison and logistic models of which team receives the next foul, controlling score/lead and conference; reports sensitivity to clustering by game.

Findings: More accumulated fouls on a team predicted a lower probability that the next foul was called against it. Home-game net-foul coefficient −0.1180 and marginal effect −0.0295; neutral-game coefficient −0.1469. Both models have pseudo-R² below .02. Leading and visiting teams were also more likely to receive the next foul.

Limitations: Recorded calls do not reveal true infractions or officiating intent; changing aggression/strategy remains an alternative. NCAA first halves from one season do not establish NBA effects. This models next called foul conditional on a foul occurring, rather than the next possession’s foul probability.

Use in WMI: Provides the closest foul-history predecessor and motivates foul differential and score controls. WMI must distinguish balancing across teams from persistence on the same defending team and cannot convert association into proof of make-up calls.

Evidence locations:
- Manuscript PDF pp. 8–11: hypotheses and methods; 365 games, first-half restriction, logistic specifications.
- Manuscript PDF pp. 11–13 and Tables 1–2 on PDF pp. 22–23: results.
- Manuscript PDF pp. 13–17: discussion and player-behavior alternative.

## Source 2: Gong, H. (2022). The effect of the crowd on home bias: Evidence from NBA games during the COVID-19 pandemic. Journal of Sports Economics, 23(7), 950–975. https://doi.org/10.1177/15270025211073337

Access: Published full text downloaded from Rice institutional repository and methods, results, discussion, conclusion read.

Methods and sample: 30,695 foul actions from 1,679 qualifying NBA regular-season games, 2017–18 through 2020–21; excludes neutral bubble games. Separates incorrect calls from incorrect non-calls using league reviews. Linear probability models with home/fan interaction, team/referee and calendar fixed effects, game-clustered errors; compares crowds with empty arenas.

Findings: No evidence that crowd presence changes home-versus-away treatment overall in this close-game sample. Fans associated with a 2.3 percentage-point increase in missed offensive-foul calls, while home players had 2.4 percentage points more missed loose-ball fouls; subgroup findings do not generalize to all foul categories.

Limitations: Close games and final two minutes/OT only; regular-season scope; no-fan games all from pandemic season and league review is the correctness benchmark. Observational pandemic comparison cannot fully isolate every simultaneous change. A non-significant interaction is not proof that crowds never matter.

Use in WMI: Supports home status and game context as controls while showing why foul type and called/non-called denominator matter. Counters a blanket referee-bias narrative and limits transfer from L2M samples to all-game WMI.

Evidence locations:
- Published pp. 955–962: methodology, L2M sample, models, clustering, Table 3.
- Published pp. 963–968: home/fan effects and interaction models.
- Published pp. 969–971: discussion, conclusion, external-validity limits.

## Source 3: Deutscher, C. (2015). No referee bias in the NBA: New evidence with leagues’ assessment data. Journal of Sports Analytics, 1(2), 91–96. https://doi.org/10.3233/JSA-150012

Access: Full publisher PDF read through web tool; local download blocked.

Methods and sample: 113 close 2014–15 games after March 1; 1,229 reviewed events, with logit analysis restricted to 619 genuine fouls.

Findings: No support for home, superstar, or nationality bias; weak underdog preference.

Limitations: Small selected late-game sample; league reviewers may be biased; excludes false-positive calls from regression.

Use in WMI: Correctness labels are needed to evaluate bias; observed call frequency alone is insufficient.

Evidence locations:
- pp. 92–93: sample and logit method.
- pp. 94–95: findings, limitations, Table 4.

## Source 4: Pelechrinis, K. (2023). Quantifying implicit biases in refereeing using NBA referees as a testbed. Scientific Reports, 13, Article 4664. https://doi.org/10.1038/s41598-023-31799-y

Access: Full PDF methods, results and discussion analyzed; not abstract-only

Methods and sample: NBA L2M reports covering 2015–2022; Monte Carlo null distributions for net whistle gain using violation-specific CC/IC/INC base rates; 106 players with at least 100 calls/noncalls; separate analysis of 5,419 personal technical fouls with exposure minutes and referee/player race.

Findings: Combined-season home net whistle gain exceeded simulated expectation by 145.55 (Table 2, p < .01); regular-season estimate 107.7, p=.03; playoff estimate 47.86, p<.01. 2020–2022 combined-period test was nonsignificant (p=.49). Twelve players had positive nominally significant gain; binomial meta-test probability approximately .007. No aggregate evidence for negative player or team bias after that meta-test. Opposite-minus-same-race technical rate difference was .0022 per 48 minutes, simulation p=.33.

Limitations: L2M is selected close-game final-two-minute evidence; do not generalize to every NBA possession. CNC inclusion changes over seasons (6.4/game in 2015 versus almost 14 in 2022), so the analysis excludes that inconsistent denominator. Small-category base rates can be noisy; meta-test assumes uncorrelated player tests; pandemic-period association cannot isolate crowd absence from other changes.

Use in WMI: Provides the strongest justification for distinguishing recorded foul frequency from correctness: WMI has calls, not CC/IC/INC labels. Use pre-possession home/away and game-context controls; L2M should be a separate selected-sample validation rather than a ground-truth label for the full season.

Evidence locations:
- PDF pp. 2–3: L2M selection, CNC problems, simulation design
- PDF pp. 5–7: Table 2, player and technical-foul results
- PDF pp. 7–9: interpretation and limitations

## Source 5: Morgulev, E., Azar, O. H., Lidor, R., Sabag, E., & Bar-Eli, M. (2018). Searching for judgment biases among elite basketball referees. Frontiers in Psychology, 9, Article 2637. https://doi.org/10.3389/fpsyg.2018.02637

Access: Full PDF methods, results and discussion analyzed; not abstract-only

Methods and sample: Observational video-coded subset of 250 attacking-player/defender collisions with defender falling, from a parent set of 501 incidents in the 2009/10 Israeli Basketball Super League; chi-square comparisons plus logistic regression for home status, player reputation, team reputation and relative size.

Findings: 48 of 250 incidents (19.2%) produced an offensive-foul call. Home/away chi-square p=.902; team-status p=.912; size p=.410; logistic regression corroborated no statistically significant predictor among tested factors. Authors explicitly say rarity and small sample made it challenging to look for sequential effects.

Limitations: Offensive fouls with defender falls are a narrow event class, and this is Israeli league evidence rather than NBA defensive-foul evidence. Only 250 selected incidents and uneven groups (e.g., 15 defending-player-favorite cases) limit precision; nonsignificance does not prove no bias. The current analysis concerns call patterns and contextual proxies, not comprehensive independent correctness labeling or a causal identification design.

Use in WMI: Useful counterevidence against assuming every refereeing study finds bias. Supports cautious interpretation of null results, sufficient exposure counts, and an explicit distinction between offensive-collision findings and WMI defensive-foul outcomes.

Evidence locations:
- PDF p. 3: sample, coding and procedure
- PDF pp. 4–5: chi-square comparisons and logistic regression Table 6
- PDF pp. 5–6: sample and sequential-effect limitations

## Source 6: Sors, F., Tomé Lourido, D., Parisi, V., Santoro, I., Galmonte, A., Agostini, T., & Murgia, M. (2019). Pressing crowd noise impairs the ability of anxious basketball referees to discriminate fouls. Frontiers in Psychology, 10, Article 2380. https://doi.org/10.3389/fpsyg.2019.02380

Access: Full PDF methods, results and discussion analyzed; not abstract-only

Methods and sample: Laboratory repeated-measures calm versus pressing crowd audio, with 30 male active referees (Italian youth leagues through national second division), median-split into 15 low/15 high competitive-anxiety participants; 20 expert-consensus clips each paired with both sounds, 40 trials; signal-detection d-prime analyzed with 2×2 mixed ANOVA.

Findings: No main effect of crowd sound (p=.97) or anxiety (p=.69), but interaction F(1,28)=7.33, p<.05, partial eta-squared=.21. High-anxiety referees had lower discrimination under pressing sound (d-prime 1.04 calm versus .73 pressing; paired t(14)=2.24, p<.05, d=.64). Low-anxiety within-participant difference was nonsignificant (p=.11); the study did not identify home/away teams to participants.

Limitations: Small, all-male non-NBA sample; median split is sample-dependent rather than a validated anxiety cutoff. Video/headphone task and two particular sound tracks limit ecological generalization; tracks differ qualitatively and quantitatively. Experimental sound manipulation supports a task-specific effect but does not establish that NBA foul sequences are caused by crowd pressure.

Use in WMI: Supplies a plausible contextual moderator and warns against interpreting pooled effects as universal. WMI cannot claim to measure referee anxiety/crowd mechanism without such variables; home context can be a control but is not a substitute for measured pressure.

Evidence locations:
- PDF pp. 2–3: participants, stimuli and procedure
- PDF p. 4: signal-detection analysis and results
- PDF pp. 5–6: generalizability and implications

## Source 7: Cervone, D., D’Amour, A., Bornn, L., & Goldsberry, K. (2016). A multiresolution stochastic process model for predicting basketball possession outcomes. Journal of the American Statistical Association, 111(514), 585–599. https://doi.org/10.1080/01621459.2016.1141685

Access: Full PDF methods, results and discussion analyzed; not abstract-only

Methods and sample: Multiresolution stochastic process for 25 Hz NBA optical tracking from 2013–14; micro-level player motion combined with macro-level passes, shots, turnovers and possession-end states, with hierarchical spatial sharing across 461 ballcarriers. Fits 90% of data and compares held-out transition log likelihood on the remaining 10%.

Findings: Full hierarchical model outperformed the simpler models for every transition class in Table 1; e.g., shot attempt held-out log likelihood improved from -48.9 thousand (player-only) to -40.7 thousand (full). Spatial effects without hierarchical shrinkage could hurt prediction; pass4 model without shrinkage scored -24.5 thousand versus -20.4 thousand player-only and -18.9 thousand full. Illustrates EPV paths and derived player summaries, rather than a foul-history effect.

Limitations: Explicitly excludes possessions containing fouls because foul type/circumstances are insufficiently annotated. Semi-Markov coarsening can miss coordinated multi-action plays; rebounds simplified to constant team probability and turnover types aggregated. Tracking still omits limb positions and other relevant information; computation and proprietary data access constrain replication.

Use in WMI: Provides a principled template for defining prediction as conditional on information available by time t and for comparing nested context models out of sample. Its foul exclusion means it cannot be cited as evidence that prior fouls predict future fouls; WMI uses a coarser and more accessible information set.

Evidence locations:
- Analyzed version: arXiv:1408.0777v3, February 25, 2016
- PDF p. 5 (printed p. 4): EPV definition, foul exclusion and footnote
- PDF pp. 19–20 (printed pp. 18–19): 90/10 split and Table 1
- PDF pp. 24–25 (printed pp. 23–24): discussion and model assumptions

## Source 8: Sicilia, A., Pelechrinis, K., & Goldsberry, K. (2019). DeepHoops: Evaluating micro-actions in basketball using deep feature representations of spatio-temporal data [Preprint]. arXiv. https://arxiv.org/abs/1902.08081

Access: Full PDF methods, results and discussion analyzed; not abstract-only

Methods and sample: Tracking from 750 NBA 2016–17 games and over 134,000 possessions; stacked three-layer LSTM with learned player embeddings; roughly five-second windows with a 16-frame (~.64-second) blind spot before terminal action. Classifies shot, shooting foul, nonshooting foul, turnover, or null; downsamples null class with K sampled windows per possession; 75/10/15 training/validation/test split.

Findings: At K=2, multiclass Brier score .3598 versus climatology .4920 and Brier skill score .2686; authors report best relative skill among K=1–4. Reliability diagrams broadly track predicted probabilities, including shooting/nonshooting foul labels; tail bin for turnovers contains just one estimate. For 512 assists versus 512 randomly sampled passes, over 72% of assists increased estimated points; distributions differed at .1% level.

Limitations: This PDF is a working preprint with a placeholder DOI; cite arXiv rather than the placeholder. Evaluation uses a downsampling scheme with altered class prevalence; the reported scores cannot be transferred directly to natural-prevalence WMI possession predictions. Method does not clearly document a chronological game-grouped split; do not infer proof of future-season generalization. League-average terminal-action point values omit lineup-specific payoff; micro-action before/after valuation is not a randomized causal effect.

Use in WMI: Demonstrates that shooting and nonshooting fouls can be probabilistic outcome classes using pre-event context. Its blind spot motivates explicit feature cutoff; WMI should group held-out games chronologically, retain natural test prevalence, and compare Brier/log loss for context-only versus added history rather than reproduce tracking architecture.

Evidence locations:
- Analyzed version: arXiv:1902.08081v1, February 21, 2019; ignore manuscript placeholder DOI
- PDF pp. 6–7: 750 games, windows, labels and blind spot
- PDF pp. 11–13: evaluation split, Brier scores and reliability
- PDF pp. 13–15: pass comparison, examples and discussion

## Source 9: Sabag, E., Lidor, R., Arnon, M., Morgulev, E., & Bar-Eli, M. (2023). Teamwork and decision making among basketball referees: The 3PO principle, refereeing level, and experience. Journal of Human Kinetics, 89, 313–326. https://doi.org/10.5114/jhk/169439

Access: Full publisher PDF downloaded; methods, results, discussion, and limitations examined.

Methods and sample: Observational coding of 321 deliberately ambiguous events from 100 Israeli Super League games in 2016–17. Nine elite international referee observers assessed edited clips; two independently assessed each event with a third for disagreement. Excluding 38 cases without consensus left 283 events involving 25 on-court referees (18 national, 7 international). Chi-square, ANOVA and binomial logistic regression related accuracy to primary coverage responsibility, rank, experience and distance.

Findings: Only 109/283 decisions (38.5%) matched expert assessments, reflecting selection of difficult cases, not a representative league accuracy rate. Errors occurred in 49/60 events (81.7%) with incorrect teamwork/coverage responsibility versus 125/223 (56.1%) with correct responsibility (Table4). Table6 reports teamwork as the only statistically significant predictor among teamwork, rank, experience and distance; rank and experience were not significantly associated with accuracy.

Limitations: Purposive selection of contentious plays inflates errors relative to ordinary play; exclusion of unresolved expert disagreement may further affect the sample. Exploratory single-league observational data cannot establish that position causes accuracy; no referee gaze measures were available. Authors explicitly call for validation in NBA and EuroLeague.

Use in WMI: Provides an alternative mechanism for observed foul patterns: positioning and crew coordination can affect detection. WMI play-by-play lacks these variables and cannot infer correctness from call counts. Cite in limitations and motivate optional video validation, not as evidence of sequential make-up calls.

Evidence locations:
- PDF pp. 3–4 (printed 315–316): Methods, Database, Procedures, Statistical Analyses
- PDF pp. 5–8 (printed 317–320): Results and Tables 4, 6, 7
- PDF pp. 10–11 (printed 322–323): Discussion; Limitations and Future Research

## Source 10: Gomez-Gonzalez, C., Dietl, H., & Nesseler, C. (2020). Unbiased decisions among women’s basketball referees. Frontiers in Psychology, 11, Article 566684. https://doi.org/10.3389/fpsyg.2020.566684

Access: Full publisher PDF downloaded; methods, results, discussion, and limitations examined.

Methods and sample: Official statistics for Spanish women’s first and second divisions, 2014–15 to 2018–19: 2,555 matches, 58 teams, 53,398 player-match records. Main homogeneous two-referee analysis drops first-division 2018–19, with full controlled models using 47,258 observations. Linear regressions use fouls per 40 minutes and a fifth-foul indicator, sequential player and match controls and team, season and referee fixed effects; standard errors cluster at player level. Close-game subsample is defined by final margin ≤3 points.

Findings: No significant adverse association with Black identity or foreign nationality in full controlled sample; mixed versus all-male referee composition also lacked significant effects. In close games, foreign players had fewer fouls per 40 minutes (fully controlled coefficient −0.789, SE0.392, p<.05; Table3); this is an observational association. No significant nationality or race effect on fifth fouls among players finishing with four or five; player position and performance controls matter for foul rates.

Limitations: Final margin is an imperfect stress proxy and is future information relative to an in-game prediction; attendance data were unavailable. Race was inferred from photos; all-female referee teams were too rare for strong subgroup conclusions. Calls do not reveal whether contact warranted a foul, and observational null results are not proof that all bias is absent.

Use in WMI: Supports covariate adjustment, exposure normalization and honest treatment of null results. WMI should use only pre-possession information rather than copying final-score or full-game performance controls into prediction.

Evidence locations:
- PDF pp. 3–5: Data and Methods; Empirical Strategy
- PDF pp. 5–7: Tables 2–4 and Results
- PDF pp. 8–9: Discussion and limitations

## Source 11: Wang, R., Chen, L., Wu, Y., & Zhang, Q. (2025). Research on the visual search behavior and decision-making ability of basketball referees. Frontiers in Psychology, 16, Article 1682389. https://doi.org/10.3389/fpsyg.2025.1682389

Access: Full publisher PDF downloaded; methods, results, discussion, and limitations examined.

Methods and sample: Laboratory eye tracking of 20 basketball referees, 10 expert and 10 non-expert. Experts averaged 36.9 years old/15.1 years officiating, non-experts22.3/5.3. Detailed methods describe 10 silent 10–30s clips from the lead-referee perspective, screened for one ambiguous foul or violation and rated by supervisors; participants selected a call after each clip. ANOVAs compared gaze measures and accuracy.

Findings: Table1 reports decision accuracy78% (SD7.89) for experts and46% (SD8.43) for non-experts. Central-area fixation time was80.38% versus53.01%; outer-area fixation time12.90% versus34.49%; number of fixations, duration and entropy did not significantly differ. [uncertain] Exact inferential statistics are internally inconsistent: abstract says20 clips while methods/procedure say10; Table2 accuracy F=.768 conflicts with Results3.6 F=76.800; invalid-area significance is described inconsistently. The group means are recorded as reported rather than used to resolve those discrepancies.

Limitations: Small nonrandom groups differ in age and experience simultaneously; laboratory silent clips omit crowd pressure, game score, movement and remaining time. Lead-referee perspective and small trial count limit transfer to real NBA officiating. Internal numerical/text inconsistencies mean exact inferential statistics should not be relied on without author clarification.

Use in WMI: Background on visual detection as an unmeasured explanation, useful for literature limitations. Do not infer sequential bias from this small gaze experiment, and do not treat its laboratory accuracy as an NBA baseline.

Evidence locations:
- PDF p.1: publication date 13 October 2025
- PDF pp. 2–5: Methods; Participants; Video clips; Procedure
- PDF pp. 6–7: Tables1–2 and Results3.6
- PDF pp. 10–11: Discussion; Limitations and outlook

## Source 12: Shu, F., Zhang, L., Xu, X., & Xu, R. (2026). Situational influences on officiating performance: An analysis of foul calls in the Chinese basketball association league (CBA). PLOS One, 21(2), Article e0342151. https://doi.org/10.1371/journal.pone.0342151

Access: Full publisher PDF downloaded; methods, results, discussion, and limitations examined.

Methods and sample: Event study of 2022–23 CBA official records:18,519 foul events in441games, final18,182calls in439games. Technical/disqualifying fouls, overtime and specified outliers excluded. Independent t tests and binary logistic regressions study which team received a recorded foul (home/away, leading/trailing, higher/lower foul counts), with score differential, foul differentials, quarter, team-strength categories, format and game type. Models are explicitly explanatory, not predictive.

Findings: Higher existing foul counts were associated with relatively fewer additional calls, consistent with balancing at the recorded-call level. Quarter-level more-versus-fewer model reports quarter foul differential OR0.893 and score differential OR1.017 (p<.05). Home-versus-away model has format OR0.913, score differential OR1.019, and quarter foul differential OR0.913 (p<.05); aggregate format comparisons were not significant. Game-level more-versus-fewer model had poor Hosmer–Lemeshow fit; quarter-level model fit was acceptable.

Limitations: Called events alone omit non-call possessions and actual opportunities; cannot identify probability of any foul next possession or call correctness. Single season and coexistence of COVID venue formats limit generalization; strategic behavior, player/bench interactions and psychological factors are unobserved. Whole-season win percentage used for strength would leak future information in prospective WMI prediction. Repeated-event dependence and the exact pre/post-call timing of foul differential need care before adapting the model.

Use in WMI: Direct rationale for comparing sequence history against a context-only baseline and for pre-possession score/foul-state controls. Crucial distinction: this conditions on a call and asks which team, while WMI next-possession incidence includes no-foul possessions; keep estimands separate and do not label associations causal bias.

Evidence locations:
- PDF p.1: authors, metadata, published19February2026
- PDF pp.3–5: Methods, exclusions, variables, analysis
- PDF pp.6–15: Results; especially pp.12,15 regression results
- PDF pp.16–17: Limitations and conclusions

## Source 13: Ziv, G., Lidor, R., Zach, S., Brams, S., & Helsen, W. F. (2020). Gaze behavior of referees in sport—A review. Frontiers in Sports and Active Living, 2, Article 572891. https://doi.org/10.3389/fspor.2020.572891

Access: Full publisher PDF downloaded; methods, results, discussion, and limitations examined.

Methods and sample: Review searched EBSCO Discovery Service and Google Scholar in March2020, English peer-reviewed studies measuring actual gaze variables plus reference scanning. Twelve studies: five association football, three gymnastics, one each softball, handball, rugby and ice hockey; none basketball. Narrative comparison rather than pooled meta-analysis.

Findings: Seven studies reported expertise-related gaze differences while four did not; five reported both gaze and performance differences, and four performance differences without gaze differences. Only three studies measured gaze in real play, and only one examined a referee team; evidence on peripheral vision and shared gaze was scarce. Authors conclude evidence is too limited and contradictory for confident gaze-training recommendations.

Limitations: Small, heterogeneous evidence base with varying expertise definitions, tasks, eye trackers and sample sizes; many studies lack power or multiple-comparison discussion. No included basketball study, so application to NBA is indirect and later work must be considered. Gaze alone does not capture stress, fatigue, anticipation, interpretation or decision correctness.

Use in WMI: Useful methodological review for explaining why WMI should avoid psychological or accuracy claims from a simple sequence association. Supports external-validation limitations and careful separation of task context from mechanism.

Evidence locations:
- PDF pp.1–2: metadata, Literature Search and inclusion criteria
- PDF pp.3–9: sport-specific synthesis and Tables2–3
- PDF pp.10–12: methodological concerns, ecological validity, practical implications

## Supplementary source 1 (abstract only): Gift, P. (2015). Sequential judgment effects in the workplace: Evidence from the National Basketball Association. Economic Inquiry, 53(2), 1259–1274. https://doi.org/10.1111/ecin.12186

Access: Abstract-only supplementary source; full text not obtained; does not count as completed full-text analysis.

Methods and sample: Observational NBA offensive-foul/violation analysis; tests player-behavior explanations. Exact sample and specification [uncertain].

Findings: Abstract reports increased scrutiny of the opposing team following a potentially questionable call; findings for the original violating team inconclusive.

Limitations: Full methods unavailable [uncertain]; abstract cannot establish effect size or robustness.

Use in WMI: Direct sequential-decision precedent, but offensive turnovers differ from defensive-foul WMI.

Evidence locations:
- Publisher abstract only.

## Supplementary source 2 (abstract only): Price, J., Remer, M., & Stone, D. F. (2012). Subperfect game: Profitable biases of NBA referees. Journal of Economics & Management Strategy, 21(1), 271–300. https://doi.org/10.1111/j.1530-9134.2011.00325.x

Access: Publisher abstract-only supplementary source; unverified third-party manuscript not used as primary full-text analysis.

Methods and sample: Compares discretionary and less discretionary turnovers as a player-behavior control. Exact published sample [uncertain].

Findings: Abstract reports evidence favoring home teams, teams trailing within games, and teams trailing in playoff series.

Limitations: Full robustness and identification assumptions [uncertain]; turnover categories do not directly identify defensive-foul bias.

Use in WMI: Motivates negative controls and distinguishing player behavior from officiating.

Evidence locations:
- Publisher abstract only.

