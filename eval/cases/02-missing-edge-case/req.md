# Delete a todo

## User story
As a user, I want to delete a todo I no longer need so that my list stays short.

## Acceptance criteria
1. `DELETE /todos/{id}` removes the todo and returns status 204; afterwards `GET /todos/{id}` returns 404.
2. `DELETE /todos/{id}` for an id that does not exist returns 404.
