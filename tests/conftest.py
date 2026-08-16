import threading
import time
import pytest
import uvicorn
from app import app

TEST_PORT = 8009
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="session", autouse=True)
def run_test_server():
    """Run test server on TEST_PORT for all integration tests."""
    config = uvicorn.Config(app, host="127.0.0.1", port=TEST_PORT, log_level="warning", loop="asyncio")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.8)
    yield
    server.should_exit = True
    thread.join(timeout=2)
