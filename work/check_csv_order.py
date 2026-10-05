import glob, os
import pandas as pd

# Check a sample of CSVs to see if dates are monotonic
sample_files = glob.glob('data/stock_data/*.csv')[:20]
needs_sort = 0
for f in sample_files:
    df = pd.read_csv(f)
    if not df['date'].is_monotonic_increasing or df['date'].duplicated().any():
        needs_sort += 1

print(f"Sample 20 files, need sort/dedup: {needs_sort}")
