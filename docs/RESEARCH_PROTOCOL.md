# Recorded defensive-foul prediction protocol

Original date: 2026-11-02. Updated: 2026-11-09. Version: `v2-draft-4`. Status: DEVELOPMENT, NOT PREREGISTERED OR LOCKED.

## Current development scope

On 2026-11-07 the user discontinued the 303-game review campaign. The preserved fourteen-game pilot is a development pool for bounded source/parser/clip diagnostics, not a new mandatory quota of full-game reviews or a replacement population-validation sample. The frozen 303-game audit and its 1%/95% policy remain unchanged historical artifacts, with their original blocked result; they are inactive and are not requirements for software completion. No smaller audit is declared passed and no numerical population-accuracy claim follows. The scientific estimand and the confirmatory safeguards below remain unchanged. Any later scientific validation design must be specified separately rather than silently reviving the larger campaign or relaxing its frozen gate.

On 2026-11-08 the user authorized a separate provisional exploratory real-data analysis. Its [versioned contract](EXPLORATORY_ANALYSIS.md) fixes the first retrospective cohort, whole-game quality exclusions, chronological split and existing matched-model specification before fitting. It uses previously exposed data, reports every exclusion/unknown and preserves all original rows/eligibility. Its local output cannot satisfy the strict audit/promotion/confirmatory route. No meaningful-gain threshold, unseen-cohort status, live feature availability, causal effect or public empirical claim is inferred. Actual results remain in ignored local outputs.

On 2026-11-09 the user supplied the research meeting's assignment. [MEETING_ALIGNMENT.md](MEETING_ALIGNMENT.md) declares a separately versioned two-model specification, `meeting-ab-v1` (additive L2 logistic shared context versus the identical design plus one flag for a counted defensive foul in either of the previous two global possessions), as the primary comparison for the intended paper. The four-model ladder below remains the existing `matched-model-v1` comparison and a labeled sensitivity. The estimand, availability rules, exposure requirements and confirmatory safeguards are unchanged.

## Primary question and target

At the start of an eligible possession, does past counted defensive-foul history improve prediction of at least one recorded counted defensive foul during that possession, beyond the same known basketball context? The unit is a reconstructed possession; the primary target is binary. Multiple counted fouls within one possession remain in the event ledger but map to one positive target.

This is a predictive comparison of fitted algorithms, not an identification of referee intent, contact opportunities, call correctness, or a causal effect. Controlling bonus/team-foul state asks for information beyond that state, not a total causal effect of past fouls.

## Data and reconstruction contract

Retain source events, hashes, source versions, and event ordering. Declare source ownership reconstruction separately from actual live-ball control. Use explicit home/away metadata where available. Invalid/ambiguous ordering, clock regressions, duplicate conflicts, unresolved ownership, and unsupported foul labels receive reasons and quarantine or audit flags; do not silently zero-fill them.

Possessions end with a control transfer or a period boundary. Offensive rebounds and retained-ball fouls continue a possession. Administrative events cannot create possession opportunities. Special foul/free-throw/and-one sequences require explicit handling and adjudicated tests. Never infer every foul ends a possession or every free throw represents a normal defensive foul.

Preserve the historical exclusion policy for legacy WMI: offensive, technical, and double-technical fouls do not count; other counted fouls require attribution to the defense. The canonical candidate must explicitly classify other supported labels and flag unknown labels. Team-penalty accounting and the research foul outcome are separate classifications. Pin rules for each season; record differences rather than silently redefining the target.

Official rule reference: <https://official.nba.com/rule-no-12-fouls-and-penalties/>. Final corrected play-by-play supports historical reconstruction, not proof of what was available live at that instant.

## Descriptive WMI

The legacy definition stays unchanged: `L_t = any(F_(t-2), F_(t-1))`, `N_t = any(F_(t+1), F_(t+2))`, and `M_t = F_t * (1 + N_t)`, using global game order, crossing period boundaries and truncating at game edges. `WMI = mean(M | L=1) / mean(M | L=0)`.

