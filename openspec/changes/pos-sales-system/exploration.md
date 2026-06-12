## Exploration: Desktop POS System — Architecture, Stack, Dependencies

### Current State

The project (`Proyecto_1` / `age-project`) is a **clean Git repository** with no source code. The user confirmed:

- **Stack**: Python 3.12 (stability with hardware) with CustomTkinter (modern UI)
- **Architecture**: MVC (Model-View-Controller) — user validated this choice
- **Domain**: Desktop POS for selling beverages (wines, sodas, beers) and products
- **Persistence**: openspec (file-based), Engram memory active
- **Return Policy**: Direct Atomic Return flow — no original ticket linkage, only current cash register session

Python 3.12 is the target version for hardware compatibility. CustomTkinter provides modern UI appearance. SQLite 3.50.4 is built-in for database persistence.

### Affected Areas

This is a **new project** — everything will be created from scratch. The following are the structural areas that will be created:

- `pos/main.py` — Application entry point
- `pos/model/` — MVC Model layer (data + business logic)
- `pos/view/` — MVC View layer (CustomTkinter UI)
- `pos/controller/` — MVC Controller layer (orchestration)
- `pos/service/` — Business services (stock, reports, printing)
- `pos/repository/` — Data access layer (SQL queries)
- `pos/tests/` — Unit tests with pytest
- `requirements.txt` — Python dependencies
- `openspec/config.yaml` — Must update Python context

---

### Task 1: Project Structure — MVC Folder Layout

```
pos/
├── main.py                          # Entry point: init DB, launch main window
├── requirements.txt                 # Python dependencies
│
├── model/
│   ├── __init__.py
│   ├── database.py                  # SQLite connection manager, PRAGMA config
│   ├── product.py                   # Product dataclass: id, name, barcode, variant, price, cost, stock, weight_enabled, category_id
│   ├── category.py                  # Category dataclass: id, name, parent_id
│   ├── sale.py                      # Sale dataclass: id, items, total, discount, payment_method, created_at
│   ├── sale_item.py                 # SaleItem dataclass: product_id, quantity, unit_price, weight_grams
│   ├── payment.py                   # PaymentMethod enum: CASH, CARD, BANK_TRANSFER
│   ├── return.py                    # Return dataclass: original_sale_id, items, reason, created_at
│   └── enums.py                     # Shared enums: PaymentMethod, ProductVariant (ml, liters, unit, weight)
│
├── repository/
│   ├── __init__.py
│   ├── product_repo.py              # Product CRUD: search by barcode, name, category; stock queries
│   ├── category_repo.py             # Category CRUD
│   ├── sale_repo.py                 # Sale creation, daily/monthly/yearly aggregation
│   ├── sale_item_repo.py            # Line items for a sale
│   └── return_repo.py               # Return recording, stock restoration tracking
│
├── service/
│   ├── __init__.py
│   ├── stock_service.py             # Auto-deduct on sale, restore on return, low-stock warnings
│   ├── report_service.py            # Revenue, profit/loss, top products, period summaries
│   ├── discount_service.py          # Discount application logic (% and fixed amount)
│   └── printer_service.py           # Receipt formatting, thermal print orchestration
│
├── controller/
│   ├── __init__.py
│   ├── sale_controller.py           # New sale flow: add item, apply discount, complete payment
│   ├── product_controller.py        # CRUD operations, barcode lookup, stock updates
│   ├── report_controller.py         # Generate and export reports
│   ├── return_controller.py         # Process return, validate original sale, restore stock
│   ├── barcode_controller.py        # Barcode scanner input routing (keyboard wedge + serial)
│   └── printer_controller.py        # Trigger receipt printing after sale/return
│
├── view/
│   ├── __init__.py
│   ├── main_window.py               # Root window with CTkTabview container
│   ├── sale_view.py                 # POS terminal view: cart, total, payment buttons
│   ├── product_view.py              # CRUD form: product list, add/edit/delete dialog
│   ├── report_view.py               # Reports: date range picker, charts, table export
│   ├── return_view.py               # Direct return: product selection, quantity, refund
│   ├── cash_register_view.py        # Cash register open/close, movements
│   └── widgets/
│       ├── __init__.py
│       ├── barcode_entry.py         # Auto-submit on scan (Enter key), focus management
│       ├── cart_table.py            # Treeview for current sale items
│       ├── product_search.py        # Search by name + category filter
│       ├── numeric_keypad.py        # Optional: on-screen numpad for touchscreens
│       └── receipt_preview.py       # Preview receipt before printing
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # pytest fixtures: in-memory SQLite DB, sample products
│   ├── test_product_repo.py         # CRUD operations, barcode search
│   ├── test_sale_repo.py            # Sale creation, aggregation queries
│   ├── test_stock_service.py        # Deduct on sale, restore on return, edge cases
│   ├── test_report_service.py       # Profit/loss calculations, period summaries
│   ├── test_discount_service.py     # Discount math, stacking rules
│   └── test_return_controller.py    # Full return flow
│
└── resources/
    ├── icons/                       # App icons
    ├── logo.png                     # Business logo for receipts
    └── printer_profile.yaml         # Thermal printer configuration (vendor ID, profile)
```

