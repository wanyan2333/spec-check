"""Hidden behavioral probes: ground truth for 'implemented'. Not part of the diff."""

import pytest
from fastapi.testclient import TestClient

from app import Todo, app, reset_store, todos

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_store():
    # The API has no way to mark a todo done, so seed the store directly.
    reset_store()
    todos[1] = Todo(id=1, title="a", done=True)
    todos[2] = Todo(id=2, title="b", done=False)
    todos[3] = Todo(id=3, title="c", done=False)
    yield
    reset_store()


def test_ac1_total_counts_all_todos():
    assert client.get("/todos/stats").json()["total"] == 3


def test_ac2_done_counts_only_done_todos():
    assert client.get("/todos/stats").json()["done"] == 1


def test_ac2_done_is_zero_when_nothing_is_done():
    todos[1] = Todo(id=1, title="a", done=False)
    assert client.get("/todos/stats").json()["done"] == 0
