# Canonical parser flag triage

Date: 2026-11-02. All counts and implementation line references below describe the frozen `canonical_candidate_v1` parser at commit `618d480eb7f97781515907452e5d43ab4b7f9a57`, SHA256 `a0fc53a3389002d79affef35300ce76f12a7fe058621d6231d35b0676a45743a`; they do not describe the current production parser. Diagnostic evidence only; no source/parser edits, rule adjudication, film review, model fit or scientific claim. All games remain independently unaudited and ineligible.

## Exact scope and provenance

Fresh size/SHA256-verified snapshots of all six `cdnnba_*.tar.xz` archives in `research/hypotheses_2026_09_12/cache/` were streamed one game at a time through the existing `archive_games` reader. All 6,084 games were scanned. The existing canonical parser was rerun only for reconstructed games reporting unexplained transfers; per-game transfer counts were checked against `output/v2/reconciliation-all-2026-11-02/report.json`. No WMI/model analysis was run. Python: project `.venv`, 3.14.7; stdlib and existing package only.

The companion `parser_triage.json` records fresh source hashes/sizes, report and parser hashes, exact CSV source rows, raw event fields, all violation subtype/qualifier/descriptor counts, all 85 quarantined games and their 91 regression references, 16 selected representative neighborhoods, and all 25 violation/transfer issue references from the 14-game pilot. Complete raw detail, including 71 signature examples, is retained in gitignored `output/v2/parser-triage-2026-11-02/full_detail.json`. The pilot comprises ten random and four enriched games; enriched cases are not a population error estimate. Exact raw field strings are preserved after the existing reader's declared missing-value normalization. Events were inspected in existing canonical source-order order; zero games required rearranging CSV rows to achieve that order. No clock sorting or clock correction was performed.

## The 10,347 violation flags

Counts below are issue/event counts among 5,999 reconstructed games, not counts of games or confirmed errors.

| Raw subtype | Raw qualifiers | Flags |
| --- | --- | ---: |
| kicked ball | missing | 4,664 |
| defensive goaltending | missing | 2,856 |
| delay-of-game | team | 2,480 |
| lane | missing | 264 |
| lane | fastbreak | 10 |
| double lane | missing | 42 |
| jumpball | missing | 31 |
| **Total** | | **10,347** |

Every descriptor in these flagged rows is missing. There are 10,558 raw violation rows across all 6,084 games: 150 occur in quarantined games and another 61 in reconstructed games lack source ownership (33 delay-of-game, 28 jumpball). Those 61 exit through `unknown_ownership`, before the generic violation flag. Thus raw violation counts must not be substituted for the 10,347 flags.

`src/whistle_research/possessions.py:460` flags every recognized-owner violation uniformly. This is a conservative unimplemented semantic distinction, not evidence that 10,347 source records are erroneous. A targeted implementation should distinguish awarded-score companions, retained-control violations, possession-loss violations and FT/jump-ball entitlements, while preserving unknown cases as blocking.

## The 2,780 unexplained transfers

The immediately preceding nonadministrative raw-label families are: defensive-goaltending violation 2,540; personal foul 178; `freethrow/1 of 1` 21; defensive rebound 11; recovered jump ball 9; delay-of-game 8; steal 3; kicked ball 3; memo 3; offensive rebound 3; jump-ball violation 1. These sum to 2,780. This adjacency table includes technical FT labels in the preceding-label description; technical FT classification itself remains administrative in the parser. Aggregate adjacency identifies investigation priorities, not independent proof of a shared cause.

### Confirmed implementation gap: a made shot and its goaltending companion become two groups

The 2,540 goaltending-adjacent transfers are 91.4% of all unexplained-transfer flags. The exact following example demonstrates a duplicate boundary in the implementation; it does not establish that all 2,540 cases have identical semantics.

Source: `cdnnba_2020.tar.xz`, member `cdnnba_2020.csv`, SHA256 `e45e1b4a70a33ce93525c58f04362b6c275f7e514789772d4a8360f22a13f4f2`; game `0022000006`.

| CSV row | Action | Period / clock | Event | Actor / source possession |
| --- | ---: | --- | --- | --- |
| 3205 | 327 | 2 / 03:26 | J. Holiday made driving layup; qualifiers `pointsinthepaint, defensivegoaltending` | MIL / MIL |
| 3206 | 329 | 2 / 03:26 | E. Paschall defensive goaltending violation; score unchanged from action 327 | GSW / MIL |
| 3207 | 330 | 2 / 03:17 | D. Lee made three | GSW / GSW |

