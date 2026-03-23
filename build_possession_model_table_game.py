import argparse

from wmi_rawgame_utils import build_possession_model_table
from wmi_rawgame_utils import default_possession_table_out_path


def parse_args():
    parser = argparse.ArgumentParser(description="Build a possession-level modeling table for any NBA game.")
    parser.add_argument("--game-id", required=True, help="NBA game ID, for example 0022500802")
    parser.add_argument(
        "--out-path",
        help="CSV output path. Default: possession_model_table_<game_id>.csv",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    out_path = args.out_path or default_possession_table_out_path(args.game_id)
    out_df = build_possession_model_table(args.game_id)
    out_df.to_csv(out_path, index=False)

    print("OK")
    print("game_id", args.game_id)
    print("rows", len(out_df))
    print(out_df.head(20).to_string(index=False))
    print("saved", out_path)


if __name__ == "__main__":
    main()

