# Proposal: Login System with Role-Based Access Control

## Intent

The POS application currently has no authentication or authorization mechanism. Any user can access all modules and perform any operation. This creates security risks (unauthorized access to sensitive operations like cash register management) and prevents accountability (no way to track which user performed specific actions).

This change adds a login system with role-based access control (RBAC) to restrict module access based on user roles, enabling proper separation of duties and audit trails.

## Scope

### In Scope
- Login screen with username/password authentication
- Four user roles: admin (superuser), gerente, cajero, inventario
- Fixed permission sets per role (no custom permission assignment)
- User management interface (admin only)
- Session management with logout functionality
- Current user/role display in main window
- Plain text password storage (school/practical system, no hashing)
- Hardcoded admin user (admin/admin123) created at startup

### Out of Scope
- Password hashing or encryption
- Password reset/recovery flows
- Custom role creation or permission editing
- Multi-factor authentication
- Session timeout or auto-logout
- Audit logging of user actions (future enhancement)
- User profile management (name, email, etc.)

## Capabilities

### New Capabilities
- `user-auth`: Authentication flow (login screen, credential validation, session creation)
- `role-permissions`: Role-based permission enforcement (module access, field-level restrictions)
- `user-management`: Admin interface for creating/editing/deactivating users
- `session-display`: Current user/role display and logout functionality

### Modified Capabilities
None (no existing capabilities change at the spec level — this is purely additive)

## Approach

### Database Schema
Add two new tables:
- `users`: id, username (unique), password, role, is_active, created_at
- `sessions`: id, user_id, login_time, logout_time (optional)

Roles stored as TEXT with CHECK constraint: `role IN ('admin', 'gerente', 'cajero', 'inventario')`

### Permission Matrix
Hardcoded in a service layer (not database-driven):

| Role | Ventas | Productos | Devoluciones | Caja | Reportes |
|------|--------|-----------|--------------|------|----------|
| admin | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| gerente | ❌ | ✅ Full | ❌ | ⚠️ View history only | ✅ Full |
| cajero | ✅ Full | ❌ | ✅ Full | ⚠️ No history, no diferencia/esperado fields | ❌ |
| inventario | ❌ | ✅ Full (CRUD products, categories, Excel import/export) | ❌ | ❌ | ❌ |

**Permission Details**:
- **admin**: Full access to all modules + user management
- **gerente**: Products (full CRUD), Cash Register (view history only, no open/close/expense registration), Reports (full access)
- **cajero**: Sales (full), Returns (full), Cash Register (no history, no diferencia/esperado fields)
- **inventario**: Products module only with full CRUD permissions (create/read/update/delete products, manage categories, Excel import/export)

### Application Flow
1. `main.py` checks for active session → if none, show `LoginView`
2. `LoginView` validates credentials via `AuthService`
3. On success, create session record, store current user in memory, launch `MainWindow`
4. `MainWindow` reads permissions from `PermissionService` and:
   - Hides/disables tabs the user cannot access
   - Passes permission context to views for field-level restrictions (e.g., hide "diferencia" field for cajero)
5. Logout button destroys main window, clears session, returns to login

### Architecture Layers
- **Model**: `User` dataclass, `UserRole` enum
- **Repository**: `UserRepo` (CRUD for users table), `SessionRepo` (session tracking)
- **Service**: `AuthService` (login/logout logic), `PermissionService` (role → permissions mapping)
- **Controller**: `LoginController` (orchestrate login flow), `UserManagementController` (admin CRUD)
- **View**: `LoginView` (login form), `UserManagementView` (admin user list + create/edit form)

### Integration Points
- `main.py`: Add login gate before `MainWindow` instantiation
- `MainWindow`: Add user/role label in top bar, logout button, tab visibility logic
- `CashRegisterView`: Conditionally hide/disable buttons based on role (open/close, expenses)
- `CashRegisterView`: Hide "diferencia" and "esperado" fields for cajero role
- `ProductView`: Receive permission context; inventario role has full CRUD access (products, categories, Excel import/export)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `pos/model/user.py` | New | User dataclass and UserRole enum |
| `pos/model/database.py` | Modified | Add users and sessions tables to DDL + migration |
| `pos/repository/user_repo.py` | New | CRUD operations for users table |
| `pos/repository/session_repo.py` | New | Session creation and tracking |
| `pos/service/auth_service.py` | New | Login/logout logic, credential validation |
| `pos/service/permission_service.py` | New | Role → permission mapping, access checks |
| `pos/controller/login_controller.py` | New | Orchestrate login flow |
| `pos/controller/user_management_controller.py` | New | Admin user CRUD operations |
| `pos/view/login_view.py` | New | Login form (username, password, submit button) |
| `pos/view/user_management_view.py` | New | User list, create/edit form (admin only) |
| `pos/view/main_window.py` | Modified | Add user/role label, logout button, tab visibility logic |
| `pos/view/cash_register_view.py` | Modified | Conditional UI elements based on role permissions |
| `pos/view/product_view.py` | Modified | Receive permission context for inventario role (full CRUD access) |
| `pos/main.py` | Modified | Add login gate before MainWindow, wire auth services |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Plain text passwords expose credentials if DB is compromised | High | Document this is intentional for school project. Add comment in code warning against production use. |
| Existing 21 test files break due to new required auth flow | Medium | Make login optional in test mode. Add `test_mode` flag to skip auth in conftest.py. |
| Tab visibility logic conflicts with existing cross-view wiring | Medium | Test all cross-view callbacks (sale→cash, return→cash, product refresh) with each role. |
| Admin user hardcoded, cannot be deleted or renamed | Low | Document this as intentional. Admin is bootstrap user for initial setup. |
| Field-level restrictions (cajero hiding diferencia/esperado) require view modifications | Medium | Pass permission context to views, use conditional rendering. Test with all roles. |

## Rollback Plan

1. Remove `users` and `sessions` tables from database (or leave them, they're additive)
2. Revert `pos/main.py` to remove login gate
3. Revert `pos/view/main_window.py` to remove user display and tab visibility logic
4. Revert `pos/view/cash_register_view.py` to remove conditional UI elements
5. Delete new files: `user.py`, `user_repo.py`, `session_repo.py`, `auth_service.py`, `permission_service.py`, `login_controller.py`, `user_management_controller.py`, `login_view.py`, `user_management_view.py`

Since this is purely additive (new tables, new files, minimal modifications to existing files), rollback is straightforward: remove the new code and revert the 3 modified files.

## Dependencies

- Python 3.12 (existing)
- CustomTkinter (existing)
- SQLite (existing)
- No new external dependencies required

## Success Criteria

- [ ] Login screen appears before main window on application start
- [ ] Hardcoded admin user (admin/admin123) can log in successfully
- [ ] Admin can create new users with gerente, cajero, or inventario roles
- [ ] Each role sees only the tabs they're authorized to access
- [ ] Gerente cannot open/close cash register or register expenses (Caja tab shows history only)
- [ ] Cajero cannot see "diferencia" or "esperado" fields in Caja tab
- [ ] Cajero cannot access Productos or Reportes tabs
- [ ] Inventario can only access Productos tab with full CRUD permissions (products, categories, Excel import/export)
- [ ] Current user and role displayed in main window top bar
- [ ] Logout button returns to login screen and clears session
- [ ] All 21 existing test files continue to pass (test mode bypasses auth)
- [ ] No ORM used, all queries parameterized
- [ ] Code follows existing MVC + Repository + Service pattern