Write `p_l = P(F=1 | L=l)` and `q_l = P(N=1 | F=1,L=l)`. The descriptive factorization is `(p_1/p_0) * ((1+q_1)/(1+q_0))` wherever its components are defined. Undefined denominators/groups/conditionals stay missing with reasons. No undocumented pseudocounts, clipping, or smoothing.

This ratio is retrospective and unadjusted. Values above one are not a test against independence: varying rates and opportunity composition can produce the same pattern. The exact observed score has no sampling error conditional on its parsed events; any inferential interval must instead define a process/population target and its assumptions. Per-game intervals remain withheld pending a validated coverage design. Percentiles name their cohort and are not significance tests.

## Prediction availability and candidate models

Prediction originates at the declared possession-start reference point. Features may include team identity, home defense, period, known remaining time, score difference/margin, reconstructed team-foul and penalty state, start type, and past history. Unverified lineup/tracking variables are not assumed available. Missingness and categorical unknowns are explicit.

Exclude current-possession foul, shot, free-throw, duration and terminal-score outcomes; future windows and final WMI; and eventual overtime duration. Future suffix changes must not change earlier prediction features. Fit preprocessing only on training data.

Model ladder: training base rate; historical additive logistic context; regularized nonlinear context with prespecified time/margin functions and limited basketball interactions; that identical context model plus precisely defined past history. Match evaluation rows and tuning budgets. Choose complexity using earlier development data only. No Hawkes, Transformer or other sequence expansion before evidence warrants it.

## Evaluation and uncertainty

Primary endpoint: possession-weighted paired held-out log loss, history minus context; negative favors history. Secondary endpoints: Brier score, calibration, equal-game log loss, season-specific and separately declared playoff performance. Report all primary results regardless of sign.

Use chronological whole-game splits. Existing 2024-25 and earlier studies are retrospective development evidence. Inventory all previous exposure before choosing another test cohort; absence of a saved result does not prove a season was unseen. If no genuinely unused cohort is verified, designate future data after protocol lock.

Preserve within-game dependence when resampling paired predictions. Report whether intervals condition on the fitted models. Investigate calendar/series dependence and training/selection variability when claiming uncertainty for a learning procedure. Sensitivities must preserve the original possession axis and avoid excluding observations based on the current outcome.

Before confirmatory evaluation, specify a minimum meaningful improvement and the decision rules for useful, negligible, unsupported and inconclusive effects. An interval containing zero does not prove equivalence. The old statistical-significance gate is not a practical-use threshold.

## Independent audit gate

Compare the canonical candidate with both historical reconstructions and an explicitly versioned alternative implementation. Pbpstats is a useful comparator with its own definitions, ordering fixes and overrides, not independent ground truth: <https://github.com/dblackrun/pbpstats/blob/main/docs/quickstart.rst>.

Create two identifiable sample strata: randomly selected ordinary game/possession material for estimating error, and enriched difficult/disagreement cases for finding failures. Record sampling seed, frame, inclusion probabilities, annotation provenance, independent reviewers, and adjudication. Do not pool enriched cases as a population error estimate without appropriate design weights. Require footage/access evidence for any film-validation claim. Preregister tolerances before evaluating audit performance and quantify error uncertainty; unresolved critical defects block release.

Last Two Minute reports concern selected close-game endings and notable non-calls. They cannot supply an all-game contact-opportunity denominator: <https://official.nba.com/2025-26-nba-officiating-last-two-minute-reports/>.

## Unresolved lock requirements

- Independently supported schedule coverage and canonical candidate release.
- Manual audit sampling size/tolerances, footage access, reviewer evidence, adjudication and uncertainty.
- Feature/model complexity choices made entirely on development data.
- Exposure inventory and genuinely unused evaluation cohort/date boundary.
- Minimum meaningful gain and a fully specified uncertainty/evaluation procedure.

Until these are resolved, implementation and exploratory diagnostics may proceed, but confirmatory evaluation and new public research claims may not.
