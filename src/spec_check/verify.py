"""Anti-hallucination checks: is every quoted snippet really in the diff?

The LLM is asked to quote code verbatim. We do not trust that. For each evidence item:
  1. the cited file must be one of the files in the diff;
  2. the snippet (with any +/- diff prefixes removed, whitespace normalized) must appear
     in that file's post-change lines (context + added). Quoting only removed lines
     does not count as evidence that something is implemented now.
Claims without any verified evidence are flagged for human review.
"""

from spec_check.diff import FileDiff, is_test_file
from spec_check.models import CheckedEvidence, Criterion, CriterionResult, Evidence, Verdict

MIN_SNIPPET_CHARS = 4  # "le=5" is fine; ")" or "" is not evidence
LOW_CONFIDENCE = 0.5


def normalize_ws(line: str) -> str:
    return " ".join(line.split())


def _normalized_block(lines: list[str]) -> str:
    return "\n".join(n for line in lines if (n := normalize_ws(line)))


def _strip_diff_prefixes(snippet: str) -> str | None:
    """If every non-blank line starts with +, - or a space, drop that first char."""
    lines = [line for line in snippet.splitlines() if line.strip()]
    if lines and all(line[0] in "+- " for line in lines):
        return "\n".join(line[1:] for line in lines)
    return None


def _clean_path(path: str) -> str:
    path = path.strip().strip("`").replace("\\", "/")
    for prefix in ("a/", "b/", "./"):
        if path.startswith(prefix):
            path = path[len(prefix) :]
    return path


def match_file(cited: str, files: dict[str, FileDiff]) -> FileDiff | None:
    """Exact match, or an unambiguous match on a path suffix (e.g. 'src/app.py' vs 'app.py')."""
    cited = _clean_path(cited)
    if cited in files:
        return files[cited]
    candidates = [
        f for path, f in files.items() if path.endswith("/" + cited) or cited.endswith("/" + path)
    ]
    return candidates[0] if len(candidates) == 1 else None


def check_evidence(evidence: Evidence, files: dict[str, FileDiff]) -> CheckedEvidence:
    file_diff = match_file(evidence.file, files)
    test_file = is_test_file(evidence.file)

    def result(verified: bool, note: str = "") -> CheckedEvidence:
        return CheckedEvidence(
            file=evidence.file,
            snippet=evidence.snippet,
            verified=verified,
            is_test_file=test_file,
            note=note,
        )

    if file_diff is None:
        return result(False, "file is not part of the diff")

    candidates = [evidence.snippet]
    stripped = _strip_diff_prefixes(evidence.snippet)
    if stripped is not None:
        candidates.append(stripped)
    candidates = [c for c in (_normalized_block(c.splitlines()) for c in candidates) if c]
    if not candidates or max(len(c) for c in candidates) < MIN_SNIPPET_CHARS:
        return result(False, "snippet is empty or too short to be evidence")

    new_text = _normalized_block(file_diff.new_lines)
    if any(c in new_text for c in candidates):
        return result(True)
    old_text = _normalized_block(file_diff.old_lines)
    if any(c in old_text for c in candidates):
        return result(False, "snippet only matches removed lines")
    return result(False, "snippet not found in this file's diff")


def build_result(
    criterion: Criterion, verdict: Verdict, files: dict[str, FileDiff]
) -> CriterionResult:
    checked = [check_evidence(e, files) for e in verdict.evidence]
    reasons: list[str] = []

    unverified = [e for e in checked if not e.verified]
    if unverified:
        reasons.append(f"{len(unverified)} evidence snippet(s) failed verification")
    if verdict.implemented in ("yes", "partial") and not any(
        e.verified and not e.is_test_file for e in checked
    ):
        reasons.append(
            f"claims implemented={verdict.implemented} without verified non-test evidence"
        )
    if verdict.tested == "yes" and not any(e.verified and e.is_test_file for e in checked):
        reasons.append("claims tested=yes without verified evidence from a test file")
    if verdict.tested == "yes" and verdict.implemented == "no":
        reasons.append("contradiction: tested=yes but implemented=no")
    if verdict.confidence < LOW_CONFIDENCE:
        reasons.append(f"low model confidence ({verdict.confidence:.2f})")

    return CriterionResult(
        id=criterion.id,
        text=criterion.text,
        implemented=verdict.implemented,
        tested=verdict.tested,
        confidence=verdict.confidence,
        reasoning=verdict.reasoning,
        evidence=checked,
        review_reasons=reasons,
    )
