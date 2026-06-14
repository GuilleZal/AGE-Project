# excel-import Specification

## Purpose

Batch product import from .xlsx files with upsert logic. Template download, header validation, row-by-row validation, and transactional commit. Error reporting per row.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| EI-01 | Template Download | MUST | Generate .xlsx with exact columns: barcode, name, sale_price, cost_price, stock, unit_type |
| EI-02 | Header Validation | MUST | Reject file if headers don't match template exactly; error: "Formato de plantilla inválido" |
| EI-03 | Row Validation | MUST | Per-row: sale_price/cost_price/stock must be numeric (≥0); required fields not null; unit_type in ('unit','weight_kg','pack') |
| EI-04 | Upsert Logic | MUST | If barcode does not exist → CREATE product; if barcode exists → UPDATE sale_price, cost_price, stock, unit_type |
| EI-05 | Batch Transaction | MUST | All valid rows committed atomically; if any valid row fails, rollback all |
| EI-06 | Preview | SHOULD | Show first 10 rows before confirming import |
| EI-07 | Error Reporting | MUST | Return summary: "X creados, Y actualizados, Errores en filas: Z" with per-row error details |
| EI-08 | Duplicate Detection | MUST | Detect duplicate barcodes within the file itself; report as error |

## Scenarios

### EI-02: Header Validation

- **Matching headers**: GIVEN file has columns [barcode, name, sale_price, cost_price, stock, unit_type], WHEN loaded, THEN pass.
- **Extra column**: GIVEN file has extra column "description", WHEN loaded, THEN reject "Formato de plantilla inválido".
- **Missing column**: GIVEN file missing "cost_price", WHEN loaded, THEN reject "Formato de plantilla inválido".
- **Wrong order**: GIVEN columns in different order, THEN reject (exact match required).
- **Empty file**: GIVEN file has only headers, WHEN loaded, THEN show "El archivo no contiene datos".

### EI-03: Row Validation

- **Non-numeric price**: GIVEN sale_price="diez", WHEN validated, THEN error "sale_price debe ser numérico".
- **Negative stock**: GIVEN stock=-5, WHEN validated, THEN error "stock debe ser ≥ 0".
- **Null required**: GIVEN name is empty, WHEN validated, THEN error "name es obligatorio".
- **Invalid unit_type**: GIVEN unit_type="litros", WHEN validated, THEN error "unit_type debe ser: unit, weight_kg, pack".

### EI-04: Upsert Logic

- **Create new**: GIVEN barcode 7791234567890 does not exist, WHEN imported, THEN new product created with all fields.
- **Update existing**: GIVEN barcode exists with old price=1000, WHEN imported with price=1200, THEN product updated (sale_price=1200, cost_price, stock, unit_type also updated; name NOT updated on upsert).
- **Upsert skips name**: GIVEN existing product name="Vino Tinto", WHEN upsert with name="Vino Blanco", THEN name remains "Vino Tinto" (name is CREATE-only, not updated on upsert).

### EI-05: Batch Transaction

- **All valid**: GIVEN 50 rows all pass validation, WHEN import confirmed, THEN all 50 committed.
- **Mixed validity**: GIVEN 100 rows, 10 have errors, WHEN import confirmed, THEN 90 committed (errors skipped), summary shows "90 creados/actualizados, Errores en filas: [row numbers]".

### EI-08: Duplicate Detection

- **Intra-file duplicate**: GIVEN rows 5 and 12 have same barcode, WHEN validated, THEN both rows flagged as duplicate error.
- **DB duplicate ok**: GIVEN barcode exists in DB (not in file), WHEN validated, THEN row valid (triggers upsert update, not duplicate error).
