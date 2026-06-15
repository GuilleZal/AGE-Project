"""Product controller — CRUD orchestration with validation and Excel import.

Every method catches ``POSException`` and returns a uniform result dict
with ``success``, ``data``, and ``error`` keys for view consumption.
"""

import sqlite3

from pos.model.exceptions import POSException
from pos.model.product import Product, Category
from pos.repository.product_repo import ProductRepo
from pos.repository.category_repo import CategoryRepo


class ProductController:
    """Orchestrates product and category CRUD operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._product_repo = ProductRepo(db)
        self._category_repo = CategoryRepo(db)

    # --------------------------------------------------------------- product CRUD

    def create_product(self, data: dict) -> dict:
        """Create a new product with validation.

        Required keys: ``name``, ``sale_price``, ``cost_price``, ``unit_type``.
        Optional: ``barcode``, ``category_id``, ``stock``, ``description``, ``low_stock_threshold``.

        Returns ``{"success": True, "data": Product, "error": None}`` or error dict.
        """
        try:
            _validate_product_data(data)
        except ValueError as e:
            return {"success": False, "data": None, "error": str(e)}

        try:
            product = Product(
                barcode=data.get("barcode"),
                name=data["name"],
                category_id=data.get("category_id"),
                sale_price=int(data["sale_price"]),
                cost_price=int(data["cost_price"]),
                stock=float(data.get("stock", 0)),
                unit_type=data.get("unit_type", "unit"),
                description=data.get("description"),
                low_stock_threshold=float(data.get("low_stock_threshold", 5)),
            )
            created = self._product_repo.create(product)
            return {"success": True, "data": created, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def update_product(self, product_id: int, data: dict) -> dict:
        """Update an existing product.

        Only the keys present in *data* are modified.  The existing product
        is fetched first and merged with *data* before persisting.
        """
        try:
            existing = self._product_repo.find_by_id(product_id)
            if existing is None:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Producto con id={product_id} no encontrado",
                }

            # Merge fields — only override keys present in data
            if "barcode" in data:
                existing.barcode = data["barcode"]
            if "name" in data and data["name"] is not None:
                existing.name = data["name"]
            if "category_id" in data:
                existing.category_id = data["category_id"]
            if "sale_price" in data:
                existing.sale_price = int(data["sale_price"])
            if "cost_price" in data:
                existing.cost_price = int(data["cost_price"])
            if "stock" in data:
                existing.stock = float(data["stock"])
            if "unit_type" in data:
                existing.unit_type = data["unit_type"]
            if "description" in data:
                existing.description = data["description"]
            if "low_stock_threshold" in data:
                existing.low_stock_threshold = float(data["low_stock_threshold"])

            updated = self._product_repo.update(existing)
            return {"success": True, "data": updated, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def delete_product(self, product_id: int) -> dict:
        """Delete a product (blocked if it has transaction history).

        Returns ``{"success": True, "data": None, "error": None}``
        or ``{"success": False, "data": None, "error": message}``.
        """
        try:
            self._product_repo.delete(product_id)
            return {"success": True, "data": None, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_product(self, product_id: int) -> dict:
        """Return a single product by ID."""
        try:
            product = self._product_repo.find_by_id(product_id)
            if product is None:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Producto con id={product_id} no encontrado",
                }
            return {"success": True, "data": product, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_products(self, filters: dict | None = None) -> dict:
        """List products, optionally filtered.

        Supported *filters* keys:
            ``search`` — searches by barcode, name, or category name
            ``category_id`` — exact category match
            ``low_stock`` — bool, only products at/below threshold
        """
        try:
            if filters and filters.get("search"):
                products = self._product_repo.search_unified(filters["search"])
            else:
                products = self._product_repo.get_all()

            # Apply additional filters in-memory (simple for MVP)
            if filters:
                if filters.get("category_id"):
                    products = [p for p in products if p.category_id == filters["category_id"]]
                if filters.get("low_stock"):
                    products = [p for p in products if p.stock <= p.low_stock_threshold]

            return {"success": True, "data": products, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # -------------------------------------------------------------- category CRUD

    def create_category(self, name: str) -> dict:
        """Create a new category.

        Returns ``{"success": True, "data": Category, "error": None}``.
        """
        try:
            cat = self._category_repo.create(name)
            return {"success": True, "data": cat, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_categories(self) -> dict:
        """Return all categories with product counts."""
        try:
            cats = self._category_repo.get_all()
            return {"success": True, "data": cats, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    # ----------------------------------------------------------- Excel import ---

    def import_from_excel(self, file_path: str) -> dict:
        """Import products from an Excel (.xlsx) file using upsert logic.

        This method opens the Excel file, validates each row, then calls
        ``ExcelImportController.execute_import`` for the transactional upsert.

        Returns ``{"success": True, "data": {created, updated, errors}, "error": None}``.
        """
        from pos.controller.excel_import_controller import ExcelImportController

        importer = ExcelImportController(self._db)
        result = importer.execute_import(file_path)
        return result

    def generate_template(self, file_path: str) -> dict:
        """Generate an empty Excel template with the correct column headers.

        Columns: barcode, name, sale_price, cost_price, stock, unit_type.

        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Productos"
            ws.append(["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"])

            # Add a sample row as hint
            ws.append(["7790000000001", "Ejemplo", 100, 60, 10, "unit"])

            wb.save(file_path)
            return {"success": True, "data": file_path, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": f"Error al generar plantilla: {e}"}


# --------------------------------------------------------------- helpers ---

def _validate_product_data(data: dict) -> None:
    """Raise ``ValueError`` with a user-friendly message if required fields are invalid."""
    if not data.get("name", "").strip():
        raise ValueError("El nombre del producto es obligatorio")
    if int(data.get("sale_price", -1)) < 0:
        raise ValueError("El precio de venta no puede ser negativo")
    if int(data.get("cost_price", -1)) < 0:
        raise ValueError("El precio de costo no puede ser negativo")
    unit_type = data.get("unit_type", "unit")
    if unit_type not in ("unit", "weight_kg", "pack"):
        raise ValueError(f"Tipo de unidad no válido: {unit_type}. Valores permitidos: unit, weight_kg, pack")
