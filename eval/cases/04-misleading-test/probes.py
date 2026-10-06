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


def test_ac1_empty_title_rejected():
    assert client.post("/todos", json={"title": ""}).status_code == 422


def test_ac2_101_char_title_rejected():
    assert client.post("/todos", json={"title": "x" * 101}).status_code == 422


def test_ac2_very_long_title_rejected():
    assert client.post("/todos", json={"title": "x" * 500}).status_code == 422


def test_ac3_100_char_title_accepted():
    assert client.post("/todos", json={"title": "x" * 100}).status_code == 201
