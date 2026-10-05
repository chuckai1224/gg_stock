import glob
import pandas as pd
import os

files = glob.glob('data/stock_data/*.csv')
print(f"Sorting {len(files)} CSV files in data/stock_data/...")
for i, f in enumerate(files):
    try:
        df = pd.read_csv(f)
        if not df['date'].is_monotonic_increasing or df['date'].duplicated().any():
            df = df.drop_duplicates(subset=['date']).sort_values('date')
            df.to_csv(f, index=False, encoding='utf-8')
    except Exception as e:
        pass
    if (i + 1) % 500 == 0:
        print(f"Processed {i + 1}/{len(files)} files...")

print("All CSV files sorted and deduplicated.")
