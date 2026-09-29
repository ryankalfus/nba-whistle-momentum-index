# WMI validation protocol

Written before this validation run; this is an internal analysis plan, not an external preregistration. Prior exploratory results for 2024–25 have already been inspected.

- Preserve the WMI equation and global two-possession windows. Correct period boundaries and time reconstruction; archive old outputs and quantify changes.
- Inputs: SHA256-verified, commit-pinned NBA CDN archives for 2020–21 through 2024–25 and 2024–25 playoffs. Compare overlapping 2024–25 mobile-feed results separately from parser changes.
- Prediction origin: reconstructed possession start, using prior recorded score and clock (period start for the first possession). Never use eventual game duration, current possession outcomes, future windows or final WMI as predictors.
- Primary target: at least one counted defensive foul in the current possession.
- Primary comparison: logistic basketball-context model versus the identical model with five foul lags and team direction. Include all possessions; late-game sensitivity excludes ALL possessions in the pre-specified time/margin situations, regardless of outcome.
- Context: offense, defense, home defense, period, known remaining time, margin, reconstructed defensive team foul count and bonus eligibility. Opportunity outcomes from the current possession are stored for description only.
- Expanding-season evaluations: train 2020–21/2021–22, evaluate 2022–23; train through 2022–23, evaluate 2023–24; train through 2023–24, evaluate 2024–25. No hyperparameter search. The 2023–24 season is the development replication; 2024–25 is the final retrospective holdout. Evaluate playoffs separately.
- Primary loss: log loss. Secondary: Brier, ROC-AUC, average precision, calibration intercept/slope and equal-frequency reliability bins. Paired bootstrap resamples entire games, 1,000 replicates. Report possession-weighted and equal-game effects.
- Expansion gate: history must improve log loss with a paired 95% interval below zero in both final regular-season evaluations and must not worsen Brier. Otherwise defer directional forecasting and document the decision. This is a research allocation rule, not a claim of causality.
- WMI uncertainty: show sample counts and denominators now; withhold per-game inferential intervals until a dedicated dependence-aware coverage study validates them. A percentile is not a significance test.
- No inference of referee intent, correctness or causal makeup calls. Missing lineups/drives/paint touches remain explicit limitations.

Conditional follow-up, specified before the primary results: if the gate passes, compare matched context/history multinomial logistic models for (a) the team committing the first foul within the current and next two possessions (home/away/no foul), and (b) the first-foul position within five possessions (1–5/no foul within five). Drop incomplete end-of-game horizons rather than label them no-foul; retain whole-game chronological splits. Evaluate multiclass log loss and paired game-bootstrap differences in 2023–24 and 2024–25. These are exploratory horizon forecasts, not Hawkes or survival-model estimates.
