import sqlite3
import os

db_path = os.path.join("data", "whatibuy.db")
if not os.path.exists(db_path):
    print("Database not found.")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("--- Status Breakdown for Xianyu Orders Missing Detail URL ---")
    
    query = """
    SELECT orders.status, count(*) 
    FROM order_items 
    JOIN orders ON order_items.order_id = orders.id 
    WHERE orders.platform = 'Xianyu' 
    AND (order_items.product_url IS NULL OR order_items.product_url = '')
    GROUP BY orders.status
    ORDER BY count(*) DESC
    """
    
    c.execute(query)
    results = c.fetchall()
    
    if not results:
        print("No orders found with missing URLs.")
    else:
        for status, count in results:
            print(f"Status: {status:10} | Count: {count}")
            
    print("-" * 50)
    
    # Also check total counts per status for comparison
    print("--- Total Status Breakdown (All Xianyu Orders) ---")
    c.execute("SELECT status, count(*) FROM orders WHERE platform = 'Xianyu' GROUP BY status ORDER BY count(*) DESC")
    total_results = c.fetchall()
    for status, count in total_results:
        print(f"Status: {status:10} | Count: {count}")

    conn.close()
