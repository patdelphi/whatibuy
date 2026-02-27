import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'whatibuy.db')

def reset_old_years():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find IDs to delete (2013 and older)
    # We can filter by date string < '2014-01-01'
    cursor.execute("SELECT id FROM orders WHERE platform='JD' AND order_date < '2014-01-01'")
    rows = cursor.fetchall()
    ids = [str(row[0]) for row in rows]
    
    if not ids:
        print("No orders before 2014 found.")
        return

    print(f"Deleting {len(ids)} orders from 2013 and earlier...")
    
    cursor.execute(f"DELETE FROM order_items WHERE order_id IN ({','.join(ids)})")
    cursor.execute(f"DELETE FROM orders WHERE id IN ({','.join(ids)})")
    
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    reset_old_years()