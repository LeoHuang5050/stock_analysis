import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from function.stock_functions import unify_date_columns
import numpy as np
import time
import math
import os
import billiard as multiprocessing  # 使用billiard替代multiprocessing
from billiard import Pool, set_start_method
import worker_threads_cy  # 这是你用Cython编译出来的模块
import re
import signal
import traceback
import threading

# 异步任务配置常量
ASYNC_TASK_CONFIG = {
    'DEFAULT_TIMEOUT': 300,           # 默认任务超时时间（秒）
    'MAX_RETRY_COUNT': 3,             # 最大重试次数
    'TASK_BATCH_SIZE': 100,           # 任务批处理大小
    'PROCESS_HEALTH_CHECK_INTERVAL': 60,  # 进程健康检查间隔（秒）
    'MAX_TASK_HISTORY': 1000,         # 最大任务历史记录数
    'LOG_LEVEL': 'INFO',              # 日志级别
    'ENABLE_PERFORMANCE_MONITORING': True,  # 启用性能监控
    'FORCE_PROCESS_REUSE': True,      # 强制进程复用
}

# 任务状态常量
TASK_STATUS = {
    'PENDING': 'pending',      # 等待中
    'RUNNING': 'running',      # 运行中
    'SUCCESS': 'success',      # 成功完成
    'FAILED': 'failed',        # 执行失败
    'TIMEOUT': 'timeout',      # 超时
    'CANCELLED': 'cancelled',  # 已取消
    'EMPTY_RESULT': 'empty_result'  # 空结果
}

def simple_test_worker(index):
    """简单的测试工作函数，只返回进程信息"""
    import os
    import time
    # 模拟一些工作
    time.sleep(0.1)
    return (index, os.getpid())

