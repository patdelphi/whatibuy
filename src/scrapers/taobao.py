import sys
from playwright.sync_api import sync_playwright
import sqlite3
import os
import time
import re
import random
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whatibuy.db')
DEBUG_HTML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'debug_taobao.html')
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'user_data')

def init_tables(conn):
    """Initializes the database tables."""
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    cursor.execute('''
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
    ''')
    conn.commit()
    print("Database tables initialized.")

def clear_tables(conn):
    """Clears all data from tables."""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    conn.commit()
    print("Database tables dropped.")
    init_tables(conn)

def get_db_connection():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def validate_date(date_str):
    """Ensures date is in YYYY-MM-DD format."""
    try:
        # Check if it matches YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            # Verify it's a valid date
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
    except ValueError:
        pass
    return None

def validate_order_id(order_id):
    """Ensures order ID contains only digits and is of reasonable length."""
    # Remove any non-digit characters
    clean_id = re.sub(r'\D', '', order_id)
    if len(clean_id) > 5: # Basic check, order IDs are usually long
        return clean_id
    return None

def validate_amount(amount):
    """Ensures amount is a valid positive float."""
    try:
        val = float(amount)
        if val >= 0 and val < 10000000: # Add reasonable upper limit (10 million)
            return val
    except (ValueError, TypeError):
        pass
    return 0.0

def check_order_exists(cursor, order_id):
    """Checks if an order already exists in the database."""
    cursor.execute("SELECT 1 FROM orders WHERE platform = ? AND order_id = ?", ("Taobao", order_id))
    return cursor.fetchone() is not None

