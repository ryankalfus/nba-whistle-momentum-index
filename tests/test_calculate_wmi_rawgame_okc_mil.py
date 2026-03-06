import pandas as pd

from calculate_wmi_rawgame_okc_mil import calculate_wmi_rawgame


def test_calculate_wmi_rawgame_returns_expected_summary():
    df = pd.DataFrame(
        {
            "L_t": [0, 1, 0, 1],
            "F_t": [1, 1, 0, 1],
            "N_t": [1, 0, 1, 0],
        }
    )

    result = calculate_wmi_rawgame(df)

    assert result["n1_count_L_t_eq_1"] == 2
    assert result["n0_count_L_t_eq_0"] == 2
    assert result["sum_M_t_where_L_t_eq_1"] == 2.0
    assert result["sum_M_t_where_L_t_eq_0"] == 2.0
    assert result["WMI_rawgame"] == 1.0
