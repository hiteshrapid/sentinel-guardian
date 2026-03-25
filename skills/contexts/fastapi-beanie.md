# FastAPI + Beanie/MongoDB Context

> Stack-specific patterns for testing FastAPI applications using Beanie ODM with MongoDB.
> Load this context when the target repo uses `from fastapi` + `beanie` or `motor`.

## Stack Summary

- **Framework:** FastAPI (async, Starlette-based)
- **ORM:** Beanie ODM (async MongoDB ODM built on Motor)
- **Database:** MongoDB
- **Package Manager:** uv (pyproject.toml + uv.lock)
- **Test Runner:** pytest + pytest-asyncio
- **Auth Pattern:** X-Server-Auth-Key header (server-to-server API key)
- **User Identity:** user_id query parameter (no role-based auth)
- **App Entry:** `from app.main import app` (no create_app() factory)

## Key Differences from Generic Defaults

| Generic Default | This Stack |
|---|---|
| SQLAlchemy + Postgres | Beanie ODM + MongoDB |
| Testcontainers(Postgres) | mongomock-motor (unit) / Testcontainers(MongoDB) (integration) |
| Alembic migrations | None (Beanie schema on write) |
| JWT Bearer tokens | X-Server-Auth-Key header |
| pip install | uv sync |
| requirements.txt | pyproject.toml + uv.lock |
| create_app() factory | `from app.main import app` |
| User roles (admin/user) | user_id query param (no role-based auth) |

## Install Dependencies

```bash
uv add --dev \
  pytest pytest-asyncio pytest-cov pytest-xdist pytest-mock \
  httpx testcontainers mongomock-motor \
  openapi-spec-validator jsonschema pyyaml \
  pip-audit safety \
  factory-boy faker \
  ruff mypy
```

## Auth in Tests

```python
# Server-to-server auth via header
AUTH_HEADERS = {
    "X-Server-Auth-Key": "test-server-auth-key",
    "Content-Type": "application/json",
}
TEST_USER_ID = "test-user-001"

# Usage in requests:
res = await client.get(
    "/api/v1/campaigns",
    headers=AUTH_HEADERS,
    params={"user_id": TEST_USER_ID},
)
```

## DB Setup — Unit Tests (mongomock-motor)

```python
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

async def setup_mock_db():
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client["test_db"],
        document_models=[User, Campaign, Customer, Sequence, Email],
    )
```

## DB Setup — Integration Tests (Testcontainers MongoDB)

```python
import os
import pytest
from testcontainers.mongodb import MongoDbContainer

@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:7") as mongo:
        os.environ["MONGODB_URI"] = mongo.get_connection_url()
        os.environ["MONGODB_DATABASE"] = "test_db"
        os.environ["SERVER_AUTH_KEY"] = "test-server-auth-key"
        yield mongo
```

## Integration Test conftest.py

```python
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

@pytest_asyncio.fixture(scope="module")
async def client(mongo_container):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

@pytest_asyncio.fixture(autouse=True)
async def clean_db(mongo_container):
    yield
    from motor.motor_asyncio import AsyncIOMotorClient
    motor_client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = motor_client[os.environ["MONGODB_DATABASE"]]
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})
    motor_client.close()
```

## Models (Beanie Documents)

```python
from beanie import Document
from pydantic import Field

class BaseDocument(Document):
    class Settings:
        use_state_management = True

class Campaign(BaseDocument):
    name: str
    user_id: str
    status: str = "draft"

    class Settings:
        name = "campaigns"

class Customer(BaseDocument):
    email: str
    first_name: str
    campaign_id: str

    class Settings:
        name = "customers"
```

## Repository Pattern

```python
from beanie import Document
from typing import TypeVar, Generic

T = TypeVar("T", bound=Document)

class BeanieRepository(Generic[T]):
    document_class: type[T]

    async def create(self, data: dict) -> T:
        doc = self.document_class(**data)
        await doc.insert()
        return doc

    async def find_by_id(self, id: str) -> T | None:
        return await self.document_class.get(id)

class CampaignRepository(BeanieRepository[Campaign]):
    document_class = Campaign
```

## External Clients to Mock (Unit Tests)

These are the external service clients that must be mocked in unit tests:
- SchedulerClient — scheduling sequences
- WorkflowClient — workflow orchestration
- TriggerClient — event triggers
- PDLClient — People Data Labs enrichment
- ApolloClient — Apollo.io enrichment
- GCSClient — Google Cloud Storage
- ExternalServiceClient — email inbox rotation
- AgentGatewayClient — AI agent gateway
- OrganisationClient — organization management
- MCPClient — Model Context Protocol

```python
from unittest.mock import AsyncMock

mock_scheduler = AsyncMock()  # SchedulerClient
mock_workflow = AsyncMock()   # WorkflowClient
mock_pdl = AsyncMock()        # PDLClient
```

## Unit Test Patterns

### Service with Beanie Repository

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

