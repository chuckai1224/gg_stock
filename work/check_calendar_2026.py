import pandas as pd
from datetime import datetime, timedelta
import glob, os

start = datetime(2026, 9, 1)
end = datetime(2026, 10, 2)
curr = start
all_weekdays = []
while curr <= end:
    if curr.weekday() < 5:  # Monday to Friday
        all_weekdays.append(curr.strftime('%Y%m%d'))
    curr += timedelta(days=1)

print("All weekdays 2026-09-01 to 2026-10-02:")
print(all_weekdays)
print(f"Total weekdays: {len(all_weekdays)}")

tse_existing = [os.path.basename(f) for f in glob.glob("data/exchange/tse/2026*")]
otc_existing = [os.path.basename(f) for f in glob.glob("data/exchange/otc/2026*")]

print("\nMissing in data/exchange/tse:")
missing_tse = [d for d in all_weekdays if d not in tse_existing]
print(missing_tse)

print("\nMissing in data/exchange/otc:")
missing_otc = [d for d in all_weekdays if d not in otc_existing]
print(missing_otc)
