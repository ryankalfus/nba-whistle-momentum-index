# What the second feed says about three disputed records

2026-11-05. These are source observations from the archive pair identified in [the run summary](diagnostic_summary.json). The comparison key is game ID and action ID, corroborated by recorded order or timestamp. CSV record numbers count the header as record 1. The complete paired output has SHA256 `f747ee29cf7861625410c7c847725ec98cefac270d844c155b7dbca47719d1ee`.

| Game | Actions in CDN order | CDN CSV records | Mobile CSV records for the same actions | Recorded clocks in that order |
| --- | --- | --- | --- | --- |
| `0022400326`, Q3 | 476 defensive rebound → 585 technical foul | 183844 → 183845 | 157763 → 157760 | 3:05 → 3:07 in both feeds |
| `0022400334`, OT | 755 timeout → 758 substitution | 188652 → 188653 | 161861 → 161859 | 25.7 → 25.9 seconds in both feeds |

The mobile CSV stores each of these pairs in the opposite **physical record order**. But sorting the two events by the mobile feed's explicit `ord` field puts them in the same relative order as the CDN feed: 4489376 → 4494843 for the first game and 7410000 → 7440000 for the second. These are relative order comparisons for the pair; mobile records can intervene. Matching the clock on the flagged action alone would miss this distinction. Neither feed establishes the live sequence, so both games remain quarantined.

In `0022400322`, CDN record 181809/action 636 follows the recorded game end at zero. It describes a team foul with no subtype. Mobile record 155993 matches this action and describes only “Foul” (`etype=6`, `mtype=0`); offense remains unknown. This supplies no supported subtype, control assignment or reason to treat the row as an out-of-band note.

The paired rows and their references were checked against the stream hash above. No raw events, parser rules, eligibility or audit decisions changed.
