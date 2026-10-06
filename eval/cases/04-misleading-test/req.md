# Validate todo titles

## User story
As a product owner, I want todo titles to be validated so that the list never contains blank or absurdly long entries.

## Acceptance criteria
1. `POST /todos` with an empty title returns 422.
2. `POST /todos` with a title longer than 100 characters returns 422.
3. A title of exactly 100 characters is accepted (201).
