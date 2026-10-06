"""Command line entry point: spec-check --req req.md --diff change.diff ..."""

import argparse
import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path

import openai

from spec_check.checker import CheckError, run_check
from spec_check.llm import LLMClient, client_from_env
from spec_check.prompts import DEFAULT_PROMPT_VERSION, PROMPTS
from spec_check.report import render_markdown
from spec_check.requirements import RequirementError, parse_requirement

EXIT_OK = 0
EXIT_GAPS = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-check",
        description="Check a code change (git diff) against a requirement's acceptance criteria.",
    )
    parser.add_argument("--req", required=True, type=Path, help="requirement Markdown file")
    parser.add_argument("--diff", required=True, type=Path, help="unified git diff file")
    parser.add_argument("--out", type=Path, help="write the Markdown report here (default: stdout)")
    parser.add_argument("--json", type=Path, help="also write the full result as JSON")
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="exit 1 if any criterion is not implemented, not tested, "
        "or has evidence that failed verification",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT_VERSION,
        choices=sorted(PROMPTS),
        help=f"prompt version (default: {DEFAULT_PROMPT_VERSION})",
    )
    parser.add_argument("--model", help="override SPEC_CHECK_MODEL")
    parser.add_argument("-q", "--quiet", action="store_true", help="only log warnings")
    return parser


def main(
    argv: list[str] | None = None,
    client_factory: Callable[[str | None], LLMClient] = client_from_env,
) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # the report contains emoji

    try:
        requirement = parse_requirement(args.req.read_text(encoding="utf-8"))
        diff_text = args.diff.read_text(encoding="utf-8")
        client = client_factory(args.model)
        report = run_check(requirement, diff_text, client, prompt_version=args.prompt)
    except (OSError, RequirementError, CheckError, RuntimeError, openai.APIError) as exc:
        print(f"spec-check: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    markdown = render_markdown(report)
    if args.out:
        args.out.write_text(markdown, encoding="utf-8")
        print(f"Report written to {args.out}", file=sys.stderr)
    else:
        print(markdown)
    if args.json:
        args.json.write_text(json.dumps(report.to_json_dict(), indent=2), encoding="utf-8")

    print(
        f"{len(report.results)} criteria, {sum(r.has_gap for r in report.results)} with gaps, "
        f"{sum(r.needs_human_review for r in report.results)} need review, "
        f"{report.unverified_snippets}/{report.total_snippets} snippets unverified, "
        f"{report.total_tokens} tokens, {report.total_latency_s:.1f}s",
        file=sys.stderr,
    )
    if args.fail_on_gaps and report.has_gaps():
        return EXIT_GAPS
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
