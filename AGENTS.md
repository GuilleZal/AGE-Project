# Code Review Rules

## Python
- Use type hints for function signatures
- Follow PEP 8 style guide
- Use dataclasses for data structures
- Prefer explicit error handling over silent failures

## Architecture (MVC)
- Models: plain dataclasses, no ORM
- Views: CustomTkinter widgets, emit events only
- Controllers: orchestrate view events → model updates
- Services: pure business logic, no UI dependency
- Repositories: SQL queries, encapsulate data access

## Database (SQLite)
- Use parameterized queries (no string interpolation)
- Enable foreign keys (PRAGMA foreign_keys=ON)
- Use WAL journal mode for performance

## Testing
- Use pytest for unit/integration tests
- In-memory SQLite for test fixtures
- Test services and controllers with mocked dependencies

## Naming
- snake_case for variables, functions, methods
- PascalCase for classes
- UPPER_CASE for constants
