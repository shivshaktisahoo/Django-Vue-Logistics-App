import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations import services as org_services
from apps.organizations.models import Membership


@pytest.fixture
def make_user(db):
    counter = iter(range(10_000))

    def _make(email: str | None = None, password: str = "S3cure!pass", **extra) -> User:
        email = email or f"user{next(counter)}@example.com"
        return User.objects.create_user(email, password, **extra)

    return _make


@pytest.fixture
def make_org(make_user):
    def _make(owner: User | None = None, **data):
        owner = owner or make_user()
        data.setdefault("name", "Atlas Logistics")
        return org_services.create_org(owner=owner, **data)

    return _make


@pytest.fixture
def make_member(make_user):
    def _make(org, role: str, user: User | None = None) -> Membership:
        return Membership.objects.create(user=user or make_user(), org=org, role=role)

    return _make


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_for():
    """APIClient authenticated as `user`, optionally scoped to an organization."""

    def _client(user: User, org=None) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        if org is not None:
            client.credentials(HTTP_X_ORG_ID=str(org.id))
        return client

    return _client
