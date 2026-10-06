from spec_check.diff import parse_diff
from spec_check.models import Criterion, Evidence, Verdict
from spec_check.verify import build_result, check_evidence, match_file
from tests.conftest import DIFF

FILES = parse_diff(DIFF)


def check(file, snippet):
    return check_evidence(Evidence(file=file, snippet=snippet), FILES)


def test_exact_snippet_is_verified():
    assert check("app.py", "todos.pop(todo_id, None)").verified


def test_whitespace_and_diff_prefixes_are_normalized():
    snippet = (
        '+@app.delete("/todos/{todo_id}",   status_code=204)\n'
        "+def delete_todo(todo_id: int) -> None:"
    )
    result = check("b/app.py", snippet)
    assert result.verified, result.note


def test_multiline_snippet_spanning_context_and_added_lines():
    snippet = '    return todos[todo_id]\n\n\n@app.delete("/todos/{todo_id}", status_code=204)'
    assert check("app.py", snippet).verified


def test_fabricated_snippet_is_unverified():
    result = check(
        "app.py",
        'raise HTTPException(status_code=404, detail="Todo not found")\n    del todos[todo_id]',
    )
    assert not result.verified
    assert result.note == "snippet not found in this file's diff"


def test_snippet_from_wrong_file_is_unverified():
    # Real code, but cited against the test file.
    result = check("test_app.py", "todos.pop(todo_id, None)")
    assert not result.verified


def test_file_not_in_diff_is_unverified():
    result = check("routes/todos.py", "todos.pop(todo_id, None)")
    assert not result.verified
    assert result.note == "file is not part of the diff"


def test_snippet_matching_only_removed_lines_is_unverified():
    files = parse_diff("--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-limit = 10\n+limit = 20\n")
    result = check_evidence(Evidence(file="m.py", snippet="limit = 10"), files)
    assert not result.verified
    assert result.note == "snippet only matches removed lines"


def test_too_short_snippet_is_unverified():
    assert not check("app.py", " ) ").verified


def test_path_suffix_matching_is_unambiguous_only():
    assert match_file("sample/app.py", FILES).path == "app.py"
    files = parse_diff(
        "--- a/x/app.py\n+++ b/x/app.py\n@@ -1 +1 @@\n-a\n+b\n"
        "--- a/y/app.py\n+++ b/y/app.py\n@@ -1 +1 @@\n-a\n+b\n"
    )
    assert match_file("app.py", files) is None


def make_verdict(**overrides):
    data = dict(
        id="AC1", implemented="yes", tested="yes", evidence=[], confidence=0.9, reasoning="r"
    )
    data.update(overrides)
    return Verdict(**data)


CRITERION = Criterion(id="AC1", text="delete works")


def test_fully_verified_claim_needs_no_review():
    verdict = make_verdict(
        evidence=[
            Evidence(file="app.py", snippet="todos.pop(todo_id, None)"),
            Evidence(file="test_app.py", snippet="assert response.status_code == 204"),
        ]
    )
    result = build_result(CRITERION, verdict, FILES)
    assert result.review_reasons == []
    assert not result.has_gap


def test_claim_with_only_fabricated_evidence_needs_review():
    verdict = make_verdict(
        evidence=[
            Evidence(file="app.py", snippet="if todo_id not in todos: raise NotFound()"),
            Evidence(
                file="test_app.py", snippet="assert client.delete('/todos/7').status_code == 404"
            ),
        ]
    )
    result = build_result(CRITERION, verdict, FILES)
    assert result.needs_human_review
    assert "2 evidence snippet(s) failed verification" in result.review_reasons
    assert any("implemented=yes without verified" in r for r in result.review_reasons)
    assert any(
        "tested=yes without verified evidence from a test file" in r for r in result.review_reasons
    )


def test_tested_yes_needs_evidence_from_a_test_file():
    verdict = make_verdict(evidence=[Evidence(file="app.py", snippet="todos.pop(todo_id, None)")])
    result = build_result(CRITERION, verdict, FILES)
    assert result.review_reasons == ["claims tested=yes without verified evidence from a test file"]


def test_honest_no_without_evidence_needs_no_review():
    result = build_result(CRITERION, make_verdict(implemented="no", tested="no"), FILES)
    assert result.review_reasons == []
    assert result.has_gap


def test_low_confidence_and_contradiction_are_flagged():
    verdict = make_verdict(
        implemented="no",
        tested="yes",
        confidence=0.3,
        evidence=[
            Evidence(file="test_app.py", snippet="assert response.status_code == 204"),
        ],
    )
    reasons = build_result(CRITERION, verdict, FILES).review_reasons
    assert "contradiction: tested=yes but implemented=no" in reasons
    assert "low model confidence (0.30)" in reasons
