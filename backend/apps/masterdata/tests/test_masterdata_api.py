import pytest

from apps.masterdata.models import Party
from apps.organizations.permissions import Role

pytestmark = pytest.mark.django_db
PARTIES = "/api/v1/masterdata/parties/"


@pytest.fixture
def setup(make_org, make_member):
    org = make_org()
    acme = Party.objects.create(org=org, name="Acme", code="ACME", country="AE", is_customer=True)
    Party.objects.create(org=org, name="Globex", code="GLOBEX", country="AE", is_customer=True)
    customer = make_member(org, Role.CUSTOMER)
    customer.party = acme
    customer.save()
    return org, acme, customer.user


def test_codes_are_uppercased_and_unique_per_org(setup, client_for, make_org):
    org, _, _ = setup
    client = client_for(org.owner, org)
    resp = client.post(PARTIES, {"name": "New Co", "code": "newco", "country": "ae"})
    assert resp.status_code == 201 and resp.data["code"] == "NEWCO" and resp.data["country"] == "AE"
    assert (
        client.post(PARTIES, {"name": "Dup", "code": "NEWCO", "country": "AE"}).status_code == 400
    )
    other = make_org(name="Other")
    assert (
        client_for(other.owner, other)
        .post(PARTIES, {"name": "Same code elsewhere", "code": "NEWCO", "country": "AE"})
        .status_code
        == 201
    )


def test_customer_sees_only_own_account_and_address_book(setup, client_for):
    org, acme, customer = setup
    client = client_for(customer, org)
    created = client.post(
        PARTIES, {"name": "Acme Warehouse", "code": "ACMEWH", "country": "AE", "is_customer": True}
    )
    assert created.status_code == 201
    assert created.data["owner"] == acme.id
    assert created.data["is_customer"] is False  # can't mint billing accounts
    names = sorted(p["name"] for p in client.get(PARTIES).data["results"])
    assert names == ["Acme", "Acme Warehouse"]


def test_customer_cannot_edit_master_data(setup, client_for):
    org, acme, customer = setup
    resp = client_for(customer, org).patch(f"{PARTIES}{acme.id}/", {"name": "Hacked"})
    assert resp.status_code == 403


def test_party_in_use_cannot_be_deleted(client_for, make_org, make_member):
    from apps.shipments.tests.conftest import World

    world = World(make_org(), None, make_member)
    client = client_for(world.ops, world.org)
    assert client.post("/api/v1/shipments/", world.payload()).status_code == 201
    resp = client.delete(f"{PARTIES}{world.shipper.id}/")
    assert resp.status_code == 400
    assert "Deactivate" in resp.data["detail"]
