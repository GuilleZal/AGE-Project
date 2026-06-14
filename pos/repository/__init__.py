# pos/repository — Data-access layer
# All repository classes receive a sqlite3.Connection via constructor.
# Parameterized queries only — no string interpolation for SQL values.
# DataError raised on integrity/constraint violations.
