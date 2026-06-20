import pandas as pd
import requests

from wmi_controlled_run_utils import compute_controlled_summary_for_game_ids


SEASON = "2025-26"
SEASON_GAME_ID_PREFIX = "00225"
MAX_GAME_NUMBER = 896
AS_OF_UTC_DATE = "2026-03-01"
OUT_PATH = "wmi_controlledseason_2025_26_summary_asof_2026_03_01.csv"
TABLE_OUT_PATH = "wmi_controlledseason_2025_26_table_asof_2026_03_01.csv"
MAX_WORKERS = 10


def get_game_ids():
    return [f"{SEASON_GAME_ID_PREFIX}{i:05d}" for i in range(1, MAX_GAME_NUMBER + 1)]


def main():
    session = requests.Session()
    game_ids = get_game_ids()

    print("season", SEASON)
    print("games_requested", len(game_ids))

    summary, all_possessions, failed_ids = compute_controlled_summary_for_game_ids(
        game_ids,
        season=SEASON,
        session=session,
        as_of_utc_date=AS_OF_UTC_DATE,
        max_workers=MAX_WORKERS,
    )

    pd.DataFrame([summary]).to_csv(OUT_PATH, index=False)
    all_possessions.to_csv(TABLE_OUT_PATH, index=False)

    print("saved_summary", OUT_PATH)
    print("saved_table", TABLE_OUT_PATH)
    print(pd.DataFrame([summary]).to_string(index=False))
    if failed_ids:
        print("failed_game_ids_sample", failed_ids[:20])


if __name__ == "__main__":
    main()
