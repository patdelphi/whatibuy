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
        cursor.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE platform='Xianyu')")
        cursor.execute("DELETE FROM orders WHERE platform='Xianyu'")
        conn.commit()
        print("Cleared Xianyu data successfully.")
    except Exception as e:
        print(f"Error clearing data: {e}")

def extract_detail_data(context, url):
    """
    Opens a new page to scrape details from a specific URL.
    Returns a dict with 'id', 'date', 'title', or None if failed.
    """
    page = context.new_page()
    result = {'id': None, 'date': None, 'title': None}
    try:
        # Anti-detection: Random delay
        time.sleep(random.uniform(2, 4))
        
        try:
            page.goto(url, timeout=30000)
        except Exception as e:
            print(f"    [Detail Extract] Navigation failed: {e}")
            return result

        # Anti-detection: Wait and random scroll
        time.sleep(random.uniform(1.0, 2.0))
        try:
            page.evaluate(f"window.scrollBy(0, {random.randint(100, 300)})")
        except: pass
        
        # Check for verification/login/captcha
        if "login" in page.url or "verify" in page.url or "sec" in page.url:
            print("    [Detail Extract] DETECTED CAPTCHA/LOGIN. Pausing for 15s...")
            time.sleep(15)
        
        # Extract data using JS
        data = page.evaluate("""
            () => {
                const res = { id: null, date: null, title: null };
                const bodyText = document.body.innerText;
                
                // 1. ID Extraction
                try {
                    const urlParams = new URLSearchParams(window.location.search);
                    const urlId = urlParams.get('orderId') || urlParams.get('bizOrderId');
                    if (urlId) res.id = urlId;
                } catch(e) {}
                
                if (!res.id) {
                    const idMatch = bodyText.match(/订单号[：:]?\\s*(\\d+)/);
                    if (idMatch) res.id = idMatch[1];
                }
                
                // 2. Date Extraction
                const dateMatch = bodyText.match(/(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2})/);
                if (dateMatch) res.date = dateMatch[1];
                
                // 3. Title Extraction
                // Try meta tag first
                const metaTitle = document.querySelector('meta[property="og:title"]');
                if (metaTitle && metaTitle.content) res.title = metaTitle.content;
                
                return res;
            }
        """)
        
        if data:
            result = data
            
    except Exception as e:
        print(f"    [Detail Extract] Error: {e}")
    finally:
        try:
            page.close()
        except: pass
        
    return result

def process_details(page, conn, orders_to_detail):
    """Processes a list of (db_id, url) tuples to scrape details."""
    cursor = conn.cursor()
    print(f"\n>> Starting Detail Page Scrape for {len(orders_to_detail)} orders...")
    
    # We need a context to open new pages, but here we are passed a 'page'.
    # We should use the context of that page.
    context = page.context
            
    for i, (db_id, url) in enumerate(orders_to_detail):
        print(f"[{i+1}/{len(orders_to_detail)}] Processing: {url[:60]}...")
        
        # Use our robust extraction function
        detail_data = extract_detail_data(context, url)
        
        real_id = detail_data.get('id')
        real_date = detail_data.get('date')
        real_title = detail_data.get('title')

        updates = []
        params = []
        
        if real_title:
            cursor.execute("UPDATE order_items SET product_title = ? WHERE order_id = ?", (real_title, db_id))
            print(f"  -> Title: {real_title[:20]}...")
        
        if real_id:
            updates.append("order_id = ?")
            params.append(real_id)
            print(f"  -> ID: {real_id}")
            
        if real_date:
            updates.append("order_date = ?")
            params.append(real_date)
            print(f"  -> Date: {real_date}")
            
        if updates:
            params.append(db_id)
            sql = f"UPDATE orders SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(sql, params)
            
        conn.commit()

