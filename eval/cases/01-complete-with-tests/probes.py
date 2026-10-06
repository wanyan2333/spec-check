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


def test_ac1_patch_sets_done_true():
    client.post("/todos", json={"title": "t"})
    response = client.patch("/todos/1", json={"done": True})
    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "t", "done": True}


def test_ac1_patch_sets_done_false():
    client.post("/todos", json={"title": "t"})
    client.patch("/todos/1", json={"done": True})
    response = client.patch("/todos/1", json={"done": False})
    assert response.status_code == 200
    assert response.json()["done"] is False


def test_ac2_patch_unknown_id_returns_404():
    assert client.patch("/todos/123", json={"done": True}).status_code == 404


def test_ac3_get_reflects_update():
    client.post("/todos", json={"title": "t"})
    client.patch("/todos/1", json={"done": True})
    assert client.get("/todos/1").json()["done"] is True
