# Design: Desktop POS Sales System

## Technical Approach

Greenfield MVC + Repository + Service architecture on Python 3.12, CustomTkinter, SQLite (WAL). Six capabilities mapped to controller/service/repository triples. Views use `CTkTabview` with 5 tabs (Sales, Products, Returns, Cash Register, Reports). Barcode input: keyboard wedge via `<Return>` on focused `BarcodeEntry`. Stock never blocks sales — maximum fluidity principle.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data tables | `ttk.Treeview` styled to CTk theme | CustomTkinter lacks Treeview; ttk widgets coexist in CTk frames |
| Barcode input | Keyboard wedge (Entry + Return) + optional serial | 90%+ scanners emulate HID keyboard; zero extra deps for default path |
| Stock policy | Never block; allow negative | UX: cashier flow never interrupted; stock is admin visibility only |
| Return model | Direct atomic (no original sale FK) | Matches kiosk reality; `cash_register_id` provides audit trail |
| Quick-create defaults | `cost=0, stock=0, unit_type=unit, threshold=5` | Minimal friction at sale time; complete later via Products CRUD |
| Excel upsert | barcode match → UPDATE (price/cost/stock/unit); no match → INSERT | Name is human-curated, not overwritten; prices/stock are import authority |
| Currency | `INTEGER` (whole ARS pesos) | No cents per domain constraint; migration path: ×100 internally if needed |
| Mixed payments | Single `payment_method='mixed'`; split not tracked per-tender | Simplifies MVP; P2 enhancement |
| Backup | Standalone Python script, zip + 30-day retention | No UI dependency; Windows Task Scheduler |

## Data Flow

### Critical Path: Complete Sale
```
BarcodeEntry ──<Return>──→ SaleController.add_by_barcode(barcode)
  ├─ ProductRepo.find_by_barcode() → found?
  │   ├─ YES → Cart.add(product, qty=1) → View.update_cart()
  │   └─ NO  → QuickCreateDialog(name, price) → ProductRepo.create() → Cart.add() → View.update_cart()
  │
PaymentButton ──→ SaleController.complete_sale(payment, received)
  ├─ [cash] received < total? → Block "Monto insuficiente"
  ├─ SaleRepo.create(sale) → SaleItemRepo.create_batch(items)
  ├─ StockService.deduct(items)         # never blocks
  ├─ CashMovementRepo.create(type='sale_cash', amount)
  └─ View.show_receipt(sale) → View.reset_cart()
```

### Cash Register Close
```
CloseButton ──→ CashRegisterController.close(actual, reason)
  ├─ expected = opening + Σcash_sales - Σreturns - Σoutflows
  ├─ diff = actual - expected
  └─ CashRegisterRepo.update(id, closing_amount=actual, difference=diff,
       close_reason=reason, status='closed')
```

### Excel Import (transactional)
```
ImportButton ──→ ExcelImportController.import_(filepath)
  ├─ validate_headers() → mismatch? → reject file
  ├─ parse_rows() → validate each (prices≥0, unit_type∈{unit,weight_kg,pack})
  ├─ detect intra-file barcode duplicates → flag rows
  └─ BEGIN TRANSACTION
       ├─ per valid row: barcode in DB? → UPDATE | INSERT
       └─ any DB error? → ROLLBACK all
     → return {created, updated, errors[]}
```

## Database Schema

10 tables with WAL journal + foreign keys ON. Connection via singleton `get_connection()` in `model/database.py`.

