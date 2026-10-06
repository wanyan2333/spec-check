import pytest
from fastapi.testclient import TestClient

from app import app, reset_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    reset_store()
    yield
    reset_store()


def test_create_todo():
    response = client.post("/todos", json={"title": "Buy milk"})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "title": "Buy milk", "done": False}


def test_list_todos():
    client.post("/todos", json={"title": "a"})
    client.post("/todos", json={"title": "b"})
    response = client.get("/todos")
    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["a", "b"]


def test_get_todo():
    client.post("/todos", json={"title": "Buy milk"})
    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Buy milk"


def test_get_missing_todo_returns_404():
    response = client.get("/todos/42")
    assert response.status_code == 404


def test_delete_todo():
    client.post("/todos", json={"title": "Buy milk"})
    response = client.delete("/todos/1")
    assert response.status_code == 204
    assert client.get("/todos/1").status_code == 404
