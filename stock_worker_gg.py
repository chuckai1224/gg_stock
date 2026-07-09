# -*- coding: utf-8 -*-
import json
import time
import datetime
import threading
import pandas as pd
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
import shioaji as sj

def load_sj_credentials():
    """載入 Shioaji 登入與 CA 憑證資料，優先使用 ~/.fut/ 設定，若無則降級讀取專案 trade/ 目錄"""
    fut_dir = Path.home() / ".fut"
    login_path = fut_dir / "login.json"
    ca_path = fut_dir / "ca.json"
    
    if not login_path.exists():
        login_path = Path("trade/login.txt")
    if not ca_path.exists():
        ca_path = Path("trade/ca.txt")
        
    if not login_path.exists() or not ca_path.exists():
        raise FileNotFoundError(
            f"找不到憑證檔案。請確保存在 ~/.fut/login.json 或專案資料夾下的 trade/login.txt"
        )
        
    with open(login_path, 'r', encoding='utf-8') as f:
        login_data = json.load(f)
    with open(ca_path, 'r', encoding='utf-8') as f:
        ca_data = json.load(f)
        
    ca_filepath = Path(str(ca_data["ca_path"]).strip().strip('"')).expanduser()
    if not ca_filepath.exists():
        raise FileNotFoundError(f"找不到 CA 憑證檔案: {ca_filepath}")
    ca_data["ca_path"] = str(ca_filepath)

    return login_data, ca_data

CACHE_DIR = Path("kbar_cache")

def _kbar_cache_path(symbol):
    return CACHE_DIR / f"{symbol}.parquet"

def _kbar_cache_path_legacy(symbol):
    return CACHE_DIR / f"{symbol}.pkl"

def load_kbar_cache(symbol):
    """讀取本地 1 分 K 快取；若不存在或損毀則回傳 None。

    優先讀 parquet；若只剩舊版 .pkl 則沿用一次(下次寫入即升級為 parquet)。
    """
    path = _kbar_cache_path(symbol)
    legacy = _kbar_cache_path_legacy(symbol)
    if path.exists():
        reader, src = pd.read_parquet, path
    elif legacy.exists():
        reader, src = pd.read_pickle, legacy
    else:
        return None
    try:
        df = reader(src)
        if 'date' not in df.columns or len(df) == 0:
            return None
        df['date'] = pd.to_datetime(df['date'])
        cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        return df[cols].sort_values('date').reset_index(drop=True)
    except Exception as e:
        print(f"讀取 K 線快取失敗 ({symbol}): {e}", flush=True)
        return None

def save_kbar_cache(symbol, df):
    """將 1 分 K base_df 寫入本地快取 (parquet)。"""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(_kbar_cache_path(symbol), index=False)
        # 升級成功後移除舊版 .pkl，避免殘留
        legacy = _kbar_cache_path_legacy(symbol)
        if legacy.exists():
            legacy.unlink()
    except Exception as e:
        print(f"寫入 K 線快取失敗 ({symbol}): {e}", flush=True)

def fetch_base_df_cached(api, contract, symbol, start_date, end_date, cache_max_days=400):
    """帶本地快取的 1 分 K 下載。

    讀取快取後只向 API 補抓「快取最後一天 ~ 今天」的缺口，合併去重後回存，
    大幅降低重複下載的 API 用量。回傳裁切到 [start_date, end_date] 的 base_df。
    """
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)

    cached = load_kbar_cache(symbol)
    if cached is not None and len(cached) > 0:
        last_date = cached['date'].max()
        # 從快取最後一天當天起重抓：覆蓋可能不完整的當日 K 棒並補上新交易日
        fetch_start = min(last_date.date(), end_ts.date())
        print(
            f"K 線快取命中 {symbol}: {cached['date'].min():%Y-%m-%d} ~ "
            f"{last_date:%Y-%m-%d} ({len(cached)} 筆)，補抓 "
            f"{fetch_start:%Y-%m-%d} ~ {end_ts:%Y-%m-%d}",
            flush=True
        )
        fresh = fetch_kbars_df(api, contract, fetch_start.strftime('%Y-%m-%d'), end_date)
        merged = pd.concat([cached, fresh], ignore_index=True)
    else:
        print(f"K 線快取未命中 {symbol}，完整下載 {start_date} ~ {end_date}", flush=True)
        merged = fetch_kbars_df(api, contract, start_date, end_date)

    if len(merged) == 0:
        return merged
    merged['date'] = pd.to_datetime(merged['date'])
    # 相同時間戳保留最新一筆（補抓資料覆蓋舊快取）
    merged = merged.drop_duplicates(subset=['date'], keep='last')
    merged = merged.sort_values('date').reset_index(drop=True)

    # 回存時保留較長歷史供下次沿用，但設上限避免無限增長
    cache_floor = end_ts - pd.Timedelta(days=cache_max_days)
    save_kbar_cache(symbol, merged[merged['date'] >= cache_floor])

    # 只回傳本次需要的區間
    window = (merged['date'] >= start_ts) & (merged['date'] < end_ts + pd.Timedelta(days=1))
    return merged[window].reset_index(drop=True)