class ProcessPoolManager:
    """固定大小的进程池管理器，使用billiard.Pool，应用启动时创建16个进程
    
    billiard相比multiprocessing的优势：
    1. 更好的Windows兼容性
    2. 更稳定的进程连接
    3. 更好的打包环境支持
    4. 减少进程意外终止的问题
    """
    
    def __init__(self):
        self._pool = None
        self._fixed_size = 16  # 固定进程池大小
        self._is_initialized = False
        self._worker_pids = []  # 记录所有工作进程的PID
        self._pool_creation_time = None  # 记录进程池创建时间
        self._original_pids = []  # 保存原始进程PID列表
        self._force_stable_pool = True  # 强制稳定进程池
        
        # 简化的进程管理属性
        self._process_check_interval = 300  # 进程检查间隔（秒）
        self._last_process_check_time = 0
    
    def initialize_pool(self):
        """在应用启动时初始化固定大小的进程池，使用billiard.Pool"""
        if not self._is_initialized:
            print(f"初始化固定大小的进程池，进程数: {self._fixed_size}")
            print(f"主进程PID: {os.getpid()}")
            
            try:
                # 设置进程启动方法，确保与Cython模块兼容
                try:
                    set_start_method('spawn', force=True)
                    print("设置进程启动方法为 'spawn'")
                except RuntimeError:
                    print("进程启动方法已设置为 'spawn'")
                
                # 创建billiard.Pool，设置最大工作进程数
                pool_kwargs = {
                    'processes': self._fixed_size,
                    'maxtasksperchild': None,  # 进程永不退出，确保进程复用
                }
                
                # 在Windows环境下，billiard会自动使用spawn方法
                if os.name == 'nt':
                    print("Windows环境检测到，billiard将自动使用spawn启动方法")
                
                # 创建billiard.Pool
                self._pool = Pool(**pool_kwargs)
                
                self._is_initialized = True
                self._pool_creation_time = time.time()
                
                # 简化的进程启动等待
                print("等待子进程启动...")
                time.sleep(5)  # 等待5秒让进程启动
                
                # 尝试捕获PID
                self._capture_worker_pids()
                
                # 保存原始PID列表
                self._original_pids = self._worker_pids.copy()
                
                # 最终验证
                unique_pids = len(set(self._original_pids))
                if unique_pids > 0:
                    print(f"✓ 进程池初始化完成，进程数: {unique_pids}")
                    print(f"工作进程PID列表: {self._original_pids}")
                else:
                    print("⚠ 警告: 未能捕获到任何工作进程PID")
                    print("进程池可能未正确初始化")
                
                # 记录进程池创建信息
                try:
                    with open('process_pool.log', 'a', encoding='utf-8') as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - billiard.Pool初始化完成\n")
                        f.write(f"主进程PID: {os.getpid()}\n")
                        f.write(f"进程池大小: {self._fixed_size}\n")
                        f.write(f"原始工作进程PID列表: {self._original_pids}\n")
                        f.write(f"唯一PID数量: {unique_pids}\n")
                        f.write(f"进程池创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._pool_creation_time))}\n")
                        f.write(f"maxtasksperchild: None (进程永不退出)\n")
                        f.write(f"启动方法: spawn (billiard自动设置)\n")
                        f.write(f"操作系统: {os.name}\n")
                        f.write("-" * 50 + "\n")
                except:
                    pass
                    
            except Exception as e:
                print(f"初始化billiard.Pool失败: {e}")
                self._pool = None
                self._is_initialized = False
    
    def _capture_worker_pids(self):
        """捕获所有工作进程的PID（简化版本）"""
        try:
            print("开始捕获工作进程PID...")
            
            # 清空之前的PID列表
            self._worker_pids = []
            
            # 使用简单的测试任务来激活进程，但不强制创建所有进程
            print("使用简单测试任务激活工作进程...")
            
            # 只创建少量测试任务来激活进程
            test_count = min(4, self._fixed_size)  # 最多测试4个进程
            test_results = []
            
            for i in range(test_count):
                try:
                    result = self._pool.apply_async(simple_test_worker, (i,))
                    test_results.append(result)
                except Exception as e:
                    print(f"激活工作进程 {i} 失败: {e}")
            
            # 等待测试任务完成并收集PID
            seen_pids = set()
            for i, result in enumerate(test_results):
                try:
                    _, pid = result.get(timeout=30)  # 30秒超时
                    if pid not in seen_pids:
                        seen_pids.add(pid)
                        self._worker_pids.append(pid)
                        print(f"工作进程 {i+1}: PID {pid}")
                    else:
                        print(f"警告: 检测到重复PID {pid}，跳过")
                except Exception as e:
                    print(f"获取工作进程 {i+1} PID失败: {e}")
            
            print(f"成功捕获 {len(self._worker_pids)} 个工作进程PID")
            
            # 按PID排序
            self._worker_pids.sort()
            
            # 验证捕获的PID数量
            unique_pids = len(set(self._worker_pids))
            print(f"成功捕获 {len(self._worker_pids)} 个工作进程PID，唯一PID数: {unique_pids}")
            
            # 如果捕获的PID数量不足，记录警告但不重新初始化
            if unique_pids < test_count * 0.5:  # 至少50%的测试进程应该成功
                print(f"⚠ 警告: 捕获的PID数量不足，期望至少 {test_count * 0.5}，实际 {unique_pids}")
                print("程序将继续运行，但性能可能受到影响")
            
        except Exception as e:
            print(f"捕获工作进程PID失败: {e}")
            self._worker_pids = []
    
    def get_process_pool(self, max_workers):
        """获取进程池，如果max_workers超过16则抛出异常"""
        if not self._is_initialized:
            self.initialize_pool()
        
        if max_workers > self._fixed_size:
            raise ValueError(f"max_workers ({max_workers}) 不能超过固定进程池大小 ({self._fixed_size})")
        
        if self._pool is None:
            raise RuntimeError("billiard.Pool未正确初始化")
        
        print(f"使用billiard.Pool，请求进程数: {max_workers}，可用进程数: {self._fixed_size}")
        
        return self._pool
    
    def get_worker_pids(self):
        """获取当前工作进程的PID列表"""
        # 直接返回工作进程PID列表
        return self._worker_pids.copy()
    
    def check_worker_health(self):
        """检查工作进程的健康状态"""
        current_time = time.time()
        if current_time - self._last_process_check_time < self._process_check_interval:
            return
        
        self._last_process_check_time = current_time
        
        if not self._worker_pids:
            return
        
        print("=== 开始工作进程健康检查 ===")
        
        try:
            import psutil
            healthy_workers = []
            unhealthy_workers = []
            
            for pid in self._worker_pids:
                try:
                    # 检查进程是否仍然存在
                    if psutil.pid_exists(pid):
                        process = psutil.Process(pid)
                        # 检查进程状态
                        if process.status() in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING]:
                            healthy_workers.append(pid)
                        else:
                            unhealthy_workers.append(pid)
                            print(f"进程 {pid} 状态异常: {process.status()}")
                    else:
                        unhealthy_workers.append(pid)
                        print(f"进程 {pid} 已不存在")
                        
                except Exception as e:
                    unhealthy_workers.append(pid)
                    print(f"检查进程 {pid} 时出错: {e}")
            
            # 记录健康检查结果
            print(f"健康检查完成:")
            print(f"  健康进程: {len(healthy_workers)}/{len(self._worker_pids)}")
            print(f"  异常进程: {len(unhealthy_workers)}")
            
            if unhealthy_workers:
                print(f"  异常进程PID: {unhealthy_workers}")
                print("建议重启程序以恢复进程池")
                
        except Exception as e:
            print(f"工作进程健康检查失败: {e}")
    

    

    
    def shutdown(self):
        """关闭billiard.Pool"""
        if self._pool is not None:
            try:
                print(f"关闭billiard.Pool，工作进程PID: {self._worker_pids}")
                self._pool.close()
                self._pool.join()
                print("billiard.Pool已关闭")
            except Exception as e:
                print(f"关闭billiard.Pool时出错: {e}")
            finally:
                self._pool = None
                self._is_initialized = False
                self._worker_pids = []
                self._pool_creation_time = None
    
    def get_healthy_workers(self):
        """获取工作进程PID列表"""
        return self._worker_pids.copy()
    
    def monitor_task_execution(self, task_id, target_pid):
        """监控任务执行状态"""
        current_time = time.time()
        self._active_tasks[task_id] = {
            'start_time': current_time,
            'target_pid': target_pid,
            'status': 'running'
        }
        self._task_process_mapping[task_id] = target_pid
        
        if target_pid not in self._process_task_count:
            self._process_task_count[target_pid] = 0
        self._process_task_count[target_pid] += 1
        
        print(f"开始监控任务 {task_id} 在进程 {target_pid} 上的执行")
    
    def update_task_status(self, task_id, status, result=None, error=None):
        """更新任务状态"""
        if task_id in self._active_tasks:
            task_info = self._active_tasks[task_id]
            task_info['status'] = status
            task_info['end_time'] = time.time()
            task_info['execution_time'] = task_info['end_time'] - task_info['start_time']
            
            if result is not None:
                task_info['result'] = result
            if error is not None:
                task_info['error'] = error
            
            # 更新进程任务计数
            target_pid = task_info.get('target_pid')
            if target_pid and target_pid in self._process_task_count:
                self._process_task_count[target_pid] = max(0, self._process_task_count[target_pid] - 1)
            
            # 如果任务完成，从活跃任务中移除
            if status in ['success', 'failed', 'timeout', 'empty_result']:
                del self._active_tasks[task_id]
                if task_id in self._task_process_mapping:
                    del self._task_process_mapping[task_id]
            
            print(f"任务 {task_id} 状态更新为: {status}")
    
    def get_process_execution_summary(self):
        """获取进程执行摘要"""
        summary = f"进程池执行摘要:\n"
        summary += f"  总进程数: {len(self._worker_pids)}\n"
        summary += f"  工作进程PID: {self._worker_pids}\n"
        return summary
    
    def force_process_stability(self):
        """检查进程稳定性"""
        print("=== 检查进程稳定性 ===")
        
        if self._original_pids:
            current_pids = set(self._worker_pids)
            original_pids_set = set(self._original_pids)
            stable_pids = current_pids & original_pids_set
            stability_rate = len(stable_pids) / len(original_pids_set) * 100 if original_pids_set else 0
            
            print(f"进程稳定性检查:")
            print(f"  原始进程数: {len(original_pids_set)}")
            print(f"  当前进程数: {len(current_pids)}")
            print(f"  稳定进程数: {len(stable_pids)}")
            print(f"  稳定性率: {stability_rate:.1f}%")
            
            if stability_rate < 80:
                print("⚠ 警告: 进程稳定性率低于80%，建议重启程序")
            else:
                print("✓ 进程稳定性良好")
        
        return stability_rate if self._original_pids else 100.0
    
    def validate_process_assignment(self, target_pid, task_id):
        """验证任务是否在指定的进程上执行"""
        import os
        current_pid = os.getpid()
        
        if current_pid != target_pid:
            error_msg = f"进程分配验证失败：任务 {task_id} 期望在进程 {target_pid} 上执行，但实际在进程 {current_pid} 上执行"
            print(error_msg)
            

            
            return False
        
        # 验证成功
        print(f"✓ 进程分配验证成功：任务 {task_id} 在正确的进程 {current_pid} 上执行")
        
        return True
    
    def get_process_assignment_report(self):
        """获取进程分配报告"""
        report = "=== 进程分配报告 ===\n"
        
        if hasattr(self, '_task_process_mapping'):
            report += f"任务-进程映射:\n"
            for task_id, pid in self._task_process_mapping.items():
                report += f"  任务 {task_id} -> 进程 {pid}\n"
        else:
            report += "无任务-进程映射信息\n"
        
        if hasattr(self, '_process_task_count'):
            report += f"进程任务计数:\n"
            for pid, count in self._process_task_count.items():
                if count > 0:
                    report += f"  进程 {pid}: {count} 个任务\n"
        
        report += f"当前工作进程PID: {self._worker_pids}\n"
        report += f"健康进程PID: {self.get_healthy_workers()}\n"
        
        return report
    
    def diagnose_worker_failure(self, failed_pid):
        """诊断特定工作进程失败的原因"""
        print(f"=== 诊断工作进程 {failed_pid} 失败原因 ===")
        
        try:
            # 检查进程是否还在运行
            import psutil
            try:
                process = psutil.Process(failed_pid)
                status = process.status()
                memory_info = process.memory_info()
                print(f"进程 {failed_pid} 状态: {status}")
                print(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB")
            except psutil.NoSuchProcess:
                print(f"进程 {failed_pid} 已不存在")
            except Exception as e:
                print(f"检查进程 {failed_pid} 状态失败: {e}")
            
            # 检查相关日志文件
            log_files = ['worker_error.log', 'worker_progress.log', 'worker_start.log']
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if str(failed_pid) in content:
                                print(f"在 {log_file} 中找到进程 {failed_pid} 的记录")
                    except Exception as e:
                        print(f"读取 {log_file} 失败: {e}")
            
            # 检查Cython模块状态
            try:
                import worker_threads_cy
                if hasattr(worker_threads_cy, 'calculate_batch_cy'):
                    print("Cython模块状态: 正常")
                else:
                    print("Cython模块状态: calculate_batch_cy函数不可用")
            except Exception as e:
                print(f"Cython模块检查失败: {e}")
                
        except Exception as e:
            print(f"诊断过程出错: {e}")
        
        print("=" * 50)

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
        new_after_high2_range = int(params.get('new_before_high2_range', 0))
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
        print(f"开始计算，进程数: {n_proc}, 股票数: {num_stocks}")
        
        merged_results = {}
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            end_date = date_columns[idx]
            merged_results[end_date] = []
        
        # 使用进程池执行任务
        print(f"开始使用进程池执行任务，进程数: {n_proc}")
        start_time = time.time()
        
        try:
            # 从管理器获取进程池
            executor = process_pool_manager.get_process_pool(n_proc)
            
            # 创建异步任务管理器
            async_task_manager = AsyncTaskManager(process_pool_manager)
            
            # 创建异步任务列表
            # 将args_list转换为task_list格式
            task_list = []
            for i, args in enumerate(args_list):
                task_list.append({
                    'task_id': i + 1,
                    'args': args
                })
            
            async_tasks = async_task_manager.create_async_tasks(task_list, cy_batch_worker, executor)
            
            # 执行任务并收集结果
            task_results = async_task_manager.execute_tasks(async_tasks, timeout=300)
            
            # 提取结果数据
            all_process_results = []
            for task_result in task_results:
                if task_result['status'] == 'success' and task_result['result']:
                    all_process_results.append(task_result['result'])
                else:
                    all_process_results.append({})
            
            print("所有子进程执行完成，开始处理结果...")
            
            # 处理结果
            result_count = 0
            for i, process_results in enumerate(all_process_results):
                try:
                    print(f"处理第 {i+1}/{len(all_process_results)} 个子进程结果...")
                    
                    if process_results:  # 确保结果不为空
                        for end_date, stocks in process_results.items():
                            if end_date in merged_results:
                                merged_results[end_date].extend(stocks)
                                result_count += len(stocks)
                        
                        print(f"第 {i+1} 个子进程结果处理完成，结果数: {len(process_results)}")
                    else:
                        print(f"第 {i+1} 个子进程返回空结果")
                                
                except Exception as e:
                    print(f"第 {i+1} 个子进程结果处理异常: {e}")
                    # 记录到error_log.txt
                    try:
                        with open('error_log.txt', 'a', encoding='utf-8') as f:
                            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 第 {i+1} 个子进程结果处理异常: {e}\n")
                            f.write("-" * 50 + "\n")
                    except:
                        pass
            
            print(f"处理完成，总结果数: {result_count}")
                             
        except Exception as e:
            import traceback
            print(f"子进程异常: {e}")
            print(f"异常详情: {traceback.format_exc()}")
            # 子进程异常记录到error_log.txt
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
    """Cython批处理工作函数，使用ProcessPoolExecutor"""
    import os
    import sys
    import time
    import signal
    import traceback
    
    # 获取当前进程信息
    current_pid = os.getpid()
    parent_pid = os.getppid()
    
    # 设置信号处理器，防止意外终止
    def signal_handler(signum, frame):
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"子进程 {current_pid}: 收到信号 {signal_name}，但不立即退出")
        # 不立即退出，让主进程有机会处理
    
    # 注册信号处理器
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except:
        pass
    
    try:
        # 简化导入逻辑，避免与init_worker重复
        try:
            import worker_threads_cy
            print(f"子进程 {current_pid}: 成功导入worker_threads_cy")
        except ImportError as e:
            print(f"子进程 {current_pid}: 导入worker_threads_cy失败: {e}")
            
            # 如果是PyInstaller打包环境，尝试从MEIPASS导入
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
                print(f"子进程 {current_pid}: 尝试从PyInstaller路径导入: {base_path}")
                
                if base_path not in sys.path:
                    sys.path.insert(0, base_path)
                
                try:
                    import worker_threads_cy
                    print(f"子进程 {current_pid}: 从PyInstaller路径导入成功")
                except ImportError:
                    print(f"子进程 {current_pid}: 从PyInstaller路径导入也失败")
                    raise ImportError(f"无法导入worker_threads_cy模块: {e}")
            else:
                raise ImportError(f"无法导入worker_threads_cy模块: {e}")
        
        # 验证模块功能
        if not hasattr(worker_threads_cy, 'calculate_batch_cy'):
            error_msg = f"子进程 {current_pid}: worker_threads_cy模块缺少calculate_batch_cy函数"
            print(error_msg)
            raise AttributeError(error_msg)
        
        print(f"子进程 {current_pid}: worker_threads_cy模块验证成功，开始处理任务")
        
        # 解包参数
        try:
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
            
        except Exception as e:
            error_msg = f"子进程 {current_pid}: 参数解包失败: {e}"
            raise
        
        # 确保数据类型正确
        try:
            stock_idx_arr = np.ascontiguousarray(stock_idx_arr, dtype=np.int32)
        except Exception as e:
            error_msg = f"子进程 {current_pid}: 数据类型转换失败: {e}"
            raise
        
        # 调用Cython函数
        try:
            start_time = time.time()
            
            # 调用Cython函数
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
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 验证返回结果
            if date_grouped_results is None:
                raise ValueError(f"子进程 {current_pid}: calculate_batch_cy返回None")
            
            if not isinstance(date_grouped_results, dict):
                raise ValueError(f"子进程 {current_pid}: calculate_batch_cy返回类型错误，期望dict，实际{type(date_grouped_results)}")
            
            print(f"子进程 {current_pid}: 执行成功，耗时: {total_time:.4f}秒")
            return date_grouped_results
            
        except Exception as e:
            error_msg = f"子进程 {current_pid}: calculate_batch_cy 执行失败: {e}"
            raise
        
    except Exception as e:
        # 记录详细的错误信息
        import traceback
        error_msg = f"子进程 {os.getpid()}: cy_batch_worker 执行异常: {e}\n"
        error_msg += f"异常详情: {traceback.format_exc()}\n"
        
        # 重新抛出异常，让主进程知道子进程出错了
        raise

