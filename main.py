import sys
from ui.stock_analysis_ui_v2 import StockAnalysisApp
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StockAnalysisApp()
    window.show()
    sys.exit(app.exec_())