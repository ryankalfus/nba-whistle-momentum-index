# Memo clocks as out-of-band source metadata

Date: 2026-11-02. Read-only assessment against frozen candidate v6, SHA256
`42d8af799859e5513410250c395c294e265f0e54f3e92f36954b12ee87d3eac5`.
No parser or test changes are made by this packet.

**Yes, 35 of the 37 memo-rise games can pass the existing reconstruction
function when only memo inputs are withheld from its clock/control sequence.**
That is a conditional software feasibility result. It does not establish
correct live time, complete officiating records, scientific validity, or
eligibility. A production change must retain every original event and block
on source-note uncertainty; the diagnostic filtering here is not that change.

## Verified evidence

All six official archives were verified by size and SHA256 in the same
bounded-memory snapshot subsequently streamed. The six home/away metadata
files were also checked against frozen v5 report hashes before use. The
parser hash was checked before and after the scan; it stayed unchanged.
The JSON records source/member/hash bindings and complete raw rows, not
inferred live actions. Source periods, scores, clocks and order are untouched.

Across all 6,084 archived games, 317 memo rows occur in 209 games. The frozen
v5 quarantine cohort has 42 memo-entering rises in 37 games; all 37 initially
have only memo-entering adjacent rises. Those games contain 74 total memo
rows. Comparing the sequence **after excluding every memo from the comparison
chain** leaves 35 games with monotone non-memo clocks and two with residual
non-memo rises. The existing v6 reconstruction function accepts exactly the
same 35 filtered sequences and rejects the remaining two.
The 37 source games contain 20,839 events: 74 notes and 20,765 non-memo
events, with an exact partition in every game. Reconstruction does not imply
all other ambiguity vanishes: filtered game `0022000232` still has one
`foul_defense_unresolved`, `0022100417` one `violation_requires_audit`, and
`0022100485` one `unexplained_control_transfer`, in addition to retained-ball
and special-descriptor audit reasons in other games.

The residual adversaries are essential:

| Game | Previous non-memo row | Next non-memo row | Remaining conflict |
| --- | --- | --- | --- |
| `0022100750` | CSV 423714, replay 452, Q3 5:50 | CSV 423716, substitution 456, Q3 5:51 | Memo 455 raises to 5:51 between them; skipping only the memo-entering check masks the real rise |
| `0022100954` | CSV 538738, timeout 664, Q4 44.3 | CSV 538741, substitution 667, Q4 46.3 | Memos 665/666 intervene; the timeout-to-substitution rise still fails |

These are `cdnnba_2021.csv`; full archive SHA256 and all row fields are in
`memo_clock_assessment.json`, `cases[].residual_nonmemo_regressions`.

All 74 memo rows in these 37 games use the same period and score as the
immediately preceding non-memo row. Forty-five have a different clock.
Three notes immediately follow game end: `0022000216` action 784,
`0022000254` action 661, and `0022100494` action 688. Six immediately follow
a period end: `0022000908` action 639; `0022100224` action 293;
`0022100251` action 157; `0022100376` action 489; `0022100494` action 517;
and `0022100743` action 369. These counts concern all notes in the 37 target
games, not just the 42 rise-entering rows. Each note has its preceding and
following non-memo source reference, where present.

## Existing before-state feature defect

Current v6 handles memo as administrative, raises a blocking source-note
issue and marks period foul counts uncertain, then still assigns `prior = e`
in `possessions.py:422`. The next new possession copies that memo's clock,
score and reference action into `BeforeState` at lines 608–622. A memo's
position in the raw source is not evidence of a live control boundary.

The scan reconstructed each memo-containing game using unmodified v6 when
possible. Among those accepted games, 59 possession start references point
directly to a memo. Six change the clock relative to the preceding non-memo
event; none of those 59 change score or period. This is not evidence that
adversarial or future notes can safely supply score/period values.

| Game | Group | Memo action / CSV row | Previous non-memo clock | Memo clock |
| --- | ---: | --- | --- | --- |
| `0022000035` | 155 | 558 / 20582 | 11:42 | 11:34 |
| `0022000998` | 203 | 655 / 560107 | 0:12 | 0:11.6 |
| `0022100683` | 134 | 498 / 385785 | 3:23 | 2:59 |
| `0022101019` | 207 | 645 / 575389 | 0:33.7 | 0:33 |
| `0022101020` | 189 | 654 / 575941 | 2:47 | 2:40 |
| `0022101049` | 187 | 627 / 592223 | 1:41 | 1:30 |

The first is an independently reproducible nonquarantined example:
`cdnnba_2020.csv` row 20581, action 556, is Garland's made layup at Q4 11:42,
score 95–72. Row 20582/action 558 is the memo *Kevin Love out will not return*
at 11:34. Row 20583/action 559 is Korkmaz's missed layup at 11:19.
Group 155's v6 before-state references memo 558 and clock 694 seconds,
instead of preceding non-memo event 556 and 702 seconds. Full raw evidence
and actual returned `BeforeState` values for all 59 references are under
`before_state_memo_references` in the JSON.

