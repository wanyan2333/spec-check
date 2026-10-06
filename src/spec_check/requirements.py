"""Parse a Markdown requirement: title, user story and numbered acceptance criteria.

Expected shape (headings are matched case-insensitively):

    # Delete a todo

    ## User story
    As a user, I want to ...

    ## Acceptance criteria
    1. DELETE /todos/{id} removes the todo ...
    2. ... (continuation lines are joined to the previous item)
"""

import re

from spec_check.models import Criterion, Requirement

_NUMBERED_ITEM = re.compile(r"^\s*(?:AC[-\s]?)?(\d+)[.):]\s+(.*)$", re.IGNORECASE)
_HEADING = re.compile(r"^(#+)\s+(.*)$")


class RequirementError(ValueError):
    pass


def parse_requirement(text: str) -> Requirement:
    title = ""
    sections: dict[str, list[str]] = {}
    current = "_preamble"
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            name = heading.group(2).strip()
            if len(heading.group(1)) == 1 and not title:
                title = name
                current = "_preamble"
            else:
                current = name.lower()
            continue
        sections.setdefault(current, []).append(line)

    story_lines = _find_section(sections, "user story") or sections.get("_preamble", [])
    user_story = " ".join(line.strip() for line in story_lines if line.strip())

    criteria_lines = _find_section(sections, "acceptance criteria")
    if criteria_lines is None:
        # No explicit section: fall back to every numbered item in the document.
        criteria_lines = [line for lines in sections.values() for line in lines]
    criteria = _parse_numbered_items(criteria_lines)
    if not criteria:
        raise RequirementError("No numbered acceptance criteria found in the requirement.")

    return Requirement(
        title=title or "Untitled requirement", user_story=user_story, criteria=criteria
    )


def _find_section(sections: dict[str, list[str]], keyword: str) -> list[str] | None:
    for name, lines in sections.items():
        if keyword in name:
            return lines
    return None


def _parse_numbered_items(lines: list[str]) -> list[Criterion]:
    items: list[list[str]] = []
    numbers: list[str] = []
    for line in lines:
        match = _NUMBERED_ITEM.match(line)
        if match:
            numbers.append(match.group(1))
            items.append([match.group(2).strip()])
        elif items and line.strip():
            items[-1].append(line.strip())  # continuation of the previous item

    if len(set(numbers)) != len(numbers):
        raise RequirementError(f"Duplicate acceptance criterion numbers: {numbers}")
    return [
        Criterion(id=f"AC{number}", text=" ".join(parts))
        for number, parts in zip(numbers, items, strict=True)
    ]
