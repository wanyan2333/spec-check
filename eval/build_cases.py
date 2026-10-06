"""Generate each case's change.diff from a real code change.

For every eval/cases/NN-name/ case, this script:
  1. copies eval/sample_app into a temporary directory and commits it to a fresh git repo;
  2. overwrites the files listed in the case's after/ directory (the real modified code);
  3. writes `git diff` of that working tree to the case's change.diff.

Usage: uv run python eval/build_cases.py
"""

import shutil
import tempfile
from pathlib import Path

from case_tools import copy_sample_app, git, list_cases


def build_diff(case: Path) -> str:
    after = case / "after"
    with tempfile.TemporaryDirectory() as tmp:
        repo = copy_sample_app(Path(tmp) / "sample_app")
        git(repo, "init", "-q")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "base")
        for src in after.rglob("*"):
            if src.is_file():
                dest = repo / src.relative_to(after)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
        git(repo, "add", "-A")
        return git(repo, "diff", "--cached", "--no-color")


def main() -> None:
    for case in list_cases():
        diff = build_diff(case)
        if not diff.strip():
            raise SystemExit(f"{case.name}: after/ produces an empty diff")
        (case / "change.diff").write_text(diff, encoding="utf-8", newline="\n")
        changed = [line[6:] for line in diff.splitlines() if line.startswith("+++ b/")]
        print(f"{case.name}: {len(diff.splitlines())} diff lines, files: {', '.join(changed)}")


if __name__ == "__main__":
    main()
