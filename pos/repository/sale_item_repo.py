"""Sale-item repository — batch insertion of line items.

The calling code (controller/service) is responsible for wrapping
``create_batch`` in an explicit ``BEGIN … COMMIT`` transaction when needed.
"""

import sqlite3

from pos.model.sale import SaleItem


class SaleItemRepo:
    """Data-access for the ``sale_items`` table.

    Cascade delete is handled by the DB schema (``ON DELETE CASCADE`` on
    ``sale_id``), so no explicit cascade logic is needed here.
    """

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # --------------------------------------------------------------- batch

    def create_batch(self, sale_id: int, items: list[SaleItem]) -> list[SaleItem]:
        """Insert multiple sale-items for a single sale.

        Each item gets its ``id`` and ``sale_id`` populated in-place.

        Returns the same list (mutated) for convenience.
        """
        for item in items:
            cur = self._db.execute(
                """INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal)
                   VALUES (?, ?, ?, ?, ?)
                   RETURNING id""",
                (sale_id, item.product_id, item.quantity, item.unit_price, item.subtotal),
            )
            item.id = cur.fetchone()["id"]
            item.sale_id = sale_id
        return items

    # ---------------------------------------------------------------- read

    def get_by_sale(self, sale_id: int) -> list[SaleItem]:
        """Return all line items belonging to *sale_id*, ordered by id."""
        rows = self._db.execute(
            "SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id",
            (sale_id,),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    # ----------------------------------------------------------- helpers ---

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SaleItem:
        return SaleItem(
            id=row["id"],
            sale_id=row["sale_id"],
            product_id=row["product_id"],
            quantity=row["quantity"],
            unit_price=row["unit_price"],
            subtotal=row["subtotal"],
        )
