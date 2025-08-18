import sys
import os
import signal
import multiprocessing
import traceback
import time

def initialize_worker():
    """子进程初始化函数"""
    pid = os.getpid()
    is_frozen = getattr(sys, 'frozen', False)
    print(f"子进程 {pid}: 初始化开始 - {'打包模式 (_MEIPASS)' if is_frozen else '开发模式'}")
    
    if is_frozen:
        try:
            base_path = sys._MEIPASS
            base_path = base_path.encode('mbcs').decode('mbcs') if os.name == 'nt' else base_path
            sys.path.insert(0, base_path)
            print(f"子进程 {pid}: _MEIPASS 路径 = {base_path}")
            
            # 设置环境变量
            os.environ['PATH'] = base_path + os.pathsep + os.environ.get('PATH', '')
            if hasattr(os, 'add_dll_directory'):
                os.add_dll_directory(base_path)
            print(f"子进程 {pid}: DLL 搜索路径已设置")
        except Exception as e:
            print(f"子进程 {pid}: 设置 _MEIPASS 路径失败: {e}")
    
    # 尝试导入必要的模块
    try:
        import worker_threads_cy
        print(f"子进程 {pid}: 导入 worker_threads_cy 成功")
    except ImportError as e:
        with open('worker_error.log', 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 子进程 {pid} 导入 worker_threads_cy 失败: {e}\n")
        print(f"子进程 {pid}: 导入 worker_threads_cy 失败: {e}")
        raise  # 抛出异常，让 Pool 重新创建子进程
    
    # 关键：直接调用 _pool_worker_init 函数
    try:
        from worker_threads import _pool_worker_init
        print(f"子进程 {pid}: 调用 _pool_worker_init 开始")
        _pool_worker_init()
        print(f"子进程 {pid}: _pool_worker_init 调用完成")
    except Exception as e:
        print(f"子进程 {pid}: 调用 _pool_worker_init 失败: {e}")
        # 如果失败，记录错误并退出，让billiard重新创建
        with open('worker_error.log', 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - 子进程 {pid} _pool_worker_init 失败: {e}\n")
        sys.exit(1)
    
    print(f"子进程 {pid}: 初始化完成，进入等待状态")
    
    # 关键：子进程必须保持运行状态，等待billiard分配任务
    # 使用一个简单的等待循环，让billiard能够接管
    import time
    while True:
        time.sleep(1)  # 每秒检查一次，避免CPU占用过高
        # 这里可以添加一些检查逻辑，看是否被billiard接管
        # 但目前我们只能保持进程运行

def is_main_process():
    """检查是否为主进程"""
    try:
        current_process = multiprocessing.current_process()
        if getattr(sys, 'frozen', False):
            if 'MAIN_PROCESS_ID' in os.environ:
                main_pid = os.environ.get('MAIN_PROCESS_ID')
                return str(os.getpid()) == main_pid
            else:
                os.environ['MAIN_PROCESS_ID'] = str(os.getpid())
                return True
        else:
            return current_process.name == 'MainProcess'
    except Exception as e:
        print(f"检查进程类型时出错: {e}")
        return False

def exception_hook(exctype, value, tb):
    """全局异常处理函数"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(error_msg)
    
    # 延迟导入以避免子进程加载 PyQt5
    try:
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("程序错误")
        msg.setText("程序发生错误，请查看详细信息")
        msg.setDetailedText(error_msg)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    except Exception:
        # 子进程或无GUI环境下忽略对话框
        pass

def signal_handler(signum, frame):
    """信号处理函数，确保程序退出时清理资源"""
    print(f"收到信号 {signum}，正在清理资源...")
    # 关闭进程池
    try:
        from worker_threads import process_pool_manager
        if process_pool_manager is not None:
            process_pool_manager.shutdown()
            print("进程池已关闭")
    except Exception as e:
        print(f"关闭进程池时出错: {e}")
    sys.exit(0)

def main():
    # 检查是否为主进程，如果不是则直接返回
    if not is_main_process():
        print(f"子进程 {os.getpid()} 检测，跳过主程序执行")
        return
    
    # 只有主进程才会执行到这里
    # 设置multiprocessing启动方式为spawn（开发环境）
    try:
        if not getattr(sys, 'frozen', False):
            multiprocessing.set_start_method('spawn', force=True)
            print("设置multiprocessing启动方法为spawn")
        else:
            print("打包环境检测到，使用默认启动方法")
    except Exception as e:
        print(f"设置启动方法时出错: {e}")

    # 支持PyInstaller打包
    multiprocessing.freeze_support()

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 设置全局异常处理器
    sys.excepthook = exception_hook

    print(f"主进程启动 - PID: {os.getpid()}")
    print("正在初始化主应用程序...")

    # 延迟导入避免子进程加载 PyQt5 和 UI
    from PyQt5.QtWidgets import QApplication
    from ui.stock_analysis_ui_v2 import StockAnalysisApp

    app = QApplication(sys.argv)
    window = StockAnalysisApp()
    window.show()
    print("主应用程序启动完成")

    # 在主进程中初始化进程池，确保子进程不会执行
    try:
        print("开始初始化进程池...")
        from worker_threads import process_pool_manager
        if process_pool_manager is not None:
            process_pool_manager.initialize_pool()
            print("进程池初始化完成")
        else:
            print("警告：进程池管理器未初始化")
    except Exception as e:
        print(f"进程池初始化失败: {e}")

    sys.exit(app.exec_())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if is_main_process():
        # 只有主进程才执行main函数
        main()
    else:
        # 子进程执行自己的初始化逻辑
        print(f"子进程 {os.getpid()} 开始初始化...")
        initialize_worker()