| Table | Key Columns | Indexes |
|-------|------------|---------|
| `categories` | `id`, `name UNIQUE` | — |
| `products` | `id`, `barcode UNIQUE`, `name`, `category_id FK`, `sale_price`, `cost_price`, `stock DEFAULT 0`, `unit_type CHECK(unit/weight_kg/pack)`, `low_stock_threshold DEFAULT 5` | barcode, name, category_id |
| `sales` | `id`, `total`, `discount DEFAULT 0`, `payment_method CHECK(cash/card/transfer/mixed)`, `cash_register_id FK`, `created_at` | created_at, payment_method |
| `sale_items` | `id`, `sale_id FK CASCADE`, `product_id FK`, `quantity`, `unit_price`, `subtotal` | sale_id, product_id |
| `cash_registers` | `id`, `opening_amount`, `opening_time`, `closing_amount`, `closing_time`, `expected_amount`, `difference`, `close_reason`, `status CHECK(open/closed)` | status, opening_time |
| `cash_movements` | `id`, `cash_register_id FK`, `type CHECK(sale_cash/return/supplier_payment/expense)`, `amount`, `description`, `created_at` | register_id, type, date |
| `returns` | `id`, `product_id FK`, `quantity`, `refund_amount`, `reason`, `cash_register_id FK`, `created_at` | product_id, date, register_id |
| `suppliers` | `id`, `name`, `cuit`, `phone`, `address`, `email` | — (P3) |
| `purchases` | `id`, `supplier_id FK`, `total`, `purchase_date`, `notes` | date, supplier_id (P3) |
| `purchase_items` | `id`, `purchase_id FK CASCADE`, `product_id FK`, `quantity`, `unit_cost`, `subtotal` | purchase_id (P3) |

## File Structure

```
pos/
├── main.py                         # Init DB, launch MainWindow
├── model/
│   ├── __init__.py
│   ├── database.py                 # get_connection() — WAL + FK pragmas
│   ├── product.py                  # Product, Category dataclasses
│   ├── sale.py                     # Sale, SaleItem dataclasses
│   ├── cash_register.py            # CashRegister, CashMovement
│   ├── return_.py                  # Return dataclass (return_ avoids keyword)
│   └── enums.py                    # PaymentMethod, UnitType, MovementType
├── repository/
│   ├── __init__.py
│   ├── product_repo.py             # CRUD, find_by_barcode, search, upsert
│   ├── category_repo.py            # CRUD, count_products
│   ├── sale_repo.py                # create, aggregate_by_period
│   ├── sale_item_repo.py           # create_batch, get_by_sale
│   ├── cash_register_repo.py       # open, close, find_active
│   ├── cash_movement_repo.py       # create, sum_by_type
│   └── return_repo.py              # create, get_by_date
├── service/
│   ├── __init__.py
│   ├── stock_service.py            # deduct(items), restore(product_id, qty), low_stock_products()
│   ├── report_service.py           # sales_summary, profit_summary, top_products, export_csv
│   └── backup_service.py           # backup_db(), cleanup_old(days=30)
├── controller/
│   ├── __init__.py
│   ├── sale_controller.py          # add_by_barcode, update_qty, complete_sale
│   ├── product_controller.py       # CRUD orchestration + validation
│   ├── cash_register_controller.py # open, close, register_outflow, get_balance
│   ├── return_controller.py        # process_return, lookup_product
│   ├── report_controller.py        # generate + CSV export orchestration
│   └── excel_import_controller.py  # validate, preview, import transactional
├── view/
│   ├── __init__.py
│   ├── main_window.py              # CTk root + CTkTabview (5 tabs)
│   ├── sale_view.py                # POS terminal layout
│   ├── product_view.py             # CRUD form + search + treeview
│   ├── return_view.py              # Return form
│   ├── cash_register_view.py       # Open/close + balance panel + history
│   ├── report_view.py              # Period selector + metrics + top10 + export
│   └── widgets/
│       ├── __init__.py
│       ├── barcode_entry.py        # Entry + <Return> → callback; sanitize + debounce 300ms
│       ├── cart_treeview.py        # ttk.Treeview: product, qty, unit_price, subtotal
│       ├── quick_create_dialog.py  # CTkToplevel: name + sale_price only
│       ├── payment_dialog.py       # Method selector + cash received field + change display
│       ├── product_search.py       # Search bar (barcode/name/category)
│       └── receipt_preview.py      # CTkToplevel with sale summary
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # in-memory SQLite fixtures: db, sample_products, open_register
│   ├── test_product_repo.py
│   ├── test_sale_repo.py
│   ├── test_cash_register_repo.py
│   ├── test_return_repo.py
│   ├── test_stock_service.py
│   ├── test_report_service.py
│   ├── test_sale_controller.py
│   ├── test_return_controller.py
│   ├── test_excel_import_controller.py
│   └── test_backup_service.py
├── scripts/
│   └── backup.py                   # Standalone: zip pos.db + 30-day cleanup
└── data/                           # Runtime: pos.db + backups/
```

