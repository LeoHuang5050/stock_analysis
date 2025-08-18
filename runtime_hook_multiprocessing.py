# PyInstaller运行时钩子 - 多进程支持
# 这个文件需要在PyInstaller打包时使用 --runtime-hook 参数指定

import sys
import os
import multiprocessing

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
    print("[Runtime Hook] 主进程检测到，开始设置多进程路径")
    
    # 为打包环境设置正确的路径
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        print(f"[Runtime Hook] 多进程路径设置完成，基础路径: {base_path}")
        
        # 确保billiard模块能够正确导入
        try:
            import billiard
            print("[Runtime Hook] billiard模块导入成功")
        except ImportError as e:
            print(f"[Runtime Hook] billiard模块导入失败: {e}")
            # 尝试添加billiard路径
            billiard_path = os.path.join(base_path, 'billiard')
            if os.path.exists(billiard_path):
                sys.path.insert(0, billiard_path)
                print(f"[Runtime Hook] 添加billiard路径: {billiard_path}")
        
        # 设置多进程相关路径
        try:
            # 添加当前目录到sys.path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
                print(f"[Runtime Hook] 添加当前目录到sys.path: {current_dir}")
            
            # 添加父目录到sys.path（如果存在）
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                print(f"[Runtime Hook] 添加父目录到sys.path: {parent_dir}")
                
        except Exception as e:
            print(f"[Runtime Hook] 设置路径时出错: {e}")
        
        print(f"[Runtime Hook] sys.path长度: {len(sys.path)}")
        print("[Runtime Hook] 多进程运行时钩子加载完成")
    else:
        print("[Runtime Hook] 非打包环境，跳过路径设置")
else:
    print("[Runtime Hook] 子进程检测到，跳过多进程路径设置")
