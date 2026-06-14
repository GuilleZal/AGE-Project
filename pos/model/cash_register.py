"""CashRegister and CashMovement domain dataclasses."""

from dataclasses import dataclass, field

from pos.model.enums import MovementType


@dataclass
class CashRegister:
    """A cash register session — opened at start of shift, closed at end.

    Currency fields are ``int`` (whole ARS pesos).
    """

    opening_amount: int
    opening_time: str
    id: int | None = None
    closing_amount: int | None = None
    closing_time: str | None = None
    expected_amount: int | None = None
    difference: int | None = None
    close_reason: str | None = None
    status: str = "open"


@dataclass
class CashMovement:
    """A single cash movement (inflow or outflow) within a register session.

    Currency fields are ``int`` (whole ARS pesos).
    """

    cash_register_id: int
    type: MovementType | str
    amount: int
    id: int | None = None
    description: str | None = None
    created_at: str | None = None
