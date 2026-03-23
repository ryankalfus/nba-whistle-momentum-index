import pandas as pd

from wmi_rawgame_utils import calculate_wmi_rawgame

IN_PATH = "possession_model_table_okc_mil.csv"
OUT_PATH = "wmi_rawgame_breakdown_okc_mil.csv"


def main():
    df = pd.read_csv(IN_PATH)
    result = calculate_wmi_rawgame(df)
    out_df = pd.DataFrame([result])
    out_df.to_csv(OUT_PATH, index=False)

    print("OK")
    print("input_rows", len(df))
    print(out_df.to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
