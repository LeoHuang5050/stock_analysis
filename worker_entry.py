#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作进程专用入口模块，完全避免导入PyQt5和任何可能导致崩溃的模块
这个模块只包含工作进程需要的功能，不包含GUI相关代码
"""

import sys
import os
import time
import traceback
import numpy as np

def worker_entry():
    """工作进程专用入口点，完全避免导入PyQt5"""
    try:
        frozen = getattr(sys, 'frozen', False)
        meipass = getattr(sys, '_MEIPASS', None)
        print(f"[WorkerEntry] 工作进程启动，PID: {os.getpid()}")
        print(f"[WorkerEntry] frozen={frozen} _MEIPASS={meipass}")

        if frozen and meipass:
            try:
                os.environ['PATH'] = meipass + os.pathsep + os.environ.get('PATH', '')
                if hasattr(os, 'add_dll_directory'):
                    os.add_dll_directory(meipass)
                print(f"[WorkerEntry] 已添加 _MEIPASS 到 PATH/DLL 搜索路径")
            except Exception as e:
                print(f"[WorkerEntry] 添加 DLL 搜索路径失败: {e}")

        # 尝试导入 worker_threads_cy
        try:
            import worker_threads_cy as wcy
            print(f"[WorkerEntry] worker_threads_cy 导入成功")
            if not hasattr(wcy, 'calculate_batch_cy'):
                raise ImportError('worker_threads_cy 缺少 calculate_batch_cy 函数')
            print(f"[WorkerEntry] worker_threads_cy 模块验证成功")
        except ImportError as e:
            print(f"[WorkerEntry] worker_threads_cy 导入失败: {e}")
            # 如果是 PyInstaller 环境，尝试从 _MEIPASS 导入
            if frozen and meipass:
                try:
                    if meipass not in sys.path:
                        sys.path.insert(0, meipass)
                    import worker_threads_cy as wcy
                    print(f"[WorkerEntry] 从 _MEIPASS 导入 worker_threads_cy 成功")
                except ImportError as e2:
                    print(f"[WorkerEntry] 从 _MEIPASS 导入也失败: {e2}")
                    # 不抛出异常，让子进程能继续运行
                    print(f"[WorkerEntry] 警告：worker_threads_cy 导入失败，但子进程继续运行")
                    return True

        print(f"[WorkerEntry] 工作进程初始化完成，PID: {os.getpid()}")
        return True

    except Exception as e:
        error_msg = f"[WorkerEntry] 工作进程初始化失败: {e}"
        print(error_msg)
        try:
            with open('worker_error.log', 'a', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [WorkerEntry] 初始化失败: {e}\n")
                f.write(f"进程PID: {os.getpid()}\n")
                f.write(f"frozen={getattr(sys,'frozen',False)} _MEIPASS={getattr(sys,'_MEIPASS',None)}\n")
                f.write(f"sys.path[:3]={sys.path[:3]}\n")
                f.write(f"当前工作目录: {os.getcwd()}\n")
                f.write(traceback.format_exc() + "\n\n")
        except Exception:
            pass
        # 不抛出异常，让子进程能继续运行
        print(f"[WorkerEntry] 错误已记录到 worker_error.log，子进程继续运行")
        return True

def cy_batch_worker(args):
    """Cython批处理工作函数，避免导入PyQt5"""
    try:
        print(f"[WorkerEntry] cy_batch_worker 开始执行，PID: {os.getpid()}")
        print(f"[WorkerEntry] 参数类型: {type(args)}")
        print(f"[WorkerEntry] 参数长度: {len(args) if hasattr(args, '__len__') else '不可迭代'}")
        
        # 尝试导入 worker_threads_cy
        try:
            import worker_threads_cy as wcy
            print(f"[WorkerEntry] worker_threads_cy 导入成功")
            if not hasattr(wcy, 'calculate_batch_cy'):
                raise ImportError('worker_threads_cy 缺少 calculate_batch_cy 函数')
            print(f"[WorkerEntry] calculate_batch_cy 函数存在")
        except ImportError as e:
            print(f"[WorkerEntry] 无法导入 worker_threads_cy: {e}")
            # 返回空结果，避免崩溃
            return {}
        
        # 解包参数
        try:
            print(f"[WorkerEntry] 开始解包参数...")
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
                profit_type,
                loss_type,
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
                comparison_vars,
            ) = args
            print(f"[WorkerEntry] 参数解包成功")
            
        except Exception as e:
            print(f"[WorkerEntry] 参数解包失败: {e}")
            return {}
        
        # 确保数据类型正确
        try:
            stock_idx_arr = np.ascontiguousarray(stock_idx_arr, dtype=np.int32)
        except Exception as e:
            print(f"[WorkerEntry] 数据类型转换失败: {e}")
            return {}
        
        # 调用Cython函数
        try:
            start_time = time.time()
            
            date_grouped_results = wcy.calculate_batch_cy(
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
                profit_type,
                loss_type,
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
                comparison_vars,
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 验证返回结果
            if date_grouped_results is None:
                print(f"[WorkerEntry] calculate_batch_cy返回None")
                return {}
            
            if not isinstance(date_grouped_results, dict):
                print(f"[WorkerEntry] calculate_batch_cy返回类型错误，期望dict，实际{type(date_grouped_results)}")
                return {}
            
            print(f"[WorkerEntry] 执行成功，耗时: {total_time:.4f}秒")
            return date_grouped_results
            
        except Exception as e:
            print(f"[WorkerEntry] calculate_batch_cy 执行失败: {e}")
            return {}
        
    except Exception as e:
        print(f"[WorkerEntry] cy_batch_worker 执行异常: {e}")
        # 返回空结果，避免崩溃
        return {}

# 测试函数
if __name__ == "__main__":
    print("测试 worker_entry 模块...")
    success = worker_entry()
    print(f"测试结果: {'成功' if success else '失败'}")
