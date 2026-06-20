import time

import pandas as pd
import requests

from calculate_wmi_rawseason_2010_11_to_2023_24 import find_max_existing_game_number
from calculate_wmi_rawseason_2010_11_to_2023_24 import season_exists
from wmi_controlled_run_utils import compute_controlled_summary_for_game_ids
from wmi_controlled_run_utils import game_id_from_prefix
from wmi_controlled_run_utils import season_label


START_PREFIX = 10
END_PREFIX = 23
AS_OF_UTC_DATE = "2026-03-01"
OUT_PATH = "wmi_controlledseason_2010_11_to_2023_24.csv"
MAX_WORKERS = 8


def main():
    session = requests.Session()

    requested = [season_label(p) for p in range(START_PREFIX, END_PREFIX + 1)]
    available = [p for p in range(START_PREFIX, END_PREFIX + 1) if season_exists(session, p)]
    unavailable = [p for p in range(START_PREFIX, END_PREFIX + 1) if p not in available]

    print("requested_seasons", requested)
    print("available_seasons", [season_label(p) for p in available])
    print("unavailable_seasons", [season_label(p) for p in unavailable])

    rows = []
    for prefix in available:
        season = season_label(prefix)
        max_num = find_max_existing_game_number(session, prefix)
        if max_num == 0:
            rows.append(
                {
                    "season": season,
                    "season_prefix": f"002{prefix:02d}",
                    "as_of_utc_date": AS_OF_UTC_DATE,
                    "max_existing_game_number": 0,
                    "games_requested": 0,
                    "games_succeeded": 0,
                    "games_failed": 0,
                    "model_id": None,
                    "formula": None,
                    "fit_method": None,
                    "fit_status": "no_games_found",
                    "converged": False,
                    "WMI_controlled": None,
                }
            )
            continue

        print(f"--- computing {season} ---")
        game_ids = [game_id_from_prefix(prefix, i) for i in range(1, max_num + 1)]
        summary, _, _ = compute_controlled_summary_for_game_ids(
            game_ids,
            season=season,
            session=session,
            as_of_utc_date=AS_OF_UTC_DATE,
            max_workers=MAX_WORKERS,
            extra_fields={
                "season_prefix": f"002{prefix:02d}",
                "max_existing_game_number": max_num,
            },
        )
        rows.append(summary)
        time.sleep(1.5)

    out_df = pd.DataFrame(rows).sort_values("season").reset_index(drop=True)
    out_df.to_csv(OUT_PATH, index=False)
    print("saved", OUT_PATH)
    keep_cols = [
        "season",
        "max_existing_game_number",
        "games_succeeded",
        "games_failed",
        "fit_status",
        "WMI_controlled",
    ]
    print(out_df[keep_cols].to_string(index=False))


if __name__ == "__main__":
    main()
