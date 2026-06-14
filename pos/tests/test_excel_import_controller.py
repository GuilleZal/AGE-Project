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
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "Producto A", 500, 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert result["success"] is True
        assert len(result["data"]["valid_rows"]) == 1
        assert result["data"]["errors"] == []

    def test_wrong_headers_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "bad_headers.xlsx"
        _create_xlsx(str(path), [
            ["codigo", "nombre", "precio", "costo", "stock", "tipo"],
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
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "Malo", -100, 50, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        # Validation should flag the row error
        assert len(result["data"]["errors"]) >= 1

    def test_invalid_unit_type_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "bad_unit.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "Malo", 500, 300, 10, "litros"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1
        assert "litros" in str(result["data"]["errors"]).lower() or "inválido" in str(result["data"]["errors"]).lower()

    def test_empty_name_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "no_name.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "", 500, 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1

    def test_non_numeric_price_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "text_price.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "Test", "abc", 300, 10, "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1

    def test_non_numeric_stock_rejected(self, excel_ctrl, tmp_path):
        path = tmp_path / "text_stock.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000001", "Test", 500, 300, "mucho", "unit"],
        ])
        result = excel_ctrl.validate_excel(str(path))
        assert len(result["data"]["errors"]) >= 1


class TestPreviewImport:
    """Import preview functionality."""

    def test_preview_first_rows(self, excel_ctrl, tmp_path):
        path = tmp_path / "preview.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["1", "P1", 100, 50, 10, "unit"],
            ["2", "P2", 200, 100, 20, "unit"],
            ["3", "P3", 300, 150, 30, "weight_kg"],
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
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000100", "Nuevo A", 500, 300, 20, "unit"],
            ["7790000000200", "Nuevo B", 800, 500, 15, "weight_kg"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 2
        assert result["data"]["updated"] == 0
        assert result["data"]["errors"] == []

    def test_execute_import_updates_existing(self, excel_ctrl, tmp_path, sample_products):
        """Import should UPDATE existing products (by barcode)."""
        path = tmp_path / "update.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790895000782", "Coca-Cola Nueva", 900, 550, 50, "unit"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["updated"] == 1

        # Name should NOT be overwritten (upsert preserves name)
        from pos.repository.product_repo import ProductRepo
        repo = ProductRepo(excel_ctrl._db)
        product = repo.find_by_barcode("7790895000782")
        assert product.name == "Coca-Cola 1.5L"  # original name preserved
        assert product.sale_price == 900  # price updated
        assert product.stock == 50.0  # stock updated

    def test_execute_import_rollback_on_error(self, excel_ctrl, tmp_path):
        """Import with a duplicate barcode (should already exist from sample)."""
        path = tmp_path / "rollback.xlsx"
        # First row is valid new product, second row has the same barcode (intra-file duplicate)
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000300", "Bueno", 500, 300, 10, "unit"],
            ["7790000000300", "Duplicado", 600, 400, 20, "pack"],
        ])
        result = excel_ctrl.execute_import(str(path))
        # Both rows should be flagged as duplicates
        assert result["data"]["created"] == 0
        assert result["data"]["updated"] == 0
        assert len(result["data"]["errors"]) >= 2

    def test_execute_import_skips_invalid_rows(self, excel_ctrl, tmp_path):
        path = tmp_path / "mixed.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000100", "Válido", 500, 300, 10, "unit"],
            ["7790000000200", "Malo", -100, 50, 5, "unit"],  # invalid price
            ["7790000000300", "Válido 2", 800, 500, 15, "pack"],
        ])
        result = excel_ctrl.execute_import(str(path))
        assert result["success"] is True
        assert result["data"]["created"] == 2  # only the valid rows
        assert len(result["data"]["errors"]) == 1  # one error row

    def test_execute_import_empty_file(self, excel_ctrl, tmp_path):
        path = tmp_path / "empty.xlsx"
        _create_xlsx(str(path), [
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
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
            ["barcode", "name", "sale_price", "cost_price", "stock", "unit_type"],
            ["7790000000100", "Test", 500, 300, 10, "unit"],
        ])
        excel_ctrl.execute_import(str(path))
        result = excel_ctrl.get_import_result()
        assert result["success"] is True
        assert result["data"]["created"] == 1
