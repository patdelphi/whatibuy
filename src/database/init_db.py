import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whatibuy.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

def init_db():
    print(f"Initializing database at {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
        cursor.executescript(schema)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
