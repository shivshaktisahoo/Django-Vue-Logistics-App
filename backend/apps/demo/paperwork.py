"""Demo paperwork: the documents a real shipment accumulates, attached at the moment
they'd exist (invoice and packing list at booking, transport document at departure,
customs entry at clearance), so every Documents tab and audit trail looks lived-in."""

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents import services as documents
from apps.documents.models import ShipmentDocument
from apps.organizations.permissions import Role
from apps.shipments.domain import ShipmentStatus as S

from .procurement import _frozen, simple_pdf

D = ShipmentDocument.DocType
TRANSPORT_DOC = {
    "ocean": (D.BILL_OF_LADING, "Bill of lading"),
    "air": (D.AIR_WAYBILL, "Air waybill"),
    "road": (D.CMR, "CMR consignment note"),
}


def _attach(shipment, actor, at, doc_type, title, lines, *, visible=True, notes=""):
    pdf = simple_pdf(
        title, [f"Shipment {shipment.reference}   Tracking {shipment.tracking_number}", *lines]
    )
    name = f"{title.replace(' ', '-')}-{shipment.reference}.pdf"
    with _frozen(at):
        documents.upload(
            shipment=shipment,
            actor=actor,
            file=SimpleUploadedFile(name, pdf),
            doc_type=doc_type,
            notes=notes,
            visible_to_customer=visible,
        )


def attach_paperwork(*, org, users, rng) -> None:
    from apps.shipments.models import Shipment

    ops, customer_user = users[Role.OPS], users[Role.CUSTOMER]
    portal_party = customer_user.memberships.get(org=org).party_id
    shipments = (
        Shipment.objects.for_org(org)
        .exclude(status__in=[S.DRAFT, S.CANCELLED])
        .select_related("customer", "shipper", "consignee", "origin", "destination", "carrier")
    )
    for s in shipments:
        events = {}
        for e in s.events.order_by("occurred_at"):
            events.setdefault(e.code, e.occurred_at)
        booked = events.get("BKD")
        if booked is None:
            continue
        uploader = customer_user if s.customer_id == portal_party else ops
        value = f"{s.declared_value:,.2f} {s.currency}" if s.declared_value else "n/a"
        parties = [
            f"Seller: {s.shipper.name}, {s.shipper.city}",
            f"Buyer: {s.consignee.name}, {s.consignee.city}",
        ]
        _attach(
            s,
            uploader,
            booked,
            D.COMMERCIAL_INVOICE,
            "Commercial invoice",
            [
                *parties,
                f"Goods: {s.commodity}   HS {s.hs_code or '-'}",
                f"Incoterm: {s.incoterm}   Value: {value}",
                f"PO: {s.customer_reference or '-'}",
            ],
        )
        _attach(
            s,
            uploader,
            booked,
            D.PACKING_LIST,
            "Packing list",
            [
                *parties,
                f"{s.total_packages} packages   Gross {s.gross_weight_kg} kg   Volume {s.volume_cbm} m3",
                f"Marks: {s.customer_reference or s.reference}",
            ],
        )
        if "DEP" in events:
            doc_type, title = TRANSPORT_DOC[s.mode]
            _attach(
                s,
                ops,
                events["DEP"],
                doc_type,
                title,
                [
                    f"Carrier: {s.carrier.name if s.carrier else '-'}   {s.voyage_number or ''}",
                    f"House: {s.house_bill or '-'}   Master: {s.master_bill or '-'}",
                    f"From {s.origin.name} ({s.origin.code}) to {s.destination.name} ({s.destination.code})",
                    *parties,
                ],
            )
        if "CLR" in events:
            _attach(
                s,
                ops,
                events["CLR"],
                D.CUSTOMS,
                "Customs declaration",
                [
                    f"Import entry {rng.randrange(10**9, 10**10)} released",
                    f"HS {s.hs_code or '-'}   Declared value {value}",
                    "Duties and VAT settled by importer of record",
                ],
            )
        # Internal paperwork the customer never sees.
        _attach(
            s,
            ops,
            booked,
            D.OTHER,
            "Cost sheet",
            [
                "Internal: buy rates, margin and accruals",
                f"Carrier: {s.carrier.name if s.carrier else 'TBC'}",
            ],
            visible=False,
            notes="Internal: not shared with the customer",
        )
