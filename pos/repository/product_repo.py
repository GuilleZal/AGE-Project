"""Product repository — CRUD with barcode uniqueness, search, and upsert-import.

All queries are parameterized. ``DataError`` is raised on integrity violations
(e.g. duplicate barcode, delete blocked by transaction history).
"""

import sqlite3
from typing import Optional

from pos.model.product import Product
from pos.model.enums import UnitType
from pos.model.exceptions import DataError


class ProductRepo:
    """Data-access for the ``products`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ------------------------------------------------------------------ read

    def find_by_barcode(self, barcode: str) -> Optional[Product]:
        """Return the product with the given barcode, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM products WHERE barcode = ?", (barcode,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def search(self, query: str) -> list[Product]:
        """Search products by name (``LIKE %query%``)."""
        rows = self._db.execute(
            "SELECT * FROM products WHERE name LIKE ?", (f"%{query}%",)
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_all(self) -> list[Product]:
        """Return every product, ordered by name."""
        rows = self._db.execute(
            "SELECT * FROM products ORDER BY name"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    # ----------------------------------------------------------------- create

    def create(self, product: Product) -> Product:
        """Insert a new product.

        Raises:
            DataError: If the barcode (when not ``None``) already exists.
        """
        ut = _unit_type_str(product.unit_type)
        try:
            cur = self._db.execute(
                """INSERT INTO products
                   (barcode, name, category_id, sale_price, cost_price,
                    stock, unit_type, description, low_stock_threshold)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   RETURNING id, created_at, updated_at""",
                (
                    product.barcode,
                    product.name,
                    product.category_id,
                    product.sale_price,
                    product.cost_price,
                    product.stock,
                    ut,
                    product.description,
                    product.low_stock_threshold,
                ),
            )
            row = cur.fetchone()
            product.id = row["id"]
            product.created_at = row["created_at"]
            product.updated_at = row["updated_at"]
            return product
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DataError(
                    f"El código de barras '{product.barcode}' ya existe"
                ) from e
            raise DataError(str(e)) from e

    # ----------------------------------------------------------------- update

    def update(self, product: Product) -> Product:
        """Update all fields of an existing product.

        Raises:
            DataError: If the product id is not found or a barcode conflict exists.
        """
        ut = _unit_type_str(product.unit_type)
        try:
            cur = self._db.execute(
                """UPDATE products
                   SET barcode = ?, name = ?, category_id = ?, sale_price = ?,
                       cost_price = ?, stock = ?, unit_type = ?,
                       description = ?, low_stock_threshold = ?,
                       updated_at = datetime('now')
                   WHERE id = ?
                   RETURNING updated_at""",
                (
                    product.barcode,
                    product.name,
                    product.category_id,
                    product.sale_price,
                    product.cost_price,
                    product.stock,
                    ut,
                    product.description,
                    product.low_stock_threshold,
                    product.id,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise DataError(
                    f"Producto con id={product.id} no encontrado"
                )
            product.updated_at = row["updated_at"]
            return product
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DataError("El código de barras ya existe") from e
            raise DataError(str(e)) from e

    # ----------------------------------------------------------------- delete

    def delete(self, product_id: int) -> None:
        """Delete a product.

        Raises:
            DataError: If the product is referenced by any sale or purchase.
        """
        sales = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM sale_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        purchases = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM purchase_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        if sales > 0 or purchases > 0:
            raise DataError(
                "El producto tiene historial de transacciones. "
                "Configure stock=0 en lugar de eliminar."
            )
        self._db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    # --------------------------------------------------------------- upsert

    def upsert_from_import(self, product: Product) -> tuple[Product, str]:
        """Insert or selectively update a product from an Excel import.

        - Barcode is NOT in DB → full INSERT (returns ``(product, "created")``).
        - Barcode IS in DB     → UPDATE only price, cost, stock, unit_type.
          Name is NOT overwritten (human-curated). Returns ``(product, "updated")``.

        Returns:
            Tuple of ``(Product, action)`` where *action* is ``"created"`` or ``"updated"``.
        """
        existing = self._db.execute(
            "SELECT id FROM products WHERE barcode = ?", (product.barcode,)
        ).fetchone()

        if existing:
            ut = _unit_type_str(product.unit_type)
            self._db.execute(
                """UPDATE products
                   SET sale_price = ?, cost_price = ?, stock = ?,
                       unit_type = ?, updated_at = datetime('now')
                   WHERE barcode = ?""",
                (product.sale_price, product.cost_price, product.stock,
                 ut, product.barcode),
            )
            product.id = existing["id"]
            return product, "updated"
        else:
            created = self.create(product)
            return created, "created"

    # ----------------------------------------------------------- helpers ---

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Product:
        return Product(
            id=row["id"],
            barcode=row["barcode"],
            name=row["name"],
            category_id=row["category_id"],
            sale_price=row["sale_price"],
            cost_price=row["cost_price"],
            stock=row["stock"],
            unit_type=row["unit_type"],
            description=row["description"],
            low_stock_threshold=row["low_stock_threshold"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# ----------------------------------------------------------------- helpers ---

def _unit_type_str(ut: UnitType | str) -> str:
    """Normalize *ut* to a plain string for DB storage."""
    return ut.value if isinstance(ut, UnitType) else ut
