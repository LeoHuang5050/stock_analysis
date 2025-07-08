import sys
import os
import multiprocessing
from ui.stock_analysis_ui_v2 import StockAnalysisApp
from PyQt5.QtWidgets import QApplication, QMessageBox
import traceback

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

if __name__ == "__main__":
    # 设置全局异常处理器
    sys.excepthook = exception_hook
    
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    window = StockAnalysisApp()
    window.show()
    sys.exit(app.exec_())