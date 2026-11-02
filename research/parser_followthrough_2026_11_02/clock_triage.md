# Frozen v5 clock/source-note follow-through

Date: 2026-11-02. This packet classifies the 84 games quarantined by
`canonical_candidate_v5`; it does not authorize clock repair or scientific
eligibility. The baseline remains fixed even if a later candidate changes.

`clock_triage.py` hashes the same bounded-memory archive snapshot it reads,
checks all six official archive byte counts and SHA256 values against the
manifest, checks each target game's report source hash and event count, and
checks its first rise against its recorded quarantine exception. Every target
CSV is already in `(orderNumber, actionNumber)` order. No clock sorting,
timestamp replacement, synthesized event, model fit, or film claim occurs.
The JSON binds the report and manifest hashes, archive identities, exact CSV
rows and complete normalized raw fields in neighborhoods around every rise.
CSV rows are one-based including the header; missing strings use the existing
archive reader's declared normalization to null. Source `orderNumber` is
preserved, even where it differs from action-number order.

## Complete quarantine counts

The 84 games contain 90 rises: 80 games have one, two have two, and two have
three. The earlier v1 packet had 85 games / 91 rises; the excluded v5 game is
`0022000925`, the narrowly supported traveling/replay restoration already
documented in the v5 semantic-change packet. These are observed row patterns,
not error rates or verified live-clock corrections.

| Entering source category | Rises | Interpretation |
| --- | ---: | --- |
| Unsupported memo | 42 | Metadata/source-note timestamp; note content still requires review |
| Replay | 33 | Sequence-specific evidence required; label alone is insufficient |
| Timeout / substitution / period start | 7 | Administrative timestamp without explicit restoration evidence |
| Technical foul | 3 | Penalty/control context remains relevant |
| Turnover | 3 | Live control conflict remains unresolved |
| Violation | 1 | Start-of-game delay record/control context remains unresolved |
| Scoring event | 1 | Reported actual game-clock malfunction; retained for audit |

## Narrow candidate and adversarial cases

- **Stronger restoration candidate:** `cdnnba_2021.csv`, game `0022100865`,
  rows 487396–487401, actions 176–182. A missed layup and offensive rebound
  at zero precede action 178, a supported replay request at 0.6 seconds with
  exact `value` **Foul occurred prior to expiration of time**. Action 179 is
  an attributed personal loose-ball foul at 0.6; the ensuing first free throw
  also uses 0.6. This supports investigating an explicitly linked correction with
  an audit reason; it does not independently validate the clock or call.
- **Same words, different evidence:** game `0022101229`, rows 691200–691203,
  actions 560/682/562/563. The same replay value enters at 6:32 after a foul
  and timeout at 6:31, followed by a made three at 6:23. It cannot be admitted
  by a rule intended for time restored after zero.
- **Already played free throws:** game `0022100206`, rows 117013–117019,
  actions 161/166/167/159/162–164. Free throws at 0.6 precede a defensive
  rebound at 0.1, then the same supported replay value returns to 0.6.
  Accepting the replay as a fresh live control clock would imply more than
  the archived record establishes.
- **Reported actual game-clock malfunction:** `cdnnba_2023.csv`, game `0022301177`,
  rows 645877–645883, actions 470/471/681/473/475/476/477. A missed shot,
  offensive rebound and late-numbered shot-clock turnover all use 1:14;
  the next made shot uses 2:06, followed by descending live events at
  1:47/1:44/1:41. There is no replay/clock-restoration row in this neighborhood.
  The source's `timeActual` also increases across the turnover and made shot,
  from `01:47:31.600Z` to `01:47:46.900Z` on 2024-04-13. ESPN's Dave McMenamin,
  [republished by ABC on 2024-04-13](https://abcnews.com/Sports/error-led-extra-time-clock-lakers-win-grizzles/story?id=109211765),
  reports NBA spokesperson Tim Frank's acknowledgment that the game clock
  was mistakenly reset from 1:14 to 2:20 and the error went unnoticed during
  play. The article identifies Davis and Goodwin baskets in the extra time,
  matching this source neighborhood. This is attributed original reporting
  with a quoted NBA statement; direct NBA.com/official.nba.com searches did
  not locate a league-hosted statement. It is not an independent footage
  review. The archived rise is 52 seconds between recorded events, whereas
  the reported reset was 66 seconds between plays; those differ because the
  next shot is recorded at 2:06. Retain a distinct game-clock-anomaly audit
  classification: do not remove 66 seconds, delete events, or sort by clock.
- **Period boundary contradiction:** `cdnnba_2021.csv`, game `0022100728`,
  rows 411222–411228, actions 548–554. Technical foul/FT records at 11:51
  precede the fourth-period start at 12:00. A later missed shot at 11:38
  does not establish whether the penalty timestamp or period-start ordering
  is correct.
- **Postgame note:** `cdnnba_2020.csv`, game `0022000254`, rows
  145171–145173, period end/game end at zero precede memo 661 at 1:11,
  value **10 second violation on  shooter.** It is a source note, not an
  explicit instruction to resume the game or restore 71 seconds.

All six archive hashes and full event fields are in the JSON; the cases above
can be located by `game_id` and `rises[].entering_action`. Neighborhoods are
limited to three preceding and three following rows; they are not complete
game validation.

## All archive memo rows

The additional all-game scan finds 317 `memo` rows, all without `teamId`,
`subType`, or `description`; text occurs in `value`, and source possession
may be zero or one of the teams. All 317 exact rows are retained under
`all_archive_memos`. Many describe records, career/season highs, and sellouts,
but others mention penalties, fouling out, ejections, injury, or stoppage.
Examples include `0022000695` action 317 (technical foul), `0022001062`
action 687 (defensive three seconds), and `0022000254` action 661 (shooter
violation). No memo should silently create a foul outcome, possession, or
clock correction. A future administrative source-note interpretation must
preserve the raw note and an explicit audit reason; absence of an actor is
not proof the underlying basketball event was already recorded elsewhere.

## Reproduction and limits

```sh
.venv/bin/python research/parser_followthrough_2026_11_02/clock_triage.py
```

Creates JSON exclusively; refuses to overwrite an existing packet. Fresh
source scan result: `ok: true`, 84 games / 90 rises, with the category counts
above. To verify an existing packet without writing:

```sh
.venv/bin/python research/parser_followthrough_2026_11_02/clock_triage.py --check
```

The check compares the complete serialized packet against fresh verified
source snapshots, including every CSV reference and raw neighborhood. It
does not execute the current parser, so later parser edits cannot redefine
the frozen cohort or this classification. The six archive hashes verify
identity with the declared saved inputs; they do not establish NBA source
correctness, footage correspondence, or independent reconstruction validity.
No games are made eligible. No parser changes are owned by this packet.

Fresh `--check` completed successfully with identical serialized JSON:
84 games / 90 rises. Ruff also passed:

```sh
.venv/bin/ruff check research/parser_followthrough_2026_11_02/clock_triage.py
```

A separate exact-reference assertion compared all 90 `(game_id, action,
CSV row)` tuples with the earlier frozen v1 packet after excluding only
`0022000925`; the sets match. A negative snapshot check passed an intentionally
incorrect SHA256 for the first archived input and confirmed rejection with
`source snapshot does not match manifest`. Every rise retains
`repair_authorized: false`. The coordinator owns the full project check.
