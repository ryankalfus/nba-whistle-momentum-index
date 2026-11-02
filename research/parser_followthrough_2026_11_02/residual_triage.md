# Residual transfer and unsupported-label triage

Date: 2026-11-02. **No additional safe parser fix is demonstrated by this
packet.** The remaining patterns require source adjudication or independent
control evidence. Counting fewer flags is not a correctness criterion.

## Frozen inputs and method

The detailed denominator is candidate v6, parser SHA256
`42d8af799859e5513410250c395c294e265f0e54f3e92f36954b12ee87d3eac5`.
Candidate v5 is
`6d6b481095e588f5346aeacea8799a7c6984b9f9b07d583c69a5df6a6d80f646`.
The script verifies both saved feature-provenance JSONL byte streams against
their manifest SHA256 values while reading those same bytes, checks the
manifests' parser hashes against the reconciliation reports, and checks all
row/transfer counts. It does not invoke reconstruction or inspect protected
model outcomes. For each flagged prior group, the next group's first event
identifies the transfer trigger; all 257 v5 and 410 v6 flags are accounted for.

It then verifies all six immutable source archives by byte count/SHA256 in
the same bounded-memory snapshots it reads, retaining complete original raw
source fields, exact CSV rows, and neighborhoods for all 410 v6 triggers.
The source patterns classify recorded rows; they do not establish actual
live control. Full previous-group raw rows are retained where a short local
window would omit earlier administrative companions. Some normalization
issues can exist outside possession `audit_flags`; the unsupported-label
search therefore inspects all raw events in report-selected affected games.

## Exact v5-to-v6 transfer comparison

| Action identity comparison | Count |
| --- | ---: |
| Persistent transfer trigger | 203 |
| Added in v6 | 207 |
| Removed from v5 | 54 |
| Total v5 | 257 |
| Total v6 | 410 |

Thus `257 + 207 - 54 = 410`. Per-game net differences obscure some changed
trigger identities: 200 games gained a net 204 flags and 49 games lost a net
51, producing the same net increase of 153. The exact action sets and all
removed `(game_id, action)` identities are in the JSON.

| Source context of added trigger | Count |
| --- | ---: |
| Recovered jump followed by unpaired losing-team turnover | 153 |
| Recovered jump followed by another source-owner reversion | 14 |
| Flagrant free throw followed by unexplained transfer | 39 |
| Rebound followed by unexplained transfer | 1 |

Persistent 203 source contexts: 147 after fouls, 42 after free throws,
nine after rebounds, one recovered-jump/unpaired-turnover, one other group
containing a jump, and three other cases. These categories describe the last
control-labeled row in the flagged group, not a scientific attribution of
cause. Complete issue-count changes are also retained in the JSON.

## Jump-loss records: evidence and limit

All 153 added unpaired-turnover cases have turnover team equal to the jump
row's original source-possession team. The corrected jump recovery assigns
the recorded recovering actor's team; the subsequent turnover then returns
to the old source owner. In 106 held-ball cases, the turnover subtype is
`lost ball` or `bad pass` but its actor differs from the recorded losing
jumper: 94 have equal clocks and 12 have different clocks. Other cases have
different jump descriptors, turnover subtypes, or timing. They are not all
instances of the already implemented, identity-matched loss companion.

Example: `0022000041`, `cdnnba_2020.csv`, rows 23896–23898, actions
304/307/308, all Q2 0:59.5. The jump names Plumlee versus Fernando, tip to
D. Wright (DET), while retaining ATL source possession. The next turnover is
attributed to T. Young (ATL), not losing jumper Fernando. The steal is
attributed to Plumlee (DET). The next recorded shot is Grant's DET basket
at 0:55.6. Existing identity-based pairing deliberately does not silently
rewrite Young's turnover as Fernando's lost jump.

Of the 153 cases, 101 have an immediately following same-clock steal by
the recorded winning jumper on the recovering team. Eighty-one of these
have held-ball jumps and lost-ball/bad-pass turnovers. The three statistical
records are mutually consistent with a delayed source companion, but the
steal is **not independent validation** of that interpretation. They do not
exclude an unrecorded intervening gain, misplaced corrected records, or an
incorrect jump/turnover attribution. No automatic pairing of mismatched
loser identities is justified solely by this count or by the steal row.
The JSON retains every such triple for future evidence review.

