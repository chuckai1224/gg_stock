# -*- coding: utf-8 -*-
import sys
import argparse
from PyQt5 import QtWidgets, QtCore
from gui_stock_main_gg import StockPlotWindow
from stock_worker_gg import StockWorker

class MainWindow(StockPlotWindow):
    def __init__(self, worker, default_symbol='2330'):
        self.worker = worker
        super().__init__(default_symbol=default_symbol)
        
    def closeEvent(self, event):
        """關閉視窗時，安全停止背景執行緒並登出 API"""
        self.statusBar().showMessage("正在卸載訂閱並安全登出 API...")
        self.worker.stop()
        if not self.worker.wait(5000):
            print("背景執行緒停止逾時，強制關閉。")
        event.accept()

def main():
    parser = argparse.ArgumentParser(description="股票日K、30分K、5分K多週期即時看盤系統")
    parser.add_argument(
        "--symbol", 
        type=str, 
        default="2330",
        help="預設載入的股票代號，例如 2330。預設值為 2330。"
    )
    args = parser.parse_args()
    
    app = QtWidgets.QApplication(sys.argv)
    
    # 1. 建立背景行情 Worker
    worker = StockWorker(default_symbol=args.symbol)
    
    # 2. 建立 GUI 視窗
    window = MainWindow(worker=worker, default_symbol=args.symbol)
    
    # 3. 串接訊號與槽函數
    worker.initial_data.connect(window.on_initial_data)
    worker.update_data.connect(window.on_update_data)
    worker.status_msg.connect(window.on_status_msg)
    
    # 關鍵：將 UI 的查詢代號訊號綁定到背景 Worker 的切換股票槽函數
    window.query_symbol_signal.connect(worker.change_symbol)
    
    # 4. 顯示視窗與啟動執行緒
    window.show()
    worker.start()
    
    # 5. 啟動後延遲 500ms 自動觸發首次查詢，加載預設股票
    QtCore.QTimer.singleShot(800, lambda: window.query_symbol_signal.emit(args.symbol))
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
