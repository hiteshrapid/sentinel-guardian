"""
Integration test fixtures for FastAPI + Beanie/MongoDB stack.
Template by Sentinel — adapt document_models for your app.

Built by Hitesh Goyal & Sentinel
"""

import os
from collections.abc import AsyncGenerator

import pymongo
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

# ---------------------------------------------------------------------------
# Constants — customize per project
# ---------------------------------------------------------------------------
TEST_AUTH_KEY = os.environ.get("SERVER_AUTH_KEY", "test-server-auth-key")
TEST_DB_NAME = "test_db_integration"

AUTH_HEADERS = {
    "X-Server-Auth-Key": TEST_AUTH_KEY,
    "Content-Type": "application/json",
}

# ---------------------------------------------------------------------------
# Set env vars before any app imports
# ---------------------------------------------------------------------------
os.environ.setdefault("SERVER_AUTH_KEY", TEST_AUTH_KEY)
os.environ.setdefault("MONGODB_DATABASE", TEST_DB_NAME)
os.environ.setdefault("ENVIRONMENT", "testing")


def _get_mongodb_uri() -> str:
    """Get MongoDB URI: env var (CI) → Testcontainers → mongomock → localhost."""
    uri = os.environ.get("MONGODB_URI", "")
    if uri:
        return uri
    try:
        from testcontainers.mongodb import MongoDbContainer
        container = MongoDbContainer("mongo:7")
        container.start()
        uri = container.get_connection_url()
        os.environ["MONGODB_URI"] = uri
        return uri
    except Exception:
        pass
    try:
        import mongomock_motor  # noqa: F401
        return "mongomock://localhost"
    except ImportError:
        return "mongodb://localhost:27017"


def _mongodb_is_reachable(uri: str) -> bool:
    if "mongomock" in uri:
        return True
    try:
        c = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
        c.admin.command("ping")
        c.close()
        return True
    except Exception:
        return False


_mongo_uri = _get_mongodb_uri()
os.environ["MONGODB_URI"] = _mongo_uri
_mongo_available = _mongodb_is_reachable(_mongo_uri)

requires_mongodb = pytest.mark.skipif(
    not _mongo_available,
    reason=f"MongoDB not reachable at {_mongo_uri}",
)


@pytest_asyncio.fixture
async def mongo_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    if "mongomock" in _mongo_uri:
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
    else:
        client = AsyncIOMotorClient(_mongo_uri)
    yield client
    client.close()


@pytest_asyncio.fixture
async def _init_beanie(mongo_client):
    """Initialize Beanie — ADD YOUR DOCUMENT MODELS HERE."""
    db = mongo_client[TEST_DB_NAME]

    await init_beanie(
        database=db,
        document_models=[
            # Add your Beanie Document classes here:
            # User, Campaign, Customer, etc.
        ],
    )
    yield db

    for name in await db.list_collection_names():
        await db[name].delete_many({})


@pytest_asyncio.fixture
async def client(_init_beanie) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient against the FastAPI app."""
    from app.main import app  # <-- adjust import path

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac
