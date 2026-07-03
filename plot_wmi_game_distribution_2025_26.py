from glob import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_GLOB = "wmi_games_2025_26_asof_*.csv"


def latest_input_path():
    matches = sorted(glob(INPUT_GLOB))
    if not matches:
        raise FileNotFoundError(f"No files matched {INPUT_GLOB}")
    return Path(matches[-1])


def output_path_for(input_path):
    stamp = input_path.stem.replace("wmi_games_2025_26_asof_", "")
    return Path(f"wmi_game_distribution_2025_26_asof_{stamp}.png")


def gaussian_kde_curve(values, grid_points=400):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("No finite WMI_game values found.")

    std = np.std(values, ddof=1) if values.size > 1 else 0.0
    if values.size == 1 or std == 0.0:
        x_grid = np.linspace(values[0] - 0.5, values[0] + 0.5, grid_points)
        density = np.zeros_like(x_grid)
        density[np.argmin(np.abs(x_grid - values[0]))] = 1.0
        return x_grid, density

    bandwidth = 1.06 * std * (values.size ** (-1.0 / 5.0))
    if bandwidth <= 0:
        bandwidth = 0.1

    xmin = min(0.0, values.min() - (3 * bandwidth))
    xmax = values.max() + (3 * bandwidth)
    x_grid = np.linspace(xmin, xmax, grid_points)

    scaled = (x_grid[:, None] - values[None, :]) / bandwidth
    kernel = np.exp(-0.5 * (scaled ** 2)) / np.sqrt(2 * np.pi)
    density = kernel.mean(axis=1) / bandwidth
    return x_grid, density


def build_plot(input_path, output_path):
    df = pd.read_csv(input_path)
    values = df["WMI_game"].dropna().astype(float).to_numpy()
    if values.size == 0:
        raise ValueError(f"No WMI_game values found in {input_path}")

    x_grid, density = gaussian_kde_curve(values)

    mean_wmi = float(values.mean())
    median_wmi = float(np.median(values))
    count = int(values.size)
    as_of_date = str(df["as_of_utc_date"].iloc[0]) if "as_of_utc_date" in df.columns else "unknown"

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 7))

    ax.hist(
        values,
        bins=30,
        density=True,
        color="#9ecae1",
        edgecolor="#2b5d7d",
        alpha=0.75,
        label="Histogram (density)",
    )
    ax.plot(x_grid, density, color="#c23b22", linewidth=2.5, label="Smoothed density curve")
    ax.axvline(mean_wmi, color="#1d3557", linestyle="--", linewidth=2, label=f"Mean = {mean_wmi:.3f}")
    ax.axvline(median_wmi, color="#2a9d8f", linestyle=":", linewidth=2, label=f"Median = {median_wmi:.3f}")

    ax.set_title("2025-26 WMI_game Distribution", fontsize=17, pad=14)
    ax.set_xlabel("WMI_game", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.text(
        0.99,
        0.97,
        f"As of {as_of_date}\nGames: {count}",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=11,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    ax.legend(frameon=True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return {
        "count": count,
        "mean_wmi_game": mean_wmi,
        "median_wmi_game": median_wmi,
        "min_wmi_game": float(values.min()),
        "max_wmi_game": float(values.max()),
        "as_of_utc_date": as_of_date,
    }


def main():
    input_path = latest_input_path()
    output_path = output_path_for(input_path)
    stats = build_plot(input_path=input_path, output_path=output_path)

    print("OK")
    print("input_path", input_path)
    print("output_path", output_path)
    print("as_of_utc_date", stats["as_of_utc_date"])
    print("games", stats["count"])
    print("mean_wmi_game", stats["mean_wmi_game"])
    print("median_wmi_game", stats["median_wmi_game"])
    print("min_wmi_game", stats["min_wmi_game"])
    print("max_wmi_game", stats["max_wmi_game"])


if __name__ == "__main__":
    main()
