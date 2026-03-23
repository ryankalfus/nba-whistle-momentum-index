import argparse

import pandas as pd

from wmi_rawgame_utils import build_possession_model_table
from wmi_rawgame_utils import calculate_wmi_rawgame
from wmi_rawgame_utils import default_possession_table_out_path
from wmi_rawgame_utils import default_wmi_breakdown_out_path


def parse_args():
    parser = argparse.ArgumentParser(description="Build and calculate WMI_rawgame for any NBA game.")
    parser.add_argument("--game-id", required=True, help="NBA game ID, for example 0022500802")
    parser.add_argument(
        "--table-out-path",
        help="CSV output path for the possession table. Default: possession_model_table_<game_id>.csv",
    )
    parser.add_argument(
        "--breakdown-out-path",
        help="CSV output path for the WMI breakdown. Default: wmi_rawgame_breakdown_<game_id>.csv",
    )
    parser.add_argument(
        "--skip-table-save",
        action="store_true",
        help="Skip saving the possession table CSV and only save the WMI breakdown CSV.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    table_out_path = args.table_out_path or default_possession_table_out_path(args.game_id)
    breakdown_out_path = args.breakdown_out_path or default_wmi_breakdown_out_path(args.game_id)

    table_df = build_possession_model_table(args.game_id)
    result = calculate_wmi_rawgame(table_df)
    out_df = pd.DataFrame([result])

    if not args.skip_table_save:
        table_df.to_csv(table_out_path, index=False)
    out_df.to_csv(breakdown_out_path, index=False)

    print("OK")
    print("game_id", args.game_id)
    print("input_rows", len(table_df))
    print(out_df.to_string(index=False))
    if not args.skip_table_save:
        print("saved_table", table_out_path)
    print("saved_breakdown", breakdown_out_path)


if __name__ == "__main__":
    main()
