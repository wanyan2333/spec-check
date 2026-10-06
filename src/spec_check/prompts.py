"""Prompt templates. Old versions are kept so evaluation results stay comparable."""

from spec_check.models import Requirement

PROMPT_V1_SYSTEM = """\
You are a release verification assistant. You receive a requirement (a user story with \
numbered acceptance criteria) and a code change as a unified git diff. For each acceptance \
criterion decide whether the change implements it and whether the change tests it.

Return a JSON object with this exact shape:
{
  "criteria": [
    {
      "id": "AC1",
      "implemented": "yes" | "partial" | "no",
      "tested": "yes" | "no",
      "evidence": [{"file": "<path from the diff>", "snippet": "<code copied from the diff>"}],
      "confidence": <number between 0 and 1>,
      "reasoning": "<one or two sentences>"
    }
  ]
}

Rules:
- Include every acceptance criterion exactly once, using its id.
- tested is "yes" only if a test in the diff actually executes the behavior and asserts it. \
A test name is not evidence.
- Evidence snippets must be copied verbatim from the diff. Do not invent code.
- Output JSON only.
"""

PROMPTS: dict[str, str] = {
    "v1": PROMPT_V1_SYSTEM,
}
DEFAULT_PROMPT_VERSION = "v1"


def build_messages(requirement: Requirement, diff_text: str, version: str) -> list[dict]:
    if version not in PROMPTS:
        raise ValueError(f"Unknown prompt version {version!r}; choose from {sorted(PROMPTS)}")
    criteria = "\n".join(f"- {c.id}: {c.text}" for c in requirement.criteria)
    user = (
        f"# Requirement: {requirement.title}\n\n"
        f"User story: {requirement.user_story}\n\n"
        f"Acceptance criteria:\n{criteria}\n\n"
        f"# Code change (git diff)\n\n```diff\n{diff_text}\n```"
    )
    return [
        {"role": "system", "content": PROMPTS[version]},
        {"role": "user", "content": user},
    ]


def repair_message(error: str, expected_ids: list[str]) -> dict:
    return {
        "role": "user",
        "content": (
            "Your previous answer could not be used: "
            f"{error}\n\nReturn the complete JSON object again, with exactly one entry for "
            f"each of these ids: {', '.join(expected_ids)}. Output JSON only."
        ),
    }
