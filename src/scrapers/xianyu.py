import sys
from playwright.sync_api import sync_playwright
import sqlite3
import os
import time
import re
import random
from datetime import datetime, timedelta

# Add src to python path to allow imports if run directly
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'whatibuy.db')
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'user_data_xianyu')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tables(conn):
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

def check_order_exists(cursor, order_id):
    cursor.execute("SELECT 1 FROM orders WHERE platform = 'Xianyu' AND order_id = ?", (order_id,))
    return cursor.fetchone() is not None

def validate_date(date_str):
    try:
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
    except ValueError:
        pass
    return None

def validate_amount(amount):
    try:
        val = float(amount)
        if val >= 0 and val < 10000000:
            return val
    except (ValueError, TypeError):
        pass
    return 0.0

def clear_platform_data(conn):
    """Clears all data for Xianyu platform only."""
    cursor = conn.cursor()
    
    try:
        # 1. Delete related items for Xianyu orders
        # Using subquery to be safer and cleaner
        cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE platform='Xianyu')")
        
        # 2. Delete orders
        cursor.execute("DELETE FROM orders WHERE platform='Xianyu'")
        
        conn.commit()
        print("Cleared Xianyu data successfully (if any).")
    except Exception as e:
        print(f"Error clearing data: {e}")

def scrape_xianyu(mode_arg=None):
    print("Starting Xianyu (Goofish) scraper...")
    
    print("-" * 50)
    print("请选择抓取模式：")
    print("1. 全量抓取 (Full Scrape) - 清空闲鱼历史数据并重新抓取")
    print("2. 增量抓取 (Incremental Scrape)")
    print("-" * 50)
    
    if mode_arg:
        mode = str(mode_arg)
    else:
        mode = input("请输入选项 (1/2): ").strip()
    
    incremental_mode = (mode == '2')
    max_pages = float('inf') if mode == '1' else 50
    
    conn = get_db_connection()
    init_tables(conn)

    if not incremental_mode:
        print(">> 全量模式：正在清空旧的闲鱼数据...")
        clear_platform_data(conn)

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
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # 1. Login Phase
        target_url = "https://www.goofish.com/bought"
        print(f"Navigating to {target_url}...")
        
        try:
            page.goto(target_url)
        except:
            pass
            
        print("-" * 50)
        print("请在打开的浏览器窗口中：")
        print("1. 手动完成闲鱼账号登录")
        print("2. 确保页面跳转到'已买到的宝贝' (订单列表页)")
        print("-" * 50)
        
        input(">> 登录完成并进入订单列表页后，请按回车键继续...")
        
        print("Login confirmed by user. Starting data extraction...")
        time.sleep(3)
        
        cursor = conn.cursor()
        page_num = 1
        stop_scraping = False
        consecutive_existing_orders = 0
        
        last_height = 0
        
        no_change_counter = 0

        while not stop_scraping:
            print(f"Scanning for orders (Page load {page_num})...")
            
            # DEBUG: Check if '订单号' exists in page text
            page_text = page.inner_text("body")
            if "订单号" not in page_text:
                print(">> WARNING: '订单号' text NOT found in page body. Page content preview:")
                print(page_text[:500].replace('\n', ' '))
                # Try checking iframes
                frames = page.frames
                for frame in frames:
                    try:
                        if "订单号" in frame.inner_text("body"):
                            print(f">> FOUND '订单号' in iframe: {frame.url}")
                            # If found in iframe, we should switch strategy to use that frame
                            # But for now just logging.
                    except:
                        pass
            else:
                print(">> '订单号' text found in page body.")

            # 1. Scroll down to trigger lazy loading
            for i in range(5):
                page.keyboard.press("PageDown")
                time.sleep(1)
            
            # Check if we reached bottom
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                print("Page height did not increase.")
                no_change_counter += 1
                if no_change_counter >= 3:
                    print(">> Page height stable for multiple checks. End of list reached.")
                    stop_scraping = True
                    break
            else:
                no_change_counter = 0 
            last_height = new_height

            # 2. Find orders using JS for performance
            try:
                # Execute JS to find order cards and return their text content
                # We filter by elements that have not been scraped yet
                new_cards_text = page.evaluate("""
                    () => {
                        const newOrders = [];
                        const seenElements = new Set();
                        
                        function isOrderCard(el) {
                            if (el.hasAttribute('data-trae-scraped')) return false;
                            const txt = el.innerText;
                            if ((txt.includes('¥') || txt.includes('￥')) && 
                                (txt.includes('交易') || txt.includes('评价') || txt.includes('联系') || txt.includes('实付'))) {
                                return true;
                            }
                            return false;
                        }

                        // Strategy 1: '联系卖家' buttons
                        const buttons = Array.from(document.querySelectorAll("button, a"));
                        const contactBtns = buttons.filter(b => b.innerText.includes('联系卖家'));
                        
                        for (const btn of contactBtns) {
                            let card = btn;
                            let found = false;
                            for (let i = 0; i < 6; i++) {
                                card = card.parentElement;
                                if (!card) break;
                                if (isOrderCard(card)) {
                                    found = true;
                                    break;
                                }
                            }
                            
                            if (found && !seenElements.has(card)) {
                                seenElements.add(card);
                                card.setAttribute('data-trae-scraped', 'true');
                                newOrders.push(card.innerText);
                            }
                        }
                        
                        // Strategy 2: Price symbols (fallback if few found)
                        if (newOrders.length < 5) {
                            const treeWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                            let node;
                            const priceNodes = [];
                            while(node = treeWalker.nextNode()) {
                                if (node.nodeValue.includes('¥') || node.nodeValue.includes('￥')) {
                                    if (node.parentElement) priceNodes.push(node.parentElement);
                                }
                            }
                            
                            for (const priceEl of priceNodes) {
                                 let card = priceEl;
                                 let found = false;
                                 for (let i = 0; i < 6; i++) {
                                     card = card.parentElement;
                                     if (!card) break;
                                     if (isOrderCard(card) && !seenElements.has(card)) {
                                         found = true;
                                         break;
                                     }
                                 }
                                 if (found) {
                                    seenElements.add(card);
                                    card.setAttribute('data-trae-scraped', 'true');
                                    newOrders.push(card.innerText);
                                 }
                            }
                        }
                        
                        return newOrders;
                    }
                """)
                
                print(f"  Extracted {len(new_cards_text)} new order cards via JS.")
                
                import hashlib
                valid_orders_data = []

                for text in new_cards_text:
                    try:
                        # --- EXTRACT FIELDS ---
                        
                        # 1. Order ID (Try find, else Generate)
                        order_id = "Unknown"
                        id_match = re.search(r'订单号[：:]?\s*(\d+)', text)
                        if id_match:
                            order_id = id_match.group(1)
                        
                        # 2. Price
                        total_amount = 0.0
                        price_match = re.search(r'实付.*?¥\s*([\d\.]+)', text)
                        if not price_match:
                             price_match = re.search(r'[￥¥]\s*([\d\.]+)', text)
                        if price_match:
                            try:
                                total_amount = float(price_match.group(1))
                            except: pass
                            
                        # 3. Status
                        status = "Unknown"
                        # Clean text first: remove extra whitespace
                        clean_text = text.replace(' ', '').replace('\n', '')
                        
                        if "交易成功" in clean_text: status = "交易成功"
                        elif "已完成" in clean_text: status = "交易成功"
                        elif "待发货" in clean_text: status = "待发货"
                        elif "待付款" in clean_text: status = "待付款"
                        elif "交易关闭" in clean_text: status = "交易关闭"
                        elif "退款" in clean_text: status = "退款"
                        
                        if status == "Unknown":
                             # Fallback: check original text split
                             for s in ["交易成功", "已完成", "待发货", "待付款", "交易关闭", "退款", "评价"]:
                                 if s in text.split('\n')[0:5]: 
                                     status = s
                                     break
                        
                        # 4. Shop Name
                        shop_name = "个人卖家"
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if lines and lines[0] != status:
                            shop_name = lines[0]
                            
                        # 5. Title
                        product_title = "Unknown"
                        for l in lines:
                            if len(l) > 10 and l != shop_name and l != status and "订单" not in l and "¥" not in l:
                                product_title = l
                                break
                                
                        # 6. Date (Mock Time Strategy)
                        extracted_date_str = None
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                        if date_match:
                            extracted_date_str = date_match.group(1)

                        # --- GENERATE ID IF MISSING ---
                        if order_id == "Unknown":
                            unique_str = f"{shop_name}_{product_title}_{total_amount}"
                            hash_id = hashlib.md5(unique_str.encode()).hexdigest()[:8].upper()
                            order_id = f"HASH-{hash_id}"
                            
                        valid_orders_data.append({
                            "order_id": order_id,
                            "extracted_date": extracted_date_str,
                            "total_amount": total_amount,
                            "status": status,
                            "shop_name": shop_name,
                            "product_title": product_title
                        })
                            
                    except Exception as e:
                        pass
                
            except Exception as e:
                print(f"Error finding orders: {e}")
                valid_orders_data = []
            
            # Initialize counters if not present
            if 'total_items_processed' not in locals():
                total_items_processed = 0
            if 'scrape_start_time' not in locals():
                scrape_start_time = datetime.now()
            
            current_batch_count = 0
            
            for data in valid_orders_data:
                if stop_scraping: break
                
                # Mock Time Logic: Decrement 1 minute per item to ensure clear ordering
                mock_time = scrape_start_time - timedelta(minutes=total_items_processed)
                final_date_str = mock_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # ID Construction
                timestamp_id_part = mock_time.strftime("%Y%m%d%H%M%S")
                temp_id = data["order_id"]
                if temp_id.startswith("HASH-"):
                    clean_hash = temp_id.replace("HASH-", "")
                    order_id = f"XY-{timestamp_id_part}-{clean_hash}"
                else:
                    order_id = data["order_id"]

                total_amount = data["total_amount"]
                status = data["status"]
                shop_name = data["shop_name"]
                product_title = data["product_title"]

                total_amount = validate_amount(total_amount)
                
                print(f"  - NEW Order: {order_id} | {final_date_str} | {total_amount} | {product_title[:15]}")
                consecutive_existing_orders = 0
                current_batch_count += 1
                total_items_processed += 1
                
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO orders (platform, order_id, order_date, total_amount, status, shop_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', ("Xianyu", order_id, final_date_str, total_amount, status, shop_name))
                    
                    cursor.execute("SELECT id FROM orders WHERE platform='Xianyu' AND order_id=?", (order_id,))
                    result = cursor.fetchone()
                    if result:
                        oid = result[0]
                        cursor.execute('''
                            INSERT INTO order_items (order_id, product_title, product_price, quantity)
                            VALUES (?, ?, ?, ?)
                        ''', (oid, product_title, total_amount, 1))
                        conn.commit()
                except Exception as db_e:
                    print(f"DB Error: {db_e}")

            if current_batch_count == 0 and consecutive_existing_orders > 20:
                print(">> No new orders found in this batch and seen many existing ones.")
                # Check if there is a "No more data" indicator
                if page.locator("text=没有更多").count() > 0 or page.locator("text=底了").count() > 0:
                    print("End of list detected.")
                    stop_scraping = True
                else:
                    # Try scrolling more?
                    pass
            
            # Try to load more
            print("Scrolling to load more...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
            
            # Detect if height changed
            new_height_after = page.evaluate("document.body.scrollHeight")
            if new_height_after <= last_height:
                print("Page height did not increase. End of list?")
                # Double check "no more" text
                if page.locator("text=没有更多").count() > 0 or page.locator("text=到底").count() > 0:
                     stop_scraping = True
                else:
                    # Maybe network slow?
                    time.sleep(2)
            
            page_num += 1
            if page_num > 100: stop_scraping = True # Safety break

        conn.close()
        print("Done.")

if __name__ == "__main__":
    scrape_xianyu()