"""Product controller — CRUD orchestration with validation and Excel import.

Every method catches ``POSException`` and returns a uniform result dict
with ``success``, ``data``, and ``error`` keys for view consumption.
"""

import sqlite3

from pos.model.exceptions import POSException
from pos.model.product import Product, Category
from pos.repository.product_repo import ProductRepo
from pos.repository.category_repo import CategoryRepo
from pos.service.settings_service import SettingsService


class ProductController:
    """Orchestrates product and category CRUD operations."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db
        self._product_repo = ProductRepo(db)
        self._category_repo = CategoryRepo(db)
        self._settings_service = SettingsService(db)

    # --------------------------------------------------------------- product CRUD

    def create_product(self, data: dict) -> dict:
        """Create a new product with validation.

        Required keys: ``name``, ``sale_price``, ``cost_price``.
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
                unit_type=data.get("unit_type", "Unidad"),
                description=data.get("description"),
                low_stock_threshold=int(data.get("low_stock_threshold", 5)),
            )
            created = self._product_repo.create(product)
            self._db.commit()
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
                val = int(data["sale_price"])
                if val < 0:
                    raise ValueError("El precio de venta no puede ser negativo")
                existing.sale_price = val
            if "cost_price" in data:
                val = int(data["cost_price"])
                if val < 0:
                    raise ValueError("El precio de costo no puede ser negativo")
                existing.cost_price = val
            if "stock" in data:
                val = float(data["stock"])
                if val < 0:
                    raise ValueError("El stock no puede ser negativo")
                if data.get("unit_type", existing.unit_type) == "Kg":
                    val = round(val, 3)
                existing.stock = val
            if "unit_type" in data:
                existing.unit_type = data["unit_type"]
            if "description" in data:
                existing.description = data["description"]
            if "low_stock_threshold" in data:
                existing.low_stock_threshold = int(data["low_stock_threshold"])

            updated = self._product_repo.update(existing)
            self._db.commit()
            return {"success": True, "data": updated, "error": None}
        except (POSException, ValueError) as e:
            return {"success": False, "data": None, "error": str(e)}

    def delete_product(self, product_id: int) -> dict:
        """Soft delete a product by setting is_active = 0.

        Returns ``{"success": True, "data": None, "error": None}``
        or ``{"success": False, "data": None, "error": message}``.
        """
        try:
            self._product_repo.delete(product_id)
            self._db.commit()
            return {"success": True, "data": None, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def reactivate_product(self, product_id: int) -> dict:
        """Reactivate a product by setting is_active = 1.

        Returns ``{"success": True, "data": None, "error": None}``
        or ``{"success": False, "data": None, "error": message}``.
        """
        try:
            self._product_repo.reactivate(product_id)
            self._db.commit()
            return {"success": True, "data": None, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def hard_delete_product(self, product_id: int) -> dict:
        """Permanently delete a product from the database.

        Only allowed if the product has no transaction history.

        Returns ``{"success": True, "data": None, "error": None}``
        or ``{"success": False, "data": None, "error": message}``.
        """
        try:
            self._product_repo.hard_delete(product_id)
            self._db.commit()
            return {"success": True, "data": None, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def smart_delete_products(self, product_ids: list[int]) -> dict:
        """Intelligently delete multiple products based on transaction history.
        
        For each product:
        - If NO transaction history: performs hard delete (DELETE).
        - If HAS transaction history: performs soft delete (UPDATE is_active = 0).
        
        Args:
            product_ids: List of product IDs to delete.
        
        Returns:
            dict: {"success": True, "data": {"hard_deleted": int, "soft_deleted": int, "errors": list}, "error": None}
            or {"success": False, "data": None, "error": message}.
        """
        try:
            result = self._product_repo.smart_delete_batch(product_ids)
            self._db.commit()
            return {"success": True, "data": result, "error": None}
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
            ``include_inactive`` — bool, include inactive products
            ``barcode`` — search by barcode (partial match)
        """
        try:
            if filters and filters.get("search"):
                products = self._product_repo.search_unified(filters["search"])
            else:
                if filters and filters.get("include_inactive"):
                    products = self._product_repo.get_all_with_inactive()
                else:
                    products = self._product_repo.get_all()

            # Apply additional filters in-memory (simple for MVP)
            if filters:
                if filters.get("category_id"):
                    products = [p for p in products if p.category_id == filters["category_id"]]
                if filters.get("low_stock"):
                    products = [p for p in products if p.stock <= p.low_stock_threshold]
                if filters.get("barcode"):
                    barcode_query = filters["barcode"].strip().lower()
                    products = [p for p in products if p.barcode and barcode_query in p.barcode.lower()]

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
            self._db.commit()
            return {"success": True, "data": cat, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def update_category(self, category_id: int, name: str) -> dict:
        """Rename an existing category.

        Returns ``{"success": True, "data": Category, "error": None}``.
        """
        try:
            cat = self._category_repo.update(category_id, name)
            self._db.commit()
            return {"success": True, "data": cat, "error": None}
        except POSException as e:
            return {"success": False, "data": None, "error": str(e)}

    def delete_category(self, category_id: int) -> dict:
        """Delete a category (only if no products use it).

        Returns ``{"success": True, "data": None, "error": None}``.
        """
        try:
            self._category_repo.delete(category_id)
            self._db.commit()
            return {"success": True, "data": None, "error": None}
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

    def export_products_to_excel(self, file_path: str) -> dict:
        """Export all products to an Excel (.xlsx) file.
        
        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            import openpyxl
            products = self._product_repo.get_all()
            cats = {c["id"]: c["name"] for c in self._category_repo.get_all()}
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Productos"
            ws.append(["Código", "Nombre", "Categoría", "Precio Costo", "Precio Venta", "Margen %", "Stock", "Unidad"])
            
            for p in products:
                cat_name = cats.get(p.category_id, "")
                margin = 0.0
                if p.cost_price > 0:
                    margin = ((p.sale_price - p.cost_price) / p.cost_price) * 100
                ws.append([
                    p.barcode or "",
                    p.name,
                    cat_name,
                    p.cost_price,
                    p.sale_price,
                    round(margin, 2),
                    p.stock,
                    getattr(p, "unit_type", "Unidad")
                ])
            wb.save(file_path)
            return {"success": True, "data": file_path, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": f"Error al exportar: {e}"}

    def generate_template(self, file_path: str) -> dict:
        """Generate an empty Excel template with the correct column headers.

        Columns: codigo, nombre, categoria, precio_venta, precio_costo, stock.

        Returns ``{"success": True, "data": file_path, "error": None}``.
        """
        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Productos"
            ws.append(["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock"])

            # Add a sample row as hint
            ws.append(["7790000000001", "Ejemplo", "General", 100, 60, 10])

            wb.save(file_path)
            return {"success": True, "data": file_path, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": f"Error al generar plantilla: {e}"}

    # --------------------------------------------------------------- settings

    def get_settings(self) -> dict:
        """Return all global settings.

        Returns ``{"success": True, "data": {low_stock_threshold, profit_margin_pct}, "error": None}``.
        """
        try:
            settings = self._settings_service.get_all()
            return {"success": True, "data": settings, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def apply_settings(
        self,
        low_stock_threshold: int | None = None,
        profit_margin_pct: float | None = None,
        apply_to_products: bool = False,
        threshold_category_id: int | None = None,
        margin_category_id: int | None = None,
    ) -> dict:
        """Apply global settings and optionally update products.

        Args:
            low_stock_threshold: New global low-stock threshold (or None to skip).
            profit_margin_pct: New global profit margin % (or None to skip).
            apply_to_products: If True, update products with the new values.
            threshold_category_id: If provided, apply threshold only to this category.
            margin_category_id: If provided, apply margin only to this category.

        Returns ``{"success": True, "data": {products_updated}, "error": None}``.
        """
        try:
            products_updated = 0

            if low_stock_threshold is not None:
                if low_stock_threshold < 0:
                    raise ValueError("El umbral de stock bajo no puede ser negativo")
                self._settings_service.set_low_stock_threshold(low_stock_threshold)
                if apply_to_products:
                    products_updated += self._settings_service.apply_low_stock_threshold(
                        low_stock_threshold, threshold_category_id
                    )

            if profit_margin_pct is not None:
                if profit_margin_pct < 0:
                    raise ValueError("El porcentaje de ganancia no puede ser negativo")
                if profit_margin_pct >= 100:
                    raise ValueError("El porcentaje de ganancia debe ser menor a 100%")
                self._settings_service.set_profit_margin_pct(profit_margin_pct)
                if apply_to_products:
                    products_updated += self._settings_service.apply_profit_margin(
                        profit_margin_pct, margin_category_id
                    )

            self._db.commit()
            return {"success": True, "data": {"products_updated": products_updated}, "error": None}
        except ValueError as e:
            self._db.rollback()
            return {"success": False, "data": None, "error": str(e)}
        except Exception as e:
            self._db.rollback()
            return {"success": False, "data": None, "error": str(e)}


# --------------------------------------------------------------- helpers ---

def _validate_product_data(data: dict) -> None:
    """Raise ``ValueError`` with a user-friendly message if required fields are invalid."""
    if not data.get("name", "").strip():
        raise ValueError("El nombre del producto es obligatorio")
    if int(data.get("sale_price", -1)) < 0:
        raise ValueError("El precio de venta no puede ser negativo")
    if int(data.get("cost_price", -1)) < 0:
        raise ValueError("El precio de costo no puede ser negativo")
    if "stock" in data:
        try:
            st = float(data["stock"])
        except (ValueError, TypeError):
            raise ValueError("El stock debe ser un número válido")
        if st < 0:
            raise ValueError("El stock no puede ser negativo")
