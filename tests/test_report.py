from spec_check.checker import run_check
from spec_check.report import overall_verdict, render_markdown
from spec_check.requirements import parse_requirement
from tests.conftest import DIFF, GOOD_ANSWER, REQ_MD, FakeLLM, as_json, verdict

REQ = parse_requirement(REQ_MD)


def make_report(answer=GOOD_ANSWER):
    return run_check(REQ, DIFF, FakeLLM(answer), prompt_version="v1")


def test_report_has_summary_details_and_calls():
    md = render_markdown(make_report())
    assert md.startswith("# Release evidence: Delete a todo")
    assert "GAPS FOUND in 1 of 2 criteria" in md
    assert "| AC1 | DELETE /todos/{id} removes the todo and returns 204. | yes | yes | 0.90 |" in md
    assert "### AC2: DELETE on an unknown id returns 404." in md
    assert "`test_app.py` (test) — ✅ verified" in md
    assert "evidence snippets verified: 3/3 (**0 UNVERIFIED**)" in md
    assert "## Model calls" in md
    assert "| 1 | initial | 0.50 | 100 | 20 | 0 |" in md


def test_unverified_evidence_is_called_out():
    answer = as_json(
        verdict(
            "AC1",
            evidence=[
                {"file": "app.py", "snippet": "todos.pop(todo_id, None)"},
                {"file": "test_app.py", "snippet": "assert client.delete('/todos/1').ok"},
            ],
        ),
        verdict("AC2", implemented="no", tested="no"),
    )
    md = render_markdown(make_report(answer))
    assert "❌ **UNVERIFIED** (snippet not found in this file's diff)" in md
    assert "⚠️ **Needs human review:**" in md
    assert "(**1 UNVERIFIED**)" in md
    assert "1 criteria need human review" in md


def test_ready_verdict_when_everything_is_verified():
    evidence = [
        {"file": "app.py", "snippet": "todos.pop(todo_id, None)"},
        {"file": "test_app.py", "snippet": "assert response.status_code == 204"},
    ]
    report = make_report(
        as_json(verdict("AC1", evidence=evidence), verdict("AC2", evidence=evidence))
    )
    assert overall_verdict(report).startswith("✅ READY")
    assert not report.has_gaps()


def test_pipes_in_criteria_are_escaped():
    req = parse_requirement("# T\n## Acceptance criteria\n1. returns a | b\n")
    report = run_check(req, DIFF, FakeLLM(as_json(verdict("AC1", "no", "no"))))
    assert "returns a \\| b" in render_markdown(report)


def test_json_dict_has_summary():
    data = make_report().to_json_dict()
    assert data["summary"]["gaps"] == 1
    assert data["summary"]["unverified_snippets"] == 0
    assert data["results"][0]["needs_human_review"] is False
