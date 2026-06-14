# Implementation Tasks: pos-sales-system

## Task Breakdown Strategy

Organized by architectural layer (bottom-up: model → repository → service → controller → view) with dependency chains. Each task is a reviewable unit with clear acceptance criteria.

**Total estimated effort**: ~4,500 LOC across 50 files
**Complexity distribution**: Low (20%), Medium (50%), High (30%)
**Recommended execution**: 8 batches, sequential within each batch

---

## Phase 1: Foundation (Tasks 1-4)

### Task 1.1: Project Structure & Database Setup
**Description**: Create directory structure, initialize SQLite database with WAL mode, foreign keys enabled, and schema DDL.

**Files to create**:
- `pos/main.py` (entry point)
- `pos/model/database.py` (connection manager)
- `pos/model/__init__.py`
- `requirements.txt`

**Dependencies**: None (first task)

**Estimated effort**: 150 LOC | Complexity: Low | Time: 2h

**Acceptance criteria**:
- [x] `python pos/main.py` runs without errors
- [x] Database file created at `pos/data/pos.db`
- [x] WAL journal mode enabled
- [x] Foreign keys enabled
- [x] All 10 tables created with correct schema
- [x] Indexes created on frequently queried columns

---

### Task 1.2: Data Models (Dataclasses)
**Description**: Define all domain entities as Python dataclasses with type hints.

**Files to create**:
- `pos/model/product.py` (Product, Category)
- `pos/model/sale.py` (Sale, SaleItem)
- `pos/model/cash_register.py` (CashRegister, CashMovement)
- `pos/model/return_.py` (Return)
- `pos/model/enums.py` (PaymentMethod, UnitType, MovementType)

**Dependencies**: Task 1.1

**Estimated effort**: 200 LOC | Complexity: Low | Time: 3h

**Acceptance criteria**:
- [x] All dataclasses defined with type hints
- [x] Enums use `str, Enum` pattern for DB compatibility
- [x] Default values match schema (stock=0, threshold=5, unit_type='unit')
- [x] Currency fields use `int` (whole ARS)
- [x] Stock field uses `float` (for weight_kg granularity)

---

### Task 1.3: Custom Exceptions
**Description**: Define exception hierarchy for error handling across layers.

**Files to create**:
- `pos/model/exceptions.py`

**Dependencies**: Task 1.1

**Estimated effort**: 30 LOC | Complexity: Low | Time: 0.5h

**Acceptance criteria**:
- [x] `POSException` base class
- [x] `DataError` for repository violations
- [x] `BusinessError` for service rule violations
- [x] All exceptions include user-friendly message

---

### Task 1.4: Test Fixtures
**Description**: Create pytest fixtures for in-memory SQLite database with sample data.

**Files to create**:
- `pos/tests/__init__.py`
- `pos/tests/conftest.py` (db, sample_products, sample_category, open_register fixtures)

**Dependencies**: Task 1.1, Task 1.2

**Estimated effort**: 100 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [x] `db` fixture creates in-memory SQLite with full DDL
- [x] `sample_products` fixture inserts 5 test products (mix of unit/weight_kg)
- [x] `sample_category` fixture inserts 2 categories
- [x] `open_register` fixture creates open cash register
- [x] All fixtures are function-scoped (isolated per test)

---

## Phase 2: Repositories (Tasks 2.1-2.7)

### Task 2.1: Product Repository
**Description**: CRUD operations for products with barcode search, name search, and upsert logic.

**Files to create**:
- `pos/repository/__init__.py`
- `pos/repository/product_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 180 LOC | Complexity: Medium | Time: 3h

**Acceptance criteria**:
- [ ] `find_by_barcode(barcode)` returns Product or None
- [ ] `search(query)` searches by name (LIKE %query%)
- [ ] `create(product)` inserts with barcode uniqueness validation
- [ ] `update(product)` updates all fields except barcode if duplicate
- [ ] `delete(product_id)` raises DataError if product has sales/purchases
- [ ] `upsert_from_import(product)` → exists: UPDATE (price, cost, stock, unit_type); not exists: INSERT
- [ ] All methods use parameterized queries

**Tests**: `pos/tests/test_product_repo.py` (≥90% coverage)

---

### Task 2.2: Category Repository
**Description**: CRUD for categories with product count validation.

**Files to create**:
- `pos/repository/category_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 80 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [ ] `create(name)` with uniqueness validation
- [ ] `update(category_id, name)`
- [ ] `delete(category_id)` raises DataError if products associated
- [ ] `count_products(category_id)` returns count
- [ ] `get_all()` returns list with product count per category