Other reversions are more visibly inconsistent. `0022000798`, rows
448356–448359, jump 618 names GSW recovery at 0:46, then shot 626 is a WAS
miss at the same clock, followed by GSW block/rebound. `0022100172`, rows
98489–98491, jump 646 names IND recovery while a UTA second free throw 645
and subsequent IND rebound appear afterward at the same clock. Neither
supports a blanket rule trusting all later source owners or ignoring all
jump-recovery actors. Keep them blocking pending adjudication.

## The 39 free-throw additions do not demonstrate stale retained state

All 39 flagged previous groups carry `retained_ball_requires_audit`, and
their last control event is a `flagrant` free throw. There is no later
control event in those groups before the conflicting trigger: only
administrative rows intervene. The entering event is 26 personal fouls,
11 offensive fouls by the preceding shooting team, or two kicked-ball rows.
No case here demonstrates retained state surviving a documented intervening
live-control boundary. V5's terminal final-free-throw boundary could hide
these conflicts; retaining a flagrant entitlement makes the incompatible
subsequent source ownership visible.

Example: `0022000259`, `cdnnba_2020.csv`, rows 147986–147994. Anthony's
flagrant personal foul 655 and Zeller's two flagrant free throws 658/659
establish the recorded CHA sequence at 1:55. Anthony's ordinary personal
foul 660 at 1:45 assigns ORL source possession despite being followed by
Graham's CHA free throws 664/665. Source possession and foul actor/context
disagree. Correcting the source offense would require a separate declared
adjudication; clearing retained state to erase the transfer is not evidence
of correct ownership. The previous known retained-state bug involved a
separate later ordinary entitlement; this inventory does not demonstrate
that bug recurring across an actual recorded control boundary.

The lone added rebound-context case is `0022100142`, `cdnnba_2021.csv`:
Portis's MIL defensive rebound 284 at 2:51 (row 80883) precedes Beal's
technical FT 292 at 2:44 (row 80887, source owner MIL), a team dead-ball
rebound 293 assigned WAS (80888), MIL's too-many-players technical 289
(80889), an overturned replay 290 (80890), and WAS shot 296 at 2:34
(80893). Treating the technical dead-ball rebound as administrative exposes
the later WAS ownership change; it does not prove which replay-adjusted
control sequence is correct. The penalty and replay ordering need source
adjudication rather than a special exemption.

## All unsupported records

| Game | CSV / row | Action | Recorded label | Context |
| --- | --- | --- | --- | --- |
| `0022000711` | `cdnnba_2020.csv` / 399068 | 169 | `freethrow/shot` | Stewart miss at 10:10 after foul 159 explicitly describing two FTs |
| `0022000711` | `cdnnba_2020.csv` / 399074 | 171 | `freethrow/shot` | Stewart make at the same clock after substitutions |
| `0022200583` | `cdnnba_2022.csv` / 325751 | 615 | `freethrow/null` | Plumlee miss at 4:33 after foul 598 describing one FT; next row is defensive rebound 616 |
| `0022400322` | `cdnnba_2024.csv` / 181809 | 636 | `foul/null` | `TEAM foul ` at zero after period end 634 and game end 635; PHI actor, zero source possession |

The foul qualifiers and neighboring records provide entitlement context but
do not supply the missing archived free-throw ordinal labels. Do not invent
`1 of 2`, `2 of 2`, or `1 of 1`, silently replace source values, or infer
a technical-foul subtype for the postgame foul. All three free throws and
the postgame team foul remain blocking. An actual trailing foul is distinct
from out-of-band memo metadata; completion checks must not discard it.

## V7 follow-up and verification

The final v7 reconciliation is separately hash-bound in the JSON:
6,036 reconstructed / 48 quarantined, 411 transfer flags, 166 violation
flags, three unsupported free throws and one unsupported label. The 35
additional reconstructed memo games explain the changed denominator.
Detailed transfer categories above remain **v6's 410**, not v7's 411.

```sh
.venv/bin/python research/parser_followthrough_2026_11_02/residual_triage.py
```

The completed source scan produced the exact counts above and writes its
new JSON exclusively. It verifies archived source and frozen provenance
hashes and refuses incomplete unsupported-record or transfer counts.
The coordinating agent subsequently ran `--check`: the complete final packet reproduced exactly, exit 0. The command compares without rewriting the packet.

```sh
.venv/bin/ruff check research/parser_followthrough_2026_11_02/residual_triage.py
```

Passed. Independent report assertions checked exact transfer set arithmetic,
all 410 source traces, all four unsupported source records, category totals,
the 101 source triples, the 39 flagrant retained-ball cases, and the v7 report
hash/count binding. No parser fixes, source edits, model evaluation,
independent film validation, Git writes or eligibility changes occurred.
