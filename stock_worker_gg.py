# -*- coding: utf-8 -*-
import json
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

def fetch_kbars_df(api, contract, start_date, end_date, max_days=30):
    """分段下載 Shioaji KBars，避開單次日期區間 30 天限制。"""
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
        kbars = api.kbars(
            contract,
            chunk_start.strftime('%Y-%m-%d'),
            chunk_end.strftime('%Y-%m-%d')
        )
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
    status_msg = pyqtSignal(str)                                         # 狀態訊息
    
    def __init__(self, default_symbol='2330'):
        super().__init__()
        self.symbol = default_symbol
        self.pending_symbol = default_symbol
        self.symbol_changed_event = threading.Event()
        self.lock = threading.Lock()
        
        self.df_daily = pd.DataFrame()
        self.df_30m = pd.DataFrame()
        self.df_5m = pd.DataFrame()
        
        self.running = True
        self.need_update = False
        self.api = None
        self.current_contract = None
        
    def change_symbol(self, new_symbol):
        """主執行緒呼叫此方法以變更監控的股票"""
        with self.lock:
            self.pending_symbol = new_symbol
        self.symbol_changed_event.set()
        
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
                    
                # 節流更新機制：每 100ms 檢查是否有即時 Tick 更新，並向 GUI 發送最新資料
                if self.need_update:
                    self.need_update = False
                    with self.lock:
                        df_d = self.df_daily.copy()
                        df_30 = self.df_30m.copy()
                        df_5 = self.df_5m.copy()
                    self.update_data.emit(df_d, df_30, df_5)
                    
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
            # 30m 下載 20 天 (約 14 個交易日)
            start_30m = (today - datetime.timedelta(days=20)).strftime('%Y-%m-%d')
            # 5m 下載 7 天 (約 5 個交易日)
            start_5m = (today - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            # 4. 分段下載歷史 KBars。Shioaji 1.5.x 單次 kbars 區間不可超過 30 天。
            self.emit_api_usage("下載 K 線前")
            base_df = fetch_kbars_df(self.api, self.current_contract, start_daily, end_date)
            self.emit_api_usage("下載 K 線後")
            df_30m_base = base_df[base_df['date'] >= pd.to_datetime(start_30m)]
            df_5m_base = base_df[base_df['date'] >= pd.to_datetime(start_5m)]
            
            with self.lock:
                self.df_daily = resample_kbars(base_df, '1D')
                self.df_30m = resample_kbars(df_30m_base, '30min')
                self.df_5m = resample_kbars(df_5m_base, '5min')

            self.initial_data.emit(self.df_daily, self.df_30m, self.df_5m)
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

            with self.lock:
                self.df_daily = update_kbar_array_daily(self.df_daily, dt, tick.close, tick.volume)
                self.df_30m = update_kbar_array_30m(self.df_30m, dt, tick.close, tick.volume)
                self.df_5m = update_kbar_array_5m(self.df_5m, dt, tick.close, tick.volume)
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
