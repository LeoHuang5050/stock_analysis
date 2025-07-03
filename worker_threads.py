import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns
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
    'OPS': 'ops_value', 'HD': 'hold_days', 'OPC': 'ops_change', 'ADJ': 'adjust_days', 'OIR': 'ops_incre_rate',
    'FMaxCV': 'forward_max_continuous_start_value', 'FMaxCNV': 'forward_max_continuous_start_next_value',
    'FMaxCNNV': 'forward_max_continuous_start_next_next_value', 'FMaxCEV': 'forward_max_continuous_end_value',
    'FMaxCEPV': 'forward_max_continuous_end_prev_value', 'FMaxCEPPV': 'forward_max_continuous_end_prev_prev_value',
    'FMinCV': 'forward_min_continuous_start_value', 'FMinCNV': 'forward_min_continuous_start_next_value',
    'FMinCNNV': 'forward_min_continuous_start_next_next_value', 'FMinCEV': 'forward_min_continuous_end_value',
    'FMinCEPV': 'forward_min_continuous_end_prev_value', 'FMinCEPPV': 'forward_min_continuous_end_prev_prev_value',
    'FMaxCASFH': 'forward_max_continuous_abs_sum_first_half', 'FMaxCASSH': 'forward_max_continuous_abs_sum_second_half',
    'FMaxCASB1': 'forward_max_continuous_abs_sum_block1', 'FMaxCASB2': 'forward_max_continuous_abs_sum_block2',
    'FMaxCASB3': 'forward_max_continuous_abs_sum_block3', 'FMaxCASB4': 'forward_max_continuous_abs_sum_block4',
    'FMinCASFH': 'forward_min_continuous_abs_sum_first_half', 'FMinCASSH': 'forward_min_continuous_abs_sum_second_half',
    'FMinCASB1': 'forward_min_continuous_abs_sum_block1', 'FMinCASB2': 'forward_min_continuous_abs_sum_block2',
    'FMinCASB3': 'forward_min_continuous_abs_sum_block3', 'FMinCASB4': 'forward_min_continuous_abs_sum_block4',
    'EDV': 'end_value',
    'FMaxLen': 'forward_max_result_len',
    'FMinLen': 'forward_min_result_len'
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
        trade_t1_mode = params.get('trade_mode', 'T+1') == 'T+1'

        stock_idx_arr = np.arange(num_stocks, dtype=np.int32)
        n_days_max = params.get("n_days_max", 0)
        op_days = int(params.get('op_days', 0))
        inc_rate = float(params.get('inc_rate', 0)) * 0.01
        after_gt_end_ratio = float(params.get('after_gt_end_ratio', 0)) * 0.01
        after_gt_start_ratio = float(params.get('after_gt_start_ratio', 0)) * 0.01
        stop_loss_inc_rate = float(params.get('stop_loss_inc_rate', 0)) * 0.01
        stop_loss_after_gt_end_ratio = float(params.get('stop_loss_after_gt_end_ratio', 0)) * 0.01
        stop_loss_after_gt_start_ratio = float(params.get('stop_loss_after_gt_start_ratio', 0)) * 0.01
        expr = params.get('expr', '') or ''
        expr = convert_expr_to_return_var_name(expr)
        formula_expr = params.get('formula_expr', '') or ''
        # formula_expr = replace_abbr(formula_expr, abbr_map)
        ops_change_input = params.get("ops_change", 0)
        select_count = int(params.get('select_count', 10))
        sort_mode = params.get('sort_mode', '最大值排序')
        only_show_selected = params.get('only_show_selected', False)
        max_cores = params.get('max_cores', 1)  # 从参数中获取最大核心数
        
        if only_show_selected:
            n_proc = max_cores  # 使用UI中设置的核心数
        else:
            n_proc = 1

        # 新增：创新高/创新低相关参数
        new_before_high_start = int(params.get('new_before_high_start', 0))
        new_before_high_range = int(params.get('new_before_high_range', 0))
        new_before_high_span = int(params.get('new_before_high_span', 0))
        new_before_high_logic = params.get('new_before_high_logic', '与')
        
        # 新增：创前新高2相关参数
        new_before_high2_start = int(params.get('new_before_high2_start', 0))
        new_before_high2_range = int(params.get('new_before_high2_range', 0))
        new_before_high2_span = int(params.get('new_before_high2_span', 0))
        new_before_high2_logic = params.get('new_before_high2_logic', '与')

        # 新增：创后新高1相关参数
        new_after_high_start = int(params.get('new_after_high_start', 0))
        new_after_high_range = int(params.get('new_after_high_range', 0))
        new_after_high_span = int(params.get('new_after_high_span', 0))
        new_after_high_logic = params.get('new_after_high_logic', '与')
        
        # 新增：创后新高2相关参数
        new_after_high2_start = int(params.get('new_after_high2_start', 0))
        new_after_high2_range = int(params.get('new_after_high2_range', 0))
        new_after_high2_span = int(params.get('new_after_high2_span', 0))
        new_after_high2_logic = params.get('new_after_high2_logic', '与')

        # 新增：创前新低1相关参数
        new_before_low_start = int(params.get('new_before_low_start', 0))
        new_before_low_range = int(params.get('new_before_low_range', 0))
        new_before_low_span = int(params.get('new_before_low_span', 0))
        new_before_low_logic = params.get('new_before_low_logic', '与')
        
        # 新增：创前新低2相关参数
        new_before_low2_start = int(params.get('new_before_low2_start', 0))
        new_before_low2_range = int(params.get('new_before_low2_range', 0))
        new_before_low2_span = int(params.get('new_before_low2_span', 0))
        new_before_low2_logic = params.get('new_before_low2_logic', '与')
        
        # 新增：创后新低1相关参数
        new_after_low_start = int(params.get('new_after_low_start', 0))
        new_after_low_range = int(params.get('new_after_low_range', 0))
        new_after_low_span = int(params.get('new_after_low_span', 0))
        new_after_low_logic = params.get('new_after_low_logic', '与')
        
        # 新增：创后新低2相关参数
        new_after_low2_start = int(params.get('new_after_low2_start', 0))
        new_after_low2_range = int(params.get('new_after_low2_range', 0))
        new_after_low2_span = int(params.get('new_after_low2_span', 0))
        new_after_low2_logic = params.get('new_after_low2_logic', '与')

        stock_idx_ranges = split_indices(num_stocks, n_proc)
        # n_proc = 1
        # 新增：创新高/创新低逻辑控件布尔参数
        start_with_new_before_high_flag = params.get('start_with_new_before_high_flag', False)
        start_with_new_before_high2_flag = params.get('start_with_new_before_high2_flag', False)
        start_with_new_after_high_flag = params.get('start_with_new_after_high_flag', False)
        start_with_new_after_high2_flag = params.get('start_with_new_after_high2_flag', False)
        start_with_new_before_low_flag = params.get('start_with_new_before_low_flag', False)
        start_with_new_before_low2_flag = params.get('start_with_new_before_low2_flag', False)
        start_with_new_after_low_flag = params.get('start_with_new_after_low_flag', False)
        start_with_new_after_low2_flag = params.get('start_with_new_after_low2_flag', False)
        valid_abs_sum_threshold = self.safe_float(params.get('valid_abs_sum_threshold', None))
        new_before_high_logic = params.get('new_before_high_logic', '与')
        comparison_vars = params.get('comparison_vars', [])
        
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
                valid_abs_sum_threshold,
                n_days_max,
                op_days,
                inc_rate,
                after_gt_end_ratio,
                after_gt_start_ratio,
                stop_loss_inc_rate,
                stop_loss_after_gt_end_ratio,
                stop_loss_after_gt_start_ratio,
                expr,
                ops_change_input,
                formula_expr,
                select_count,
                sort_mode,
                trade_t1_mode,
                only_show_selected,
                new_before_high_start,
                new_before_high_range,
                new_before_high_span,
                new_before_high_logic,
                new_before_high2_start,
                new_before_high2_range,
                new_before_high2_span,
                new_before_high2_logic,
                new_after_high_start,
                new_after_high_range,
                new_after_high_span,
                new_after_high_logic,
                new_after_high2_start,
                new_after_high2_range,
                new_after_high2_span,
                new_after_high2_logic,
                new_before_low_start,
                new_before_low_range,
                new_before_low_span,
                new_before_low_logic,
                new_before_low2_start,
                new_before_low2_range,
                new_before_low2_span,
                new_before_low2_logic,
                new_after_low_start,
                new_after_low_range,
                new_after_low_span,
                new_after_low_logic,
                new_after_low2_start,
                new_after_low2_range,
                new_after_low2_span,
                new_after_low2_logic,
                start_with_new_before_high_flag,
                start_with_new_before_high2_flag,
                start_with_new_after_high_flag,
                start_with_new_after_high2_flag,
                start_with_new_before_low_flag,
                start_with_new_before_low2_flag,
                start_with_new_after_low_flag,
                start_with_new_after_low2_flag,
                comparison_vars,  # 添加比较变量列表
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
                try:
                    process_results = fut.result()
                    for end_date, stocks in process_results.items():
                        if end_date in merged_results:
                            merged_results[end_date].extend(stocks)
                except Exception as e:
                    print(f"子进程异常: {e}")
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
        # 移除行首的空白字符
        stripped_line = line.lstrip()
        # 检查是否是result赋值语句
        if stripped_line.startswith('result ='):
            # 获取等号后面的值，并移除所有空白字符
            var = stripped_line.split('=')[1].strip()
            # 保持原始缩进
            indent = line[:len(line) - len(stripped_line)]
            if var == 'INC':
                new_lines.append(f"{indent}result = 'increment_value'")
            elif var == 'AGE':
                new_lines.append(f"{indent}result = 'after_gt_end_value'")
            elif var == 'AGS':
                new_lines.append(f"{indent}result = 'after_gt_start_value'")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    result = '\n'.join(new_lines)
    return result

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
    (
        price_data_np, 
        date_columns, 
        width, 
        start_option, 
        shift_days, 
        end_date_start_idx, 
        end_date_end_idx, 
        diff_data_np, 
        stock_idx_arr, 
        is_forward, 
        n_days, 
        user_range_ratio, 
        continuous_abs_threshold, 
        valid_abs_sum_threshold, 
        n_days_max, 
        op_days, 
        inc_rate, 
        after_gt_end_ratio, 
        after_gt_start_ratio, 
        stop_loss_inc_rate,
        stop_loss_after_gt_end_ratio,
        stop_loss_after_gt_start_ratio,
        expr, 
        ops_change_input, 
        formula_expr, 
        select_count, 
        sort_mode, 
        trade_t1_mode,
        only_show_selected, 
        new_before_high_start, 
        new_before_high_range, 
        new_before_high_span, 
        new_before_high_logic, 
        new_before_high2_start, 
        new_before_high2_range, 
        new_before_high2_span, 
        new_before_high2_logic, 
        new_after_high_start, 
        new_after_high_range, 
        new_after_high_span, 
        new_after_high_logic, 
        new_after_high2_start, 
        new_after_high2_range, 
        new_after_high2_span, 
        new_after_high2_logic,
        new_before_low_start,
        new_before_low_range,
        new_before_low_span,
        new_before_low_logic,
        new_before_low2_start,
        new_before_low2_range,
        new_before_low2_span,
        new_before_low2_logic,
        new_after_low_start,
        new_after_low_range,
        new_after_low_span,
        new_after_low_logic,
        new_after_low2_start,
        new_after_low2_range,
        new_after_low2_span,
        new_after_low2_logic,
        start_with_new_before_high_flag, 
        start_with_new_before_high2_flag, 
        start_with_new_after_high_flag,
        start_with_new_after_high2_flag,
        start_with_new_before_low_flag, 
        start_with_new_before_low2_flag,
        start_with_new_after_low_flag,
        start_with_new_after_low2_flag,
        comparison_vars,  # 添加比较变量列表
    ) = args
    stock_idx_arr = np.ascontiguousarray(stock_idx_arr, dtype=np.int32)
    date_grouped_results = worker_threads_cy.calculate_batch_cy(
        price_data_np, 
        date_columns, 
        width, 
        start_option, 
        shift_days, 
        end_date_start_idx, 
        end_date_end_idx, 
        diff_data_np, 
        stock_idx_arr, 
        is_forward, 
        n_days, 
        user_range_ratio, 
        continuous_abs_threshold, 
        valid_abs_sum_threshold, 
        n_days_max, 
        op_days, 
        inc_rate, 
        after_gt_end_ratio, 
        after_gt_start_ratio, 
        stop_loss_inc_rate,
        stop_loss_after_gt_end_ratio,
        stop_loss_after_gt_start_ratio,
        expr, 
        ops_change_input, 
        formula_expr, 
        select_count, 
        sort_mode, 
        trade_t1_mode,
        only_show_selected, 
        new_before_high_start, 
        new_before_high_range, 
        new_before_high_span,  
        new_before_high_logic, 
        new_before_high2_start, 
        new_before_high2_range, 
        new_before_high2_span, 
        new_before_high2_logic, 
        new_after_high_start, 
        new_after_high_range, 
        new_after_high_span, 
        new_after_high_logic, 
        new_after_high2_start, 
        new_after_high2_range, 
        new_after_high2_span, 
        new_after_high2_logic,
        new_before_low_start,
        new_before_low_range,
        new_before_low_span,
        new_before_low_logic,
        new_before_low2_start,
        new_before_low2_range,
        new_before_low2_span,
        new_before_low2_logic,
        new_after_low_start,
        new_after_low_range,
        new_after_low_span,
        new_after_low_logic,
        new_after_low2_start,
        new_after_low2_range,
        new_after_low2_span,
        new_after_low2_logic,
        start_with_new_before_high_flag, 
        start_with_new_before_high2_flag,
        start_with_new_after_high_flag,
        start_with_new_after_high2_flag,
        start_with_new_before_low_flag, 
        start_with_new_before_low2_flag,
        start_with_new_after_low_flag,
        start_with_new_after_low2_flag,
        comparison_vars,  # 添加比较变量列表
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
