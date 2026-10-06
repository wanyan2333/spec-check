# Label notes: 04-misleading-test

Scenario: the implementation is right, but one test is a copy-paste mistake. Its name promises
one thing and its body checks another.

## AC1: empty title returns 422: implemented = yes, tested = yes

- Implemented: `title: str = Field(min_length=1, max_length=100)`.
- Tested: `test_create_rejects_empty_title` posts `json={"title": ""}` and asserts
  `assert response.status_code == 422`. (The misleading test below also posts `""`.)
- Mutation check: dropping `min_length=1` makes both tests fail.

## AC2: title longer than 100 characters returns 422: implemented = yes, tested = no

- Implemented: `max_length=100` in the same `Field(...)`.
- Not tested: `test_create_rejects_too_long_title` builds `long_title = "x" * 101` but then
  sends `response = client.post("/todos", json={"title": ""})`. The variable is never used,
  so the test exercises the *empty* title again (AC1) and would pass even if there were no
  length limit.
- Mutation check: removing `max_length=100` leaves every app test passing.
- Trap for the model: the test name `test_create_rejects_too_long_title` and the
  `long_title` variable look like evidence. Only the request body counts.

## AC3: exactly 100 characters is accepted: implemented = yes, tested = no

- Implemented: `max_length=100` is inclusive in pydantic, so a 100-character title gets 201 (probe).
- Not tested: no test posts a 100-character title.
- Mutation check: changing it to `max_length=99` breaks the probe, and every app test still passes.
