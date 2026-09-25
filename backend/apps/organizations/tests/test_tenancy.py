import uuid

import pytest

from apps.organizations.permissions import Role

pytestmark = pytest.mark.django_db


def test_creator_becomes_admin(make_user, client_for):
    user = make_user()
    resp = client_for(user).post("/api/v1/orgs/", {"name": "Atlas Logistics"})
    assert resp.status_code == 201
    assert resp.data["role"] == Role.ADMIN
    assert "*" in resp.data["permissions"]


def test_org_header_required(make_org, client_for):
    org = make_org()
    assert client_for(org.owner).get("/api/v1/orgs/current/").status_code == 403


def test_non_member_gets_404_not_403(make_org, make_user, client_for):
    org = make_org()
    outsider = make_user()
    assert client_for(outsider, org).get("/api/v1/orgs/current/").status_code == 404


def test_garbage_org_id_is_404(make_org, client_for):
    org = make_org()
    client = client_for(org.owner)
    client.credentials(HTTP_X_ORG_ID="not-a-uuid")
    assert client.get("/api/v1/orgs/current/").status_code == 404
    client.credentials(HTTP_X_ORG_ID=str(uuid.uuid4()))
    assert client.get("/api/v1/orgs/current/").status_code == 404


def test_members_are_isolated_per_org(make_org, client_for):
    a, b = make_org(name="A"), make_org(name="B")
    resp = client_for(a.owner, a).get("/api/v1/orgs/current/members/")
    assert [m["email"] for m in resp.data] == [a.owner.email]
    assert b.owner.email not in {m["email"] for m in resp.data}


@pytest.mark.parametrize("role", [Role.OPS, Role.CUSTOMER, Role.CARRIER])
def test_only_admin_manages_members(make_org, make_member, client_for, role):
    org = make_org()
    member = make_member(org, role)
    resp = client_for(member.user, org).post(
        "/api/v1/orgs/current/members/", {"email": "new@example.com", "role": Role.OPS}
    )
    assert resp.status_code == 403


def test_carrier_cannot_view_member_list(make_org, make_member, client_for):
    org = make_org()
    carrier = make_member(org, Role.CARRIER)
    assert client_for(carrier.user, org).get("/api/v1/orgs/current/members/").status_code == 403


def test_owner_cannot_be_removed(make_org, client_for):
    org = make_org()
    client = client_for(org.owner, org)
    owner_membership = client.get("/api/v1/orgs/current/members/").data[0]
    resp = client.delete(f"/api/v1/orgs/current/members/{owner_membership['id']}/")
    assert resp.status_code == 400


def test_health_endpoints_are_public(api_client):
    assert api_client.get("/api/v1/health/").data["status"] == "ok"
    assert api_client.get("/api/v1/health/ready/").data["status"] == "ok"
