import sqlite3
conn = sqlite3.connect('pos/data/pos.db')
cur = conn.cursor()
cur.execute("SELECT payment_method, COUNT(*) FROM sales GROUP BY payment_method")
print("Data:", cur.fetchall())
