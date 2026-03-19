# Django ORM Context

> Stack-specific patterns for testing Django applications.
> Load this context when the target repo uses `from django`.

## Stack Summary

- **Framework:** Django (sync, with optional async views)
- **ORM:** Django ORM
- **Database:** PostgreSQL (default) / SQLite (test)
- **Package Manager:** pip
- **Test Runner:** pytest + pytest-django
- **Auth Pattern:** Django auth / DRF TokenAuthentication / SimpleJWT
- **App Entry:** `django.conf.settings` + WSGI/ASGI application

## Key Differences from FastAPI Default

| FastAPI Default | Django |
|---|---|
| pytest-asyncio | pytest-django |
| httpx AsyncClient | django.test.Client or DRF APIClient |
| Testcontainers | Django test DB (auto-created) |
| Manual migration | manage.py migrate |
| Pydantic | Django serializers / forms |
| OpenAPI at /openapi.json | drf-spectacular at /api/schema/ |

## Install Dependencies

```bash
pip install \
  pytest pytest-django pytest-cov \
  djangorestframework drf-spectacular \
  factory-boy faker
```

## pytest Configuration

```ini
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py"]
markers = ["unit", "integration", "contract", "security"]
```

## Test Client Setup

```python
import pytest
from rest_framework.test import APIClient

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
```

## Model Factory (factory-boy)

```python
import factory
from django.contrib.auth import get_user_model

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
```

## Integration Test Pattern

```python
import pytest
from rest_framework import status

@pytest.mark.django_db
class TestUserEndpoints:
    def test_create_user_201(self, api_client):
        res = api_client.post("/api/users/", {"email": "a@b.com", "password": "Secure123!"})
        assert res.status_code == status.HTTP_201_CREATED

    def test_list_users_requires_auth(self, api_client):
        res = api_client.get("/api/users/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_read_own_profile(self, auth_client, user):
        res = auth_client.get(f"/api/users/{user.id}/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["email"] == user.email
```