TICK_CACHE_DIR = Path("tick_cache")
# 該日 tick 抓取時間需晚於此時刻，快取才視為完整 (13:30 收盤 + 緩衝)
TICK_SESSION_CLOSE = datetime.time(13, 35)

def _tick_cache_path(symbol):
    return TICK_CACHE_DIR / f"{symbol}.parquet"

def _tick_day_complete(day, fetched_at):
    """判斷該交易日的快取是否為收盤後抓的完整資料。

    fetched_at 為 NaT 代表舊版快取 (無抓取時間欄位)，視為完整以免整批重抓。
    """
    if pd.isna(fetched_at):
        return True
    return fetched_at >= pd.Timestamp.combine(day, TICK_SESSION_CLOSE)

def load_tick_cache(symbol):
    """讀取本地逐筆 tick VP 快取 (每交易日/價位彙總量)；無或損毀回傳 None。"""
    path = _tick_cache_path(symbol)
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        if not {'date', 'close', 'volume'}.issubset(df.columns) or len(df) == 0:
            return None
        df['date'] = pd.to_datetime(df['date'])
        if 'fetched_at' in df.columns:
            df['fetched_at'] = pd.to_datetime(df['fetched_at'])
        else:
            df['fetched_at'] = pd.NaT
        return df[['date', 'close', 'volume', 'fetched_at']]
    except Exception as e:
        print(f"讀取 tick 快取失敗 ({symbol}): {e}", flush=True)
        return None

def save_tick_cache(symbol, df):
    try:
        TICK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_parquet(_tick_cache_path(symbol), index=False)
    except Exception as e:
        print(f"寫入 tick 快取失敗 ({symbol}): {e}", flush=True)

