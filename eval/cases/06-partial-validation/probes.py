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


def test_ac1_default_priority_is_3():
    response = client.post("/todos", json={"title": "t"})
    assert response.status_code == 201
    assert response.json()["priority"] == 3


def test_ac1_explicit_priority_is_stored_and_returned():
    assert client.post("/todos", json={"title": "t", "priority": 5}).json()["priority"] == 5
    assert client.get("/todos/1").json()["priority"] == 5


def test_ac2_priority_above_5_rejected():
    assert client.post("/todos", json={"title": "t", "priority": 6}).status_code == 422


def test_ac2_priority_0_rejected():
    assert client.post("/todos", json={"title": "t", "priority": 0}).status_code == 422


def test_ac2_negative_priority_rejected():
    assert client.post("/todos", json={"title": "t", "priority": -3}).status_code == 422
