"""Offline package and environment diagnostics."""

import argparse
from importlib import metadata
import json
import platform

from whistle_research import __version__


def environment() -> dict:
    """Describe the environment without importing scientific libraries."""
    packages = {}
    for name in ("numpy", "pandas", "scipy", "statsmodels", "scikit-learn"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "package_version": __version__,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "machine": platform.machine(),
        "dependencies": packages,
        "research_status": "development; independent reconstruction audit pending",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("command", choices=("environment",))
    parser.parse_args()
    print(json.dumps(environment(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
