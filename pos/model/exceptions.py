"""Custom exception hierarchy for the POS system.

All exceptions inherit from ``POSException`` so the controller layer can
catch a single base type and translate it to a user-facing message.

- ``DataError`` — raised by repositories for integrity/constraint violations.
- ``BusinessError`` — raised by services for business rule violations.
"""


class POSException(Exception):
    """Base exception for all POS system errors.

    Every subclass should include a user-friendly message suitable for
    display via ``messagebox.showerror()``.
    """


class DataError(POSException):
    """Repository-layer violation (e.g. duplicate barcode, FK constraint)."""


class BusinessError(POSException):
    """Service-layer rule violation (e.g. second register open, insufficient cash)."""