**Key design decisions**:
- **Repository pattern** separates SQL from business logic — model classes are plain dataclasses, not ORM objects
- **Service layer** keeps complex business logic (stock, reports) out of controllers, making it testable
- **View has its own widget sub-package** for reusable Tkinter components
- **Tests mirror the structure** — one test file per module

---

### Task 2: Dependencies

| Package | Version | Purpose | Installation |
|---------|---------|---------|-------------|
| `customtkinter` | latest | Modern UI framework (built on Tkinter) | `pip install customtkinter` |
| `python-escpos` | latest | Thermal printer control via ESC/POS protocol (USB, serial, network) | `pip install python-escpos` |
| `python-barcode` | latest | Generate barcode images for labels | `pip install python-barcode` |
| `Pillow` | latest | Image processing (resize logos for printer, barcode image rendering) | `pip install pillow` |
| `pyserial` | latest | Serial port communication (serial barcode scanners, serial printers) | `pip install pyserial` |

**Built-in (no install needed)**:
- `sqlite3` — Database engine (SQLite 3.50.4)
- `dataclasses` — Model definitions
- `decimal` — Monetary calculations (avoids float precision issues)
- `datetime` — Date/time handling for reports
- `csv` — Report export
- `json` — Configuration files

**Total external deps**: 5 packages. Minimal, stable ecosystem.

---

### Task 3: Database — SQLite Schema (DEFINITIVE)

**Database**: SQLite (zero config, built-in, single-file backup)

**Configuration**:
```python
# model/database.py
import sqlite3

DB_PATH = "data/pos.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

**DEFINITIVE SCHEMA** (approved by user — includes suppliers and purchases):

```sql
-- CATEGORÍAS
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- PRODUCTOS
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    sale_price REAL NOT NULL,
    cost_price REAL NOT NULL,
    stock REAL NOT NULL DEFAULT 0,
    unit_type TEXT NOT NULL CHECK(unit_type IN ('unit', 'weight_kg', 'pack')),
    description TEXT,
    low_stock_threshold REAL DEFAULT 5,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_products_barcode ON products(barcode);
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category_id);

-- VENTAS
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0,
    payment_method TEXT NOT NULL CHECK(payment_method IN ('cash', 'card', 'transfer', 'mixed')),
    cash_register_id INTEGER REFERENCES cash_registers(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_sales_date ON sales(created_at);
CREATE INDEX idx_sales_payment ON sales(payment_method);

-- ITEMS DE VENTA
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    subtotal REAL NOT NULL
);
CREATE INDEX idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX idx_sale_items_product ON sale_items(product_id);

-- PROVEEDORES
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cuit TEXT,
    phone TEXT,
    address TEXT,
    email TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- COMPRAS
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER REFERENCES suppliers(id),
    total REAL NOT NULL,
    purchase_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_purchases_date ON purchases(purchase_date);
CREATE INDEX idx_purchases_supplier ON purchases(supplier_id);

-- ITEMS DE COMPRA
CREATE TABLE purchase_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_cost REAL NOT NULL,
    subtotal REAL NOT NULL
);
CREATE INDEX idx_purchase_items_purchase ON purchase_items(purchase_id);

-- CAJA
CREATE TABLE cash_registers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_amount REAL NOT NULL,
    opening_time TEXT NOT NULL,
    closing_amount REAL,
    closing_time TEXT,
    expected_amount REAL,
    difference REAL,
    close_reason TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed'))
);
CREATE INDEX idx_cash_registers_status ON cash_registers(status);
CREATE INDEX idx_cash_registers_time ON cash_registers(opening_time);

-- MOVIMIENTOS DE CAJA
CREATE TABLE cash_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    type TEXT NOT NULL CHECK(type IN ('sale_cash', 'return', 'supplier_payment', 'expense')),
    amount REAL NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_cash_movements_register ON cash_movements(cash_register_id);
