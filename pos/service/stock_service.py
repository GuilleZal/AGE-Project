"""Stock service — deduct and restore stock with transaction safety.

Key principle: **never block a sale due to insufficient stock**.
Stock is allowed to go negative — this is an admin visibility metric,
not a sales gate.
"""

import sqlite3

from pos.model.exceptions import DataError
from pos.model.sale import SaleItem
from pos.model.product import Product
from pos.repository.product_repo import ProductRepo


class StockService:
    """Business logic for stock management.

    Wraps a ``ProductRepo`` for data access. All write operations that
    affect multiple products are executed inside a single transaction.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._repo = ProductRepo(db)

    # ---------------------------------------------------------------- deduct

    def deduct(self, items: list[SaleItem]) -> None:
        """Reduce stock for each sale item inside a transaction.

        Never raises ``BusinessError`` for insufficient stock — the system
        allows negative stock per the domain policy.

        Raises:
            DataError: If a ``product_id`` does not exist in the database.
        """
        if not items:
            return

        try:
            self._db.execute("BEGIN")
            self._deduct_impl(items)
            self._db.execute("COMMIT")
        except Exception:
            self._db.execute("ROLLBACK")
            raise

    def deduct_without_transaction(self, items: list[SaleItem]) -> None:
        """Deduct stock without managing the transaction boundary.

        The **caller** is responsible for ``BEGIN`` / ``COMMIT`` /
        ``ROLLBACK``.  This method only performs the data updates so it
        can participate in a larger atomic operation (e.g. a complete sale
        that also persists the sale record and cash movement).

        Args:
            items: Sale items whose stock must be reduced.

        Raises:
            DataError: If a ``product_id`` does not exist in the database.
        """
        if not items:
            return
        self._deduct_impl(items)

    # --------------------------------------------------------- impl (shared)

    def _deduct_impl(self, items: list[SaleItem]) -> None:
        """Core stock deduction — no transaction management."""
        for item in items:
            product = self._repo.find_by_id(item.product_id)
            if product is None:
                raise DataError(
                    f"Producto con id={item.product_id} no encontrado"
                )
            if product.unit_type == "Kg":
                new_stock = round(float(product.stock - item.quantity), 3)
            else:
                new_stock = int(product.stock - item.quantity)
            self._repo.update_stock(item.product_id, new_stock)

    # --------------------------------------------------------------- restore

    def restore(self, product_id: int, quantity: int | float) -> None:
        """Increase stock for a single product (e.g. after a return).

        Args:
            product_id: The product to restore stock for.
            quantity:   Amount to add back (must be > 0).

        Raises:
            ValueError: If *quantity* ≤ 0 or *product_id* does not exist.
        """
        if quantity <= 0:
            raise ValueError("La cantidad a restaurar debe ser mayor a 0")

        product = self._repo.find_by_id(product_id)
        if product is None:
            raise ValueError(
                f"Producto con id={product_id} no encontrado"
            )

        if product.unit_type == "Kg":
            self._db.execute(
                """UPDATE products
                   SET stock = round(CAST(stock + ? AS REAL), 3), updated_at = datetime('now')
                   WHERE id = ?""",
                (quantity, product_id),
            )
        else:
            self._db.execute(
                """UPDATE products
                   SET stock = CAST(stock + ? AS INTEGER), updated_at = datetime('now')
                   WHERE id = ?""",
                (quantity, product_id),
            )

    # ------------------------------------------------------- low stock ----

    def low_stock_products(self, threshold: int | None = None) -> list[Product]:
        """Return all products whose current stock is at or below *threshold*.

        When *threshold* is ``None`` each product is compared against its
        own ``low_stock_threshold`` field.

        Args:
            threshold: Optional absolute threshold. Defaults to per-product setting.

        Returns:
            Products with ``stock <= threshold``, ordered by stock ascending.
        """
        if threshold is not None:
            rows = self._db.execute(
                """SELECT * FROM products
                   WHERE stock <= ?
                   ORDER BY stock ASC""",
                (threshold,),
            ).fetchall()
        else:
            rows = self._db.execute(
                """SELECT * FROM products
                   WHERE stock <= low_stock_threshold
                   ORDER BY stock ASC""",
            ).fetchall()

        return [self._repo._from_row(r) for r in rows]
