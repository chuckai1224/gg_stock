# -*- coding: utf-8 -*-
import datetime
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# 設定 pyqtgraph 深色背景主題
pg.setConfigOption('background', '#151515')
pg.setConfigOption('foreground', '#dcdcdc')


def _filter_peaks_with_edges(peaks, volume_data):
    """移植自 fut2026 vol_profile.filter_peaks_with_edges：
    去掉相鄰兩側量能更大的峰，只留下相對突出的大量點。"""
    if len(peaks) <= 1:
        return peaks
    peak_volumes = volume_data[peaks]
    filtered = []
    for idx in range(len(peaks)):
        left_ok = True if idx == 0 else peak_volumes[idx] > peak_volumes[idx - 1]
        right_ok = True if idx == len(peaks) - 1 else peak_volumes[idx] > peak_volumes[idx + 1]
        if left_ok and right_ok:
            filtered.append(peaks[idx])
    return np.asarray(filtered, dtype=peaks.dtype)


def get_volume_peak_markers(df):
    """回傳「大量點」的 (x 索引, y 價位)。

    移植自 fut2026 vol_profile.get_volume_peaks_dxdy：找成交量的局部高峰
    (find_peaks) 且高於均量者，點畫在該棒 open 價。
    """
    empty = (np.array([]), np.array([]))
    if df is None or len(df) < 3:
        return empty
    volume = df['volume'].astype(float).to_numpy()
    if volume.size == 0 or not np.any(volume > 0):
        return empty
    avg_vol = volume.mean()
    peaks, _ = find_peaks(volume, height=avg_vol)
    peaks = _filter_peaks_with_edges(peaks, volume)
    if peaks.size == 0:
        return empty
    opens = df['open'].astype(float).to_numpy()
    return peaks.astype(float), opens[peaks]

class TimeIndexAxis(pg.AxisItem):
    """自定義 X 軸，將 KBar 索引值對齊轉換為美觀的時間/日期標籤"""
    def __init__(self, orientation="bottom", is_daily=False):
        super().__init__(orientation=orientation)
        self.is_daily = is_daily
        self._time_array = None
        self._label_cache = {}

    def set_time_array(self, time_array):
        self._time_array = time_array
        self._label_cache = {}
        self.update()

    def tickStrings(self, values, scale, spacing):
        if self._time_array is None or len(self._time_array) == 0:
            return ["" for _ in values]
            
        n = len(self._time_array)
        labels = []
        for v in values:
            idx = int(round(v))
            if idx in self._label_cache:
                labels.append(self._label_cache[idx])
                continue
                
            if idx < 0 or idx >= n:
                label = ""
            else:
                val = self._time_array[idx]
                # 確保為 pandas Timestamp 或 datetime
                if not hasattr(val, 'strftime'):
                    val = pd.to_datetime(val)
                    
                if self.is_daily:
                    # 日K 顯示 月/日 (跨年顯示 年/月/日)
                    if idx == 0 or val.year != pd.to_datetime(self._time_array[idx - 1]).year:
                        label = val.strftime('%Y/%m/%d')
                    else:
                        label = val.strftime('%m/%d')
                else:
                    # 分K 跨天時的第一個 K 棒顯示 日期+時間，否則只顯示 時間
                    if idx == 0 or val.date() != pd.to_datetime(self._time_array[idx - 1]).date():
                        label = val.strftime('%m/%d %H:%M')
                    else:
                        label = val.strftime('%H:%M')
                        
            labels.append(label)
            self._label_cache[idx] = label
        return labels

class CandlestickLayer:
    """K 線圖層，沿用 fut2026 的 BarGraphItem + shadow pairs 畫法。"""
    def __init__(self, body_width=0.55):
        self.data = pd.DataFrame()
        self.body_width = body_width
        self.min_body = 0.01
        self.up_color = pg.mkColor('#ff3333')
        self.down_color = pg.mkColor('#00b050')
        self.up_bars = pg.BarGraphItem(x=[], height=[], width=body_width, y0=[], brush=self.up_color, pen=self.up_color)
        self.down_bars = pg.BarGraphItem(x=[], height=[], width=body_width, y0=[], brush=self.down_color, pen=self.down_color)
        self.shadows = pg.PlotDataItem(connect="pairs")

    def add_to_plot(self, plot):
        plot.addItem(self.shadows)
        plot.addItem(self.up_bars)
        plot.addItem(self.down_bars)

    def set_data(self, data):
        self.data = data.reset_index(drop=True) if len(data) else data
        if len(self.data) == 0:
            self.up_bars.setOpts(x=[], height=[], y0=[])
            self.down_bars.setOpts(x=[], height=[], y0=[])
            self.shadows.setData([], [])
            return

        x = np.arange(len(self.data))
        opens = self.data['open'].astype(float).to_numpy()
        highs = self.data['high'].astype(float).to_numpy()
        lows = self.data['low'].astype(float).to_numpy()
        closes = self.data['close'].astype(float).to_numpy()

        up = closes >= opens
        down = ~up
        body_low = np.minimum(opens, closes)
        body_height = np.maximum(np.abs(closes - opens), self.min_body)

        shadow_x = np.repeat(x, 2)
        shadow_y = np.column_stack((lows, highs)).ravel()
        shadow_pen = pg.mkPen(color=(180, 180, 180, 180), width=1)
        shadow_pen.setCosmetic(True)
        self.shadows.setData(x=shadow_x, y=shadow_y, pen=shadow_pen, connect="pairs")

        self.up_bars.setOpts(
            x=x[up],
            height=body_height[up],
            width=self.body_width,
            y0=body_low[up],
            brush=self.up_color,
            pen=self.up_color,
        )
        self.down_bars.setOpts(
            x=x[down],
            height=body_height[down],
            width=self.body_width,
            y0=body_low[down],
            brush=self.down_color,
            pen=self.down_color,
        )

class VolumeBarItem(pg.GraphicsObject):
    """自定義成交量直條圖項目"""
    def __init__(self, data=None):
        super().__init__()
        self.data = data
        self.picture = None

    def set_data(self, data):
        self.data = data
        self.picture = None
        # boundingRect 會隨資料改變，必須通知場景重算幾何，否則 ViewBox
        # 會沿用舊的快取邊界 (換股票後成交量 Y 軸不會更新)。
        self.prepareGeometryChange()
        self.update()

    def paint(self, p, *args):
        if self.picture is None:
            self.generate_picture()
        p.drawPicture(0, 0, self.picture)

    def generate_picture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        
        if self.data is None or len(self.data) == 0:
            p.end()
            return
            
        up_brush = pg.mkBrush(color='#ff333388')
        up_pen = pg.mkPen(color='#ff3333', width=1)
        down_brush = pg.mkBrush(color='#00b05088')
        down_pen = pg.mkPen(color='#00b050', width=1)
        
        w = 0.6
        
        for x, (_, row) in enumerate(self.data.iterrows()):
            open_p = float(row['open'])
            close_p = float(row['close'])
            vol = float(row['volume'])
            
            if close_p >= open_p:
                p.setPen(up_pen)
                p.setBrush(up_brush)
            else:
                p.setPen(down_pen)
                p.setBrush(down_brush)
                
            p.drawRect(QtCore.QRectF(x - w/2, 0, w, vol))
        p.end()

    def boundingRect(self):
        if self.data is None or len(self.data) == 0:
            return QtCore.QRectF(0, 0, 0, 0)
        vols = self.data['volume'].astype(float)
        return QtCore.QRectF(-1, 0, len(self.data) + 2, max(1.0, vols.max()))

def tail_kbars(df, count=60):
    """取最後 count 根 KBar，並重設索引供繪圖座標使用。"""
    if len(df) == 0:
        return df
    return df.tail(count).reset_index(drop=True)

class StockPlotWindow(QtWidgets.QMainWindow):
    # 定義查詢股票事件訊號 (將代號傳給背景 Worker)
    query_symbol_signal = QtCore.pyqtSignal(str)
    
    def __init__(self, default_symbol='2330'):
        super().__init__()
        self.default_symbol = default_symbol
        self.setWindowTitle("股票即時雙週期看盤系統 (日K / 30分K)")
        self.resize(1500, 900)
        self.inspect_enabled = False
        self.inspect_targets = []
        self.ma_visible = True
        self.force_visible = False
        self.profile_visible = False
        self.bigvol_visible = True           # 大量點 (成交量高峰黃點)
        self.df_1m_source = pd.DataFrame()       # 30分 VP 分箱來源 (1 分 K，近 7 天)
        self.df_daily_1m_source = pd.DataFrame() # 日K VP 分箱來源 (1 分 K，全區間)
        self._last_plot_30m = None               # 最近一次 30 分視窗，供 VP 重繪錨定
        self._last_df_daily = None               # 最近一次日K，供日K VP 重繪錨定
        self._vp_ref_30m = None                  # 30分藍色 VP 的分箱範圍/量能基準 (橘色沿用)
        self._vp_ref_daily = None                # 日K 藍色 VP 的分箱範圍/量能基準 (橘色沿用)
        self.shortcut_help = None                # 快捷鍵說明疊層 (按 H 切換)

        # 建立主 Layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 頂部控制與輸入欄
        self.setup_control_bar()
        
        # 繪圖佈局視窗
        self.win = pg.GraphicsLayoutWidget()
        self.main_layout.addWidget(self.win)
        
        # 狀態列
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系統登入與初始化中...")
        
        # 初始化圖表
        self.setup_plots()
        
    def setup_control_bar(self):
        self.control_layout = QtWidgets.QHBoxLayout()
        
        # 代號輸入標籤與框
        self.input_label = QtWidgets.QLabel("股票代號:")
        self.input_label.setFont(QtGui.QFont("Microsoft JhengHei", 10, QtGui.QFont.Bold))
        self.input_label.setStyleSheet("color: #ffffff;")
        
        self.symbol_input = QtWidgets.QLineEdit()
        self.symbol_input.setText(self.default_symbol)
        self.symbol_input.setFixedWidth(100)
        self.symbol_input.setFont(QtGui.QFont("Consolas", 11, QtGui.QFont.Bold))
        self.symbol_input.setStyleSheet(
            "background-color: #2b2b2b; color: #00ff00; border: 1px solid #555555; padding: 3px; border-radius: 3px;"
        )
        # 綁定 Enter 鍵直接觸發查詢
        self.symbol_input.returnPressed.connect(self.on_query_click)
        self.symbol_input.installEventFilter(self)
        
        # 查詢按鈕
        self.query_button = QtWidgets.QPushButton("查詢股票")
        self.query_button.setFont(QtGui.QFont("Microsoft JhengHei", 10, QtGui.QFont.Bold))
        self.query_button.setStyleSheet(
            "background-color: #007acc; color: white; border: none; padding: 5px 15px; border-radius: 3px;"
        )
        self.query_button.clicked.connect(self.on_query_click)
        
        # 股票名稱資訊標籤
        self.info_label = QtWidgets.QLabel("載入中...")
        self.info_label.setFont(QtGui.QFont("Microsoft JhengHei", 12, QtGui.QFont.Bold))
        self.info_label.setStyleSheet("color: #00e6ff; margin-left: 20px;")

        # 最新成交單標籤 (顯示於股票名稱旁)
        self.tick_label = QtWidgets.QLabel("")
        self.tick_label.setFont(QtGui.QFont("Consolas", 11, QtGui.QFont.Bold))
        self.tick_label.setStyleSheet("color: #dddddd; margin-left: 16px;")

        self.control_layout.addWidget(self.input_label)
        self.control_layout.addWidget(self.symbol_input)
        self.control_layout.addWidget(self.query_button)
        self.control_layout.addWidget(self.info_label)
        self.control_layout.addWidget(self.tick_label)
        self.control_layout.addStretch()
        
        self.main_layout.addLayout(self.control_layout)
        
    def setup_plots(self):
        # 建立時間 X 軸元件
        self.axis_daily = TimeIndexAxis(orientation='bottom', is_daily=True)
        self.axis_daily_vol = TimeIndexAxis(orientation='bottom', is_daily=True)
        self.axis_30m = TimeIndexAxis(orientation='bottom', is_daily=False)
        self.axis_30m_vol = TimeIndexAxis(orientation='bottom', is_daily=False)
        
        # 1. 日K 主圖與成交量副圖 (佔據上半部)
        self.plot_daily = self.win.addPlot(row=0, col=0, axisItems={'bottom': self.axis_daily}, title="日 K線走勢")
        self.plot_daily_vol = self.win.addPlot(row=1, col=0, axisItems={'bottom': self.axis_daily_vol})
        
        # 2. 30分K 主圖與成交量副圖 (佔據下半部)
        self.plot_30m = self.win.addPlot(row=2, col=0, axisItems={'bottom': self.axis_30m}, title="30分 K線走勢")
        self.plot_30m_vol = self.win.addPlot(row=3, col=0, axisItems={'bottom': self.axis_30m_vol})
        
        # 設定行列佈局高度比例
        self.win.ci.layout.setRowStretchFactor(0, 12)
        self.win.ci.layout.setRowStretchFactor(1, 4)
        self.win.ci.layout.setRowStretchFactor(2, 9)
        self.win.ci.layout.setRowStretchFactor(3, 3)
        self.win.ci.layout.setVerticalSpacing(0)
        self.win.ci.layout.setColumnStretchFactor(0, 1)
        
        # 基本圖表外觀設定與 X 軸同歩縮放連動
        plots_list = [
            self.plot_daily, self.plot_daily_vol,
            self.plot_30m, self.plot_30m_vol,
        ]
        for p in plots_list:
            p.showGrid(x=False, y=False)
            p.setLabel('left', '價格' if p in [self.plot_daily, self.plot_30m] else '成交量')
            p.getViewBox().setMouseEnabled(x=True, y=True)
            p.setContentsMargins(0, 0, 0, 0)
            
        # 軸連動設定
        self.plot_daily.setXLink(self.plot_daily_vol)
        self.plot_30m.setXLink(self.plot_30m_vol)
        self.plot_daily.hideAxis('bottom')
        self.plot_30m.hideAxis('bottom')
        
        # 繪圖圖層 Item 加入
        self.kline_daily = CandlestickLayer()
        self.vol_daily = VolumeBarItem()
        self.kline_daily.add_to_plot(self.plot_daily)
        self.plot_daily_vol.addItem(self.vol_daily)
        
        self.kline_30m = CandlestickLayer()
        self.vol_30m = VolumeBarItem()
        self.kline_30m.add_to_plot(self.plot_30m)
        self.plot_30m_vol.addItem(self.vol_30m)
        
        # 繪製移動平均線
        # 日K: MA5, MA20, MA60
        self.ma5_daily = pg.PlotCurveItem(pen=pg.mkPen('#e1b12c', width=1.5))
        self.ma20_daily = pg.PlotCurveItem(pen=pg.mkPen('#44bd32', width=1.5))
        self.ma60_daily = pg.PlotCurveItem(pen=pg.mkPen('#00a8ff', width=1.5))
        self.plot_daily.addItem(self.ma5_daily)
        self.plot_daily.addItem(self.ma20_daily)
        self.plot_daily.addItem(self.ma60_daily)
        
        # 30m: MA5, MA20
        self.ma5_30m = pg.PlotCurveItem(pen=pg.mkPen('#e1b12c', width=1.5))
        self.ma20_30m = pg.PlotCurveItem(pen=pg.mkPen('#44bd32', width=1.5))
        self.plot_30m.addItem(self.ma5_30m)
        self.plot_30m.addItem(self.ma20_30m)

        self.force_line_30m = pg.PlotCurveItem(pen=pg.mkPen(color=(200, 0, 200, 180), width=1.5, style=QtCore.Qt.DashLine))
        # Volume Profile 以水平量柱呈現 (取代原本連線，較符合 VP 樣式)
        self.profile_vp_30m = pg.BarGraphItem(
            x0=[], y=[], width=[], height=[],
            brush=pg.mkBrush(120, 160, 210, 90), pen=pg.mkPen(None))
        self.profile_vp_daily = pg.BarGraphItem(
            x0=[], y=[], width=[], height=[],
            brush=pg.mkBrush(120, 160, 210, 90), pen=pg.mkPen(None))
        # 游標 K 棒 VP：檢視模式(I)下滑鼠所在單一 K 棒的 VP，畫於 K 線右側 (橘色)
        def _mk_hover_vp():
            return pg.BarGraphItem(x0=[], y=[], width=[], height=[],
                                   brush=pg.mkBrush(255, 150, 0, 205),
                                   pen=pg.mkPen(255, 120, 0, 230, width=1))
        self.hover_vp_30m = _mk_hover_vp()
        self.hover_vp_daily = _mk_hover_vp()
        # VP 成交量數字標註 (藍色標 POC 量、橘色標游標 K 棒量)
        def _mk_vp_label(color):
            t = pg.TextItem(text="", color=color, anchor=(0, 0.5))
            t.setVisible(False)
            return t
        self.vp_label_30m = _mk_vp_label((150, 195, 240))
        self.vp_label_daily = _mk_vp_label((150, 195, 240))
        self.hover_label_30m = _mk_vp_label((255, 185, 90))
        self.hover_label_daily = _mk_vp_label((255, 185, 90))
        self.force_line_30m.setVisible(self.force_visible)
        self.profile_vp_30m.setVisible(self.profile_visible)
        self.profile_vp_daily.setVisible(self.profile_visible)
        self.hover_vp_30m.setVisible(False)
        self.hover_vp_daily.setVisible(False)
        self.plot_30m.addItem(self.force_line_30m)
        self.plot_30m.addItem(self.profile_vp_30m)
        self.plot_daily.addItem(self.profile_vp_daily)
        self.plot_30m.addItem(self.hover_vp_30m)
        self.plot_daily.addItem(self.hover_vp_daily)
        for lb, pl in ((self.vp_label_30m, self.plot_30m), (self.vp_label_daily, self.plot_daily),
                       (self.hover_label_30m, self.plot_30m), (self.hover_label_daily, self.plot_daily)):
            pl.addItem(lb, ignoreBounds=True)

        # 大量點 (成交量局部高峰且高於均量) — 黃色圓點，畫在該棒 open 價
        self.bigvol_daily = pg.ScatterPlotItem(
            size=10, symbol='o', pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 255))
        self.bigvol_30m = pg.ScatterPlotItem(
            size=10, symbol='o', pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 0, 255))
        self.bigvol_daily.setVisible(self.bigvol_visible)
        self.bigvol_30m.setVisible(self.bigvol_visible)
        self.plot_daily.addItem(self.bigvol_daily)
        self.plot_30m.addItem(self.bigvol_30m)

        self.setup_inspector()
        
    def on_query_click(self):
        target_symbol = self.symbol_input.text().strip()
        if target_symbol:
            self.statusBar().showMessage(f"發送查詢請求: {target_symbol}...")
            self.query_symbol_signal.emit(target_symbol)
            self.symbol_input.clearFocus()
            
    @QtCore.pyqtSlot(pd.DataFrame, pd.DataFrame, pd.DataFrame)
    def on_initial_data(self, df_daily, df_30m, df_5m):
        """收到背景歷史資料，首次完整渲染圖表"""
        self.update_plots(df_daily, df_30m, df_5m, auto_range=True)
        self.statusBar().showMessage("歷史 K 線載入完成。")
        
    @QtCore.pyqtSlot(pd.DataFrame, pd.DataFrame, pd.DataFrame)
    def on_update_data(self, df_daily, df_30m, df_5m):
        """即時 Tick 行情更新"""
        self.update_plots(df_daily, df_30m, df_5m, auto_range=False)
        self.statusBar().showMessage(f"行情即時更新中... 最後更新時間: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
    @QtCore.pyqtSlot(dict)
    def on_tick_info(self, info):
        """更新股票名稱旁的最新成交單顯示。"""
        chg = info.get('chg', 0.0)
        # 台股慣例：漲紅、跌綠、平白
        color = "#ff3333" if chg > 0 else ("#00d060" if chg < 0 else "#dddddd")
        arrow = "▲" if chg > 0 else ("▼" if chg < 0 else "－")
        side_map = {1: "外", 2: "內"}
        side = side_map.get(info.get('tick_type', 0), "")
        side_txt = f" [{side}盤]" if side else ""
        text = (
            f"成交 {info.get('price', 0):.2f} "
            f"{arrow}{abs(chg):.2f} ({info.get('pct', 0):+.2f}%) "
            f"單量 {info.get('volume', 0)} 總量 {info.get('total_volume', 0)}"
            f"{side_txt}  {info.get('time', '')}"
        )
        self.tick_label.setText(text)
        self.tick_label.setStyleSheet(f"color: {color}; margin-left: 16px;")

    @QtCore.pyqtSlot(pd.DataFrame)
    def on_profile_data(self, df_1m):
        """收到 1 分 K，作為 30 分 Volume Profile 分箱來源並重繪。"""
        self.df_1m_source = df_1m
        if self._last_plot_30m is not None:
            self.update_volume_profile(self._last_plot_30m)

    @QtCore.pyqtSlot(pd.DataFrame)
    def on_daily_profile_data(self, df_daily_1m):
        """收到全區間 1 分 K，作為日K Volume Profile 分箱來源並重繪。"""
        self.df_daily_1m_source = df_daily_1m
        if self._last_df_daily is not None:
            self.update_daily_volume_profile(self._last_df_daily)

    @QtCore.pyqtSlot(str)
    def on_status_msg(self, msg):
        """接收背景狀態資訊"""
        self.statusBar().showMessage(msg)
        # 若狀態訊息包含 "已選定股票"，代表成功獲取股票名稱，更新頂部 Label
        if "已選定股票:" in msg:
            info = msg.split("已選定股票:")[1].split("，")[0].strip()
            self.info_label.setText(info)
            # 切換股票時清掉舊的成交單顯示，避免殘留前一檔資料
            self.tick_label.setText("")

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_C:
            self.save_screenshot()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_I:
            self.toggle_inspector()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_M:
            self.toggle_moving_averages()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_F:
            self.toggle_force_line()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_V:
            self.toggle_volume_profile()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_B:
            self.toggle_bigvol()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_9:
            self.reset_view()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_H:
            self.toggle_shortcut_help()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if (
            obj is self.symbol_input
            and event.type() == QtCore.QEvent.KeyPress
            and event.key() in (QtCore.Qt.Key_C, QtCore.Qt.Key_I, QtCore.Qt.Key_M, QtCore.Qt.Key_F, QtCore.Qt.Key_V, QtCore.Qt.Key_B, QtCore.Qt.Key_H)
            and event.modifiers() == QtCore.Qt.NoModifier
        ):
            if event.key() == QtCore.Qt.Key_C:
                self.save_screenshot()
            elif event.key() == QtCore.Qt.Key_I:
                self.toggle_inspector()
            elif event.key() == QtCore.Qt.Key_M:
                self.toggle_moving_averages()
            elif event.key() == QtCore.Qt.Key_F:
                self.toggle_force_line()
            elif event.key() == QtCore.Qt.Key_B:
                self.toggle_bigvol()
            elif event.key() == QtCore.Qt.Key_H:
                self.toggle_shortcut_help()
            else:
                self.toggle_volume_profile()
            return True
        return super().eventFilter(obj, event)

    def toggle_moving_averages(self):
        self.ma_visible = not self.ma_visible
        ma_items = [
            self.ma5_daily, self.ma20_daily, self.ma60_daily,
            self.ma5_30m, self.ma20_30m,
        ]
        for item in ma_items:
            item.setVisible(self.ma_visible)
        state = "顯示" if self.ma_visible else "隱藏"
        self.statusBar().showMessage(f"均線已{state}。按 M 切換。")

    def toggle_force_line(self):
        self.force_visible = not self.force_visible
        self.force_line_30m.setVisible(self.force_visible)
        state = "顯示" if self.force_visible else "隱藏"
        self.statusBar().showMessage(f"30分量價力道線已{state}。按 F 切換。")

    def toggle_volume_profile(self):
        self.profile_visible = not self.profile_visible
        self.profile_vp_30m.setVisible(self.profile_visible)
        self.profile_vp_daily.setVisible(self.profile_visible)
        # 藍色 POC 成交量標註跟著 V 切換 (空字串時本來就不顯示內容)
        self.vp_label_30m.setVisible(self.profile_visible)
        self.vp_label_daily.setVisible(self.profile_visible)
        state = "顯示" if self.profile_visible else "隱藏"
        self.statusBar().showMessage(f"日K/30分 Volume Profile 已{state}。按 V 切換。")

    def toggle_bigvol(self):
        self.bigvol_visible = not self.bigvol_visible
        self.bigvol_daily.setVisible(self.bigvol_visible)
        self.bigvol_30m.setVisible(self.bigvol_visible)
        state = "顯示" if self.bigvol_visible else "隱藏"
        self.statusBar().showMessage(f"大量點(黃點)已{state}。按 B 切換。")

    def _autorange_with_right_margin(self, plot, n):
        """價格圖自動貼齊資料，並在 K 線右側固定保留約 6 格，供 VP 量柱 (自下一根起) 顯示。"""
        vb = plot.getViewBox()
        vb.autoRange()  # 立即 fit 全部項目 (X+Y)
        xr = vb.viewRange()[0]
        vb.setXRange(min(xr[0], -1), n + 11, padding=0)  # 右側保留 VP 量柱 + 成交量標註空間

    def reset_view(self):
        """恢復最大畫面：取消手動縮放，四張圖重新自動貼齊全部資料 (參考 fut2026 按 9)。"""
        if self._last_df_daily is not None and len(self._last_df_daily):
            self._autorange_with_right_margin(self.plot_daily, len(self._last_df_daily))
            self._fit_volume_axis(self.plot_daily_vol, self._last_df_daily, force=True)
        if self._last_plot_30m is not None and len(self._last_plot_30m):
            self._autorange_with_right_margin(self.plot_30m, len(self._last_plot_30m))
            self._fit_volume_axis(self.plot_30m_vol, self._last_plot_30m, force=True)
        self.statusBar().showMessage("已恢復最大畫面。按 9 重設。")

    def _position_shortcut_help(self):
        if self.shortcut_help is None:
            return
        margin = 16
        x = max(margin, self.width() - self.shortcut_help.width() - margin)
        self.shortcut_help.move(x, margin + 40)

    def toggle_shortcut_help(self):
        """按 H 顯示/隱藏快捷鍵說明疊層 (參考 fut2026)。"""
        if self.shortcut_help is None:
            help_text = (
                "快捷鍵說明\n\n"
                "H       顯示 / 隱藏本說明\n"
                "9       恢復最大畫面 (取消縮放)\n"
                "C       截圖存檔 stock.png\n"
                "I       檢視游標 (十字線/K棒資訊) + 游標所在K棒VP(日K/30分)\n"
                "M       均線 (MA)\n"
                "F       30分 量價力道線\n"
                "V       Volume Profile (日K / 30分)\n"
                "B       大量點 (成交量高峰黃點)"
            )
            self.shortcut_help = QtWidgets.QLabel(help_text, self)
            self.shortcut_help.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            self.shortcut_help.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.shortcut_help.setStyleSheet(
                "QLabel {"
                "background-color: rgba(12, 12, 12, 235);"
                "color: #f2f2f2;"
                "border: 1px solid #777;"
                "border-radius: 4px;"
                "padding: 14px 18px;"
                "font-family: 'Consolas', 'Microsoft JhengHei';"
                "font-size: 14px;"
                "}"
            )
            self.shortcut_help.adjustSize()

        if self.shortcut_help.isVisible():
            self.shortcut_help.hide()
            return
        self._position_shortcut_help()
        self.shortcut_help.raise_()
        self.shortcut_help.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.shortcut_help is not None and self.shortcut_help.isVisible():
            self._position_shortcut_help()

    def update_force_line(self, data):
        if len(data) < 2:
            self.force_line_30m.setData([], [])
            return

        closes = data['close'].astype(float).to_numpy()
        opens = data['open'].astype(float).to_numpy()
        volumes = data['volume'].astype(float).to_numpy()
        signed = np.sign(closes - opens) * volumes
        force = np.cumsum(signed)
        if np.nanmax(force) == np.nanmin(force):
            self.force_line_30m.setData([], [])
            return

        y_min = float(np.nanmin(data['low'].astype(float)))
        y_max = float(np.nanmax(data['high'].astype(float)))
        pad = (y_max - y_min) * 0.12
        lo = y_min + pad
        hi = y_max - pad
        scaled = lo + (force - np.nanmin(force)) / (np.nanmax(force) - np.nanmin(force)) * max(0.01, hi - lo)
        self.force_line_30m.setData(np.arange(len(data)), scaled)

    def _render_vp_bars(self, bar_item, source, base_x, max_width=5.0, ref=None, price_round=2):
        """依實際成交價 (round 到 price_round 位) 每個價位畫一根水平量柱。

        ref=(pmin, pmax, max_vol, poc)：若提供則以其量能 (ref[2]) 為寬度基準，
        讓橘色游標 VP 與藍色全區間 VP 用同一把尺、可直接比較；否則以 source 自算。
        回傳 (pmin, pmax, max_vol, poc_price)；無法繪製時回傳 None。
        """
        if source is None or len(source) == 0:
            bar_item.setOpts(x0=[], y=[], width=[], height=[])
            return None
        prices = np.round(source['close'].astype(float).to_numpy(), price_round)
        vols = source['volume'].astype(float).to_numpy()
        valid = np.isfinite(prices) & np.isfinite(vols) & (vols > 0)
        prices, vols = prices[valid], vols[valid]
        if len(prices) == 0:
            bar_item.setOpts(x0=[], y=[], width=[], height=[])
            return None

        # 每一個成交價位彙總成一根量柱
        y, inv = np.unique(prices, return_inverse=True)
        vol_by_price = np.bincount(inv, weights=vols)
        own_max = float(vol_by_price.max())
        max_vol = ref[2] if ref is not None else own_max  # 沿用基準或自算
        if max_vol <= 0:
            bar_item.setOpts(x0=[], y=[], width=[], height=[])
            return None

        # 上限夾在 max_width：橘色若在單一價位量超過基準也不溢出量柱區
        widths = np.minimum(vol_by_price / max_vol * max_width, max_width)
        if len(y) > 1:
            bar_h = float(np.median(np.diff(y)))  # 相鄰價位間距，讓量柱接近連續
        else:
            bar_h = max(float(y[0]) * 0.001, 0.01)
        if bar_h <= 0:
            bar_h = 0.01
        bar_item.setOpts(x0=base_x, y=y, width=widths, height=bar_h)
        poc_price = float(y[int(np.argmax(vol_by_price))])  # 最大量價位
        return (float(y.min()), float(y.max()), own_max, poc_price)

    @staticmethod
    def _fmt_vol(v):
        """成交量數字格式化 (萬/億)。"""
        v = float(v or 0)
        if v >= 1e8:
            return f"{v / 1e8:.2f}億"
        if v >= 1e4:
            return f"{v / 1e4:.1f}萬"
        return f"{int(round(v))}"

    def _draw_vp_bars(self, bar_item, source, anchor_data):
        """以 1 分 K 收盤+成交量分箱畫水平量柱 Volume Profile。

        source: 1 分 K 分箱來源；會對齊 anchor_data 的起始時間。無 source 時
        退回用 anchor_data 的 close 近似。量柱錨定於 anchor_data 右緣。
        30 分與日K 共用此方法。
        """
        if anchor_data is None or len(anchor_data) == 0:
            bar_item.setOpts(x0=[], y=[], width=[], height=[])
            return None

        if source is not None and len(source) > 0:
            t0 = pd.to_datetime(anchor_data['date'].values[0])
            source = source[pd.to_datetime(source['date']) >= t0]
        if source is None or len(source) == 0:
            source = anchor_data
        return self._render_vp_bars(bar_item, source, base_x=len(anchor_data), max_width=5.0)

    def _annotate_vp_label(self, label_item, info, base_x, visible):
        """在 VP 最大量價位 (POC) 右側標註「價位 / 該價位成交量」。"""
        if info is None or not visible:
            label_item.setVisible(False)
            return
        poc_price, poc_vol = info[3], info[2]  # 最大量價位 與 該價位量
        label_item.setText(f"{poc_price:.2f} / {self._fmt_vol(poc_vol)}")
        label_item.setPos(base_x + 5.3, poc_price)
        label_item.setVisible(True)

    def update_volume_profile(self, anchor_data):
        """30 分 Volume Profile：用近 7 天 1 分 K，錨定於 30 分視窗。"""
        # 存下分箱範圍與量能基準，供橘色游標 VP 沿用同一把尺
        self._vp_ref_30m = self._draw_vp_bars(self.profile_vp_30m, self.df_1m_source, anchor_data)
        n = len(anchor_data) if anchor_data is not None else 0
        self._annotate_vp_label(self.vp_label_30m, self._vp_ref_30m, n, self.profile_visible)

    def update_daily_volume_profile(self, anchor_daily):
        """日K Volume Profile：用全區間 1 分 K 收盤+成交量，錨定於日K。"""
        self._vp_ref_daily = self._draw_vp_bars(self.profile_vp_daily, self.df_daily_1m_source, anchor_daily)
        n = len(anchor_daily) if anchor_daily is not None else 0
        self._annotate_vp_label(self.vp_label_daily, self._vp_ref_daily, n, self.profile_visible)

    def _clear_hover_vp(self):
        for it in (self.hover_vp_30m, self.hover_vp_daily,
                   self.hover_label_30m, self.hover_label_daily):
            it.setVisible(False)

    def _update_hover_vp(self, data, idx, bar_item, label_item, src_1m, bar_delta, ref):
        """畫出滑鼠所在「單一 K 棒」的 VP 到 K 線右側 (橘色)，並標註該根成交量。

        取該根 K 棒時間範圍內的 1 分 K 收盤+成交量做 VP，橘色量柱畫在最後一根 K
        的下一根起。ref 沿用藍色全區間 VP 的分箱範圍與量能基準，讓寬度比例與
        藍色一致、可直接比較。日K 與 30 分共用。
        """
        if data is None or len(data) < 1 or idx < 0 or idx >= len(data):
            bar_item.setVisible(False)
            label_item.setVisible(False)
            return

        bar_start = pd.to_datetime(data['date'].values[idx])
        bar_end = bar_start + bar_delta
        src = src_1m
        if src is not None and len(src) > 0:
            ds = pd.to_datetime(src['date'])
            src = src[(ds >= bar_start) & (ds < bar_end)]
        if src is None or len(src) == 0:
            src = data.iloc[idx:idx + 1]  # 無 1 分資料則退回用該根 K

        base_x = len(data)  # 從最後一根 K 的下一根開始畫 (右側已保留空間)
        info = self._render_vp_bars(bar_item, src, base_x, max_width=5.0, ref=ref)
        if info is not None:
            bar_item.setVisible(True)
            self._annotate_vp_label(label_item, info, base_x, True)
        else:
            bar_item.setVisible(False)
            label_item.setVisible(False)

    def setup_inspector(self):
        self.inspect_targets = [
            ("日K", self.plot_daily, self.plot_daily_vol, self.kline_daily, True),
            ("30分K", self.plot_30m, self.plot_30m_vol, self.kline_30m, False),
        ]
        for _, plot, vol_plot, _, _ in self.inspect_targets:
            # 價格圖：K 棒下方的有限垂直線 (只畫 K 棒下方，不穿過 K 棒、留空間)
            vline = pg.PlotCurveItem(pen=pg.mkPen('#ffff00', width=1))
            # 成交量副圖：整條垂直線，一路連到量柱
            vol_vline = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#ffff00', width=1))
            label = pg.TextItem(
                text="",
                color="#ffffff",
                anchor=(0, 1),
                fill=pg.mkBrush(0, 0, 0, 190),
                border=pg.mkPen('#ffff00', width=1),
            )
            plot.addItem(vline, ignoreBounds=True)
            plot.addItem(label, ignoreBounds=True)
            vol_plot.addItem(vol_vline, ignoreBounds=True)
            vline.hide()
            vol_vline.hide()
            label.hide()
            plot._inspect_vline = vline
            plot._inspect_vol_vline = vol_vline
            plot._inspect_label = label

        self.win.scene().sigMouseMoved.connect(self.on_mouse_moved)

    def toggle_inspector(self):
        self.inspect_enabled = not self.inspect_enabled
        if not self.inspect_enabled:
            self.hide_inspector()
        state = "開啟" if self.inspect_enabled else "關閉"
        self.statusBar().showMessage(f"KBar 檢視模式已{state}。按 I 切換。")

    def hide_inspector(self):
        for _, plot, _, _, _ in self.inspect_targets:
            plot._inspect_vline.hide()
            plot._inspect_vol_vline.hide()
            plot._inspect_label.hide()
        self._clear_hover_vp()

    def on_mouse_moved(self, scene_pos):
        if not self.inspect_enabled:
            return

        for name, plot, vol_plot, layer, is_daily in self.inspect_targets:
            if not plot.sceneBoundingRect().contains(scene_pos):
                continue

            data = layer.data
            if len(data) == 0:
                return

            mouse_point = plot.getViewBox().mapSceneToView(scene_pos)
            idx = int(round(mouse_point.x()))
            if idx < 0 or idx >= len(data):
                self.hide_inspector()
                return

            row = data.iloc[idx]
            dt = pd.to_datetime(row['date'])
            time_text = dt.strftime('%Y/%m/%d') if is_daily else dt.strftime('%Y/%m/%d %H:%M')
            msg = (
                f"{name} {time_text}  "
                f"O:{float(row['open']):.2f} H:{float(row['high']):.2f} "
                f"L:{float(row['low']):.2f} C:{float(row['close']):.2f} "
                f"V:{float(row['volume']):.0f}"
            )

            self.hide_inspector()
            plot._inspect_label.setText(msg)
            x_ratio = idx / max(1, len(data) - 1)
            label_anchor_x = 1 if x_ratio > 0.65 else 0

            view_range = plot.getViewBox().viewRange()
            y_min, y_max = view_range[1]
            row_high = float(row['high'])
            row_low = float(row['low'])
            y_mid = (y_min + y_max) / 2
            if row_high > y_mid:
                label_y = row_low
                label_anchor_y = 0
            else:
                label_y = row_high
                label_anchor_y = 1

            # 價格圖：從 K 棒下方 (留 gap) 往下畫到圖底，不穿過 K 棒
            gap = (y_max - y_min) * 0.03
            plot._inspect_vline.setData([idx, idx], [y_min, row_low - gap])
            # 成交量副圖：整條垂直線，連到量柱
            plot._inspect_vol_vline.setPos(idx)

            plot._inspect_label.setAnchor((label_anchor_x, label_anchor_y))
            plot._inspect_label.setPos(idx, label_y)
            plot._inspect_vline.show()
            plot._inspect_vol_vline.show()
            plot._inspect_label.show()
            # 另外畫出滑鼠所在力道段的 VP 到 K 線右側 (日K/30分各自的 1 分來源)
            if is_daily:
                self._update_hover_vp(
                    data, idx, self.hover_vp_daily, self.hover_label_daily,
                    self.df_daily_1m_source, pd.Timedelta(days=1), self._vp_ref_daily)
            else:
                self._update_hover_vp(
                    data, idx, self.hover_vp_30m, self.hover_label_30m,
                    self.df_1m_source, pd.Timedelta(minutes=30), self._vp_ref_30m)
            self.statusBar().showMessage(msg)
            return

        self.hide_inspector()

    def save_screenshot(self):
        path = "stock.png"
        pixmap = self.grab()
        if pixmap.save(path):
            self.statusBar().showMessage(f"畫面已保存: {path}")
            print(f"畫面已保存: {path}", flush=True)
        else:
            self.statusBar().showMessage(f"保存畫面失敗: {path}")
            print(f"保存畫面失敗: {path}", flush=True)
            
    def update_plots(self, df_daily, df_30m, df_5m, auto_range=False):
        # 1. 更新日K (最多顯示 120 根)
        if len(df_daily) > 0:
            df_daily = tail_kbars(df_daily, 120)
            self.axis_daily.set_time_array(df_daily['date'].values)
            self.axis_daily_vol.set_time_array(df_daily['date'].values)
            self.kline_daily.set_data(df_daily)
            self.vol_daily.set_data(df_daily)
            
            close_prices = df_daily['close'].values.astype(float)
            if len(close_prices) >= 5:
                ma5 = pd.Series(close_prices).rolling(5).mean().values
                self.ma5_daily.setData(np.arange(len(df_daily)), ma5)
            if len(close_prices) >= 20:
                ma20 = pd.Series(close_prices).rolling(20).mean().values
                self.ma20_daily.setData(np.arange(len(df_daily)), ma20)
            if len(close_prices) >= 60:
                ma60 = pd.Series(close_prices).rolling(60).mean().values
                self.ma60_daily.setData(np.arange(len(df_daily)), ma60)

            bvx, bvy = get_volume_peak_markers(df_daily)
            self.bigvol_daily.setData(x=bvx, y=bvy)

            self._last_df_daily = df_daily
            self.update_daily_volume_profile(df_daily)

            if auto_range:
                self._autorange_with_right_margin(self.plot_daily, len(df_daily))
            self._fit_volume_axis(self.plot_daily_vol, df_daily, force=auto_range)
                
        # 2. 更新 30分K (最多顯示 120 根)
        if len(df_30m) > 0:
            plot_30m = tail_kbars(df_30m, 120)
            self.axis_30m.set_time_array(plot_30m['date'].values)
            self.axis_30m_vol.set_time_array(plot_30m['date'].values)
            self.kline_30m.set_data(plot_30m)
            self.vol_30m.set_data(plot_30m)
            
            close_prices_30m = plot_30m['close'].values.astype(float)
            if len(close_prices_30m) >= 5:
                ma5 = pd.Series(close_prices_30m).rolling(5).mean().values
                self.ma5_30m.setData(np.arange(len(plot_30m)), ma5)
            if len(close_prices_30m) >= 20:
                ma20 = pd.Series(close_prices_30m).rolling(20).mean().values
                self.ma20_30m.setData(np.arange(len(plot_30m)), ma20)

            bvx30, bvy30 = get_volume_peak_markers(plot_30m)
            self.bigvol_30m.setData(x=bvx30, y=bvy30)

            self.update_force_line(plot_30m)
            self._last_plot_30m = plot_30m
            self.update_volume_profile(plot_30m)
                
            if auto_range:
                self._autorange_with_right_margin(self.plot_30m, len(plot_30m))
            self._fit_volume_axis(self.plot_30m_vol, plot_30m, force=auto_range)

    def _fit_volume_axis(self, vol_plot, data, force=False):
        """調整成交量副圖 Y 軸上限。

        force=True (換股票時) 直接貼齊當前資料 (可放大也可縮小)；
        force=False (盤中即時) 只在需要時放大，避免與使用者縮放互搏、也避免抖動。
        VolumeBarItem 為自繪項目，autorange 會沿用舊快取邊界而失效，故改用明確 setYRange。
        """
        if data is None or len(data) == 0:
            return
        vmax = float(data['volume'].astype(float).max())
        if vmax <= 0:
            return
        target = vmax * 1.08
        cur_min, cur_max = vol_plot.getViewBox().viewRange()[1]
        if force or target > cur_max:
            vol_plot.setYRange(0, target, padding=0)
                
