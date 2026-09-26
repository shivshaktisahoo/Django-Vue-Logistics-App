import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db
URL = "/api/v1/documents/"
PDF = b"%PDF-1.7\n" + b"0" * 100


def _upload(client, shipment_id, data=PDF, name="invoice.pdf", **extra):
    return client.post(
        URL,
        {
            "shipment": shipment_id,
            "doc_type": "commercial_invoice",
            "file": SimpleUploadedFile(name, data),
            **extra,
        },
        format="multipart",
    )


def test_upload_list_and_download(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    doc = _upload(ops, booked["id"], name='../../etc/"evil".pdf').json()
    assert doc["content_type"] == "application/pdf" and doc["size"] == len(PDF)
    assert doc["file_name"] == "_evil_.pdf"  # path and quotes stripped
    resp = ops.get(f"{URL}{doc['id']}/download/")
    assert resp.status_code == 200 and resp.content == PDF
    assert resp["Content-Disposition"] == 'attachment; filename="_evil_.pdf"'


def test_type_is_decided_by_content_not_name(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    resp = _upload(ops, booked["id"], data=b"MZ\x90\x00 not really a pdf", name="invoice.pdf")
    assert resp.status_code == 400


def test_size_limit(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    big = PDF + b"0" * (5 * 1024 * 1024)
    assert _upload(ops, booked["id"], data=big).status_code == 400


def test_internal_documents_are_hidden_from_customers(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    _upload(ops, booked["id"], visible_to_customer=False)
    shared = _upload(ops, booked["id"], name="pl.pdf").json()
    customer = client_for(world.customer, world.org)
    listed = customer.get(URL, {"shipment": booked["id"]}).json()
    assert [d["id"] for d in listed] == [shared["id"]]
    assert customer.delete(f"{URL}{shared['id']}/").status_code == 403  # not their upload


def test_other_tenant_cannot_download(world, booked, client_for, make_org):
    doc = _upload(client_for(world.ops, world.org), booked["id"]).json()
    rival = make_org(name="Rival")
    assert client_for(rival.owner, rival).get(f"{URL}{doc['id']}/download/").status_code == 404
