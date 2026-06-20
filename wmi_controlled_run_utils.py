import time
from datetime import UTC, datetime

import pandas as pd

from wmi_controlled_utils import build_controlled_tables_for_game_ids
from wmi_controlled_utils import calculate_wmi_controlled


def season_label(prefix):
    start_year = 2000 + prefix
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def game_id_from_prefix(prefix, number):
    return f"002{prefix:02d}{number:05d}"


def fetch_json_with_retry(session, url, timeout=30, tries=4):
    last_error = None
    for i in range(tries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as error:
            last_error = error
            time.sleep(0.6 * (i + 1))
    raise last_error


def compute_controlled_summary_for_game_ids(
    game_ids,
    *,
    season,
    session,
    as_of_utc_date=None,
    max_workers=10,
    timeout=30,
    extra_fields=None,
):
    if as_of_utc_date is None:
        as_of_utc_date = datetime.now(UTC).date().isoformat()

    tables, failed_ids = build_controlled_tables_for_game_ids(
        game_ids=game_ids,
        session=session,
        timeout=timeout,
        max_workers=max_workers,
    )
    if not tables:
        raise RuntimeError("No controlled possession tables were built.")

    all_possessions = pd.concat(tables, ignore_index=True)
    result = calculate_wmi_controlled(all_possessions)
    summary = {
        "season": season,
        "as_of_utc_date": as_of_utc_date,
        "games_requested": len(game_ids),
        "games_succeeded": int(all_possessions["game_id"].nunique()),
        "games_failed": len(failed_ids),
    }
    if extra_fields:
        summary.update(extra_fields)
    summary.update(result)
    return summary, all_possessions, failed_ids
