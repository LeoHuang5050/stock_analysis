import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns, calc_continuous_sum_np, calc_valid_sum, calc_continuous_sum_sliding
import numpy as np
import time
from multiprocessing import Pool, cpu_count
import concurrent.futures
import worker_threads_cy  # 这是你用Cython编译出来的模块
import re

# 全局缩写映射表
abbr_map = {
    'MAX': 'max_value', 'MIN': 'min_value', 'END': 'end_value', 'START': 'start_value',
    'ACT': 'actual_value', 'CLS': 'closest_value', 'NDAYMAX': 'n_days_max_value',
    'NMAXISMAX': 'n_max_is_max', 'RRL': 'range_ratio_is_less', 'CAL': 'continuous_abs_is_less',
    'PDC': 'prev_day_change', 'EDC': 'end_day_change', 'DEV': 'diff_end_value',
    'CR': 'continuous_results', 'CL': 'continuous_len',
    'CSV': 'continuous_start_value', 'CSNV': 'continuous_start_next_value',
    'CSNNV': 'continuous_start_next_next_value', 'CEV': 'continuous_end_value',
    'CEPV': 'continuous_end_prev_value', 'CEPPV': 'continuous_end_prev_prev_value',
    'CASFH': 'continuous_abs_sum_first_half', 'CASSH': 'continuous_abs_sum_second_half',
    'CASB1': 'continuous_abs_sum_block1', 'CASB2': 'continuous_abs_sum_block2',
    'CASB3': 'continuous_abs_sum_block3', 'CASB4': 'continuous_abs_sum_block4',
    'VSA': 'valid_sum_arr', 'VSL': 'valid_sum_len', 'VPS': 'valid_pos_sum', 'VNS': 'valid_neg_sum',
    'VASFH': 'valid_abs_sum_first_half', 'VASSH': 'valid_abs_sum_second_half',
    'VASB1': 'valid_abs_sum_block1', 'VASB2': 'valid_abs_sum_block2',
    'VASB3': 'valid_abs_sum_block3', 'VASB4': 'valid_abs_sum_block4',
    'FMD': 'forward_max_date', 'FMR': 'forward_max_result',
    'FMVSL': 'forward_max_valid_sum_len', 'FMVSA': 'forward_max_valid_sum_arr',
    'FMVPS': 'forward_max_valid_pos_sum', 'FMVNS': 'forward_max_valid_neg_sum',
    'FMVASFH': 'forward_max_valid_abs_sum_first_half', 'FMVASSH': 'forward_max_valid_abs_sum_second_half',
    'FMVASB1': 'forward_max_valid_abs_sum_block1', 'FMVASB2': 'forward_max_valid_abs_sum_block2',
    'FMVASB3': 'forward_max_valid_abs_sum_block3', 'FMVASB4': 'forward_max_valid_abs_sum_block4',
    'FMinD': 'forward_min_date', 'FMinR': 'forward_min_result',
    'FMinVSL': 'forward_min_valid_sum_len', 'FMinVSA': 'forward_min_valid_sum_arr',
    'FMinVPS': 'forward_min_valid_pos_sum', 'FMinVNS': 'forward_min_valid_neg_sum',
    'FMinVASFH': 'forward_min_valid_abs_sum_first_half', 'FMinVASSH': 'forward_min_valid_abs_sum_second_half',
    'FMinVASB1': 'forward_min_valid_abs_sum_block1', 'FMinVASB2': 'forward_min_valid_abs_sum_block2',
    'FMinVASB3': 'forward_min_valid_abs_sum_block3', 'FMinVASB4': 'forward_min_valid_abs_sum_block4',
    'INC': 'increment_value', 'AGE': 'after_gt_end_value', 'AGS': 'after_gt_start_value',
    'OPS': 'ops_value', 'HD': 'hold_days', 'OPC': 'ops_change', 'ADJ': 'adjust_days', 'OIR': 'ops_incre_rate'
}

def split_indices(total, n_parts):
    part_size = (total + n_parts - 1) // n_parts
    # 返回每个分组的起止索引（左闭右开）
    return [(i * part_size, min((i + 1) * part_size, total)) for i in range(n_parts)]

class OpValue:
    def __init__(self, key, value, days):
        self.key = key
        self.value = value
        self.days = days
    def __eq__(self, other):
        # 只要是同一个对象就相等
        return id(self) == id(other)
    def __gt__(self, other):
        return self.value > (other.value if isinstance(other, OpValue) else other)
    def __lt__(self, other):
        return self.value < (other.value if isinstance(other, OpValue) else other)
    def __float__(self):
        return float(self.value)
    def __repr__(self):
        return f"{self.key}({self.value})"

class RowResult:
    __slots__ = [
        'code', 'name', 'max_value', 'min_value', 'end_value', 'start_value',
        'actual_value', 'closest_value', 'continuous_results', 'forward_max_result',
        'forward_min_result', 'forward_max_date', 'forward_min_date', 'n_max_value',
        'n_max_is_max', 'prev_day_change', 'end_day_change', 'diff_end_value',
        'range_ratio_is_less', 'continuous_abs_is_less', 'continuous_start_value',
        'continuous_start_next_value', 'continuous_start_next_next_value',
        'continuous_end_value', 'continuous_end_prev_value', 'continuous_end_prev_prev_value',
        'continuous_len', 'continuous_abs_sum_first_half', 'continuous_abs_sum_second_half',
        'continuous_abs_sum_block1', 'continuous_abs_sum_block2', 'continuous_abs_sum_block3',
        'continuous_abs_sum_block4', 'valid_sum_arr', 'forward_max_valid_sum_arr',
        'forward_min_valid_sum_arr', 'valid_pos_sum', 'valid_neg_sum',
        'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum', 'forward_min_valid_pos_sum',
        'forward_min_valid_neg_sum', 'valid_sum_len', 'valid_abs_sum_first_half',
        'valid_abs_sum_second_half', 'valid_abs_sum_block1', 'valid_abs_sum_block2',
        'valid_abs_sum_block3', 'valid_abs_sum_block4', 'forward_max_valid_sum_len',
        'forward_max_valid_abs_sum_first_half', 'forward_max_valid_abs_sum_second_half',
        'forward_max_valid_abs_sum_block1', 'forward_max_valid_abs_sum_block2',
        'forward_max_valid_abs_sum_block3', 'forward_max_valid_abs_sum_block4',
        'forward_min_valid_sum_len', 'forward_min_valid_abs_sum_first_half',
        'forward_min_valid_abs_sum_second_half', 'forward_min_valid_abs_sum_block1',
        'forward_min_valid_abs_sum_block2', 'forward_min_valid_abs_sum_block3',
        'forward_min_valid_abs_sum_block4', 'increment_value', 'after_gt_end_value',
        'after_gt_start_value', 'ops_value', 'hold_days', 'ops_change',
        'adjust_days', 'ops_incre_rate', 'score'
    ]

    def __init__(self):
        for slot in self.__slots__:
            setattr(self, slot, None)

    def to_dict(self):
        return {slot: getattr(self, slot) for slot in self.__slots__}

