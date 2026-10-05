import sys, os
sys.path.insert(0, os.path.abspath('.'))
import stock_comm as comm
from datetime import datetime

dates_to_insert = [
    datetime(2026, 9, 14),
    datetime(2026, 10, 1),
    datetime(2026, 10, 2),
]

for d in dates_to_insert:
    print(f"Inserting daily stock data for {d.strftime('%Y-%m-%d')}...")
    comm.insert_daily_stock_data(d)

print("All dates inserted successfully!")
