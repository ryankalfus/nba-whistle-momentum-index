# Synthetic mathematical validation

Date: 2026-11-02. Scope: stage 5 software and finite-process mathematical diagnostics, not independent possession validation or a public empirical basketball result. The independent reconstruction gate remains blocked. No protected outcomes, archived games, fitted models, or public explorer data enter this study.

## Definition and targets

The immutable legacy score uses each game's globally ordered binary sequence, truncated two-neighbor windows, `L_t=any(F_(t-2),F_(t-1))`, `N_t=any(F_(t+1),F_(t+2))`, and `M_t=F_t(1+N_t)`. Period boundaries do not reset windows. Write `S_l=sum M_t I(L_t=l)` and `N_l=sum I(L_t=l)`; the exact realized score is `(S_1/N_1)/(S_0/N_0)`. An empty group or zero baseline makes that score undefined; a defined zero numerator stays zero. Conditional on parsed events, this arithmetic has no sampling uncertainty. No per-game confidence interval is produced.

The simulation reports the entire per-game distribution, with undefined mass separate. Quantiles and means explicitly condition on defined scores; undefined games remain in total counts. The fraction above one uses **all games** as its denominator and is a descriptive frequency, never a rejection rate for an independence test.

The separate uncertainty target is the process functional

`theta = (E[S_1]/E[N_1]) / (E[S_0]/E[N_0])`.

Expectations are over a specified random game generator, with windows computed within each game. This is a ratio of expected game components. It is not the expected per-game WMI, the observed score of a particular game, or a new edition of the public WMI. No game concatenation occurs. For random-length games this functional weights opportunities through expected component counts; it does not give each game equal influence on conditional means.

For independent, possibly nonidentical Bernoulli coordinates with rates `p_t`, define `a_t=1-product_(j=max(0,t-2)..t-1)(1-p_j)` and `b_t=1-product_(j=t+1..min(n-1,t+2))(1-p_j)`, with empty products equal to one. The disjoint past, current, and future coordinates give, by direct independence:

- `E[N_1]=sum a_t`, `E[N_0]=sum (1-a_t)`.
- `E[S_1]=sum a_t p_t(1+b_t)`, `E[S_0]=sum (1-a_t)p_t(1+b_t)`.

These finite-sample formulas are independently checked against exact rational enumeration. They do not imply independence after pooling positions with changing rates. Neither ratios of expected sums nor ratios of expected conditional means can replace an expected random ratio.

## Reproduction and implementation

Run from the project with its pinned environment, choosing an output directory that does not already exist:

```sh
.venv/bin/python -m whistle_research.simulations --output research/NEW_SYNTHETIC_RUN --seed 20261102
```

The CLI refuses an existing directory, writes JSON with no NaN values, and records the seed, PCG64 generator, Python/NumPy/SciPy versions, metric identity, simulation/metric source SHA-256 hashes, explicit absence of a parser, process parameters, sample sizes, and resample counts. The recorded run is [simulation_summary.json](../research/rewrite_completion_2026_11_02/simulation_summary.json). Defaults use 4,000 games per main scenario, 200 possessions per game, 20,000 games for the small-reference comparison, and 200 coverage trials with 399 resamples each. Memory is bounded by these explicit sample sizes; defaults are suitable for the project's 8 GB machine. Larger user-selected settings naturally require more memory/time. The output is byte-content reproducible through deterministic JSON serialization in the recorded environment; no timestamp is inserted. The report was reproduced by comparing its parsed content with a fresh `run_study()` result.

`simulations.py` contains a vectorized within-game component calculator, process generation, exact enumeration (limited to 16 positions), analytic component expectations, whole-game bootstrap, coverage study, and CLI. Its component calculations agree exhaustively with the exact legacy implementation over all binary sequences of lengths 1–8.

## Declared processes and observed synthetic results

Each scenario uses newly generated independent uniform draws at each possession. In the independent scenarios those draws are thresholded by a deterministic rate schedule. In the history scenarios the actual transition is `P(F_t=1 | past)=clip(p_t+delta*L_t,0,1)` with empty starting history.

| Process | Declared rates | Conditional mean WMI | Undefined games | Fraction above 1, all games |
| --- | --- | ---: | ---: | ---: |
| Independent constant | 0.2 | 1.0065 | 0% | 45.425% |
| Independent step | first 100: 0.05; last 100: 0.5 | 3.4000 | 0% | 100% |
| Independent smooth | linear 0.03 to 0.6 | 1.7968 | 0% | 98.25% |
| Independent alternating | 0.05, 0.5 repeated | 0.9930 | 0% | 43.825% |
| History excitation | baseline 0.1; delta +0.3 | 4.1179 | 0% | 100% |
| History inhibition | baseline 0.3; delta -0.25 | 0.1620 | 0% | 0% |
| Independent rare | 0.002 | 0.1386 | 67.275% | 0.15% |

