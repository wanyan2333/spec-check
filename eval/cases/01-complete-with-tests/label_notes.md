# Label notes: 01-complete-with-tests

Scenario: a clean, complete change. This is the control case for false positives.

## AC1: PATCH updates `done` and returns the updated todo (200): implemented = yes, tested = yes

- Implemented: the new endpoint copies the stored todo with the new status and returns it:
  `updated = todos[todo_id].model_copy(update={"done": payload.done})` and `return updated`.
  Both `true` and `false` work because the value comes straight from `TodoUpdate.done: bool`.
- Tested: `test_mark_todo_done` asserts the full body
  `assert response.json() == {"id": 1, "title": "Buy milk", "done": True}` and
  `test_mark_todo_not_done_again` asserts `assert response.json()["done"] is False`.
- Mutation check: replacing `update={"done": payload.done}` with `update={}` makes both tests fail.

## AC2: PATCH on an unknown id returns 404: implemented = yes, tested = yes

- Implemented: `if todo_id not in todos:` / `raise HTTPException(status_code=404, detail="Todo not found")`
  inside `update_todo`.
- Tested: `test_update_missing_todo_returns_404` calls `client.patch("/todos/99", json={"done": True})`
  and asserts `assert response.status_code == 404`.
- Mutation check: deleting the guard makes the endpoint raise `KeyError`; the test fails.

## AC3: GET reflects the update: implemented = yes, tested = yes

- Implemented: `todos[todo_id] = updated` writes the new object back to the store.
- Tested: `test_update_is_visible_in_get` asserts `assert client.get("/todos/1").json()["done"] is True`.
- Mutation check: removing `todos[todo_id] = updated` still returns the right PATCH response
  (AC1 keeps passing) but this test fails, so the label is specific to AC3.
