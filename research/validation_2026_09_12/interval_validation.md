# Per-game interval coverage stress test

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
