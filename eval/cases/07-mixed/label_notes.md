# Label notes: 07-mixed

Scenario: three criteria with three different states: tested, untested, and missing.

## AC1: `limit=N` returns at most N todos: implemented = yes, tested = yes

- Implemented: `def list_todos(limit: int = 50, offset: int = 0)` and
  `return items[offset : offset + limit]`.
- Tested: `test_list_todos_with_limit` creates 3 todos, calls `params={"limit": 2}` and asserts
  `assert [t["title"] for t in response.json()] == ["a", "b"]`.
- Mutation check: changing the slice to `items[offset:]` makes the test fail.

## AC2: `offset=M` skips the first M todos: implemented = yes, tested = no

- Implemented: the same slice, `items[offset : offset + limit]`.
- Not tested: no test passes `offset`. The only new test uses `offset`'s default of 0.
- Mutation check: changing the slice to `items[:limit]` (ignoring offset) breaks the offset
  probes, and every app test still passes.

## AC3: `limit` > 100 returns 422: implemented = no, tested = no

- Not implemented: `limit: int = 50` has no upper bound. There is no `Query(le=100)` and no
  manual check. `GET /todos?limit=101` returns 200 (probe fails).
- Not tested: no test uses a limit above 100.
