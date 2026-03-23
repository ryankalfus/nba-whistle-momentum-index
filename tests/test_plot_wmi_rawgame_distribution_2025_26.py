from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plot_wmi_rawgame_distribution_2025_26 import gaussian_kde_curve
from plot_wmi_rawgame_distribution_2025_26 import output_path_for


def test_output_path_for_uses_matching_stamp():
    input_path = Path("wmi_rawgames_2025_26_asof_2026_03_23.csv")
    assert str(output_path_for(input_path)) == "wmi_rawgame_distribution_2025_26_asof_2026_03_23.png"


def test_gaussian_kde_curve_returns_nonnegative_density():
    x_grid, density = gaussian_kde_curve(np.array([0.5, 1.0, 1.5]))

    assert len(x_grid) == 400
    assert len(density) == 400
    assert np.all(np.isfinite(density))
    assert np.all(density >= 0)
