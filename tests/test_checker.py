import json

import pytest

from spec_check.checker import CheckError, OutputError, parse_llm_output, run_check
from spec_check.requirements import parse_requirement
from tests.conftest import DIFF, GOOD_ANSWER, REQ_MD, FakeLLM, as_json, verdict

REQ = parse_requirement(REQ_MD)
IDS = ["AC1", "AC2"]


def test_valid_answer_produces_report_in_one_call():
    llm = FakeLLM(GOOD_ANSWER)
    report = run_check(REQ, DIFF, llm, prompt_version="v1")
    assert len(llm.calls) == 1
    assert [r.id for r in report.results] == IDS
    assert report.results[0].implemented == "yes"
    assert report.results[1].implemented == "no"
    assert report.unverified_snippets == 0
    assert report.total_tokens == 120
    assert report.calls[0].purpose == "initial"


def test_prompt_contains_criteria_and_diff():
    llm = FakeLLM(GOOD_ANSWER)
    run_check(REQ, DIFF, llm, prompt_version="v1")
    user_prompt = llm.calls[0][-1]["content"]
    assert "AC2: DELETE on an unknown id returns 404." in user_prompt
    assert "todos.pop(todo_id, None)" in user_prompt


def test_invalid_json_is_retried_once_with_the_error():
    llm = FakeLLM("Sure! Here is the analysis: {not json", GOOD_ANSWER)
    report = run_check(REQ, DIFF, llm, prompt_version="v1")
    assert len(llm.calls) == 2
    repair_prompt = llm.calls[1][-1]["content"]
    assert "invalid JSON" in repair_prompt
    assert llm.calls[1][-2] == {
        "role": "assistant",
        "content": "Sure! Here is the analysis: {not json",
    }
    assert [c.purpose for c in report.calls] == ["initial", "repair"]


def test_missing_criterion_is_retried_with_the_missing_id():
    llm = FakeLLM(as_json(verdict("AC1")), GOOD_ANSWER)
    run_check(REQ, DIFF, llm, prompt_version="v1")
    assert "missing criteria: ['AC2']" in llm.calls[1][-1]["content"]


def test_second_invalid_answer_raises():
    llm = FakeLLM("nope", as_json(verdict("AC1")))
    with pytest.raises(CheckError, match="still invalid after retry"):
        run_check(REQ, DIFF, llm, prompt_version="v1")


def test_parse_accepts_fences_bare_list_and_loose_values():
    text = "```json\n" + json.dumps([verdict("1", implemented="Yes")]) + "\n```"
    verdicts = parse_llm_output(text, ["AC1"])
    assert verdicts["AC1"].implemented == "yes"


@pytest.mark.parametrize(
    "text, message",
    [
        (as_json(verdict("AC1", implemented="maybe"), verdict("AC2")), "schema"),
        (as_json(verdict("AC1", confidence=1.7), verdict("AC2")), "schema"),
        (as_json(verdict("AC1"), verdict("AC1"), verdict("AC2")), "more than once"),
        (as_json(verdict("AC1"), verdict("AC2"), verdict("AC3")), "unknown ids: ['AC3']"),
    ],
)
def test_parse_rejects_bad_answers(text, message):
    with pytest.raises(OutputError, match=message.replace("[", r"\[").replace("]", r"\]")):
        parse_llm_output(text, IDS)


def test_empty_diff_is_an_error():
    with pytest.raises(CheckError, match="no file changes"):
        run_check(REQ, "", FakeLLM(GOOD_ANSWER))
