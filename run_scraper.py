import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.taobao import scrape_taobao
from scrapers.jd import scrape_jd

if __name__ == "__main__":
    print("-" * 50)
    print("请选择抓取平台：")
    print("1. 淘宝 (Taobao)")
    print("2. 京东 (JD)")
    print("-" * 50)
    
    # Check if platform is passed as argument
    if len(sys.argv) > 1 and sys.argv[1] in ['1', '2']:
        platform_choice = sys.argv[1]
        mode_arg = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        platform_choice = input("请输入选项 (1/2): ").strip()
        mode_arg = None

    if platform_choice == '1':
        scrape_taobao(mode_arg)
    elif platform_choice == '2':
        scrape_jd(mode_arg)
    else:
        print("无效的选项。")
