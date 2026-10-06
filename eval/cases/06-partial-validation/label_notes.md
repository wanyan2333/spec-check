# Label notes: 06-partial-validation

Scenario: a range check that only enforces one side.

## AC1: optional priority, defaults to 3, returned in the todo: implemented = yes, tested = yes

- Implemented: `priority: int = Field(default=3, le=5)` on `TodoIn`, `priority: int = 3` on
  `Todo`, and `Todo(id=_next_id, title=payload.title, priority=payload.priority)`.
- Tested: the updated `test_create_todo` asserts the default,
  `assert response.json() == {"id": 1, "title": "Buy milk", "done": False, "priority": 3}`, and
  `test_create_todo_with_priority` asserts `assert response.json()["priority"] == 1`.
- Mutation check: hard-coding `priority=3)` in `create_todo` makes `test_create_todo_with_priority` fail.

## AC2: priority outside 1 to 5 returns 422: implemented = partial, tested = yes

- Partially implemented: `Field(default=3, le=5)` rejects 6 and above, but there is no `ge=1`,
  so `priority: 0` and `priority: -3` are accepted with 201 (probes: 1 of 3 pass).
- Tested = yes for the implemented half: `test_create_todo_rejects_priority_above_5` posts
  `"priority": 6` and asserts `assert response.status_code == 422`. Removing `le=5` makes it fail.
  The missing lower bound is not tested either. That is why the criterion is a gap: the
  implementation is only partial.
- Labeling convention: `tested` refers to the behavior that exists. When an implemented part
  of a criterion would be caught by a test if it broke, `tested = yes`. A `partial` label
  already flags the missing part.
