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


def test_mark_todo_done():
    client.post("/todos", json={"title": "Buy milk"})
    response = client.patch("/todos/1", json={"done": True})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Buy milk", "done": True}


def test_mark_todo_not_done_again():
    client.post("/todos", json={"title": "Buy milk"})
    client.patch("/todos/1", json={"done": True})
    response = client.patch("/todos/1", json={"done": False})
    assert response.status_code == 200
    assert response.json()["done"] is False


def test_update_missing_todo_returns_404():
    response = client.patch("/todos/99", json={"done": True})
    assert response.status_code == 404


def test_update_is_visible_in_get():
    client.post("/todos", json={"title": "Buy milk"})
    client.patch("/todos/1", json={"done": True})
    assert client.get("/todos/1").json()["done"] is True
