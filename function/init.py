from PyQt5.QtWidgets import QMessageBox, QFileDialog, QApplication
from PyQt5.QtCore import QDate
import pandas as pd
from worker_threads import FileLoaderThread

class StockAnalysisInit:
    def __init__(self, main_window):
        self.main_window = main_window
        self.df = None
        self.price_data = None
        self.diff_data = None
        self.workdays_str = []
        self.last_valid_date = None
        self.range_max_value = None
        self.range_min_value = None
        self.range_price_data = None
        self.range_date_range = None

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "选择文件", "", "CSV/Excel Files (*.csv *.xlsx)")
        if file_path:
            self.main_window.result_text.setText("正在上传，请稍候...")
            QApplication.processEvents()
            # 判断文件类型
            if file_path.lower().endswith('.csv'):
                self.main_window.loader_thread = FileLoaderThread(file_path)
            elif file_path.lower().endswith('.xlsx'):
                self.main_window.loader_thread = FileLoaderThread(file_path, file_type='xlsx')
            else:
                QMessageBox.warning(self.main_window, "提示", "仅支持CSV或XLSX文件！")
                return
            self.main_window.loader_thread.finished.connect(self.on_file_loaded)
            self.main_window.loader_thread.start()

    def on_file_loaded(self, df, price_data, diff_data, workdays_str, error_msg):
        if error_msg:
            QMessageBox.critical(self.main_window, "错误", f"文件读取失败：{error_msg}")
            return
        
        self.df = df
        self.price_data = price_data
        self.diff_data = diff_data
        self.workdays_str = workdays_str
        
        # 设置日期选择器范围
        min_date = QDate.fromString(self.workdays_str[0], "yyyy-MM-dd")
        max_date = QDate.fromString(self.workdays_str[-1], "yyyy-MM-dd")
        # self.main_window.date_picker.setMinimumDate(min_date)
        # self.main_window.date_picker.setMaximumDate(max_date)

        # 获取今天
        today = QDate.currentDate()

        # 如果今天在范围内，设置为今天，否则设置为最大日期
        if min_date <= today <= max_date:
            self.main_window.date_picker.setDate(today)
            self.last_valid_date = today
        else:
            self.main_window.date_picker.setDate(max_date)
            self.last_valid_date = max_date
        
        # 更新自动分析界面的开始和结束日期为最大交易日
        self.main_window.last_analysis_start_date = max_date.toString("yyyy-MM-dd")
        self.main_window.last_analysis_end_date = max_date.toString("yyyy-MM-dd")

        # 获取当前结束日期
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        if end_date in self.workdays_str:
            max_width = self.workdays_str.index(end_date)
        else:
            max_width = len(self.workdays_str) - 1  # 兜底

        self.main_window.width_label.setText(f"请选择日期宽度（最大宽度为 {max_width}）：")
        self.main_window.width_spin.setMaximum(max_width)
        self.main_window.result_text.setText("文件上传成功，请选择参数后进行选股计算。")
        
        QMessageBox.information(self.main_window, "提示", "文件上传成功，请选择参数后进行选股计算")

        # 恢复config日期
        if hasattr(self.main_window, 'pending_date'):
            date_str = self.main_window.pending_date
            if date_str in self.workdays_str:
                self.main_window.date_picker.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
            else:
                max_date = self.workdays_str[-1]
                self.main_window.date_picker.setDate(QDate.fromString(max_date, "yyyy-MM-dd"))
            del self.main_window.pending_date

    def on_date_changed(self, qdate):
        # 只保存日期，不做验证
        self.last_valid_date = qdate
        # 动态调整日期宽度最大值
        if hasattr(self, 'workdays_str') and self.workdays_str:
            date_str = qdate.toString("yyyy-MM-dd")
            end_idx = self.workdays_str.index(date_str) if date_str in self.workdays_str else len(self.workdays_str) - 1
            max_width = end_idx
            self.main_window.width_spin.setMaximum(max_width)
            self.main_window.width_label.setText(f"请选择日期宽度（最大宽度为 {max_width}）：")
            if self.main_window.width_spin.value() > max_width:
                self.main_window.width_spin.setValue(max_width)

    def on_start_option_changed(self, idx):
        pass  # 不再做隐藏/显示 