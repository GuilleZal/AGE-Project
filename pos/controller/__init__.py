"""Controllers — orchestrate views, services, and repositories.

Each controller receives a ``sqlite3.Connection`` and creates the
repositories/services it needs internally (following the same pattern
used by ``pos.service``).  Controllers catch ``POSException`` subclasses
and translate them into user-facing ``{success, data, error}`` dicts
suitable for direct consumption by views.
"""
