# Label notes: 05-unrelated-change

Scenario: the change has nothing to do with the requirement. Someone linked the wrong PR.

## AC1: `GET /todos?q=<text>` filters by title, case-insensitive: implemented = no, tested = no

- Not implemented: the only production change is a new endpoint
  `@app.get("/health")` / `return {"status": "ok"}`. `list_todos()` is untouched and takes
  no `q` parameter, so `GET /todos?q=BUY` returns every todo (probe fails).
- Not tested: the only new test is `test_health`, which asserts
  `assert response.json() == {"status": "ok"}`.

## AC2: a search with no match returns 200 and `[]`: implemented = no, tested = no

- Not implemented: `q` is ignored, so with todos in the store `GET /todos?q=zebra` returns all
  of them instead of `[]` (probe fails).
- Not tested: as above.
- Trap for the model: the diff context includes `def list_todos() -> list[Todo]:` /
  `return list(todos.values())`, which a careless reader might take as a search implementation.
