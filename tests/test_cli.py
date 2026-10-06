import json

import httpx
import openai
import pytest

from spec_check.cli import EXIT_ERROR, EXIT_GAPS, EXIT_OK, main
from tests.conftest import GOOD_ANSWER, FakeLLM, as_json, verdict

VERIFIED_EVIDENCE = [
    {"file": "app.py", "snippet": "todos.pop(todo_id, None)"},
    {"file": "test_app.py", "snippet": "assert response.status_code == 204"},
]
ALL_GOOD = as_json(
    verdict("AC1", evidence=VERIFIED_EVIDENCE),
    verdict("AC2", evidence=VERIFIED_EVIDENCE),
)


def run(req_file, diff_file, answer, *extra):
    argv = ["--req", str(req_file), "--diff", str(diff_file), "--quiet", *extra]
    return main(argv, client_factory=lambda model: FakeLLM(answer))


def test_writes_markdown_and_json(req_file, diff_file, tmp_path):
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    code = run(req_file, diff_file, GOOD_ANSWER, "--out", str(out), "--json", str(js))
    assert code == EXIT_OK  # gaps alone do not fail without --fail-on-gaps
    assert "# Release evidence" in out.read_text(encoding="utf-8")
    assert json.loads(js.read_text(encoding="utf-8"))["summary"]["criteria"] == 2


def test_prints_report_to_stdout_without_out(req_file, diff_file, capsys):
    run(req_file, diff_file, GOOD_ANSWER)
    assert "# Release evidence: Delete a todo" in capsys.readouterr().out


def test_fail_on_gaps_returns_1_when_a_criterion_is_missing(req_file, diff_file):
    assert run(req_file, diff_file, GOOD_ANSWER, "--fail-on-gaps") == EXIT_GAPS


def test_fail_on_gaps_returns_0_when_all_good(req_file, diff_file):
    assert run(req_file, diff_file, ALL_GOOD, "--fail-on-gaps") == EXIT_OK


def test_fail_on_gaps_returns_1_for_unverified_evidence_alone(req_file, diff_file):
    # Both criteria claim yes/yes, but AC2 also cites code that is not in the diff.
    fabricated = {"file": "app.py", "snippet": "raise HTTPException(status_code=404)  # delete"}
    answer = as_json(
        verdict("AC1", evidence=VERIFIED_EVIDENCE),
        verdict("AC2", evidence=[*VERIFIED_EVIDENCE, fabricated]),
    )
    assert run(req_file, diff_file, answer, "--fail-on-gaps") == EXIT_GAPS


def test_missing_file_is_an_error(req_file, tmp_path, capsys):
    assert run(req_file, tmp_path / "nope.diff", GOOD_ANSWER) == EXIT_ERROR
    assert "error" in capsys.readouterr().err


def test_unusable_llm_output_is_an_error(req_file, diff_file):
    llm = FakeLLM("garbage", "still garbage")
    argv = ["--req", str(req_file), "--diff", str(diff_file), "--quiet"]
    assert main(argv, client_factory=lambda model: llm) == EXIT_ERROR


def test_api_failure_after_retries_is_a_clean_error(req_file, diff_file, capsys):
    # Seen for real: gemini-3.5-flash answered 503 "high demand" on every retry.
    class OverloadedLLM:
        model = "busy-model"

        def complete(self, messages):
            request = httpx.Request("POST", "https://example.test")
            raise openai.InternalServerError(
                "high demand", response=httpx.Response(503, request=request), body=None
            )

    argv = ["--req", str(req_file), "--diff", str(diff_file), "--quiet"]
    assert main(argv, client_factory=lambda model: OverloadedLLM()) == EXIT_ERROR
    assert "high demand" in capsys.readouterr().err


def test_missing_api_key_is_an_error(req_file, diff_file, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    argv = ["--req", str(req_file), "--diff", str(diff_file), "--quiet"]
    assert main(argv) == EXIT_ERROR


def test_unknown_prompt_version_is_rejected(req_file, diff_file):
    with pytest.raises(SystemExit):
        run(req_file, diff_file, GOOD_ANSWER, "--prompt", "v99")
