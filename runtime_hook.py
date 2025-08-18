# -*- coding: utf-8 -*-
"""
PyInstaller 运行时钩子，确保 multiprocessing 正常工作
"""

import multiprocessing
import sys
import os

def is_main_process():
    """检查是否为主进程"""
    try:
        # 检查进程名称
        current_process = multiprocessing.current_process()
        
        # 检查是否在打包环境中
        if getattr(sys, 'frozen', False):
            # 打包环境中，通过进程名称和环境变量来判断
            if current_process.name == 'MainProcess':
                # 检查是否设置了主进程标记
                if 'MAIN_PROCESS_ID' in os.environ:
                    # 如果环境变量中的PID与当前PID匹配，说明是主进程
                    main_pid = os.environ.get('MAIN_PROCESS_ID')
                    if str(os.getpid()) == main_pid:
                        return True
                    else:
                        return False
                else:
                    # 如果没有设置环境变量，说明这是第一次运行的主进程
                    # 设置环境变量标记
                    os.environ['MAIN_PROCESS_ID'] = str(os.getpid())
                    return True
            else:
                return False
        else:
            # 开发环境中，检查进程名称
            return current_process.name == 'MainProcess'
    except Exception as e:
        print(f"检查进程类型时出错: {e}")
        # 出错时默认认为是子进程，避免误判
        return False

# 只在主进程中执行runtime hook
if is_main_process():
    print("Runtime hook: 主进程检测到，开始初始化多进程环境")
    
    # 只在非frozen环境下设置进程启动方式
    if not getattr(sys, 'frozen', False):
        try:
            multiprocessing.set_start_method('spawn', force=True)
            print("Runtime hook: 设置进程启动方式为spawn")
        except Exception as e:
            print(f"Runtime hook: 设置进程启动方式失败: {e}")
    else:
        print("Runtime hook: 打包环境检测到，使用默认启动方式")
    
    # 确保 freeze_support 被调用（Python 3.13+ 中直接调用）
    try:
        multiprocessing.freeze_support()
        print("Runtime hook: freeze_support 已调用")
    except Exception as e:
        print(f"Runtime hook: freeze_support 调用失败: {e}")
    
    # 为打包环境设置正确的路径
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        print(f"Runtime hook: 打包环境基础路径: {base_path}")

        # 将 _MEIPASS 加入 PATH 与 DLL 搜索目录，便于 .pyd/.dll 解析
        try:
            os.environ['PATH'] = base_path + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(base_path)
            print("Runtime hook: 已添加 _MEIPASS 到 PATH/DLL 搜索路径")
        except Exception as e:
            print(f"Runtime hook: 添加 DLL 搜索路径失败: {e}")

        # 确保billiard模块能够正确导入
        try:
            import billiard
            print("Runtime hook: billiard模块导入成功")
        except ImportError as e:
            print(f"Runtime hook: billiard模块导入失败: {e}")
            billiard_path = os.path.join(base_path, 'billiard')
            if os.path.exists(billiard_path):
                sys.path.insert(0, billiard_path)
                print(f"Runtime hook: 添加billiard路径: {billiard_path}")
    
    print(f"Runtime hook: 进程启动方式: {multiprocessing.get_start_method()}")
    print(f"Runtime hook: 是否在 frozen 环境: {getattr(sys, 'frozen', False)}")
    print("Runtime hook: 主进程多进程环境初始化完成")
else:
    print("Runtime hook: 子进程检测到，跳过多进程环境初始化")
