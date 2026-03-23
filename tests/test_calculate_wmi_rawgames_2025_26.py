import math
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculate_wmi_rawgames_2025_26 import add_z_scores


def test_add_z_scores_returns_expected_values():
    df = pd.DataFrame({"WMI_rawgame": [1.0, 2.0, 3.0]})
    out, mean_wmi, std_wmi = add_z_scores(df)

    assert math.isclose(mean_wmi, 2.0)
    assert math.isclose(std_wmi, (2.0 / 3.0) ** 0.5)
    assert math.isclose(out.loc[0, "wmi_rawgame_z_score"], -1.22474487139, rel_tol=1e-9)
    assert math.isclose(out.loc[1, "wmi_rawgame_z_score"], 0.0, abs_tol=1e-12)
    assert math.isclose(out.loc[2, "wmi_rawgame_z_score"], 1.22474487139, rel_tol=1e-9)


def test_add_z_scores_handles_zero_std():
    df = pd.DataFrame({"WMI_rawgame": [0.5, 0.5]})
    out, mean_wmi, std_wmi = add_z_scores(df)

    assert math.isclose(mean_wmi, 0.5)
    assert math.isclose(std_wmi, 0.0)
    assert out["wmi_rawgame_z_score"].isna().all()
