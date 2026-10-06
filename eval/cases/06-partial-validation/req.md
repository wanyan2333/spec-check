# Todo priority

## User story
As a user, I want to give each todo a priority from 1 (highest) to 5 (lowest) so that I can sort my work.

## Acceptance criteria
1. `POST /todos` accepts an optional integer `priority`; when it is omitted the priority defaults to 3. The priority is included in the returned todo.
2. A priority outside the range 1 to 5 (inclusive) is rejected with 422.
