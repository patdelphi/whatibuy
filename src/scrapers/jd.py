
import sys
from playwright.sync_api import sync_playwright
import sqlite3
import os
import time
import re
import random
from datetime import datetime

# Reuse DB path and user data dir
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whatibuy.db')
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'user_data_jd')

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
    """Clears JD data from tables."""
    cursor = conn.cursor()
    # Only delete JD orders
    cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE platform = 'JD')")
    cursor.execute("DELETE FROM orders WHERE platform = 'JD'")
    conn.commit()
    print("JD data cleared.")

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

def validate_amount(amount):
    """Ensures amount is a valid positive float."""
    try:
        val = float(amount)
        if val >= 0 and val < 10000000:
            return val
    except (ValueError, TypeError):
        pass
    return 0.0

def check_order_exists(cursor, order_id):
    """Checks if an order already exists in the database."""
    cursor.execute("SELECT 1 FROM orders WHERE platform = ? AND order_id = ?", ("JD", order_id))
    return cursor.fetchone() is not None

def clear_platform_data(conn):
    """Clears all data for JD platform only."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE platform = 'JD')")
        cursor.execute("DELETE FROM orders WHERE platform = 'JD'")
        conn.commit()
        print("Cleared JD data successfully.")
    except Exception as e:
        print(f"Error clearing data: {e}")

def scrape_jd(mode_arg=None):
    print("Starting JD scraper...")
    
    # User Prompt Logic
    print("-" * 50)
    print("请选择抓取模式：")
    print("1. 全量抓取 (Full Scrape) - 清空京东历史数据并重新抓取")
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
    max_pages = float('inf') if mode == '1' else 50 
    
    conn = get_db_connection()
    init_tables(conn)
    
    if not incremental_mode:
        print(">> 全量模式：正在清空旧的京东数据...")
        clear_platform_data(conn)
    else:
        print(">> 已启用增量抓取模式。")
    
    conn.close()

    with sync_playwright() as p:
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

        print("Navigating to JD order page...")
        # Check if already logged in by going straight to order page
        try:
            page.goto("https://order.jd.com/center/list.action")
            time.sleep(2)
        except Exception:
            pass

        # Check if we are on login page or order page
        if "passport.jd.com" in page.url or "login" in page.url:
            print("Login required. Redirecting to login page...")
            try:
                page.goto("https://passport.jd.com/new/login.aspx")
            except:
                pass
            
            print("-" * 50)
            print("请在打开的浏览器窗口中：")
            print("1. 手动完成京东账号登录")
            print("2. 确保页面跳转到'我的订单' (order.jd.com)")
            print("-" * 50)
            
            login_check_start = time.time()
            last_url = ""
            
            while True:
                # ... (rest of login check loop)
                target_page = None
                try:
                    for p in context.pages:
                        try:
                            url = p.url
                            title = p.title()
                            if "order.jd.com" in url or "我的订单" in title:
                                target_page = p
                                break
                        except:
                            pass
                except:
                    pass
                
                if target_page:
                    page = target_page
                    try:
                        page.bring_to_front()
                    except:
                        pass
                    print(f"页面确认成功！(URL: {page.url})")
                    break
                
                try:
                    current_url = page.url
                except:
                    current_url = ""

                if current_url != last_url:
                    print(f"Current URL: {current_url} - Waiting for order list...")
                    last_url = current_url
                
                if time.time() - login_check_start > 600:
                    print("Login timeout. Exiting.")
                    context.close()
                    return

                time.sleep(2)
        else:
            print("Already logged in (or on order page).")
            # Ensure we are exactly on the order list page
            if "order.jd.com" not in page.url:
                 try:
                    page.goto("https://order.jd.com/center/list.action")
                 except:
                    pass

        print("Login successful. Starting data extraction...")
        
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass
            
def scrape_page_loop(page, cursor, conn, incremental_mode, max_pages):
    page_num = 1
    stop_scraping = False
    
    while page_num <= max_pages and not stop_scraping:
        print(f"  Processing page {page_num}...")
        
        # Try to ensure the order list is loaded
        try:
            page.wait_for_selector(".order-tb", timeout=5000)
        except:
            pass

        # DEBUG: Check what tables exist
        tables = page.locator("table")
        print(f"  [DEBUG] Found {tables.count()} tables on page.")
        
        # JD usually uses tbody with id='tb-order-...' for each order
        orders = page.locator("tbody[id^='tb-order-']")
        count = orders.count()
        print(f"  Found {count} potential orders on page {page_num}.")
        
        if count == 0:
            # Fallback: maybe it's not using tb-order- id?
            # Try finding rows directly
            orders = page.locator("table.order-tb tbody")
            count = orders.count()
            print(f"  [Fallback] Found {count} orders using 'table.order-tb tbody'")
            
            if count == 0:
                # Debug HTML content if really nothing found
                # content_sample = page.content()[:1000]
                # print(f"  [DEBUG] Page Content Start: {content_sample}")
                pass
        
        for i in range(count):
            if stop_scraping:
                break
            
            order = orders.nth(i)
            try:
                # Initialize default values
                order_date = "Unknown"
                order_id = "Unknown"
                total_amount = 0.0
                status = "Unknown"
                shop_name = "京东自营" # Default
                product_title = "Unknown"
                
                # --- 1. Order Header ---
                # Usually in the first tr of the tbody, or a separate tr with class 'tr-th'
                header_text = ""
                header_row = order.locator("tr.tr-th").first
                if header_row.count() > 0:
                    header_text = header_row.inner_text()
                else:
                    # Maybe the tbody itself is the container and first tr is header?
                    first_tr = order.locator("tr").first
                    if first_tr.count() > 0:
                        header_text = first_tr.inner_text()
                
                # Extract Data from Header
                # Date: YYYY-MM-DD
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', header_text)
                if date_match:
                    order_date = date_match.group(1)
                
                # Order ID
                # 订单号：123456
                id_match = re.search(r'订单号[：:]?\s*(\d+)', header_text)
                if id_match:
                    order_id = id_match.group(1)
                
                # Shop Name
                if "京东" in header_text and "自营" in header_text:
                    shop_name = "京东自营"
                else:
                    # Try to find link in header
                    shop_link = header_row.locator("span.shop-txt, div.shop-name a").first
                    if shop_link.count() > 0:
                        shop_name = shop_link.inner_text().strip()

                # --- 2. Order Body ---
                # Product Info
                # Usually in 'div.p-name'
                p_name = order.locator(".p-name").first
                if p_name.count() > 0:
                    product_title = p_name.inner_text().strip()
                
                # Amount
                # Usually in 'div.amount'
                amount_el = order.locator(".amount span, .amount-pay").first
                if amount_el.count() > 0:
                    amount_text = amount_el.inner_text()
                    # Remove currency symbol
                    clean_amount = re.sub(r'[^\d\.]', '', amount_text)
                    try:
                        total_amount = float(clean_amount)
                    except:
                        pass
                
                # Status
                # Usually in 'div.status' or 'span.order-status'
                status_el = order.locator(".status .order-status, .status-txt, span.order-status").first
                if status_el.count() > 0:
                    status = status_el.inner_text().strip()
                else:
                    # Try finding status text in the whole row text
                    full_text = order.inner_text()
                    for s in ["已完成", "待收货", "已取消", "待付款", "完成", "已库房", "正在出库"]:
                        if s in full_text:
                            status = s
                            break

                # --- Validation & Storage ---
                if order_id != "Unknown" and validate_date(order_date):
                    total_amount = validate_amount(total_amount)
                    
                    if check_order_exists(cursor, order_id):
                        print(f"    - Order {order_id} already exists.")
                        if incremental_mode:
                            print("    >> Found existing order. Stopping scrape for this year.")
                            stop_scraping = True
                            break
                    else:
                        print(f"    - Found NEW JD Order: {order_id} | {order_date} | {total_amount}")
                        try:
                            cursor.execute('''
                                INSERT OR IGNORE INTO orders (platform, order_id, order_date, total_amount, status, shop_name)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', ("JD", order_id, order_date, total_amount, status, shop_name))
                            
                            # Get DB ID
                            cursor.execute("SELECT id FROM orders WHERE platform = 'JD' AND order_id = ?", (order_id,))
                            row = cursor.fetchone()
                            if row:
                                db_order_id = row[0]
                                cursor.execute('''
                                    INSERT INTO order_items (order_id, product_title, product_price, quantity)
                                    VALUES (?, ?, ?, ?)
                                ''', (db_order_id, product_title, total_amount, 1))
                        except Exception as e:
                            print(f"    DB Error: {e}")
            except Exception as e:
                print(f"    - Error processing order {i}: {e}")

        conn.commit()

        if stop_scraping:
            break
            
        if count == 0:
            print("  No orders found. Stopping.")
            break

        # Pagination
        try:
            print("  Checking pagination...")
            next_btn = None
            
            # Strategy 1: Standard JD class 'pn-next'
            btn_candidates = page.locator("a.pn-next")
            if btn_candidates.count() > 0:
                print("  [DEBUG] Found 'a.pn-next'")
                next_btn = btn_candidates.first
            
            # Strategy 2: Text content '下一页'
            if not next_btn:
                btn_candidates = page.get_by_text("下一页", exact=True)
                if btn_candidates.count() > 0:
                     print("  [DEBUG] Found text '下一页'")
                     next_btn = btn_candidates.first

            # Strategy 3: Text content 'Next'
            if not next_btn:
                 btn_candidates = page.get_by_text("Next", exact=True)
                 if btn_candidates.count() > 0:
                     print("  [DEBUG] Found text 'Next'")
                     next_btn = btn_candidates.first

            # Strategy 4: Generic ui-pager-next class
            if not next_btn:
                btn_candidates = page.locator(".ui-pager-next")
                if btn_candidates.count() > 0:
                    print("  [DEBUG] Found '.ui-pager-next'")
                    next_btn = btn_candidates.first

            if next_btn and next_btn.is_visible():
                # Check for disabled state (often class includes 'disabled' or attribute 'disabled')
                class_attr = next_btn.get_attribute("class") or ""
                if "disabled" in class_attr.lower():
                     print("  Next button is disabled. Reached end.")
                     break
                
                print("  Navigating to next page...")
                try:
                    # Sometimes click might be intercepted, use force=True or JS click
                    next_btn.click(timeout=3000)
                except:
                    print("  Click failed, trying JS click...")
                    next_btn.evaluate("el => el.click()")

                time.sleep(random.uniform(3, 5))
                page_num += 1
            else:
                print("  No next button found (or not visible). Reached end.")
                # Debug: print pagination html
                try:
                    pager = page.locator(".ui-pager, .pagin, .pagination").first
                    if pager.count() > 0:
                        print(f"  [DEBUG] Pager HTML: {pager.inner_html()}")
                except:
                    pass
                break
        except Exception as e:
            print(f"  Pagination error: {e}")
            break

def scrape_jd(mode_arg=None):
    # ... (Keep initialization code same as before until "Detecting year filter...")
    # I will replace the year detection part below
    # ...
    
    # [Rest of the file setup code is assumed to be preserved by SearchReplace context if I target the right block]
    # But since I'm replacing scrape_jd, I need to include the setup.
    # To save tokens and avoid errors, I will use a targeted replacement for the scrape_jd function body or just the loop.
    # But wait, I defined scrape_page_loop as a helper. I need to make sure it's called.
    pass 


def scrape_jd(mode_arg=None):
    print("Starting JD scraper...")
    
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
    max_pages = float('inf') if mode == '1' else 50 
    
    if incremental_mode:
        print(">> 已启用增量抓取模式。")
        conn = get_db_connection()
        init_tables(conn)
        conn.close()
    else:
        print(">> 已启用全量抓取模式。")
        conn = get_db_connection()
        # For full scrape, we might want to be careful not to delete Taobao data
        # clear_tables only clears JD data
        clear_tables(conn)
        conn.close()

    with sync_playwright() as p:
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

        print("Navigating to JD login page...")
        try:
            page.goto("https://passport.jd.com/new/login.aspx")
        except Exception:
            pass

        print("-" * 50)
        print("请在打开的浏览器窗口中：")
        print("1. 手动完成京东账号登录")
        print("2. 确保页面跳转到'我的订单' (order.jd.com)")
        print("-" * 50)
        
        login_check_start = time.time()
        last_url = ""
        
        while True:
            target_page = None
            try:
                for p in context.pages:
                    try:
                        url = p.url
                        title = p.title()
                        if "order.jd.com" in url or "我的订单" in title:
                            target_page = p
                            break
                    except:
                        pass
            except:
                pass
            
            if target_page:
                page = target_page
                try:
                    page.bring_to_front()
                except:
                    pass
                print(f"页面确认成功！(URL: {page.url})")
                break
            
            try:
                current_url = page.url
            except:
                current_url = ""

            if current_url != last_url:
                print(f"Current URL: {current_url} - Waiting for order list...")
                last_url = current_url
            
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
        
        # --- Year Traversal Logic ---
        print("Detecting year filter...")
        
        # Try to find the year filter by text content "近三个月订单"
        # It's usually a selected option text
        time_filter = None
        try:
            # Find the element containing this text
            candidates = page.get_by_text("近三个月订单")
            count = candidates.count()
            print(f"[DEBUG] Found {count} elements with text '近三个月订单'")
            
            for i in range(count):
                el = candidates.nth(i)
                if el.is_visible():
                    # Check if it's clickable or has a parent that is a container
                    print(f"[DEBUG] Candidate {i} tag: {el.evaluate('el => el.tagName')}")
                    time_filter = el
                    break
        except Exception as e:
            print(f"[DEBUG] Error finding time filter: {e}")

        if time_filter:
            print("Found time filter trigger. Attempting to expand...")
            try:
                # Hover and click to ensure list is shown
                time_filter.hover()
                time.sleep(0.5)
                time_filter.click()
                time.sleep(1)
            except:
                pass
                
            # Now try to find all year options in the page
            # They should be visible now.
            # Look for elements matching year pattern "20\d\d年订单" or "今年内订单"
            # We search globally because the dropdown container might be attached to body
            
            # Get all links/items with text matching the pattern
            # Using evaluate to scan all <a> and <li> tags is safer
            found_years = page.evaluate("""() => {
                const results = [];
                const elements = document.querySelectorAll('a, li');
                for (const el of elements) {
                    const text = el.innerText.trim();
                    if (text.includes('订单') && (text.includes('年') || text.includes('今年'))) {
                        results.push(text);
                    }
                }
                return [...new Set(results)]; // Unique
            }""")
            
            print(f"Found year options: {found_years}")
            
            # Filter logic
            valid_years = []
            has_this_year = any("今年内" in y for y in found_years)
            
            for y in found_years:
                if "近三个月" in y and has_this_year:
                    continue
                valid_years.append(y)
            
            if not valid_years:
                print("No specific year options found (or only current view). Scraping current view.")
                scrape_page_loop(page, cursor, conn, incremental_mode, max_pages)
            else:
                for year_text in valid_years:
                    print(f"--- Switching to year view: {year_text} ---")
                    try:
                        # Determine 'd' parameter for URL navigation
                        d_val = None
                        if "今年" in year_text:
                            d_val = "2"
                        elif "2014年以前" in year_text:
                            d_val = "3"
                        else:
                            year_num_match = re.search(r'(\d{4})', year_text)
                            if year_num_match:
                                d_val = year_num_match.group(1)

                        if d_val:
                            print(f"Navigating to URL for year {year_text} (d={d_val})")
                            try:
                                target_url = f"https://order.jd.com/center/list.action?search=0&d={d_val}&s=4096"
                                page.goto(target_url)
                                # Wait for table to load
                                try:
                                    page.wait_for_selector(".order-tb", timeout=5000)
                                except:
                                    time.sleep(2)
                                
                                # For "Before 2014", force full scrape to ensure all pages are reached 
                                # even if there are overlaps or existing data.
                                year_incremental_mode = incremental_mode
                                if "2014年以前" in year_text:
                                    print("  >> Enforcing full scrape for 'Before 2014' to handle deep history.")
                                    year_incremental_mode = False

                                scrape_page_loop(page, cursor, conn, year_incremental_mode, max_pages)
                            except Exception as e_nav:
                                print(f"Navigation failed: {e_nav}")
                        else:
                            print(f"Could not determine 'd' parameter for year: {year_text}")
                            
                    except Exception as e:
                        print(f"Error processing year {year_text}: {e}")

        else:
            print("Could not identify time filter. Scraping current view only.")
            scrape_page_loop(page, cursor, conn, incremental_mode, max_pages)

        conn.commit()
        conn.close()
        print("JD Scraping completed.")

if __name__ == "__main__":
    scrape_jd()
