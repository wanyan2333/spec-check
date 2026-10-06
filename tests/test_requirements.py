import pytest

from spec_check.requirements import RequirementError, parse_requirement
from tests.conftest import REQ_MD


def test_parses_title_story_and_criteria():
    req = parse_requirement(REQ_MD)
    assert req.title == "Delete a todo"
    assert req.user_story.startswith("As a user, I want to delete a todo")
    assert [c.id for c in req.criteria] == ["AC1", "AC2"]
    assert req.criteria[1].text == "DELETE on an unknown id returns 404."


def test_joins_continuation_lines_and_accepts_ac_prefix():
    text = "# T\n\n## Acceptance Criteria\nAC1: first line\n   continues here\nAC2) second\n"
    req = parse_requirement(text)
    assert [(c.id, c.text) for c in req.criteria] == [
        ("AC1", "first line continues here"),
        ("AC2", "second"),
    ]


def test_falls_back_to_numbered_items_without_section():
    req = parse_requirement("# T\n\n1. only item\n")
    assert [c.text for c in req.criteria] == ["only item"]


def test_ignores_numbered_items_outside_criteria_section():
    text = "# T\n\n## Notes\n1. not a criterion\n\n## Acceptance criteria\n1. real one\n"
    assert [c.text for c in parse_requirement(text).criteria] == ["real one"]


def test_no_criteria_is_an_error():
    with pytest.raises(RequirementError):
        parse_requirement("# Title\n\nJust prose, no list.\n")


def test_duplicate_numbers_are_an_error():
    with pytest.raises(RequirementError):
        parse_requirement("# T\n## Acceptance criteria\n1. a\n1. b\n")
