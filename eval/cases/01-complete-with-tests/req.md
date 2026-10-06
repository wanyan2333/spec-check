# Mark a todo as done

## User story
As a user, I want to mark a todo as done (or not done again) so that I can track my progress.

## Acceptance criteria
1. `PATCH /todos/{id}` with a JSON body `{"done": true}` or `{"done": false}` updates the todo's done status and returns the updated todo with status 200.
2. `PATCH /todos/{id}` for an id that does not exist returns 404.
3. After a successful update, `GET /todos/{id}` returns the new done status.
