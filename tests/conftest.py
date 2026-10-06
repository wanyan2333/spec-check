import json

import pytest

from spec_check.llm import LLMResponse

REQ_MD = """\
# Delete a todo

## User story
As a user, I want to delete a todo so that my list stays clean.

## Acceptance criteria
1. DELETE /todos/{id} removes the todo and returns 204.
2. DELETE on an unknown id returns 404.
"""

DIFF = """\
diff --git a/app.py b/app.py
index 1111111..2222222 100644
--- a/app.py
+++ b/app.py
@@ -10,3 +10,8 @@ def get_todo(todo_id: int) -> Todo:
     if todo_id not in todos:
         raise HTTPException(status_code=404, detail="Todo not found")
     return todos[todo_id]
+
+
+@app.delete("/todos/{todo_id}", status_code=204)
+def delete_todo(todo_id: int) -> None:
+    todos.pop(todo_id, None)
diff --git a/test_app.py b/test_app.py
index 3333333..4444444 100644
--- a/test_app.py
+++ b/test_app.py
@@ -5,2 +5,7 @@ def test_get_missing():
     response = client.get("/todos/99")
     assert response.status_code == 404
+
+
+def test_delete_todo():
+    response = client.delete("/todos/1")
+    assert response.status_code == 204
"""


def verdict(ac_id, implemented="yes", tested="yes", evidence=None, confidence=0.9):
    return {
        "id": ac_id,
        "implemented": implemented,
        "tested": tested,
        "evidence": evidence or [],
        "confidence": confidence,
        "reasoning": "because",
    }


def as_json(*verdicts) -> str:
    return json.dumps({"criteria": list(verdicts)})


class FakeLLM:
    """Returns scripted responses in order and records the messages it was sent."""

    model = "fake-model"

    def __init__(self, *texts: str):
        self.texts = list(texts)
        self.calls: list[list[dict]] = []

    def complete(self, messages):
        self.calls.append([dict(m) for m in messages])
        return LLMResponse(
            text=self.texts.pop(0),
            model=self.model,
            latency_s=0.5,
            prompt_tokens=100,
            completion_tokens=20,
        )


GOOD_ANSWER = as_json(
    verdict(
        "AC1",
        evidence=[
            {"file": "app.py", "snippet": '@app.delete("/todos/{todo_id}", status_code=204)'},
            {"file": "test_app.py", "snippet": "assert response.status_code == 204"},
        ],
    ),
    verdict(
        "AC2",
        implemented="no",
        tested="no",
        evidence=[{"file": "app.py", "snippet": "todos.pop(todo_id, None)"}],
    ),
)


@pytest.fixture
def req_file(tmp_path):
    path = tmp_path / "req.md"
    path.write_text(REQ_MD, encoding="utf-8")
    return path


@pytest.fixture
def diff_file(tmp_path):
    path = tmp_path / "change.diff"
    path.write_text(DIFF, encoding="utf-8")
    return path
