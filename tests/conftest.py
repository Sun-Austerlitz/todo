
import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app
from main import app

@pytest.fixture(scope="session")
def client():
    """Provide a TestClient for the app."""
    with TestClient(app) as c:
        yield c