**Tests**: `pos/tests/test_category_repo.py` (≥90% coverage)

---

### Task 2.3: Sale Repository
**Description**: Sale creation and aggregation queries for reports.

**Files to create**:
- `pos/repository/sale_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 120 LOC | Complexity: Medium | Time: 2.5h

**Acceptance criteria**:
- [ ] `create(sale)` inserts sale record
- [ ] `aggregate_by_period(start_date, end_date, group_by)` → GROUP BY strftime
- [ ] `top_products(start_date, end_date, limit=10)` → JOIN sale_items + products
- [ ] `total_by_payment_method(start_date, end_date)` → breakdown by payment type
- [ ] All queries use date indexes for performance

**Tests**: `pos/tests/test_sale_repo.py` (≥90% coverage)

---

### Task 2.4: Sale Item Repository
**Description**: Batch creation of sale line items.

**Files to create**:
- `pos/repository/sale_item_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 60 LOC | Complexity: Low | Time: 1h

**Acceptance criteria**:
- [ ] `create_batch(sale_id, items)` inserts multiple items in transaction
- [ ] `get_by_sale(sale_id)` returns list of SaleItem
- [ ] Cascade delete on sale deletion (handled by DB)

**Tests**: Included in `test_sale_repo.py`

---

### Task 2.5: Cash Register Repository
**Description**: Open/close lifecycle and active register lookup.

**Files to create**:
- `pos/repository/cash_register_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 100 LOC | Complexity: Medium | Time: 2h

**Acceptance criteria**:
- [ ] `open_register(opening_amount)` creates new register with status='open'
- [ ] `find_active()` returns open register or None
- [ ] `close_register(register_id, closing_amount, difference, reason)` updates status='closed'
- [ ] `get_balance(register_id)` returns dict with opening, inflows, outflows, expected
- [ ] Only ONE register can be open at a time (enforced in service layer)

**Tests**: `pos/tests/test_cash_register_repo.py` (≥90% coverage)

---

### Task 2.6: Cash Movement Repository
**Description**: Track all cash movements (sales, returns, outflows).

**Files to create**:
- `pos/repository/cash_movement_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 70 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [ ] `create(register_id, type, amount, description)` inserts movement
- [ ] `sum_by_type(register_id, type)` returns total for type
- [ ] `get_by_register(register_id)` returns list of movements
- [ ] Types: sale_cash, return, supplier_payment, expense

**Tests**: Included in `test_cash_register_repo.py`

---

### Task 2.7: Return Repository
**Description**: Record atomic returns with cash register linkage.

**Files to create**:
- `pos/repository/return_repo.py`

**Dependencies**: Task 1.2, Task 1.4

**Estimated effort**: 60 LOC | Complexity: Low | Time: 1h

**Acceptance criteria**:
- [ ] `create(return_)` inserts return record
- [ ] `get_by_date(start_date, end_date)` returns list
- [ ] NO foreign key to sales (atomic return model)
- [ ] Links to cash_register_id for audit trail

**Tests**: `pos/tests/test_return_repo.py` (≥90% coverage)

---

## Phase 3: Services (Tasks 3.1-3.3)

### Task 3.1: Stock Service
**Description**: Business logic for stock deduction (sales) and restoration (returns). Never blocks sales.

**Files to create**:
- `pos/service/__init__.py`
- `pos/service/stock_service.py`

**Dependencies**: Task 2.1

**Estimated effort**: 100 LOC | Complexity: Medium | Time: 2h

**Acceptance criteria**:
- [ ] `deduct(items: List[SaleItem])` reduces stock for each product
- [ ] `restore(product_id, quantity)` increases stock
- [ ] Allows negative stock (never raises error for insufficient stock)
- [ ] `low_stock_products(threshold=None)` returns products below threshold
- [ ] Uses transaction for batch deduction

**Tests**: `pos/tests/test_stock_service.py` (≥90% coverage)

---

### Task 3.2: Report Service
**Description**: Aggregation logic for sales and profit reports with CSV export.

**Files to create**:
- `pos/service/report_service.py`

**Dependencies**: Task 2.3, Task 2.4

**Estimated effort**: 150 LOC | Complexity: High | Time: 3h

**Acceptance criteria**:
- [ ] `sales_summary(start_date, end_date)` → total, count, avg_ticket
- [ ] `profit_summary(start_date, end_date)` → revenue, cost, profit, margin%
- [ ] `top_products(start_date, end_date, limit=10)` → by quantity and amount
- [ ] `export_csv(data, filepath)` writes CSV with BOM and semicolon delimiter
- [ ] Performance: <3s for 10k sales (verified via test with mock data)

**Tests**: `pos/tests/test_report_service.py` (≥90% coverage)

---

### Task 3.3: Backup Service
**Description**: Daily backup with zip compression and 30-day retention policy.

**Files to create**:
- `pos/service/backup_service.py`
- `pos/scripts/backup.py` (standalone script)

**Dependencies**: Task 1.1

**Estimated effort**: 80 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [ ] `backup_db()` copies `data/pos.db` → `data/backups/pos_YYYY-MM-DD_HHMM.zip`
- [ ] `cleanup_old(days=30)` deletes zips older than 30 days
- [ ] Standalone script imports only stdlib (shutil, zipfile, os, datetime)
- [ ] Can be scheduled via Windows Task Scheduler
- [ ] Returns success/failure status

**Tests**: `pos/tests/test_backup_service.py` (≥90% coverage)

---

## Phase 4: Controllers (Tasks 4.1-4.6)

### Task 4.1: Sale Controller
**Description**: Orchestrate sale flow: barcode lookup, cart management, payment processing.

**Files to create**:
- `pos/controller/__init__.py`
- `pos/controller/sale_controller.py`

**Dependencies**: Task 2.1, Task 2.3, Task 2.4, Task 3.1

**Estimated effort**: 200 LOC | Complexity: High | Time: 4h

**Acceptance criteria**:
- [ ] `add_by_barcode(barcode)` → found: add to cart; not found: return QuickCreateDialog data
- [ ] `update_qty(product_id, qty)` updates cart item
- [ ] `remove_item(product_id)` removes from cart
- [ ] `complete_sale(payment_method, received_amount)` → validates cash received ≥ total, creates sale, deducts stock, registers cash movement
- [ ] `get_cart()` returns current cart state
- [ ] `clear_cart()` resets for next sale
- [ ] Catches all exceptions, returns user-friendly messages

**Tests**: `pos/tests/test_sale_controller.py` (≥80% coverage)

---

### Task 4.2: Product Controller
**Description**: CRUD orchestration with validation and Excel import.

**Files to create**:
- `pos/controller/product_controller.py`

**Dependencies**: Task 2.1, Task 2.2

**Estimated effort**: 180 LOC | Complexity: High | Time: 3.5h

**Acceptance criteria**:
- [ ] `create_product(data)` validates barcode uniqueness, creates product
- [ ] `update_product(product_id, data)` validates, updates
- [ ] `delete_product(product_id)` checks transaction history, blocks if exists
- [ ] `create_category(name)` validates uniqueness
- [ ] `import_from_excel(filepath)` → validates headers, row-by-row validation, upsert logic, returns {created, updated, errors[]}
- [ ] `download_template(filepath)` generates .xlsx with exact columns
- [ ] All methods catch DataError, return user-friendly messages

**Tests**: `pos/tests/test_product_controller.py` (≥80% coverage)

---

### Task 4.3: Cash Register Controller
**Description**: Open/close lifecycle, balance calculation, outflow registration.

**Files to create**:
- `pos/controller/cash_register_controller.py`

**Dependencies**: Task 2.5, Task 2.6

**Estimated effort**: 150 LOC | Complexity: Medium | Time: 3h

**Acceptance criteria**:
- [ ] `open_register(opening_amount)` validates no active register, creates
- [ ] `close_register(actual_amount, reason)` calculates expected, difference, closes
- [ ] `register_outflow(type, amount, description)` creates cash movement
- [ ] `get_balance()` returns dict with opening, inflows, outflows, expected, difference
- [ ] `get_history()` returns list of movements
- [ ] Enforces single-active-register rule

**Tests**: `pos/tests/test_cash_register_controller.py` (≥80% coverage)

