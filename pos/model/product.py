"""Product and Category domain dataclasses."""

from dataclasses import dataclass, field


@dataclass
class Category:
    """Product category (e.g. 'Vinos', 'Gaseosas')."""

    name: str
    id: int | None = None
    created_at: str | None = None


@dataclass
class Product:
    """A sellable item with optional barcode, category, and stock tracking.

    Currency fields (sale_price, cost_price) are ``int`` (whole ARS pesos).
    Stock is ``float``. All products operate by unit.
    """

    name: str
    sale_price: int
    cost_price: int
    id: int | None = None
    barcode: str | None = None
    category_id: int | None = None
    stock: float = 0.0
    description: str | None = None
    low_stock_threshold: float = 5.0
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None
