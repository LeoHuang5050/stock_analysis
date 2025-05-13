import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns, calc_continuous_sum_np
import numpy as np

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
                if col not in ['代码', '名称']:  # 只对非"代码""名称"列做数值转换
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    except Exception:
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
        n_days = self.params.get("n_days", 5)  # 默认为5，可由界面传入

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

        # 组装结果
        all_results = []
        for idx in range(self.price_data.shape[0]):
            row = self.price_data.iloc[idx]
            code = str(row['代码']) if '代码' in row else str(row.iloc[0])
            name = str(row['名称']) if '名称' in row else str(row.iloc[1])
            price_data = [row[d] for d in date_columns]
            valid_values = [v for v in price_data if pd.notna(v)]

            # 最大值、最小值（按行计算）
            max_value = None
            max_date = None
            min_value = None
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
            if target_date in date_columns:
                target_idx = date_columns.index(target_date)
                target_value = price_data[target_idx] if target_idx < len(price_data) else None
                target_date_val = target_date
            else:
                target_value = None
                target_date_val = None
            # 结束值、开始值
            end_value = price_data[0] if price_data else None
            end_date_val = date_columns[0] if price_data else None
            start_value = price_data[-1] if price_data else None
            start_date_val = date_columns[-1] if price_data else None
            # 实际开始日期值
            base_idx = None
            if start_option == "最大值":
                base_idx = price_data.index(max_value) if valid_values else None
            elif start_option == "最小值":
                base_idx = price_data.index(min_value) if valid_values else None
            elif start_option == "接近值":
                # 先计算最接近值
                closest_value = None
                closest_date = None
                if target_value is not None and pd.notna(target_value):
                    min_diff = float('inf')
                    for i, (d, v) in enumerate(zip(date_columns, price_data)):
                        if d == target_date or pd.isna(v):
                            continue
                        diff = abs(v - target_value)
                        if diff < min_diff:
                            min_diff = diff
                            closest_date = d
                            closest_value = v
                            closest_idx = i
                    base_idx = closest_idx if closest_value is not None else None
                else:
                    base_idx = None
            else:
                base_idx = len(price_data) - 1 if price_data else None
            actual_idx = base_idx + shift_days if base_idx is not None else None
            actual_date_val = date_columns[actual_idx] if actual_idx is not None and 0 <= actual_idx < len(price_data) else None
            actual_value = price_data[actual_idx] if actual_idx is not None and 0 <= actual_idx < len(price_data) else None
            # 最接近值（已在接近值分支中计算）
            if start_option != "接近值":
                closest_value = None
                closest_date = None
                if target_value is not None and pd.notna(target_value):
                    min_diff = float('inf')
                    for d, v in zip(date_columns, price_data):
                        if d == target_date or pd.isna(v):
                            continue
                        diff = abs(v - target_value)
                        if diff < min_diff:
                            min_diff = diff
                            closest_date = d
                            closest_value = v
            # diff_data相关（每行）
            continuous_results = []
            forward_max_result = []
            forward_min_result = []
            forward_max_date = None
            forward_min_date = None
            # 只要实际开始日期和结束日期都在diff_data中
            if actual_date_val and end_date in self.diff_data.columns and actual_date_val in self.diff_data.columns:
                columns_diff = list(self.diff_data.columns)
                start_idx_diff = columns_diff.index(actual_date_val)
                end_idx_diff = columns_diff.index(end_date)
                this_row = self.diff_data.iloc[idx]
                arr = [this_row[d] for d in columns_diff]
                continuous_results = calc_continuous_sum_np(arr, start_idx_diff, end_idx_diff)
                # 向前最大/最小连续累加值
                if is_forward and actual_idx is not None and actual_idx > 0:
                    # 向前区间：实际开始日期左侧（索引更小，结束日期方向）
                    forward_range = price_data[:actual_idx]
                    valid_forward = [(i, v) for i, v in enumerate(forward_range) if pd.notna(v)]
                    if valid_forward and len(valid_forward) > 1:
                        min_i, min_val = min(valid_forward, key=lambda x: x[1])
                        max_i, max_val = max(valid_forward, key=lambda x: x[1])
                        min_idx = min_i
                        max_idx = max_i
                        forward_min_date = date_columns[min_idx]
                        forward_max_date = date_columns[max_idx]
                        min_start_idx = columns_diff.index(forward_min_date)
                        max_start_idx = columns_diff.index(forward_max_date)
                        forward_min_result = calc_continuous_sum_np(arr, min_start_idx, end_idx_diff)
                        forward_max_result = calc_continuous_sum_np(arr, max_start_idx, end_idx_diff)
                    else:
                        forward_min_date = forward_max_date = None

            # 前N日最大值
            if n_days == 0:
                n_max_value = end_value  # 直接用结束值
            else:
                n_max_candidates = [v for v in price_data[:n_days] if pd.notna(v)]
                n_max_value = max(n_max_candidates) if n_max_candidates else None
                
            # 前N最大值是否大于等于区间最大值
            n_max_is_max = None
            if n_max_value is not None and max_value is not None:
                n_max_is_max = n_max_value >= max_value

            # 前1组结束地址前1日涨跌幅，前1组结束日涨跌幅
            prev_day_change = None
            end_day_change = None
            if len(price_data) >= 3 and pd.notna(price_data[1]) and pd.notna(price_data[2]) and pd.notna(price_data[0]):
                try:
                    if price_data[2] == 0 or price_data[2] is None or np.isnan(price_data[2]):
                        prev_day_change = None
                    else:
                        prev_day_change = ((price_data[1] - price_data[2]) / price_data[2]) * 100
                except Exception:
                    prev_day_change = None
                try:
                    if price_data[1] == 0 or price_data[1] is None or np.isnan(price_data[1]):
                        end_day_change = None
                    else:
                        end_day_change = ((price_data[0] - price_data[1]) / price_data[1]) * 100
                except Exception:
                    end_day_change = None

            # 获取diff_data中end_date对应的值
            diff_end_value = None
            if end_date in self.diff_data.columns:
                this_row_diff = self.diff_data.iloc[idx]
                diff_end_value = this_row_diff[end_date]
            
            # 读取用户输入的区间比值和绝对值阈值
            range_ratio_is_less = None
            abs_sum_is_less = None
            try:
                user_range_ratio = float(self.params.get('range_value', None))
            except Exception:
                user_range_ratio = None
            try:
                user_abs_sum = float(self.params.get('abs_sum_value', None))
            except Exception:
                user_abs_sum = None
            # 区间最大值/最小值比值判断
            if max_value is not None and min_value is not None and min_value != 0 and user_range_ratio is not None:
                range_ratio_is_less = (max_value / min_value) < user_range_ratio
            # 连续累加值绝对值判断
            if continuous_results and user_abs_sum is not None:
                abs_sum_is_less = all(abs(v) < user_abs_sum for v in continuous_results if v is not None)

            # 获取连续累加值开始值、开始后一位值、开始后两位值、连续累加值结束值、结束前一位值、结束前两位值
            continuous_start_value = continuous_results[0] if continuous_results else None
            continuous_start_next_value = continuous_results[1] if len(continuous_results) > 1 else None
            continuous_start_next_next_value = continuous_results[2] if len(continuous_results) > 2 else None
            continuous_end_value = continuous_results[-1] if continuous_results else None
            continuous_end_prev_value = continuous_results[-2] if len(continuous_results) > 1 else None
            continuous_end_prev_prev_value = continuous_results[-3] if len(continuous_results) > 2 else None

            # 连续累加值数组长度、连续累加值数组前一半绝对值之和、连续累加值数组后一半绝对值之和
            continuous_len = len(continuous_results) if continuous_results else None
            half = continuous_len // 2
            continuous_abs_sum_first_half = sum(abs(v) for v in continuous_results[:half]) if continuous_len > 0 else None
            continuous_abs_sum_second_half = sum(abs(v) for v in continuous_results[half:]) if continuous_len > 0 else None

            # 连续累加值数组分成四块，每块分别计算绝对值之和
            abs_arr = [abs(v) for v in continuous_results if v is not None]
            n = len(abs_arr)
            q1 = n // 4
            q2 = n // 2
            q3 = (3 * n) // 4
            continuous_abs_sum_block1 = sum(abs_arr[:q1]) if n > 0 else None
            continuous_abs_sum_block2 = sum(abs_arr[q1:q2]) if n > 0 else None
            continuous_abs_sum_block3 = sum(abs_arr[q2:q3]) if n > 0 else None
            continuous_abs_sum_block4 = sum(abs_arr[q3:]) if n > 0 else None

            # 有效累加值、向前最大有效累加值、向前最小有效累加值
            def calc_valid_sum(arr):
                arr = [v for v in arr if v is not None]
                n = len(arr)
                if n == 0:
                    return []
                result = []
                for i in range(n - 1):
                    cur = arr[i]
                    nxt = arr[i + 1]
                    if abs(nxt) > abs(cur):
                        result.append(cur)
                    else:
                        result.append(nxt if nxt >= 0 else -abs(nxt))
                # 补最后一位0
                result.append(0)
                return result
            valid_sum_arr = calc_valid_sum(continuous_results)
            forward_max_valid_sum_arr = calc_valid_sum(forward_max_result)
            forward_min_valid_sum_arr = calc_valid_sum(forward_min_result)

            # 有效累加值正加值和负加值
            def calc_pos_neg_sum(arr):
                pos_sum = sum(v for v in arr if v > 0)
                neg_sum = sum(v for v in arr if v < 0)
                return pos_sum, neg_sum
            valid_pos_sum, valid_neg_sum = calc_pos_neg_sum(valid_sum_arr)
            forward_max_valid_pos_sum, forward_max_valid_neg_sum = calc_pos_neg_sum(forward_max_valid_sum_arr)
            forward_min_valid_pos_sum, forward_min_valid_neg_sum = calc_pos_neg_sum(forward_min_valid_sum_arr)

            # 有效累加值数组长度，有效累加值一半绝对值之和、有效累加后一半绝对值之和
            valid_sum_len = len(valid_sum_arr) if valid_sum_arr else None
            valid_abs_sum_first_half = sum(abs(v) for v in valid_sum_arr[:valid_sum_len//2]) if valid_sum_len is not None and valid_sum_len > 0 else None
            valid_abs_sum_second_half = sum(abs(v) for v in valid_sum_arr[valid_sum_len//2:]) if valid_sum_len is not None and valid_sum_len > 0 else None

            # 有效累加值数组分成四块，每块分别计算绝对值之和
            abs_arr = [abs(v) for v in valid_sum_arr if v is not None]
            n = len(abs_arr)
            q1 = n // 4
            q2 = n // 2
            q3 = (3 * n) // 4
            valid_abs_sum_block1 = sum(abs_arr[:q1]) if n > 0 else None
            valid_abs_sum_block2 = sum(abs_arr[q1:q2]) if n > 0 else None
            valid_abs_sum_block3 = sum(abs_arr[q2:q3]) if n > 0 else None
            valid_abs_sum_block4 = sum(abs_arr[q3:]) if n > 0 else None

            # 只有勾选了"是否计算向前向后"才计算向前最大/最小相关
            if is_forward:
                # 向前最大有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_max_valid_sum_len = len(forward_max_valid_sum_arr) if forward_max_valid_sum_arr else None
                forward_max_valid_abs_sum_first_half = sum(abs(v) for v in forward_max_valid_sum_arr[:forward_max_valid_sum_len//2]) if forward_max_valid_sum_len is not None and forward_max_valid_sum_len > 0 else None
                forward_max_valid_abs_sum_second_half = sum(abs(v) for v in forward_max_valid_sum_arr[forward_max_valid_sum_len//2:]) if forward_max_valid_sum_len is not None and forward_max_valid_sum_len > 0 else None
                # 分四块
                abs_arr = [abs(v) for v in forward_max_valid_sum_arr if v is not None]
                n = len(abs_arr)
                q1 = n // 4
                q2 = n // 2
                q3 = (3 * n) // 4
                forward_max_valid_abs_sum_block1 = sum(abs_arr[:q1]) if n > 0 else None
                forward_max_valid_abs_sum_block2 = sum(abs_arr[q1:q2]) if n > 0 else None
                forward_max_valid_abs_sum_block3 = sum(abs_arr[q2:q3]) if n > 0 else None
                forward_max_valid_abs_sum_block4 = sum(abs_arr[q3:]) if n > 0 else None

                # 向前最小有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_min_valid_sum_len = len(forward_min_valid_sum_arr) if forward_min_valid_sum_arr else None
                forward_min_valid_abs_sum_first_half = sum(abs(v) for v in forward_min_valid_sum_arr[:forward_min_valid_sum_len//2]) if forward_min_valid_sum_len is not None and forward_min_valid_sum_len > 0 else None
                forward_min_valid_abs_sum_second_half = sum(abs(v) for v in forward_min_valid_sum_arr[forward_min_valid_sum_len//2:]) if forward_min_valid_sum_len is not None and forward_min_valid_sum_len > 0 else None
                # 分四块
                abs_arr = [abs(v) for v in forward_min_valid_sum_arr if v is not None]
                n = len(abs_arr)
                q1 = n // 4
                q2 = n // 2
                q3 = (3 * n) // 4
                forward_min_valid_abs_sum_block1 = sum(abs_arr[:q1]) if n > 0 else None
                forward_min_valid_abs_sum_block2 = sum(abs_arr[q1:q2]) if n > 0 else None
                forward_min_valid_abs_sum_block3 = sum(abs_arr[q2:q3]) if n > 0 else None
                forward_min_valid_abs_sum_block4 = sum(abs_arr[q3:]) if n > 0 else None
            else:
                forward_max_valid_sum_len = None
                forward_max_valid_abs_sum_first_half = None
                forward_max_valid_abs_sum_second_half = None
                forward_max_valid_abs_sum_block1 = None
                forward_max_valid_abs_sum_block2 = None
                forward_max_valid_abs_sum_block3 = None
                forward_max_valid_abs_sum_block4 = None
                forward_min_valid_sum_len = None
                forward_min_valid_abs_sum_first_half = None
                forward_min_valid_abs_sum_second_half = None
                forward_min_valid_abs_sum_block1 = None
                forward_min_valid_abs_sum_block2 = None
                forward_min_valid_abs_sum_block3 = None
                forward_min_valid_abs_sum_block4 = None

            # 获取全量价格数据
            row = self.price_data.iloc[idx]
            full_price_data = [row[d] for d in self.price_data.columns if d in row.index]
            end_idx = list(self.price_data.columns).index(end_date_val)

            # 递增值计算逻辑
            op_days = int(self.params.get("op_days", 0))
            inc_rate = float(self.params.get("inc_rate", 0)) * 0.01
            end_value = full_price_data[end_idx] if end_idx < len(full_price_data) else None

            increment_value = None
            if idx == 0:
                print(f"full_price_data: {full_price_data}")
                print(f"end_idx: {end_idx}, op_days: {op_days}, inc_rate: {inc_rate}, end_value: {end_value}")
            if end_value is not None and op_days > 0 and inc_rate > 0:
                threshold = end_value * inc_rate
                found = False
                start = end_idx
                stop = end_idx - op_days
                if idx == 0:
                    print(f"递增值遍历区间: start={start}, stop={stop}, threshold={threshold}")
                for i in range(start, stop, -1):
                    v = full_price_data[i]
                    if idx == 0:
                        print(f"i: {i}, v: {v}, v-end_value: {v-end_value if v is not None else None}")
                    if v is not None and (v - end_value) > threshold:
                        if idx == 0:
                            print(f"满足条件: i={i}, v={v}, v-end_value={v-end_value}, threshold={threshold}")
                        increment_value = v
                        found = True
                        break
                if not found:
                    fallback_idx = end_idx - op_days
                    if idx == 0:
                        print(f"未找到满足条件，fallback_idx: {fallback_idx}")
                    if fallback_idx >= 0:
                        increment_value = full_price_data[fallback_idx]
                    else:
                        increment_value = None
            else:
                increment_value = None
            if idx == 0:
                print(f"最终increment_value: {increment_value}")

            row_result = {
                "code": code,
                "name": name,
                "max_value": [max_date, max_value],
                "min_value": [min_date, min_value],
                "target_value": [target_date_val, target_value],
                "end_value": [end_date_val, end_value],
                "start_value": [start_date_val, start_value],
                "actual_value": [actual_date_val, actual_value],
                "closest_value": [closest_date, closest_value],
                "continuous_results": continuous_results,
                "forward_max_result": forward_max_result,
                "forward_min_result": forward_min_result,
                "forward_max_date": forward_max_date,
                "forward_min_date": forward_min_date,
                "n_max_value": n_max_value,
                "n_max_is_max": n_max_is_max,
                "prev_day_change": prev_day_change,
                "end_day_change": end_day_change,
                "diff_end_value": diff_end_value,  # 新增后一组结束地址值
                "range_ratio_is_less": range_ratio_is_less,  # 区间比值布尔
                "abs_sum_is_less": abs_sum_is_less,          # 绝对值布尔
                "continuous_start_value": continuous_start_value,
                "continuous_start_next_value": continuous_start_next_value,
                "continuous_start_next_next_value": continuous_start_next_next_value,
                "continuous_end_value": continuous_end_value,
                "continuous_end_prev_value": continuous_end_prev_value,
                "continuous_end_prev_prev_value": continuous_end_prev_prev_value,
                "continuous_len": continuous_len,  # 非空数据长度
                "continuous_abs_sum_first_half": continuous_abs_sum_first_half,  # 前一半绝对值之和
                "continuous_abs_sum_second_half": continuous_abs_sum_second_half,  # 后一半绝对值之和
                "continuous_abs_sum_block1": continuous_abs_sum_block1,  # 第一块绝对值之和
                "continuous_abs_sum_block2": continuous_abs_sum_block2,  # 第二块绝对值之和
                "continuous_abs_sum_block3": continuous_abs_sum_block3,  # 第三块绝对值之和
                "continuous_abs_sum_block4": continuous_abs_sum_block4,  # 第四块绝对值之和
                "valid_sum_arr": valid_sum_arr,  # 有效累加值数组
                "forward_max_valid_sum_arr": forward_max_valid_sum_arr,  # 向前最大有效累加值数组
                "forward_min_valid_sum_arr": forward_min_valid_sum_arr,  # 向前最小有效累加值数组
                "valid_pos_sum": valid_pos_sum,  # 有效累加值正加值和
                "valid_neg_sum": valid_neg_sum,  # 有效累加值负加值和
                "forward_max_valid_pos_sum": forward_max_valid_pos_sum,  # 向前最大有效累加值正加值和
                "forward_max_valid_neg_sum": forward_max_valid_neg_sum,  # 向前最大有效累加值负加值和
                "forward_min_valid_pos_sum": forward_min_valid_pos_sum,  # 向前最小有效累加值正加值和
                "forward_min_valid_neg_sum": forward_min_valid_neg_sum,  # 向前最小有效累加值负加值和
                "valid_sum_len": valid_sum_len,  # 有效累加值数组长度
                "valid_abs_sum_first_half": valid_abs_sum_first_half,  # 有效累加值一半绝对值之和
                "valid_abs_sum_second_half": valid_abs_sum_second_half,  # 有效累加值后一半绝对值之和
                "valid_abs_sum_block1": valid_abs_sum_block1,  # 有效累加值第一块绝对值之和
                "valid_abs_sum_block2": valid_abs_sum_block2,  # 有效累加值第二块绝对值之和
                "valid_abs_sum_block3": valid_abs_sum_block3,  # 有效累加值第三块绝对值之和
                "valid_abs_sum_block4": valid_abs_sum_block4,  # 有效累加值第四块绝对值之和
                "forward_max_valid_sum_len": forward_max_valid_sum_len,  # 向前最大有效累加值数组长度
                "forward_max_valid_abs_sum_first_half": forward_max_valid_abs_sum_first_half,  # 向前最大有效累加值数组前一半绝对值之和
                "forward_max_valid_abs_sum_second_half": forward_max_valid_abs_sum_second_half,  # 向前最大有效累加值数组后一半绝对值之和
                "forward_max_valid_abs_sum_block1": forward_max_valid_abs_sum_block1,  # 向前最大有效累加值数组第一块绝对值之和
                "forward_max_valid_abs_sum_block2": forward_max_valid_abs_sum_block2,  # 向前最大有效累加值数组第二块绝对值之和
                "forward_max_valid_abs_sum_block3": forward_max_valid_abs_sum_block3,  # 向前最大有效累加值数组第三块绝对值之和
                "forward_max_valid_abs_sum_block4": forward_max_valid_abs_sum_block4,  # 向前最大有效累加值数组第四块绝对值之和
                "forward_min_valid_sum_len": forward_min_valid_sum_len,  # 向前最小有效累加值数组长度
                "forward_min_valid_abs_sum_first_half": forward_min_valid_abs_sum_first_half,  # 向前最小有效累加值数组前一半绝对值之和
                "forward_min_valid_abs_sum_second_half": forward_min_valid_abs_sum_second_half,  # 向前最小有效累加值数组后一半绝对值之和
                "forward_min_valid_abs_sum_block1": forward_min_valid_abs_sum_block1,  # 向前最小有效累加值数组第一块绝对值之和
                "forward_min_valid_abs_sum_block2": forward_min_valid_abs_sum_block2,  # 向前最小有效累加值数组第二块绝对值之和
                "forward_min_valid_abs_sum_block3": forward_min_valid_abs_sum_block3,  # 向前最小有效累加值数组第三块绝对值之和
                "forward_min_valid_abs_sum_block4": forward_min_valid_abs_sum_block4,  # 向前最小有效累加值数组第四块绝对值之和
                "increment_value": increment_value,  # 递增值
            }
            all_results.append(row_result)

        result = {
            "rows": all_results,
            "shift_days": shift_days,
            "is_forward": is_forward,
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
        }
        self.finished.emit(result)