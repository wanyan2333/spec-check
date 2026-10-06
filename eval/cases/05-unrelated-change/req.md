# Search todos by title

## User story
As a user with many todos, I want to search them by a word in the title so that I can find one quickly.

## Acceptance criteria
1. `GET /todos?q=<text>` returns only the todos whose title contains `<text>`, ignoring case.
2. A search that matches nothing returns status 200 and an empty list.
