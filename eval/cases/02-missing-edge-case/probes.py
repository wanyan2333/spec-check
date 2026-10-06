"""Hidden behavioral probes: ground truth for 'implemented'. Not part of the diff."""

import pytest
from fastapi.testclient import TestClient

from app import app, reset_store

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def clean_store():
    reset_store()
    yield
    reset_store()


def test_ac1_delete_removes_todo_and_returns_204():
    client.post("/todos", json={"title": "t"})
    client.post("/todos", json={"title": "keep"})
    response = client.delete("/todos/1")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/todos/1").status_code == 404
    assert client.get("/todos/2").status_code == 200


def test_ac2_delete_unknown_id_returns_404():
    assert client.delete("/todos/123").status_code == 404


def test_ac2_delete_twice_returns_404_second_time():
    client.post("/todos", json={"title": "t"})
    client.delete("/todos/1")
    assert client.delete("/todos/1").status_code == 404
