from wmi_rawgame_utils import build_possession_model_table

GAME_ID = "0022500789"
OUT_PATH = "possession_model_table_okc_mil.csv"


def main():
    out_df = build_possession_model_table(GAME_ID)
    out_df.to_csv(OUT_PATH, index=False)
    print("OK")
    print("game_id", GAME_ID)
    print("rows", len(out_df))
    print(out_df.head(20).to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
