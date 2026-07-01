"""Sale and SaleItem domain dataclasses."""

from dataclasses import dataclass, field

from pos.model.enums import PaymentMethod


@dataclass
class Sale:
    """A completed customer transaction.

    Currency fields are ``int`` (whole ARS pesos).
    """

    total: int
    payment_method: PaymentMethod | str
    id: int | None = None
    discount: int = 0
    surcharge: int = 0
    cash_register_id: int | None = None
    created_at: str | None = None


@dataclass
class SaleItem:
    """One line item within a sale.

    Currency fields are ``int`` (whole ARS pesos).
    Quantity is ``float`` to support weight_kg products.
    """

    product_id: int
    quantity: float
    unit_price: int
    subtotal: int
    id: int | None = None
    sale_id: int | None = None