## Proposed fail-closed contract

1. Preserve the entire original normalized/raw event stream, original source
   row indices, action/order numbers, timestamps and hashes. Memo notes are
   source metadata, not synthesized basketball events. Keep exactly-once
   accounting for notes, either as explicitly unassigned notes or a declared
   non-control association; do not silently drop them.
2. Handle memo before period-change, terminal, ownership and boundary logic.
   Memo fields must not close a possession, manufacture a period start/end,
   establish an owner, change score/clock references, or replace the prior
   non-memo event used by `BeforeState`. Administrative non-memo events remain
   subject to the existing clock checks.
3. Compare every non-memo event to the preceding non-memo event, preserving
   period and monotonicity checks. The two residual examples above must still
   fail. Existing actual-clock malfunction `0022301177` must still fail;
   replay restoration remains governed by its separate narrow contract.
4. Retain blocking `source_note_requires_audit` and unknown counted-foul
   history conservatively. A note may mention missing penalties, ejections,
   injury or records. Neither its label nor lack of a team actor proves
   absence of a missing foul or turnover. Notes with conflicting periods
   require explicit uncertainty rather than using the note's period as a
   live boundary. Unknown eligibility remains false.
5. For completion-marker diagnostics, find the terminal **non-memo** event
   while retaining trailing notes in the full event stream. Current
   `reconcile.py` and `features.py:183` use `events[-1]`, which would classify
   a retained postgame note as the terminal event. Marker selection may
   ignore only memo, including notes when deriving the observed-period set;
   do not let a true event after game end pass silently.
6. Require metamorphic checks: insert same-period monotone and rising memos,
   conflicting-clock/score/period memos, postgame notes and notes between
   genuine rising non-memo events. Actual non-memo possessions and before
   references must remain invariant except for declared blocking note
   uncertainty. Raw event/source-row retention must remain exact. All target
   games stay ineligible.

The source inventory supports this limited metadata interpretation: all 317
memo rows lack a team actor/subtype/description, and text is stored in `value`.
It does not supply an official general CDN field specification or prove that
the implied officiating records exist elsewhere. Consequently the blocking
uncertainty is a substantive condition, not an optional warning.

## Assessment method and checks

The one-off `.venv/bin/python` scan used the existing verified archive reader
and current `reconstruct`, verified the parser hash before/after, and wrote
the new JSON exclusively. For each target game it computed the original
event count, all memo indices, the residual non-memo clock chain, and a
temporary reconstruction of non-memo input rows. The shadow result records
group counts and all issue counts; any remaining ambiguity is visible.

For every source game with a memo and successful full v6 reconstruction, it
selected returned possessions whose `start_state.reference_action_number`
matched a memo, retained their actual returned before-state, and compared
the note's period/clock/score with the preceding non-memo row. The scan output:

```text
42 memo rises; 37 memo-rise games; 35 monotone non-memo sequences;
35 shadow reconstructions; 209 archive memo games;
59 returned memo before-state references; 6 clock differences;
0 score differences; 0 period differences.
```

The filtered diagnostic temporarily omits notes, so its normalized
`source_row` indices are re-enumerated by the current parser. **Do not ship
that filtering call as the implementation.** The JSON's accounting identity
`source_event_count == memo_count + retained_live_reference_event_count`
only proves the partition is complete; it does not prove a future parser
retains all raw notes. Production raw-retention and unchanged-index tests
remain necessary. No full project checks or parser fix are claimed here.

## All 42 memo-entering rises

