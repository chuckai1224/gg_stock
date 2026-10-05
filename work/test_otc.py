import sys, os
sys.path.insert(0, os.path.abspath('.'))
from crawl import Crawler

c = Crawler()
print("Testing 2026-09-01 OTC:")
c._get_otc_data((2026, 9, 1))

print("Testing 2026-09-11 OTC:")
c._get_otc_data((2026, 9, 11))

print("Testing 2026-10-01 OTC:")
c._get_otc_data((2026, 10, 1))

print("Testing 2026-10-02 OTC:")
c._get_otc_data((2026, 10, 2))