---

### Task 4.4: Return Controller
**Description**: Process direct atomic returns with stock restoration.

**Files to create**:
- `pos/controller/return_controller.py`

**Dependencies**: Task 2.1, Task 2.7, Task 3.1

**Estimated effort**: 100 LOC | Complexity: Medium | Time: 2h

**Acceptance criteria**:
- [ ] `lookup_product(barcode)` returns product info
- [ ] `process_return(product_id, quantity, reason)` → restores stock, registers cash movement (type='return'), creates return record
- [ ] Uses current cash_register_id (no original sale linkage)
- [ ] Validates quantity > 0
- [ ] Returns refund_amount = sale_price × quantity

**Tests**: `pos/tests/test_return_controller.py` (≥80% coverage)

---

### Task 4.5: Report Controller
**Description**: Generate reports and export to CSV.

**Files to create**:
- `pos/controller/report_controller.py`

**Dependencies**: Task 3.2

**Estimated effort**: 80 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [ ] `generate_sales_report(start_date, end_date, filters)` calls report_service
- [ ] `generate_profit_report(start_date, end_date)` calls report_service
- [ ] `export_to_csv(data, filepath)` delegates to service
- [ ] Handles date parsing errors

**Tests**: Included in `test_report_service.py`

---

### Task 4.6: Excel Import Controller
**Description**: Validate and import products from Excel with upsert logic.

**Files to create**:
- `pos/controller/excel_import_controller.py`

**Dependencies**: Task 2.1

**Estimated effort**: 120 LOC | Complexity: High | Time: 2.5h

**Acceptance criteria**:
- [ ] `validate_headers(filepath)` checks exact column match
- [ ] `parse_and_validate(filepath)` row-by-row validation (prices≥0, unit_type valid, no nulls)
- [ ] `preview(filepath)` returns first 10 rows
- [ ] `import_products(filepath)` → transaction: upsert logic, returns {created, updated, errors[]}
- [ ] Detects intra-file barcode duplicates
- [ ] Rolls back entire transaction on any DB error

**Tests**: `pos/tests/test_excel_import_controller.py` (≥80% coverage)

---

## Phase 5: Views (Tasks 5.1-5.8)

### Task 5.1: Main Window & Tab Navigation
**Description**: Root window with CTkTabview containing 5 tabs.

**Files to create**:
- `pos/view/__init__.py`
- `pos/view/main_window.py`

**Dependencies**: Task 1.1

**Estimated effort**: 80 LOC | Complexity: Low | Time: 1.5h

**Acceptance criteria**:
- [ ] CTk root window with title "Sistema POS"
- [ ] CTkTabview with 5 tabs: Ventas, Productos, Devoluciones, Caja, Reportes
- [ ] Dark theme default
- [ ] Window size 1200x800
- [ ] Sales tab is default/active

---

### Task 5.2: Barcode Entry Widget
**Description**: Custom entry widget with keyboard wedge support and debounce.

**Files to create**:
- `pos/view/widgets/__init__.py`
- `pos/view/widgets/barcode_entry.py`

**Dependencies**: Task 5.1

**Estimated effort**: 60 LOC | Complexity: Medium | Time: 1.5h

**Acceptance criteria**:
- [ ] Binds `<Return>` event to callback
- [ ] Strips whitespace from input
- [ ] Validates numeric characters only
- [ ] Debounces rapid scans (<300ms ignored)
- [ ] Auto-focuses after each scan
- [ ] Emits `on_scan` event with barcode value

---

### Task 5.3: Cart Treeview Widget
**Description**: ttk.Treeview styled to match CustomTkinter theme.

**Files to create**:
- `pos/view/widgets/cart_treeview.py`

**Dependencies**: Task 5.1

**Estimated effort**: 70 LOC | Complexity: Medium | Time: 1.5h

**Acceptance criteria**:
- [ ] Columns: Producto, Cantidad, Precio Unit., Subtotal
- [ ] Styled to match CTk dark theme
- [ ] `update_cart(items: List[dict])` refreshes display
- [ ] `get_selected_item()` returns selected row
- [ ] Supports delete key to remove item

---

### Task 5.4: Sale View (POS Terminal)
**Description**: Main sales screen with barcode entry, cart, total, payment buttons.

