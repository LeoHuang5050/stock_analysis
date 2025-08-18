# -*- coding: utf-8 -*-
"""
PyInstaller 运行时钩子，确保 multiprocessing 正常工作
"""

import multiprocessing
import sys

# 设置进程启动方式为 spawn（推荐用于打包后的程序）
multiprocessing.set_start_method('spawn', force=True)

# 确保 freeze_support 被调用（Python 3.13+ 中直接调用）
if hasattr(multiprocessing, 'freeze_support'):
    multiprocessing.freeze_support()

print("Runtime hook: multiprocessing 环境已配置")
print(f"进程启动方式: {multiprocessing.get_start_method()}")
print(f"是否在 frozen 环境: {getattr(sys, 'frozen', False)}")
