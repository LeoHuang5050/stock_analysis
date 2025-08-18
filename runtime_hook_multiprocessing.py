# PyInstaller运行时钩子 - 多进程支持
# 这个文件需要在PyInstaller打包时使用 --runtime-hook 参数指定

import os
import sys

def _setup_multiprocessing_paths():
    """为多进程环境设置正确的路径"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境
        base_path = sys._MEIPASS
        
        # 添加必要的路径
        paths_to_add = [
            base_path,  # PyInstaller基础路径
            os.path.join(base_path, 'lib'),  # 可能的库路径
            os.getcwd(),  # 当前工作目录
        ]
        
        for path in paths_to_add:
            if path and path not in sys.path:
                sys.path.insert(0, path)
        
        # 设置环境变量
        os.environ['PYTHONPATH'] = os.pathsep.join([base_path] + sys.path[1:])
        
        print(f"[Runtime Hook] 多进程路径设置完成，基础路径: {base_path}")
        print(f"[Runtime Hook] sys.path长度: {len(sys.path)}")

# 在模块导入时执行
_setup_multiprocessing_paths()

# 为billiard设置特殊处理
try:
    import billiard
    print("[Runtime Hook] billiard模块导入成功")
except ImportError as e:
    print(f"[Runtime Hook] billiard模块导入失败: {e}")
    # 尝试从MEIPASS导入
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        billiard_path = os.path.join(base_path, 'billiard')
        if os.path.exists(billiard_path):
            sys.path.insert(0, billiard_path)
            print(f"[Runtime Hook] 添加billiard路径: {billiard_path}")

print("[Runtime Hook] 多进程运行时钩子加载完成")
