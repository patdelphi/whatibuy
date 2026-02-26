import sqlite3
from pathlib import Path

# Define the path to the database
# Assuming the API is run from the project root
DB_PATH = Path("data/whatibuy.db")

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn
