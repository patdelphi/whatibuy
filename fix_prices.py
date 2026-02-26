
import sqlite3
import os

DB_PATH = os.path.join('data', 'whatibuy.db')

def fix_abnormal_prices():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    threshold = 1000000 # 1 million

    # 1. Check count of abnormal orders
    cursor.execute("SELECT COUNT(*) FROM orders WHERE total_amount > ?", (threshold,))
    count = cursor.fetchone()[0]
    print(f"Found {count} orders with abnormal prices (> {threshold}).")

    if count > 0:
        print("Fixing abnormal prices in 'orders' table...")
        cursor.execute("UPDATE orders SET total_amount = 0 WHERE total_amount > ?", (threshold,))
        print(f"Updated {cursor.rowcount} rows.")

    # 2. Check count of abnormal order items
    cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_price > ?", (threshold,))
    item_count = cursor.fetchone()[0]
    print(f"Found {item_count} order items with abnormal prices (> {threshold}).")

    if item_count > 0:
        print("Fixing abnormal prices in 'order_items' table...")
        cursor.execute("UPDATE order_items SET product_price = 0 WHERE product_price > ?", (threshold,))
        print(f"Updated {cursor.rowcount} rows.")

    conn.commit()
    conn.close()
    print("Database cleanup completed.")

if __name__ == "__main__":
    fix_abnormal_prices()
