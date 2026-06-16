"""Tests for ExcelImportController — validation, preview, and transactional import."""
import pytest
import sqlite3
import openpyxl
from pos.controller.excel_import_controller import ExcelImportController


@pytest.fixture
def excel_ctrl(db: sqlite3.Connection) -> ExcelImportController:
    return ExcelImportController(db)


def _create_xlsx(path: str, rows: list[list]) -> None:
    """Helper: create a minimal .xlsx file with data rows (including header)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    wb.save(path)


class TestValidateExcel:
    """Header and row validation."""

    def test_valid_file(self, excel_ctrl, tmp_path):
        path = tmp_path / "valid.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "Producto A", "General", 500, 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert result["success"] is True
        assert len(result["data"]["valid_rows"]) == 1
        assert result["data"]["errors"] == []

    def test_wrong_headers_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "bad_headers.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["779", "X", 100, 50, 5, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert result["success"] is False
        assert "Encabezados" in result["error"]

    def test_missing_file(self, excel_ctrl):
        result = excel_ctrl.validate_excel("nonexistent.xlsx")
        assert result["success"] is False
        assert "no encontrado" in result["error"].lower()

    def test_invalid_price_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "bad_price.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "Malo", "General", -100, 50, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        # Validation should flag the row error
        assert len(result["data"]["errors"]) >= 1

    def test_invalid_unit_type_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "bad_unit.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "Malo", "General", 500, 300, 10, "litros"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1
        assert "litros" in str(result["data"]["errors"]).lower() or "inválido" in str(result["data"]["errors"]).lower()

    def test_empty_name_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "no_name.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "", "General", 500, 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1

    def test_non_numeric_price_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "text_price.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "Test", "General", "abc", 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1

    def test_non_numeric_stock_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "text_stock.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000001", "Test", "General", 500, 300, "mucho", "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1


class TestPreviewImport:
    """Import preview functionality."""

    def test_preview_first_rows(self, excel_ctrl, tmp_path):
        path = tmp_path / "preview.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["1", "P1", "General", 100, 50, 10, "unit"],
            ["2", "P2", "General", 200, 100, 20, "unit"],
            ["3", "P3", "General", 300, 150, 30, "weight_kg"],
        ])
        result = excel_ctrl.preview_import(str(path))
        assert result["success"] is True
        assert result["data"]["total_rows"] == 3
        assert len(result["data"]["rows"]) == 3  # all ≤ 10


class TestExecuteImport:
    """Transactional import execution."""

    def test_execute_import_creates_products(self, excel_ctrl, tmp_path):
        path = tmp_path / "import.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000100", "Nuevo A", "General", 500, 300, 20, "unit"],
            ["7790000000200", "Nuevo B", "General", 800, 500, 15, "weight_kg"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 2
        assert result["data"]["updated"] == 0
        assert result["data"]["errors"] == 0
        assert result["data"]["error_details"] == []

    def test_execute_import_updates_existing(self, excel_ctrl, tmp_path, sample_products):
        """Import should UPDATE existing products (by barcode)."""
        path = tmp_path / "update.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790895000782", "Coca-Cola Nueva", "Bebidas", 900, 550, 50, "unit"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["updated"] == 1

        # Name SHOULD be overwritten (upsert updates name)
        from pos.repository.product_repo import ProductRepo
        repo = ProductRepo(excel_ctrl._db)
        product = repo.find_by_barcode("7790895000782")
        assert product.name == "Coca-Cola Nueva"  # name updated
        assert product.sale_price == 900  # price updated
        assert product.stock == 50.0  # stock updated

    def test_execute_import_rollback_on_error(self, excel_ctrl, tmp_path):
        """Import with a duplicate barcode (should already exist from sample)."""
        path = tmp_path / "rollback.xlsx"
        # First row is valid new product, second row has the same barcode (intra-file duplicate)
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000300", "Bueno", "General", 500, 300, 10, "unit"],
            ["7790000000300", "Duplicado", "General", 600, 400, 20, "pack"],
        ])
        result = excel_ctrl.execute_import(str(path))
        # Both rows should be flagged as duplicates
        assert result["data"]["created"] == 0
        assert result["data"]["updated"] == 0
        assert result["data"]["errors"] >= 2

    def test_execute_import_skips_invalid_rows(self, excel_ctrl, tmp_path):
        path = tmp_path / "mixed.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000100", "Válido", "General", 500, 300, 10, "unit"],
            ["7790000000200", "Malo", "General", -100, 50, 5, "unit"],  # invalid price
            ["7790000000300", "Válido 2", "General", 800, 500, 15, "pack"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 2  # only the valid rows
        assert result["data"]["errors"] == 1  # one error row

    def test_execute_import_empty_file(self, excel_ctrl, tmp_path):
        path = tmp_path / "empty.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 0
        assert result["data"]["updated"] == 0

    def test_non_xlsx_format_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("barcode,name\n")
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is False
        assert "formato" in result["error"].lower()

    def test_get_import_result_no_import(self, excel_ctrl):
        result = excel_ctrl.get_import_result()
        assert result["success"] is False

    def test_get_import_result_after_import(self, excel_ctrl, tmp_path):
        path = tmp_path / "result.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000100", "Test", "General", 500, 300, 10, "unit"],
        ])
        excel_ctrl.execute_import(str(path))
        result = excel_ctrl.get_import_result()
        assert result["success"] is True
        assert result["data"]["created"] == 1

    def test_category_sanitization(self, excel_ctrl, tmp_path):
        """Test that category names are sanitized (trimmed and title-cased)."""
        path = tmp_path / "categories.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000100", "Product 1", "  bebidas  ", 500, 300, 10, "unit"],
            ["7790000000200", "Product 2", "BEBIDAS", 600, 400, 20, "unit"],
            ["7790000000300", "Product 3", "bebidas", 700, 500, 30, "unit"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 3
        
        # Verify all three products were assigned to the same category "Bebidas"
        from pos.repository.product_repo import ProductRepo
        from pos.repository.category_repo import CategoryRepo
        repo = ProductRepo(excel_ctrl._db)
        cat_repo = CategoryRepo(excel_ctrl._db)
        
        # Check that "Bebidas" category was created
        category = cat_repo.find_by_name("Bebidas")
        assert category is not None
        
        # Check that all products have the same category_id
        p1 = repo.find_by_barcode("7790000000100")
        p2 = repo.find_by_barcode("7790000000200")
        p3 = repo.find_by_barcode("7790000000300")
        assert p1.category_id == category.id
        assert p2.category_id == category.id
        assert p3.category_id == category.id

    def test_detailed_error_reporting(self, excel_ctrl, tmp_path):
        """Test that import provides detailed error reporting per row."""
        path = tmp_path / "errors.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "categoria", "precio_venta", "precio_costo", "stock", "tipo_unidad"],
            ["7790000000100", "Valid Product", "General", 500, 300, 10, "unit"],  # Valid
            ["7790000000200", "", "General", 600, 400, 20, "unit"],  # Invalid: empty name
            ["7790000000300", "Another Valid", "General", 700, 500, 30, "unit"],  # Valid
            ["7790000000400", "Bad Price", "General", -100, 400, 40, "unit"],  # Invalid: negative price
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 2  # Only valid rows
        assert result["data"]["errors"] == 2  # Two error rows
        
        # Check error details
        error_details = result["data"]["error_details"]
        assert len(error_details) == 2
        
        # Find errors by row number
        error_rows = {e["row"] for e in error_details}
        assert 3 in error_rows  # Row 3 (empty name)
        assert 5 in error_rows  # Row 5 (negative price)