def fetch_tick_vp_cached(api, contract, symbol, trading_days, timeout=30000, progress=None):
    """下載/快取歷史逐筆 tick，彙總成每(交易日, 價位)成交量，作為精確 VP 來源。

    只補抓未快取或快取不完整的交易日：今日永遠重抓；盤中抓過的歷史日
    (fetched_at 早於該日收盤) 也會重抓，避免部分資料永久留在快取。
    下載失敗的日子保留舊快取。回傳 columns=[date, close, volume]：
    date=交易日(midnight)、close=價位(round 2)、volume=該日該價位總量。
    """
    today = datetime.date.today()
    cached = load_tick_cache(symbol)
    if cached is not None and len(cached):
        fetched_at_by_day = cached.groupby(cached['date'].dt.date)['fetched_at'].max()
    else:
        fetched_at_by_day = pd.Series(dtype='datetime64[ns]')
    cached_days = set(fetched_at_by_day.index)

    target = sorted({d for d in trading_days})
    to_fetch = [
        d for d in target
        if d not in cached_days
        or d == today
        or not _tick_day_complete(d, fetched_at_by_day[d])
    ]

    print(f"tick VP {symbol}: 需補抓 {len(to_fetch)} 天 (快取已有 {len(cached_days)} 天)", flush=True)
    frames = []
    fetched_days = set()
    for i, d in enumerate(to_fetch, 1):
        try:
            ticks = api.ticks(contract, d.strftime('%Y-%m-%d'), timeout=timeout)
        except Exception as e:
            print(f"  tick 下載失敗 {d}: {e}", flush=True)
            continue
        if not ticks or len(ticks.ts) == 0:
            continue
        tdf = pd.DataFrame({
            'close': pd.to_numeric(pd.Series(ticks.close), errors='coerce').round(2),
            'volume': pd.to_numeric(pd.Series(ticks.volume), errors='coerce'),
        }).dropna()
        if len(tdf) == 0:
            continue
        tdf = tdf.groupby('close', as_index=False)['volume'].sum()
        tdf['date'] = pd.Timestamp(d)
        tdf['fetched_at'] = pd.Timestamp.now()
        frames.append(tdf[['date', 'close', 'volume', 'fetched_at']])
        fetched_days.add(d)
        if progress and (i % 20 == 0 or i == len(to_fetch)):
            progress(i, len(to_fetch))

    # 只汰換成功重抓的日子；下載失敗的日子沿用舊快取資料
    if cached is not None and len(cached):
        kept = cached[~cached['date'].dt.date.isin(fetched_days)]
        if len(kept):
            frames.insert(0, kept)

    if not frames:
        return pd.DataFrame(columns=['date', 'close', 'volume'])
    merged = pd.concat(frames, ignore_index=True)
    merged['date'] = pd.to_datetime(merged['date'])
    merged = merged.sort_values(['date', 'close']).reset_index(drop=True)
    # 回存只留本次請求區間內的日子 (比最舊交易日更早的不會再被請求)，避免快取無限增長
    cache_floor = pd.Timestamp(target[0])
    save_tick_cache(symbol, merged[merged['date'] >= cache_floor])
    return merged[['date', 'close', 'volume']]

def kbars_to_df(kbars):
    """將 Shioaji API kbars 轉為標準 DataFrame"""
    if not kbars or len(kbars.ts) == 0:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    df = pd.DataFrame({**kbars})
    df['date'] = pd.to_datetime(df['ts'])
    lower_columns = {str(col).lower(): col for col in df.columns}
    required = ['open', 'high', 'low', 'close', 'volume']
    missing = [col for col in required if col not in lower_columns]
    if missing:
        print(f"KBars 欄位缺少 {missing}，實際欄位: {list(df.columns)}", flush=True)
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

    df = df[['date'] + [lower_columns[col] for col in required]]
    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

def resample_kbars(df, rule):
    """將 Shioaji 1 分 K 轉為指定週期 K 線。"""
    if len(df) == 0:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

    # Shioaji 會回傳零成交量的補價列；這些列不是實際 K 棒成交，會扭曲分K的 open/close。
    work = df[df['volume'].astype(float) > 0].copy()
    if len(work) == 0:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

    work = work.set_index('date').sort_index()
    agg = work.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    })
    agg = agg.dropna(subset=['open', 'high', 'low', 'close']).reset_index()
    return agg[['date', 'open', 'high', 'low', 'close', 'volume']]

def fetch_kbars_df(api, contract, start_date, end_date, max_days=30,
                   timeout=30000, retries=3):
    """分段下載 Shioaji KBars，避開單次日期區間 30 天限制。

    timeout: 單次 api.kbars 逾時毫秒數 (預設 30 秒，避開預設 5 秒過短)。
    retries: 逾時或連線錯誤時的重試次數。
    """
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    chunks = []

    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + datetime.timedelta(days=max_days - 1), end)
        print(
            f"下載 K 線區間: {chunk_start:%Y-%m-%d} ~ {chunk_end:%Y-%m-%d}",
            flush=True
        )
        kbars = None
        for attempt in range(1, retries + 1):
            try:
                kbars = api.kbars(
                    contract,
                    chunk_start.strftime('%Y-%m-%d'),
                    chunk_end.strftime('%Y-%m-%d'),
                    timeout=timeout,
                )
                break
            except sj.ShioajiTimeoutError as exc:
                if attempt >= retries:
                    raise
                wait = 2 * attempt
                print(
                    f"  K 線下載逾時 (第 {attempt}/{retries} 次)，{wait} 秒後重試… ({exc})",
                    flush=True
                )
                time.sleep(wait)
        df = kbars_to_df(kbars)
        if len(df) > 0:
            chunks.append(df)
        chunk_start = chunk_end + datetime.timedelta(days=1)

    if not chunks:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])

    merged = pd.concat(chunks, ignore_index=True)
    merged = merged.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
    return merged[['date', 'open', 'high', 'low', 'close', 'volume']]

