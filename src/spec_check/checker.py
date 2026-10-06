"""Orchestrates one check: prompt the LLM, validate its JSON, verify the evidence."""

import json
import logging

from pydantic import ValidationError

from spec_check.diff import parse_diff
from spec_check.llm import LLMClient, LLMResponse
from spec_check.models import CallStat, CheckReport, LLMOutput, Requirement, Verdict
from spec_check.prompts import DEFAULT_PROMPT_VERSION, build_messages, repair_message
from spec_check.verify import build_result

log = logging.getLogger(__name__)


class CheckError(RuntimeError):
    """The LLM did not produce a usable answer, even after one repair attempt."""


class OutputError(ValueError):
    """The LLM answer is not valid JSON or does not match the expected criteria."""


def parse_llm_output(text: str, expected_ids: list[str]) -> dict[str, Verdict]:
    text = text.strip()
    if text.startswith("```"):  # tolerate ```json fences
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutputError(f"invalid JSON ({exc})") from exc
    if isinstance(data, list):  # some models return the bare list
        data = {"criteria": data}
    try:
        output = LLMOutput.model_validate(data)
    except ValidationError as exc:
        raise OutputError(f"JSON does not match the schema: {exc}") from exc

    verdicts: dict[str, Verdict] = {}
    for verdict in output.criteria:
        if verdict.id in verdicts:
            raise OutputError(f"criterion {verdict.id} appears more than once")
        verdicts[verdict.id] = verdict
    missing = [i for i in expected_ids if i not in verdicts]
    unknown = [i for i in verdicts if i not in expected_ids]
    if missing or unknown:
        raise OutputError(
            f"missing criteria: {missing or 'none'}; unknown ids: {unknown or 'none'}"
        )
    return verdicts


def run_check(
    requirement: Requirement,
    diff_text: str,
    client: LLMClient,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> CheckReport:
    files = parse_diff(diff_text)
    if not files:
        raise CheckError("The diff contains no file changes.")
    expected_ids = [c.id for c in requirement.criteria]
    messages = build_messages(requirement, diff_text, prompt_version)
    calls: list[CallStat] = []

    def call(purpose: str) -> LLMResponse:
        response = client.complete(messages)
        calls.append(
            CallStat(
                purpose=purpose,
                model=response.model,
                latency_s=round(response.latency_s, 3),
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                retries=response.retries,
            )
        )
        return response

    response = call("initial")
    try:
        verdicts = parse_llm_output(response.text, expected_ids)
    except OutputError as first_error:
        log.warning("LLM output rejected (%s); asking it to repair once", first_error)
        messages.append({"role": "assistant", "content": response.text})
        messages.append(repair_message(str(first_error), expected_ids))
        response = call("repair")
        try:
            verdicts = parse_llm_output(response.text, expected_ids)
        except OutputError as second_error:
            raise CheckError(f"LLM output still invalid after retry: {second_error}") from None

    results = [build_result(c, verdicts[c.id], files) for c in requirement.criteria]
    return CheckReport(
        title=requirement.title,
        user_story=requirement.user_story,
        model=client.model,
        prompt_version=prompt_version,
        results=results,
        calls=calls,
    )
