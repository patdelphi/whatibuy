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

def get_db_connection():
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
        if val >= 0:
            return val
    except (ValueError, TypeError):
        pass
    return 0.0

def check_order_exists(cursor, order_id):
    """Checks if an order already exists in the database."""
    cursor.execute("SELECT 1 FROM orders WHERE platform = ? AND order_id = ?", ("Taobao", order_id))
    return cursor.fetchone() is not None

def scrape_taobao():
    print("Starting Taobao scraper...")
    
    # User Prompt Logic
    print("-" * 50)
    print("请选择抓取模式：")
    print("1. 全量抓取 (Full Scrape) - 抓取所有页面的数据")
    print("2. 增量抓取 (Incremental Scrape) - 遇到数据库中已存在的订单时停止")
    print("3. 跳过抓取 (Skip) - 直接退出")
    print("-" * 50)
    
    mode = input("请输入选项 (1/2/3): ").strip()
    
    if mode == '3':
        print("已跳过抓取。")
        return
        
    incremental_mode = (mode == '2')
    max_pages = float('inf') if mode == '1' else 50 # No limit for full scrape
    
    if incremental_mode:
        print(">> 已启用增量抓取模式。如果遇到已存在的订单，抓取将自动停止。")
    else:
        print(">> 已启用全量抓取模式。")

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
        
        while True:
            input("当您在浏览器中看到订单列表后，请按回车键继续...")
            print("正在确认页面状态...")
            current_url = page.url
            if "list_bought_items.htm" in current_url:
                print(f"页面确认成功！(URL: {current_url})")
                break
            else:
                print(f"警告：当前页面似乎不是订单列表页 (URL: {current_url})")
                print("请在浏览器中手动跳转到'已买到的宝贝'，或者等待页面加载完成。")
                choice = input("输入 'r' 重试检查，输入 'g' 尝试强制跳转，输入 'q' 退出: ").strip().lower()
                if choice == 'g':
                    print("尝试自动跳转到订单页面...")
                    try:
                        page.goto("https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm")
                        time.sleep(3)
                    except Exception as e:
                        print(f"跳转请求已发送: {e}")
                        time.sleep(3)
                elif choice == 'q':
                    print("用户取消操作。")
                    context.close()
                    return

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
                    
                    # Strategy B: Look for generic price if Real Payment not found
                    if total_amount == 0.0:
                        price_els = order.query_selector_all('[class*="price-integer"], [class*="price-decimal"]')
                        if price_els:
                            # Construct price from parts if split
                            full_price_text = "".join([el.inner_text() for el in price_els])
                            try:
                                total_amount = float(re.search(r'[\d\.]+', full_price_text).group(0))
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

            # Pagination Logic
            try:
                next_btn = page.get_by_role("button", name="下一页")
                
                if not next_btn or not next_btn.is_visible():
                    next_btn = page.query_selector("button.pagination-next, li.pagination-next, .next-pagination-item")
                
                if not next_btn and not page.get_by_text("下一页").is_visible():
                    print("Next button not found. Looking for numeric pagination...")
                    current_page_el = page.query_selector(".pagination-item-active, .active")
                    if current_page_el:
                        try:
                            current_page_num = int(current_page_el.inner_text())
                            next_page_num = current_page_num + 1
                            
                            next_num_btn = page.get_by_text(str(next_page_num), exact=True)
                            if next_num_btn.is_visible():
                                next_btn = next_num_btn
                            else:
                                next_num_btn = page.locator(f"//a[text()='{next_page_num}'] | //button[text()='{next_page_num}']")
                                if next_num_btn.count() > 0:
                                    next_btn = next_num_btn.first
                        except ValueError:
                            pass
                
                if next_btn:
                    is_disabled = False
                    if hasattr(next_btn, 'is_disabled'):
                        is_disabled = next_btn.is_disabled()
                    elif hasattr(next_btn, 'get_attribute'):
                        is_disabled = next_btn.get_attribute("disabled") is not None or "disabled" in (next_btn.get_attribute("class") or "")

                    if not is_disabled:
                        print("Navigating to next page...")
                        next_btn.click()
                        time.sleep(random.uniform(3, 6)) 
                        page_num += 1
                    else:
                        print("Next button/page is disabled. Reached end.")
                        break
                else:
                    # More careful check for next text
                    next_text_loc = page.locator("text=下一页")
                    if next_text_loc.count() > 0:
                        # Check if any of these are visible and likely clickable
                        clicked = False
                        for i in range(next_text_loc.count()):
                             el = next_text_loc.nth(i)
                             if el.is_visible():
                                 # Check if parent is disabled button
                                 # This is hard to do perfectly, but usually disabled elements have a class
                                 # Let's try to click and if it fails or nothing happens, our duplicate check will catch it next loop
                                 print(f"Found '下一页' text (element {i}), trying to click...")
                                 try:
                                     el.click(timeout=3000)
                                     clicked = True
                                     time.sleep(4)
                                     break
                                 except:
                                     print("Click failed.")
                        
                        if clicked:
                            page_num += 1
                        else:
                            print("Found '下一页' text but could not click or it was disabled.")
                            break
                    else:
                        print("No next page button found.")
                        break
                        
            except Exception as e:
                print(f"Pagination error: {e}")
                break

        conn.commit()
        conn.close()
        print("Scraping completed.")

if __name__ == "__main__":
    scrape_taobao()
