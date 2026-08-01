"""Cash-movement repository — track inflows/outflows within a register session.

Movements are auto-generated (``sale_cash`` on sales, ``return`` on returns) or
manually registered (``supplier_payment``, ``expense``).
"""

import sqlite3

from pos.model.cash_register import CashMovement
from pos.model.enums import MovementType


class CashMovementRepo:
    """Data-access for the ``cash_movements`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ----------------------------------------------------------------- create

    def create(
        self,
        register_id: int,
        type_: MovementType | str,
        amount: int,
        description: str | None = None,
    ) -> CashMovement:
        """Insert a single cash movement.

        Args:
            register_id: The active cash register.
            type_:       One of ``sale_cash``, ``return``, ``supplier_payment``, ``expense``.
            amount:      Whole ARS pesos (positive for inflows, negative conceptually
                         but stored as positive int by convention — the type signals direction).
            description: Optional note.
        """
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mt = type_.value if isinstance(type_, MovementType) else type_
        cur = self._db.execute(
            """INSERT INTO cash_movements (cash_register_id, type, amount, description, created_at)
               VALUES (?, ?, ?, ?, ?)
               RETURNING id, created_at""",
            (register_id, mt, amount, description, now),
        )
        row = cur.fetchone()
        return CashMovement(
            id=row["id"],
            cash_register_id=register_id,
            type=mt,
            amount=amount,
            description=description,
            created_at=row["created_at"],
        )

    # --------------------------------------------------------------- sums --

    def sum_by_type(self, register_id: int, type_: str) -> int:
        """Return the total amount for movements of *type_* in *register_id*."""
        row = self._db.execute(
            """SELECT COALESCE(SUM(amount), 0) AS total
               FROM cash_movements
               WHERE cash_register_id = ? AND type = ?""",
            (register_id, type_),
        ).fetchone()
        return row["total"]

    # ---------------------------------------------------------------- read

    def get_by_register(self, register_id: int) -> list[CashMovement]:
        """Return all movements for *register_id*, ordered by time."""
        rows = self._db.execute(
            "SELECT * FROM cash_movements WHERE cash_register_id = ? ORDER BY created_at",
            (register_id,),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    # ----------------------------------------------------------- helpers ---

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CashMovement:
        return CashMovement(
            id=row["id"],
            cash_register_id=row["cash_register_id"],
            type=row["type"],
            amount=row["amount"],
            description=row["description"],
            created_at=row["created_at"],
        )
