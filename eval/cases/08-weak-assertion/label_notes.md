# Label notes: 08-weak-assertion

Scenario: the test checks that a field exists but never checks its value, so a wrong value passes.

## AC1: `total` equals the number of todos: implemented = yes, tested = yes

- Implemented: `total = len(todos)`, returned as `{"total": total, "done": done}`. The route is
  registered before `/todos/{todo_id}`, so `/todos/stats` is not parsed as an id.
- Tested: `test_stats` creates two todos and asserts `assert body["total"] == 2`.
- Mutation check: `total = 0` makes the test fail.

## AC2: `done` equals the number of done todos: implemented = no, tested = no

- Not implemented (the value is wrong): `done = sum(1 for t in todos.values() if t.done is not None)`.
  `t.done` is a `bool` and never `None`, so this counts every todo. With 1 done and 2 open
  todos the endpoint returns `done: 3`. Both probes fail, including "0 done gives 0", so the
  field exists but the behavior the criterion describes does not.
- Not tested: `test_stats` only asserts `assert "done" in body`. That holds for any value,
  which is why the bug passes. It also creates only open todos, so even an equality check on
  `total` would not have covered `done`.
- Trap for the model: the key `"done"` is returned and the test mentions it, so a surface
  reading suggests both implemented and tested.
