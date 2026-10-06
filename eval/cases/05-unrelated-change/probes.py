"""Hidden behavioral probes: ground truth for 'implemented'. Not part of the diff."""

import pytest
from fastapi.testclient import TestClient

from app import app, reset_store

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_store():
    reset_store()
    for title in ["Buy milk", "Call mom", "buy stamps"]:
        client.post("/todos", json={"title": title})
    yield
    reset_store()


def test_ac1_search_is_case_insensitive_substring():
    response = client.get("/todos", params={"q": "BUY"})
    assert [t["title"] for t in response.json()] == ["Buy milk", "buy stamps"]


def test_ac2_no_match_returns_empty_list():
    response = client.get("/todos", params={"q": "zebra"})
    assert response.status_code == 200
    assert response.json() == []
