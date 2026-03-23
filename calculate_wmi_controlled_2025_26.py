from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pandas as pd
import requests

from calculate_wmi_rawgames_2025_26 import MAX_WORKERS
from calculate_wmi_rawgames_2025_26 import SEASON
from calculate_wmi_rawgames_2025_26 import fetch_json_with_retry
from calculate_wmi_rawgames_2025_26 import find_max_existing_game_number
from calculate_wmi_rawgames_2025_26 import game_id
from wmi_controlled_utils import build_controlled_possession_table
from wmi_controlled_utils import fit_wmi_controlled_model


def build_game_table(session, gid):
    boxscore_url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gid}.json"
    boxscore_payload = fetch_json_with_retry(session, boxscore_url, timeout=30, tries=4)
    game = boxscore_payload.get("game", {})

    game_status = game.get("gameStatus")
    game_status_text = game.get("gameStatusText")
    if game_status != 3 and str(game_status_text).lower() != "final":
        return {"status": "skip_not_final", "game_id": gid}

    table_df = build_controlled_possession_table(gid, session=session)
    table_df = table_df.copy()
    table_df.insert(1, "game_date_et", game.get("gameEt"))
    table_df["_row_number_in_game"] = range(len(table_df))

    return {"status": "ok", "game_id": gid, "table": table_df}


def main():
    session = requests.Session()
    as_of_date = datetime.now(UTC).date().isoformat()
    stamp = as_of_date.replace("-", "_")
    table_out_path = f"wmi_controlled_table_2025_26_asof_{stamp}.csv"
    summary_out_path = f"wmi_controlled_2025_26_summary_asof_{stamp}.csv"

    max_existing = find_max_existing_game_number(session)
    if max_existing == 0:
        raise RuntimeError("No existing 2025-26 regular-season game IDs found.")

    game_ids = [game_id(i) for i in range(1, max_existing + 1)]
    print("season", SEASON)
    print("max_existing_game_number", max_existing)
    print("game_ids_checked", len(game_ids))

    tables = []
    skipped_not_final = []
    failed_ids = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(build_game_table, session, gid): gid for gid in game_ids}
        total = len(future_to_id)
        done = 0

        for future in as_completed(future_to_id):
            gid = future_to_id[future]
            done += 1
            try:
                result = future.result()
                status = result["status"]
                if status == "ok":
                    tables.append(result["table"])
                elif status == "skip_not_final":
                    skipped_not_final.append(gid)
                else:
                    failed_ids.append(gid)
            except Exception:
                failed_ids.append(gid)

            if done % 100 == 0 or done == total:
                print(
                    f"progress {done}/{total} ok={len(tables)} "
                    f"not_final={len(skipped_not_final)} failed={len(failed_ids)}"
                )

    if failed_ids:
        retry_failed = []
        for gid in failed_ids:
            try:
                result = build_game_table(session, gid)
                status = result["status"]
                if status == "ok":
                    tables.append(result["table"])
                elif status == "skip_not_final":
                    skipped_not_final.append(gid)
                else:
                    retry_failed.append(gid)
            except Exception:
                retry_failed.append(gid)
        failed_ids = retry_failed

    if not tables:
        raise RuntimeError("No completed games were successfully processed.")

    controlled_df = pd.concat(tables, ignore_index=True)
    controlled_df = controlled_df.sort_values(["game_id", "_row_number_in_game"]).reset_index(drop=True)
    controlled_df = controlled_df.drop(columns="_row_number_in_game")
    controlled_df.to_csv(table_out_path, index=False)

    rows_before_exclusion = int(len(controlled_df))
    rows_excluded_intentional = int(controlled_df["intentional_foul_excluded_t"].sum())
    model_input_df = controlled_df[controlled_df["intentional_foul_excluded_t"] == 0].copy()
    rows_before_model = int(len(model_input_df))
    model_result = fit_wmi_controlled_model(model_input_df)

    summary_row = {
        "season": SEASON,
        "as_of_utc_date": as_of_date,
        "model_id": model_result["model_id"],
        "trigger_variable": model_result["trigger_variable"],
        "formula": model_result["formula"],
        "games_requested": len(game_ids),
        "games_succeeded": int(controlled_df["game_id"].nunique()),
        "games_failed": len(set(failed_ids)),
        "rows_before_exclusion": rows_before_exclusion,
        "rows_excluded_intentional": rows_excluded_intentional,
        "rows_before_model": rows_before_model,
        "rows_used_in_model": model_result["rows_used_in_model"],
        "fit_method": model_result["fit_method"],
        "converged": model_result["converged"],
        "beta_trigger": model_result["beta_trigger"],
        "odds_ratio_trigger": model_result["odds_ratio_trigger"],
        "std_err_trigger": model_result["std_err_trigger"],
        "p_value_trigger": model_result["p_value_trigger"],
        "ci_low_beta": model_result["ci_low_beta"],
        "ci_high_beta": model_result["ci_high_beta"],
        "ci_low_odds_ratio": model_result["ci_low_odds_ratio"],
        "ci_high_odds_ratio": model_result["ci_high_odds_ratio"],
    }

    summary_df = pd.DataFrame([summary_row])
    summary_df.to_csv(summary_out_path, index=False)

    print("saved_table", table_out_path)
    print("saved_summary", summary_out_path)
    print("games_succeeded", summary_row["games_succeeded"])
    print("games_not_final", len(set(skipped_not_final)))
    print("games_failed", summary_row["games_failed"])
    print(summary_df.to_string(index=False))
    if failed_ids:
        print("failed_game_ids_sample", sorted(set(failed_ids))[:20])


if __name__ == "__main__":
    main()
