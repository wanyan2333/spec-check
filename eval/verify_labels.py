"""Programmatically verify every ground-truth label in eval/cases.

For each case (in a temporary copy of eval/sample_app):
  0. `git apply change.diff` and check the result equals the case's after/ files,
     i.e. the diff really is the change that was made.
  1. The sample app's own tests must all pass after the change. Every defect in the
     cases is therefore invisible to the existing test suite.
  2. implemented label: hidden behavioral probes (probes.py, tests named test_acN_*)
     are run. yes = all of the criterion's probes pass, no = none pass,
     partial = some pass.
  3. tested label: for criteria with implemented != no, the implementation is broken
     with the mutation(s) in mutations.json. The mutation must be effective (at least
     one probe for that criterion that passed now fails). Then:
       tested=yes -> at least one sample app test must fail;
       tested=no  -> all sample app tests must still pass.
     For implemented=no the label must be tested=no (nothing exists to test).

Results are written to eval/LABEL_VERIFICATION.md. Exit code 1 if any label disagrees.

Usage: uv run python eval/verify_labels.py
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from case_tools import (
    EVAL_DIR,
    copy_sample_app,
    list_cases,
    load_expected,
    run_probes,
    run_suite,
)

OUTPUT = EVAL_DIR / "LABEL_VERIFICATION.md"


@dataclass
class Row:
    case: str
    ac: str
    label_impl: str
    label_tested: str
    probes: str  # e.g. "2/3 pass"
    impl_observed: str
    mutation: str  # what happened when the implementation was broken
    tested_observed: str
    ok: bool
    problem: str = ""


def probe_ac(name: str) -> str | None:
    match = re.match(r"test_(ac\d+)_", name)
    return match.group(1).upper() if match else None


def classify(passed: list[bool]) -> str:
    if all(passed):
        return "yes"
    if not any(passed):
        return "no"
    return "partial"


def apply_mutation(workdir: Path, edits: list[dict]) -> dict[Path, str]:
    """Apply find/replace edits; return the original contents for restoring."""
    originals: dict[Path, str] = {}
    for edit in edits:
        path = workdir / edit["file"]
        current = path.read_text(encoding="utf-8")
        originals.setdefault(path, current)
        count = current.count(edit["find"])
        if count != 1:
            raise ValueError(f"mutation target found {count} times in {edit['file']}")
        path.write_text(current.replace(edit["find"], edit["replace"]), encoding="utf-8")
    return originals


def verify_case(case: Path) -> tuple[list[Row], list[str]]:
    expected = load_expected(case)
    mutations = json.loads((case / "mutations.json").read_text(encoding="utf-8"))
    rows: list[Row] = []
    case_problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        work = copy_sample_app(Path(tmp) / "app")
        subprocess.run(
            ["git", "apply", "--whitespace=nowarn", str((case / "change.diff").resolve())],
            cwd=work,
            check=True,
            capture_output=True,
        )
        for after_file in (case / "after").rglob("*"):
            if after_file.is_file():
                applied = (work / after_file.relative_to(case / "after")).read_text("utf-8")
                if applied != after_file.read_text("utf-8"):
                    case_problems.append(
                        f"change.diff does not reproduce after/{after_file.name}"
                        " (run eval/build_cases.py)"
                    )
        (work / "probes.py").write_text((case / "probes.py").read_text("utf-8"), "utf-8")

        if not run_suite(work):
            case_problems.append("sample app tests fail after applying the change")
        baseline = run_probes(work)

        for ac, label in expected.items():
            names = [n for n in baseline if probe_ac(n) == ac]
            if not names:
                rows.append(
                    Row(
                        case.name,
                        ac,
                        label["implemented"],
                        label["tested"],
                        "-",
                        "-",
                        "-",
                        "-",
                        False,
                        "no probes for this criterion",
                    )
                )
                continue
            passed = [baseline[n] for n in names]
            impl_observed = classify(passed)
            probes = f"{sum(passed)}/{len(passed)} pass"
            problems = []
            if impl_observed != label["implemented"]:
                problems.append(f"probes say implemented={impl_observed}")

            if label["implemented"] == "no":
                mutation = "n/a (nothing implemented)"
                tested_observed = "no"
            elif ac not in mutations:
                mutation, tested_observed = "missing", "?"
                problems.append("no mutation defined")
            else:
                originals = apply_mutation(work, mutations[ac])
                suite_passes = run_suite(work)
                after = run_probes(work)
                for path, text in originals.items():
                    path.write_text(text, encoding="utf-8")
                broken = [n for n in names if baseline[n] and not after.get(n, False)]
                if not broken:
                    problems.append("mutation did not break any passing probe")
                tested_observed = "no" if suite_passes else "yes"
                mutation = (
                    f"breaks {len(broken)} probe(s); app tests "
                    f"{'still pass' if suite_passes else 'FAIL'}"
                )
            if tested_observed != label["tested"]:
                problems.append(f"mutation testing says tested={tested_observed}")

            rows.append(
                Row(
                    case.name,
                    ac,
                    label["implemented"],
                    label["tested"],
                    probes,
                    impl_observed,
                    mutation,
                    tested_observed,
                    not problems,
                    "; ".join(problems),
                )
            )
    return rows, case_problems


def write_report(all_rows: list[Row], problems: dict[str, list[str]]) -> None:
    ok = all(r.ok for r in all_rows) and not any(problems.values())
    lines = [
        "# Label verification",
        "",
        "Generated by `uv run python eval/verify_labels.py`. Do not edit by hand.",
        "",
        "How each label is checked (see the script docstring for details):",
        "",
        "- **change.diff is real**: `git apply change.diff` on a copy of `eval/sample_app` "
        "must reproduce the case's `after/` files exactly.",
        "- **Existing tests pass**: the sample app's test suite passes after the change, so "
        "none of the defects below is caught by the tests in the diff.",
        "- **implemented**: hidden behavioral probes (`probes.py`, not part of the diff) for "
        "the criterion: all pass = yes, some pass = partial, none pass = no.",
        "- **tested**: the implementation is broken with the mutation in `mutations.json` "
        "(which must make at least one of the criterion's probes fail). If an app test then "
        "fails, tested = yes; if all app tests still pass, tested = no.",
        "",
        f"**Result: {'ALL LABELS CONFIRMED' if ok else 'MISMATCHES FOUND'}** "
        f"({sum(r.ok for r in all_rows)}/{len(all_rows)} criteria agree)",
        "",
        "| Case | AC | Label impl. | Probes | Observed impl. | Mutation result | Label tested "
        "| Observed tested | OK |",
        "|------|----|-------------|--------|----------------|-----------------|--------------"
        "|-----------------|----|",
    ]
    for r in all_rows:
        lines.append(
            f"| {r.case} | {r.ac} | {r.label_impl} | {r.probes} | {r.impl_observed} | "
            f"{r.mutation} | {r.label_tested} | {r.tested_observed} | "
            f"{'yes' if r.ok else 'NO: ' + r.problem} |"
        )
    lines += ["", "## Case-level checks", ""]
    for case, issues in problems.items():
        status = "; ".join(issues) if issues else "diff reproduces after/, app tests pass"
        lines.append(f"- `{case}`: {'OK' if not issues else 'PROBLEM'} — {status}")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    all_rows: list[Row] = []
    problems: dict[str, list[str]] = {}
    for case in list_cases():
        rows, case_problems = verify_case(case)
        all_rows += rows
        problems[case.name] = case_problems
        for r in rows:
            mark = "ok " if r.ok else "BAD"
            print(
                f"[{mark}] {r.case} {r.ac}: impl {r.label_impl} (probes {r.impl_observed}), "
                f"tested {r.label_tested} (observed {r.tested_observed}) {r.problem}"
            )
        for issue in case_problems:
            print(f"[BAD] {case.name}: {issue}")
    write_report(all_rows, problems)
    ok = all(r.ok for r in all_rows) and not any(problems.values())
    print(f"\n{'All labels confirmed' if ok else 'MISMATCHES FOUND'}; see {OUTPUT.name}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
