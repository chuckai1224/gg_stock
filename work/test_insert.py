import sys, os
sys.path.insert(0, os.path.abspath('.'))
import stock_comm as comm
from datetime import datetime

d = datetime(2026, 9, 11)
print(f"Testing insert_daily_stock_data for {d}...")
comm.insert_daily_stock_data(d)
print("Done.")
