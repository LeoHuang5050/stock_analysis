import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns, calc_continuous_sum_np

class FileLoaderThread(QThread):
    finished = pyqtSignal(object, object, object, list, str)  # df, price_data, diff_data, workdays_str, error_msg

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            # 读取Excel文件
            # df = pd.read_excel(self.file_path, dtype=str)  # 先全部读为字符串
            # 只用csv
            df = pd.read_csv(self.file_path, dtype=str)  # 先全部读为字符串
            
            # 处理数据类型转换
            for col in df.columns:
                try:
                    # 先尝试转换为float
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except Exception:
                    # 如果转换失败，保持原样
                    continue
            
            # 后续逻辑不变
            columns = df.columns.tolist()
            separator_idx = None
            for i, col in enumerate(columns):
                if (pd.isna(col) or col == '' or str(col).startswith('Unnamed')):
                    separator_idx = i
                    break
            if separator_idx is None:
                self.finished.emit(None, None, None, [], "未找到分隔列")
                return
            price_data = df.iloc[:, 0:separator_idx]
            price_data = unify_date_columns(price_data)
            diff_data = df.iloc[:, separator_idx+1:]
            diff_data = unify_date_columns(diff_data)
            all_dates = [col for col in price_data.columns if col[:4].isdigit()]
            all_dates = sorted(all_dates)
            self.finished.emit(df, price_data, diff_data, all_dates, "")
        except Exception as e:
            self.finished.emit(None, None, None, [], str(e))

class CalculateThread(QThread):
    finished = pyqtSignal(dict)  # 用字典传递所有结果

    def __init__(self, price_data, diff_data, workdays_str, params):
        super().__init__()
        self.price_data = price_data
        self.diff_data = diff_data
        self.workdays_str = workdays_str
        self.params = params  # 传递所有界面参数

    def run(self):
        # 1. 取出参数
        end_date = self.params.get("end_date")
        width = self.params.get("width")
        target_date = self.params.get("target_date")
        start_option = self.params.get("start_option")
        shift_days = self.params.get("shift_days")
        is_forward = self.params.get("is_forward")

        columns = list(self.diff_data.columns)
        try:
            end_idx = columns.index(end_date)
        except ValueError:
            self.finished.emit({"error": "结束日期不在diff_data中！"})
            return
        start_idx = end_idx + width - 1
        if start_idx >= len(columns):
            start_idx = len(columns) - 1
        date_columns = columns[end_idx:start_idx+1]
        first_row = self.price_data.iloc[0]
        price_data = [first_row[d] for d in date_columns]

        # 计算最大值、最小值
        max_value = max([v for v in price_data if pd.notna(v)])
        min_value = min([v for v in price_data if pd.notna(v)])

        # 目标日期相关
        target_value = None
        target_idx = None
        if target_date in date_columns:
            target_idx = date_columns.index(target_date)
            target_value = price_data[target_idx]
        else:
            target_value = None

        # 计算最接近值
        closest_date = "无"
        closest_value = "无"
        min_diff = float('inf')
        if start_option == "接近值" and target_value is not None and pd.notna(target_value):
            for i, (d, v) in enumerate(zip(date_columns, price_data)):
                if d == target_date or pd.isna(v):
                    continue
                diff = abs(v - target_value)
                if diff < min_diff:
                    min_diff = diff
                    closest_date = d
                    closest_value = v

        # 开始值
        start_value = price_data[-1] if price_data else "无"

        # 计算实际开始索引
        if start_option == "最大值":
            base_idx = price_data.index(max_value)
        elif start_option == "最小值":
            base_idx = price_data.index(min_value)
        elif start_option == "接近值":
            base_idx = price_data.index(closest_value) if closest_value != "无" else None
        else:  # "开始值"
            base_idx = len(price_data) - 1 if price_data else None

        # 前移天数
        actual_idx = None
        actual_date = "无"
        actual_value = "无"
        if base_idx is not None:
            actual_idx = base_idx + shift_days
            if 0 <= actual_idx < len(price_data):
                actual_date = date_columns[actual_idx]
                actual_value = price_data[actual_idx]

        # 计算连续累加值
        continuous_results = []
        forward_max_result = []
        forward_min_result = []
        forward_max_date = None
        forward_min_date = None

        if actual_date != "无" and end_date in self.diff_data.columns and actual_date in self.diff_data.columns:
            columns = list(self.diff_data.columns)
            start_idx = columns.index(actual_date)
            end_idx = columns.index(end_date)
            # 只计算diff_data第一行
            first_row = self.diff_data.iloc[0]
            arr = [first_row[d] for d in columns]
            result = calc_continuous_sum_np(arr, start_idx, end_idx)
            continuous_results = result

            # 向前最大/最小连续累加值
            if is_forward and actual_idx is not None and actual_idx < len(price_data) - 1:
                forward_range = price_data[actual_idx+1:]
                valid_forward = [(i, v) for i, v in enumerate(forward_range) if pd.notna(v)]
                if valid_forward and len(valid_forward) > 1:
                    min_i, min_val = min(valid_forward, key=lambda x: x[1])
                    max_i, max_val = max(valid_forward, key=lambda x: x[1])
                    min_idx = actual_idx + 1 + min_i
                    max_idx = actual_idx + 1 + max_i
                    forward_min_date = date_columns[min_idx]
                    forward_max_date = date_columns[max_idx]
                    min_start_idx = columns.index(forward_min_date)
                    max_start_idx = columns.index(forward_max_date)
                    print(f"min_start_idx: {min_start_idx}, max_start_idx: {max_start_idx}， end_idx: {end_idx}")
                    # 只计算diff_data第一行
                    first_row = self.diff_data.iloc[0]
                    arr = [first_row[d] for d in columns]
                    forward_min_result = [
                        calc_continuous_sum_np(arr, min_start_idx, end_idx)
                    ]
                    forward_max_result = [
                        calc_continuous_sum_np(arr, max_start_idx, end_idx)
                    ]
                else:
                    forward_min_date = forward_max_date = "无"
                    # 或者 forward_min_date = forward_max_date = date_columns[actual_idx+1]（如果只有一个有效值）

        # 组装结果
        result = {
            'shift_days': shift_days,
            'max_value': max_value,
            'min_value': min_value,
            'target_date': target_date,
            'target_value': target_value,
            'closest_date': closest_date,
            'closest_value': closest_value,
            'start_value': start_value,
            'actual_date': actual_date,
            'actual_value': actual_value,
            'is_forward': is_forward,
            'continuous_results': continuous_results,
            'forward_max_date': forward_max_date,
            'forward_max_result': forward_max_result,
            'forward_min_date': forward_min_date,
            'forward_min_result': forward_min_result,
        }
        self.finished.emit(result) 