class FileLoaderThread(QThread):
    finished = pyqtSignal(object, object, object, list, str)  # df, price_data, diff_data, workdays_str, error_msg

    def __init__(self, file_path, file_type='csv'):
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type

    def run(self):
        try:
            if self.file_type == 'xlsx':
                df = pd.read_excel(self.file_path, dtype=str)
            else:
                df = pd.read_csv(self.file_path, dtype=str)
            
            # 处理数据类型转换
            for col in df.columns:
                if col not in ['代码', '名称']:
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    except Exception:
                        continue
            
            # 只对price_data部分做0.0转为NaN
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
            # 只对price_data做0.0转为NaN
            for col in price_data.columns:
                price_data.loc[price_data[col] == 0.0, col] = np.nan
            diff_data = df.iloc[:, separator_idx+1:]
            diff_data = unify_date_columns(diff_data)
            
            # 对diff_data的数值列进行精度控制
            for col in diff_data.columns:
                diff_data[col] = diff_data[col].round(2)  # 保留两位小数
            
            all_dates = [col for col in price_data.columns if col[:4].isdigit()]
            all_dates = sorted(all_dates)
            self.finished.emit(df, price_data, diff_data, all_dates, "")
        except Exception as e:
            self.finished.emit(None, None, None, [], str(e))

def calculate_one_worker(args):
    price_data, diff_data, params, preprocessed_data = args
    # 使用预处理好的数据
    temp_thread = CalculateThread(price_data, diff_data, [], params)
    temp_thread.preprocessed_data = preprocessed_data  # 传入预处理数据
    return temp_thread.calculate_one(params)

class CalculateThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, price_data, diff_data, workdays_str, params):
        super().__init__()
        self.price_data = price_data
        self.diff_data = diff_data
        self.workdays_str = workdays_str
        self.params = params
        self.prev_continuous_results = {}
        self.prev_start_idx = {}
        self.prev_end_idx = {}
        self.preprocessed_data = None  # 存储预处理数据

    def calculate_one(self, params):
        t0 = time.time()
        end_date = params.get("end_date")
        width = params.get("width")
        start_option = params.get("start_option")
        shift_days = params.get("shift_days")
        is_forward = params.get("is_forward")
        n_days = params.get("n_days", 5)
        expr = params.get("expr", "") or ''
        ops_change_input = params.get("ops_change", 0) * 0.01
        columns = list(self.diff_data.columns)
        end_idx = columns.index(end_date)
        start_idx = end_idx + width
        date_columns = columns[end_idx:start_idx+1]
        all_results = []
        actual_idx = None
        print(f"正在处理 end_date: {end_date}, start_idx: {start_idx}")

        # 统计各类方法总耗时
        maxmin_time_sum = 0
        closest_time_sum = 0
        continuous_time_sum = 0
        valid_time_sum = 0
        inc_time_sum = 0
        other_time_sum = 0

        # 使用预处理数据或进行预处理
        if self.preprocessed_data is None:
            self.preprocessed_data = self.preprocess_data(date_columns)
        
        price_data = self.preprocessed_data['price_data']
        diff_data = self.preprocessed_data['diff_data']
        for idx in range(price_data.shape[0]):
            t1 = time.time()
            row = self.price_data.iloc[idx]
            code = str(row['代码']) if '代码' in row else str(row.iloc[0])
            name = str(row['名称']) if '名称' in row else str(row.iloc[1])
            current_price_data = price_data[idx]
            # 逐点判断有效性，生成有效值索引
            valid_indices = [i for i, v in enumerate(current_price_data) if v is not None and not np.isnan(v)]
            valid_values = [current_price_data[i] for i in valid_indices]
            # 最大/最小值
            t_maxmin = time.time()
            max_value = min_value = max_date = min_date = None
            if len(valid_values) > 0:
                try:
                    max_idx = np.argmax(valid_values)
                    min_idx = np.argmin(valid_values)
                    if 0 <= max_idx < len(valid_values) and 0 <= min_idx < len(valid_values):
                        max_value = valid_values[max_idx]
                        min_value = valid_values[min_idx]
                        if len(valid_indices) > 0:
                            if 0 <= max_idx < len(valid_indices) and 0 <= min_idx < len(valid_indices):
                                max_date = date_columns[valid_indices[max_idx]]
                                min_date = date_columns[valid_indices[min_idx]]
                except Exception as e:
                    print(f"计算最大值最小值时出错: {e}")
                    max_value = min_value = max_date = min_date = None
            maxmin_time_sum += time.time() - t_maxmin

            # 最接近值
            t_closest = time.time()
            end_value = current_price_data[0] if len(current_price_data) > 0 else None
            end_date_val = date_columns[0] if len(date_columns) > 0 else None
            start_value = current_price_data[-1] if len(current_price_data) > 0 else None
            start_date_val = date_columns[-1] if len(date_columns) > 0 else None
            closest_value = None
            closest_date = None
            closest_idx = None
            if end_value is not None and not np.isnan(end_value):
                try:
                    # 逐点判断有效性和日期掩码
                    valid_indices2 = [i for i, v in enumerate(current_price_data) if v is not None and not np.isnan(v) and date_columns[i] != date_columns[0]]
                    if len(valid_indices2) > 0:
                        valid_values2 = [current_price_data[i] for i in valid_indices2]
                        diff = np.abs(np.array(valid_values2) - end_value)
                        min_diff_idx = np.argmin(diff)
                        if 0 <= min_diff_idx < len(valid_indices2):
                            closest_idx = valid_indices2[min_diff_idx]
                            closest_date = date_columns[closest_idx]
                            closest_value = current_price_data[closest_idx]
                except Exception as e:
                    print(f"计算最接近值时出错: {e}")
                    closest_value = closest_date = closest_idx = None
            closest_time_sum += time.time() - t_closest

            # --- NumPy化区间累加 ---
            t_continuous = time.time()
            continuous_results = []
            forward_max_result = []
            forward_min_result = []
            # 只要有实际开始日期和结束日期，直接用NumPy切片
            if end_date in self.diff_data.columns and start_date_val in self.diff_data.columns:
                columns_diff = list(self.diff_data.columns)
                start_idx_diff = columns_diff.index(start_date_val)
                end_idx_diff = columns_diff.index(end_date)
                diff_data_row = diff_data[idx]
                # 用NumPy切片区间
                arr = diff_data_row[start_idx_diff:end_idx_diff+1]
                # 连续累加值（区间和）
                continuous_sum = np.sum(arr)
                # 连续累加序列（区间累加和）
                continuous_results = np.cumsum(arr).tolist()
                # 你可以根据需要保留continuous_sum或continuous_results
                # 滑动窗口缓存逻辑可按需保留
            continuous_time_sum += time.time() - t_continuous

            # 有效累加值
            t_valid = time.time()
            valid_sum_arr = calc_valid_sum(continuous_results)
            valid_time_sum += time.time() - t_valid

            # 递增值等其它主要分支
            t_inc = time.time()
            # ... 递增值等其它逻辑 ...
            inc_time_sum += time.time() - t_inc

            # 其它统计项可继续补充
            other_time_sum += time.time() - t1

            # 根据选项设置base_idx
            if start_option == "最大值":
                base_idx = np.where(current_price_data)[0][max_idx] if len(valid_values) > 0 else None
            elif start_option == "最小值":
                base_idx = np.where(current_price_data)[0][min_idx] if len(valid_values) > 0 else None
            elif start_option == "接近值":
                base_idx = closest_idx if closest_value is not None else None
            else:  # "开始值"
                base_idx = len(current_price_data) - 1 if len(current_price_data) > 0 else None

            actual_idx = base_idx - shift_days if base_idx is not None else None
            
            # 从原始数据中获取actual_date_val
            all_columns = list(self.price_data.columns)
            if actual_idx is not None:
                start_pos = all_columns.index(date_columns[0])
                actual_pos = start_pos + actual_idx
                if 0 <= actual_pos < len(all_columns):
                    actual_date_val = all_columns[actual_pos]
                    actual_value = row[actual_date_val] if actual_date_val in row else None
                else:
                    actual_date_val = None
                    actual_value = None

            t5 = time.time()
            # 计算连续累加值
            continuous_results = []
            forward_max_result = []
            forward_min_result = []
            if actual_date_val and end_date in self.diff_data.columns and actual_date_val in self.diff_data.columns:
                columns_diff = list(self.diff_data.columns)
                start_idx_diff = columns_diff.index(actual_date_val)
                end_idx_diff = columns_diff.index(end_date)
                this_row = self.diff_data.iloc[idx]
                arr = [this_row[d] for d in columns_diff]
                
                # 使用滑动窗口优化计算连续累加值
                continuous_results = calc_continuous_sum_sliding(
                    arr, 
                    start_idx_diff, 
                    end_idx_diff,
                    self.prev_continuous_results.get(idx),
                    self.prev_start_idx.get(idx),
                    self.prev_end_idx.get(idx)
                )
                
                # 保存当前计算结果用于下一次计算
                self.prev_continuous_results[idx] = continuous_results
                self.prev_start_idx[idx] = start_idx_diff
                self.prev_end_idx[idx] = end_idx_diff
                
                # 向前最大/最小连续累加值
                if is_forward and min_date is not None and max_date is not None:
                    min_start_idx = columns_diff.index(min_date)
                    forward_min_result = calc_continuous_sum_sliding(
                        arr,
                        min_start_idx,
                        end_idx_diff,
                        self.prev_continuous_results.get(f"{idx}_min"),
                        self.prev_start_idx.get(f"{idx}_min"),
                        self.prev_end_idx.get(f"{idx}_min")
                    )
                    self.prev_continuous_results[f"{idx}_min"] = forward_min_result
                    self.prev_start_idx[f"{idx}_min"] = min_start_idx
                    self.prev_end_idx[f"{idx}_min"] = end_idx_diff
                            
                    max_start_idx = columns_diff.index(max_date)
                    forward_max_result = calc_continuous_sum_sliding(
                        arr,
                        max_start_idx,
                        end_idx_diff,
                        self.prev_continuous_results.get(f"{idx}_max"),
                        self.prev_start_idx.get(f"{idx}_max"),
                        self.prev_end_idx.get(f"{idx}_max")
                    )
                    self.prev_continuous_results[f"{idx}_max"] = forward_max_result
                    self.prev_start_idx[f"{idx}_max"] = max_start_idx
                    self.prev_end_idx[f"{idx}_max"] = end_idx_diff
                else:
                    forward_max_result = []
                    forward_min_result = []
            continuous_time_sum += time.time() - t5

            t6 = time.time()
            # 前N日最大值
            if n_days == 0:
                n_max_value = end_value  # 直接用结束值
            else:
                # 使用NumPy的向量化操作来处理前N日数据
                n_max_candidates = price_data[idx, :n_days]
                if np.any(~np.isnan(n_max_candidates)):
                    n_max_value = np.max(n_max_candidates[~np.isnan(n_max_candidates)])
                else:
                    n_max_value = None
                
            # 前N最大值是否大于等于区间最大值
            n_max_is_max = None
            if n_max_value is not None and max_value is not None:
                n_max_is_max = n_max_value >= max_value

            t7 = time.time()
            # 前1组结束地址前1日涨跌幅，前1组结束日涨跌幅
            prev_day_change = None
            end_day_change = None
            if len(current_price_data) >= 3:
                # 使用NumPy的向量化操作检查有效性
                valid_prices = ~np.isnan(current_price_data[:3])
                if np.all(valid_prices):
                    try:
                        if current_price_data[2] == 0:
                            prev_day_change = None
                        else:
                            prev_day_change = round(((current_price_data[1] - current_price_data[2]) / current_price_data[2]) * 100, 2)
                    except Exception:
                        prev_day_change = None
                    try:
                        if current_price_data[1] == 0:
                            end_day_change = None
                        else:
                            end_day_change = round(((current_price_data[0] - current_price_data[1]) / current_price_data[1]) * 100, 2)
                    except Exception:
                        end_day_change = None

            t8 = time.time()
            # 获取diff_data中end_date对应的值
            diff_end_value = None
            if end_date in self.diff_data.columns:
                this_row_diff = self.diff_data.iloc[idx]
                diff_end_value = this_row_diff[end_date]
            
            # 读取用户输入的区间比值和绝对值阈值
            range_ratio_is_less = None
            continuous_abs_is_less = None
            try:
                user_range_ratio = float(params.get('range_value', None))
            except Exception:
                user_range_ratio = None
            try:
                user_abs_sum = float(params.get('continuous_abs_threshold', None))
            except Exception:
                user_abs_sum = None
            # 区间最大值/最小值比值判断
            if max_value is not None and min_value is not None and min_value != 0 and user_range_ratio is not None:
                range_ratio_is_less = (max_value / min_value) < user_range_ratio
            # 连续累加值绝对值判断
            if continuous_results and user_abs_sum is not None:
                continuous_abs_is_less = all(abs(v) < user_abs_sum for v in continuous_results if v is not None)

            t9 = time.time()
            # 获取连续累加值开始值、开始后一位值、开始后两位值、连续累加值结束值、结束前一位值、结束前两位值
            continuous_start_value = continuous_results[0] if continuous_results else None
            continuous_start_next_value = continuous_results[1] if len(continuous_results) > 1 else None
            continuous_start_next_next_value = continuous_results[2] if len(continuous_results) > 2 else None
            continuous_end_value = continuous_results[-1] if continuous_results else None
            continuous_end_prev_value = continuous_results[-2] if len(continuous_results) > 1 else None
            continuous_end_prev_prev_value = continuous_results[-3] if len(continuous_results) > 2 else None

            # 连续累加值数组长度、连续累加值数组前一半绝对值之和、连续累加值数组后一半绝对值之和
            continuous_len = len(continuous_results) if continuous_results else None
            if continuous_len is None or continuous_len == 0:
                continuous_abs_sum_first_half = 0
                continuous_abs_sum_second_half = 0
                continuous_abs_sum_block1 = 0
                continuous_abs_sum_block2 = 0
                continuous_abs_sum_block3 = 0
                continuous_abs_sum_block4 = 0
            else:
                # 使用NumPy向量化操作一次性计算所有绝对值
                abs_arr = np.abs(continuous_results)
                n = len(abs_arr)
                half = n // 2
                q1 = n // 4
                q2 = n // 2
                q3 = (3 * n) // 4
                
                # 一次性计算所有分块的和
                continuous_abs_sum_first_half = round(np.sum(abs_arr[:half]), 2)
                continuous_abs_sum_second_half = round(np.sum(abs_arr[half:]), 2)
                continuous_abs_sum_block1 = round(np.sum(abs_arr[:q1]), 2)
                continuous_abs_sum_block2 = round(np.sum(abs_arr[q1:q2]), 2)
                continuous_abs_sum_block3 = round(np.sum(abs_arr[q2:q3]), 2)
                continuous_abs_sum_block4 = round(np.sum(abs_arr[q3:]), 2)

            t10 = time.time()
            # 有效累加值、向前最大有效累加值、向前最小有效累加值
            valid_sum_arr = calc_valid_sum(continuous_results)
            forward_max_valid_sum_arr = calc_valid_sum(forward_max_result)
            forward_min_valid_sum_arr = calc_valid_sum(forward_min_result)

            # 有效累加值正加值和负加值
            def calc_pos_neg_sum(arr):
                if len(arr) == 0:
                    return 0, 0
                arr = np.array(arr)
                # 使用布尔索引一次性计算正负值
                pos_mask = arr > 0
                neg_mask = arr < 0
                pos_sum = round(np.sum(arr[pos_mask]), 2)
                neg_sum = round(np.sum(arr[neg_mask]), 2)
                return pos_sum, neg_sum

            valid_pos_sum, valid_neg_sum = calc_pos_neg_sum(valid_sum_arr)
            forward_max_valid_pos_sum, forward_max_valid_neg_sum = calc_pos_neg_sum(forward_max_valid_sum_arr)
            forward_min_valid_pos_sum, forward_min_valid_neg_sum = calc_pos_neg_sum(forward_min_valid_sum_arr)

            t11 = time.time()
            # 有效累加值数组长度，有效累加值一半绝对值之和、有效累加后一半绝对值之和
            valid_sum_len = len(valid_sum_arr) if valid_sum_arr else None
            if valid_sum_len is not None and valid_sum_len > 0:
                # 使用NumPy向量化操作一次性计算所有绝对值
                abs_arr = np.abs(valid_sum_arr)
                n = len(abs_arr)
                half = n // 2
                q1 = n // 4
                q2 = n // 2
                q3 = (3 * n) // 4
                
                # 一次性计算所有分块的和
                valid_abs_sum_first_half = round(np.sum(abs_arr[:half]), 2)
                valid_abs_sum_second_half = round(np.sum(abs_arr[half:]), 2)
                valid_abs_sum_block1 = round(np.sum(abs_arr[:q1]), 2)
                valid_abs_sum_block2 = round(np.sum(abs_arr[q1:q2]), 2)
                valid_abs_sum_block3 = round(np.sum(abs_arr[q2:q3]), 2)
                valid_abs_sum_block4 = round(np.sum(abs_arr[q3:]), 2)
            else:
                valid_abs_sum_first_half = 0
                valid_abs_sum_second_half = 0
                valid_abs_sum_block1 = 0
                valid_abs_sum_block2 = 0
                valid_abs_sum_block3 = 0
                valid_abs_sum_block4 = 0

            t12 = time.time()
            # 只有勾选了"是否计算向前向后"才计算向前最大/最小相关
            if is_forward:
                # 向前最大有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_max_valid_sum_len = len(forward_max_valid_sum_arr) if forward_max_valid_sum_arr else None
                if forward_max_valid_sum_len is not None and forward_max_valid_sum_len > 0:
                    abs_arr = np.abs(forward_max_valid_sum_arr)
                    half = forward_max_valid_sum_len // 2
                    forward_max_valid_abs_sum_first_half = round(np.sum(abs_arr[:half]), 2)
                    forward_max_valid_abs_sum_second_half = round(np.sum(abs_arr[half:]), 2)
                    
                    # 分四块
                    n = len(abs_arr)
                    q1 = n // 4
                    q2 = n // 2
                    q3 = (3 * n) // 4
                    forward_max_valid_abs_sum_block1 = round(np.sum(abs_arr[:q1]), 2)
                    forward_max_valid_abs_sum_block2 = round(np.sum(abs_arr[q1:q2]), 2)
                    forward_max_valid_abs_sum_block3 = round(np.sum(abs_arr[q2:q3]), 2)
                    forward_max_valid_abs_sum_block4 = round(np.sum(abs_arr[q3:]), 2)
                else:
                    forward_max_valid_abs_sum_first_half = 0
                    forward_max_valid_abs_sum_second_half = 0
                    forward_max_valid_abs_sum_block1 = 0
                    forward_max_valid_abs_sum_block2 = 0
                    forward_max_valid_abs_sum_block3 = 0
                    forward_max_valid_abs_sum_block4 = 0

                # 向前最小有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_min_valid_sum_len = len(forward_min_valid_sum_arr) if forward_min_valid_sum_arr else None
                if forward_min_valid_sum_len is not None and forward_min_valid_sum_len > 0:
                    abs_arr = np.abs(forward_min_valid_sum_arr)
                    half = forward_min_valid_sum_len // 2
                    forward_min_valid_abs_sum_first_half = round(np.sum(abs_arr[:half]), 2)
                    forward_min_valid_abs_sum_second_half = round(np.sum(abs_arr[half:]), 2)
                    
                    # 分四块
                    n = len(abs_arr)
                    q1 = n // 4
                    q2 = n // 2
                    q3 = (3 * n) // 4
                    forward_min_valid_abs_sum_block1 = round(np.sum(abs_arr[:q1]), 2)
                    forward_min_valid_abs_sum_block2 = round(np.sum(abs_arr[q1:q2]), 2)
                    forward_min_valid_abs_sum_block3 = round(np.sum(abs_arr[q2:q3]), 2)
                    forward_min_valid_abs_sum_block4 = round(np.sum(abs_arr[q3:]), 2)
                else:
                    forward_min_valid_abs_sum_first_half = 0
                    forward_min_valid_abs_sum_second_half = 0
                    forward_min_valid_abs_sum_block1 = 0
                    forward_min_valid_abs_sum_block2 = 0
                    forward_min_valid_abs_sum_block3 = 0
                    forward_min_valid_abs_sum_block4 = 0

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
            op_days = int(params.get("op_days", 0))
            inc_rate = float(params.get("inc_rate", 0)) * 0.01
            after_gt_end_ratio = float(params.get("after_gt_end_ratio", 0)) * 0.01
            after_gt_start_ratio = float(params.get("after_gt_start_ratio", 0)) * 0.01
            end_value = full_price_data[end_idx] if end_idx < len(full_price_data) else None

            increment_value = None
            after_gt_end_value = None
            after_gt_start_value = None

            increment_days = None
            after_gt_end_days = None
            after_gt_start_days = None

            after_gt_end_threshold = end_value * after_gt_end_ratio

            start = end_idx
            stop = end_idx - op_days
            n = 1  # 递增天数计数，从1开始

            for i in range(start - 1, stop - 1, -1):
                v = full_price_data[i]
                increment_threshold = end_value * (inc_rate * n)
                # 递增值、后值大于结束值比例、后值大于前值比例
                if v is not None and pd.notna(v):
                    v = float(v)  # 确保v是浮点数
                    # 递增值
                    if increment_threshold != 0:
                        if (v - end_value) > increment_threshold:
                            if increment_value is None:  # 只记录第一个满足条件的值
                                increment_value = v
                                increment_days = start - i
                            n += 1
                    # 后值大于结束值比例
                    if after_gt_end_threshold != 0:
                        if after_gt_end_value is None and (v - end_value) > after_gt_end_threshold:  # 只记录第一个满足条件的值
                            after_gt_end_value = v
                            after_gt_end_days = start - i
                    # 后值大于前值比例
                    if after_gt_start_ratio != 0:
                        prev_v = full_price_data[i+1]
                        if prev_v is not None and pd.notna(prev_v):
                            prev_v = float(prev_v)
                            if after_gt_start_value is None and round(v - prev_v, 2) > round(prev_v * after_gt_start_ratio, 2):  # 只记录第一个满足条件的值
                                after_gt_start_value = v
                                after_gt_start_days = start - i
                        # if (idx == 9):
                        #     print(f"v: {v}, prev_v: {prev_v}, after_gt_start_value: {after_gt_start_value}, (v - prev_v): {round(v - prev_v, 2)}, (prev_v * after_gt_start_ratio): {round(prev_v * after_gt_start_ratio, 2)}")
            # 如果op_days > 0，则从stop开始往前找，找到第一个满足条件的值
            if op_days > 0:
                if increment_value is None:  # 如果循环内没有找到符合条件的值
                    fallback_idx = stop
                    if 0 <= fallback_idx < len(full_price_data):
                        increment_value = full_price_data[fallback_idx]
                        increment_days = start - fallback_idx
                    else:
                        increment_value = None
                        increment_days = None
    
                if after_gt_end_value is None and after_gt_end_ratio > 0:
                    fallback_idx = stop
                    if 0 <= fallback_idx < len(full_price_data):
                        after_gt_end_value = full_price_data[fallback_idx]
                        after_gt_end_days = start - fallback_idx
                    else:
                        after_gt_end_value = None
                        after_gt_end_days = None

                if after_gt_start_value is None and after_gt_start_ratio > 0:
                    fallback_idx = stop
                    if 0 <= fallback_idx < len(full_price_data):
                        after_gt_start_value = full_price_data[fallback_idx]
                        after_gt_start_days = start - fallback_idx
                    else:
                        after_gt_start_value = None
                        after_gt_start_days = None

            # if idx == 9:
            #     print(f"increment_value: {increment_value}")
            #     print(f"increment_days: {increment_days}, after_gt_end_days: {after_gt_end_days}, after_gt_start_days: {after_gt_start_days}")

            ops_value = None
            hold_days = None
            INC = OpValue('INC', increment_value, increment_days)
            AGE = OpValue('AGE', after_gt_end_value, after_gt_end_days)
            AGS = OpValue('AGS', after_gt_start_value, after_gt_start_days)
            local_vars = {'INC': INC, 'AGE': AGE, 'AGS': AGS, 'result': None}
            try:
                exec(expr, {}, local_vars)
                ops_obj = local_vars['result']
                if isinstance(ops_obj, OpValue):
                    ops_key = ops_obj.key
                    ops_value = ops_obj.value
                    hold_days = ops_obj.days
                else:
                    ops_key = None
                    ops_value = ops_obj
                    hold_days = None
            except Exception as e:
                ops_value = None
                hold_days = None
                print("表达式错误：", e)
            
            # 计算操作涨幅
            if ops_value is not None and end_value not in (None, 0):
                ops_change = round((ops_value - end_value) / end_value * 100, 2)  # 百分比
            else:
                ops_change = None
            adjust_days = None
            if ops_change_input != 0 and ops_change is not None:
                if ops_change > ops_change_input and hold_days == 1:
                    adjust_days = op_days / 3
                else:
                    adjust_days = hold_days + 1

            ops_incre_rate = None
            if adjust_days is not None:
                ops_incre_rate = round(ops_change / adjust_days, 2)

            # 使用RowResult替代字典
            row_result = RowResult()
            row_result.code = code
            row_result.name = name
            row_result.max_value = [max_date, max_value]
            row_result.min_value = [min_date, min_value]
            row_result.end_value = [end_date_val, end_value]
            row_result.start_value = [start_date_val, start_value]
            row_result.actual_value = [actual_date_val, actual_value]
            row_result.closest_value = [closest_date, closest_value]
            row_result.continuous_results = continuous_results
            row_result.forward_max_result = forward_max_result
            row_result.forward_min_result = forward_min_result
            row_result.forward_max_date = max_date
            row_result.forward_min_date = min_date
            row_result.n_max_value = n_max_value
            row_result.n_max_is_max = n_max_is_max
            row_result.prev_day_change = prev_day_change
            row_result.end_day_change = end_day_change
            row_result.diff_end_value = diff_end_value
            row_result.range_ratio_is_less = range_ratio_is_less
            row_result.continuous_abs_is_less = continuous_abs_is_less
            row_result.continuous_start_value = continuous_start_value
            row_result.continuous_start_next_value = continuous_start_next_value
            row_result.continuous_start_next_next_value = continuous_start_next_next_value
            row_result.continuous_end_value = continuous_end_value
            row_result.continuous_end_prev_value = continuous_end_prev_value
            row_result.continuous_end_prev_prev_value = continuous_end_prev_prev_value
            row_result.continuous_len = continuous_len
            row_result.continuous_abs_sum_first_half = continuous_abs_sum_first_half
            row_result.continuous_abs_sum_second_half = continuous_abs_sum_second_half
            row_result.continuous_abs_sum_block1 = continuous_abs_sum_block1
            row_result.continuous_abs_sum_block2 = continuous_abs_sum_block2
            row_result.continuous_abs_sum_block3 = continuous_abs_sum_block3
            row_result.continuous_abs_sum_block4 = continuous_abs_sum_block4
            row_result.valid_sum_arr = valid_sum_arr
            row_result.forward_max_valid_sum_arr = forward_max_valid_sum_arr
            row_result.forward_min_valid_sum_arr = forward_min_valid_sum_arr
            row_result.valid_pos_sum = valid_pos_sum
            row_result.valid_neg_sum = valid_neg_sum
            row_result.forward_max_valid_pos_sum = forward_max_valid_pos_sum
            row_result.forward_max_valid_neg_sum = forward_max_valid_neg_sum
            row_result.forward_min_valid_pos_sum = forward_min_valid_pos_sum
            row_result.forward_min_valid_neg_sum = forward_min_valid_neg_sum
            row_result.valid_sum_len = valid_sum_len
            row_result.valid_abs_sum_first_half = valid_abs_sum_first_half
            row_result.valid_abs_sum_second_half = valid_abs_sum_second_half
            row_result.valid_abs_sum_block1 = valid_abs_sum_block1
            row_result.valid_abs_sum_block2 = valid_abs_sum_block2
            row_result.valid_abs_sum_block3 = valid_abs_sum_block3
            row_result.valid_abs_sum_block4 = valid_abs_sum_block4
            row_result.forward_max_valid_sum_len = forward_max_valid_sum_len
            row_result.forward_max_valid_abs_sum_first_half = forward_max_valid_abs_sum_first_half
            row_result.forward_max_valid_abs_sum_second_half = forward_max_valid_abs_sum_second_half
            row_result.forward_max_valid_abs_sum_block1 = forward_max_valid_abs_sum_block1
            row_result.forward_max_valid_abs_sum_block2 = forward_max_valid_abs_sum_block2
            row_result.forward_max_valid_abs_sum_block3 = forward_max_valid_abs_sum_block3
            row_result.forward_max_valid_abs_sum_block4 = forward_max_valid_abs_sum_block4
            row_result.forward_min_valid_sum_len = forward_min_valid_sum_len
            row_result.forward_min_valid_abs_sum_first_half = forward_min_valid_abs_sum_first_half
            row_result.forward_min_valid_abs_sum_second_half = forward_min_valid_abs_sum_second_half
            row_result.forward_min_valid_abs_sum_block1 = forward_min_valid_abs_sum_block1
            row_result.forward_min_valid_abs_sum_block2 = forward_min_valid_abs_sum_block2
            row_result.forward_min_valid_abs_sum_block3 = forward_min_valid_abs_sum_block3
            row_result.forward_min_valid_abs_sum_block4 = forward_min_valid_abs_sum_block4
            row_result.increment_value = increment_value
            row_result.after_gt_end_value = after_gt_end_value
            row_result.after_gt_start_value = after_gt_start_value
            row_result.ops_value = ops_value
            row_result.hold_days = hold_days
            row_result.ops_change = ops_change
            row_result.adjust_days = adjust_days
            row_result.ops_incre_rate = ops_incre_rate
            
            all_results.append(row_result)

        result = {
            "rows": [r.to_dict() for r in all_results],
            "shift_days": shift_days,
            "is_forward": is_forward,
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
            "base_idx": actual_idx,
        }

        print(f"最大/最小值总耗时: {maxmin_time_sum:.4f}秒")
        print(f"最接近值总耗时: {closest_time_sum:.4f}秒")
        print(f"连续累加值总耗时: {continuous_time_sum:.4f}秒")
        print(f"有效累加值总耗时: {valid_time_sum:.4f}秒")
        print(f"递增值等其它分支总耗时: {inc_time_sum:.4f}秒")
        print(f"其它总耗时(含循环体): {other_time_sum:.4f}秒")
        print(f"单次calculate_one总耗时: {time.time() - t0:.4f}秒")

        return result

    def calculate_batch(self, params):
        columns = list(self.diff_data.columns)
        date_columns = list(self.price_data.columns[2:])
        width = params.get("width")   #日期宽度
        start_option = params.get("start_option")  #开始日期选项
        shift_days = params.get("shift_days")  #偏移天数
        is_forward = params.get("is_forward", False)  # 是否计算向前
        n_days = params.get("n_days", 0)  # 前N日
        range_value = params.get('range_value', None)
        user_range_ratio = self.safe_float(range_value)
        continuous_abs_threshold = self.safe_float(params.get('continuous_abs_threshold', None))
        # 自动分析 结束日期开始到结束日期结束
        end_date_start = "2023-11-17"
        # end_date_start = "2025-04-30"
        end_date_end = "2025-04-30"
        end_date_start_idx = date_columns.index(end_date_start)
        end_date_end_idx = date_columns.index(end_date_end)
        print(f"end_date_start: {end_date_start}, end_date_end: {end_date_end}, end_date_start_idx: {end_date_start_idx}, end_date_end_idx: {end_date_end_idx}")
        # 数据准备：转为NumPy数组
        price_data_np = self.price_data.iloc[:, 2:].values.astype(np.float64)
        diff_data_np = self.diff_data.values.astype(np.float64)  # 不要去掉前两列
        # 调用Cython加速方法
        t0 = time.time()
        n_days_max = params.get("n_days_max", 0)
        op_days = int(params.get('op_days', 0))
        inc_rate = float(params.get('inc_rate', 0)) * 0.01
        after_gt_end_ratio = float(params.get('after_gt_end_ratio', 0)) * 0.01
        after_gt_start_ratio = float(params.get('after_gt_start_ratio', 0)) * 0.01
        expr = params.get('expr', '') or ''
        ops_change_input = params.get("ops_change", 0)
        formula_expr = params.get('formula_expr', '') or ''
        formula_expr = replace_abbr(formula_expr, abbr_map)
        all_results = worker_threads_cy.calculate_batch_cy(
            price_data_np, date_columns, width, start_option, shift_days, end_date_start_idx, end_date_end_idx,
            diff_data_np, np.arange(price_data_np.shape[0], dtype=np.int32), is_forward, n_days, user_range_ratio, continuous_abs_threshold, n_days_max, op_days, inc_rate, after_gt_end_ratio, after_gt_start_ratio, expr, ops_change_input, formula_expr
        )
        t1 = time.time()
        print(f"calculate_batch_cy 总耗时: {t1 - t0:.4f}秒")
        result = {
            "dates": all_results,  # 现在all_results是按日期分组的数组
            "shift_days": shift_days,
            "is_forward": params.get("is_forward"),
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
            "base_idx": None,
        }
        return result

    def safe_float(self, val, default=float('nan')):
        try:
            if val is None or (isinstance(val, str) and val.strip() == ''):
                return default
            return float(val)
        except Exception:
            return default

    def expr_to_tuple(self, expr, abbr_map):
        # 1. 缩写转全名
        for abbr, full in abbr_map.items():
            expr = re.sub(rf'\b{abbr}\b', full, expr)
        # 2. 自动将 result = xxx 替换为 result = (xxx, xxx_days)
        for full in abbr_map.values():
            expr = re.sub(
                rf'result\s*=\s*{full}\b',
                f'result = ({full}, {full.replace("value", "days")})',
                expr
            )
        return expr

    def calculate_batch_16_cores(self, params):
        columns = list(self.diff_data.columns)
        date_columns = list(self.price_data.columns[2:])
        width = params.get("width")
        start_option = params.get("start_option")
        shift_days = params.get("shift_days")
        is_forward = params.get("is_forward", False)  # 是否计算向前
        n_days = params.get("n_days", 0)  # 前N日
        range_value = params.get('range_value', None)
        user_range_ratio = self.safe_float(range_value)
        continuous_abs_threshold = self.safe_float(params.get('continuous_abs_threshold', None))
        end_date_start = params.get('end_date_start', "2025-04-30")
        end_date_end = params.get('end_date_end', "2025-04-30")
        print(f"end_date_start: {end_date_start}, end_date_end: {end_date_end}")
        end_date_start_idx = date_columns.index(end_date_start)
        end_date_end_idx = date_columns.index(end_date_end)
        price_data_np = self.price_data.iloc[:, 2:].values.astype(np.float64)
        diff_data_np = self.diff_data.values.astype(np.float64)
        num_stocks = price_data_np.shape[0]
        n_proc = 16
        # n_proc = 1
        stock_idx_arr = np.arange(num_stocks, dtype=np.int32)
        stock_idx_ranges = split_indices(num_stocks, n_proc)
        n_days_max = params.get("n_days_max", 0)
        op_days = int(params.get('op_days', 0))
        inc_rate = float(params.get('inc_rate', 0)) * 0.01
        after_gt_end_ratio = float(params.get('after_gt_end_ratio', 0)) * 0.01
        after_gt_start_ratio = float(params.get('after_gt_start_ratio', 0)) * 0.01
        expr = params.get('expr', '') or ''
        expr = convert_expr_to_return_var_name(expr)
        formula_expr = params.get('formula_expr', '') or ''
        formula_expr = replace_abbr(formula_expr, abbr_map)
        ops_change_input = params.get("ops_change", 0)
        select_count = int(params.get('select_count', 10))
        sort_mode = params.get('sort_mode', '最大值排序')
        only_show_selected = params.get('only_show_selected', False)
        args_list = [
            (
                price_data_np,
                date_columns,
                width,
                start_option,
                shift_days,
                end_date_start_idx,
                end_date_end_idx,
                diff_data_np,
                np.ascontiguousarray(stock_idx_arr[start:end], dtype=np.int32),
                is_forward,
                n_days,
                user_range_ratio,
                continuous_abs_threshold,
                n_days_max,
                op_days,
                inc_rate,
                after_gt_end_ratio,
                after_gt_start_ratio,
                expr,
                ops_change_input,
                formula_expr,
                select_count,
                sort_mode,
                only_show_selected
            )
            for (start, end) in stock_idx_ranges if end > start
        ]
        t0 = time.time()
        merged_results = {}
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            end_date = date_columns[idx]
            merged_results[end_date] = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=n_proc) as executor:
            futures = [executor.submit(cy_batch_worker, args) for args in args_list]
            for fut in concurrent.futures.as_completed(futures):
                process_results = fut.result()
                for end_date, stocks in process_results.items():
                    if end_date in merged_results:
                        merged_results[end_date].extend(stocks)
        
        t1 = time.time()
        print(f"calculate_batch_{n_proc}_cores 总耗时: {t1 - t0:.4f}秒")
        if only_show_selected:
            for end_date in merged_results:
                merged_results[end_date] = sorted(
                    merged_results[end_date],
                    key=lambda x: x['score'],
                    reverse=(sort_mode == "最大值排序")
                )[:select_count]
        
        result = {
            "dates": merged_results,
            "shift_days": shift_days,
            "is_forward": params.get("is_forward"),
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
            "base_idx": None,
        }
        return result

    def calculate_py_version(self, params):
        columns = list(self.diff_data.columns)
        date_columns = list(self.price_data.columns[2:])
        width = params.get("width")
        start_option = params.get("start_option")
        shift_days = params.get("shift_days")
        # end_date_start = "2023-11-17"
        end_date_start = "2025-04-30"
        end_date_end = "2025-04-30"
        end_date_start_idx = date_columns.index(end_date_start)
        end_date_end_idx = date_columns.index(end_date_end)
        price_data_np = self.price_data.iloc[:, 2:].values.astype(np.float64)
        diff_data_np = self.diff_data.values.astype(np.float64)  # 不要去掉前两列
        num_stocks = price_data_np.shape[0]
        num_dates = price_data_np.shape[1]
        all_results = []
        t0 = time.time()
        for stock_idx in range(num_stocks):
            for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
                end_date_idx = idx
                end_date = date_columns[end_date_idx]
                start_date_idx = end_date_idx + width
                if stock_idx == 0:
                    print(f"end_date_idx: {end_date_idx}, start_date_idx: {start_date_idx}")
                start_date = date_columns[start_date_idx]
                price_slice = price_data_np[stock_idx, end_date_idx:start_date_idx+1]
                window_len = price_slice.shape[0]
                if window_len == 0 or np.isnan(price_slice).all():
                    max_price = min_price = np.nan
                    max_idx_in_window = min_idx_in_window = -1
                else:
                    max_price = np.nanmax(price_slice)
                    min_price = np.nanmin(price_slice)
                    max_idx_in_window = int(np.where(price_slice == max_price)[0][0])
                    min_idx_in_window = int(np.where(price_slice == min_price)[0][0])
                end_value = price_data_np[stock_idx, end_date_idx]
                start_value = price_data_np[stock_idx, start_date_idx]
                # 最接近值
                if np.isnan(end_value):
                    closest_value = np.nan
                    closest_idx_in_window = -1
                else:
                    mask = ~np.isnan(price_slice)
                    if mask.sum() > 0:
                        diffs = np.abs(price_slice[mask] - end_value)
                        min_idx = np.argmin(diffs)
                        valid_indices = np.where(mask)[0]
                        closest_value = price_slice[mask][min_idx]
                        closest_idx_in_window = int(valid_indices[min_idx])
                    else:
                        closest_value = np.nan
                        closest_idx_in_window = -1
                # 实际开始值索引
                if start_option == "最大值":
                    base_idx = end_date_idx + max_idx_in_window if max_idx_in_window >= 0 else -1
                elif start_option == "最小值":
                    base_idx = end_date_idx + min_idx_in_window if min_idx_in_window >= 0 else -1
                elif start_option == "接近值":
                    base_idx = end_date_idx + closest_idx_in_window if closest_idx_in_window >= 0 else -1
                else:
                    base_idx = start_date_idx
                actual_idx = base_idx - shift_days if base_idx >= 0 else -1
                actual_value = price_data_np[stock_idx, actual_idx] if actual_idx >= 0 and actual_idx < num_dates else np.nan
                # 计算diff_data的连续累加值
                continuous_results = calc_continuous_sum_sliding(
                    arr=diff_data_np[stock_idx],  # 传入完整的diff_data行数据
                    start_idx=actual_idx,         # 实际开始索引
                    end_idx=end_date_idx,       # 结束索引
                    prev_result=self.prev_continuous_results.get(stock_idx),  # 获取上一次的结果
                    prev_start_idx=self.prev_start_idx.get(stock_idx),       # 获取上一次的开始索引
                    prev_end_idx=self.prev_end_idx.get(stock_idx)            # 获取上一次的结束索引
                )
                # print(f"stock_idx: {stock_idx}, continuous_results: {continuous_results}")
                
                # 保存当前计算结果用于下一次计算
                self.prev_continuous_results[stock_idx] = continuous_results
                self.prev_start_idx[stock_idx] = actual_idx
                self.prev_end_idx[stock_idx] = end_date_idx-1
                
                row_result = {
                    'stock_idx': stock_idx,
                    'code': self.price_data.iloc[stock_idx, 0],
                    'name': self.price_data.iloc[stock_idx, 1],
                    'max_value': [date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None, max_price],
                    'min_value': [date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None, min_price],
                    'end_value': [end_date, end_value],
                    'start_value': [start_date, start_value],
                    'actual_value': [date_columns[actual_idx] if actual_idx >= 0 and actual_idx < num_dates else None, actual_value],
                    'closest_value': [date_columns[end_date_idx + closest_idx_in_window] if closest_idx_in_window >= 0 else None, closest_value],
                    'continuous_results': continuous_results,
                }
                all_results.append(row_result)
        t1 = time.time()
        print(f"calculate_py_version 总耗时: {t1 - t0:.4f}秒")
        result = {
            "rows": all_results,
            "shift_days": shift_days,
            "is_forward": params.get("is_forward"),
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
            "base_idx": None,
        }
        return result

