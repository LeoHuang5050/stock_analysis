import sys
import os
import signal
import multiprocessing
from ui.stock_analysis_ui_v2 import StockAnalysisApp
from PyQt5.QtWidgets import QApplication, QMessageBox
import traceback
from worker_threads import ProcessPoolManager

def exception_hook(exctype, value, tb):
    """全局异常处理函数"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(error_msg)  # 同时在控制台打印错误信息
    
    # 创建错误对话框
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("程序错误")
    msg.setText("程序发生错误，请查看详细信息")
    msg.setDetailedText(error_msg)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

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

if __name__ == "__main__":
    # 检查是否为主进程
    if not is_main_process():
        print("检测到子进程，跳过主进程初始化")
        # 子进程不应该继续执行后续代码，应该进入等待状态
        # 让billiard的worker进程管理逻辑接管
        multiprocessing.freeze_support()  # 支持PyInstaller打包
        print("子进程已准备就绪，等待任务分配...")
        
        # 在进入等待循环之前，先初始化工作线程
        # 这样有任务提交时就能直接执行运算
        try:
            print("子进程开始初始化工作线程...")
            from worker_threads import _pool_worker_init
            if callable(_pool_worker_init):
                _pool_worker_init()
                print("子进程工作线程初始化完成")
            else:
                print("警告：_pool_worker_init 不可调用")
        except Exception as e:
            print(f"子进程工作线程初始化失败: {e}")
        
        # 子进程进入无限循环等待状态，不要执行后续的GUI初始化代码
        try:
            while True:
                import time
                time.sleep(1)  # 每秒检查一次，避免CPU占用过高
        except KeyboardInterrupt:
            print("子进程收到中断信号，退出")
            sys.exit(0)
    
    # 只有主进程才会执行到这里
    print(f"主进程启动 - PID: {os.getpid()}")
    
    # 设置multiprocessing启动方式为spawn（推荐用于打包后的程序）
    # 注意：billiard会自动处理启动方法，不需要强制设置
    try:
        # 只在非frozen环境下设置启动方法
        if not getattr(sys, 'frozen', False):
            multiprocessing.set_start_method('spawn', force=True)
            print("设置multiprocessing启动方法为spawn")
        else:
            print("打包环境检测到，使用默认启动方法")
    except Exception as e:
        print(f"设置启动方法时出错: {e}")
    
    multiprocessing.freeze_support()  # 支持PyInstaller打包
    
    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    # 设置全局异常处理器
    sys.excepthook = exception_hook
    
    print("正在初始化主应用程序...")
    app = QApplication(sys.argv)
    
    window = StockAnalysisApp()
    window.show()
    print("主应用程序启动完成")
    
    # 在GUI启动后初始化进程池
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