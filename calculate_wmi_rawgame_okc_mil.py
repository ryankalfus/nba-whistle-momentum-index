import pandas as pd

IN_PATH = "possession_model_table_okc_mil.csv"
OUT_PATH = "wmi_rawgame_breakdown_okc_mil.csv"


def calculate_wmi_rawgame(df):
    # User formula:
    # M_t = F_t(1 + N_t)
    # WMI_game = [ (1 / n1) * sum_{t: L_t=1} M_t ] / [ (1 / n0) * sum_{t: L_t=0} M_t ]
    l = df["L_t"].astype(float)
    m = df["M_t"].astype(float)

    group_l1 = df[l == 1.0]
    group_l0 = df[l == 0.0]

    n1 = int(len(group_l1))
    n0 = int(len(group_l0))
    sum_m_l1 = float(group_l1["M_t"].astype(float).sum())
    sum_m_l0 = float(group_l0["M_t"].astype(float).sum())

    mean_m_l1 = None
    if n1 > 0:
        mean_m_l1 = float(sum_m_l1 / n1)

    mean_m_l0 = None
    if n0 > 0:
        mean_m_l0 = float(sum_m_l0 / n0)

    wmi_rawgame = None
    if mean_m_l1 is not None and mean_m_l0 not in (None, 0.0):
        wmi_rawgame = float(mean_m_l1 / mean_m_l0)

    return {
        "n1_count_L_t_eq_1": n1,
        "n0_count_L_t_eq_0": n0,
        "sum_M_t_where_L_t_eq_1": sum_m_l1,
        "sum_M_t_where_L_t_eq_0": sum_m_l0,
        "mean_M_t_where_L_t_eq_1": mean_m_l1,
        "mean_M_t_where_L_t_eq_0": mean_m_l0,
        "WMI_rawgame": wmi_rawgame,
    }


def main():
    df = pd.read_csv(IN_PATH)
    required = {"L_t", "M_t"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise ValueError(f"Missing required columns in {IN_PATH}: {missing}")

    result = calculate_wmi_rawgame(df)
    out_df = pd.DataFrame([result])
    out_df.to_csv(OUT_PATH, index=False)

    print("OK")
    print("input_rows", len(df))
    print(out_df.to_string(index=False))
    print("saved", OUT_PATH)


if __name__ == "__main__":
    main()
