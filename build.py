#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能打包脚本 - 自动检测文件并执行PyInstaller打包
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

def find_cython_file():
    """自动查找Cython编译后的.pyd文件"""
    patterns = [
        "worker_threads_cy.pyd",
        "worker_threads_cy.*.pyd",
        "worker_threads_cy.cp*.pyd"
    ]
    
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return files[0]
    
    return None

def find_runtime_hooks():
    """查找runtime hook文件"""
    hooks = []
    hook_files = [
        "runtime_hook.py",
        "runtime_hook_multiprocessing.py"
    ]
    
    for hook_file in hook_files:
        if os.path.exists(hook_file):
            hooks.append(hook_file)
    
    return hooks

def build_command(mode="release"):
    """构建打包命令"""
    
    # 基础命令
    base_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile"
    ]
    
    # 收集所有模块
    collect_all = [
        "numpy",
        "pandas", 
        "PyQt5",
        "billiard",
        "psutil"
    ]
    
    # 查找Cython文件
    cython_file = find_cython_file()
    if cython_file:
        collect_all.append("worker_threads_cy")
        print(f"✓ 找到Cython文件: {cython_file}")
    else:
        print("⚠ 未找到Cython文件，将跳过相关依赖")
    
    # 添加collect-all参数
    for module in collect_all:
        base_cmd.extend(["--collect-all", module])

    # 明确收集 Cython 扩展二进制
    base_cmd.extend(["--collect-binaries", "worker_threads_cy"])
    
    # 添加额外的二进制收集，确保Cython扩展的依赖被收集
    additional_binaries = [
        "numpy.core._multiarray_umath",
        "numpy.core._multiarray_tests", 
        "numpy.linalg._umath_linalg",
        "numpy.fft._pocketfft_internal",
        "numpy.random._common",
        "numpy.random._bounded_integers",
        "numpy.random._mt19937",
        "numpy.random._philox",
        "numpy.random._pcg64",
        "numpy.random._sfc64",
        "numpy.random._generator"
    ]
    
    for binary in additional_binaries:
        base_cmd.extend(["--collect-binaries", binary])
    
    # 隐藏导入
    hidden_imports = [
        "billiard", "billiard.pool", "billiard.connection", "billiard.managers",
        "billiard.synchronize", "billiard.heap", "billiard.queues", "billiard.process",
        "billiard.socket", "billiard.forking", "billiard.spawn", "billiard.util", "billiard.compat",
        "multiprocessing", "multiprocessing.pool", "multiprocessing.managers", "multiprocessing.synchronize",
        "multiprocessing.heap", "multiprocessing.queues", "multiprocessing.process", "multiprocessing.socket",
        "multiprocessing.forking", "multiprocessing.spawn", "multiprocessing.util", "multiprocessing.compat",
        "function", "ui", "worker_threads", "worker_entry"
    ]
    
    for imp in hidden_imports:
        base_cmd.extend(["--hidden-import", imp])
    
    # 查找runtime hooks - 只使用一个主要的runtime hook
    hooks = ["runtime_hook.py"]  # 只使用主要的runtime hook
    if os.path.exists("runtime_hook.py"):
        base_cmd.extend(["--runtime-hook", "runtime_hook.py"])
        print(f"✓ 使用主要runtime hook: runtime_hook.py")
    else:
        print("⚠ 未找到主要runtime hook")
    
    # 添加数据文件
    add_data = []
    
    # 不再将 .pyd 当作数据添加，交由 --collect-binaries 处理
    
    # 添加worker_entry.py
    if os.path.exists("worker_entry.py"):
        add_data.append("worker_entry.py;.")
    
    # 添加目录
    if os.path.exists("function"):
        add_data.append("function;function")
    if os.path.exists("ui"):
        add_data.append("ui;ui")
    
    for data in add_data:
        base_cmd.extend(["--add-data", data])
    
    # 输出路径
    base_cmd.extend([
        "--distpath", "./dist",
        "--workpath", "./build", 
        "--specpath", "."
    ])
    
    # 调试模式
    if mode == "debug":
        base_cmd.append("--debug")
        base_cmd.append("all")
        print("🔍 启用调试模式")
    
    # 主文件
    base_cmd.append("main.py")
    
    return base_cmd

