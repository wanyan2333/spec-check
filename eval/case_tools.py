"""Shared helpers for the evaluation scripts (build_cases, verify_labels, run_eval)."""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
SAMPLE_APP = EVAL_DIR / "sample_app"
CASES_DIR = EVAL_DIR / "cases"

# Fixed identity and line endings so generated diffs are reproducible on any machine.
GIT = ["git", "-c", "core.autocrlf=false", "-c", "user.name=eval", "-c", "user.email=eval@x"]
PYTEST = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def list_cases() -> list[Path]:
    return sorted(p for p in CASES_DIR.iterdir() if (p / "req.md").exists())


def load_expected(case: Path) -> dict[str, dict[str, str]]:
    return json.loads((case / "expected.json").read_text(encoding="utf-8"))["criteria"]


def copy_sample_app(dest: Path) -> Path:
    shutil.copytree(SAMPLE_APP, dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return dest


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [*GIT, *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout


def run_suite(workdir: Path) -> bool:
    """Run the sample app's own tests. True if they all pass."""
    result = subprocess.run([*PYTEST, "test_app.py"], cwd=workdir, capture_output=True)
    return result.returncode == 0


def run_probes(workdir: Path) -> dict[str, bool]:
    """Run probes.py and return {test_name: passed}. Collection errors count as all failed."""
    report = workdir / "_probes.xml"
    subprocess.run([*PYTEST, "probes.py", f"--junitxml={report}"], cwd=workdir, capture_output=True)
    outcomes: dict[str, bool] = {}
    if report.exists():
        for case in ET.parse(report).getroot().iter("testcase"):
            failed = case.find("failure") is not None or case.find("error") is not None
            outcomes[case.get("name")] = not failed
        report.unlink()
    return outcomes
