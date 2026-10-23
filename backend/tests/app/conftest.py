import os

import pytest
from fastapi.testclient import TestClient

from app import db as app_db
from app.main import create_app


@pytest.fixture
def anon_client(db):
    app = create_app()
    app.dependency_overrides[app_db.get_session] = lambda: db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(anon_client):
    r = anon_client.post("/api/auth/login", json={"password": os.environ["UI_PASSWORD"]})
    assert r.status_code == 204, r.text
    return anon_client
