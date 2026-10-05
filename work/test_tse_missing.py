import sys, os
sys.path.insert(0, os.path.abspath('.'))
from crawl import Crawler

c = Crawler()
test_dates = [(2026, 9, 14), (2026, 9, 25), (2026, 9, 28), (2026, 10, 2)]
for y, m, d in test_dates:
    print(f"Testing TSE {y}-{m:02d}-{d:02d}:")
    try:
        c._get_tse_data((y, m, d))
    except Exception as e:
        print(f"Error {y}{m:02d}{d:02d}: {e}")
