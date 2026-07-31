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
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    TRANSFER = "transfer"
    QR = "qr"


class MovementType(str, Enum):
    """Type of cash movement within a cash register session."""

    SALE_CASH = "sale_cash"
    SALE_CARD = "sale_card"
    SALE_DEBIT_CARD = "sale_debit_card"
    SALE_CREDIT_CARD = "sale_credit_card"
    SALE_TRANSFER = "sale_transfer"
    SALE_QR = "sale_qr"
    RETURN = "return"
    SUPPLIER_PAYMENT = "supplier_payment"
    EXPENSE = "expense"


class UserRole(str, Enum):
    """User role for RBAC — maps to CHECK constraint in users table."""

    ADMIN = "admin"
    GERENTE = "gerente"
    CAJERO = "cajero"
    INVENTARIO = "inventario"
