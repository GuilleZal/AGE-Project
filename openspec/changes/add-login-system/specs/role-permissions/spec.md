# Role Permissions Specification

## Purpose

Defines the hardcoded permission matrix, tab visibility logic in `MainWindow`, and field-level restrictions within `CashRegisterView` and `ProductView`.

## Requirements

### Requirement: Permission Matrix

The system SHALL enforce a fixed permission matrix stored in `PermissionService` (not database-driven). Each role maps to a set of allowed modules and access levels.

| Role | Ventas | Productos | Devoluciones | Caja | Reportes |
|------|--------|-----------|--------------|------|----------|
| admin | Full | Full | Full | Full | Full |
| gerente | Denied | Full | Denied | History-only | Full |
| cajero | Full | Denied | Full | Restricted | Denied |
| inventario | Denied | Full (CRUD) | Denied | Denied | Denied |

#### Scenario: Admin has full access

- GIVEN an authenticated admin user
- WHEN `PermissionService.get_permissions('admin')` is called
- THEN all five modules are returned with `Full` access level

#### Scenario: Cajero denied from Productos

- GIVEN an authenticated cajero user
- WHEN `PermissionService.can_access('cajero', 'Productos')` is called
- THEN it returns `False`

#### Scenario: Inventario accesses only Productos

- GIVEN an authenticated inventario user
- WHEN permissions are queried for each module
- THEN only `Productos` returns `True`; all others return `False`

### Requirement: Tab Visibility in MainWindow

`MainWindow` SHALL hide tabs the current role cannot access. Hidden tabs MUST NOT be renderable or focusable. The tab bar MUST reflect only permitted modules at construction time.

#### Scenario: Cajero sees only Ventas, Devoluciones, Caja

- GIVEN a cajero is authenticated
- WHEN `MainWindow` is constructed with the cajero permission context
- THEN the tabview contains exactly "Ventas", "Devoluciones", "Caja"

#### Scenario: Gerente sees Productos, Caja, Reportes

- GIVEN a gerente is authenticated
- WHEN `MainWindow` is constructed
- THEN the tabview contains exactly "Productos", "Caja", "Reportes"

#### Scenario: Inventario sees only Productos

- GIVEN an inventario user is authenticated
- WHEN `MainWindow` is constructed
- THEN the tabview contains only "Productos"

### Requirement: Caja Field-Level Restrictions (Gerente)

When the authenticated user is `gerente`, `CashRegisterView` SHALL display the history treeview and the movement preview panel (showing products/movements of the selected register). The open/close buttons and expense registration form MUST be hidden or disabled.

#### Scenario: Gerente cannot open cash register

- GIVEN a gerente is viewing the Caja tab
- WHEN the view renders
- THEN the "Abrir caja" button is not visible

#### Scenario: Gerente cannot register expenses

- GIVEN a gerente is viewing the Caja tab
- WHEN the view renders
- THEN the outflow registration form is not visible

#### Scenario: Gerente can view history

- GIVEN a gerente is viewing the Caja tab
- WHEN the view renders
- THEN the history treeview is visible and populated with past sessions

#### Scenario: Gerente can view movements of selected register

- GIVEN a gerente is viewing the Caja tab
- WHEN the gerente selects a register from the history treeview
- THEN the movement preview panel displays the products/movements of that register

### Requirement: Caja Field-Level Restrictions (Cajero)

When the authenticated user is `cajero`, `CashRegisterView` SHALL hide the history treeview, the "diferencia" label/field, and the "esperado" label/field.

#### Scenario: Cajero cannot see history

- GIVEN a cajero is viewing the Caja tab
- WHEN the view renders
- THEN the history treeview is not visible

#### Scenario: Cajero cannot see diferencia field

- GIVEN a cajero is viewing the Caja tab
- WHEN the view renders
- THEN the "diferencia" label and its value are not visible

#### Scenario: Cajero cannot see esperado field

- GIVEN a cajero is viewing the Caja tab
- WHEN the view renders
- THEN the "esperado" label and its value are not visible

### Requirement: ProductView Permission Context

`ProductView` SHALL accept a permission context indicating the user's role. The `inventario` role MUST have full CRUD access (create, read, update, delete products, manage categories, Excel import/export) identical to admin.

#### Scenario: Inventario has full product CRUD

- GIVEN an inventario user is viewing the Productos tab
- WHEN the view renders
- THEN all action buttons (New, Edit, Delete, Import Excel) and category management are visible and functional

#### Scenario: Cross-view wiring preserved for permitted roles

- GIVEN a user with access to both Ventas and Productos
- WHEN a quick-create product occurs in SaleView
- THEN `ProductView._refresh_products` is called as before
