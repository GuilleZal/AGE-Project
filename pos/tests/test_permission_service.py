"""Tests for PermissionService — role-based permission matrix."""

import pytest
from pos.service.permission_service import PermissionService
from pos.model.user import User, PermissionContext
from pos.model.enums import UserRole


@pytest.fixture
def perm_service() -> PermissionService:
    """Return a PermissionService instance."""
    return PermissionService()


def test_admin_has_full_access(perm_service: PermissionService) -> None:
    """Test admin has access to all modules."""
    assert perm_service.can_access("admin", "Ventas") is True
    assert perm_service.can_access("admin", "Productos") is True
    assert perm_service.can_access("admin", "Devoluciones") is True
    assert perm_service.can_access("admin", "Caja") is True
    assert perm_service.can_access("admin", "Reportes") is True
    assert perm_service.can_access("admin", "Usuarios") is True


def test_gerente_access(perm_service: PermissionService) -> None:
    """Test gerente has limited access."""
    assert perm_service.can_access("gerente", "Ventas") is False
    assert perm_service.can_access("gerente", "Productos") is True
    assert perm_service.can_access("gerente", "Devoluciones") is False
    assert perm_service.can_access("gerente", "Caja") is True
    assert perm_service.can_access("gerente", "Reportes") is True


def test_cajero_access(perm_service: PermissionService) -> None:
    """Test cajero has limited access."""
    assert perm_service.can_access("cajero", "Ventas") is True
    assert perm_service.can_access("cajero", "Productos") is False
    assert perm_service.can_access("cajero", "Devoluciones") is True
    assert perm_service.can_access("cajero", "Caja") is True
    assert perm_service.can_access("cajero", "Reportes") is False


def test_inventario_access(perm_service: PermissionService) -> None:
    """Test inventario only has access to Productos."""
    assert perm_service.can_access("inventario", "Ventas") is False
    assert perm_service.can_access("inventario", "Productos") is True
    assert perm_service.can_access("inventario", "Devoluciones") is False
    assert perm_service.can_access("inventario", "Caja") is False
    assert perm_service.can_access("inventario", "Reportes") is False


def test_get_permissions_admin(perm_service: PermissionService) -> None:
    """Test get_permissions returns correct PermissionContext for admin."""
    user = User(username="admin", password="pass", role=UserRole.ADMIN, id=1)
    ctx = perm_service.get_permissions(user)
    
    assert isinstance(ctx, PermissionContext)
    assert ctx.user == user
    assert "Ventas" in ctx.allowed_tabs
    assert "Productos" in ctx.allowed_tabs
    assert "Usuarios" in ctx.allowed_tabs
    assert ctx.cash_register_mode == "full"


def test_get_permissions_cajero(perm_service: PermissionService) -> None:
    """Test get_permissions returns correct PermissionContext for cajero."""
    user = User(username="cajero1", password="pass", role=UserRole.CAJERO, id=2)
    ctx = perm_service.get_permissions(user)
    
    assert "Ventas" in ctx.allowed_tabs
    assert "Devoluciones" in ctx.allowed_tabs
    assert "Caja" in ctx.allowed_tabs
    assert "Productos" not in ctx.allowed_tabs
    assert ctx.cash_register_mode == "restricted"


def test_get_allowed_tabs(perm_service: PermissionService) -> None:
    """Test get_allowed_tabs returns correct tuple."""
    tabs = perm_service.get_allowed_tabs("gerente")
    assert "Productos" in tabs
    assert "Caja" in tabs
    assert "Reportes" in tabs
    assert "Ventas" not in tabs


def test_get_cash_register_mode(perm_service: PermissionService) -> None:
    """Test get_cash_register_mode returns correct mode."""
    assert perm_service.get_cash_register_mode("admin") == "full"
    assert perm_service.get_cash_register_mode("gerente") == "history_only"
    assert perm_service.get_cash_register_mode("cajero") == "restricted"
    assert perm_service.get_cash_register_mode("inventario") == "none"


def test_can_access_with_enum(perm_service: PermissionService) -> None:
    """Test can_access works with UserRole enum."""
    assert perm_service.can_access(UserRole.ADMIN, "Ventas") is True
    assert perm_service.can_access(UserRole.CAJERO, "Productos") is False