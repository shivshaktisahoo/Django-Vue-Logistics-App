import pytest
from django.conf import settings

from apps.demo.seed import seed_demo
from apps.organizations.permissions import Role

pytestmark = pytest.mark.django_db


def test_login_sets_httponly_refresh_cookie_and_refresh_rotates(api_client, make_user):
    make_user("ops@example.com", "S3cure!pass")

    resp = api_client.post(
        "/api/v1/auth/login/", {"email": "OPS@example.com", "password": "S3cure!pass"}
    )

    assert resp.status_code == 200
    assert resp.data["access"]
    cookie = resp.cookies[settings.REFRESH_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["path"] == settings.REFRESH_COOKIE_PATH
    assert "refresh" not in resp.data  # never exposed to JavaScript

    refreshed = api_client.post("/api/v1/auth/refresh/")
    assert refreshed.status_code == 200
    assert refreshed.data["user"]["email"] == "ops@example.com"


def test_wrong_password_is_rejected(api_client, make_user):
    make_user("ops@example.com", "S3cure!pass")
    resp = api_client.post("/api/v1/auth/login/", {"email": "ops@example.com", "password": "nope"})
    assert resp.status_code == 400


def test_refresh_without_cookie_means_no_session(api_client):
    assert api_client.post("/api/v1/auth/refresh/").status_code == 204


def test_refresh_with_garbage_cookie_is_401(api_client):
    api_client.cookies[settings.REFRESH_COOKIE_NAME] = "garbage"
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


def test_logout_blacklists_refresh_token(api_client, make_user):
    make_user("ops@example.com", "S3cure!pass")
    api_client.post("/api/v1/auth/login/", {"email": "ops@example.com", "password": "S3cure!pass"})
    old = api_client.cookies[settings.REFRESH_COOKIE_NAME].value

    assert api_client.post("/api/v1/auth/logout/").status_code == 204

    api_client.cookies[settings.REFRESH_COOKIE_NAME] = old
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


@pytest.mark.parametrize("role", [r.value for r in Role])
def test_demo_login_for_every_role(api_client, role):
    org = seed_demo()

    resp = api_client.post("/api/v1/auth/demo/", {"role": role})

    assert resp.status_code == 200
    assert resp.data["user"]["is_demo"] is True
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
    orgs = api_client.get("/api/v1/orgs/").data
    assert [(o["org"]["id"], o["role"]) for o in orgs] == [(str(org.id), role)]


def test_demo_login_before_seed_gives_friendly_error(api_client):
    resp = api_client.post("/api/v1/auth/demo/", {"role": "admin"})
    assert resp.status_code == 400
    assert "demo workspace" in resp.data["detail"]


def test_seed_demo_is_idempotent_and_reset_rebuilds():
    first = seed_demo()
    assert seed_demo().id == first.id
    assert seed_demo(reset=True).id != first.id
