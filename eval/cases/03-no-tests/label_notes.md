# Label notes: 03-no-tests

Scenario: a correct implementation that ships with no tests at all. The diff touches only `app.py`.

## AC1: `?done=true` returns only done todos: implemented = yes, tested = no

- Implemented: `def list_todos(done: bool | None = None)` and
  `if done is True:` / `return [t for t in todos.values() if t.done]`.
- Not tested: the diff contains no test file. The pre-existing `test_list_todos` calls
  `GET /todos` without the parameter, so it never runs this branch.
- Mutation check: replacing the filter with `list(todos.values())` breaks the probe, and every
  sample app test still passes.

## AC2: `?done=false` returns only open todos: implemented = yes, tested = no

- Implemented: `if done is False:` / `return [t for t in todos.values() if not t.done]`.
- Not tested: same reason as AC1.
- Mutation check: same result as AC1. The probe breaks and the app tests still pass.
