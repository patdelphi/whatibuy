
import sqlite3
import os

DB_PATH = os.path.join('data', 'whatibuy.db')

def update_order_price(order_id, price):
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Checking order {order_id}...")
    cursor.execute("SELECT id, total_amount FROM orders WHERE order_id = ?", (order_id,))
    result = cursor.fetchone()
    
    if result:
        db_id, current_price = result
        print(f"Found order. Current price: {current_price}")
        
        # Update orders table
        cursor.execute("UPDATE orders SET total_amount = ? WHERE order_id = ?", (price, order_id))
        print(f"Updated 'orders' table. New price: {price}")
        
        # Update order_items table
        cursor.execute("UPDATE order_items SET product_price = ? WHERE order_id = ?", (price, db_id))
        print(f"Updated 'order_items' table. New price: {price}")
        
        conn.commit()
    else:
        print(f"Order {order_id} not found.")

    conn.close()

if __name__ == "__main__":
    update_order_price('746737027443604282', 2380.0)