def scrape_taobao(mode_arg=None):
    print("Starting Taobao scraper...")
    
    # User Prompt Logic
    print("-" * 50)
    print("请选择抓取模式：")
    print("1. 全量抓取 (Full Scrape) - 抓取所有页面的数据")
    print("2. 增量抓取 (Incremental Scrape) - 遇到数据库中已存在的订单时停止")
    print("3. 跳过抓取 (Skip) - 直接退出")
    print("-" * 50)
    
    if mode_arg:
        mode = str(mode_arg)
        print(f"Using mode from argument: {mode}")
    else:
        mode = input("请输入选项 (1/2/3): ").strip()
    
    if mode == '3':
        print("已跳过抓取。")
        return
        
    incremental_mode = (mode == '2')
    max_pages = float('inf') if mode == '1' else 50 # No limit for full scrape
    
    if incremental_mode:
        print(">> 已启用增量抓取模式。如果遇到已存在的订单，抓取将自动停止。")
        # Ensure tables exist
        conn = get_db_connection()
        init_tables(conn)
        conn.close()
    else:
        print(">> 已启用全量抓取模式。")
        # Clear DB for full scrape
        conn = get_db_connection()
        clear_tables(conn)
        conn.close()

    with sync_playwright() as p:
        # Launch browser in headful mode for manual login
        args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-infobars',
        ]
        
        print(f"Using user data directory: {USER_DATA_DIR}")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False, 
                channel="msedge",
                args=args,
                viewport={'width': 1280, 'height': 800}
            )
        except Exception:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False, 
                channel="chrome",
                args=args,
                viewport={'width': 1280, 'height': 800}
            )
            
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("Navigating to Taobao login page...")
        try:
            page.goto("https://login.taobao.com/member/login.jhtml")
        except Exception:
            print("Navigation to login page might have been redirected. Trying order list page...")
            pass

        print("-" * 50)
        print("请在打开的浏览器窗口中：")
        print("1. 手动完成淘宝账号登录")
        print("2. 确保页面跳转到'已买到的宝贝' (订单列表页)")
        print("-" * 50)
        
        print("Waiting for login... (Will automatically proceed when 'list_bought_items.htm' is detected)")
        
        login_check_start = time.time()
        last_url = ""
        while True:
            # Check all pages in the context (sometimes login opens a new tab)
            target_page = None
            try:
                for p in context.pages:
                    try:
                        url = p.url
                        title = p.title()
                        if "list_bought_items.htm" in url or "已买到的宝贝" in title:
                            target_page = p
                            break
                    except:
                        pass
            except:
                pass
            
            if target_page:
                page = target_page
                # Ensure the page is active
                try:
                    page.bring_to_front()
                except:
                    pass
                print(f"页面确认成功！(URL: {page.url})")
                break
            
            # Check current page (fallback)
            try:
                current_url = page.url
            except:
                current_url = ""

            if current_url != last_url:
                print(f"Current URL: {current_url} - Waiting for order list...")
                last_url = current_url
            
            # Check timeout (e.g. 10 minutes)
            if time.time() - login_check_start > 600:
                print("Login timeout. Exiting.")
                context.close()
                return

            time.sleep(2)

        print("Login successful. Starting data extraction...")
        
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        page_num = 1
        consecutive_existing_orders = 0
        stop_scraping = False
        
        prev_page_order_ids = set()
        
        while page_num <= max_pages and not stop_scraping:
            print(f"Processing page {page_num}...")
            
            try:
                page.wait_for_selector(".bought-wrapper-mod__trade-order___2lRZV, .index-mod__order-container___1ur4-", timeout=10000)
            except:
                print("Timeout waiting for order list selectors. Page structure might be different.")
            
            orders = page.query_selector_all("div[class*='trade-order'], div[class*='order-container']")
            
            if not orders:
                orders = page.query_selector_all("table[class*='bought-table']") 
            
            print(f"Found {len(orders)} potential order items on page {page_num}.")
            
            current_page_order_ids = set()
            page_new_orders_count = 0
            
            for order in orders:
                if stop_scraping:
                    break
                    
                try:
                    # Initialize default values
                    order_date = "Unknown"
                    order_id = "Unknown"
                    total_amount = 0.0
                    status = "Unknown"
                    shop_name = "Unknown"
                    product_title = "Unknown"
                    
                    # --- 1. Order ID Parsing ---
                    # Strategy A: Check data-spm="order_detail" (Very reliable)
                    detail_el = order.query_selector('[data-spm="order_detail"]')
                    if detail_el:
                        detail_text = detail_el.inner_text()
                        # Extract from text "订单详情" or similar if ID is not there, but usually it's just a link
                        # Check href for biz_order_id
                        link = detail_el.query_selector('a')
                        if link:
                            href = link.get_attribute('href')
                            if href and 'biz_order_id=' in href:
                                match = re.search(r'biz_order_id=(\d+)', href)
                                if match:
                                    order_id = match.group(1)

                    # Strategy B: Text Regex (Fallback)
                    if order_id == "Unknown":
                        text_content = order.inner_text()
                        id_match = re.search(r'订单号[：:]?\s*(\d+)', text_content)
                        if id_match:
                            order_id = id_match.group(1)
                            
                    # Track ID for pagination check
                    if order_id != "Unknown":
                        current_page_order_ids.add(order_id)
                            
                    # --- 2. Shop Name Parsing ---
                    # Strategy A: Check data-spm="order_shopname" (Very reliable)
                    shop_el = order.query_selector('[data-spm="order_shopname"]')
                    if shop_el:
                        shop_name = shop_el.inner_text().strip()
                    
                    # Strategy B: Find 'a' tag with specific class patterns
                    if shop_name == "Unknown":
                        shop_link = order.query_selector('a[class*="shopInfoName"], a[class*="shop-name"]')
                        if shop_link:
                            shop_name = shop_link.inner_text().strip()
                            
                    # Strategy C: Text heuristic (Fallback)
                    if shop_name == "Unknown":
                        lines = order.inner_text().split('\n')
                        for line in lines:
                            if "店" in line and len(line) < 30 and "订单" not in line and "旗舰" in line: # specific heuristic
                                shop_name = line.strip()
                                break

                    # --- 3. Date Parsing ---
                    # Strategy A: Regex on text content
                    text_content = order.inner_text()
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text_content)
                    if date_match:
                        order_date = date_match.group(1)

                    # --- 4. Total Amount Parsing ---
                    # Strategy A: Look for "Real Payment" (实付款) container
                    price_real_el = order.query_selector('[class*="priceReal"], [class*="realPay"]')
                    if price_real_el:
                        price_text = price_real_el.inner_text()
                        # Extract number
                        price_match = re.search(r'[\d\.]+', price_text.replace('￥', '').replace('¥', ''))
                        if price_match:
                            total_amount = float(price_match.group(0))
                    
                    # Strategy B: Text Regex for "实付款" (More reliable fallback)
                    if total_amount == 0.0:
                        text_content = order.inner_text()
                        # Matches "实付款：￥123.45" or similar
                        # Also handle possible spaces inside number (though rare)
                        price_match = re.search(r'实付款.*?([0-9]+(?:\.[0-9]+)?)', text_content.replace('\n', '').replace(' ', ''))
                        if price_match:
                             try:
                                total_amount = float(price_match.group(1))
                             except:
                                pass
                                
                    # Strategy C: Last resort - look for price elements but be careful
                    if total_amount == 0.0:
                        # Try to find elements that are likely the total price (often bold or specific class)
                        # Instead of joining all, let's try to find the one near "实付款"
                        try:
                            # Use evaluate to find element with text containing "实付款"
                            # This is complex in playwright without robust selectors. 
                            # Let's stick to the text regex above as main fallback.
                            pass 
                        except:
                            pass

                    # --- 5. Product Title Parsing ---
                    # Strategy A: data-spm="suborder_itemtitle"
                    title_el = order.query_selector('[data-spm="suborder_itemtitle"]')
                    if title_el:
                        # Get text but remove "[交易快照]"
                        raw_title = title_el.inner_text()
                        product_title = raw_title.replace('[交易快照]', '').strip()
                    
                    # Strategy B: Fallback to first long link text
                    if product_title == "Unknown":
                        links = order.query_selector_all('a')
                        for link in links:
                            txt = link.inner_text().strip()
                            if len(txt) > 10 and "订单" not in txt and "查看" not in txt and "评价" not in txt:
                                product_title = txt
                                break

                    # --- 6. Status Parsing ---
                    status_el = order.query_selector('[class*="status"], [class*="state"]')
                    if status_el:
                         status = status_el.inner_text().strip()
                    if status == "Unknown":
                         # Text fallback
                         for s in ["交易成功", "待发货", "待付款", "交易关闭", "已签收", "双方已评"]:
                             if s in text_content:
                                 status = s
                                 break
                                 
                    # --- Validation & Storage ---
                    if order_id == "746737027443604282" or order_id == "12153969408604200":
                        print(f"\n[DEBUG] Found target order: {order_id}")
                        print(f"[DEBUG] Extracted Price: {total_amount}")
                        print(f"[DEBUG] Extracted Date: {order_date}")
                        print(f"[DEBUG] Extracted Shop: {shop_name}")
                        print(f"[DEBUG] Extracted Status: {status}")
                        
                        # Save HTML for analysis
                        try:
                            debug_file = os.path.join(os.path.dirname(DB_PATH), f"debug_order_{order_id}.html")
                            with open(debug_file, "w", encoding="utf-8") as f:
                                f.write(order.evaluate("el => el.outerHTML"))
                            print(f"[DEBUG] HTML saved to: {debug_file}")
                            
                            # Print parsing details
                            price_real_el = order.query_selector('[class*="priceReal"], [class*="realPay"]')
                            if price_real_el:
                                print(f"[DEBUG] Strategy A Element Text: {price_real_el.inner_text()}")
                            else:
                                print("[DEBUG] Strategy A Element: Not Found")
                                
                            print(f"[DEBUG] Order Inner Text:\n{order.inner_text()}")
                        except Exception as e:
                            print(f"[DEBUG] Failed to save debug info: {e}")

                    if order_id != "Unknown" and validate_date(order_date):
                        total_amount = validate_amount(total_amount)
                        
                        # INCREMENTAL CHECK
                        if check_order_exists(cursor, order_id):
                            print(f"  - Order {order_id} already exists.")
                            consecutive_existing_orders += 1
                            
                            if incremental_mode:
                                # If we found an existing order in incremental mode, we assume all subsequent orders (which are older) are also in DB.
                                # However, sometimes order list isn't strictly chronological or there are pinned orders?
                                # Let's be safe and wait for a few consecutive existing orders before stopping?
                                # Actually, usually stopping at the first existing one is standard for time-sorted lists.
                                # But Taobao list is strictly time sorted.
                                print(">> Found existing order in incremental mode. Stopping scrape.")
                                stop_scraping = True
                                break
                        else:
                            # New order
                            print(f"  - Found NEW Order: {order_id} | {order_date} | {total_amount}")
                            consecutive_existing_orders = 0 # Reset counter
                            page_new_orders_count += 1
                            
                            try:
                                cursor.execute('''
                                    INSERT OR IGNORE INTO orders (platform, order_id, order_date, total_amount, status, shop_name)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', ("Taobao", order_id, order_date, total_amount, status, shop_name))
                                
                                cursor.execute("SELECT id FROM orders WHERE platform = ? AND order_id = ?", ("Taobao", order_id))
                                db_order_id = cursor.fetchone()[0]
                                
                                if product_title != "Unknown":
                                    cursor.execute('''
                                        INSERT INTO order_items (order_id, product_title, product_price, quantity)
                                        VALUES (?, ?, ?, ?)
                                    ''', (db_order_id, product_title, total_amount, 1))
                                    
                            except Exception as e:
                                print(f"DB Error: {e}")
                    else:
                        pass

                except Exception as e:
                    print(f"  - Error parsing order item: {e}")

            # Commit after each page to save progress
            conn.commit()

            if stop_scraping:
                break
                
            # If no orders found on page, maybe end of list?
            if len(orders) == 0:
                print("No orders found on this page. Stopping.")
                break

            # Check for pagination loop (same orders as previous page)
            if len(current_page_order_ids) > 0 and current_page_order_ids == prev_page_order_ids:
                print(">> Detected duplicate page content (pagination loop). Reached end of list.")
                break
            
            prev_page_order_ids = current_page_order_ids

            # Scroll to bottom to ensure pagination is visible
            page.keyboard.press("End")
            time.sleep(1)

            # Pagination Logic
            try:
                next_btn = None
                
                # Strategy 2: Numeric Pagination (Next Number) - PRIMARY STRATEGY
                if not next_btn:
                    # Assume current page is page_num
                    next_page_num = page_num + 1
                    print(f"Looking for page {next_page_num}...")
                    
                    # Try to find the number in common pagination containers
                    # rc-pagination, .pagination, etc.
                    # Strict exact match for the number to avoid matching order IDs or prices
                    
                    # 1. Try generic "text=N" but filter by tag
                    # Only click a, button, li
                    candidates = page.locator("a, button, li").filter(has_text=re.compile(f"^{next_page_num}$"))
                    
                    if candidates.count() > 0:
                        print(f"[DEBUG] Found {candidates.count()} candidates for page {next_page_num}")
                        for i in range(candidates.count()):
                            cand = candidates.nth(i)
                            if cand.is_visible():
                                # Verify it's inside a pagination container if possible
                                # Or just try it if it looks safe
                                next_btn = cand
                                print(f"Found next page number {next_page_num} (Candidate {i})")
                                break
                    
                    # 2. Try searching within specific pagination containers if 1 failed
                    if not next_btn:
                        pagination_containers = [
                            ".pagination", ".rc-pagination", ".next-pagination", 
                            "ul[class*='pagination']", "div[class*='pagination']"
                        ]
                        for container in pagination_containers:
                            if next_btn: break
                            try:
                                cont = page.locator(container)
                                if cont.count() > 0:
                                    target = cont.get_by_text(str(next_page_num), exact=True)
                                    if target.count() > 0 and target.first.is_visible():
                                        next_btn = target.first
                                        print(f"Found next page number {next_page_num} inside {container}")
                            except:
                                pass

                # Strategy 1: Specific Button/Link with "下一页" text (FALLBACK)
                if not next_btn:
                     # Often it's <button> or <li class="item next"> or <a class="next">
                     # Also check standard Taobao pagination classes
                     potential_next = page.locator("button, a, li").filter(has_text=re.compile(r"下一页|Next"))
                     
                     # Debug pagination
                     print(f"[DEBUG] Found {potential_next.count()} potential 'Next' buttons.")
                     
                     # Iterate to find the visible and enabled one
                     count = potential_next.count()
                     for i in range(count):
                         el = potential_next.nth(i)
                         if el.is_visible():
                             # Check if disabled
                             class_attr = el.get_attribute("class") or ""
                             disabled_attr = el.get_attribute("disabled")
                             if "disabled" not in class_attr and disabled_attr is None:
                                 next_btn = el
                                 print(f"Found '下一页' button using Strategy 1 (index {i})")
                                 break
                             else:
                                 print(f"[DEBUG] Potential Next button {i} ignored: class={class_attr}, disabled={disabled_attr}")

                # Strategy 3: Generic 'next' class search (rc-pagination-next)
                if not next_btn:
                     next_class_btn = page.locator(".rc-pagination-next, .next-pagination-item, .next")
                     if next_class_btn.count() > 0:
                         for i in range(next_class_btn.count()):
                             btn = next_class_btn.nth(i)
                             if btn.is_visible() and "disabled" not in (btn.get_attribute("class") or ""):
                                 next_btn = btn
                                 print("Found next button using Strategy 3 (class name)")
                                 break

                if next_btn:
                    print("Navigating to next page...")
                    try:
                        # Try normal click
                        next_btn.click(timeout=3000)
                    except Exception as e:
                        print(f"Normal click failed: {e}. Trying JS click...")
                        # Fallback to JS click
                        page.evaluate("arguments[0].click();", next_btn.element_handle())
                    
                    time.sleep(random.uniform(3, 6)) 
                    page_num += 1
                else:
                    print("No next page button found (reached end or selector changed).")
                    break
                        
            except Exception as e:
                print(f"Pagination error: {e}")
                break

        conn.commit()
        conn.close()
        print("Scraping completed.")

if __name__ == "__main__":
    scrape_taobao()
