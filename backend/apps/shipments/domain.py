"""Pure logistics rules: no database, no Django models. Unit-tested directly."""

import string
from decimal import ROUND_HALF_UP, Decimal

from django.db import models


class ShipmentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    BOOKED = "booked", "Booked"
    PICKED_UP = "picked_up", "Picked up"
    IN_TRANSIT = "in_transit", "In transit"
    AT_CUSTOMS = "at_customs", "At customs"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
    DELIVERED = "delivered", "Delivered"
    ON_HOLD = "on_hold", "On hold"
    CANCELLED = "cancelled", "Cancelled"


S = ShipmentStatus

# Allowed forward moves. ON_HOLD can be entered from any active status and returns to
# the status it was entered from (see services.change_status).
TRANSITIONS: dict[str, frozenset[str]] = {
    S.DRAFT: frozenset({S.BOOKED, S.CANCELLED}),
    S.BOOKED: frozenset({S.PICKED_UP, S.ON_HOLD, S.CANCELLED}),
    S.PICKED_UP: frozenset({S.IN_TRANSIT, S.ON_HOLD}),
    S.IN_TRANSIT: frozenset({S.AT_CUSTOMS, S.OUT_FOR_DELIVERY, S.ON_HOLD}),
    S.AT_CUSTOMS: frozenset({S.OUT_FOR_DELIVERY, S.ON_HOLD}),
    S.OUT_FOR_DELIVERY: frozenset({S.DELIVERED, S.ON_HOLD}),
    S.ON_HOLD: frozenset(),  # only "resume"
    S.DELIVERED: frozenset(),
    S.CANCELLED: frozenset(),
}

ACTIVE_STATUSES = frozenset(
    {S.BOOKED, S.PICKED_UP, S.IN_TRANSIT, S.AT_CUSTOMS, S.OUT_FOR_DELIVERY, S.ON_HOLD}
)
TERMINAL_STATUSES = frozenset({S.DELIVERED, S.CANCELLED})
# Full editing of route/cargo is allowed only before the freight physically moves.
EDITABLE_STATUSES = frozenset({S.DRAFT, S.BOOKED})


class EventCode(models.TextChoices):
    """Milestone codes, modelled on common EDI/visibility-platform event codes."""

    BOOKED = "BKD", "Booking confirmed"
    PICKED_UP = "PUP", "Cargo picked up"
    GATE_IN = "GIN", "Gate in at origin"
    LOADED = "LOD", "Loaded on vessel / aircraft / truck"
    DEPARTED = "DEP", "Departed origin"
    ARRIVED = "ARR", "Arrived at destination hub"
    DISCHARGED = "DIS", "Discharged / unloaded"
    CUSTOMS_HOLD = "CUS", "Customs inspection"
    CUSTOMS_CLEARED = "CLR", "Customs cleared"
    OUT_FOR_DELIVERY = "OFD", "Out for delivery"
    DELIVERED = "DLV", "Delivered (POD)"
    ON_HOLD = "HLD", "Shipment on hold"
    RESUMED = "RES", "Hold released"
    CANCELLED = "CAN", "Shipment cancelled"
    DELAYED = "DLY", "Delay reported"
    NOTE = "NTE", "Update"


# The milestone written automatically when a shipment enters a status.
STATUS_EVENT: dict[str, str] = {
    S.BOOKED: EventCode.BOOKED,
    S.PICKED_UP: EventCode.PICKED_UP,
    S.IN_TRANSIT: EventCode.DEPARTED,
    S.AT_CUSTOMS: EventCode.CUSTOMS_HOLD,
    S.OUT_FOR_DELIVERY: EventCode.OUT_FOR_DELIVERY,
    S.DELIVERED: EventCode.DELIVERED,
    S.ON_HOLD: EventCode.ON_HOLD,
    S.CANCELLED: EventCode.CANCELLED,
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


# ---------------------------------------------------------------- chargeable weight

KG = Decimal("0.01")

# Volumetric conversion factors (kg per m³) used across the industry:
#   air   1:6000 cm³/kg → 166.67 kg/m³
#   road  1:3000 cm³/kg → 333.33 kg/m³
#   ocean W/M: 1 m³ counts as 1 revenue tonne → 1000 kg/m³
VOLUMETRIC_KG_PER_CBM = {
    "air": Decimal("1000000") / Decimal("6000"),
    "road": Decimal("1000000") / Decimal("3000"),
    "ocean": Decimal("1000"),
}


def chargeable_weight(mode: str, gross_kg: Decimal, volume_cbm: Decimal) -> Decimal:
    """The weight freight is billed on: the greater of actual and volumetric weight."""
    volumetric = volume_cbm * VOLUMETRIC_KG_PER_CBM[mode]
    return max(gross_kg, volumetric).quantize(KG, rounding=ROUND_HALF_UP)


def volume_cbm(length_cm, width_cm, height_cm, quantity) -> Decimal:
    if not (length_cm and width_cm and height_cm):
        return Decimal("0")
    cbm = Decimal(length_cm) * Decimal(width_cm) * Decimal(height_cm) / Decimal("1000000")
    return (cbm * quantity).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------- ISO 6346 containers


def _iso6346_letter_values() -> dict[str, int]:
    # A=10 upwards, skipping multiples of 11 (11, 22, 33).
    values, n = {}, 10
    for letter in string.ascii_uppercase:
        if n % 11 == 0:
            n += 1
        values[letter] = n
        n += 1
    return values


_LETTER_VALUES = _iso6346_letter_values()


def container_check_digit(first_ten: str) -> int:
    """Check digit for owner code (3) + category (1) + serial (6), e.g. MSCU123456 → ?"""
    total = 0
    for i, ch in enumerate(first_ten):
        value = _LETTER_VALUES[ch] if ch.isalpha() else int(ch)
        total += value * (2**i)
    return total % 11 % 10


def is_valid_container_number(number: str) -> bool:
    """ISO 6346: 4 letters (owner + U/J/Z category), 6 digits, check digit."""
    n = number.replace(" ", "").upper()
    if len(n) != 11 or not n[:4].isalpha() or not n[4:].isdigit() or n[3] not in "UJZ":
        return False
    return container_check_digit(n[:10]) == int(n[10])
