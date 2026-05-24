# -*- coding: utf-8 -*-
"""
make_snapshot.py — 打包資料快照 / 更新下載連結

用法：
    # 步驟 1：打包（生成 gg_stock_data_YYYYMMDD.tar.gz）
    .\\venv\\Scripts\\python.exe make_snapshot.py

    # 步驟 2：把 .tar.gz 上傳到 Google Drive，從分享連結取得 file_id
    #   分享連結格式：https://drive.google.com/file/d/<file_id>/view?usp=drive_link

    # 步驟 3：更新 download_snapshot.py 與 data_sources.md
    .\\venv\\Scripts\\python.exe make_snapshot.py --update <file_id>
"""
import os
import re
import sys
import tarfile
from datetime import datetime

# ── 設定 ─────────────────────────────────────────────────────────────────────

INCLUDE_PATHS = [
    'sql',
    'data/stock_data',
    'data/down_pe_networth_yield',
    'data/director/final',
    'data/revenue',       # 若不存在會自動略過
]

DOWNLOAD_SCRIPT = 'download_snapshot.py'
DATA_SOURCES_MD = 'data_sources.md'


# ── pack ──────────────────────────────────────────────────────────────────────

def pack():
    today = datetime.today().strftime('%Y%m%d')
    out_name = f'gg_stock_data_{today}.tar.gz'

    print(f'打包快照：{out_name}')
    total_files = 0
    with tarfile.open(out_name, 'w:gz') as tar:
        for path in INCLUDE_PATHS:
            if not os.path.exists(path):
                print(f'  略過（不存在）：{path}')
                continue
            print(f'  加入：{path}/ ...', end='', flush=True)
            before = total_files
            tar.add(path, arcname=path)
            # 計算加入了幾個檔案
            added = sum(1 for m in tar.getmembers() if m.isfile()) - before
            total_files += added
            print(f' ({added} 檔)')

    size_mb = os.path.getsize(out_name) / 1024 / 1024
    print(f'\n完成：{out_name}  ({size_mb:.1f} MB，共 {total_files} 個檔案)')
    print()
    print('下一步：')
    print(f'  1. 上傳 {out_name} 到 Google Drive（取代舊版本或新增）')
    print(f'  2. 開啟分享連結，從 URL 複製 file_id')
    print(f'     格式：https://drive.google.com/file/d/<file_id>/view')
    print(f'  3. 執行：.\\venv\\Scripts\\python.exe make_snapshot.py --update <file_id>')
    return out_name, today, size_mb


# ── update ────────────────────────────────────────────────────────────────────

def update(file_id):
    today = datetime.today().strftime('%Y%m%d')
    snap_name = f'gg_stock_data_{today}.tar.gz'
    date_display = f'{today[:4]}-{today[4:6]}-{today[6:]}'  # YYYY-MM-DD

    # 計算 tar.gz 大小（若剛打包完就在目錄裡）
    size_str = ''
    if os.path.exists(snap_name):
        mb = os.path.getsize(snap_name) / 1024 / 1024
        size_str = f'{mb:.0f} MB'

    gdrive_url = f'https://drive.google.com/file/d/{file_id}/view?usp=drive_link'

    # ── 更新 download_snapshot.py ─────────────────────────────────────────
    with open(DOWNLOAD_SCRIPT, 'r', encoding='utf-8') as f:
        src = f.read()

    src = re.sub(
        r'(file_id\s*=\s*")[^"]*(")',
        lambda m: f'{m.group(1)}{file_id}{m.group(2)}',
        src
    )
    src = re.sub(
        r'(destination\s*=\s*")gg_stock_data_\d{8}\.tar\.gz(")',
        lambda m: f'{m.group(1)}{snap_name}{m.group(2)}',
        src
    )

    with open(DOWNLOAD_SCRIPT, 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'[OK] {DOWNLOAD_SCRIPT} 已更新（file_id={file_id[:12]}..., dest={snap_name}）')

    # ── 更新 data_sources.md ──────────────────────────────────────────────
    with open(DATA_SOURCES_MD, 'r', encoding='utf-8') as f:
        md = f.read()

    # 更新下載連結那一行（### 📦 下載連結 區塊）
    old_size_pattern = r'\(\d+ MB，解壓後約 \d+ MB\)'
    size_suffix = f'({size_str}，解壓後請自行確認)' if size_str else '(請確認大小)'

    md = re.sub(
        r'\[(\*\*gg_stock_data_\d{8}\.tar\.gz\*\*)\]\(https://drive\.google\.com/file/d/[^)]+\)(\s*\([^)]+\))?',
        f'[**{snap_name}**]({gdrive_url}) {size_suffix}',
        md
    )

    # 更新解壓命令裡的舊檔名
    md = re.sub(r'gg_stock_data_\d{8}\.tar\.gz', snap_name, md)

    # 更新「快照日期為 YYYY-MM-DD」
    md = re.sub(
        r'快照日期為\s+\*\*[\d-]+\*\*',
        f'快照日期為 **{date_display}**',
        md
    )

    with open(DATA_SOURCES_MD, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f'[OK] {DATA_SOURCES_MD} 已更新（連結、檔名、快照日期）')

    print()
    print('下一步：')
    print(f'  git add {DOWNLOAD_SCRIPT} {DATA_SOURCES_MD}')
    print(f'  git commit -m "snapshot: update to {today}"')
    print(f'  git push')


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if args and args[0] == '--update':
        if len(args) < 2:
            print('用法：make_snapshot.py --update <Google Drive file_id>')
            sys.exit(1)
        update(args[1])
    else:
        pack()


if __name__ == '__main__':
    main()
