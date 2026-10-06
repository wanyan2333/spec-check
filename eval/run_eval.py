"""Run spec-check against every evaluation case and score it against the verified labels.

Each case is checked `--runs` times (default 2) to measure run-to-run consistency.
Raw results go to eval/results/<prompt>.json, a Markdown summary to eval/results/<prompt>.md.

Usage:
    uv run python eval/run_eval.py --prompt v1
    uv run python eval/run_eval.py --prompt v2 --runs 2 --pause 5
    uv run python eval/run_eval.py --compare v1 v2      # table from saved results, no API calls
"""

import argparse
import json
import time

from case_tools import EVAL_DIR, list_cases, load_expected
from spec_check.checker import CheckError, run_check
from spec_check.llm import client_from_env
from spec_check.requirements import parse_requirement

RESULTS_DIR = EVAL_DIR / "results"


def run_all(prompt: str, runs: int, pause_s: float, only: list[str] | None) -> dict:
    client = client_from_env()
    cases = [c for c in list_cases() if not only or c.name[:2] in only]
    records = []
    for run in range(1, runs + 1):
        for case in cases:
            requirement = parse_requirement((case / "req.md").read_text(encoding="utf-8"))
            diff_text = (case / "change.diff").read_text(encoding="utf-8")
            print(f"run {run} {case.name} ...", flush=True)
            record = {"run": run, "case": case.name, "error": None}
            try:
                report = run_check(requirement, diff_text, client, prompt_version=prompt)
                record["report"] = report.to_json_dict()
            except CheckError as exc:
                record["error"] = str(exc)
            records.append(record)
            time.sleep(pause_s)  # stay under the free-tier requests-per-minute limit
    return {"prompt": prompt, "model": client.model, "runs": runs, "records": records}


# ---------- scoring ----------


def predictions(data: dict) -> list[dict]:
    """One row per (run, case, criterion) with expected and predicted labels."""
    rows = []
    for record in data["records"]:
        expected = load_expected(EVAL_DIR / "cases" / record["case"])
        results = {}
        if record["error"] is None:
            results = {r["id"]: r for r in record["report"]["results"]}
        for ac, label in expected.items():
            result = results.get(ac)
            rows.append(
                {
                    "run": record["run"],
                    "case": record["case"],
                    "ac": ac,
                    "exp_impl": label["implemented"],
                    "exp_tested": label["tested"],
                    "impl": result["implemented"] if result else "error",
                    "tested": result["tested"] if result else "error",
                    "review": result["needs_human_review"] if result else True,
                    "reasoning": result["reasoning"] if result else record["error"],
                    "evidence": result["evidence"] if result else [],
                    "review_reasons": result["review_reasons"] if result else [],
                    "confidence": result["confidence"] if result else 0.0,
                }
            )
    return rows


def ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.0f}%)"


def compute_metrics(data: dict) -> dict[str, str]:
    rows = predictions(data)
    impl_ok = [r for r in rows if r["impl"] == r["exp_impl"]]
    tested_ok = [r for r in rows if r["tested"] == r["exp_tested"]]
    both_ok = [r for r in impl_ok if r["tested"] == r["exp_tested"]]

    missing_impl = [r for r in rows if r["exp_impl"] != "yes"]
    missing_tests = [r for r in rows if r["exp_tested"] == "no"]
    correct_items = [r for r in rows if r["exp_impl"] == "yes" and r["exp_tested"] == "yes"]
    flagged_gap = [r for r in correct_items if r["impl"] != "yes" or r["tested"] != "yes"]
    flagged_any = [
        r for r in correct_items if r["impl"] != "yes" or r["tested"] != "yes" or r["review"]
    ]

    reports = [rec["report"] for rec in data["records"] if rec["error"] is None]
    snippets = sum(rep["summary"]["total_snippets"] for rep in reports)
    unverified = sum(rep["summary"]["unverified_snippets"] for rep in reports)
    calls = [c for rep in reports for c in rep["calls"]]
    latency = sum(rep["summary"]["total_latency_s"] for rep in reports)
    tokens = sum(rep["summary"]["total_tokens"] for rep in reports)

    # Consistency: same (implemented, tested) for a criterion in every run.
    by_item: dict[tuple, set] = {}
    for r in rows:
        by_item.setdefault((r["case"], r["ac"]), set()).add((r["impl"], r["tested"]))
    consistent = sum(1 for answers in by_item.values() if len(answers) == 1)

    return {
        "Judgments (criteria x runs)": str(len(rows)),
        "Implemented accuracy": ratio(len(impl_ok), len(rows)),
        "Tested accuracy": ratio(len(tested_ok), len(rows)),
        "Both correct": ratio(len(both_ok), len(rows)),
        "Missing-implementation detection (exp. no/partial, pred. not yes)": ratio(
            sum(r["impl"] != "yes" for r in missing_impl), len(missing_impl)
        ),
        "Missing-test detection (exp. tested=no, pred. no)": ratio(
            sum(r["tested"] == "no" for r in missing_tests), len(missing_tests)
        ),
        "False positives on fully correct items (pred. gap)": ratio(
            len(flagged_gap), len(correct_items)
        ),
        "False positives incl. human-review flags": ratio(len(flagged_any), len(correct_items)),
        "Unverified evidence snippets": ratio(unverified, snippets),
        "Run-to-run consistency": ratio(consistent, len(by_item)),
        "Errors (no usable output)": str(sum(rec["error"] is not None for rec in data["records"])),
        "Repair retries used": str(sum(c["purpose"] == "repair" for c in calls)),
        "429/5xx retries": str(sum(c["retries"] for c in calls)),
        "Avg latency per check": f"{latency / max(len(reports), 1):.2f}s",
        "Total tokens": str(tokens),
    }


