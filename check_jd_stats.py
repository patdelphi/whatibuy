import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'whatibuy.db')

def check_stats():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all orders for JD
    cursor.execute("SELECT order_date FROM orders WHERE platform='JD'")
    rows = cursor.fetchall()
    
    year_counts = {}
    total = 0
    
    for row in rows:
        date_str = row[0]
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            year = dt.year
            year_counts[year] = year_counts.get(year, 0) + 1
            total += 1
        except:
            pass
            
    print(f"Total JD Orders: {total}")
    print("Orders by Year:")
    for year in sorted(year_counts.keys(), reverse=True):
        print(f"  {year}: {year_counts[year]} orders")
        
    conn.close()

if __name__ == "__main__":
    check_stats()