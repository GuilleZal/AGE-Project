# Tasks: Login System with Role-Based Access Control

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1200-1400 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Services+Controllers) → PR 3 (Views+Integration) → PR 4 (Tests) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Models, repos, DB migration (foundation layer) | PR 1 | Base: main. All tests pass (DDL additive). ~350 lines |
| 2 | Auth service, permission service, both controllers | PR 2 | Base: PR 1 branch. Unit-testable without UI. ~300 lines |
| 3 | LoginView, UserManagementView, MainWindow/CashRegister/ProductView mods, main.py wiring | PR 3 | Base: PR 2 branch. Full integration. ~370 lines |
| 4 | New test files for all auth components | PR 4 | Base: PR 3 branch. ~420 lines |

## Phase 1: Foundation (Models + Database + Repositories)

- [ ] 1.1 Add `UserRole(str, Enum)` to `pos/model/enums.py` with values ADMIN, GERENTE, CAJERO, INVENTARIO (~8 LOC)
- [ ] 1.2 Create `pos/model/user.py` with `User`, `Session`, `PermissionContext` dataclasses per design §2 (~50 LOC)
- [ ] 1.3 Add `users` + `sessions` tables to `DDL` string in `pos/model/database.py` and add Migration 7 in `_run_migrations()` per design §1.1-1.2 (~30 LOC)
- [ ] 1.4 Create `pos/repository/user_repo.py` with `UserRepo` class: `find_by_username`, `find_by_id`, `create`, `update`, `get_all`, `_from_row` per design §3.1 (~80 LOC)
- [ ] 1.5 Create `pos/repository/session_repo.py` with `SessionRepo` class: `create_session`, `close_session`, `get_active_session`, `_from_row` per design §3.2 (~55 LOC)
- [ ] 1.6 Verify: `python -c "from pos.model.user import User, Session, PermissionContext; from pos.repository.user_repo import UserRepo; from pos.repository.session_repo import SessionRepo"` imports cleanly

## Phase 2: Services + Controllers

- [ ] 2.1 Create `pos/service/auth_service.py` with `AuthService`: `login`, `logout`, `bootstrap_admin`, `create_synthetic_admin` per design §4.1 (~70 LOC)
- [ ] 2.2 Create `pos/service/permission_service.py` with `PermissionService`: `_TAB_PERMISSIONS`, `_CASH_MODE` dicts, `can_access`, `get_permissions`, `get_allowed_tabs`, `get_cash_register_mode` per design §4.2 (~65 LOC)
- [ ] 2.3 Create `pos/controller/login_controller.py` with `LoginController`: `validate`, `validate_input`, `logout`, `bootstrap_admin` per design §5.1 (~65 LOC)
- [ ] 2.4 Create `pos/controller/user_management_controller.py` with `UserManagementController`: `create_user`, `list_users`, `update_user`, `deactivate_user`, `activate_user`, `is_admin_protected` per design §5.2 (~100 LOC)
- [ ] 2.5 Verify: instantiate `LoginController(db)` and `UserManagementController(db)` against in-memory DB; call `bootstrap_admin()`, `validate("admin", "admin123")` returns success dict

## Phase 3: Views + Integration

- [ ] 3.1 Create `pos/view/login_view.py` with `LoginView(ctk.CTk)`: 400x300 window, username/password fields, submit button, error label, Enter key binding, `set_controller`, `show_error`, `get_username`, `get_password`, `_on_submit` per design §6.1 (~100 LOC)
- [ ] 3.2 Create `pos/view/user_management_view.py` with `UserManagementView(ctk.CTkFrame)`: user list treeview (username/role/status), create/edit form, deactivate toggle, `set_controller`, `refresh_users` per design §6.2 (~180 LOC)
- [ ] 3.3 Modify `pos/view/main_window.py`: accept `PermissionContext` param, add user/role label + logout button in top bar, filter tabs by `allowed_tabs`, add "Usuarios" tab for admin, add `set_logout_callback`/`set_close_callback` per design §6.3 (~50 LOC added)
- [ ] 3.4 Modify `pos/view/cash_register_view.py`: accept `cash_register_mode` param, add `_apply_permission_mode()` to hide widgets via `grid_remove()`/`pack_forget()` per design §6.4 (~30 LOC added)
- [ ] 3.5 Modify `pos/view/product_view.py`: accept optional `role` param in constructor (stored, no UI change) per design §6.5 (~5 LOC added)
- [ ] 3.6 Rewrite `pos/main.py`: add login gate with `_run_login_loop`, `_launch_with_user`, `_wire_views` (permission-filtered wiring), test mode bypass via `POS_TEST_MODE` env var per design §7.1-7.2 (~100 LOC changed/added)
- [ ] 3.7 Verify: run app with `POS_TEST_MODE=1`, confirm MainWindow opens directly with all tabs. Run without test mode, confirm LoginView appears, login with admin/admin123, verify all tabs visible

## Phase 4: Testing

- [ ] 4.1 Create `pos/tests/test_user_repo.py`: test `find_by_username` (hit/miss), `create`, `update`, `get_all`, duplicate username raises `IntegrityError` (~80 LOC)
- [ ] 4.2 Create `pos/tests/test_session_repo.py`: test `create_session`, `close_session`, `get_active_session` (open/closed) (~50 LOC)
- [ ] 4.3 Create `pos/tests/test_auth_service.py`: test `login` (valid/wrong pw/inactive/nonexistent), `logout`, `bootstrap_admin` (idempotent), spec scenarios from `user-auth/spec.md` (~80 LOC)
- [ ] 4.4 Create `pos/tests/test_permission_service.py`: test `can_access` for all role/module combos, `get_permissions` returns correct `PermissionContext`, spec scenarios from `role-permissions/spec.md` (~70 LOC)
- [ ] 4.5 Create `pos/tests/test_login_controller.py`: test `validate` (success/failure), `validate_input` (empty fields), response dict format (~60 LOC)
- [ ] 4.6 Create `pos/tests/test_user_management_controller.py`: test `create_user` (success/duplicate/empty), `deactivate_user`, `is_admin_protected`, spec scenarios from `user-management/spec.md` (~80 LOC)
- [ ] 4.7 Run full test suite: `pytest pos/tests/` — all 21 existing + 6 new test files pass. Verify `DDL` changes don't break existing fixtures

## Dependency Graph

```
1.1 → 1.2 → 1.3 → 1.4, 1.5 (parallel)
                    ↓
              2.1, 2.2 (parallel) → 2.3, 2.4 (parallel)
                                        ↓
              3.1, 3.2 (parallel) → 3.3, 3.4, 3.5 (parallel) → 3.6
                                                                  ↓
              4.1, 4.2 (parallel, after Phase 1)
              4.3, 4.4 (parallel, after Phase 2)
              4.5, 4.6 (parallel, after Phase 2)
              4.7 (after all Phase 4 tasks)
```

## LOC Summary

| Category | Files | Estimated LOC |
|----------|-------|---------------|
| Models | `enums.py` (mod), `user.py` (new) | ~58 |
| Database | `database.py` (mod) | ~30 |
| Repositories | `user_repo.py`, `session_repo.py` | ~135 |
| Services | `auth_service.py`, `permission_service.py` | ~135 |
| Controllers | `login_controller.py`, `user_management_controller.py` | ~165 |
| Views (new) | `login_view.py`, `user_management_view.py` | ~280 |
| Views (mod) | `main_window.py`, `cash_register_view.py`, `product_view.py` | ~85 |
| Integration | `main.py` | ~100 |
| Tests | 6 new test files | ~420 |
| **Total** | **9 new + 6 modified** | **~1408** |
