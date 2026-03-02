import sqlite3
import os

db_path = os.path.join("data", "whatibuy.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("Cleaning up Mock ID orders (XY-*, HASH-*) for Xianyu...")

# 1. Count before
c.execute("SELECT count(*) FROM orders WHERE platform='Xianyu'")
total_before = c.fetchone()[0]
c.execute("SELECT count(*) FROM orders WHERE platform='Xianyu' AND (order_id LIKE 'XY-%' OR order_id LIKE 'HASH-%')")
mock_count = c.fetchone()[0]

print(f"Total Orders: {total_before}")
print(f"Mock Orders to delete: {mock_count}")

# 2. Delete items first (referential integrity usually handled by DB, but safe to do explicitly)
# Using subquery to find order IDs (internal DB IDs) to delete items for
c.execute("""
    DELETE FROM order_items 
    WHERE order_id IN (
        SELECT id FROM orders 
        WHERE platform='Xianyu' 
        AND (order_id LIKE 'XY-%' OR order_id LIKE 'HASH-%')
    )
""")
items_deleted = c.rowcount
print(f"Deleted {items_deleted} order items.")

# 3. Delete orders
c.execute("""
    DELETE FROM orders 
    WHERE platform='Xianyu' 
    AND (order_id LIKE 'XY-%' OR order_id LIKE 'HASH-%')
""")
orders_deleted = c.rowcount
print(f"Deleted {orders_deleted} orders.")

conn.commit()
conn.close()
print("Cleanup complete.")
