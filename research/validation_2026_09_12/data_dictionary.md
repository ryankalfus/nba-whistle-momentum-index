# Possession data dictionary

One row is a reconstructed team possession. Ownership is read from final corrected NBA CDN events. Period changes split groups; administrative-only and technical-only ownership artifacts cannot independently establish live-ball possessions. Rows remain in global game order, including consecutive same-team possessions when control is legitimately retained after a terminal event.

| Fields | Meaning and timing |
| --- | --- |
| game_id, season, season_type, game_date | Game identifiers; IDs retain leading zeros. Dates are Eastern dates from source timestamps. |
| possession_number, possession_group | One-based global game sequence after reconstruction. |
| parser_version | Reconstruction version; the WMI equation is unchanged. |
| period, period_bucket | Period at possession start; overtime has its own category. |
| offense_team/id, defense_team/id, home_team, away_team, home_defense | Possession ownership and team identities. Home identity is inferred from scoring-side changes in the feed. |
| start_action_number, end_action_number | First/last included source action IDs. Source orderNumber controls sorting; action IDs need not be contiguous or increasing after edits. |
| start_clock, seconds_left_before, elapsed_before | Reconstructed start time. The clock comes from the preceding recorded event, or the period-start clock. Known time remaining excludes future overtime. Units: seconds. |
| score_difference_before, score_margin_before | Prior recorded offense-minus-defense score and its absolute value. |
| home_score_before, away_score_before | Recorded score before the first event in the reconstructed possession. |
| defense_team_fouls_before, defense_last_two_fouls_before | Reconstructed team-foul state before the possession. Personal fouls other than offensive/double/technical count; rare exceptions are not fully adjudicated. |
| defense_bonus_before | Whether the next common defensive foul would ordinarily incur the team-foul penalty, including the last-two-minute rule. |
| late_strategy_context | Pre-possession time/margin flag, independent of F_t. Used only to define the sensitivity cohort and as a context feature. |
| foul_lag_1 … foul_lag_5 | Counted foul indicator from each earlier global possession; game-start padding is zero. |
| same_defense_foul_lag_1 … 5 | Whether each earlier foul possession had the same defending team as the current possession. |
| F_t, foul_called_this_possession | Outcome: at least one counted defensive foul in this possession. |
| defensive_foul_count | Number of counted defensive foul events; can exceed F_t. |
| L_t, N_t, M_t | Original WMI variables. N_t and M_t use future information and are not prediction inputs. |
| foul_events | JSON array containing source action, period, clock, team, committing/drawing player IDs, subtype, descriptor and description. ID 0 means unavailable. |
| end_clock, seconds_left_in_game, score_difference, home_score_after, away_score_after | End-of-possession context/outcomes; excluded from prediction inputs. |
| points_home, points_away | Recorded score differences across the reconstructed segment; includes assigned technical points and source score corrections, not a causal foul value. |
| free_throw_attempts, free_throw_points | Attempts/makes recorded in the segment, including technical attempts when assigned. These are not an event-level causal link from every foul to its awarded free throws. |
| field_goal_attempts, rim_attempts | Segment outcomes from source field-goal and restricted-area labels. Neither is used to predict the current possession. |
| rim_attempts_available | False where shot-zone fields are absent; rim_attempts is missing in those games, never silently zero-filled. |
| player_foul_max_before | Maximum tracked personal-foul count among all players observed earlier in this game; not restricted to players on court. Not a model feature. |
| unassigned_foul_events, invalid_timed_events, administrative_groups_removed | Per-game audit counts, repeated on each possession. Sum once per game, not over all rows. |
| control_event_count, last_control_terminal | Parser diagnostics for separating live-play segments from technical-only ownership artifacts. |

Model feature allowlists are explicit in validate_wmi.py. Crew assignments, validated lineups, drives and paint touches are not part of this model. Their absence limits interpretation. The compressed partitions are fully reproducible from the pinned raw archives, not a replacement for those archives.
