import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AI_MODE"] = "demo"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def plants(client):
    return client.get("/api/plants").json()


def by_name(plants, name):
    return next(p for p in plants if p["plant"]["name"] == name)
