> Superseded: use `../checkpoint3/problem_statement_and_objectives.md` and `../checkpoint3/check_off_guide.md` for the completed assignment and current status.

# WMI next-meeting brief

Prepared 22 October 2026 for discussion with Joe Xiao. The prior session identified two next steps: define one problem statement and measurable objectives. The Crimson task page lists 12 November 2026 for the bibliography and Zotero tasks; it does not show the next meeting date.

## Proposed central problem

**Can recent defensive-foul history improve prediction of a defensive foul on the next NBA possession after accounting for the game state known before that possession?**

This is an observational prediction question. The output is a tested comparison and a transparent public explainer, rather than a claim that referees compensate for earlier calls. The existing game-level WMI remains the descriptive companion measure.

## Why this question

The September discussion found that 17 foul-related analyses do not yet form one endpoint. Existing results show slightly lower immediate foul occurrence after recent fouls and slightly higher conditional continuation. Lag patterns oscillate; another foul often intervenes. Existing validation suggests only small predictive gains, so this question gives the project a meaningful way to decide whether the history signal is useful at all.

## Measurable objectives

1. **Reliable inputs.** Reconstruct possession boundaries and counted defensive fouls, audit edge cases, and document exclusions and unavailable source games.
2. **Prediction comparison.** Hold out later seasons by whole game. Compare an identical context feature set with and without past foul history using log loss as the primary metric; report Brier score and calibration as secondary metrics.
3. **Uncertainty and sensitivity.** Resample whole games, compare season and game-type results, and test whether intervening fouls or likely intentional-foul states change the interpretation.
4. **Communication.** Keep one WMI per completed game and show the numerator, denominator, component ratios, group counts, parser version, and timeline where available. Explain that WMI uses future possessions and is retrospective.
5. **Research synthesis.** Read and annotate at least ten sources, identify what each does and does not establish, and use them to motivate the analysis rather than to claim equivalence with WMI.

## Proposed endpoint and decision rule

A paper and site are ready for a v2 research release when the possession audit is reproducible, the matched held-out comparison is documented, and the effect is reported with uncertainty and calibration. If foul history yields negligible or unstable held-out improvement, publish that finding and focus the paper on describing foul sequences and why apparent lag effects are hard to interpret. Do not add live prediction or simulations until this gate is met.

## Evidence already available

- The audited 2024–25 pooled diagnostic decomposition is immediate ratio 0.96864, continuation ratio 1.01136, WMI 0.97965. This is not the average game WMI.
- The 2024–25 context-adjusted recent-foul odds ratio is 0.95298 in the expanded hypothesis study. It is observational and missing some opportunity variables.
- The active public WMI remains one score per game; archived comparison set has 6,727 games. Search includes a broader set and labels recalculated vs original rows.
- Per-game intervals remain withheld because the tested bootstrap coverage was inconsistent.

See `../WMI_comprehensive_project_summary.md`, `../hypotheses_2026_09_12/full_hypothesis_report.md`, and `../validation_2026_09_12/report.md` for full methods and limits.

## Questions to settle with Joe

1. Is the primary deliverable an empirical paper, a validated prediction result, or a research site plus paper?
2. Is next-possession defensive-foul log loss the right primary endpoint? What minimum practical improvement would count as useful?
3. Which context variables must be included before the comparison is credible, particularly foul opportunity, bonus, and late-game strategy?
4. Should an intervening foul reset the sequence being studied? If so, what event-level estimand answers the scientific question?
5. Which citation style and annotated bibliography format does Indigo require? The official template was not included in the material provided.

## Next meeting agenda (30 minutes)

- 0–5 min: approve or revise the problem statement and endpoint.
- 5–15 min: inspect the matched prediction result and the lag/intervening-foul caveat.
- 15–23 min: review ten-source bibliography and gaps.
- 23–30 min: agree on a locked protocol, paper outline, and next milestone.

## Ready-to-say opening

“My project now asks whether recent defensive-foul history adds useful predictive information beyond known game context. WMI remains a descriptive game score. In the existing analysis the immediate and continuation components pull in opposite directions, and lag effects are hard to isolate when another foul intervenes. I’d like to agree on the prediction endpoint and the evidence needed before I build simulations or make stronger claims.”
