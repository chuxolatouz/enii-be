# tests/conftest.py
import pytest

from api.index import app
from pymongo import MongoClient

@pytest.fixture
def test_db():
    uri = app.config["MONGO_URI"]
    client = MongoClient(uri)
    db = client.get_default_database()
    yield db
    # Limpiar al final del test
    client.drop_database(db.name)

@pytest.fixture
def client():
    app.config.update({
        "TESTING": True,
    })
    return app.test_client()
