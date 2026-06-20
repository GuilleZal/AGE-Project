"""Product repository — CRUD with barcode uniqueness, search, and upsert-import.

All queries are parameterized. ``DataError`` is raised on integrity violations
(e.g. duplicate barcode, delete blocked by transaction history).
"""

import sqlite3
from typing import Optional

from pos.model.product import Product
from pos.model.exceptions import DataError


class ProductRepo:
    """Data-access for the ``products`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ------------------------------------------------------------------ read

    def find_by_id(self, product_id: int) -> Optional[Product]:
        """Return the product with the given id, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def find_by_barcode(self, barcode: str) -> Optional[Product]:
        """Return the product with the given barcode, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM products WHERE barcode = ? AND is_active = 1", (barcode,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def find_by_barcode_any(self, barcode: str) -> Optional[Product]:
        """Return the product with the given barcode (active or inactive), or ``None``."""
        row = self._db.execute(
            "SELECT * FROM products WHERE barcode = ?", (barcode,)
        ).fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def search_unified(self, query: str) -> list[Product]:
        """Search products by barcode, name, or category name."""
        q = f"%{query}%"
        rows = self._db.execute(
            """SELECT DISTINCT p.id, p.barcode, p.name, p.cost_price,
                      p.sale_price, p.stock, p.description,
                      p.low_stock_threshold, p.category_id, p.is_active,
                      p.created_at, p.updated_at
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.is_active = 1
                 AND (p.barcode LIKE ? OR p.name LIKE ? OR c.name LIKE ?)
               ORDER BY p.name""",
            (q, q, q),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def search(self, query: str) -> list[Product]:
        """Search products by name (``LIKE %query%``)."""
        rows = self._db.execute(
            "SELECT * FROM products WHERE name LIKE ? AND is_active = 1", (f"%{query}%",)
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_all(self) -> list[Product]:
        """Return every active product, ordered by name."""
        rows = self._db.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY name"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_all_with_inactive(self) -> list[Product]:
        """Return all products (active and inactive), ordered by name."""
        rows = self._db.execute(
            "SELECT * FROM products ORDER BY name"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def low_stock_products(self) -> list[dict]:
        """Return active products where stock is at or below the threshold.

        Each dict has keys ``product_id``, ``name``, ``stock``, and
        ``location`` (the category name, or ``"Sin categoría"`` when
        the product has no category).  Results are ordered by stock
        ascending.
        """
        rows = self._db.execute(
            """SELECT p.id AS product_id,
                      p.name,
                      p.stock,
                      COALESCE(c.name, 'Sin categoría') AS location
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.is_active = 1
                 AND p.stock <= p.low_stock_threshold
               ORDER BY p.stock ASC"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------------- create

    def create(self, product: Product) -> Product:
        """Insert a new product.

        Raises:
            DataError: If the barcode (when not ``None``) already exists.
        """
        try:
            cur = self._db.execute(
                """INSERT INTO products
                   (barcode, name, category_id, sale_price, cost_price,
                    stock, description, low_stock_threshold)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   RETURNING id, created_at, updated_at""",
                (
                    product.barcode,
                    product.name,
                    product.category_id,
                    product.sale_price,
                    product.cost_price,
                    product.stock,
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
        try:
            cur = self._db.execute(
                """UPDATE products
                   SET barcode = ?, name = ?, category_id = ?, sale_price = ?,
                       cost_price = ?, stock = ?,
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
        """Soft delete a product by setting is_active = 0.

        Raises:
            DataError: If the product is not found.
        """
        result = self._db.execute(
            "UPDATE products SET is_active = 0, updated_at = datetime('now') WHERE id = ? AND is_active = 1",
            (product_id,),
        )
        if result.rowcount == 0:
            raise DataError(f"Producto con id={product_id} no encontrado")

    def reactivate(self, product_id: int) -> None:
        """Reactivate a product by setting is_active = 1.

        Raises:
            DataError: If the product is not found or already active.
        """
        result = self._db.execute(
            "UPDATE products SET is_active = 1, updated_at = datetime('now') WHERE id = ? AND is_active = 0",
            (product_id,),
        )
        if result.rowcount == 0:
            raise DataError(f"Producto con id={product_id} no encontrado o ya está activo")

    def hard_delete(self, product_id: int) -> None:
        """Permanently delete a product from the database.

        Only allowed if the product has no transaction history.

        Raises:
            DataError: If the product has transaction history or is not found.
        """
        # Check for transaction history
        sales = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM sale_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        purchases = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM purchase_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        returns = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM returns WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        if sales > 0 or purchases > 0 or returns > 0:
            raise DataError(
                "No se puede eliminar permanentemente: el producto tiene historial de transacciones. "
                "Use la opción 'Desactivar' en su lugar."
            )
        
        # Perform hard delete
        result = self._db.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,),
        )
        if result.rowcount == 0:
            raise DataError(f"Producto con id={product_id} no encontrado")

    def smart_delete(self, product_id: int) -> str:
        """Intelligently delete a product based on transaction history.
        
        If the product has NO transaction history: performs hard delete (DELETE).
        If the product HAS transaction history: performs soft delete (UPDATE is_active = 0).
        
        Returns:
            str: "hard_deleted" if physically removed, "soft_deleted" if deactivated.
        
        Raises:
            DataError: If the product is not found.
        """
        # Check for transaction history
        sales = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM sale_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        purchases = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM purchase_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        returns = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM returns WHERE product_id = ?",
            (product_id,),
        ).fetchone()["cnt"]
        
        has_history = sales > 0 or purchases > 0 or returns > 0
        
        if has_history:
            # Soft delete
            result = self._db.execute(
                "UPDATE products SET is_active = 0, updated_at = datetime('now') WHERE id = ? AND is_active = 1",
                (product_id,),
            )
            if result.rowcount == 0:
                raise DataError(f"Producto con id={product_id} no encontrado")
            return "soft_deleted"
        else:
            # Hard delete
            result = self._db.execute(
                "DELETE FROM products WHERE id = ?",
                (product_id,),
            )
            if result.rowcount == 0:
                raise DataError(f"Producto con id={product_id} no encontrado")
            return "hard_deleted"

    def smart_delete_batch(self, product_ids: list[int]) -> dict:
        """Intelligently delete multiple products based on transaction history.
        
        For each product:
        - If NO transaction history: performs hard delete (DELETE).
        - If HAS transaction history: performs soft delete (UPDATE is_active = 0).
        
        Args:
            product_ids: List of product IDs to delete.
        
        Returns:
            dict: {"hard_deleted": int, "soft_deleted": int, "errors": list[str]}
        """
        result = {
            "hard_deleted": 0,
            "soft_deleted": 0,
            "errors": []
        }
        
        for product_id in product_ids:
            try:
                action = self.smart_delete(product_id)
                if action == "hard_deleted":
                    result["hard_deleted"] += 1
                else:
                    result["soft_deleted"] += 1
            except DataError as e:
                result["errors"].append(f"Producto ID {product_id}: {str(e)}")
        
        return result

    # ----------------------------------------------------------- stock ----

    def update_stock(self, product_id: int, new_stock: float) -> None:
        """Set the stock for a product to an absolute value.

        Called by ``StockService.deduct_without_transaction()`` during
        sale atomicity — the caller manages the transaction boundary.

        Args:
            product_id: The product to update.
            new_stock:   The new stock value (may be negative).
        """
        self._db.execute(
            """UPDATE products
               SET stock = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (new_stock, product_id),
        )

    # --------------------------------------------------------------- upsert

    def upsert_from_import(self, product: Product) -> tuple[Product, str]:
        """Insert or selectively update a product from an Excel import.

        - Barcode is NOT in DB → full INSERT (returns ``(product, "created")``).
        - Barcode IS in DB     → UPDATE price, cost, stock, name,
          category_id, and reactivate (is_active = 1).
          Returns ``(product, "updated")``.

        Returns:
            Tuple of ``(Product, action)`` where *action* is ``"created"`` or ``"updated"``.
        """
        existing = self._db.execute(
            "SELECT id FROM products WHERE barcode = ?", (product.barcode,)
        ).fetchone()

        if existing:
            self._db.execute(
                """UPDATE products
                   SET sale_price = ?, cost_price = ?, stock = ?,
                       name = ?, category_id = ?,
                       is_active = 1, updated_at = datetime('now')
                   WHERE barcode = ?""",
                (product.sale_price, product.cost_price, product.stock,
                 product.name, product.category_id, product.barcode),
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
            description=row["description"],
            low_stock_threshold=row["low_stock_threshold"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
