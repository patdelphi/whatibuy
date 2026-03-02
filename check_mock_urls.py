import sqlite3
import os

db_path = os.path.join("data", "whatibuy.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check Mock IDs missing URLs
c.execute("""
    SELECT count(*) 
    FROM order_items 
    JOIN orders ON order_items.order_id = orders.id 
    WHERE orders.platform = 'Xianyu' 
    AND (order_items.product_url IS NULL OR order_items.product_url = '')
    AND (orders.order_id LIKE 'XY-%' OR orders.order_id LIKE 'HASH-%')
""")
mock_missing = c.fetchone()[0]

# Check Real IDs missing URLs
c.execute("""
    SELECT count(*) 
    FROM order_items 
    JOIN orders ON order_items.order_id = orders.id 
    WHERE orders.platform = 'Xianyu' 
    AND (order_items.product_url IS NULL OR order_items.product_url = '')
    AND orders.order_id NOT LIKE 'XY-%' 
    AND orders.order_id NOT LIKE 'HASH-%'
""")
real_missing = c.fetchone()[0]

print(f"Mock IDs Missing URL: {mock_missing}")
print(f"Real IDs Missing URL: {real_missing}")

conn.close()
