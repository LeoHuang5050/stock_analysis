import sys
import os
import signal
import multiprocessing
from ui.stock_analysis_ui_v2 import StockAnalysisApp
from PyQt5.QtWidgets import QApplication, QMessageBox
import traceback
from worker_threads import ProcessPoolManager

def exception_hook(exctype, value, tb):
    """全局异常处理函数"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(error_msg)  # 同时在控制台打印错误信息
    
    # 创建错误对话框
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("程序错误")
    msg.setText("程序发生错误，请查看详细信息")
    msg.setDetailedText(error_msg)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

def signal_handler(signum, frame):
    """信号处理函数，确保程序退出时清理资源"""
    print(f"收到信号 {signum}，正在清理资源...")
    # 关闭进程池
    try:
        from worker_threads import process_pool_manager
        if process_pool_manager is not None:
            process_pool_manager.shutdown()
            print("进程池已关闭")
    except Exception as e:
        print(f"关闭进程池时出错: {e}")
    sys.exit(0)

if __name__ == "__main__":
    # 设置multiprocessing启动方式为spawn（推荐用于打包后的程序）
    multiprocessing.set_start_method('spawn', force=True)
    multiprocessing.freeze_support()  # 支持PyInstaller打包
    
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    # 设置全局异常处理器
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    
    window = StockAnalysisApp()
    window.show()
    sys.exit(app.exec_())