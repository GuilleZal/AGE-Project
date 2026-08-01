import sqlite3
conn = sqlite3.connect('pos/data/pos.db')
cur = conn.cursor()
cur.execute("UPDATE sales SET created_at = datetime(created_at, '-3 hours')")
conn.commit()
print('Updated rows:', cur.rowcount)
