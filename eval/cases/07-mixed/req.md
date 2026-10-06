# Paginate the todo list

## User story
As a user with a long list, I want `GET /todos` to be paginated so that the app stays fast.

## Acceptance criteria
1. `GET /todos?limit=N` returns at most N todos.
2. `GET /todos?offset=M` skips the first M todos.
3. A `limit` greater than 100 is rejected with 422.
