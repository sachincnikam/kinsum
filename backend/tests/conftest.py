import os
import tempfile

import pytest

# Tests never touch the real data folder.
os.environ.setdefault("KINSUM_DATA_DIR", tempfile.mkdtemp(prefix="kinsum-test-"))
os.environ.setdefault("ANTHROPIC_API_KEY", "")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402

PASSCODE = "correct-horse-42"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def app(tmp_path, clock):
    """A fresh app with its own empty data folder and a clock the test controls."""
    app = create_app(data_dir=tmp_path, idle_lock_minutes=10)
    app.state.lock.clock = clock
    yield app
    app.state.lock.lock()  # close the database so Windows can delete the temp folder


@pytest.fixture
def client(app):
    return TestClient(app, base_url="http://localhost")


@pytest.fixture
def unlocked(client):
    """A client that has finished first-run setup and holds a session cookie."""
    assert client.post("/api/lock/setup", json={"name": "Alex", "passcode": PASSCODE}).status_code == 201
    return client
