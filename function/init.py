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
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "选择CSV文件", "", "CSV Files (*.csv)")
        if file_path:
            self.main_window.result_text.setText("正在上传，请稍候...")
            QApplication.processEvents()
            self.main_window.loader_thread = FileLoaderThread(file_path)
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
        self.main_window.date_picker.setMinimumDate(min_date)
        self.main_window.date_picker.setMaximumDate(max_date)

        # 获取今天
        today = QDate.currentDate()

        # 如果今天在范围内，设置为今天，否则设置为最大日期
        if min_date <= today <= max_date:
            self.main_window.date_picker.setDate(today)
            self.last_valid_date = today
        else:
            self.main_window.date_picker.setDate(max_date)
            self.last_valid_date = max_date

        # 计算最大宽度并更新标签
        max_width = len(self.workdays_str)
        self.main_window.width_label.setText(f"请选择日期宽度（最大宽度为 {max_width}）：")
        self.main_window.width_spin.setMaximum(max_width)
        self.main_window.result_text.setText("文件上传成功，请选择参数后点击计算。")

    def on_date_changed(self, qdate):
        date_str = qdate.toString("yyyy-MM-dd")
        if date_str not in self.workdays_str:
            QMessageBox.warning(self.main_window, "提示", "只能选择工作日！")
            if self.last_valid_date:
                self.main_window.date_picker.setDate(self.last_valid_date)
        else:
            self.last_valid_date = qdate
            # 动态调整日期宽度最大值
            end_idx = self.workdays_str.index(date_str)
            max_width = end_idx + 1  # 包含当前日期
            self.main_window.width_spin.setMaximum(max_width)
            self.main_window.width_label.setText(f"请选择日期宽度（最大宽度为 {max_width}）：")
            # 如果当前宽度大于最大宽度，自动调整
            if self.main_window.width_spin.value() > max_width:
                self.main_window.width_spin.setValue(max_width)

    def on_confirm_range(self):
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        width = self.main_window.width_spin.value()
        end_idx = self.workdays_str.index(end_date)
        start_idx = max(0, end_idx - width + 1)
        date_range = self.workdays_str[start_idx:end_idx+1]
        self.confirmed_date_range = date_range  # 保存下来
        
        # 更新目标日期下拉框
        self.main_window.target_date_combo.clear()
        self.main_window.target_date_combo.addItems(date_range)
        
        # 获取区间内的股票价格数据
        first_row = self.price_data.iloc[0]
        price_data = [first_row[d] for d in date_range]
        max_value = max([v for v in price_data if pd.notna(v)])
        min_value = min([v for v in price_data if pd.notna(v)])
        
        # 保存这些值供后续使用
        self.range_max_value = max_value
        self.range_min_value = min_value
        self.range_price_data = price_data
        self.range_date_range = date_range

        # 新增：设置提示
        start_date = date_range[0] if date_range else ""
        end_date = date_range[-1] if date_range else ""
        self.main_window.result_text.setText(
            f"日期宽度设置完毕，开始日期为：{start_date}，结束日期为：{end_date}"
        )

        # 新增：设置操作天数最大值和标签
        end_idx = self.workdays_str.index(end_date)
        max_op_days = len(self.workdays_str) - end_idx - 1  # 最大可操作天数为end_date到数组结束的距离
        if max_op_days < 0:
            max_op_days = 0
        self.main_window.op_days_label.setText(f"操作天数（最大{max_op_days}）")
        from PyQt5.QtGui import QIntValidator
        self.main_window.op_days_edit.setValidator(QIntValidator(0, max_op_days))

    def on_start_option_changed(self, idx):
        pass  # 不再做隐藏/显示 