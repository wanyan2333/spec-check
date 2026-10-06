"""Hidden behavioral probes: ground truth for 'implemented'. Not part of the diff."""

import pytest
from fastapi.testclient import TestClient

from app import app, reset_store

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_store():
    reset_store()
    for title in ["a", "b", "c", "d", "e"]:
        client.post("/todos", json={"title": title})
    yield
    reset_store()


def titles(response):
    return [t["title"] for t in response.json()]


def test_ac1_limit_caps_the_result():
    assert titles(client.get("/todos", params={"limit": 3})) == ["a", "b", "c"]


def test_ac2_offset_skips_items():
    assert titles(client.get("/todos", params={"offset": 2})) == ["c", "d", "e"]


def test_ac2_offset_with_limit():
    assert titles(client.get("/todos", params={"offset": 1, "limit": 2})) == ["b", "c"]


def test_ac3_limit_above_100_rejected():
    assert client.get("/todos", params={"limit": 101}).status_code == 422