def scrape_xianyu(mode_arg=None):
    print("Starting Xianyu (Goofish) scraper...")
    print("-" * 50)
    print("1. Full Scrape (Clear Data)")
    print("2. Incremental Scrape (New Orders Only)")
    print("3. Detail Scrape Only (Fix Missing Details)")
    print("-" * 50)
    
    mode = str(mode_arg) if mode_arg else input("Option (1/2/3): ").strip()
    
    conn = get_db_connection()
    init_tables(conn)

    # Mode 3: Detail Scrape Only
    if mode == '3':
        print(">> Detail Scrape Mode...")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.id, oi.product_url 
            FROM orders o 
            JOIN order_items oi ON o.id = oi.order_id 
            WHERE o.platform = 'Xianyu' 
            AND oi.product_url IS NOT NULL 
            AND oi.product_url != ''
            AND (o.order_date IS NULL OR o.order_date LIKE '2026%') -- Filter by mock date or missing date
        ''')
        orders_to_detail = cursor.fetchall()
        
        if not orders_to_detail:
            print("No orders need detail updating.")
            return

        with sync_playwright() as p:
            args = ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-infobars']
            context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="msedge", args=args, viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            page.goto("https://www.goofish.com/bought")
            input(">> Login and Press Enter...")
            process_details(page, conn, orders_to_detail)
        return

    incremental_mode = (mode == '2')
    if not incremental_mode:
        print(">> Clearing old data...")
        clear_platform_data(conn)

    with sync_playwright() as p:
        args = ['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-infobars']
        try:
            context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="msedge", args=args, viewport={'width': 1280, 'height': 800})
        except:
            context = p.chromium.launch_persistent_context(user_data_dir=USER_DATA_DIR, headless=False, channel="chrome", args=args, viewport={'width': 1280, 'height': 800})
            
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("Navigating to Order List...")
        page.goto("https://www.goofish.com/bought")
        input(">> Login and Press Enter when list is visible...")
        
        cursor = conn.cursor()
        page_num = 1
        stop_scraping = False
        last_height = 0
        no_change_counter = 0
        total_items_processed = 0
        orders_to_detail = []
        scrape_start_time = datetime.now()

        while not stop_scraping:
            print(f"Scanning Page {page_num}...")
            
            # Scroll
            for i in range(5):
                page.keyboard.press("PageDown")
                time.sleep(1)
            
            # Check Height
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                no_change_counter += 1
                if no_change_counter >= 3:
                    print(">> End of list reached.")
                    stop_scraping = True
                    break
            else:
                no_change_counter = 0 
            last_height = new_height

            # Extract Cards
            new_cards = page.evaluate("""
                () => {
                    const cards = [];
                    
                    // Helper to check if an element is a card container
                    function isCard(el) {
                        const txt = el.innerText;
                        return (txt.includes('¥') || txt.includes('￥')) && 
                               (txt.includes('交易') || txt.includes('待发货') || txt.includes('已完成'));
                    }

                    // Strategy: Find specific anchors and walk UP to the container
                    const anchors = Array.from(document.querySelectorAll('a, button'))
                                    .filter(el => {
                                        const txt = el.innerText;
                                        const hr = el.href || "";
                                        return txt.includes('联系卖家') || txt.includes('订单详情') || 
                                               hr.includes('order-detail') || hr.includes('itemId=');
                                    });
                    
                    const processedCards = new Set();

                    for (const startEl of anchors) {
                        let card = startEl;
                        // Walk up to find the container div
                        for (let i = 0; i < 10; i++) {
                            card = card.parentElement;
                            if (!card || card.tagName === 'BODY') break;
                            
                            // Check if this container is already processed or is an order card
                            if (card.hasAttribute('data-trae-scraped')) {
                                processedCards.add(card); // Already handled
                                break;
                            }
                            
                            if (isCard(card)) {
                                // Mark it and collect info
                                card.setAttribute('data-trae-scraped', 'true');
                                processedCards.add(card);

                                const links = Array.from(card.querySelectorAll('a'));
                                let detailUrl = "";
                                let orderId = null;

                                // Extract link/ID
                                const idLink = links.find(l => l.href && (l.href.includes('orderId=') || l.href.includes('bizOrderId=')));
                                if (idLink) {
                                    detailUrl = idLink.href;
                                    const match = detailUrl.match(/[?&](?:bizOrderId|orderId)=(\\d+)/);
                                    if (match) orderId = match[1];
                                }

                                if (!detailUrl) {
                                    const detailLink = links.find(l => l.href && l.href.includes('order-detail'));
                                    if (detailLink) detailUrl = detailLink.href;
                                }

                                cards.push({
                                    text: card.innerText,
                                    detailUrl: detailUrl,
                                    extractedId: orderId
                                });
                                break; // Found the card, move to next anchor
                            }
                        }
                    }
                    return cards;
                }
            """)
            
            print(f"  Found {len(new_cards)} new cards.")

            for item in new_cards:
                text = item['text']
                detail_url = item['detailUrl']
                order_id = item['extractedId']

                # Python fallback extraction
                if not order_id and detail_url:
                     match = re.search(r'[?&](?:bizOrderId|orderId)=(\d+)', detail_url)
                     if match: order_id = match.group(1)
                
                if not order_id:
                     # Text fallback
                     match = re.search(r'订单号[：:]?\s*(\d+)', text)
                     if match: order_id = match.group(1)

                if not order_id:
                    # Try visiting detail page NOW
                    if detail_url:
                        print(f"    >> Visiting detail to find ID: {detail_url[:40]}...")
                        detail_data = extract_detail_data(context, detail_url)
                        order_id = detail_data.get('id')
                
                if not order_id:
                    # Generate Mock ID as fallback
                    import hashlib
                    # Use a combination of price, text content snippet to create a semi-unique hash
                    # We can't use date because we don't have it yet.
                    unique_str = f"{text[:50]}_{total_amount}_{page_num}"
                    hash_id = hashlib.md5(unique_str.encode()).hexdigest()[:12].upper()
                    # Use a prefix to identify these as mock IDs
                    order_id = f"XY-MOCK-{hash_id}"
                    print(f"    >> WARNING: Could not find Real ID. Generated Mock ID: {order_id}")

                # Parse other fields
                total_amount = 0.0
                price_match = re.search(r'[￥¥]\s*([\d\.]+)', text)
                if price_match: total_amount = validate_amount(price_match.group(1))

                status = "Unknown"
                for s in ["交易成功", "已完成", "待发货", "待付款", "交易关闭", "退款"]:
                    if s in text: 
                        status = s
                        break
                
                # Extract Title from text (simple heuristic)
                # Usually title is the longest line that is not status/shop/price
                product_title = "Unknown Title"
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                for l in lines:
                    if len(l) > 5 and l != status and "订单" not in l and "¥" not in l and "实付" not in l and "联系" not in l:
                        product_title = l
                        break

                # Mock Date (updated later)
                mock_time = scrape_start_time - timedelta(minutes=total_items_processed)
                final_date_str = mock_time.strftime("%Y-%m-%d %H:%M:%S")

                print(f"  - Order: {order_id} | {status} | ¥{total_amount} | {product_title[:15]}...")

                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO orders (platform, order_id, order_date, total_amount, status, shop_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', ("Xianyu", order_id, final_date_str, total_amount, status, "个人卖家"))
                    
                    # Get internal ID
                    cursor.execute("SELECT id FROM orders WHERE platform='Xianyu' AND order_id=?", (order_id,))
                    oid = cursor.fetchone()[0]
                    
                    # Insert Item
                    cursor.execute('''
                        INSERT OR IGNORE INTO order_items (order_id, product_title, product_price, quantity, product_url)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (oid, product_title, total_amount, 1, detail_url))
                    
                    if detail_url:
                        orders_to_detail.append((oid, detail_url))
                        
                    conn.commit()
                    total_items_processed += 1
                except Exception as e:
                    print(f"    DB Error: {e}")

            page_num += 1
            if page_num > 50: stop_scraping = True

        if orders_to_detail:
            process_details(page, conn, orders_to_detail)

        conn.close()
        print("Done.")

if __name__ == "__main__":
    scrape_xianyu(sys.argv[1] if len(sys.argv) > 1 else None)