CREATE INDEX idx_cash_movements_type ON cash_movements(type);
CREATE INDEX idx_cash_movements_date ON cash_movements(created_at);

-- DEVOLUCIONES
CREATE TABLE returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    refund_amount REAL NOT NULL,
    reason TEXT,
    cash_register_id INTEGER NOT NULL REFERENCES cash_registers(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_returns_product ON returns(product_id);
CREATE INDEX idx_returns_date ON returns(created_at);
CREATE INDEX idx_returns_cash_register ON returns(cash_register_id);
```

**KEY DESIGN DECISIONS**:

1. **Direct Atomic Return Flow**: Returns are NOT linked to original sales. They only reference the current cash register session (`cash_register_id`). This matches real-world kiosk/despensa behavior where customers rarely keep receipts.

2. **Cash Register Tracking**: `cash_registers` table tracks opening/closing amounts, expected vs actual, and differences. All sales and returns are associated with the active cash register session.

3. **Cash Movements**: Separate table for all cash movements (sales, returns, supplier payments, expenses) to maintain audit trail within a cash register session.

4. **Supplier & Purchase Management**: Full supplier tracking (`suppliers`) with purchase orders (`purchases`, `purchase_items`) for stock replenishment. Purchases update product stock and cost basis.

5. **Unit Types**: Products use `unit_type` CHECK constraint: 'unit' (discrete items), 'weight_kg' (sold by weight), 'pack' (multi-packs). No volume-based units (liters/ml) — volume is metadata only, not a sales unit.

6. **Low Stock Alerts**: `low_stock_threshold` per product for configurable stock warnings.

7. **Cascade Deletes**: `sale_items` and `purchase_items` cascade delete when parent sale/purchase is deleted (for error correction during same session).

8. **Strategic Indexes**: Indexes on frequently queried columns (barcode, name, dates, foreign keys) for performance without over-indexing.

---

### Task 4: Barcode Scanner Integration

**How Python receives barcode input**:

There are two common scanner types:

| Approach | How It Works | Python Library | Pros | Cons |
|----------|-------------|----------------|------|------|
| **Keyboard wedge (HID)** | Scanner emulates keyboard — types digits + Enter | None (Tkinter Entry + `<Return>` binding) | Zero deps, works with any USB scanner | Tied to focused widget, can't distinguish scanner vs keyboard typing |
| **Serial (COM port)** | Scanner connected via serial port | `pyserial` | Can read asynchronously, distinguish scanner input | Extra dep, serial port config needed, less common for modern USB scanners |

**Recommendation**: Support BOTH approaches.

- **Default**: Keyboard wedge — focus the barcode entry, scanner types the code + Enter, the `<Return>` event fires the lookup. Zero extra dependencies, works with 90%+ of USB scanners on the market.
- **Optional**: Serial scanner support via `pyserial` for users who have RS232/COM scanners. Configurable via a settings file.

**Implementation sketch**:
```python
# view/widgets/barcode_entry.py
import tkinter as tk

class BarcodeEntry(tk.Frame):
    def __init__(self, parent, on_scan_callback, **kwargs):
        super().__init__(parent)
        self.entry = tk.Entry(self, font=("Consolas", 16))
        self.entry.pack(fill="x")
        self.entry.bind("<Return>", lambda e: self._handle_scan())

    def _handle_scan(self):
        barcode = self.entry.get().strip()
        if barcode:
            self.on_scan_callback(barcode)
            self.entry.delete(0, "end")

    def focus(self):
        self.entry.focus_set()  # ensure scanner sends here
```

---

### Task 5: Thermal Printer — ESC/POS Libraries

| Library | Protocol | Printer Types | Maintenance | Stars |
|---------|----------|---------------|-------------|-------|
| **python-escpos** | ESC/POS | USB, Serial, Network, File | Active (135 snippets on Context7) | ~900 |
| **escpos (hennedo)** | ESC/POS | Partial implementation | Less active | Smaller |

**Recommendation: `python-escpos`**.

It's the de-facto standard Python library for thermal receipt printers:
- Supports Epson, Star, and ESC/POS-compatible printers
- Multiple connection types: USB (vendor ID + product ID), Serial, Network (TCP/IP), File
- Print text, images, barcodes, QR codes
- Built-in paper cut, cash drawer control
- Profile system for different printer models (TM-T88III, TM-T20, etc.)

**Implementation sketch**:
```python
# service/printer_service.py
from escpos.printer import Usb

class ReceiptPrinter:
    def __init__(self, vendor_id=0x04b8, product_id=0x0202, profile="TM-T88III"):
        self.printer = Usb(vendor_id, product_id, profile=profile)

    def print_receipt(self, sale_data: dict):
        self.printer.text(f"{'RECIBO DE VENTA':^32}\n")
        self.printer.text("=" * 32 + "\n")
        for item in sale_data["items"]:
            self.printer.text(f"{item['name']:<20} x{item['qty']}\n")
            self.printer.text(f"  ${item['subtotal']:>8.2f}\n")
        self.printer.text("=" * 32 + "\n")
        self.printer.text(f"{'TOTAL':<20} ${sale_data['total']:>8.2f}\n")
        self.printer.cut()
```

---

### Task 6: MVC Mapping

| Layer | Responsibility | Files | Testability |
|-------|---------------|-------|-------------|
| **Model** | Data structures + database schema | `model/` dataclasses, `repository/` SQL access, `service/` business logic | **High** — pure functions, no UI dependency |
| **View** | Tkinter windows, frames, widgets, user input capture | `view/` — Tk classes, event bindings, layout | **Low** — UI is hard to automate; manual QA recommended |
| **Controller** | Orchestrates View events → Model updates | `controller/` — receives view events, calls services/repos, updates view | **High** — inject mock repos/services, no UI |

**Data flow example — Complete Sale**:

```
User clicks "Add Item" (View)
  → View calls sale_controller.add_product(barcode/qty)
    → Controller calls product_repo.find_by_barcode(barcode)
    → Controller calls stock_service.check_availability(product, qty)
    → Controller updates Sale model (adds SaleItem)
    → Controller calls view.update_cart_display(items, total)

User clicks "Pay" (View)
  → View calls sale_controller.complete_sale(payment_method, discount)
    → Controller calls discount_service.apply(discount, total)
    → Controller calls stock_service.deduct_stock(items)
    → Controller calls sale_repo.create(sale)
    → Controller calls printer_service.print_receipt(sale)
    → Controller calls view.show_receipt_preview(sale)
    → Controller calls view.reset_for_new_sale()
```

**Why this works**:
- Controllers depend on abstractions (repositories/services), not on views
- Services contain pure business logic — no Tkinter imports
- Repositories encapsulate SQL — easy to swap DB later
- Views are dumb — they render and emit events, nothing more

---

### Task 7: UI Framework — CustomTkinter

**Choice**: CustomTkinter (modern UI library built on top of Tkinter)

**Why CustomTkinter**:
- Modern appearance with rounded corners, dark mode support, and contemporary widgets
- Built on top of Tkinter (familiar API, same event model)
- No GPL license restrictions (MIT license)
- Easy migration path from Tkinter code
- Active maintenance and good documentation

**Installation**: `pip install customtkinter`

**Key widgets**:
- `CTkButton`, `CTkEntry`, `CTkLabel` — modern styled versions
- `CTkFrame`, `CTkScrollableFrame` — containers with modern look
- `CTkTabview` — tab navigation (Sales, Products, Reports, Returns)
- `CTkComboBox`, `CTkOptionMenu` — dropdown selections
- `CTkTextbox` — multi-line text areas
- Dark/light theme switching built-in

**Implementation sketch**:
```python
# view/main_window.py
import customtkinter as ctk

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("POS System")
        self.geometry("1200x800")
        
        # Tab navigation
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True)
        
        # Add tabs
        self.sale_tab = self.tabview.add("Sales")
        self.product_tab = self.tabview.add("Products")
        self.report_tab = self.tabview.add("Reports")
        self.return_tab = self.tabview.add("Returns")
