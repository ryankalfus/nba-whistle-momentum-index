"""Run the maintained offline checks with the project's Python environment."""

from pathlib import Path
import subprocess
import sys
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
LEGACY_LINT = [
    "forecast_foul_sequences.py", "run_all_wmi_hypotheses.py",
    "run_wmi_expansion_analysis.py", "validate_wmi.py", "validate_wmi_intervals.py",
    "wmi_possessions.py", "wmi_utils.py", "tests/test_all_wmi_hypotheses.py",
    "tests/test_wmi_validation.py",
]


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        raise SystemExit("Run this check with .venv/bin/python scripts/check.py")
    python = sys.executable
    run([python, "-m", "pip", "check"])
    run([python, "-m", "ruff", "check", *LEGACY_LINT, "src", "scripts", "tests/v2"])
    run([python, "-m", "pytest", "-q"])
    run(["node", "tests/test_site.cjs"])
    run(["node", "--test", "tests/test_v2_site.cjs"])
    run([python, "-m", "whistle_research", "environment"])
    # Install the wheel without editable paths or dependencies, outside the source tree.
    # The package's basic diagnostics intentionally need only the standard library.
    with tempfile.TemporaryDirectory(prefix="whistle-build-", dir=ROOT) as temporary:
        work = Path(temporary)
        wheel_dir = work / "dist"
        run([python, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(wheel_dir)])
        wheels = list(wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit("Expected exactly one built wheel")
        clean_env = work / "venv"
        venv.EnvBuilder(with_pip=True).create(clean_env)
        clean_python = str(clean_env / "bin" / "python")
        run([clean_python, "-m", "pip", "install", "--no-deps", str(wheels[0])], cwd=work)
        run([clean_python, "-I", "-m", "whistle_research", "--version"], cwd=work)
        run([clean_python, "-I", "-m", "whistle_research", "environment"], cwd=work)
    print("All maintained offline checks passed.", flush=True)


if __name__ == "__main__":
    main()