| Game | Memo action | CSV row | Previous raw clock | Memo clock | Note text |
| --- | --- | ---: | --- | --- | --- |
| `0022000216` | 742 | 123217 | PT03M29.00S | PT03M32.00S | Jeff Green Season high in points scored |
| `0022000216` | 781 | 123248 | PT00M10.80S | PT00M16.60S | Kyrie Irving sets season high in points |
| `0022000216` | 784 | 123251 | PT00M00.00S | PT00M03.40S | Taurean Prince sets season high in points |
| `0022000232` | 571 | 132384 | PT06M44.00S | PT06M56.00S | Jarrett Allen ties season high in points |
| `0022000254` | 661 | 145173 | PT00M00.00S | PT01M11.00S | 10 second violation on shooter. |
| `0022000323` | 642 | 183894 | PT02M19.00S | PT02M37.00S | VanVleet - Most Points Ever Scored by an Undrafted Player in NBA History |
| `0022000449` | 668 | 253998 | PT00M56.20S | PT00M59.60S | Magic - Vucevic 3rd Career Triple Double |
| `0022000450` | 659 | 254572 | PT00M27.60S | PT00M29.20S | EMBIID career high points |
| `0022000881` | 669 | 494716 | PT00M14.80S | PT00M31.10S | Darius Garland sets franchise record for fastest player to make 200 three point field goals in Cavs history |
| `0022000908` | 639 | 509759 | PT00M00.00S | PT00M00.60S | Kleber - season high rebounds (was 9), career high assists (was 4) |
| `0022001027` | 566 | 576115 | PT04M52.00S | PT05M06.00S | Isaac Okoro sets career high in rebounds |
| `0022100016` | 440 | 9276 | PT05M53.00S | PT05M56.00S | 378th Sellout |
| `0022100224` | 510 | 127233 | PT08M13.00S | PT08M28.00S | Dean Wade season high in points |
| `0022100234` | 66 | 132366 | PT06M26.00S | PT06M52.00S | Khris Middleton set new Bucks 3-pt FGM record @ 11:14 of 1st Qtr. (1,052 3-pt FGM) |
| `0022100251` | 695 | 142379 | PT01M30.00S | PT01M49.00S | Suns - Season High, Total Points (prev. 11/4 vs. HOU) |
| `0022100367` | 610 | 207579 | PT03M38.00S | PT03M46.00S | Evan Mobley sets career high in blocks |
| `0022100376` | 625 | 212698 | PT02M52.00S | PT02M54.00S | POR: Nurkic fouls out at 2:54 in the 4th |
| `0022100417` | 653 | 235724 | PT02M10.00S | PT02M22.00S | Alperen Sengun career high in points and rebounds |
| `0022100456` | 563 | 257524 | PT07M24.00S | PT07M37.00S | Suns - Season High 3pt made, 20 ( 18, 11/12 @ MEM) |
| `0022100462` | 429 | 260835 | PT03M16.00S | PT03M28.00S | GSW: 394th CONSECUTIVE SELLOUT |
| `0022100485` | 422 | 273597 | PT07M03.00S | PT07M08.00S | GSW: 395th consecutive sellout |
| `0022100494` | 538 | 278966 | PT11M01.00S | PT11M03.00S | Denzel Velentine sets season high in points |
| `0022100581` | 644 | 328722 | PT01M56.00S | PT02M06.00S | Phoenix - Chris Paul - Career High Rebounds |
| `0022100604` | 531 | 341702 | PT08M09.00S | PT08M24.00S | GSW: 398th consecutive sellout. |
| `0022100697` | 516 | 393807 | PT10M41.00S | PT10M54.00S | Suns - Biyombo ties Career High Pts (prev. ORL@WAS, 1/12/18) |
| `0022100743` | 369 | 419585 | PT00M00.00S | PT00M01.10S | Suns - Season High Pts, 1st Half (prev. 73, 11/21 vs DEN; 1/2 @ CHA) |
| `0022100750` | 455 | 423715 | PT05M50.00S | PT05M51.00S | 405TH SELLOUT |
| `0022100758` | 530 | 428136 | PT08M31.00S | PT08M48.00S | Spurs - Jones ties Season High pts (prev.1/1/22 @ DET) |
| `0022100758` | 591 | 428187 | PT03M14.00S | PT03M25.00S | Suns - Paul Season High assists (prev. 18 vs NOP, 11/2) |
| `0022100758` | 636 | 428225 | PT00M05.50S | PT00M07.50S | Suns - Bridges, Season High Pts (prev. 23, 2x, last 11/22 vs IND) |
| `0022100759` | 541 | 428689 | PT09M02.00S | PT09M18.00S | Cedi Osman sets career high in assists |
| `0022100759` | 601 | 428740 | PT04M59.00S | PT05M06.00S | Brandon Goodwin ties career high in points |
| `0022100805` | 605 | 454056 | PT04M43.00S | PT04M48.00S | Rajon Rondo sets season high in assists |
| `0022100807` | 572 | 455155 | PT06M49.00S | PT07M03.00S | Collins - season high rebounds (was 12) |
| `0022100853` | 562 | 480939 | PT02M08.00S | PT02M15.00S | Mann season high points (was 19) |
| `0022100920` | 428 | 519297 | PT03M04.00S | PT03M18.00S | Brandon Goodwin sets career high in assists |
| `0022100932` | 554 | 526190 | PT06M38.00S | PT06M52.00S | Darius Garland sets season high in points |
| `0022100935` | 636 | 528005 | PT00M30.10S | PT00M34.10S | HOU - Martin Jr. season high points (prev 17, 1/28 vs POR) |
| `0022100954` | 666 | 538740 | PT00M44.30S | PT00M46.30S | Fox - ties career high points (44) |
| `0022101060` | 589 | 598311 | PT05M23.00S | PT05M32.00S | Jerami Grant sets season high in points |
| `0022101065` | 634 | 601070 | PT01M38.00S | PT01M42.00S | Magic - Carter Jr. Career High Points |
| `0022101227` | 588 | 690186 | PT00M26.10S | PT00M34.80S | MAGIC - Hampton Career High Points |