def execute_build(mode="release"):
    """执行打包"""
    print(f"🚀 开始执行 {mode} 模式打包...")
    print("=" * 60)
    
    # 构建命令
    cmd = build_command(mode)
    
    # 显示完整命令
    print("完整打包命令:")
    print(" ".join(cmd))
    print("=" * 60)
    
    # 执行打包 - 使用实时输出
    try:
        print("正在执行打包，请稍候...")
        print("注意: 首次打包可能需要较长时间，请耐心等待")
        print("如果长时间没有输出，可能是依赖收集过程，请等待...")
        
        # 使用实时输出，避免卡住
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时显示输出，带超时检查
        import time
        start_time = time.time()
        last_output_time = start_time
        timeout_seconds = 300  # 5分钟超时
        
        while True:
            # 检查超时
            current_time = time.time()
            if current_time - start_time > timeout_seconds:
                print(f"⚠ 打包超时 ({timeout_seconds}秒)，正在终止进程...")
                process.terminate()
                time.sleep(2)
                if process.poll() is None:
                    process.kill()
                print("❌ 打包超时，已终止进程")
                return False
            
            # 尝试读取输出
            try:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    last_output_time = current_time
                else:
                    # 如果没有输出，短暂等待
                    time.sleep(0.1)
                    
                    # 如果长时间没有输出，显示进度提示
                    if current_time - last_output_time > 30:
                        elapsed = int(current_time - start_time)
                        print(f"⏳ 正在收集依赖... 已耗时: {elapsed}秒")
                        last_output_time = current_time
                        
            except Exception as e:
                print(f"⚠ 读取输出时出错: {e}")
                break
        
        # 等待进程完成
        return_code = process.poll()
        
        if return_code == 0:
            print("✅ 打包成功完成！")
            print(f"输出文件位置: ./dist/main.exe")
            return True
        else:
            print(f"❌ 打包失败！错误代码: {return_code}")
            return False
            
    except FileNotFoundError:
        print("❌ 错误: 未找到 pyinstaller 命令")
        print("请先安装: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"❌ 打包执行出错: {e}")
        return False

def main():
    """主函数"""
    print("🔧 PyInstaller 智能打包脚本")
    print("=" * 60)
    
    # 检查环境
    if not os.path.exists("main.py"):
        print("❌ 错误: 未找到 main.py 文件")
        print("请确保在正确的项目目录中运行此脚本")
        return
    
    # 检查PyInstaller
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
        print("✓ PyInstaller 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误: PyInstaller 未安装")
        print("请先安装: pip install pyinstaller")
        return
    
    # 显示可用模式
    print("\n可用打包模式:")
    print("1. release - 发布版本（推荐）")
    print("2. debug   - 调试版本（显示控制台）")
    
    # 获取用户选择
    while True:
        choice = input("\n请选择打包模式 (1/2 或直接回车使用release模式): ").strip()
        
        if choice == "" or choice == "1":
            mode = "release"
            break
        elif choice == "2":
            mode = "debug"
            break
        else:
            print("❌ 无效选择，请输入 1 或 2")
    
    # 执行打包
    success = execute_build(mode)
    
    if success:
        print("\n🎉 打包完成！")
        print("您可以在 ./dist 文件夹中找到 main.exe 文件")
        
        # 询问是否立即测试
        test_choice = input("\n是否立即测试打包后的程序？(y/N): ").strip().lower()
        if test_choice in ['y', 'yes']:
            exe_path = "./dist/main.exe"
            if os.path.exists(exe_path):
                print(f"🚀 启动测试: {exe_path}")
                try:
                    subprocess.Popen([exe_path])
                except Exception as e:
                    print(f"启动失败: {e}")
            else:
                print("❌ 未找到打包后的程序")
    else:
        print("\n❌ 打包失败，请检查错误信息")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断打包过程")
    except Exception as e:
        print(f"\n❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