These are Monte Carlo summaries of declared generators, not exact universal values. The step and smooth examples establish constructive counterexamples to treating a score above one as an independence test. Alternating rates also show that rate variation need not shift the score in a single direction. Known history dependence shifts the score in these examples but does not make the score identify a mechanism in observational data. Rare events demonstrate why dropping undefined scores changes the population represented by a reported mean.

The exact nonstationary reference enumerates all `2^8` sequences under probabilities `[0.1,0.15,0.2,0.25,0.6,0.65,0.7,0.75]` using rational sequence masses. Undefined probability is **0.019278**, conditional expected WMI is **1.9014834**, and the separate ratio-of-expected-components target is **1.9173169**. The full probability mass function, including rational WMI values, is saved. The 20,000-game Monte Carlo conditional mean is **1.9056967** (estimated MC SE **0.0101924**); undefined fraction is **0.0196** (reference-based MC SE **0.0009723**); the largest absolute finite-atom mass difference is **0.00421975**. These are numerical agreement diagnostics, not proof of scientific validity or simultaneous confidence bands.

A hand-checkable two-position example with rates 0.25 and 0.75 has undefined mass 0.75, conditional expected WMI 0.375, and ratio-of-expected-components 1.3125. Tests verify all three distinctly.

## Whole-game uncertainty and coverage

The estimator plugs average sampled game components into `theta`. Each bootstrap draw samples whole game vectors with replacement, preserving all dependence inside a game. The 95% percentile interval uses no possession-level resampling. It assumes IID games from the declared process, finite component moments, and population denominators bounded away from zero for stable ratio estimation. This is a procedure being diagnosed, not a finite-sample coverage guarantee. If the observed ratio or **any** bootstrap ratio is undefined, the entire interval is withheld; undefined resamples are counted, never discarded. This conservative reporting policy can itself lower interval availability as the number of resamples increases.

The coverage population draws a latent rate independently for each game: rate 0.1 or 0.7 with equal probability, followed by eight independent Bernoulli possessions conditional on that rate. Exact mixture component expectations give `theta=2.8088492872`. Each trial creates a new sample; bootstrap randomness is included in the procedure being evaluated. The dependent failure case shares one latent rate across every game of a trial, preserving the same single-game marginal population target while violating independent-game sampling. No training/selection variability is involved.

| Coverage design | Games/trial | Available intervals | Covered/all 200 trials | Estimated MC SE | Exact binomial 95% interval for coverage |
| --- | ---: | ---: | ---: | ---: | --- |
| IID games | 120 | 200 | 190/200 = 95% | 1.54 percentage points | 91.00%–97.58% |
| Sparse IID games | 8 | 178 | 150/200 = 75% | 3.06 percentage points | 68.40%–80.84% |
| Shared cross-game latent rate | 120 | 200 | 0/200 = 0% | 0 plug-in estimate | 0%–1.83% |

Unavailable intervals count as missed for the reported operational coverage. Binomial intervals quantify uncertainty in these independent simulation trials. The plug-in Monte Carlo SE `sqrt(c_hat(1-c_hat)/trials)` is zero at zero observed coverage; the exact binomial bounds make clear that the true failure-scenario coverage has not been established to be exactly zero. The experiment supports approximate performance only for the tested IID configuration; it does not validate every rate, game length, process, or dependence regime.

## Limits and gates

These tests establish arithmetic contracts and reproducible behavior under chosen synthetic generators. They do not validate possession reconstruction, foul-label semantics, missingness mechanisms, referee interpretations, or a basketball population model. Sparse denominators, heavy-tailed ratios, changing populations, informative missingness, calendar/series dependence, common latent conditions, and model-fitting/selection variability can invalidate intervals based on IID games. The shared-latent experiment demonstrates one failure directly. Resampling paired held-out predictive losses and accounting for fitted-model uncertainty belong to the separate evaluation design; this module does neither.

Do not publish per-game WMI inferential intervals from this work. Do not interpret WMI thresholds as p-values, identify call correctness or intent, or advance the independent audit gate based on simulation success. Stage 5 implementation and synthetic mathematical verification can be complete while empirical scientific validation remains blocked.
