import sqlite3
conn = sqlite3.connect('pos/data/pos.db')
cur = conn.cursor()
cur.execute("SELECT payment_method, created_at FROM sales WHERE payment_method IN ('credit_card', 'debit_card')")
print(cur.fetchall())