class SelectStockThread(QThread):
    finished = pyqtSignal(list)
    def __init__(self, all_results, formula_expr, select_count, sort_mode):
        super().__init__()
        self.all_results = all_results
        self.formula_expr = formula_expr
        self.select_count = select_count
        self.sort_mode = sort_mode  # '最大值排序' or '最小值排序'

    def run(self):
        import re
        # 替换公式中的缩写为原参数名
        expr = self.formula_expr
        for abbr, full in abbr_map.items():
            expr = re.sub(r'\b' + abbr + r'\b', full, expr)
        results = []
        for row in self.all_results:
            local_vars = dict(row)
            print_flag = False
            if print_flag:
                print(f"[SelectStockThread] local_vars: {local_vars}")
            # 只对极少数元组参数自动取数值
            for k in ['max_value', 'min_value', 'end_value', 'start_value', 'actual_value', 'closest_value']:
                v = local_vars.get(k)
                if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[1], (int, float)):
                    local_vars[k] = v[1]
            if print_flag:
                print(f"[SelectStockThread] eval expr: {expr}")
            try:
                exec(expr, {}, local_vars)
                score = round(local_vars.get('result', 0), 2)
            except Exception as e:
                if print_flag:
                    print(f"[SelectStockThread] eval error: {e}")
                score = float('-inf') if self.sort_mode == '最大值排序' else float('inf')
            if score is not None and score != float('inf') and score != float('-inf') and score != 0:
                results.append({'code': row.get('code', ''), 'name': row.get('name', ''), 'hold_days': row.get('hold_days', ''), 'ops_change': row.get('ops_change', ''), 'ops_incre_rate': row.get('ops_incre_rate', ''), 'score': score})
            print_flag = True
        reverse = self.sort_mode == '最大值排序'
        results.sort(key=lambda x: x['score'], reverse=reverse)
        selected = results[:self.select_count]
        print(f"[SelectStockThread] selected: {selected}")
        self.finished.emit(selected)
        