## UI Layout

| Tab | Key Widgets | Notes |
|-----|------------|-------|
| **Sales** (default) | `BarcodeEntry` (always focused), `CartTreeview`, Total label, Payment buttons, `QuickCreateDialog` (on unknown barcode) | POS terminal; dark theme default |
| **Products** | `ProductSearch` bar, `ProductTreeview`, Add/Edit/Delete buttons, `ImportExcel` button | Category CRUD inline |
| **Returns** | `BarcodeEntry`, Product info display, Qty spinbox, Reason entry, Confirm button | Direct atomic return |
| **Cash Register** | Balance panel (initial, inflows, outflows, expected), Open/Close buttons, Outflow form, History treeview | Single-active enforcement |
| **Reports** | Period selector (Today/Week/Month/Custom), Metrics cards, Top10 treeview, ExportCSV | Sales + profit |

## Key Implementation Details

**Keyboard wedge barcode**: `BarcodeEntry` binds `<Return>`, strips whitespace, validates numeric chars, debounces rapid scans (<300ms ignored). Always focused during sale.

**Quick product creation**: `QuickCreateDialog` (`CTkToplevel`) pre-fills scanned barcode (read-only), prompts only `name` + `sale_price` (int ≥0). On confirm → `ProductRepo.create()` → auto-adds to cart. Remaining fields use defaults.

**Weight products** (`unit_type='weight_kg'`): Sale view switches qty input to kg. Price = `sale_price × kg`. Stock tracked as `REAL` (kg granularity).

**Excel import upsert**: 1) Validate headers (exact match). 2) Row-by-row: prices≥0, unit_type in allowed set, barcode unique within file. 3) Transaction: `SELECT` by barcode → found → `UPDATE` (price, cost, stock, unit_type; name preserved); not found → `INSERT`. 4) Return `{created, updated, errors[]}`.

**Cash register tracking**: `expected_amount` computed live: `opening + Σsale_cash - Σreturns - Σoutflows`. `difference = actual - expected` on close. Only one `status='open'` row permitted at a time.

**Reports aggregation**: SQL `GROUP BY strftime` on `sales.created_at`. Top 10: `JOIN sale_items + products GROUP BY product_id ORDER BY SUM(quantity) DESC LIMIT 10`. Profit: `SUM(sale_items.subtotal) - SUM(sale_items.quantity * products.cost_price)`. Performance target: <3s for 10k sales via date indexes.

**Backup script**: `scripts/backup.py` — independent of app, imports only stdlib (`shutil`, `zipfile`, `os`, `datetime`). Copies `data/pos.db` → `data/backups/pos_YYYY-MM-DD_HHMM.zip`. Deletes zips >30 days.

## Error Handling

| Layer | Mechanism | View Impact |
|-------|-----------|-------------|
| Repository | `DataError(msg)` on integrity violations, not-found → `None` | — |
| Service | `BusinessError(msg)` for rule violations | — |
| Controller | Catches all, translates to user-facing message | `messagebox.showerror(title, msg)` |
| View | Input validation at widget level | Block action, highlight invalid field |

All custom exceptions inherit from `POSException`. Raw SQLite errors never reach the view.

## Testing Strategy

| Layer | Approach | Target |
|-------|----------|--------|
| Repository | in-memory SQLite, schema per test via `conftest.py` fixture; verify SQL correctness | ≥90% |
| Service | Mock repositories via `pytest-mock`; test business rules + edge cases | ≥90% |
| Controller | Mock services + repos; test orchestration + error handling paths | ≥80% |
| View | Manual QA only | — |

**Fixtures** (`tests/conftest.py`): `db` (in-memory SQLite with full DDL), `sample_products`, `sample_category`, `open_register`.

## Open Questions

- [ ] `python-escpos` included? Specs omit it, exploration assumes it. Recommend: defer to P2; receipt preview only in MVP.
- [ ] Suppliers/purchases tables included in schema but P3 scope — controllers/repos for them in MVP or deferred? Recommend: schema only; controllers deferred.
- [ ] Dark theme confirmation for default? (Assumed for beverage shop lighting conditions.)
