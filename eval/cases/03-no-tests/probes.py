"""Hidden behavioral probes: ground truth for 'implemented'. Not part of the diff."""

import pytest
from fastapi.testclient import TestClient

from app import Todo, app, reset_store, todos

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_store():
    # The API has no way to mark a todo done yet, so seed the store directly.
    reset_store()
    todos[1] = Todo(id=1, title="open one", done=False)
    todos[2] = Todo(id=2, title="finished", done=True)
    todos[3] = Todo(id=3, title="open two", done=False)
    yield
    reset_store()


def titles(response):
    return [t["title"] for t in response.json()]


def test_ac1_done_true_returns_only_done():
    assert titles(client.get("/todos", params={"done": "true"})) == ["finished"]


def test_ac2_done_false_returns_only_open():
    assert titles(client.get("/todos", params={"done": "false"})) == ["open one", "open two"]
