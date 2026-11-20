import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT = Path(__file__).resolve().parents[2]
os.environ["MEDICAL_DB_PATH"] = str(PROJECT / "data" / "derived" / "test_medical_ops.db")
os.environ["MEDICAL_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"

from app.core.database import init_db
from app.main import app
from etl.jobs.pipeline import run_all


@pytest.fixture(scope="session", autouse=True)
def database():
    path = Path(os.environ["MEDICAL_DB_PATH"])
    path.unlink(missing_ok=True)
    init_db()
    run_all()
    yield
    path.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def token(client, username="admin", password="admin123"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["token"]


@pytest.fixture(scope="session")
def admin_headers(client):
    return {"Authorization": "Bearer "+token(client)}


@pytest.fixture(scope="session")
def dept_headers(client):
    return {"Authorization": "Bearer "+token(client, "dept_hn", "dept123")}
