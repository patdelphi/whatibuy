import sqlite3
import os

db_path = os.path.join("data", "whatibuy.db")
if not os.path.exists(db_path):
    print("Database not found.")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("=== Xianyu Data Health Check ===")
    
    # 1. Total Xianyu orders
    c.execute("SELECT count(*) FROM orders WHERE platform = 'Xianyu'")
    total_orders = c.fetchone()[0]
    print(f"Total Orders: {total_orders}")
    
    # 2. Mock IDs vs Real IDs
    c.execute("SELECT count(*) FROM orders WHERE platform = 'Xianyu' AND (order_id LIKE 'XY-%' OR order_id LIKE 'HASH-%')")
    mock_ids = c.fetchone()[0]
    real_ids = total_orders - mock_ids
    print(f"Real IDs: {real_ids}")
    print(f"Mock IDs: {mock_ids}")
    
    # 3. Missing Detail URLs
    c.execute("""
        SELECT count(*) 
        FROM order_items 
        JOIN orders ON order_items.order_id = orders.id 
        WHERE orders.platform = 'Xianyu' 
        AND (order_items.product_url IS NULL OR order_items.product_url = '')
    """)
    missing_urls = c.fetchone()[0]
    print(f"Orders missing Detail URL: {missing_urls}")
    
    # 4. Recent Real ID Examples
    print("\n--- Recent 5 Real ID Orders ---")
    c.execute("""
        SELECT order_id, total_amount, status, order_date 
        FROM orders 
        WHERE platform = 'Xianyu' AND order_id NOT LIKE 'XY-%' AND order_id NOT LIKE 'HASH-%'
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent = c.fetchall()
    for r in recent:
        print(f"ID: {r[0]} | Amount: {r[1]} | Status: {r[2]} | Date: {r[3]}")

    conn.close()
