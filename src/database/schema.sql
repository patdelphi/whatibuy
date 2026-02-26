CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    order_id TEXT NOT NULL,
    order_date TEXT,
    total_amount REAL,
    status TEXT,
    shop_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, order_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_title TEXT,
    product_price REAL,
    quantity INTEGER,
    product_url TEXT,
    image_url TEXT,
    category TEXT,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);
