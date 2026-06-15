"""Domain enumerations shared across all layers.

Uses ``(str, Enum)`` so values serialize directly to the CHECK-constrained
TEXT columns in the database.
"""

from enum import Enum


class UnitType(str, Enum):
    """How a product is measured and sold."""

    UNIT = "unit"
    WEIGHT_KG = "weight_kg"
    PACK = "pack"


class PaymentMethod(str, Enum):
    """Payment method for a sale."""

    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"


class MovementType(str, Enum):
    """Type of cash movement within a cash register session."""

    SALE_CASH = "sale_cash"
    RETURN = "return"
    SUPPLIER_PAYMENT = "supplier_payment"
    EXPENSE = "expense"