**Files to create**:
- `pos/view/sale_view.py`

**Dependencies**: Task 5.2, Task 5.3

**Estimated effort**: 150 LOC | Complexity: High | Time: 3h

**Acceptance criteria**:
- [ ] Layout: BarcodeEntry (top), CartTreeview (center), Total label (bottom-right), Payment buttons (bottom)
- [ ] BarcodeEntry always focused
- [ ] Total updates in real-time
- [ ] Payment buttons: Efectivo, Tarjeta, Transferencia, Mixto
- [ ] Emits events: `on_scan`, `on_update_qty`, `on_remove_item`, `on_payment`
- [ ] Shows receipt preview after sale

---

### Task 5.5: Quick Create Dialog
**Description**: Modal dialog for creating product when barcode not found.

**Files to create**:
- `pos/view/widgets/quick_create_dialog.py`

**Dependencies**: Task 5.4

**Estimated effort**: 80 LOC | Complexity: Medium | Time: 2h

**Acceptance criteria**:
- [ ] CTkToplevel modal dialog
- [ ] Pre-fills barcode (read-only)
- [ ] Prompts: name (required), sale_price (required, int ≥0)
- [ ] OK/Cancel buttons
- [ ] Returns dict with product data or None if cancelled
- [ ] Validates input before allowing OK

---

### Task 5.6: Payment Dialog
**Description**: Modal dialog for payment method selection and cash received.

**Files to create**:
- `pos/view/widgets/payment_dialog.py`

**Dependencies**: Task 5.4

**Estimated effort**: 90 LOC | Complexity: Medium | Time: 2h

**Acceptance criteria**:
- [ ] Payment method selector (radio buttons or dropdown)
- [ ] If cash: "Monto recibido" field (int ≥ total)
- [ ] Calculates and displays change (vuelto)
- [ ] Validates received ≥ total for cash
- [ ] Returns dict with {payment_method, received, change} or None

---

### Task 5.7: Product View (CRUD)
**Description**: Product management screen with search, treeview, and CRUD buttons.

**Files to create**:
- `pos/view/product_view.py`
- `pos/view/widgets/product_search.py`

**Dependencies**: Task 5.1, Task 5.3

**Estimated effort**: 200 LOC | Complexity: High | Time: 4h

**Acceptance criteria**:
- [ ] Search bar: barcode, name, category filter
- [ ] ProductTreeview with columns: Código, Nombre, Categoría, Precio, Stock
- [ ] Buttons: Nuevo, Editar, Eliminar, Importar Excel
- [ ] Category CRUD inline (dropdown with "Nueva categoría" option)
- [ ] Emits events: `on_create`, `on_edit`, `on_delete`, `on_import`
- [ ] Shows confirmation dialog before delete

---

### Task 5.8: Remaining Views (Returns, Cash Register, Reports)
**Description**: Complete remaining views for returns, cash register, and reports.

**Files to create**:
- `pos/view/return_view.py`
- `pos/view/cash_register_view.py`
- `pos/view/report_view.py`
- `pos/view/widgets/receipt_preview.py`

**Dependencies**: Task 5.1, Task 5.3

**Estimated effort**: 400 LOC | Complexity: High | Time: 8h

**Acceptance criteria**:

**Return View**:
- [ ] BarcodeEntry for product lookup
- [ ] Product info display (name, price)
- [ ] Quantity spinbox (default=1)
- [ ] Reason entry (optional)
- [ ] Confirm button

**Cash Register View**:
- [ ] Balance panel: initial, inflows, outflows, expected, difference
- [ ] Open/Close buttons
- [ ] Outflow form (type, amount, description)
- [ ] History treeview

**Report View**:
- [ ] Period selector: Today, Week, Month, Custom range
- [ ] Metrics cards: total, count, avg_ticket, profit, margin%
- [ ] Top10 treeview
- [ ] ExportCSV button

**Receipt Preview**:
- [ ] CTkToplevel with sale summary
- [ ] Items list, total, payment method, change
- [ ] Close button

---

## Phase 6: Integration & Testing (Tasks 6.1-6.3)

### Task 6.1: Wire Controllers to Views
**Description**: Connect all controllers to views, implement event handlers.

**Files to modify**:
- `pos/view/*.py` (all views)
- `pos/controller/*.py` (all controllers)

