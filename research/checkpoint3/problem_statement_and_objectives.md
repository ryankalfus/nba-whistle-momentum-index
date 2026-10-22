# NBA Whistle Momentum Index: problem statement and objectives

Ryan Kalfus | 22 October 2026 | Proposal for Joe Xiao to review

## Directions considered

1. Describe short sequences of NBA defensive fouls with one transparent score per game. This fits the existing WMI product, but an unadjusted ratio alone cannot distinguish game context from sequence dependence.
2. Test whether past defensive fouls add predictive information beyond known game context. This gives the project a measurable research endpoint and builds on the existing validation work.
3. Explain referee bias or build a live win predictor. The available play-by-play does not identify all foul opportunities, call correctness, or individual whistle responsibility; the existing win-prediction comparison did not improve with foul features.

Selected direction: combine the game-level descriptive product in direction 1 with the focused empirical test in direction 2.

## Concrete problem statement

NBA foul calls can appear to occur in streaks, but these patterns can also arise because teams, score, time remaining, bonus status, and tactics change within a game. A simple sequence statistic cannot establish whether recent fouls contain additional information beyond that context. This project will measure short-term defensive-foul patterns using the Whistle Momentum Index (WMI), explain the components of each game's score, and test whether past foul history improves prediction of the next possession's defensive-foul outcome after accounting for information available before that possession. The intended result is a reproducible empirical paper supported by an interactive game explorer that communicates both the observed patterns and their limits.

## Primary research question

At the start of an NBA possession, does recent defensive-foul history improve prediction of at least one counted defensive foul during that possession, beyond a model using the same available game context?

Secondary descriptive questions: How much of WMI comes from immediate foul occurrence versus subsequent continuation? How often do intervening fouls complicate interpretation of individual lag associations?

## Measurable objectives

1. Establish a consistent analysis dataset. Document source versions, possession rules, exclusions, missing games, and anomalous clocks. Reconcile the validation and hypothesis reconstructions or retain explicitly separate samples with a quantified comparison. Completion evidence: a data dictionary, source manifest, parser comparison, and event audit.
2. Explain the descriptive score. Retain WMI = mean(M_t | L_t=1) / mean(M_t | L_t=0), with M_t=F_t(1+N_t), and the existing global two-possession windows. Report each game's group counts, means, immediate and continuation components, source version, and missing values where appropriate. Completion evidence: components reproduce WMI wherever defined and are inspectable in the explorer.
3. Evaluate incremental prediction. Compare a context-only logistic model with the identical model plus past foul history on the same possessions. Train only on earlier seasons and keep whole games together. Primary metric: paired change in held-out log loss, history minus context. Secondary metrics: Brier score, calibration, and equal-game performance. Report whole-game bootstrap 95% intervals and the season-specific results.
4. Test robustness and sequence interpretation. Report the pre-existing late-strategy sensitivity, regular-season/playoff differences, foul-gap distribution, and intervening-foul rates at specified lags. Explain how changing the conditioning or censoring changes the question. Completion evidence: a sensitivity table with sample sizes and limits; lag associations are not described as isolated causal effects.
5. Ground the paper in published research. Complete at least ten source analyses using the Indigo template, with citations, access status, methods, findings, limitations, and a clear contribution to this project's design. Keep detailed notes traceable to pages or named full-text sections. Completion evidence: the Workspace bibliography, Zotero collection, and source notes.
6. Deliver a usable research product. Provide searchable completed-game WMI, game comparisons, definitions, source labels, and evidence limitations. Completion evidence: functioning search/comparison, readable desktop/mobile views, and accessible research results without meeting-preparation content.

## Intended endpoints and completion rule

The primary scientific endpoint is the paired change in held-out defensive-foul log loss. A negative value favors adding history. The existing internal expansion gate requires the upper 95% interval to be below zero in both 2023–24 and 2024–25 regular-season evaluations, with no worse Brier score. That gate has already passed in the saved retrospective validation. The 2024–25 change is -0.000055 (95% interval -0.000107 to -0.000007), so the observed gain is small. This criterion supports research follow-up; it does not establish practical usefulness or a causal officiating mechanism.

The project is complete when it produces (a) a paper answering the primary question with uncertainty, calibration, sensitivities, and limitations; (b) reproducible data-processing and analysis instructions with parser/sample discrepancies resolved or explicitly quantified; and (c) a game explorer presenting the descriptive WMI transparently. A small or null predictive result is a valid endpoint. A new practical-use threshold or prospective test must be specified before examining new evaluation data.

## Existing work and remaining decisions

The project already contains game scores, possession audits, all-18-hypotheses results, chronological prediction comparisons, and an explorer. The two research reconstructions use different possession groups (1,208,809 validation possessions versus 1,225,902 hypothesis groups); that integration issue must remain explicit. Per-game confidence intervals are withheld because the tested method had inconsistent coverage.

Joe's review should decide whether this central question and paper-plus-product endpoint fit the Indigo project, which missing context variables are essential, and what future evidence would make a small prediction gain useful. Ryan's two preparation assignments are complete once he has read this proposal and can explain the chosen question, the primary metric, and the completion rule. Joe's review remains pending until Joe conducts it.
