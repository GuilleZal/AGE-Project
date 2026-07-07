"""User domain dataclasses for authentication and authorization."""

from dataclasses import dataclass
from pos.model.enums import UserRole


@dataclass
class User:
    """An authenticated user account.

    Plain-text password — intentional for school project.
    """
    username: str
    password: str
    role: UserRole | str
    id: int | None = None
    is_active: int = 1
    created_at: str | None = None


@dataclass
class Session:
    """An active login session."""
    user_id: int
    id: int | None = None
    login_time: str | None = None
    logout_time: str | None = None


@dataclass
class PermissionContext:
    """Immutable snapshot of what the current user can access.

    Passed from MainWindow to child views at construction time.
    """
    user: User
    allowed_tabs: tuple[str, ...]
    cash_register_mode: str  # "full" | "history_only" | "restricted"