# Label notes: 02-missing-edge-case

Scenario: the happy path works and is tested, but the error case was forgotten.

## AC1: DELETE removes the todo, returns 204, then GET returns 404: implemented = yes, tested = yes

- Implemented: `@app.delete("/todos/{todo_id}", status_code=204)` and `todos.pop(todo_id, None)`.
- Tested: `test_delete_todo` asserts `assert response.status_code == 204` and
  `assert client.get("/todos/1").status_code == 404`.
- Mutation check: replacing `todos.pop(todo_id, None)` with `pass` still returns 204, but the
  follow-up GET returns 200, so the test fails.

## AC2: DELETE on an unknown id returns 404: implemented = no, tested = no

- Not implemented: `todos.pop(todo_id, None)` silently ignores missing keys and the decorator
  always answers `status_code=204`. There is no `HTTPException(status_code=404 ...)` in
  `delete_todo`. The probe `client.delete("/todos/123")` gets 204.
- Not tested: no test in the diff calls DELETE with an unknown id.
- Trap for the model: the diff context shows `raise HTTPException(status_code=404, detail="Todo not found")`
  from the pre-existing `get_todo`; citing it as evidence for AC2 would be wrong.
