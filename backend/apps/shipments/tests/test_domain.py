from decimal import Decimal

import pytest

from apps.shipments import domain
from apps.shipments.domain import ShipmentStatus as S


@pytest.mark.parametrize(
    ("number", "valid"),
    [
        ("CSQU3054383", True),  # the worked example from ISO 6346
        ("MSKU9070323", True),
        ("CSQU3054384", False),  # wrong check digit
        ("CSQA3054383", False),  # category must be U, J or Z
        ("CSQU305438", False),  # too short
        ("csqu 305438 3", True),  # case and spaces are normalised
    ],
)
def test_iso6346_container_numbers(number, valid):
    assert domain.is_valid_container_number(number) is valid


@pytest.mark.parametrize(
    ("mode", "gross", "cbm", "expected"),
    [
        ("air", "100", "1.2", "200.00"),  # volumetric wins: 1.2 m³ × 166.67
        ("air", "500", "1.2", "500.00"),  # actual wins
        ("road", "1000", "6", "2000.00"),  # 6 m³ × 333.33
        ("ocean", "3500", "12", "12000.00"),  # W/M: 12 m³ = 12 revenue tonnes
    ],
)
def test_chargeable_weight(mode, gross, cbm, expected):
    assert domain.chargeable_weight(mode, Decimal(gross), Decimal(cbm)) == Decimal(expected)


def test_volume_from_dimensions():
    assert domain.volume_cbm(Decimal(120), Decimal(100), Decimal(150), 4) == Decimal("7.200")
    assert domain.volume_cbm(None, Decimal(100), Decimal(150), 4) == Decimal("0")


def test_lifecycle_rules():
    assert domain.can_transition(S.DRAFT, S.BOOKED)
    assert domain.can_transition(S.IN_TRANSIT, S.OUT_FOR_DELIVERY)  # domestic, no customs
    assert not domain.can_transition(S.DRAFT, S.DELIVERED)
    assert not domain.can_transition(S.PICKED_UP, S.CANCELLED)  # cargo already moving
    assert not domain.can_transition(S.DELIVERED, S.IN_TRANSIT)
    assert all(not domain.TRANSITIONS[s] for s in domain.TERMINAL_STATUSES)
