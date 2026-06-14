"""Return domain dataclass (atomic return model — no FK to original sale)."""

from dataclasses import dataclass


@dataclass
class Return:
    """A direct atomic product return linked to the current cash register session.

    Currency fields are ``int`` (whole ARS pesos).
    Quantity is ``float`` to support weight_kg products.
    """

    product_id: int
    quantity: float
    refund_amount: int
    cash_register_id: int
    id: int | None = None
    reason: str | None = None
    created_at: str | None = None
