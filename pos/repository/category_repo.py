"""Category repository — CRUD with uniqueness validation and product counts.

All queries are parameterized. ``DataError`` is raised on integrity violations.
"""

import sqlite3

from pos.model.product import Category
from pos.model.exceptions import DataError


class CategoryRepo:
    """Data-access for the ``categories`` table."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    # ----------------------------------------------------------------- create

    def create(self, name: str) -> Category:
        """Create a new category.

        Raises:
            DataError: If the category name already exists.
        """
        try:
            cur = self._db.execute(
                "INSERT INTO categories (name) VALUES (?) RETURNING id, created_at",
                (name,),
            )
            row = cur.fetchone()
            return Category(id=row["id"], name=name, created_at=row["created_at"])
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DataError(f"La categoría '{name}' ya existe") from e
            raise DataError(str(e)) from e

    # ----------------------------------------------------------------- update

    def update(self, category_id: int, name: str) -> Category:
        """Rename a category.

        Raises:
            DataError: If category not found or name conflict.
        """
        try:
            cur = self._db.execute(
                "UPDATE categories SET name = ? WHERE id = ? RETURNING created_at",
                (name, category_id),
            )
            row = cur.fetchone()
            if row is None:
                raise DataError(f"Categoría con id={category_id} no encontrada")
            return Category(id=category_id, name=name, created_at=row["created_at"])
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise DataError(f"La categoría '{name}' ya existe") from e
            raise DataError(str(e)) from e

    # ----------------------------------------------------------------- delete

    def delete(self, category_id: int) -> None:
        """Delete a category and set associated products to 'Sin categoría' (NULL)."""
        self._db.execute("UPDATE products SET category_id = NULL WHERE category_id = ?", (category_id,))
        self._db.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    # -------------------------------------------------------------- queries

    def count_products(self, category_id: int) -> int:
        """Return the number of active products belonging to this category."""
        row = self._db.execute(
            "SELECT COUNT(*) AS cnt FROM products WHERE category_id = ? AND is_active = 1",
            (category_id,),
        ).fetchone()
        return row["cnt"]

    def get_all(self) -> list[dict]:
        """Return every category with its product count.

        Returns:
            List of dicts with keys: ``id``, ``name``, ``created_at``, ``product_count``.
        """
        rows = self._db.execute(
            """SELECT c.id, c.name, c.created_at,
                      COALESCE(p.cnt, 0) AS product_count
               FROM categories c
               LEFT JOIN (
                   SELECT category_id, COUNT(*) AS cnt
                   FROM products
                   WHERE is_active = 1
                   GROUP BY category_id
               ) p ON p.category_id = c.id
               ORDER BY c.name"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------- helpers ---

    def find_by_id(self, category_id: int) -> Category | None:
        """Return the category with *category_id*, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        if row is None:
            return None
        return Category(id=row["id"], name=row["name"], created_at=row["created_at"])

    def find_by_name(self, name: str) -> Category | None:
        """Return the category with *name*, or ``None``."""
        row = self._db.execute(
            "SELECT * FROM categories WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return Category(id=row["id"], name=row["name"], created_at=row["created_at"])
