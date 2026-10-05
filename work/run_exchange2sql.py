import sys, os
sys.path.insert(0, os.path.abspath('.'))
import stock_comm as comm
from datetime import datetime

dates = [
    datetime(2026, 9, 11),
    datetime(2026, 9, 14),
    datetime(2026, 10, 1),
    datetime(2026, 10, 2),
]

for d in dates:
    print(f"Running exchange2sql for {d.strftime('%Y-%m-%d')}...")
    comm.exchange2sql(d, d)
print("exchange2sql done.")
