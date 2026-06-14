# product-catalog Specification

## Purpose

Product and category CRUD with uniqueness validations, integrity constraints, and transaction-history delete protection. Search by barcode, name, or category. Stock visibility with configurable low-stock thresholds.

## Requirements

| # | Requirement | Strength | Summary |
|---|-------------|----------|---------|
| PC-01 | Product Creation | MUST | Required: name, sale_price (≥0), cost_price (≥0), unit_type. Optional: barcode (unique), category_id, stock (default 0), low_stock_threshold (default 5), description |
| PC-02 | Product Editing | MUST | Modify all fields except barcode if new value duplicates existing; auto-update updated_at |
| PC-03 | Product Deletion | MUST | Block if product has sales OR purchases (FK check); error: "El producto tiene historial de transacciones. Establezca stock=0 en su lugar." |
| PC-04 | Barcode Uniqueness | MUST | Validate no duplicate barcode on create and on edit; nullable barcode allowed (products without barcode) |
| PC-05 | Category CRUD | MUST | Create (unique name), edit (name), delete (block if products associated → "La categoría tiene productos asociados.") |
| PC-06 | Product Search | MUST | Search by barcode (exact), name (LIKE), category (filter); results shown in table |
| PC-07 | Stock Visibility | MUST | Show current stock per product; highlight if stock ≤ low_stock_threshold |
| PC-08 | Unit Type Validation | MUST | unit_type must be one of: 'unit', 'weight_kg', 'pack' |

## Scenarios

### PC-01: Product Creation

- **Happy path**: GIVEN barcode=7791234567890, name="Vino Tinto", sale_price=2000, cost_price=800, unit_type=unit, stock=30, WHEN created, THEN product saved with timestamps.
- **Duplicate barcode**: GIVEN barcode already exists, WHEN create attempted, THEN reject "El código de barras ya existe".
- **Missing name**: GIVEN name empty, WHEN create attempted, THEN reject "El nombre es obligatorio".
- **Negative price**: GIVEN sale_price=-100, WHEN create attempted, THEN reject "El precio debe ser ≥ 0".
- **Invalid unit_type**: GIVEN unit_type="liters", WHEN create attempted, THEN reject "Tipo de unidad inválido".
- **No barcode**: GIVEN barcode is null/empty, WHEN create attempted, THEN allowed (product without barcode).

### PC-03: Product Deletion

- **With history**: GIVEN product has sale_items referencing it, WHEN delete attempted, THEN reject with history message.
- **No history**: GIVEN product has zero sales and zero purchases, WHEN delete attempted, THEN product deleted from DB.
- **With purchases only**: GIVEN product has purchase_items only (never sold), WHEN delete attempted, THEN reject (purchase history blocks deletion).

### PC-05: Category CRUD

- **Create duplicate name**: GIVEN category "Bebidas" exists, WHEN create with same name, THEN reject "La categoría ya existe".
- **Delete with products**: GIVEN category "Bebidas" has 5 products, WHEN delete attempted, THEN reject "La categoría tiene productos asociados.".
- **Delete empty category**: GIVEN category has 0 products, WHEN delete attempted, THEN category deleted.

### PC-06: Product Search

- **Barcode exact**: GIVEN search term=7791234567890, THEN return exact match or none.
- **Name partial**: GIVEN search term="vino", THEN return all products with "vino" in name (case-insensitive LIKE).
- **Category filter**: GIVEN category="Bebidas" selected, THEN return only products in that category.

### PC-07: Stock Visibility

- **Low stock alert**: GIVEN product stock=3, threshold=5, THEN row highlighted in UI (stock ≤ threshold).
- **Normal stock**: GIVEN product stock=20, threshold=5, THEN no highlight.
