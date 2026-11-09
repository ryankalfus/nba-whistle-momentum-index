"""Synthetic multi-season rows and team-foul states for plan-stage5-v1 tests."""

from datetime import date, timedelta

import numpy as np

from whistle_research import team_fouls

SEASONS = (("2020-21", "regular_season", date(2020, 12, 22)), ("2021-22", "regular_season", date(2021, 10, 19)),
           ("2022-23", "regular_season", date(2022, 10, 18)), ("2023-24", "regular_season", date(2023, 10, 24)),
           ("2024-25", "regular_season", date(2024, 10, 22)), ("2024-25", "playoffs", date(2025, 4, 19)))
SPLIT = {"train_start": "2020-12-01", "tune_start": "2021-07-01", "test_start": "2022-07-01",
         "test_end": "2025-07-01"}


def synthetic(seed=7, games=24, possessions=40, playoff_games=6):
    """Rows sorted like the loader output plus {game_id: {number: state}} with consistent lags and counts."""
    rng = np.random.default_rng(seed)
    rows, supplement = [], {}
    for season, game_type, start in SEASONS:
        for g in range(playoff_games if game_type == "playoffs" else games):
            game_id = f"{season}-{game_type[0]}-{g:03d}"
            home, away = 1 + g % 6, 1 + (g + 1) % 6 if (g + 1) % 6 != g % 6 else 7
            counts, past, score = {}, [], 0
            states = supplement.setdefault(game_id, {})
            for number in range(1, possessions + 1):
                period = 1 + (number - 1) // 10
                clock = float(720 - ((number - 1) % 10) * 70)
                offense, defense = (home, away) if number % 2 else (away, home)
                d_fouls, o_fouls = counts.get((period, defense), 0), counts.get((period, offense), 0)
                recent = int(bool(past[-2:]) and 1 in past[-2:])
                eta = -1.7 + 0.5 * recent + 0.15 * d_fouls + (0.3 if game_type == "playoffs" else 0)
                outcome = int(rng.random() < 1 / (1 + np.exp(-eta)))
                score += int(rng.integers(-3, 4))
                rows.append({"game_id": game_id, "date": (start + timedelta(days=g)).isoformat(), "season": season,
                             "game_type": game_type, "possession_number": number, "period": period,
                             "clock": clock, "score_margin": abs(score), "score_difference": score,
                             "defense_team_id": defense, "offense_team_id": offense,
                             "home_defense": int(defense == home), "defense_counted_fouls": d_fouls,
                             "previous_foul_1": past[-1] if past else None,
                             "previous_foul_2": past[-2] if len(past) > 1 else None,
                             "start_type": "before_control_event", "outcome": outcome})
                states[number] = {"defense_team_fouls": d_fouls, "offense_team_fouls": o_fouls,
                                  "defense_in_penalty": team_fouls.in_penalty(d_fouls, 0, clock, period),
                                  "offense_in_penalty": team_fouls.in_penalty(o_fouls, 0, clock, period),
                                  "counted_foul_events": outcome}
                if outcome:
                    counts[(period, defense)] = d_fouls + 1
                past.append(outcome)
    rows.sort(key=lambda r: (r["date"], r["game_id"], r["possession_number"]))
    return rows, supplement
