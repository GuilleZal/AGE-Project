import sqlite3
conn = sqlite3.connect('pos/data/pos.db')
print(conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'").fetchone()[0])