def convert_expr_to_return_var_name(expr):
    """把返回变量的表达式转换成返回变量名的表达式
    例如：
    if INC > 10:
        result = INC
    转换成：
    if INC > 10:
        result = 'increment_value'
    """
    lines = expr.split('\n')
    new_lines = []
    for line in lines:
        if 'result =' in line:
            var = line.split('=')[1].strip()
            if var == 'INC':
                new_lines.append("    result = 'increment_value'")
            elif var == 'AGE':
                new_lines.append("    result = 'after_gt_end_value'")
            elif var == 'AGS':
                new_lines.append("    result = 'after_gt_start_value'")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)

def make_user_func(expr):
    # 预处理表达式，把返回变量的表达式转换成返回变量名的表达式
    expr = convert_expr_to_return_var_name(expr)
    def user_func(INC, AGE, AGS):
        # 动态执行表达式
        local_vars = {
            'INC': INC,
            'AGE': AGE,
            'AGS': AGS,
            'increment_value': INC,
            'after_gt_end_value': AGE,
            'after_gt_start_value': AGS
        }
        exec(expr, {}, local_vars)
        return local_vars.get('result', None)  # 直接返回表达式的结果，不做值判断
    return user_func

def cy_batch_worker(args):
    import worker_threads_cy
    price_data_np, date_columns, width, start_option, shift_days, end_date_start_idx, end_date_end_idx, diff_data_np, stock_idx_arr, is_forward, n_days, user_range_ratio, continuous_abs_threshold, n_days_max, op_days, inc_rate, after_gt_end_ratio, after_gt_start_ratio, expr, ops_change_input, formula_expr, select_count, sort_mode, only_show_selected = args
    stock_idx_arr = np.ascontiguousarray(stock_idx_arr, dtype=np.int32)
    date_grouped_results = worker_threads_cy.calculate_batch_cy(
        price_data_np, date_columns, width, start_option, shift_days, end_date_start_idx, end_date_end_idx, diff_data_np, stock_idx_arr, is_forward, n_days, user_range_ratio, continuous_abs_threshold, n_days_max, op_days, inc_rate, after_gt_end_ratio, after_gt_start_ratio, expr, ops_change_input, formula_expr, select_count, sort_mode, only_show_selected
    )
    return date_grouped_results

def replace_abbr(expr, abbr_map):
    for abbr, full in abbr_map.items():
        expr = re.sub(rf'\b{abbr}\b', full, expr)
    return expr

def split_indices(total, n_parts):
    part_size = (total + n_parts - 1) // n_parts
    # 返回每个分组的起止索引（左闭右开）
    return [(i * part_size, min((i + 1) * part_size, total)) for i in range(n_parts)]
