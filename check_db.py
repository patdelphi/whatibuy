
import sqlite3
import os

DB_PATH = os.path.join('data', 'whatibuy.db')

def check_abnormal_orders():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Check the specific order mentioned by user
    print(f"--- Checking Order: 12153969408604200 ---")
    cursor.execute("SELECT * FROM orders WHERE order_id = '12153969408604200'")
    order = cursor.fetchone()
    if order:
        print(f"Found: {order}")
    else:
        print("Order not found.")

    # 2. Check for other high price orders
    print(f"\n--- Top 10 Highest Price Orders ---")
    cursor.execute("SELECT order_id, total_amount, shop_name, order_date FROM orders ORDER BY total_amount DESC LIMIT 10")
    top_orders = cursor.fetchall()
    for o in top_orders:
        print(o)

    conn.close()

if __name__ == "__main__":
    check_abnormal_orders()