def replace_abbr(expr, abbr_map):
    for abbr, full in abbr_map.items():
        expr = re.sub(rf'\b{abbr}\b', full, expr)
    return expr

def split_indices(total, n_parts):
    part_size = (total + n_parts - 1) // n_parts
    # 返回每个分组的起止索引（左闭右开）
    return [(i * part_size, min((i + 1) * part_size, total)) for i in range(n_parts)]

# 独立的函数，用于在子进程中获取PID
def get_pid_worker(x):
    """获取进程PID的独立函数"""
    import os
    return (x, os.getpid())

class AsyncTaskManager:
    """异步任务管理器，负责创建、分配和监控异步任务"""
    
    def __init__(self, process_pool_manager, config=None):
        self.process_pool_manager = process_pool_manager
        self.config = config or ASYNC_TASK_CONFIG.copy()
        self.task_history = []  # 任务执行历史
        self.process_usage_stats = {}  # 进程使用统计
        self.task_counter = 0  # 任务计数器
        self.health_check_timer = None  # 健康检查定时器
        
    def create_async_tasks(self, task_list, worker_function, executor):
        """创建异步任务列表"""
        if not task_list:
            return []
        
        async_tasks = []
        
        for task_info in task_list:
            # 生成唯一任务ID
            task_info['unique_id'] = f"TASK_{len(async_tasks) + 1}_{int(time.time())}"
            task_info['status'] = TASK_STATUS['PENDING']
            task_info['created_at'] = time.time()
            task_info['retry_count'] = 0
            
            # 关键修改：不再强制指定进程，而是使用任务队列机制
            print(f"创建任务 {task_info['task_id']} (ID: {task_info['unique_id']})")
            
            # 使用进程池的默认调度机制，但添加任务跟踪
            async_result = executor.apply_async(worker_function, (task_info['args'],))
            task_info['async_result'] = async_result
            async_tasks.append(task_info)
            
            print(f"任务 {task_info['task_id']} (ID: {task_info['unique_id']}) 已提交到进程池")
            

        
        return async_tasks
    
    def execute_tasks(self, async_tasks, timeout=None):
        """执行异步任务并收集结果，使用billiard.Pool的AsyncResult对象"""
        if not async_tasks:
            return []
        
        print(f"=== 开始执行 {len(async_tasks)} 个异步任务 ===")
        
        # 设置超时时间
        if timeout is None:
            timeout = ASYNC_TASK_CONFIG['DEFAULT_TIMEOUT']
        
        start_time = time.time()
        results = []
        completed_tasks = 0
        failed_tasks = 0
        
        # 任务执行状态跟踪
        task_status = {}
        for task in async_tasks:
            task_id = task['unique_id']
            task_status[task_id] = {
                'status': 'running',
                'start_time': time.time(),
                'result': None,
                'error': None,
                'worker_pid': None
            }
        
        try:
            # 等待所有任务完成或超时
            while completed_tasks + failed_tasks < len(async_tasks):
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # 检查超时
                if elapsed_time > timeout:
                    print(f"⚠ 任务执行超时 ({timeout}秒)，强制结束剩余任务")
                    break
                
                # 检查每个任务的状态
                for task in async_tasks:
                    task_id = task['unique_id']
                    async_result = task['async_result']
                    
                    # 跳过已完成的任务
                    if task_status[task_id]['status'] in ['completed', 'failed']:
                        continue
                    
                    try:
                        # 检查任务是否完成
                        if async_result.ready():
                            if async_result.successful():
                                # 任务成功完成
                                result = async_result.get(timeout=1)  # 1秒超时获取结果
                                task_status[task_id]['status'] = 'completed'
                                task_status[task_id]['result'] = result
                                task_status[task_id]['end_time'] = time.time()
                                
                                # 尝试获取执行进程的PID（如果可用）
                                try:
                                    if hasattr(async_result, '_worker'):
                                        worker_pid = getattr(async_result._worker, 'pid', None)
                                        if worker_pid:
                                            task_status[task_id]['worker_pid'] = worker_pid
                                except:
                                    pass
                                
                                completed_tasks += 1
                                print(f"✓ 任务 {task['task_id']} (ID: {task_id}) 完成")
                                
                                # 记录成功日志
                                try:
                                    with open('worker_progress.log', 'a', encoding='utf-8') as f:
                                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 任务完成\n")
                                        f.write(f"任务ID: {task['task_id']}\n")
                                        f.write(f"唯一ID: {task_id}\n")
                                        f.write(f"执行时间: {task_status[task_id]['end_time'] - task_status[task_id]['start_time']:.2f}秒\n")
                                        if task_status[task_id]['worker_pid']:
                                            f.write(f"执行进程PID: {task_status[task_id]['worker_pid']}\n")
                                        f.write("-" * 30 + "\n")
                                except:
                                    pass
                                
                            else:
                                # 任务执行失败
                                try:
                                    error = async_result.get(timeout=1)
                                except Exception as e:
                                    error = str(e)
                                
                                task_status[task_id]['status'] = 'failed'
                                task_status[task_id]['error'] = error
                                task_status[task_id]['end_time'] = time.time()
                                
                                failed_tasks += 1
                                print(f"✗ 任务 {task['task_id']} (ID: {task_id}) 失败: {error}")
                                
                                # 记录失败日志
                                try:
                                    with open('worker_error.log', 'a', encoding='utf-8') as f:
                                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 任务执行失败\n")
                                        f.write(f"任务ID: {task['task_id']}\n")
                                        f.write(f"唯一ID: {task_id}\n")
                                        f.write(f"错误信息: {error}\n")
                                        f.write(f"执行时间: {task_status[task_id]['end_time'] - task_status[task_id]['start_time']:.2f}秒\n")
                                        f.write("-" * 30 + "\n")
                                except:
                                    pass
                        
                        # 检查任务是否超时
                        elif elapsed_time > timeout:
                            task_status[task_id]['status'] = 'timeout'
                            task_status[task_id]['error'] = '任务执行超时'
                            task_status[task_id]['end_time'] = time.time()
                            failed_tasks += 1
                            print(f"⏰ 任务 {task['task_id']} (ID: {task_id}) 超时")
                    
                    except Exception as e:
                        # 处理任务状态检查异常
                        print(f"⚠ 检查任务 {task_id} 状态时出错: {e}")
                        task_status[task_id]['status'] = 'error'
                        task_status[task_id]['error'] = str(e)
                        task_status[task_id]['end_time'] = time.time()
                        failed_tasks += 1
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n⚠ 用户中断任务执行")
            # 尝试取消未完成的任务
            for task in async_tasks:
                if task_status[task['unique_id']]['status'] == 'running':
                    try:
                        task['async_result'].cancel()
                        print(f"已取消任务 {task['task_id']}")
                    except:
                        pass
        
        # 收集结果
        for task in async_tasks:
            task_id = task['unique_id']
            status_info = task_status[task_id]
            
            if status_info['status'] == 'completed':
                results.append({
                    'task_id': task['task_id'],
                    'unique_id': task_id,
                    'status': 'success',
                    'result': status_info['result'],
                    'execution_time': status_info['end_time'] - status_info['start_time'],
                    'worker_pid': status_info['worker_pid']
                })
            else:
                results.append({
                    'task_id': task['task_id'],
                    'unique_id': task_id,
                    'status': 'failed',
                    'error': status_info['error'],
                    'execution_time': status_info['end_time'] - status_info['start_time'] if 'end_time' in status_info else 0,
                    'worker_pid': status_info['worker_pid']
                })
        
        # 执行完成统计
        total_time = time.time() - start_time
        print(f"\n=== 任务执行完成 ===")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"成功任务: {completed_tasks}")
        print(f"失败任务: {failed_tasks}")
        print(f"成功率: {completed_tasks / len(async_tasks) * 100:.1f}%")
        

        
        return results
    
    def _check_process_status_after_timeout(self, target_pid):
        """检查超时后的进程状态"""
        try:
            print(f"超时任务进程 {target_pid} 状态检查:")
            print(f"  建议检查进程是否仍然活跃")
        except Exception as e:
            print(f"检查超时进程状态时出错: {e}")
    
    def _check_process_status_after_error(self, target_pid, error):
        """检查错误后的进程状态"""
        try:
            print(f"错误任务进程 {target_pid} 状态检查:")
            print(f"  错误信息: {error}")
            print(f"  建议检查进程是否仍然活跃")
        except Exception as e:
            print(f"检查错误进程状态时出错: {e}")
    
    def _update_process_stats(self, pid, status):
        """更新进程使用统计"""
        if pid not in self.process_usage_stats:
            self.process_usage_stats[pid] = {'success': 0, 'failed': 0, 'total': 0}
        
        self.process_usage_stats[pid]['total'] += 1
        self.process_usage_stats[pid][status] += 1
    
    def _log_task_error(self, task_info, error):
        """记录任务错误日志"""
        pass
        
        # 特殊处理WorkerLostError，提供诊断信息
        if "WorkerLostError" in str(error) or "Worker exited prematurely" in str(error):
            print(f"⚠ 检测到工作进程异常退出，开始诊断...")
            target_pid = task_info.get('target_pid')
            if target_pid:
                self.process_pool_manager.diagnose_worker_failure(target_pid)
            
            # 尝试从错误信息中提取退出码
            import re
            exit_code_match = re.search(r'exitcode (\d+)', str(error))
            if exit_code_match:
                exit_code = int(exit_code_match.group(1))
                print(f"进程退出码: {exit_code} (0x{exit_code:08X})")
                if exit_code == 0xC0000005:
                    print("⚠ 这是Windows访问违规错误，通常由以下原因引起:")
                    print("  1. Cython代码访问了无效内存地址")
                    print("  2. 数组越界或空指针访问")
                    print("  3. OpenMP并行化冲突")
                    print("  4. 数据类型不匹配")
                elif exit_code == 0xC00000FD:
                    print("⚠ 这是栈溢出错误")
                elif exit_code == 0xC000001D:
                    print("⚠ 这是非法指令错误")
    
    def _print_execution_summary(self, completed, failed, timeout, total_time):
        """打印执行摘要"""
        print("\n=== 任务执行摘要 ===")
        print(f"总任务数: {completed + failed + timeout}")
        print(f"成功完成: {completed}")
        print(f"执行失败: {failed}")
        print(f"超时任务: {timeout}")
        print(f"总执行时间: {total_time:.2f}秒")
        print(f"平均任务时间: {total_time / (completed + failed + timeout):.2f}秒")
        
        # 打印进程使用统计
        if self.process_usage_stats:
            print("\n进程使用统计:")
            for pid, stats in self.process_usage_stats.items():
                success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                print(f"  进程PID {pid}: 成功 {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
    
    def _save_task_history(self, results):
        """保存任务执行历史"""
        self.task_history.extend(results)
        
        # 只保留最近1000条记录
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]
    
    def get_process_performance_report(self):
        """获取进程性能报告"""
        if not self.process_usage_stats:
            return "暂无进程使用统计"
        
        report = "进程性能报告:\n"
        for pid, stats in self.process_usage_stats.items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"  进程PID {pid}: 成功率 {success_rate:.1f}% ({stats['success']}/{stats['total']})\n"
        
        return report
    
    def reset_stats(self):
        """重置统计信息"""
        self.process_usage_stats.clear()
        self.task_history.clear()
        print("统计信息已重置")

