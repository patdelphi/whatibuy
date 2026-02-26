import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.taobao import scrape_taobao

if __name__ == "__main__":
    scrape_taobao()