# ---------- reporting ----------


def render_markdown(data: dict) -> str:
    rows = predictions(data)
    out = [
        f"# Eval results: prompt {data['prompt']}",
        "",
        f"Model `{data['model']}`, {data['runs']} runs per case, temperature 0. "
        "Generated by `eval/run_eval.py`.",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    out += [f"| {k} | {v} |" for k, v in compute_metrics(data).items()]

    out += [
        "",
        "## Per case",
        "",
        "| Case | AC | Expected (impl/tested) | "
        + " | ".join(f"Run {i}" for i in range(1, data["runs"] + 1))
        + " |",
        "|------|----|------------------------|" + "-------|" * data["runs"],
    ]
    grouped: dict[tuple, list[dict]] = {}
    for r in rows:
        grouped.setdefault((r["case"], r["ac"]), []).append(r)
    for (case, ac), items in grouped.items():
        cells = []
        for r in items:
            ok = r["impl"] == r["exp_impl"] and r["tested"] == r["exp_tested"]
            flag = "" if ok else " ❌"
            review = " ⚠️" if r["review"] else ""
            cells.append(f"{r['impl']}/{r['tested']}{flag}{review}")
        exp = f"{items[0]['exp_impl']}/{items[0]['exp_tested']}"
        out.append(f"| {case} | {ac} | {exp} | " + " | ".join(cells) + " |")
    out += ["", "❌ = wrong label, ⚠️ = flagged for human review by the evidence checks."]

    out += ["", "## Wrong judgments", ""]
    wrong = [r for r in rows if r["impl"] != r["exp_impl"] or r["tested"] != r["exp_tested"]]
    if not wrong:
        out.append("None.")
    for r in wrong:
        out.append(
            f"- **{r['case']} {r['ac']} (run {r['run']})**: expected "
            f"{r['exp_impl']}/{r['exp_tested']}, got {r['impl']}/{r['tested']} "
            f'(confidence {r["confidence"]}). Model reasoning: "{r["reasoning"]}"'
        )

    out += ["", "## Unverified evidence (possible hallucinations)", ""]
    bad = [(r, e) for r in rows for e in r["evidence"] if not e["verified"]]
    if not bad:
        out.append("None.")
    for r, e in bad:
        snippet = " ⏎ ".join(line.strip() for line in e["snippet"].splitlines())
        out.append(
            f"- {r['case']} {r['ac']} (run {r['run']}), `{e['file']}`: `{snippet}` ({e['note']})"
        )
    return "\n".join(out) + "\n"


def compare(versions: list[str]) -> str:
    metrics = {v: compute_metrics(load(v)) for v in versions}
    keys = list(next(iter(metrics.values())))
    out = ["| Metric | " + " | ".join(versions) + " |", "|--------|" + "------|" * len(versions)]
    out += [f"| {k} | " + " | ".join(metrics[v][k] for v in versions) + " |" for k in keys]
    return "\n".join(out)


def load(prompt: str) -> dict:
    return json.loads((RESULTS_DIR / f"{prompt}.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--pause", type=float, default=4.0, help="seconds between calls")
    parser.add_argument("--cases", help="comma-separated case numbers, e.g. 01,04")
    parser.add_argument("--compare", nargs="+", metavar="PROMPT")
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="re-render the Markdown from saved JSON without calling the API",
    )
    args = parser.parse_args()

    if args.compare:
        print(compare(args.compare))
        return
    RESULTS_DIR.mkdir(exist_ok=True)
    if args.rescore:
        data = load(args.prompt)
    else:
        only = args.cases.split(",") if args.cases else None
        data = run_all(args.prompt, args.runs, args.pause, only)
        (RESULTS_DIR / f"{args.prompt}.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8", newline="\n"
        )
    markdown = render_markdown(data)
    (RESULTS_DIR / f"{args.prompt}.md").write_text(markdown, encoding="utf-8", newline="\n")
    for key, value in compute_metrics(data).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