```

**Note**: CustomTkinter does NOT have a Treeview widget. For tables (cart, product list), we'll need to use:
- `tkinter.ttk.Treeview` (classic Tkinter widget, works alongside CustomTkinter)
- OR custom scrollable frame with labels (more work, less feature-rich)

Recommendation: Use `ttk.Treeview` for data tables, styled to match CustomTkinter theme.

---

### Task 8: Testing Strategy

**Tool**: `pytest` (via `pip install pytest pytest-mock`)

**Approach**:

| Layer | Test Strategy | Tool | Coverage Target |
|-------|--------------|------|-----------------|
| **Model** (dataclasses) | Test creation, validation, enum behavior | pytest | 100% |
| **Repository** | SQLite `:memory:` DB per test, verify SQL queries | pytest + conftest fixtures | 90%+ |
| **Service** | Pure business logic — inject mock repos, test edge cases | pytest + pytest-mock | 95%+ |
| **Controller** | Inject mock repos + mock services, test orchestration flow | pytest + pytest-mock | 80%+ |
| **View** | Manual testing only (Tkinter is hard to automate) | Manual QA | 0% (manual) |

**conftest.py fixtures**:
```python
# tests/conftest.py
import pytest
import sqlite3

@pytest.fixture
def db():
    """In-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Run schema DDL here or import from model.database
    yield conn
    conn.close()

@pytest.fixture
def sample_product(db):
    db.execute(
        "INSERT INTO products (barcode, name, sale_price, cost_price, stock) "
        "VALUES (?, ?, ?, ?, ?)",
        ("7791234567890", "Test Wine", 150.0, 80.0, 10)
    )
    db.commit()
```

**Example test**:
```python
# tests/test_stock_service.py
class TestStockService:
    def test_deduct_stock_reduces_quantity(self, db, sample_product):
        stock_service = StockService(db)
        stock_service.deduct(product_id=1, quantity=3)
        product = db.execute("SELECT stock FROM products WHERE id=1").fetchone()
        assert product["stock"] == 7  # 10 - 3

    def test_deduct_insufficient_stock_raises(self, db, sample_product):
        stock_service = StockService(db)
        with pytest.raises(InsufficientStockError):
            stock_service.deduct(product_id=1, quantity=99)
```

---

---

## MVP SCOPE (Version 1.0)

### IN SCOPE (What enters MVP)
- Cash sales management (cash, card, transfer, mixed payments)
- Automatic stock control (deduct on sale, restore on return)
- Products and Categories CRUD (ABM)
- Unit types: unit (discrete), weight_kg (by weight), pack (multi-packs)
- Cash register control (open/close/movements with cash counting)
- Excel import for products (openpyxl)
- Basic reports (sales, profits, filtered by date)
- Non-fiscal receipt printing (thermal printer)

### OUT OF SCOPE (What stays out of MVP)
- Fiscal module (ARCA/AFIP integration)
- Customer accounts / credit tracking ("fiado")
- Barcode label generation/printing
- Serial scale integration
- Multi-register network sales

---

## FUNCTIONAL REQUIREMENTS & PRIORITIZATION

### PRIORITY 1 — Critical for operations (MVP must-have)

**Sales Module:**
- Barcode scanner input (keyboard wedge) + manual entry fallback
- Add items to cart with quantity adjustment
- Real-time total calculation
- Payment methods: cash, card, transfer, mixed
- Change calculation for cash payments
- Automatic stock deduction on sale confirmation
- Cash register movement registration

**Cash Register Control:**
- Opening with initial balance
- Cash outflow registration (supplier payments, expenses)
- Closing with cash counting (expected vs actual, difference calculation)
- Single active register enforcement (only one open at a time)

**Direct Atomic Return:**
- Product lookup by barcode scan (same as sales flow)
- Quantity input with default = 1
- Refund calculation: current_price × quantity
- Automatic stock restoration
- Cash register movement registration (type: return)
- NO linkage to original sale (atomic, session-based)

### PRIORITY 2 — Necessary for management (MVP should-have)

**Products & Categories CRUD:**
- Product creation with barcode uniqueness validation
- Product editing (update timestamp)
- Product deletion (blocked if has sales/purchase history)
- Category CRUD with product association validation

**Excel Import:**
- Import products from .xlsx files
- Column validation (barcode, name, sale_price, cost_price, stock, unit_type)
- Duplicate detection (in file and in database)
- Batch import with error reporting per row

**Reports:**
- Sales report by date range (total, count, average ticket)
- Top 10 products (by quantity and amount)
- Profit report (revenue - cost, margin %)
- Filter by payment method, category
- Export to CSV

### PRIORITY 3 — Optional / Nice-to-have (MVP can defer)

**Purchases & Suppliers:**
- Supplier CRUD (name, CUIT, phone, address, email)
- Purchase registration (supplier, date, items with cost)
- Automatic stock addition on purchase confirmation
- Supplier payment tracking (cash movement)

---

## USER FLOWS

### PRIORITY 1 — Critical for operations

#### Flow 1.1: Product Sale (P1)
1. Cashier opens "Sales" view (default main screen)
2. Scans barcode OR enters code manually
3. System finds product, shows name + price + available stock
4. If product not found or insufficient stock → shows alert
5. Cashier can adjust quantity (default: 1)
6. System adds item to cart, updates subtotal and total
7. Repeats steps 2-6 until sale is complete
8. Cashier selects payment method (cash/card/transfer/mixed)
9. If cash: enters amount received → system calculates change
10. Cashier confirms sale → system deducts stock, registers in cash register, prints receipt
11. Cart clears for next sale

#### Flow 1.2: Direct Return (P1)
1. Cashier opens "Returns" view
2. **Scans product barcode** (same as sales flow) → system finds product automatically
3. System shows product name + current price
4. Cashier enters quantity to return (default: 1)
5. System calculates refund amount (current_price × quantity)
6. Cashier enters reason (optional)
7. Cashier confirms return → system:
   - Restores product stock
   - Registers cash movement (type: return, cash outflow)
   - Records atomic return (linked to current cash_register_id)
8. Optionally prints return receipt

#### Flow 1.3: Cash Register Opening (P1)
1. Cashier opens "Cash Register" view
2. If register already open → system shows alert "There is already an open register"
3. Enters initial amount (cash in register)
4. Confirms opening → system records timestamp + status "open"
5. View shows current register with real-time movements

#### Flow 1.4: Cash Register Outflow (P1)
1. With open register, cashier opens "Cash Register" view
2. Selects outflow type (supplier_payment / expense / other)
3. Enters amount + description
4. Confirms → system registers movement and updates expected balance

#### Flow 1.5: Cash Register Closing with Cash Counting (P1)
1. Cashier opens "Cash Register" view with open register
2. System shows: initial amount, cash sales, returns, outflows, expected balance
3. Cashier enters actual counted amount (physical cash in register)
4. System calculates difference (actual - expected)
5. Cashier enters closing reason
6. Confirms closing → system:
   - Updates status to "closed"
   - Records closing amount, difference, reason
   - Blocks new sales until next opening

---

### PRIORITY 2 — Necessary for management

#### Flow 2.1: Product Creation (P2)
1. User opens "Products" view
2. Clicks "New product"
3. Fills form: barcode, name, category (dropdown), sale price, cost price, initial stock, unit type (unit/weight_kg/pack), low stock threshold
4. Validates barcode is not duplicated
5. Confirms → system creates product with timestamps

#### Flow 2.2: Product Editing (P2)
1. User opens "Products" view
2. Searches product (by code/name/category)
3. Selects product from list
4. Clicks "Edit"
5. Modifies allowed fields (barcode change blocked if duplicate exists)
6. Confirms → system updates product + updated_at timestamp

#### Flow 2.3: Product Deletion (P2)
1. User searches and selects product
2. Clicks "Delete"
3. System validates: if product has sales or purchases → **blocks deletion with error message** "Product has transaction history and cannot be deleted. Set stock to 0 instead."
4. If product has NO history → system deletes physically

#### Flow 2.4: Category CRUD (P2)
1. User opens "Products" view → "Categories" section
2. Create: enters unique name → confirms
3. Edit: selects category, modifies name → confirms
4. Delete: validates no products are associated → **blocks deletion with error** "Category has associated products and cannot be deleted."

#### Flow 2.5: Excel Mass Import (P2)
1. User opens "Products" view → "Import from Excel" button
2. Selects .xlsx file
3. System reads file, validates required columns (barcode, name, sale_price, cost_price, stock, unit_type)
4. Shows preview of data to import (first 10 rows)
5. Validates: duplicate codes, negative prices, invalid unit types
6. If errors → shows list of problematic rows
7. If all OK → confirms import → system creates products in batch
8. Shows summary: "X products imported, Y skipped (duplicates)"

#### Flow 2.6: Sales Report by Period (P2)
1. User opens "Reports" view
2. Selects date range (from/to)
3. Optionally filters by: payment method, product category
4. System generates report:
   - Total sold (breakdown by payment method)
   - Number of sales
   - Average ticket
   - Top 10 best-selling products
   - Gross profit (sales - cost)
5. Shows table + option to export to CSV

#### Flow 2.7: Profit Report (P2)
1. User opens "Reports" view → "Profits" tab
2. Selects date range
3. System calculates:
   - Total revenue (sum of sales)
   - Total cost (sum of cost of products sold)
   - Gross profit (revenue - cost)
   - Profit margin (%)
4. Shows breakdown by product or category
5. Option to export to CSV

---

### PRIORITY 3 — Optional / Nice-to-have

#### Flow 3.1: Supplier Creation (P3)
1. User opens "Suppliers" view
2. Clicks "New supplier"
3. Fills: name, CUIT, phone, address, email
4. Confirms → system creates supplier

#### Flow 3.2: Purchase Registration (P3)
1. User opens "Purchases" view → "New purchase"
2. Selects supplier
3. Enters purchase date
4. Adds items: product + quantity + unit cost
5. System calculates subtotal per item and grand total
6. Confirms purchase → system:
   - Creates purchase record
   - Adds stock to products
   - Updates average cost (if applicable)
   - Optionally registers cash movement (if paid immediately)

#### Flow 3.3: Supplier Payment (P3)
1. With open register, user opens "Purchases" view
2. Selects pending purchase
3. Enters paid amount
4. System registers cash movement (type: supplier_payment)

---

## ACCEPTANCE CRITERIA

### PRIORITY 1 — Critical for operations

#### Sales Module (P1)
- [ ] Barcode search works with USB scanner (keyboard wedge)
- [ ] Manual code search works if scanner unavailable
- [ ] Scanning non-existent product → shows clear alert
- [ ] Scanning product with insufficient stock → shows alert with current stock
- [ ] Cart shows: product name, quantity, unit price, subtotal
- [ ] Total updates in real-time when adding/removing items
- [ ] Can modify quantity of an already-added item
- [ ] Can remove an item from cart before confirming sale
- [ ] Payment methods: cash, card, transfer, mixed (combined)
- [ ] If cash payment: "Amount received" field → calculates change automatically
- [ ] On sale confirmation: deducts stock from all sold items
- [ ] On sale confirmation: registers sale in `sales` + items in `sale_items`
- [ ] On sale confirmation: registers cash movement (if cash payment)
- [ ] Thermal receipt prints automatically (optional, can be disabled)
- [ ] Cart clears automatically after successful sale

#### Direct Return (P1)
- [ ] Product lookup by barcode scan (same as sales flow)
- [ ] Product lookup by name search (fallback)
- [ ] Quantity field with default = 1, editable
- [ ] Refund calculation: sale_price × quantity (uses current price, not historical)
- [ ] Reason field optional (free text)
- [ ] On confirmation: restores product stock
- [ ] On confirmation: registers in `returns` table with `cash_register_id` from current session
- [ ] On confirmation: registers cash movement type "return" (cash outflow)
- [ ] NO original sale ID required (atomic return)
- [ ] Return receipt optional (printable)

#### Cash Register Control (P1)
- [ ] Opening: "Initial amount" field mandatory (>= 0)
- [ ] Opening: records timestamp + status "open"
- [ ] Only ONE register can be open at a time
- [ ] If attempting to open second register → alert "There is already an open register"
- [ ] Register view shows: initial amount, cash sales, returns, outflows, expected balance
- [ ] Outflow registration: type (supplier_payment/expense), amount, description
- [ ] Closing: "Actual counted amount" field mandatory
- [ ] Closing: calculates difference (actual - expected) automatically
- [ ] Closing: "Reason" field mandatory
- [ ] On closing: status changes to "closed", closing timestamp
- [ ] With closed register: cannot register sales or movements
- [ ] Previous register history accessible (read-only)

---

### PRIORITY 2 — Necessary for management

#### Product CRUD (P2)
- [ ] Create: mandatory fields (name, sale_price, cost_price, unit_type)
- [ ] Create: barcode unique (validates duplicates)
- [ ] Create: category selectable from dropdown (or create new inline)
- [ ] Create: initial stock default = 0 if not specified
- [ ] Create: low stock threshold default = 5 if not specified
- [ ] Edit: allows modifying all fields except barcode if duplicate exists
- [ ] Edit: updates updated_at timestamp automatically
- [ ] Delete: if product has sales or purchases → **blocks with error** "Product has transaction history and cannot be deleted. Set stock to 0 instead."
- [ ] Delete: if product has NO history → deletes physically
- [ ] Product list: search by code, name, category
- [ ] Product list: sorting by columns
- [ ] Product list: pagination if > 50 products

#### Category CRUD (P2)
- [ ] Create: unique name (validates duplicates)
- [ ] Edit: allows modifying name
- [ ] Delete: if category has products → **blocks with error** "Category has associated products and cannot be deleted."
- [ ] Category list: shows product count per category

#### Excel Import (P2)
- [ ] Accepts .xlsx files (modern Excel format)
- [ ] Required columns: barcode, name, sale_price, cost_price, stock, unit_type
- [ ] Optional columns: category_name, description, low_stock_threshold
- [ ] Validates data types: prices >= 0, stock >= 0, unit_type in ('unit', 'weight_kg', 'pack')
- [ ] Preview of first 10 rows before confirming import
- [ ] Detects duplicate barcodes (in file or in database)
- [ ] Shows errors per row: "Row 5: negative price", "Row 12: duplicate code"
- [ ] Batch import (transaction: all or nothing)
- [ ] Post-import summary: "X products created, Y skipped"

#### Reports (P2)
- [ ] Sales report: filter by date range (mandatory)
- [ ] Sales report: optional filter by payment method
- [ ] Sales report: optional filter by product category
- [ ] Metrics: total sold, number of sales, average ticket
- [ ] Metrics: top 10 best-selling products (by quantity and by amount)
- [ ] Profit report: total revenue, total cost, gross profit, margin %
- [ ] Profit breakdown by product or category
- [ ] Export to CSV (Excel compatible)
- [ ] Performance: 1-year report with 10k sales generates in < 3 seconds

---

### PRIORITY 3 — Optional / Nice-to-have

#### Supplier CRUD (P3)
- [ ] Create: name mandatory, CUIT/phone/address/email optional
- [ ] Edit: allows modifying all fields
- [ ] Delete: if supplier has purchases → alert "Supplier has transaction history"
- [ ] Supplier list: search by name or CUIT

#### Purchase Registration (P3)
- [ ] Supplier selection from dropdown
- [ ] Purchase date mandatory (default: today)
- [ ] Add items: product + quantity + unit cost
- [ ] Automatic calculation of subtotal per item and grand total
- [ ] "Notes" field optional (free text)
- [ ] On confirmation: creates record in `purchases` + `purchase_items`
- [ ] On confirmation: adds stock to products
- [ ] On confirmation: optionally registers cash movement (if paid immediately)
- [ ] Purchase list: filter by supplier, date range

---

## Recommendation Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture** | MVC + Repository + Service | Clean separation, testable layers, future-proof for view swap |
| **Database** | SQLite | Zero config, built-in, single-user POS ideal |
| **Return Policy** | Direct Atomic Return | No ticket linkage, only cash register session. Matches kiosk/despensa reality |
| **Barcode** | Keyboard wedge (default) + optional serial | 90%+ of scanners work with Entry + Return binding |
| **Printer** | `python-escpos` | Mature, active, ESC/POS standard, multiple connection types |
| **UI Framework** | CustomTkinter | Modern appearance, MIT license, built on Tkinter familiarity |
| **Testing** | pytest + in-memory SQLite | Model/repository/service layers fully testable |
| **External deps** | 5 packages (`customtkinter`, `python-escpos`, `python-barcode`, `Pillow`, `pyserial`) | Minimal, stable, well-maintained |

### Risks

1. **Python version specificity**: Python 3.12 is stable but verify library compatibility (customtkinter, python-escpos, Pillow) before committing to all deps.
2. **Barcode scanner variability**: While keyboard wedge works for most scanners, some budget scanners have quirks (extra prefix/suffix chars, duplicate Enter keys). Need to handle input sanitization.
3. **Thermal printer profiles**: `python-escpos` works with Epson and Star printers, but obscure/no-name thermal printers may have incomplete ESC/POS support. Need a configuration step for printer setup.
4. **CustomTkinter Treeview limitation**: CustomTkinter does NOT include a Treeview widget. Must use `tkinter.ttk.Treeview` for data tables and style it to match the modern theme.
5. **Single-user assumption**: SQLite handles single-user well, but if multi-user access is ever needed, the entire data layer would need migration to PostgreSQL/MySQL.
6. **Direct Return auditability**: Atomic returns without ticket linkage simplify UX but reduce traceability. Cash register session tracking (`cash_register_id`) provides the audit trail instead.

### Ready for Next Phase

**EXPLORE PHASE: COMPLETED** ✅

The exploration is complete with:
- ✅ Architecture decisions (MVC + Repository + Service)
- ✅ Stack selection (Python 3.12 + CustomTkinter + SQLite)
- ✅ Database schema (10 tables + indexes)
- ✅ MVP scope defined (in/out)
- ✅ Functional requirements prioritized (P1/P2/P3)
- ✅ User flows documented (13 flows)
- ✅ Acceptance criteria specified (40+ criteria)

**Next step**: Proceed to `/sdd-propose` to create the formal change proposal.

- Change name: `pos-sales-system`
- Architecture: MVC + Repository + Service
- Stack: Python 3.12 + CustomTkinter + SQLite + python-escpos
- Return Policy: Direct Atomic Return (cash register session linkage only)
- Delivery strategy: Start with single-PR (new project, no existing code to conflict with)
