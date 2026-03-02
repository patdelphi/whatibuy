import sqlite3
import os

db_path = os.path.join("data", "whatibuy.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

query = """
SELECT orders.order_id, order_items.product_title, orders.status
FROM order_items 
JOIN orders ON order_items.order_id = orders.id 
WHERE orders.platform = 'Xianyu' 
AND (order_items.product_url IS NULL OR order_items.product_url = '')
LIMIT 20
"""

c.execute(query)
results = c.fetchall()

print("--- Sample Orders Missing Detail URL ---")
for r in results:
    print(r)

conn.close()
