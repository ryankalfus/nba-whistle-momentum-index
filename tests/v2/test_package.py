"""The installed entry points work without scientific imports or network access."""

import json
from pathlib import Path
import subprocess
import sys
import tomllib

from whistle_research import __version__
from whistle_research.__main__ import environment


def test_package_version_matches_metadata():
    root = Path(__file__).resolve().parents[2]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert __version__ == project["project"]["version"]


def test_environment_is_explicit():
    report = environment()
    assert report["package_version"] == __version__
    assert report["python"].startswith("3.14.")
    assert all(report["dependencies"].values())
    assert "audit pending" in report["research_status"]


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-I", "-m", "whistle_research", "environment"],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout)["package_version"] == __version__