# 使用示例：展示如何使用AsyncTaskManager
def example_usage_async_task_manager():
    """示例：使用AsyncTaskManager创建异步任务列表并强制使用指定进程"""
    
    print("=== AsyncTaskManager 使用示例 ===")
    
    # 1. 初始化进程池管理器
    process_pool_manager = ProcessPoolManager()
    process_pool_manager.initialize_pool()
    
    # 2. 创建异步任务管理器
    async_task_manager = AsyncTaskManager(process_pool_manager)
    
    # 3. 获取进程池
    executor = process_pool_manager.get_process_pool(8)  # 使用8个进程
    
    # 4. 准备测试数据
    test_args_list = [
        {'start_date': '2024-01-01', 'end_date': '2024-01-31', 'batch_id': 1},
        {'start_date': '2024-02-01', 'end_date': '2024-02-29', 'batch_id': 2},
        {'start_date': '2024-03-01', 'end_date': '2024-03-31', 'batch_id': 3},
        {'start_date': '2024-04-01', 'end_date': '2024-04-30', 'batch_id': 4},
        {'start_date': '2024-05-01', 'end_date': '2024-05-31', 'batch_id': 5},
        {'start_date': '2024-06-01', 'end_date': '2024-06-30', 'batch_id': 6},
        {'start_date': '2024-07-01', 'end_date': '2024-07-31', 'batch_id': 7},
        {'start_date': '2024-08-01', 'end_date': '2024-08-31', 'batch_id': 8},
    ]
    
    # 5. 定义测试工作函数
    def test_worker_function(args):
        """测试工作函数，模拟实际任务"""
        import time
        import random
        
        # 模拟工作负载
        work_time = random.uniform(0.1, 0.5)
        time.sleep(work_time)
        
        # 返回模拟结果
        return {
            'batch_id': args['batch_id'],
            'start_date': args['start_date'],
            'end_date': args['end_date'],
            'result_count': random.randint(10, 100),
            'worker_pid': os.getpid(),
            'execution_time': work_time
        }
    
    try:
        print("开始创建异步任务...")
        
        # 6. 创建异步任务列表
        async_tasks = async_task_manager.create_async_tasks(
            executor, 
            test_args_list, 
            test_worker_function
        )
        
        print(f"成功创建 {len(async_tasks)} 个异步任务")
        
        # 7. 执行任务
        print("开始执行任务...")
        results = async_task_manager.execute_tasks(async_tasks, timeout=60)
        
        # 8. 显示结果
        print("\n=== 执行结果 ===")
        for result in results:
            if result['status'] == 'success':
                data = result['result']
                print(f"✓ 任务 {result['task_id']} (PID: {result['target_pid']}): "
                      f"批次 {data['batch_id']}, 结果数 {data['result_count']}")
            else:
                print(f"✗ 任务 {result['task_id']} (PID: {result['target_pid']}): "
                      f"状态 {result['status']}")
        
        # 9. 任务执行完成
        print("所有任务执行完成")
        
        # 10. 清理资源
        executor.close()
        executor.join()
        
        print("示例执行完成！")
        
    except Exception as e:
        print(f"示例执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行示例
    example_usage_async_task_manager()