MIL is `1610612749`; GSW is `1610612744`. The exact observed three-row subset yields groups `[327]` with `made_field_goal`, `[329]` with `source_control_transfer` plus `unexplained_control_transfer`/`violation_requires_audit`, and `[330]` with `input_exhausted`. The subset is intentionally partial and is never scored or eligible.

Cause: `possessions.py:331`–337 permits same-clock foul/FT continuation after a made basket, but excludes the linked goaltending row. Lines 338–350 close the basket group and open the companion as another group; the next opposite-owner action then triggers an unexplained transfer. Rule 11 treats the defensive awarded score and ensuing procedure as a made basket. [NBA Rule 11](https://official.nba.com/rule-no-11-basket-interference-goaltending/)

Next scoped correction: recognize a same-clock, same-owner defensive-goaltending companion linked to the made/awarded shot, preserve both rows in one group and retain the made-shot terminal boundary. Require a regression fixture for this exact neighborhood and adversarial fixtures for unpaired, conflicting-owner, different-clock and different-period violations. Do not blanket-mark all violations administrative or remove their audit requirements; do not make games eligible.

### Remaining transfers need source/rule review

- **Personal labels hide special entitlement descriptors.** Game `0022000157`, actions 733/735 show `foul/personal` with descriptor `away-from-play`, followed by `freethrow/1 of 1` with the same descriptor. Action 736 then has source owner equal to the fouling actor, before the other team's FT action 738. The code activates special entitlement only for `e.subtype in SPECIAL` (`possessions.py:424`), although the raw source sometimes stores that meaning in `descriptor`. This is a confirmed label-normalization coverage gap; the correct full sequence/owner still needs season-rule and footage review. Do not silently infer retained control for every personal or take descriptor.
- **Apparent absent/reordered outcomes.** Game `0022000013`, action 500 says shooting personal foul with two FT entitlement, but the immediately following row is opponent action 506; the saved neighborhood has no intervening FT rows or scoring change. Determine whether this is overturned/corrected-feed information or a missing sequence. Do not invent two throws.
- **Offensive-foul source ownership conflict.** Game `0022000180`, defensive rebound 311 establishes ORL ownership; foul 313 assigns BOS possession despite ORL actor; same-clock turnover 357 assigns ORL, and challenge 317 says overturned. Existing conservative flags are justified pending explicit replay/source-semantics adjudication. The same-clock pairing fix alone cannot resolve conflicting ownership.
- **Technical FT context.** The saved `freethrow/1 of 1 -> 3pt/Jump Shot` example is a technical FT before the flagged live action, so nearest raw nonadministrative-label adjacency is not the last live control event. Review the preceding active possession and source ownership; do not treat technical FT ownership as a live transfer. All raw context is preserved.

## The 85 quarantines

Every report quarantine is a `clock/period regression` exception at `possessions.py:232`–235. Fresh scanning finds 91 same-period clock rises: 81 games have one, two have two, two have three. Increases range from 0.1 to 71 seconds. No period reversal occurs in these 91 pairs.

The row carrying the increase is `memo` 42 times, instant replay 34, turnover 3, timeout 3, substitution 3, technical foul 3, period start 1, delay-of-game violation 1, and two-point shot 1. In 86/91 the new row is administrative under the parser or unsupported `memo`; only five rises enter control-classified rows, in five games. This is a row-context classification, not a finding that 86 are harmless or recoverable.

All four enriched pilot examples:

| Game | Action entering rise | Increase | Observed scenario |
| --- | ---: | ---: | --- |
| 0022000181 | 594 | 1.0 s | Replay request at 01:19 follows clear-path FTs at 01:18 |
| 0022000254 | 661 | 71.0 s | A memo timestamped 01:11 follows period/game end at 00:00 |
| 0022000925 | 338 | 0.2 s | Replay request at 00:00.2 follows traveling at 00:00; live events then occur at 00:00.2 |
| 0022301177 | 473 | 52.0 s | Made shot at 02:06 follows a shot-clock turnover timestamped 01:14, then live rows descend again |

Other control-classified rises include three turnover rows and a start-of-game delay-of-game row; their exact game/action IDs and raw neighborhoods are in JSON. In particular, game `0022301177` needs event-order/source-correction evidence, not a rule that ignores all administrative times. Memo is currently unsupported, so merely bypassing its monotonicity exception would not complete semantic handling.

Next scoped work: specify immutable recorded timestamps separately from the live-state clock, retain explicit correction links/evidence, and add fixtures for these four distinct scenarios before accepting any clock repair. Official replay rules allow timing adjustments, but they do not prove that any saved rise is one. [NBA Rule 13](https://official.nba.com/rule-no-13-instant-replay/)

## Rule evidence and remaining limits

Rules were consulted on 2026-11-02. Current official pages support category distinctions only; archived season-specific editions still need pinning before adjudicating 2020–25 sequences. Kicked-ball outcomes depend on offense/defense; jump-ball violations may award control or repeat a toss. [NBA Rule 10, IV–V](https://official.nba.com/rule-no-10-violations-and-penalties/) Lane outcomes depend on shooter/team/opponent, result and whether the FT remains live. [NBA Rule 9, I](https://official.nba.com/rule-no-9-free-throws-and-penalties/)

Counts are complete for the six verified archives and match the diagnostic report; manual interpretation covers selected signature examples and the four enriched clock cases. No independent footage evidence, reviewer annotation, complete-season schedule proof, or scientific error-rate estimate is provided. Passing parser fixtures would establish implementation behavior only.

## Verification

The streaming run printed `DONE 6084 10347 2780 85`; every reconstructed affected game's transfer count matched the existing report. `parser_triage.json` parses with strict `json.loads`, its flagged subtype/signature sums equal 10,347, its transfer signature sum equals 2,780, and all 85 quarantine records contain their reported first exception action. The baseline evidence remains frozen. The standalone reproduction script was added on 2026-11-02 so a later parser version can reproduce these results without rebinding them to current code; six historical home/away metadata CSV hashes are now pinned in the compact JSON. These metadata remain derived evidence, not an independent schedule. No production parser or scientific eligibility changes are made by reproduction.

### Reproduce with the baseline parser, even when production is v2

`research/footage_2026_11_02/reproduce_triage.py` uses only the standard library and never imports or monkeypatches production modules. It verifies the baseline module's exact recorded hash before executing those same bytes under a distinct registered module name (required by its dataclasses). It verifies archive size/hash into one bounded-memory snapshot before streaming that snapshot, verifies the six home/away metadata CSV hashes, directly calls baseline `reconstruct` on every game, and compares game/quarantine identities and errors, violation subtypes/qualifiers, transfer signatures, and all regression references and aggregates to the compact JSON. It does not depend on the old diagnostic report, full-detail JSON, network access or WMI/model code. Existing output paths are refused and the result is created exclusively.

From repository root, choose a new output directory name. The `mkdir` must succeed before obtaining the baseline module:

```sh
mkdir output/v2/parser-triage-baseline-new
```

```sh
git show 618d480eb7f97781515907452e5d43ab4b7f9a57:src/whistle_research/possessions.py > output/v2/parser-triage-baseline-new/baseline_possessions.py
```

```sh
.venv/bin/python research/footage_2026_11_02/reproduce_triage.py --baseline-parser output/v2/parser-triage-baseline-new/baseline_possessions.py --output output/v2/parser-triage-baseline-new/reproduced.json
```

The existing local full-detail neighborhoods remain in gitignored `output/v2/parser-triage-2026-11-02/full_detail.json`; they are optional diagnostic context and are not required for baseline reproduction. No archived source, historical release or current parser is overwritten.

Full standalone reproduction ran successfully on 2026-11-02 while production used v2:

```sh
.venv/bin/python research/footage_2026_11_02/reproduce_triage.py --baseline-parser output/v2/parser-triage-baseline-reproduced-2026-11-02/baseline_possessions.py --output output/v2/parser-triage-baseline-reproduced-2026-11-02/reproduced.json
```

Output: `PASS: 6084 games / 5999 reconstructed / 85 quarantined / 10347 violation flags / 2780 transfer flags / 91 clock rises; compact evidence matches`. Saved result contains all 6,084 game classifications, exact quarantine errors and regression references, verified source/metadata hashes, baseline version, Python version and the compact evidence hash. All game eligibility fields remain false.

```sh
.venv/bin/ruff check research/footage_2026_11_02/reproduce_triage.py
```

Ruff: `All checks passed!`. Focused probes also verified that the current v2 module fails baseline hash checking before execution, the baseline dataclass module is registered separately with no production parser import, a snapshot hash mismatch fails before yielding bytes, and an existing output is refused before scanning without changing that file. The saved result's compact-evidence hash and all 6,084 unique game classifications were checked after the run. These checks establish reproducibility of the recorded v1 diagnosis, not scientific validity.
