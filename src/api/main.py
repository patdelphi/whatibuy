from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import sqlite3
from src.api.database import get_db_connection

app = FastAPI(title="WhatIBuy API", description="API for WhatIBuy Shopping Analysis", version="0.1.0")

# Configure CORS
origins = [
    "http://localhost:5173",  # React frontend dev server
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class OrderItem(BaseModel):
    title: Optional[str]
    price: Optional[float]
    quantity: Optional[int]
    sku_info: Optional[str]
    image_url: Optional[str]

class Order(BaseModel):
    id: int
    order_id: str
    order_date: Optional[str]
    status: Optional[str]
    shop_name: Optional[str] = None
    total_price: Optional[float] = None
    currency: Optional[str] = "CNY"
    platform: str
    items: List[OrderItem] = []

class ConsumptionStats(BaseModel):
    total_spent: float
    order_count: int
    platform_breakdown: dict
    monthly_breakdown: dict

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to WhatIBuy API"}

class OrderListResponse(BaseModel):
    items: List[Order]
    total: int
    page: int
    limit: int

@app.get("/api/orders", response_model=OrderListResponse)
def get_orders(
    page: int = 1, 
    limit: int = 100, 
    platform: Optional[str] = None,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * limit
    
    query = "SELECT * FROM orders WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM orders WHERE 1=1"
    params = []
    
    if platform:
        query += " AND platform = ?"
        count_query += " AND platform = ?"
        params.append(platform)
        
    if search:
        query += " AND (shop_name LIKE ? OR order_id LIKE ?)"
        count_query += " AND (shop_name LIKE ? OR order_id LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    if start_date:
        query += " AND order_date >= ?"
        count_query += " AND order_date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND order_date <= ?"
        count_query += " AND order_date <= ?"
        params.append(end_date)
        
    # Get total count
    total_count = cursor.execute(count_query, params).fetchone()[0]

    query += " ORDER BY order_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    orders = cursor.execute(query, params).fetchall()
    
    result = []
    for order in orders:
        order_dict = dict(order)
        # Map total_amount to total_price for Pydantic model compatibility
        if 'total_amount' in order_dict:
            order_dict['total_price'] = order_dict['total_amount']
            
        # Fetch items for this order
        # order_items.order_id is the foreign key to orders.id (integer), not the string order_id
        items = cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order['id'],)).fetchall()
        
        mapped_items = []
        for item in items:
            item_dict = dict(item)
            mapped_items.append({
                "title": item_dict.get("product_title"),
                "price": item_dict.get("product_price"),
                "quantity": item_dict.get("quantity"),
                "sku_info": item_dict.get("sku_info"), # Assuming this column exists or is None
                "image_url": item_dict.get("image_url")
            })
            
        order_dict['items'] = mapped_items
        result.append(order_dict)
        
    conn.close()
    return {
        "items": result,
        "total": total_count,
        "page": page,
        "limit": limit
    }

@app.get("/api/stats", response_model=ConsumptionStats)
def get_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND order_date >= ?"
        params.append(start_date)
        
    if end_date:
        where_clause += " AND order_date <= ?"
        params.append(end_date)
    
    # Total stats
    total = cursor.execute(f"SELECT SUM(total_amount), COUNT(*) FROM orders {where_clause}", params).fetchone()
    total_spent = total[0] or 0.0
    order_count = total[1] or 0
    
    # Platform breakdown
    platforms = cursor.execute(f"SELECT platform, SUM(total_amount) FROM orders {where_clause} GROUP BY platform", params).fetchall()
    platform_breakdown = {row[0]: row[1] for row in platforms}
    
    # Monthly breakdown
    monthly = cursor.execute(f"SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) FROM orders {where_clause} GROUP BY month ORDER BY month DESC", params).fetchall()
    monthly_breakdown = {row[0]: row[1] for row in monthly if row[0]}
    
    conn.close()
    return {
        "total_spent": total_spent,
        "order_count": order_count,
        "platform_breakdown": platform_breakdown,
        "monthly_breakdown": monthly_breakdown
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
