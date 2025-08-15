import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns
import numpy as np
import time
import math
from multiprocessing import Pool, cpu_count
import concurrent.futures
import worker_threads_cy  # 这是你用Cython编译出来的模块
import re
import threading
import atexit

class ProcessPoolManager:
    """全局进程池管理器，使用单例模式"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._process_pool = None
            self._max_workers = None
            self._pool_lock = threading.Lock()
            self._initialized = True
            # 注册程序退出时的清理函数
            atexit.register(self.shutdown)
    
    def get_process_pool(self, max_workers):
        """获取或创建进程池，只有在进程数不同时才重新创建"""
        with self._pool_lock:
            if self._process_pool is None or self._max_workers != max_workers:
                # 关闭旧的进程池
                if self._process_pool is not None:
                    try:
                        self._process_pool.shutdown(wait=True)
                        self._log_to_file(f"关闭旧的进程池，max_workers={self._max_workers}")
                    except Exception as e:
                        self._log_to_file(f"关闭旧进程池时出错: {e}", "ERROR")
                
                # 创建新的进程池
                self._process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
                self._max_workers = max_workers
                self._log_to_file(f"【打开程序】创建新的进程池，max_workers={max_workers}")
            else:
                self._log_to_file(f"复用现有进程池，max_workers={max_workers}")
            
            return self._process_pool
    
    def shutdown(self):
        """关闭进程池"""
        with self._pool_lock:
            if self._process_pool is not None:
                try:
                    self._process_pool.shutdown(wait=True)
                    self._process_pool = None
                    self._max_workers = None
                    self._log_to_file("全局进程池已关闭")
                except Exception as e:
                    self._log_to_file(f"关闭全局进程池时出错: {e}", "ERROR")
    
    def _log_to_file(self, message, log_type="INFO"):
        """记录进程池相关日志到process_pool.log文件"""
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] [{log_type}] [ProcessPoolManager] {message}\n"
            
            with open('process_pool.log', 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            # 如果日志写入失败，至少尝试输出到控制台
            try:
                print(f"日志写入失败: {e}")
            except:
                pass

# 全局进程池管理器实例
process_pool_manager = ProcessPoolManager()

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
            # 只对price_data做0.0转为NaN，并对数值进行传统四舍五入保留两位小数
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

    def _log_to_file(self, message, log_type="INFO"):
        """记录进程池相关日志到process_pool.log文件
        
        日志分类规则：
        - process_pool.log: 进程池生命周期、内存监控、计算状态等
        - error_log.txt: 子进程异常、错误详情等（在calculate_batch_16_cores中处理）
        """
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            log_message = f"[{timestamp}] [{log_type}] {message}\n"
            
            with open('process_pool.log', 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            # 如果日志写入失败，至少尝试输出到控制台
            try:
                print(f"日志写入失败: {e}")
            except:
                pass
    
    def _get_process_pool(self, max_workers):
        """从全局管理器获取进程池"""
        return process_pool_manager.get_process_pool(max_workers)

    def safe_float(self, val, default=float('nan')):
        try:
            if val is None or (isinstance(val, str) and val.strip() == ''):
                return default
            return float(val)
        except Exception:
            return default

    def _round_numeric_values(self, stock_data):
        """
        统一的数值四舍五入处理
        对数值字段进行四舍五入保留两位小数
        对使用 round_to_2_nan 的字段进行特殊处理（如果为0则设为None）
        """
        import math
        
        # 使用 round_to_2_nan 的字段列表（如果为0则设为None）
        round_to_2_nan_fields = [
            'cont_sum_pos_sum',
            'cont_sum_neg_sum', 
            'cont_sum_pos_sum_first_half',
            'cont_sum_pos_sum_second_half',
            'cont_sum_neg_sum_first_half',
            'cont_sum_neg_sum_second_half',
            'forward_max_cont_sum_pos_sum',
            'forward_max_cont_sum_neg_sum',
            'forward_min_cont_sum_pos_sum',
            'forward_min_cont_sum_neg_sum',
            'forward_max_valid_pos_sum',
            'forward_max_valid_neg_sum',
            'forward_min_valid_pos_sum',
            'forward_min_valid_neg_sum'
        ]
        
        # 需要四舍五入的数值字段列表（包含所有字段，包括 round_to_2_nan_fields）
        numeric_fields = [
            'score', 'hold_days', 'ops_change', 'ops_incre_rate', 
            'adjust_days', 'adjust_ops_change', 'adjust_ops_incre_rate',
            'max_value', 'min_value', 'end_value', 'start_value', 
            'actual_value', 'closest_value', 'increment_value',
            'after_gt_end_value', 'after_gt_start_value', 'ops_value',
            'continuous_len', 'continuous_start_value', 'continuous_start_next_value', 
            'continuous_start_next_next_value', 'continuous_end_value', 
            'continuous_end_prev_value', 'continuous_end_prev_prev_value',
            'continuous_abs_sum_first_half', 'continuous_abs_sum_second_half',
            'continuous_abs_sum_block1', 'continuous_abs_sum_block2', 
            'continuous_abs_sum_block3', 'continuous_abs_sum_block4',
            'forward_max_result', 'forward_max_continuous_start_value',
            'forward_max_continuous_start_next_value', 'forward_max_continuous_start_next_next_value',
            'forward_max_continuous_end_value', 'forward_max_continuous_end_prev_value',
            'forward_max_continuous_end_prev_prev_value', 'forward_max_abs_sum_first_half',
            'forward_max_abs_sum_second_half', 'forward_max_abs_sum_block1',
            'forward_max_abs_sum_block2', 'forward_max_abs_sum_block3', 'forward_max_abs_sum_block4',
            'forward_min_result', 'forward_min_continuous_start_value',
            'forward_min_continuous_start_next_value', 'forward_min_continuous_start_next_next_value',
            'forward_min_continuous_end_value', 'forward_min_continuous_end_prev_value',
            'forward_min_continuous_end_prev_prev_value', 'forward_min_abs_sum_first_half',
            'forward_min_abs_sum_second_half', 'forward_min_abs_sum_block1',
            'forward_min_abs_sum_block2', 'forward_min_abs_sum_block3', 'forward_min_abs_sum_block4',
            'valid_sum_len', 'valid_pos_sum', 'valid_neg_sum',
            'forward_max_valid_sum_len', 'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
            'forward_min_valid_sum_len', 'forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
            'valid_abs_sum_first_half', 'valid_abs_sum_second_half',
            'valid_abs_sum_block1', 'valid_abs_sum_block2', 'valid_abs_sum_block3', 'valid_abs_sum_block4',
            'forward_max_valid_abs_sum_first_half', 'forward_max_valid_abs_sum_second_half',
            'forward_max_valid_abs_sum_block1', 'forward_max_valid_abs_sum_block2',
            'forward_max_valid_abs_sum_block3', 'forward_max_valid_abs_sum_block4',
            'forward_min_valid_abs_sum_first_half', 'forward_min_valid_abs_sum_second_half',
            'forward_min_valid_abs_sum_block1', 'forward_min_valid_abs_sum_block2',
            'forward_min_valid_abs_sum_block3', 'forward_min_valid_abs_sum_block4',
            'n_days_max_value', 'prev_day_change', 'end_day_change', 'diff_end_value',
            'increment_change', 'after_gt_end_change', 'after_gt_start_change',
            'forward_max_result_len', 'forward_min_result_len',
            'n_max_is_max', 'range_ratio_is_less', 'continuous_abs_is_less', 'valid_abs_is_less',
            'forward_min_continuous_abs_is_less', 'forward_min_valid_abs_is_less',
            'forward_max_continuous_abs_is_less', 'forward_max_valid_abs_is_less',
            'stop_loss', 'take_profit', 'op_day_change', 'has_three_consecutive_zeros',
            'take_and_stop_increment_change', 'take_and_stop_after_gt_end_change', 'take_and_stop_after_gt_start_change',
            'take_and_stop_change', 'take_and_stop_incre_rate',
            'stop_and_take_increment_change', 'stop_and_take_after_gt_end_change', 'stop_and_take_after_gt_start_change',
            'stop_and_take_change', 'stop_and_take_incre_rate',
            # 添加 round_to_2_nan_fields 中的所有字段
            'cont_sum_pos_sum', 'cont_sum_neg_sum', 
            'cont_sum_pos_sum_first_half', 'cont_sum_pos_sum_second_half',
            'cont_sum_neg_sum_first_half', 'cont_sum_neg_sum_second_half',
            'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
            'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum',
            'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
            'forward_min_valid_pos_sum', 'forward_min_valid_neg_sum'
        ]
        
        # 处理所有数值字段
        for field in numeric_fields:
            if field in stock_data:
                val = stock_data[field]
                if val is not None and val != '' and not (isinstance(val, float) and math.isnan(val)):
                    try:
                        float_val = float(val)
                        # 对使用 round_to_2_nan 的字段进行特殊处理
                        if field in round_to_2_nan_fields:
                            if abs(float_val) == 0.0:  # 如果四舍五入后为0，设为None
                                stock_data[field] = None
                            else:
                                stock_data[field] = round(float_val, 2)
                        else:
                            # 普通字段直接四舍五入
                            stock_data[field] = round(float_val, 2)
                    except (ValueError, TypeError):
                        continue

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
        
        # 盈损参数，默认为INC
        profit_type = params.get('profit_type', 'INC')  # 盈的类型：INC, AGE, AGS
        loss_type = params.get('loss_type', 'INC')      # 损的类型：INC, AGE, AGS
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
                profit_type,  # 盈的类型
                loss_type,    # 损的类型
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
        self._log_to_file(f"开始计算，进程数: {n_proc}, 股票数: {num_stocks}")
        
        # 添加内存监控
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            print(f"初始内存使用: {initial_memory:.2f} MB")
            # 内存监控信息记录到process_pool.log
            self._log_to_file(f"初始内存使用: {initial_memory:.2f} MB")
        except ImportError:
            print("psutil未安装，无法监控内存使用")
            # 内存监控信息记录到process_pool.log
            self._log_to_file("psutil未安装，无法监控内存使用")
        
        merged_results = {}
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            end_date = date_columns[idx]
            merged_results[end_date] = []
        # 使用复用的进程池
        executor = self._get_process_pool(n_proc)
        futures = [executor.submit(cy_batch_worker, args) for args in args_list]
        for fut in concurrent.futures.as_completed(futures):
            try:
                process_results = fut.result()
                for end_date, stocks in process_results.items():
                    if end_date in merged_results:
                        merged_results[end_date].extend(stocks)
            except Exception as e:
                import traceback
                print(f"子进程异常: {e}")
                print(f"异常详情: {traceback.format_exc()}")
                # 子进程异常记录到error_log.txt，与进程池日志分开
                try:
                    with open('error_log.txt', 'a', encoding='utf-8') as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 子进程异常: {e}\n")
                        f.write(f"异常详情: {traceback.format_exc()}\n")
                        f.write("-" * 50 + "\n")
                except:
                    pass
        t1 = time.time()
        total_time = t1 - t0
        print(f"calculate_batch_{n_proc}_cores 总耗时: {total_time:.4f}秒")
        self._log_to_file(f"计算完成，总耗时: {total_time:.4f}秒")
        
        # 统一处理股票代码和名称
        for end_date in merged_results:
            for stock in merged_results[end_date]:
                stock_idx = stock.get('stock_idx', None)
                if stock_idx is not None:
                    # 获取股票代码和名称
                    code = self.price_data.iloc[stock_idx, 0]
                    name = self.price_data.iloc[stock_idx, 1]
                    
                    # 格式化股票代码为6位数字格式
                    if code is not None and code != '':
                        try:
                            code_str = str(code).strip()
                            if code_str.isdigit() and len(code_str) < 6:
                                code = code_str.zfill(6)
                        except Exception:
                            pass
                    
                    stock['code'] = code
                    stock['name'] = name if name is not None else ''
                
                # 统一的数值四舍五入处理
                self._round_numeric_values(stock)
        
        if only_show_selected:
            for end_date in merged_results:
                merged_results[end_date] = sorted(
                    merged_results[end_date],
                    key=lambda x: x['score'],
                    reverse=(sort_mode == "最大值排序")
                )[:select_count]
        
        # 定义数值字段和非数值字段
        numeric_fields = [
            'score', 'hold_days', 'ops_change', 'ops_incre_rate', 
            'adjust_days', 'adjust_ops_change', 'adjust_ops_incre_rate',
            'max_value', 'min_value', 'end_value', 'start_value', 
            'actual_value', 'closest_value', 'increment_value',
            'after_gt_end_value', 'after_gt_start_value', 'ops_value',
            'continuous_len', 'continuous_start_value', 'continuous_start_next_value', 
            'continuous_start_next_next_value', 'continuous_end_value', 
            'continuous_end_prev_value', 'continuous_end_prev_prev_value',
            'continuous_abs_sum_first_half', 'continuous_abs_sum_second_half',
            'continuous_abs_sum_block1', 'continuous_abs_sum_block2', 
            'continuous_abs_sum_block3', 'continuous_abs_sum_block4',
            'forward_max_result', 'forward_max_continuous_start_value',
            'forward_max_continuous_start_next_value', 'forward_max_continuous_start_next_next_value',
            'forward_max_continuous_end_value', 'forward_max_continuous_end_prev_value',
            'forward_max_continuous_end_prev_prev_value', 'forward_max_abs_sum_first_half',
            'forward_max_abs_sum_second_half', 'forward_max_abs_sum_block1',
            'forward_max_abs_sum_block2', 'forward_max_abs_sum_block3', 'forward_max_abs_sum_block4',
            'forward_min_result', 'forward_min_continuous_start_value',
            'forward_min_continuous_start_next_value', 'forward_min_continuous_start_next_next_value',
            'forward_min_continuous_end_value', 'forward_min_continuous_end_prev_value',
            'forward_min_continuous_end_prev_prev_value', 'forward_min_abs_sum_first_half',
            'forward_min_abs_sum_second_half', 'forward_min_abs_sum_block1',
            'forward_min_abs_sum_block2', 'forward_min_abs_sum_block3', 'forward_min_abs_sum_block4',
            'valid_sum_len', 'valid_pos_sum', 'valid_neg_sum',
            'forward_max_valid_sum_len', 'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
            'forward_min_valid_sum_len', 'forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
            'valid_abs_sum_first_half', 'valid_abs_sum_second_half',
            'valid_abs_sum_block1', 'valid_abs_sum_block2', 'valid_abs_sum_block3', 'valid_abs_sum_block4',
            'forward_max_valid_abs_sum_first_half', 'forward_max_valid_abs_sum_second_half',
            'forward_max_valid_abs_sum_block1', 'forward_max_valid_abs_sum_block2',
            'forward_max_valid_abs_sum_block3', 'forward_max_valid_abs_sum_block4',
            'forward_min_valid_abs_sum_first_half', 'forward_min_valid_abs_sum_second_half',
            'forward_min_valid_abs_sum_block1', 'forward_min_valid_abs_sum_block2',
            'forward_min_valid_abs_sum_block3', 'forward_min_valid_abs_sum_block4',
            'n_max_is_max', 'range_ratio_is_less', 'continuous_abs_is_less', 'valid_abs_is_less',
            'forward_min_continuous_abs_is_less', 'forward_min_valid_abs_is_less',
            'forward_max_continuous_abs_is_less', 'forward_max_valid_abs_is_less',
            'n_days_max_value', 'prev_day_change', 'end_day_change', 'diff_end_value',
            'increment_change', 'after_gt_end_change', 'after_gt_start_change',
            'forward_max_result_len', 'forward_min_result_len',
            'cont_sum_pos_sum', 'cont_sum_neg_sum',
            'cont_sum_pos_sum_first_half', 'cont_sum_pos_sum_second_half',
            'cont_sum_neg_sum_first_half', 'cont_sum_neg_sum_second_half',
            'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
            'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum',
            'start_with_new_before_high', 'start_with_new_before_high2',
            'start_with_new_after_high', 'start_with_new_after_high2',
            'start_with_new_before_low', 'start_with_new_before_low2',
            'start_with_new_after_low', 'start_with_new_after_low2',
            'stop_loss', 'take_profit', 'op_day_change', 'has_three_consecutive_zeros',
            'take_and_stop_increment_change', 'take_and_stop_after_gt_end_change', 'take_and_stop_after_gt_start_change',
            'take_and_stop_change', 'take_and_stop_incre_rate',
            'stop_and_take_increment_change', 'stop_and_take_after_gt_end_change', 'stop_and_take_after_gt_start_change',
            'stop_and_take_change', 'stop_and_take_incre_rate',
        ]
        
        # 定义非数值类型字段（数组对象和布尔对象）
        non_numeric_fields = {
            'forward_max_result', 'forward_min_result',  # 数组对象
            'n_max_is_max', 'range_ratio_is_less', 'continuous_abs_is_less', 'valid_abs_is_less',
            'forward_min_continuous_abs_is_less', 'forward_min_valid_abs_is_less',
            'forward_max_continuous_abs_is_less', 'forward_max_valid_abs_is_less',
            'start_with_new_before_high', 'start_with_new_before_high2',
            'start_with_new_after_high', 'start_with_new_after_high2',
            'start_with_new_before_low', 'start_with_new_before_low2',
            'start_with_new_after_low', 'start_with_new_after_low2',
            'has_three_consecutive_zeros'  # 布尔对象
        }
        
        # 初始化总体统计收集器
        overall_values = {field: [] for field in numeric_fields if field not in non_numeric_fields}
        
        # 添加统计行：最大值、最小值、中值
        for end_date in merged_results:
            stocks = merged_results[end_date]
            if not stocks:
                continue
                
            # 收集所有数值字段用于统计
            stats = {}
            for field in numeric_fields:
                # 跳过非数值类型字段
                if field in non_numeric_fields:
                    continue
                    
                values = []
                for stock in stocks:
                    val = stock.get(field)
                    if val is not None and val != '' and not (isinstance(val, float) and math.isnan(val)):
                        try:
                            float_val = float(val)
                            values.append(float_val)
                            # 同时收集总体统计值
                            overall_values[field].append(float_val)
                        except (ValueError, TypeError):
                            continue
                
                if values:
                    stats[f'{field}_max'] = max(values)
                    stats[f'{field}_min'] = min(values)
                    # 计算中值：如果是奇数个，取中间值；如果是偶数个，取中间两个值的平均值
                    sorted_values = sorted(values)
                    n = len(sorted_values)
                    if n % 2 == 1:  # 奇数个
                        stats[f'{field}_median'] = round(sorted_values[n // 2], 2)
                    else:  # 偶数个
                        stats[f'{field}_median'] = round((sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2, 2)
                else:
                    stats[f'{field}_max'] = None
                    stats[f'{field}_min'] = None
                    stats[f'{field}_median'] = None
            
            # 创建统计行
            max_row = {'code': '', 'name': '统计最大值', 'stock_idx': -3}
            min_row = {'code': '', 'name': '统计最小值', 'stock_idx': -2}
            median_row = {'code': '', 'name': '统计中值', 'stock_idx': -1}
            
            # 填充统计值
            for field in numeric_fields:
                if field in non_numeric_fields:
                    # 非数值类型字段在统计行中留空
                    max_row[field] = ''
                    min_row[field] = ''
                    median_row[field] = ''
                else:
                    max_row[field] = stats.get(f'{field}_max')
                    min_row[field] = stats.get(f'{field}_min')
                    median_row[field] = stats.get(f'{field}_median')
            
            # 将统计行添加到结果中
            merged_results[end_date].extend([max_row, min_row, median_row])
        
        # 计算总体统计值
        overall_stats = {}
        for field, values in overall_values.items():
            if values:
                overall_stats[f'{field}_max'] = round(max(values), 2)
                overall_stats[f'{field}_min'] = round(min(values), 2)
                # 计算中值：如果是奇数个，取中间值；如果是偶数个，取中间两个值的平均值
                sorted_values = sorted(values)
                n = len(sorted_values)
                if n % 2 == 1:  # 奇数个
                    overall_stats[f'{field}_median'] = round(sorted_values[n // 2], 2)
                else:  # 偶数个
                    overall_stats[f'{field}_median'] = round((sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2, 2)
                # 计算正值中值
                positive_values = [v for v in sorted_values if v > 0]
                n_pos = len(positive_values)
                if n_pos > 0:
                    if n_pos % 2 == 1:
                        overall_stats[f'{field}_positive_median'] = round(positive_values[n_pos // 2], 2)
                    else:
                        overall_stats[f'{field}_positive_median'] = round((positive_values[n_pos // 2 - 1] + positive_values[n_pos // 2]) / 2, 2)
                else:
                    overall_stats[f'{field}_positive_median'] = None
                # 计算负值中值
                negative_values = [v for v in sorted_values if v < 0]
                n_neg = len(negative_values)
                if n_neg > 0:
                    if n_neg % 2 == 1:
                        overall_stats[f'{field}_negative_median'] = round(negative_values[n_neg // 2], 2)
                    else:
                        overall_stats[f'{field}_negative_median'] = round((negative_values[n_neg // 2 - 1] + negative_values[n_neg // 2]) / 2, 2)
                else:
                    overall_stats[f'{field}_negative_median'] = None
                
                # 专门打印 diff_end_value 的统计信息
                # if field == 'diff_end_value':
                #     print(f"[worker_threads] diff_end_value 统计数组长度: {len(values)}")
                #     print(f"[worker_threads] diff_end_value 统计数组前10个值: {values[:10]}")
                #     print(f"[worker_threads] diff_end_value 统计数组后10个值: {values[-10:]}")
                #     print(f"[worker_threads] diff_end_value 最终统计值:")
                #     print(f"  最大值: {overall_stats[f'{field}_max']}")
                #     print(f"  最小值: {overall_stats[f'{field}_min']}")
                #     print(f"  中值: {overall_stats[f'{field}_median']}")
                #     print(f"  正值中值: {overall_stats[f'{field}_positive_median']}")
                #     print(f"  负值中值: {overall_stats[f'{field}_negative_median']}")
                #     print(f"  正值数量: {len(positive_values)}")
                #     print(f"  负值数量: {len(negative_values)}")
                #     print(f"  零值数量: {len([v for v in values if v == 0])}")
            else:
                overall_stats[f'{field}_max'] = None
                overall_stats[f'{field}_min'] = None
                overall_stats[f'{field}_median'] = None
                overall_stats[f'{field}_positive_median'] = None
                overall_stats[f'{field}_negative_median'] = None

        #print(f"[SelectStockThread] overall_stats: {overall_stats}")
        
        result = {
            "dates": merged_results,
            "shift_days": shift_days,
            "is_forward": params.get("is_forward"),
            "start_date": date_columns[0],
            "end_date": date_columns[-1],
            "base_idx": None,
            "overall_stats": overall_stats,  # 添加总体统计值
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
        profit_type,  # 盈的类型
        loss_type,    # 损的类型
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
        profit_type,  # profit_type: 盈的类型，默认为INC
        loss_type,  # loss_type: 损的类型，默认为INC
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
