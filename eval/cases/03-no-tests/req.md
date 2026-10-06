# Filter todos by status

## User story
As a user, I want to list only my completed or only my open todos so that I can focus.

## Acceptance criteria
1. `GET /todos?done=true` returns only the todos that are done.
2. `GET /todos?done=false` returns only the todos that are not done.
