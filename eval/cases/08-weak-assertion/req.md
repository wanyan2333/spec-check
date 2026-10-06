# Todo statistics

## User story
As a user, I want to see how many todos I have and how many are done so that I can see my progress at a glance.

## Acceptance criteria
1. `GET /todos/stats` returns a `total` field equal to the number of todos.
2. `GET /todos/stats` returns a `done` field equal to the number of todos that are done.
