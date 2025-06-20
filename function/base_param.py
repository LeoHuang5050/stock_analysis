from PyQt5.QtWidgets import QMessageBox, QApplication
import pandas as pd
from worker_threads import CalculateThread
import numpy as np

class BaseParamHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        self.range_max_value = None  # 确保有这个属性

    def on_calculate_clicked(self, params=None):
        if self.main_window.init.price_data is None:
            QMessageBox.warning(self.main_window, "提示", "请先上传Excel文件！")
            return None
        
        # 收集所有参数
        if params is None:
            params = {}
            
        params.update({
            "width": self.main_window.width_spin.value(),
            "start_option": self.main_window.start_option_combo.currentText(),
            "shift_days": self.main_window.shift_spin.value(),
            "is_forward": self.main_window.direction_checkbox.isChecked(),
            "n_days": self.main_window.n_days_spin.value(),
            "range_value": self.main_window.range_value_edit.text(),
            "continuous_abs_threshold": self.main_window.continuous_abs_threshold_edit.text(),
            "op_days": int(self.main_window.op_days_edit.text() or 0),
            "inc_rate": float(self.main_window.inc_rate_edit.text() or 0),
            "after_gt_end_ratio": float(self.main_window.after_gt_end_edit.text() or 0),
            "after_gt_start_ratio": float(self.main_window.after_gt_prev_edit.text() or 0),
            "expr": getattr(self.main_window, 'last_expr', ''),
            "ops_change": float(self.main_window.ops_change_edit.text() or 0),# 添加 only_show_selected 参数
        })
        
        self.main_window.result_text.setText("正在切换窗口，请稍候...")
        QApplication.processEvents()
        
        calc = CalculateThread(
            self.main_window.init.price_data, 
            self.main_window.init.diff_data, 
            self.main_window.init.workdays_str, 
            params
        )
        # result = calc.calculate_batch(params)
        # result = calc.calculate_py_version(params)
        result = calc.calculate_batch_16_cores(params)
        
        self.main_window.all_row_results = result  # 直接存储整个结果对象
        self.main_window.continuous_results = result.get('continuous_results', None)
        self.main_window.forward_max_date = result.get('forward_max_date')
        self.main_window.forward_max_result = result.get('forward_max_result')
        self.main_window.forward_min_date = result.get('forward_min_date')
        self.main_window.forward_min_result = result.get('forward_min_result')
        
        return result

    def update_shift_spin_range(self):
        # 获取当前区间
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        width = self.main_window.width_spin.value()
        end_idx = self.main_window.init.workdays_str.index(end_date)
        start_idx = max(0, end_idx - width)
        date_range = self.main_window.init.workdays_str[start_idx:end_idx+1]
        date_columns = [col for col in self.main_window.init.price_data.columns if col in date_range]
        first_row = self.main_window.init.price_data.iloc[0]
        price_data = [first_row[d] for d in date_columns]

        # 最大值、最小值及其对应日期，一次遍历完成
        max_value = None
        min_value = None
        max_date = None
        min_date = None
        for d, v in zip(date_columns, price_data):
            if pd.notna(v):
                if (max_value is None) or (v > max_value):
                    max_value = v
                    max_date = d
                if (min_value is None) or (v < min_value):
                    min_value = v
                    min_date = d

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
        
        # 获取第一行数据
        first_row = price_data.iloc[0]
        price_values = [first_row[d] for d in date_range if d in first_row.index]
        
        # 计算前N日最高值
        max_value = max([v for v in price_values if pd.notna(v)])
        
        # 获取结束日价格
        end_price = first_row[end_date]
        
        # 计算涨跌幅
        prev_date = self.main_window.init.workdays_str[end_idx-1]
        prev_prev_date = self.main_window.init.workdays_str[end_idx-2]
        
        prev_price = first_row[prev_date]
        prev_prev_price = first_row[prev_prev_date]
        
        # 计算前一日涨跌幅
        prev_day_change = ((prev_price - prev_prev_price) / prev_prev_price) * 100
        
        # 计算结束日涨跌幅
        end_day_change = ((end_price - prev_price) / prev_price) * 100
        
        # 获取后一组结束地址值
        diff_first_row = diff_data.iloc[0]
        diff_end_value = diff_first_row[end_date]
        
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