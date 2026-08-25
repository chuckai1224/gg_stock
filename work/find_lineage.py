import os

search_roots = [r"D:\LineageRemastered", r"C:\Program Files (x86)\Lineage", r"C:\Lineage", r"D:\Lineage"]
found = []

for root_dir in [r"D:\LineageRemastered", r"C:", r"D:"]:
    if os.path.exists(root_dir):
        try:
            for root, dirs, files in os.walk(root_dir):
                for f in files:
                    if f.lower() in ['lin.bin', 'lineage.exe', 'linlauncher.exe']:
                        full_path = os.path.join(root, f)
                        found.append(full_path)
                # prevent deep search into venv/node_modules/windows
                if root.count(os.sep) > 4 and root_dir in [r"C:", r"D:"] and not root.lower().startswith(r"d:\lineage"):
                    del dirs[:]
        except Exception:
            pass

print("=== 找到的天堂相關程式路徑 ===")
for p in set(found):
    print(p)
