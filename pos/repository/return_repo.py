"""Return repository — atomic returns with cash-register linkage.

No foreign key to the original sale (atomic return model).
``cash_register_id`` provides the audit trail.
"""

import sqlite3

from pos.model.return_ import Return


class ReturnRepo:
    """Data-access for the ``returns`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ----------------------------------------------------------------- create

    def create(self, return_: Return) -> Return:
        """Insert a return record.

        Returns the same object with ``id`` and ``created_at`` populated.
        """
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self._db.execute(
            """INSERT INTO returns
               (product_id, quantity, refund_amount, reason, cash_register_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               RETURNING id, created_at""",
            (
                return_.product_id,
                return_.quantity,
                return_.refund_amount,
                return_.reason,
                return_.cash_register_id,
                now,
            ),
        )
        row = cur.fetchone()
        return_.id = row["id"]
        return_.created_at = row["created_at"]
        return return_

    # ---------------------------------------------------------------- read

    def get_by_date(self, start_date: str, end_date: str) -> list[Return]:
        """Return all returns within a date range, most-recent first."""
        rows = self._db.execute(
            """SELECT * FROM returns
               WHERE created_at >= ? AND created_at <= ?
               ORDER BY created_at DESC""",
            (start_date, end_date),
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def get_all(self) -> list[Return]:
        """Return every return record, most-recent first."""
        rows = self._db.execute(
            "SELECT * FROM returns ORDER BY created_at DESC"
        ).fetchall()
        return [self._from_row(r) for r in rows]

    # ----------------------------------------------------------- helpers ---

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Return:
        return Return(
            id=row["id"],
            product_id=row["product_id"],
            quantity=row["quantity"],
            refund_amount=row["refund_amount"],
            reason=row["reason"],
            cash_register_id=row["cash_register_id"],
            created_at=row["created_at"],
        )
