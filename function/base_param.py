from PyQt5.QtWidgets import QMessageBox, QApplication
import pandas as pd
from worker_threads import CalculateThread

class BaseParamHandler:
    def __init__(self, main_window):
        self.main_window = main_window

    def on_calculate_clicked(self):
        if self.main_window.init.price_data is None:
            QMessageBox.warning(self.main_window, "提示", "请先上传Excel文件！")
            return
            
        # 收集所有参数
        params = {
            "end_date": self.main_window.date_picker.date().toString("yyyy-MM-dd"),
            "width": self.main_window.width_spin.value(),
            "target_date": self.main_window.target_date_combo.currentText(),
            "start_option": self.main_window.start_option_combo.currentText(),
            "shift_days": self.main_window.shift_spin.value(),
            "is_forward": self.main_window.direction_checkbox.isChecked()
        }
        
        self.main_window.result_text.setText("正在生成基础参数，请稍候...")
        QApplication.processEvents()
        
        self.main_window.calc_thread = CalculateThread(
            self.main_window.init.price_data, 
            self.main_window.init.diff_data, 
            self.main_window.init.workdays_str, 
            params
        )
        self.main_window.calc_thread.finished.connect(self.on_calculate_finished)
        self.main_window.calc_thread.start()

    def on_calculate_finished(self, result):
        # 这里用result字典恢复所有展示内容
        self.main_window.result_text.setText(
            f"前移天数：{result['shift_days']}\n"
            f"最大值：{result['max_value']}\n"
            f"最小值：{result['min_value']}\n"
            f"目标日期：{result['target_date']} 股价：{result['target_value']}\n"
            f"最接近值日期：{result['closest_date']} 股价：{result['closest_value']}\n"
            f"开始值日期：{result['start_date']} 开始值：{result['start_value']}\n"
            f"实际开始日期：{result['actual_date']} 实际开始日期值：{result['actual_value']}\n"
            f"是否计算向前向后：{result['is_forward']}\n"
            f"连续累加值结果：{result['continuous_results'][0] if result['continuous_results'] else '无'}\n"
            f"向前最大开始日期：{result['forward_max_date']} 结果：{result['forward_max_result'][0] if result['forward_max_result'] else '无'}\n"
            f"向前最小开始日期：{result['forward_min_date']} 结果：{result['forward_min_result'][0] if result['forward_min_result'] else '无'}\n"
        )

    def update_shift_spin_range(self):
        # 获取当前区间
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        width = self.main_window.width_spin.value()
        end_idx = self.main_window.init.workdays_str.index(end_date)
        start_idx = max(0, end_idx - width + 1)
        date_range = self.main_window.init.workdays_str[start_idx:end_idx+1]
        date_columns = [col for col in self.main_window.init.price_data.columns if col in date_range]
        first_row = self.main_window.init.price_data.iloc[0]
        price_data = [first_row[d] for d in date_columns]

        # 最大值、最小值、最接近值
        max_value = max([v for v in price_data if pd.notna(v)])
        min_value = min([v for v in price_data if pd.notna(v)])

        # 目标日期
        target_date = self.main_window.target_date_combo.currentText()
        target_value = None
        if target_date in date_columns:
            target_value = price_data[date_columns.index(target_date)]

        # 最接近值
        closest_value = None
        if self.main_window.start_option_combo.currentText() == "接近值" and target_value is not None and pd.notna(target_value):
            min_diff = float('inf')
            for i, (d, v) in enumerate(zip(date_columns, price_data)):
                if d == target_date or pd.isna(v):
                    continue
                diff = abs(v - target_value)
                if diff < min_diff:
                    min_diff = diff
                    closest_value = v

        # 计算base_idx
        start_option = self.main_window.start_option_combo.currentText()
        if start_option == "最大值":
            base_idx = price_data.index(max_value)
        elif start_option == "最小值":
            base_idx = price_data.index(min_value)
        elif start_option == "接近值":
            base_idx = price_data.index(closest_value) if closest_value is not None else None
        else:  # "开始值"
            base_idx = len(price_data) - 1 if price_data else None

        # 设置shift_spin范围
        if base_idx is not None:
            min_shift = -base_idx
            max_shift = len(price_data) - 1 - base_idx
            self.main_window.shift_spin.setMinimum(min_shift)
            self.main_window.shift_spin.setMaximum(max_shift)
        else:
            self.main_window.shift_spin.setMinimum(0)
<<<<<<< Updated upstream
            self.main_window.shift_spin.setMaximum(0) 
=======
            self.main_window.shift_spin.setMaximum(0)

        self.range_max_value = max_value  # 记录最大值
        self.main_window.max_value = max_value
        self.main_window.min_value = min_value
        self.main_window.max_date = max_date
        self.main_window.min_date = min_date

    def on_extend_clicked(self):
        if self.main_window.init.price_data is None:
            QMessageBox.warning(self.main_window, "提示", "请先上传文件！")
            return
            
        self.main_window.result_text.setText("正在生成扩展参数，请稍候...")
        QApplication.processEvents()
        
        # 获取结束日期
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        n_days = self.main_window.n_days_spin.value()
        
        # 获取价格数据
        price_data = self.main_window.init.price_data
        diff_data = self.main_window.init.diff_data
        
        # 获取日期索引
        end_idx = self.main_window.init.workdays_str.index(end_date)
        start_idx = max(0, end_idx - n_days + 1)
        date_range = self.main_window.init.workdays_str[start_idx:end_idx+1]
        
        # 获取所有行的区间数据
        price_rows = []
        for idx in range(price_data.shape[0]):
            row = price_data.iloc[idx]
            price_rows.append([row[d] for d in date_range if d in row.index])
        
        # 计算前N日最高值
        max_value = max([v for v in price_rows[-1] if pd.notna(v)])
        
 # 获取结束日价格
        end_price = price_rows[-1][-1] if price_rows[-1] else None
        
        # 计算涨跌幅
        prev_date = self.main_window.init.workdays_str[end_idx-1]
        prev_prev_date = self.main_window.init.workdays_str[end_idx-2]
        
        prev_price = price_rows[-2][-1] if price_rows[-2] else None
        prev_prev_price = price_rows[-3][-1] if price_rows[-3] else None
        
        # 计算前一日涨跌幅
        prev_day_change = ((prev_price - prev_prev_price) / prev_prev_price) * 100 if prev_price and prev_prev_price else None
        
        # 计算结束日涨跌幅
        end_day_change = ((end_price - prev_price) / prev_price) * 100 if end_price and prev_price else None
        
        # 获取后一组结束地址值
        diff_first_row = diff_data.iloc[0]
        diff_end_value = diff_first_row[end_date] if end_date in diff_first_row.index else None
        
        # 显示结果
        self.main_window.result_text.setText(
            f"前一组结束地址值：{end_price}\n"
            f"前N日最高值：{max_value}\n"
            f"前1组结束地址前1日涨跌幅：{prev_day_change:.2f}%\n"
            f"前一组结束日涨跌幅：{end_day_change:.2f}%\n"
            f"后一组结束地址值：{diff_end_value}"
        ) 

    def get_range_max_value(self):
        return self.range_max_value 
>>>>>>> Stashed changes