**Dependencies**: Tasks 4.1-4.6, Tasks 5.1-5.8

**Estimated effort**: 300 LOC | Complexity: High | Time: 6h

**Acceptance criteria**:
- [ ] All view events wired to controller methods
- [ ] Controller responses update view state
- [ ] Error messages displayed via messagebox
- [ ] End-to-end flow works: scan → cart → pay → receipt

---

### Task 6.2: End-to-End Manual Testing
**Description**: Manual QA of all P1 flows with real hardware (scanner, printer optional).

**Dependencies**: Task 6.1

**Estimated effort**: 0 LOC | Complexity: Medium | Time: 4h

**Acceptance criteria**:
- [ ] Flow 1.1 (Sale) works end-to-end
- [ ] Flow 1.2 (Return) works end-to-end
- [ ] Flow 1.3-1.5 (Cash register) works end-to-end
- [ ] Quick product creation works
- [ ] Weight-based products work (kg input → price calc)
- [ ] All P1 acceptance criteria pass

---

### Task 6.3: Documentation & Deployment
**Description**: README, installation guide, backup script scheduling.

**Files to create**:
- `README.md`
- `INSTALL.md`
- `docs/backup_scheduling.md`

**Dependencies**: Task 6.2

**Estimated effort**: 100 LOC | Complexity: Low | Time: 2h

**Acceptance criteria**:
- [ ] README with project overview, features, screenshots
- [ ] INSTALL with Python 3.12 setup, pip install, DB initialization
- [ ] Backup scheduling guide for Windows Task Scheduler
- [ ] All dependencies listed in requirements.txt

---

## Dependency Graph

```
1.1 → 1.2 → 1.4
  ↓     ↓
  1.3   2.1 → 3.1 → 4.1 → 5.4 → 6.1 → 6.2 → 6.3
  ↓     ↓     ↓     ↓     ↓
  1.4   2.2   3.2   4.2   5.5
        ↓     ↓     ↓     ↓
        2.3   3.3   4.3   5.6
        ↓           ↓     ↓
        2.4         4.4   5.7
        ↓           ↓     ↓
        2.5         4.5   5.8
        ↓           ↓
        2.6         4.6
        ↓
        2.7
```

---

## Execution Order (8 Batches)

**Batch 1** (Foundation): Tasks 1.1, 1.2, 1.3, 1.4
**Batch 2** (Repositories): Tasks 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
**Batch 3** (Services): Tasks 3.1, 3.2, 3.3
**Batch 4** (Controllers): Tasks 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
**Batch 5** (Views - Core): Tasks 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
**Batch 6** (Views - Extended): Tasks 5.7, 5.8
**Batch 7** (Integration): Task 6.1
**Batch 8** (Testing & Docs): Tasks 6.2, 6.3

---

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| 2.3 (Sale Repo aggregation) | High | Complex SQL queries; test with 10k mock records |
| 3.2 (Report Service) | High | Performance target <3s; optimize indexes |
| 4.1 (Sale Controller) | High | Complex orchestration; test all payment paths |
| 4.6 (Excel Import) | High | Transaction rollback; test duplicate detection |
| 5.4 (Sale View) | High | Real-time updates; test barcode debounce |
| 5.8 (Remaining Views) | High | 400 LOC; split into sub-tasks if needed |
| 6.1 (Integration) | High | Wiring errors; test each flow end-to-end |

---

## Review Workload Forecast

**Total estimated LOC**: ~4,500
**Chained PRs recommended**: Yes (split by batch)
**400-line budget risk**: High (most batches exceed 400 LOC)
**Decision needed before apply**: Yes — choose delivery strategy

**Recommended PR structure**:
- PR #1: Foundation (Tasks 1.1-1.4) — ~500 LOC
- PR #2: Repositories (Tasks 2.1-2.7) — ~700 LOC
- PR #3: Services (Tasks 3.1-3.3) — ~350 LOC
- PR #4: Controllers (Tasks 4.1-4.6) — ~850 LOC
- PR #5: Views Core (Tasks 5.1-5.6) — ~550 LOC
- PR #6: Views Extended (Tasks 5.7-5.8) — ~600 LOC
- PR #7: Integration (Task 6.1) — ~300 LOC
- PR #8: Testing & Docs (Tasks 6.2-6.3) — ~100 LOC
