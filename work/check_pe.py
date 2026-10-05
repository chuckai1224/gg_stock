import glob, os

pe_files = sorted(glob.glob("data/down_pe_networth_yield/tse*.csv"))
print("PE files count:", len(pe_files))
print("Latest PE files:", [os.path.basename(f) for f in pe_files[-5:]] if pe_files else "none")