class TestCampaignService:
    def setup_method(self):
        self.mock_repo = AsyncMock(spec=CampaignRepository)
        self.mock_scheduler = AsyncMock()

    @pytest.mark.unit
    async def test_create_campaign_returns_draft(self):
        self.mock_repo.create.return_value = MagicMock(
            id=ObjectId(), name="Test", user_id="user-1", status="draft"
        )
        # result = await self.service.create({"name": "Test", "user_id": "user-1"})
        # assert result.status == "draft"

    @pytest.mark.unit
    async def test_activate_calls_scheduler(self):
        mock_campaign = MagicMock(status="draft", id=ObjectId())
        self.mock_repo.find_by_id.return_value = mock_campaign
        # await self.service.activate(str(mock_campaign.id), user_id="user-1")
        # self.mock_scheduler.create_schedule.assert_called_once()

    @pytest.mark.unit
    async def test_cannot_activate_archived(self):
        mock_campaign = MagicMock(status="archived", id=ObjectId())
        self.mock_repo.find_by_id.return_value = mock_campaign
        # with pytest.raises(ValueError, match="Cannot activate"):
        #     await self.service.activate(str(mock_campaign.id), user_id="user-1")
```

### Mocking External Clients

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestPDLClient:
    @pytest.mark.unit
    async def test_search_respects_credit_limit(self):
        pass

    @pytest.mark.unit
    async def test_enrich_handles_not_found(self):
        pass
```

## Integration Test Patterns

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

AUTH_HEADERS = {
    "X-Server-Auth-Key": "test-server-auth-key",
    "Content-Type": "application/json",
}
TEST_USER_ID = "integration-test-user-001"

class TestCampaignEndpoints:
    async def test_201_creates_campaign(self, client: AsyncClient):
        res = await client.post(
            "/api/v1/campaigns",
            json={"name": "Test Campaign", "description": "Integration test"},
            headers=AUTH_HEADERS,
            params={"user_id": TEST_USER_ID},
        )
        assert res.status_code == 201
        assert res.json()["status"] == "draft"

    async def test_401_missing_auth_key(self, client: AsyncClient):
        res = await client.get("/api/v1/campaigns", params={"user_id": TEST_USER_ID})
        assert res.status_code == 401

    async def test_403_invalid_auth_key(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers={"X-Server-Auth-Key": "wrong-key"},
            params={"user_id": TEST_USER_ID},
        )
        assert res.status_code == 403
```

## Security Test Patterns

### Server Auth Key Boundary Tests

```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.security

VALID_AUTH = {"X-Server-Auth-Key": "test-server-auth-key"}

class TestServerAuthSecurity:
    async def test_rejects_missing_auth_key(self, client: AsyncClient):
        res = await client.get("/api/v1/campaigns", params={"user_id": "u1"})
        assert res.status_code == 401

    async def test_rejects_empty_auth_key(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers={"X-Server-Auth-Key": ""},
            params={"user_id": "u1"},
        )
        assert res.status_code == 401

    async def test_rejects_partial_key(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers={"X-Server-Auth-Key": "test-server"},
            params={"user_id": "u1"},
        )
        assert res.status_code == 403

    async def test_auth_key_not_leaked_in_error(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers={"X-Server-Auth-Key": "wrong-key"},
            params={"user_id": "u1"},
        )
        assert "wrong-key" not in res.text

class TestUserIsolation:
    async def test_user_cannot_see_other_users_data(self, client: AsyncClient):
        await client.post(
            "/api/v1/campaigns",
            json={"name": "User1 Campaign"},
            headers=VALID_AUTH,
            params={"user_id": "user-1"},
        )
        res = await client.get(
            "/api/v1/campaigns",
            headers=VALID_AUTH,
            params={"user_id": "user-2"},
        )
        assert res.status_code == 200
        for c in res.json().get("data", []):
            assert c.get("user_id") != "user-1"
```

### NoSQL Injection Protection

```python
class TestNoSQLInjection:
    async def test_operator_in_query_param(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers=VALID_AUTH,
            params={"user_id": : null},
        )
        assert res.status_code in (200, 422)

    async def test_where_injection(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers=VALID_AUTH,
            params={"user_id": : 1==1},
        )
        assert res.status_code in (200, 422)

    async def test_regex_injection(self, client: AsyncClient):
        res = await client.get(
            "/api/v1/campaigns",
            headers=VALID_AUTH,
            params={"user_id": : .*},
        )
        assert res.status_code in (200, 422)
```

## Smoke Test Patterns

```python
import os

# Auth for smoke tests uses X-Server-Auth-Key, not JWT
SMOKE_AUTH_HEADERS = {
    "X-Server-Auth-Key": os.environ.get("SMOKE_AUTH_KEY", ""),
}

@pytest.mark.smoke
def test_authenticated_endpoint(client):
    if not SMOKE_AUTH_HEADERS["X-Server-Auth-Key"]:
        pytest.skip("SMOKE_AUTH_KEY not set")
    res = client.get(
        "/api/v1/campaigns",
        headers=SMOKE_AUTH_HEADERS,
        params={"user_id": "smoke-test-user"},
    )
    assert res.status_code == 200
```

## CI Environment Variables

```yaml
env:
  MONGODB_URI: mongodb://localhost:27017
  MONGODB_DATABASE: test_db
  SERVER_AUTH_KEY: test-server-auth-key
  AI_GATEWAY_BASE_URL: http://localhost:9999
  AI_GATEWAY_API_KEY: test-api-key
  REDIS_URL: redis://localhost:6379
  GCS_BUCKET_NAME: test-bucket
```

## Lessons Learned

- Architecture deletions leave obsolete version guards — audit skips after major removals
- Python version differences between local and CI can mislead diagnosis — trust CI
- FastAPI trailing slash redirects and env completeness are frequent CI traps
- Fresh branches from dev beat rebasing long-lived feature branches
- AI/external service endpoints: mock at the client method level, not HTTP level
- Redis: use AsyncMock for the entire client instance
