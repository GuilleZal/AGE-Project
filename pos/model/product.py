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
    Stock is ``int``. All products operate by unit.
    """

    name: str
    sale_price: int
    cost_price: int
    id: int | None = None
    barcode: str | None = None
    category_id: int | None = None
    stock: float = 0.0
    unit_type: str = "Unidad"
    description: str | None = None
    low_stock_threshold: int = 5
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.unit_type == "Kg" and self.stock is not None:
            self.stock = round(float(self.stock), 3)