def format_bytes(value):
    """將 byte 數格式化為易讀單位。"""
    value = float(value or 0)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if value < 1024 or unit == 'GB':
            return f"{value:.2f} {unit}"
        value /= 1024

def update_kbar_array_5m(df, dt, price, vol):
    """增量更新 5分K 棒"""
    if dt.time() >= datetime.time(13, 30, 0):
        dt = dt.replace(hour=13, minute=29, second=59, microsecond=0)
    m = dt.minute
    t_start = dt.replace(minute=(m // 5) * 5, second=0, microsecond=0)
    
    if len(df) == 0:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        return pd.concat([df, new_row], ignore_index=True)
        
    last_idx = df.index[-1]
    last_date = df.loc[last_idx, 'date']
    
    if t_start == last_date:
        df.loc[last_idx, 'high'] = max(df.loc[last_idx, 'high'], price)
        df.loc[last_idx, 'low'] = min(df.loc[last_idx, 'low'], price)
        df.loc[last_idx, 'close'] = price
        df.loc[last_idx, 'volume'] += vol
    elif t_start > last_date:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    return df

def update_kbar_array_1m(df, dt, price, vol):
    """增量更新 1分K 棒 (供 Volume Profile 分箱用)"""
    if dt.time() >= datetime.time(13, 30, 0):
        dt = dt.replace(hour=13, minute=29, second=59, microsecond=0)
    t_start = dt.replace(second=0, microsecond=0)

    if len(df) == 0:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        return pd.concat([df, new_row], ignore_index=True)

    last_idx = df.index[-1]
    last_date = df.loc[last_idx, 'date']

    if t_start == last_date:
        df.loc[last_idx, 'high'] = max(df.loc[last_idx, 'high'], price)
        df.loc[last_idx, 'low'] = min(df.loc[last_idx, 'low'], price)
        df.loc[last_idx, 'close'] = price
        df.loc[last_idx, 'volume'] += vol
    elif t_start > last_date:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    return df

def update_kbar_array_30m(df, dt, price, vol):
    """增量更新 30分K 棒"""
    if dt.time() >= datetime.time(13, 30, 0):
        dt = dt.replace(hour=13, minute=29, second=59, microsecond=0)
    m = dt.minute
    t_start = dt.replace(minute=(m // 30) * 30, second=0, microsecond=0)
    
    if len(df) == 0:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        return pd.concat([df, new_row], ignore_index=True)
        
    last_idx = df.index[-1]
    last_date = df.loc[last_idx, 'date']
    
    if t_start == last_date:
        df.loc[last_idx, 'high'] = max(df.loc[last_idx, 'high'], price)
        df.loc[last_idx, 'low'] = min(df.loc[last_idx, 'low'], price)
        df.loc[last_idx, 'close'] = price
        df.loc[last_idx, 'volume'] += vol
    elif t_start > last_date:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    return df

def update_kbar_array_daily(df, dt, price, vol):
    """增量更新 日K 棒"""
    t_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if len(df) == 0:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        return pd.concat([df, new_row], ignore_index=True)
        
    last_idx = df.index[-1]
    last_date = df.loc[last_idx, 'date'].date()
    
    if t_start.date() == last_date:
        df.loc[last_idx, 'high'] = max(df.loc[last_idx, 'high'], price)
        df.loc[last_idx, 'low'] = min(df.loc[last_idx, 'low'], price)
        df.loc[last_idx, 'close'] = price
        df.loc[last_idx, 'volume'] += vol
    elif t_start.date() > last_date:
        new_row = pd.DataFrame([{
            'date': t_start, 'open': price, 'high': price, 'low': price, 'close': price, 'volume': vol
        }])
        df = pd.concat([df, new_row], ignore_index=True)
    return df

class StockWorker(QThread):
    # PyQt5 訊號定義
    initial_data = pyqtSignal(pd.DataFrame, pd.DataFrame, pd.DataFrame)  # (df_daily, df_30m, df_5m)
    update_data = pyqtSignal(pd.DataFrame, pd.DataFrame, pd.DataFrame)   # (df_daily, df_30m, df_5m)
    profile_data = pyqtSignal(pd.DataFrame)                              # 1 分 K (30分 Volume Profile 分箱來源，近 7 天)
    daily_profile_data = pyqtSignal(pd.DataFrame)                        # 1 分 K (日K Volume Profile 分箱來源，全區間 ~180 天)
    tick_info = pyqtSignal(dict)                                         # 最新成交單 (顯示於股票名稱旁)
    status_msg = pyqtSignal(str)                                         # 狀態訊息
    
    def __init__(self, default_symbol='2330'):
        super().__init__()
        self.symbol = default_symbol
        self.pending_symbol = default_symbol
        self.symbol_changed_event = threading.Event()
        self.tick_vp_event = threading.Event()
        self.tick_vp_thread = None
        self.lock = threading.Lock()
        
        self.df_daily = pd.DataFrame()
        self.df_30m = pd.DataFrame()
        self.df_5m = pd.DataFrame()
        self.df_1m = pd.DataFrame()
        self.latest_tick = None

        self.running = True
        self.need_update = False
        self.api = None
        self.current_contract = None
        
    def change_symbol(self, new_symbol):
        """主執行緒呼叫此方法以變更監控的股票"""
        with self.lock:
            self.pending_symbol = new_symbol
        self.symbol_changed_event.set()

    def request_tick_vp(self):
        """由 GUI 按 P 觸發：在背景執行緒補抓歷史 tick VP。"""
        self.tick_vp_event.set()
        
    def run(self):
        try:
            self.status_msg.emit("正在登入永豐金證券 Shioaji API...")
            login_data, ca_data = load_sj_credentials()
            
            self.api = sj.Shioaji(simulation=False)
            self.api.login(**login_data)
            self.api.activate_ca(
                ca_path=ca_data['ca_path'],
                ca_passwd=ca_data['ca_passwd'],
                person_id=ca_data['person_id']
            )
            self.register_tick_callback()
            self.status_msg.emit("登入成功，系統就緒。")
            self.emit_api_usage("登入後")
            
            # 定時更新與切換檢查迴圈
            while self.running:
                # 檢查是否有股票代號切換請求
                if self.symbol_changed_event.is_set():
                    self.symbol_changed_event.clear()
                    with self.lock:
                        self.symbol = self.pending_symbol
                    self.process_symbol_change()

                if self.tick_vp_event.is_set():
                    self.tick_vp_event.clear()
                    self.start_tick_vp_download()
                    
                # 節流更新機制：每 100ms 檢查是否有即時 Tick 更新，並向 GUI 發送最新資料
                if self.need_update:
                    self.need_update = False
                    with self.lock:
                        df_d = self.df_daily.copy()
                        df_30 = self.df_30m.copy()
                        df_5 = self.df_5m.copy()
                        df_1 = self.df_1m.copy()
                        tick_snap = dict(self.latest_tick) if self.latest_tick else None
                    self.update_data.emit(df_d, df_30, df_5)
                    self.profile_data.emit(df_1)
                    if tick_snap is not None:
                        self.tick_info.emit(tick_snap)
                    
                self.msleep(100)
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.status_msg.emit(f"背景 Worker 發生錯誤: {e}")
            
    def process_symbol_change(self):
        """在背景執行緒中處理股票切換、下載歷史 K 線與重新訂閱即時行情"""
        try:
            target_symbol = self.symbol
            self.status_msg.emit(f"正在查詢股票代號: {target_symbol}...")
            
            # 1. 取消先前的訂閱
            if self.current_contract:
                try:
                    self.api.quote.unsubscribe(self.current_contract, quote_type=sj.QuoteType.Tick)
                except Exception as e:
                    print(f"取消訂閱失敗: {e}")
                    
            # 2. 獲取新的合約 (股票)
            self.current_contract = self.api.Contracts.Stocks[target_symbol]
            if not self.current_contract:
                self.status_msg.emit(f"錯誤: 找不到股票代號 {target_symbol}")
                return
                
            stock_name = self.current_contract.name
            self.status_msg.emit(f"已選定股票: {target_symbol} {stock_name}，正在下載歷史 K 線...")
            symbol_usage_start = self.emit_api_usage(f"{target_symbol} 查詢前")
            
            # 3. 計算歷史資料時間區間
            today = datetime.date.today()
            # 日K 下載 180 天 (約 120 個交易日)
            start_daily = (today - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
            # 30m 取 30 天 (約 20 個交易日 ~180 根，確保畫面 120 根足夠；由 base_df 過濾，零額外 API)
            start_30m = (today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            # 5m 下載 7 天 (約 5 個交易日)
            start_5m = (today - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            # 4. 分段下載歷史 KBars（帶本地快取，僅補抓近期缺口）。
            #    Shioaji 1.5.x 單次 kbars 區間不可超過 30 天，由 fetch_kbars_df 分段處理。
            self.emit_api_usage("下載 K 線前")
            base_df = fetch_base_df_cached(
                self.api, self.current_contract, target_symbol, start_daily, end_date
            )
            self.emit_api_usage("下載 K 線後")
            df_30m_base = base_df[base_df['date'] >= pd.to_datetime(start_30m)]
            df_5m_base = base_df[base_df['date'] >= pd.to_datetime(start_5m)]
            
            with self.lock:
                self.df_daily = resample_kbars(base_df, '1D')
                self.df_30m = resample_kbars(df_30m_base, '30min')
                self.df_5m = resample_kbars(df_5m_base, '5min')
                # df_5m_base 本身即為近 7 天的 1 分 K，直接留作 Volume Profile 分箱來源
                self.df_1m = df_5m_base[['date', 'open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)

            self.initial_data.emit(self.df_daily, self.df_30m, self.df_5m)
            self.profile_data.emit(self.df_1m.copy())
            # 先用全區間 1 分 K 收盤+量送一份「快速 VP」，畫面立即有 VP 可看
            self.daily_profile_data.emit(base_df.copy())
            self.status_msg.emit(f"成功載入 {target_symbol} {stock_name} 的歷史 K 線。正在訂閱即時報價...")

            # 5. 訂閱即時 Tick
            self.api.quote.subscribe(
                self.current_contract,
                quote_type=sj.QuoteType.Tick,
                version=sj.QuoteVersion.v1
            )
            symbol_usage_end = self.emit_api_usage(f"{target_symbol} 訂閱後")
            if symbol_usage_start is not None and symbol_usage_end is not None:
                symbol_used = max(0, symbol_usage_end - symbol_usage_start)
                msg = f"單檔 {target_symbol} API 用量: {format_bytes(symbol_used)} ({symbol_used} bytes)"
                print(msg, flush=True)
                self.status_msg.emit(msg)
            self.status_msg.emit(f"監控中: {target_symbol} {stock_name} | 即時行情已訂閱。")

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.status_msg.emit(f"載入股票 {target_symbol} 失敗: {e}")

    def start_tick_vp_download(self):
        """在獨立執行緒補抓 tick VP，避免下載期間 worker 迴圈停擺、圖表凍結。"""
        if self.tick_vp_thread is not None and self.tick_vp_thread.is_alive():
            self.status_msg.emit("tick VP 下載進行中，請稍候。")
            return
        self.tick_vp_thread = threading.Thread(
            target=self.process_tick_vp_request, daemon=True
        )
        self.tick_vp_thread.start()

    def process_tick_vp_request(self):
        """按 P 後才補抓歷史 tick VP，避免換股時自動消耗大量 API。

        由 start_tick_vp_download 於獨立執行緒執行。
        """
        try:
            if not self.api or not self.current_contract:
                self.status_msg.emit("尚未選定股票，無法下載 tick VP。")
                return

            with self.lock:
                target_symbol = self.symbol
                df_daily = self.df_daily.copy()

            if len(df_daily) == 0:
                self.status_msg.emit("尚無日K資料，無法下載 tick VP。")
                return

            tick_usage_start = self.emit_api_usage("tick VP 前")
            trading_days = sorted(pd.to_datetime(df_daily['date']).dt.date.unique())

            def _tick_progress(i, total):
                self.status_msg.emit(f"下載 {target_symbol} 歷史 tick VP... {i}/{total} 天")

            self.status_msg.emit(f"正在下載 {target_symbol} 歷史 tick 建立精確 VP ({len(trading_days)} 天)...")
            tick_vp = fetch_tick_vp_cached(
                self.api, self.current_contract, target_symbol, trading_days,
                progress=_tick_progress)
            tick_usage_end = self.emit_api_usage("tick VP 後")
            if tick_usage_start is not None and tick_usage_end is not None:
                used = max(0, tick_usage_end - tick_usage_start)
                self.status_msg.emit(f"tick VP 消耗 API: {format_bytes(used)}")
            # 下載期間使用者可能已換股，只在仍是同一檔時才覆蓋 VP
            if len(tick_vp) > 0 and self.symbol == target_symbol:
                self.daily_profile_data.emit(tick_vp)
                self.status_msg.emit(f"{target_symbol} 精確 tick VP 完成 ({len(tick_vp)} 筆價量)。")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.status_msg.emit(f"tick VP 下載失敗 (沿用快速版): {e}")

    def emit_api_usage(self, label):
        """印出 Shioaji API 流量額度資訊。"""
        if not self.api:
            return None

        try:
            usage = self.api.usage()
            used = getattr(usage, 'bytes', 0)
            limit = getattr(usage, 'limit_bytes', 0)
            remaining = getattr(usage, 'remaining_bytes', 0)
            connections = getattr(usage, 'connections', 0)
            percent = (remaining / limit * 100) if limit else 0
            msg = (
                f"API 用量({label}): 已用 {format_bytes(used)} / "
                f"上限 {format_bytes(limit)}，剩餘 {format_bytes(remaining)} "
                f"({percent:.1f}%)，連線數 {connections}"
            )
            print(msg, flush=True)
            self.status_msg.emit(msg)
            return used
        except Exception as e:
            print(f"查詢 API 用量失敗({label}): {e}", flush=True)
            return None

    def register_tick_callback(self):
        """註冊股票 Tick callback；切換股票時只變更 current_contract 與 symbol。"""
        @self.api.on_tick_stk_v1()
        def tick_callback(exchange, tick):
            with self.lock:
                target_symbol = self.symbol

            if tick.code != target_symbol:
                return

            dt = tick.datetime
            if not (datetime.time(9, 0, 0) <= dt.time() < datetime.time(13, 35, 0)):
                return

            # Shioaji 的 tick.close 為 Decimal，直接寫入 float64 K 棒欄位會拋
            # TypeError 並被 Shioaji 吞掉，導致 K 棒不會即時更新。先轉 float。
            price = float(tick.close)
            vol = float(tick.volume)

            # 最新成交單資訊 (顯示於股票名稱旁)。pct_chg 原始值單位不一致，
            # 這裡用 price_chg 與前收自行計算漲跌幅較可靠。
            chg = float(getattr(tick, 'price_chg', 0) or 0)
            prev_close = price - chg
            pct = (chg / prev_close * 100) if prev_close else 0.0
            tick_snapshot = {
                'time': dt.strftime('%H:%M:%S'),
                'price': price,
                'chg': chg,
                'pct': pct,
                'volume': int(tick.volume),
                'total_volume': int(getattr(tick, 'total_volume', 0) or 0),
                'tick_type': int(getattr(tick, 'tick_type', 0) or 0),
            }

            with self.lock:
                self.df_daily = update_kbar_array_daily(self.df_daily, dt, price, vol)
                self.df_30m = update_kbar_array_30m(self.df_30m, dt, price, vol)
                self.df_5m = update_kbar_array_5m(self.df_5m, dt, price, vol)
                self.df_1m = update_kbar_array_1m(self.df_1m, dt, price, vol)
                self.latest_tick = tick_snapshot
                self.need_update = True
            
    def stop(self):
        """停止背景執行緒與安全登出"""
        self.running = False
        if self.api:
            try:
                if self.current_contract:
                    self.api.quote.unsubscribe(self.current_contract, quote_type=sj.QuoteType.Tick)
                self.api.logout()
            except Exception as e:
                print(f"API 登出失敗: {e}")
