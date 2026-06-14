"""Tests for CategoryRepo — CRUD, product-count validation, and queries."""

import pytest

from pos.model.exceptions import DataError
from pos.repository.category_repo import CategoryRepo


class TestCreate:
    def test_success(self, db):
        repo = CategoryRepo(db)
        cat = repo.create("Vinos")
        assert cat.id is not None
        assert cat.name == "Vinos"
        assert cat.created_at is not None

    def test_duplicate_name(self, db):
        repo = CategoryRepo(db)
        repo.create("Única")
        with pytest.raises(DataError, match="ya existe"):
            repo.create("Única")

    def test_duplicate_case(self, db):
        """SQLite UNIQUE is case-sensitive for TEXT by default."""
        repo = CategoryRepo(db)
        repo.create("Categoria")
        # "categoria" (lowercase) is different from "Categoria" in SQLite
        cat = repo.create("categoria")
        assert cat.id is not None


class TestUpdate:
    def test_success(self, db):
        repo = CategoryRepo(db)
        cat = repo.create("Original")
        updated = repo.update(cat.id, "Renamed")
        assert updated.name == "Renamed"
        assert updated.id == cat.id

    def test_not_found(self, db):
        repo = CategoryRepo(db)
        with pytest.raises(DataError, match="no encontrada"):
            repo.update(99999, "Ghost")

    def test_duplicate_name(self, db):
        repo = CategoryRepo(db)
        repo.create("First")
        second = repo.create("Second")
        with pytest.raises(DataError, match="ya existe"):
            repo.update(second.id, "First")


class TestDelete:
    def test_success(self, db):
        repo = CategoryRepo(db)
        cat = repo.create("Para Borrar")
        repo.delete(cat.id)
        assert repo.find_by_id(cat.id) is None

    def test_with_products_blocks(self, db, sample_products, sample_category):
        repo = CategoryRepo(db)
        bebidas_id = sample_category[0]
        with pytest.raises(DataError, match="productos asociados"):
            repo.delete(bebidas_id)

    def test_no_products_allows(self, db, sample_category):
        repo = CategoryRepo(db)
        snacks_id = sample_category[1]
        # Remove all snack products first
        db.execute("DELETE FROM products WHERE category_id = ?", (snacks_id,))
        db.commit()
        # Now deletion should succeed
        repo.delete(snacks_id)
        assert repo.find_by_id(snacks_id) is None


class TestCountProducts:
    def test_returns_count(self, db, sample_products, sample_category):
        repo = CategoryRepo(db)
        bebidas_id = sample_category[0]
        # In conftest: Coca-Cola, Fernet, Six-Pack all use bebidas
        assert repo.count_products(bebidas_id) == 3

    def test_empty_category(self, db, sample_category):
        """Category with no products (sample_products fixture not used)."""
        repo = CategoryRepo(db)
        snacks_id = sample_category[1]
        assert repo.count_products(snacks_id) == 0

    def test_category_with_products(self, db, sample_products, sample_category):
        """Snacks has Queso Cremoso and Maní = 2 products."""
        repo = CategoryRepo(db)
        snacks_id = sample_category[1]
        assert repo.count_products(snacks_id) == 2

    def test_nonexistent_category(self, db):
        repo = CategoryRepo(db)
        assert repo.count_products(99999) == 0


class TestGetAll:
    def test_returns_with_counts(self, db, sample_products, sample_category):
        repo = CategoryRepo(db)
        rows = repo.get_all()
        assert len(rows) == 2
        # Find the bebidas row
        bebidas = next(r for r in rows if r["name"] == "Bebidas")
        assert bebidas["product_count"] == 3
        snacks = next(r for r in rows if r["name"] == "Snacks")
        assert snacks["product_count"] == 2

    def test_empty_db(self, db):
        repo = CategoryRepo(db)
        assert repo.get_all() == []


class TestFindBy:
    def test_find_by_id_found(self, db, sample_category):
        repo = CategoryRepo(db)
        cat = repo.find_by_id(sample_category[0])
        assert cat is not None
        assert cat.name == "Bebidas"

    def test_find_by_id_not_found(self, db):
        repo = CategoryRepo(db)
        assert repo.find_by_id(99999) is None

    def test_find_by_name_found(self, db, sample_category):
        repo = CategoryRepo(db)
        cat = repo.find_by_name("Snacks")
        assert cat is not None
        assert cat.id == sample_category[1]

    def test_find_by_name_not_found(self, db):
        repo = CategoryRepo(db)
        assert repo.find_by_name("Nonexistent") is None
