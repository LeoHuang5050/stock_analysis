import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy, QDialog, QTabWidget, QMessageBox, QGridLayout, QDateEdit, QInputDialog, QAbstractItemView, QGroupBox, QCheckBox, QHeaderView, QScrollArea, QToolButton, QApplication, QMainWindow
from PyQt5.QtCore import QDate, QObject, QEvent, Qt, QTimer
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QColor, QCursor
import time
from function.common_widgets import TableSearchDialog

import math
import concurrent.futures
from multiprocessing import cpu_count
import re
import gc
import statistics

def format_overall_stat_value(value):
    """
    格式化总体统计值：
    - 正数向上取整，负数向下取整
    - 如1.2取整为2，-1.2取整为-2
    """
    if value is None:
        return None
    
    try:
        value = float(value)
        if value == 0:
            return 0
        # 正数向上取整，负数向下取整
        if value > 0:
            return math.ceil(value)  # 向上取整
        else:
            return math.floor(value)  # 向下取整
    except (ValueError, TypeError):
        return value

EXPR_PLACEHOLDER_TEXT = (
    "需要严格按照python表达式规则填入。\n"
    "规则提醒：\n"
    "1. 每个条件、赋值、if/else等都要符合python语法缩进（建议用4个空格）。\n"
    "2. 赋值用=，判断用==，不等于用!=。\n"
    "3. 逻辑与用and，或用or，非用not。\n"
    "4. 代码块必须用冒号结尾（如if/else/for/while等）。\n"
    "5. result变量必须在表达式中赋值，作为最终输出。\n"
    "6. 支持多行表达式，注意缩进和语法。\n"
    "示例:\n"
    "if INC != 0:\n    result = INC\nelse:\n    result = 0\n"
)

FORMULAR_EXPR_PLACEHOLDER_TEXT = (
    "需要严格按照python表达式规则填入。\n"
    "规则提醒：\n"
    "1. 每个条件、赋值、if/else等都要符合python语法缩进（建议用4个空格）。\n"
    "2. 赋值用=，判断用==，不等于用!=。\n"
    "3. 逻辑与用and，或用or，非用not。\n"
    "4. 代码块必须用冒号结尾（如if/else/for/while等）。\n"
    "5. result变量必须在表达式中赋值，作为最终输出。\n"
    "6. 支持多行表达式，注意缩进和语法。\n"
    "示例:\n"
    "if (\n    abs(CEV) < 3 and\n    abs(CEPV) < 3 and\n    abs(CEPPV) < 3000 and\n    abs(NDAYMAX) < 3000 and\n    abs(CSV) > 150 and\n    abs(CEPV) > 0 and\n    abs(CEPPV) > 0 and\n    CASFH > 3 * CASSH\n):\n    result = VNS + VPS\nelse:\n    result = 0"
)
# 连续累加值参数表头
param_headers = [
    "连续累加值长度", "连续累加值正加和", "连续累加值负加和", '连续累加值正加和前一半', '连续累加值正加和后一半', '连续累加值负加和前一半', '连续累加值负加和后一半',
    "连续累加值开始值", "连续累加值开始后1位值", "连续累加值开始后2位值",
    "连续累加值结束值", "连续累加值结束前1位值", "连续累加值结束前2位值",
    "连续累加值前一半绝对值之和", "连续累加值后一半绝对值之和",
    "连续累加值前四分之一绝对值之和", "连续累加值前四分之二绝对值之和",
    "连续累加值前四分之三绝对值之和", "连续累加值后四分之一绝对值之和"
]
# 有效累加值参数表头
valid_param_headers = [
    "有效累加值数组长度", "有效累加值正加值和", "有效累加值负加值和",
    "有效累加值前一半绝对值之和", "有效累加值后一半绝对值之和",
    "有效累加值前四分之1绝对值之和", "有效累加值前四分之1-2绝对值之和",
    "有效累加值前四分之2-3绝对值之和", "有效累加值后四分之1绝对值之和"
]
# 向前最大相关参数表头
forward_param_headers = [
    "向前最大日期",
    "向前最大连续累加值长度",
    "向前最大有效累加值数组长度", "向前最大有效累加值", "向前最大有效累加值正加值和", "向前最大有效累加值负加值和",
    "向前最大连续累加值正加值和", "向前最大连续累加值负加值和",
    "向前最大连续累加值开始值", "向前最大连续累加值开始后1位值", "向前最大连续累加值开始后2位值",
    "向前最大连续累加值结束值", "向前最大连续累加值结束前1位值", "向前最大连续累加值结束前2位值",
    "向前最大连续累加值前一半绝对值之和", "向前最大连续累加值后一半绝对值之和",
    "向前最大连续累加值前四分之1绝对值之和", "向前最大连续累加值前四分之1-2绝对值之和",
    "向前最大连续累加值前四分之2-3绝对值之和", "向前最大连续累加值后四分之1绝对值之和",
    "向前最大有效累加值数组前一半绝对值之和", "向前最大有效累加值数组后一半绝对值之和",
    "向前最大有效累加值数组前四分之1绝对值之和", "向前最大有效累加值数组前四分之1-2绝对值之和",
    "向前最大有效累加值数组前四分之2-3绝对值之和", "向前最大有效累加值数组后四分之1绝对值之和"
]
# 向前最小相关参数表头
forward_min_param_headers = [
    "向前最小日期",
    "向前最小连续累加值长度",
    "向前最小有效累加值数组长度", "向前最小有效累加值", "向前最小有效累加值正加值和", "向前最小有效累加值负加值和",
    "向前最小连续累加值正加值和", "向前最小连续累加值负加值和",
    "向前最小连续累加值开始值", "向前最小连续累加值开始后1位值", "向前最小连续累加值开始后2位值",
    "向前最小连续累加值结束值", "向前最小连续累加值结束前1位值", "向前最小连续累加值结束前2位值",
    "向前最小连续累加值前一半绝对值之和", "向前最小连续累加值后一半绝对值之和",
    "向前最小连续累加值前四分之1绝对值之和", "向前最小连续累加值前四分之1-2绝对值之和",
    "向前最小连续累加值前四分之2-3绝对值之和", "向前最小连续累加值后四分之1绝对值之和",
    "向前最小有效累加值数组前一半绝对值之和", "向前最小有效累加值数组后一半绝对值之和",
    "向前最小有效累加值数组前四分之1绝对值之和", "向前最小有效累加值数组前四分之1-2绝对值之和",
    "向前最小有效累加值数组前四分之2-3绝对值之和", "向前最小有效累加值数组后四分之1绝对值之和"
]

# 表格搜索事件过滤器
class TableSearchFilter(QObject):
    def __init__(self, table):
        super().__init__()
        self.table = table
        self.search_dialog = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.show_search_dialog()
            return True
        return super().eventFilter(obj, event)

    def show_search_dialog(self):
        if self.search_dialog is None or not self.search_dialog.isVisible():
            self.search_dialog = TableSearchDialog(self.table, self.table.parent())
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()
        self.search_dialog.input.setFocus()

def safe_val(val):
    import math
    if val is None:
        return ""
    if isinstance(val, float) and (math.isnan(val) or str(val).lower() == 'nan'):
        return ""
    # 如果是数字类型，保留两位小数
    if isinstance(val, (int, float)):
        return f"{val:.2f}"
    return val

def show_continuous_sum_table(parent, all_results, price_data, as_widget=False):
    try:
        if not all_results or not all_results.get("dates"):
            if not as_widget:
                QMessageBox.information(parent, "提示", "请先生成参数！")
            return None

        dates = all_results.get("dates", [])
        if not dates:
            if not as_widget:
                QMessageBox.information(parent, "提示", "没有可用的日期数据！")
            return None

        # 获取第一个日期的数据作为初始显示
        first_date_data = dates[0]
        end_date = first_date_data.get("end_date")
        stocks_data = first_date_data.get("stocks", [])

        # 按stock_idx排序
        stocks_data = sorted(stocks_data, key=lambda row: row.get('stock_idx', 0))

        if not stocks_data:
            if not as_widget:
                QMessageBox.information(parent, "提示", f"日期 {end_date} 没有股票数据！")
            return None

        tab_widget = QTabWidget(parent)
        # 统计最大长度
        max_len = max(int(row.get('continuous_len', 0)) for row in stocks_data)
        max_valid_len = max(len(row.get('valid_sum_arr', [])) for row in stocks_data)
        max_forward_len = max(len(row.get('forward_max_result', [])) for row in stocks_data)
        max_forward_min_len = max(len(row.get('forward_min_result', [])) for row in stocks_data)
        n_val = max(max_len, max_valid_len, max_forward_len, max_forward_min_len)

        # 创建四个表格
        headers1 = ['代码', '名称', '实际开始日期值', '计算开始日期'] + [f'连续累加值{i+1}' for i in range(max_len)] + param_headers
        headers2 = ['代码', '名称'] + [f'有效累加值{i+1}' for i in range(max_valid_len)] + valid_param_headers
        headers3 = ['代码', '名称', '向前最大日期'] + [f'向前最大连续累加值{i+1}' for i in range(max_forward_len)] + [h for h in forward_param_headers if h != "向前最大日期"]
        headers4 = ['代码', '名称', '向前最小日期'] + [f'向前最小连续累加值{i+1}' for i in range(max_forward_min_len)] + [h for h in forward_min_param_headers if h != "向前最小日期"]
        # 合并表头：连续累加值 + 空列 + 有效累加值
        merged_headers = headers1 + [''] + headers2[2:]
        table1 = QTableWidget(len(stocks_data), len(merged_headers))
        table3 = QTableWidget(len(stocks_data), len(headers3))
        table4 = QTableWidget(len(stocks_data), len(headers4))

        table1.setHorizontalHeaderLabels(merged_headers)
        table3.setHorizontalHeaderLabels(headers3)
        table4.setHorizontalHeaderLabels(headers4)

        # 安装Ctrl+F搜索事件过滤器并保存引用，防止被回收
        for idx, t in enumerate([table1, table3, table4]):
            f = TableSearchFilter(t)
            t.installEventFilter(f)
            setattr(tab_widget, f'search_filter_{idx+1}', f)

        def update_tables(stocks_data):
            stocks_data = sorted(stocks_data, key=lambda row: row.get('stock_idx', 0))
            table1.setRowCount(len(stocks_data))
            for row_idx, row in enumerate(stocks_data):
                stock_idx = row.get('stock_idx', 0)
                code = row.get('code', '')
                name = row.get('name', '')
                # 实际开始日期值
                actual_value_val = row.get('actual_value', '')
                
                # 检查是否有连续三个0
                has_three_consecutive_zeros = row.get('has_three_consecutive_zeros', False)
                
                # 设置股票代码
                code_item = QTableWidgetItem(str(code))
                if has_three_consecutive_zeros:
                    code_item.setForeground(QColor('red'))
                table1.setItem(row_idx, 0, code_item)
                
                # 设置股票名称
                name_item = QTableWidgetItem(str(name))
                if has_three_consecutive_zeros:
                    name_item.setForeground(QColor('red'))
                table1.setItem(row_idx, 1, name_item)
                table1.setItem(row_idx, 2, QTableWidgetItem(str(safe_val(actual_value_val))))
                table1.setItem(row_idx, 3, QTableWidgetItem(str(safe_val(row.get('actual_value_date', '')))))
                results = row.get('continuous_results', [])
                for col_idx in range(max_len):
                    val = results[col_idx] if col_idx < len(results) else ""
                    table1.setItem(row_idx, 4 + col_idx, QTableWidgetItem(str(safe_val(val))))
                param_values = [
                    row.get('continuous_len', ''),
                    row.get('cont_sum_pos_sum', ''),
                    row.get('cont_sum_neg_sum', ''),
                    row.get('cont_sum_pos_sum_first_half', ''),
                    row.get('cont_sum_pos_sum_second_half', ''),
                    row.get('cont_sum_neg_sum_first_half', ''),
                    row.get('cont_sum_neg_sum_second_half', ''),
                    row.get('continuous_start_value', ''),
                    row.get('continuous_start_next_value', ''),
                    row.get('continuous_start_next_next_value', ''),
                    row.get('continuous_end_value', ''),
                    row.get('continuous_end_prev_value', ''),
                    row.get('continuous_end_prev_prev_value', ''),
                    row.get('continuous_abs_sum_first_half', ''),
                    row.get('continuous_abs_sum_second_half', ''),
                    row.get('continuous_abs_sum_block1', ''),
                    row.get('continuous_abs_sum_block2', ''),
                    row.get('continuous_abs_sum_block3', ''),
                    row.get('continuous_abs_sum_block4', ''),
                ]
                for i, val in enumerate(param_values):
                    table1.setItem(row_idx, 4 + max_len + i, QTableWidgetItem(str(safe_val(val))))
                # 空一列
                table1.setItem(row_idx, 4 + max_len + len(param_values), QTableWidgetItem(""))
                # 有效累加值内容
                valid_arr = row.get('valid_sum_arr', [])
                for col_idx in range(max_valid_len):
                    val = valid_arr[col_idx] if col_idx < len(valid_arr) else ""
                    table1.setItem(row_idx, 4 + max_len + len(param_values) + 1 + col_idx, QTableWidgetItem(str(safe_val(val))))
                valid_param_values = [
                    row.get('valid_sum_len', ''),
                    row.get('valid_pos_sum', ''),
                    row.get('valid_neg_sum', ''),
                    row.get('valid_abs_sum_first_half', ''),
                    row.get('valid_abs_sum_second_half', ''),
                    row.get('valid_abs_sum_block1', ''),
                    row.get('valid_abs_sum_block2', ''),
                    row.get('valid_abs_sum_block3', ''),
                    row.get('valid_abs_sum_block4', ''),
                ]
                for i, val in enumerate(valid_param_values):
                    table1.setItem(row_idx, 4 + max_len + len(param_values) + 1 + max_valid_len + i, QTableWidgetItem(str(safe_val(val))))

            # table3
            table3.setRowCount(len(stocks_data))
            for row_idx, row in enumerate(stocks_data):
                stock_idx = row.get('stock_idx', 0)
                code = row.get('code', '')
                name = row.get('name', '')
                table3.setItem(row_idx, 0, QTableWidgetItem(str(code)))
                table3.setItem(row_idx, 1, QTableWidgetItem(str(name)))
                table3.setItem(row_idx, 2, QTableWidgetItem(str(row.get('forward_max_date', ''))))
                forward_arr = row.get('forward_max_result', [])
                for col_idx in range(max_forward_len):
                    val = forward_arr[col_idx] if col_idx < len(forward_arr) else ""
                    table3.setItem(row_idx, 3 + col_idx, QTableWidgetItem(str(val)))
                # 新增：向前最大连续累加值长度，放在连续累加值打印完之后
                table3.setItem(row_idx, 3 + max_forward_len, QTableWidgetItem(str(row.get('forward_max_result_len', ''))))
                # 合并后的参数列表，顺序与表头一致
                forward_param_values = [
                    row.get('forward_max_valid_sum_len', ''),
                    row.get('forward_max_valid_sum_arr', ''),
                    row.get('forward_max_valid_pos_sum', ''),
                    row.get('forward_max_valid_neg_sum', ''),
                    row.get('forward_max_cont_sum_pos_sum', ''),
                    row.get('forward_max_cont_sum_neg_sum', ''),
                    row.get('forward_max_continuous_start_value', ''),
                    row.get('forward_max_continuous_start_next_value', ''),
                    row.get('forward_max_continuous_start_next_next_value', ''),
                    row.get('forward_max_continuous_end_value', ''),
                    row.get('forward_max_continuous_end_prev_value', ''),
                    row.get('forward_max_continuous_end_prev_prev_value', ''),
                    row.get('forward_max_abs_sum_first_half', ''),
                    row.get('forward_max_abs_sum_second_half', ''),
                    row.get('forward_max_abs_sum_block1', ''),
                    row.get('forward_max_abs_sum_block2', ''),
                    row.get('forward_max_abs_sum_block3', ''),
                    row.get('forward_max_abs_sum_block4', ''),
                    row.get('forward_max_valid_abs_sum_first_half', ''),
                    row.get('forward_max_valid_abs_sum_second_half', ''),
                    row.get('forward_max_valid_abs_sum_block1', ''),
                    row.get('forward_max_valid_abs_sum_block2', ''),
                    row.get('forward_max_valid_abs_sum_block3', ''),
                    row.get('forward_max_valid_abs_sum_block4', ''),
                ]
                for i, val in enumerate(forward_param_values):
                    table3.setItem(row_idx, 4 + max_forward_len + i, QTableWidgetItem(str(safe_val(val))))

            # table4
            table4.setRowCount(len(stocks_data))
            for row_idx, row in enumerate(stocks_data):
                stock_idx = row.get('stock_idx', 0)
                code = row.get('code', '')
                name = row.get('name', '')
                table4.setItem(row_idx, 0, QTableWidgetItem(str(code)))
                table4.setItem(row_idx, 1, QTableWidgetItem(str(name)))
                table4.setItem(row_idx, 2, QTableWidgetItem(str(row.get('forward_min_date', ''))))
                forward_min_arr = row.get('forward_min_result', [])
                for col_idx in range(max_forward_min_len):
                    val = forward_min_arr[col_idx] if col_idx < len(forward_min_arr) else ""
                    table4.setItem(row_idx, 3 + col_idx, QTableWidgetItem(str(val)))
                # 新增：向前最小连续累加值长度，放在连续累加值打印完之后
                table4.setItem(row_idx, 3 + max_forward_min_len, QTableWidgetItem(str(row.get('forward_min_result_len', ''))))
                # 合并后的参数列表，顺序与表头一致
                forward_min_param_values = [
                    row.get('forward_min_valid_sum_len', ''),
                    row.get('forward_min_valid_sum_arr', ''),
                    row.get('forward_min_valid_pos_sum', ''),
                    row.get('forward_min_valid_neg_sum', ''),
                    row.get('forward_min_cont_sum_pos_sum', ''),
                    row.get('forward_min_cont_sum_neg_sum', ''),
                    row.get('forward_min_continuous_start_value', ''),
                    row.get('forward_min_continuous_start_next_value', ''),
                    row.get('forward_min_continuous_start_next_next_value', ''),
                    row.get('forward_min_continuous_end_value', ''),
                    row.get('forward_min_continuous_end_prev_value', ''),
                    row.get('forward_min_continuous_end_prev_prev_value', ''),
                    row.get('forward_min_abs_sum_first_half', ''),
                    row.get('forward_min_abs_sum_second_half', ''),
                    row.get('forward_min_abs_sum_block1', ''),
                    row.get('forward_min_abs_sum_block2', ''),
                    row.get('forward_min_abs_sum_block3', ''),
                    row.get('forward_min_abs_sum_block4', ''),
                    row.get('forward_min_valid_abs_sum_first_half', ''),
                    row.get('forward_min_valid_abs_sum_second_half', ''),
                    row.get('forward_min_valid_abs_sum_block1', ''),
                    row.get('forward_min_valid_abs_sum_block2', ''),
                    row.get('forward_min_valid_abs_sum_block3', ''),
                    row.get('forward_min_valid_abs_sum_block4', ''),
                ]
                for i, val in enumerate(forward_min_param_values):
                    table4.setItem(row_idx, 4 + max_forward_min_len + i, QTableWidgetItem(str(safe_val(val))))

            # 设置表格列宽自适应
            table1.resizeColumnsToContents()
            table3.resizeColumnsToContents()
            table4.resizeColumnsToContents()

            # 设置表头样式
            for table in [table1, table3, table4]:
                table.horizontalHeader().setFixedHeight(50)
                table.horizontalHeader().setStyleSheet("font-size: 12px;")

        # 初始化表格内容
        update_tables(stocks_data)

        tab_widget.addTab(table1, f"连续累加值 ({end_date})")
        tab_widget.addTab(table3, f"向前最大连续累加值 ({end_date})")
        tab_widget.addTab(table4, f"向前最小连续累加值 ({end_date})")

        # --- 新增：恢复选中行 ---
        if hasattr(parent, 'last_selected_row_continuous') and parent.last_selected_row_continuous is not None:
            try:
                table1.selectRow(parent.last_selected_row_continuous)
            except Exception:
                pass
        # --- 新增：保存选中行 ---
        def save_selected_row():
            parent.last_selected_row_continuous = table1.currentRow()
        table1.itemSelectionChanged.connect(save_selected_row)

        # 主布局（去除顶部日期选择器）
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)

        if as_widget:
            container = QWidget(parent)
            container.setLayout(main_layout)
            container.setMinimumSize(1200, 600)
            container.show()
            return container
        else:
            dialog = QWidget()
            dialog.setLayout(main_layout)
            dialog.resize(1200, 600)
            dialog.show()
            return dialog
    except Exception as e:
        print("show_continuous_sum_table 异常:", e)
        return None
    
def show_formula_select_table_result_window(table, content_widget):
    # 获取主窗口引用
    parent = content_widget.parent()
    while parent and not hasattr(parent, 'formula_select_result_window'):
        parent = parent.parent()
    
    if parent is None:
        # 如果找不到主窗口，回退到原来的逻辑
        if not hasattr(content_widget, 'result_window') or content_widget.result_window is None:
            result_window = QMainWindow()
            result_window.setWindowTitle("选股结果")
            flags = result_window.windowFlags()
            flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
            flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
            result_window.setWindowFlags(flags)
            content_widget.result_window = result_window
        else:
            result_window = content_widget.result_window
            # 如果窗口最小化，则恢复显示
            if result_window.isMinimized():
                result_window.showNormal()
            # 确保窗口在最前面
            result_window.raise_()
            result_window.activateWindow()
        
        # 替换内容
        central_widget = QWidget()
        layout_ = QVBoxLayout(central_widget)
        layout_.addWidget(table)
        result_window.setCentralWidget(central_widget)
        result_window.resize(1200, 450)
        result_window.show()
        content_widget.result_window = result_window
        content_widget.result_table = table
    else:
        # 使用主窗口级别的窗口管理
        if not hasattr(parent, 'formula_select_result_window') or parent.formula_select_result_window is None:
            result_window = QMainWindow()
            result_window.setWindowTitle("选股结果")
            flags = result_window.windowFlags()
            flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
            flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
            result_window.setWindowFlags(flags)
            parent.formula_select_result_window = result_window
        else:
            result_window = parent.formula_select_result_window
            # 如果窗口最小化，则恢复显示
            if result_window.isMinimized():
                result_window.showNormal()
            # 确保窗口在最前面
            result_window.raise_()
            result_window.activateWindow()
        
        # 替换内容
        central_widget = QWidget()
        layout_ = QVBoxLayout(central_widget)
        layout_.addWidget(table)
        
        # 添加导航按钮
        if hasattr(parent, 'all_param_result') and parent.all_param_result:
            # 创建按钮容器
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(10, 5, 10, 10)
            button_layout.setSpacing(10)
            
            # 获取当前日期和可用日期列表
            workdays_str = getattr(parent.init, 'workdays_str', [])
            
            # 使用缓存的日期索引，如果没有则使用第一个日期
            if hasattr(parent, 'last_selected_date_idx_for_navigation') and parent.last_selected_date_idx_for_navigation is not None:
                current_date_idx = parent.last_selected_date_idx_for_navigation
                if 0 <= current_date_idx < len(workdays_str):
                    current_date = workdays_str[current_date_idx]
                else:
                    current_date = workdays_str[0] if workdays_str else None
                    current_date_idx = 0
            else:
                current_dates = list(parent.all_param_result.get('dates', {}).keys())
                if current_dates and workdays_str:
                    current_date = current_dates[0]  # 当前显示的日期
                    current_date_idx = workdays_str.index(current_date) if current_date in workdays_str else -1
                else:
                    current_date = None
                    current_date_idx = -1
            
            if current_date is not None and current_date_idx >= 0:
                # 向左按钮
                left_btn = QPushButton("向左")
                left_btn.setFixedWidth(80)
                left_btn.setEnabled(current_date_idx > 0)  # 如果不是第一个交易日，则启用
                
                # 向右按钮
                right_btn = QPushButton("向右")
                right_btn.setFixedWidth(80)
                right_btn.setEnabled(current_date_idx < len(workdays_str) - 1)  # 如果不是最后一个交易日，则启用
                
                # 添加按钮到布局
                button_layout.addStretch()  # 左侧弹性空间
                button_layout.addWidget(left_btn)
                button_layout.addWidget(right_btn)
                button_layout.addStretch()  # 右侧弹性空间
                
                # 按钮点击事件
                def on_left_clicked():
                    if current_date_idx > 0:
                        target_date = workdays_str[current_date_idx - 1]
                        # 更新缓存的日期索引
                        parent.last_selected_date_idx_for_navigation = current_date_idx - 1
                        # 重新执行选股逻辑，使用新的日期
                        perform_stock_selection_for_date(parent, target_date)
                
                def on_right_clicked():
                    if current_date_idx < len(workdays_str) - 1:
                        target_date = workdays_str[current_date_idx + 1]
                        # 更新缓存的日期索引
                        parent.last_selected_date_idx_for_navigation = current_date_idx + 1
                        # 重新执行选股逻辑，使用新的日期
                        perform_stock_selection_for_date(parent, target_date)
                
                left_btn.clicked.connect(on_left_clicked)
                right_btn.clicked.connect(on_right_clicked)
                
                # 将按钮容器添加到主布局
                layout_.addWidget(button_container)
        
        result_window.setCentralWidget(central_widget)
        result_window.resize(1200, 450)
        result_window.show()
        parent.formula_select_result_window = result_window
        parent.formula_select_result_table = table

def perform_stock_selection_for_date(parent, target_date):
    """为指定日期重新执行选股逻辑"""
    try:
        # 获取当前的选股参数
        formula_expr = getattr(parent, 'last_formula_expr', '')
        select_count = getattr(parent, 'last_select_count', 10)
        sort_mode = getattr(parent, 'last_sort_mode', '最大值排序')
        profit_type = getattr(parent, 'last_profit_type', 'INC')
        loss_type = getattr(parent, 'last_loss_type', 'INC')
        
        # 获取比较变量（如果有的话）
        comparison_vars = []
        if hasattr(parent, 'last_formula_select_state'):
            # 这里需要根据实际情况获取比较变量
            # 暂时使用空列表，可以根据需要扩展
            pass
        
        # 重新执行选股
        all_param_result = parent.get_or_calculate_result(
            formula_expr=formula_expr,
            select_count=select_count,
            sort_mode=sort_mode,
            show_main_output=False,
            only_show_selected=False,
            comparison_vars=comparison_vars,
            profit_type=profit_type,
            loss_type=loss_type,
            end_date=target_date
        )
        
        if all_param_result is None:
            QMessageBox.information(parent, "提示", "无法获取选股结果")
            return
        
        merged_results = all_param_result.get('dates', {})
        
        # 检查目标日期是否有数据
        if target_date not in merged_results:
            QMessageBox.information(parent, "提示", f"日期 {target_date} 没有选股数据")
            return
        
        # 根据排序模式过滤结果
        filtered_results = {}
        for date, results in merged_results.items():
            if date == target_date:
                # 排除统计行（stock_idx为-3, -2, -1的行）
                valid_results = [r for r in results if r.get('stock_idx', 0) >= 0]
                
                # 根据排序模式过滤score
                if sort_mode == "最大值排序":
                    filtered_results[date] = [r for r in valid_results if r.get('score') is not None and r.get('score', 0) > 0]
                else:  # 最小值排序
                    filtered_results[date] = [r for r in valid_results if r.get('score') is not None and r.get('score', 0) < 0]
                
                # 按score排序
                if sort_mode == "最大值排序":
                    filtered_results[date].sort(key=lambda x: x['score'], reverse=True)
                else:  # 最小值排序
                    filtered_results[date].sort(key=lambda x: x['score'])
                
                # 只保留指定数量的结果
                filtered_results[date] = filtered_results[date][:select_count]
        
        # 使用过滤后的结果
        if not filtered_results or not any(filtered_results.values()):
            QMessageBox.information(parent, "提示", f"日期 {target_date} 没有选股结果")
            return
        
        # 更新结果数据
        parent.last_formula_select_result_data = {'dates': filtered_results}
        
        # 更新缓存的日期索引
        workdays_str = getattr(parent.init, 'workdays_str', [])
        if target_date in workdays_str:
            parent.last_selected_date_idx_for_navigation = workdays_str.index(target_date)
        
        # 重新生成表格
        table = show_formula_select_table_result(parent, parent.last_formula_select_result_data, 
                                               getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), 
                                               is_select_action=True)
        
        # 更新窗口内容
        if hasattr(parent, 'formula_select_result_window') and parent.formula_select_result_window is not None:
            # 获取当前窗口的中央部件
            central_widget = parent.formula_select_result_window.centralWidget()
            if central_widget:
                # 清除旧的内容
                layout = central_widget.layout()
                if layout:
                    # 移除旧的表格
                    while layout.count() > 0:
                        item = layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                    
                    # 添加新的表格
                    layout.addWidget(table)
                    
                    # 重新添加导航按钮
                    if hasattr(parent, 'all_param_result') and parent.all_param_result:
                        # 创建按钮容器
                        button_container = QWidget()
                        button_layout = QHBoxLayout(button_container)
                        button_layout.setContentsMargins(10, 5, 10, 10)
                        button_layout.setSpacing(10)
                        
                        # 获取当前日期和可用日期列表
                        workdays_str = getattr(parent.init, 'workdays_str', [])
                        
                        # 使用缓存的日期索引
                        if hasattr(parent, 'last_selected_date_idx_for_navigation') and parent.last_selected_date_idx_for_navigation is not None:
                            current_date_idx = parent.last_selected_date_idx_for_navigation
                            if 0 <= current_date_idx < len(workdays_str):
                                current_date = workdays_str[current_date_idx]
                            else:
                                current_date = workdays_str[0] if workdays_str else None
                                current_date_idx = 0
                        else:
                            current_date = target_date  # 更新为新的目标日期
                            current_date_idx = workdays_str.index(current_date) if current_date in workdays_str else -1
                        
                        if current_date is not None and current_date_idx >= 0:
                            # 向左按钮
                            left_btn = QPushButton("向左")
                            left_btn.setFixedWidth(80)
                            left_btn.setEnabled(current_date_idx > 0)
                            
                            # 向右按钮
                            right_btn = QPushButton("向右")
                            right_btn.setFixedWidth(80)
                            right_btn.setEnabled(current_date_idx < len(workdays_str) - 1)
                            
                            # 添加按钮到布局
                            button_layout.addStretch()
                            button_layout.addWidget(left_btn)
                            button_layout.addWidget(right_btn)
                            button_layout.addStretch()
                            
                            # 按钮点击事件
                            def on_left_clicked():
                                if current_date_idx > 0:
                                    new_target_date = workdays_str[current_date_idx - 1]
                                    # 更新缓存的日期索引
                                    parent.last_selected_date_idx_for_navigation = current_date_idx - 1
                                    perform_stock_selection_for_date(parent, new_target_date)
                            
                            def on_right_clicked():
                                if current_date_idx < len(workdays_str) - 1:
                                    new_target_date = workdays_str[current_date_idx + 1]
                                    # 更新缓存的日期索引
                                    parent.last_selected_date_idx_for_navigation = current_date_idx + 1
                                    perform_stock_selection_for_date(parent, new_target_date)
                            
                            left_btn.clicked.connect(on_left_clicked)
                            right_btn.clicked.connect(on_right_clicked)
                            
                            # 将按钮容器添加到主布局
                            layout.addWidget(button_container)
                    
                    # 更新表格引用
                    parent.formula_select_result_table = table
                    
    except Exception as e:
        QMessageBox.warning(parent, "错误", f"重新选股时出错: {str(e)}")
        print(f"重新选股时出错: {e}")

def unify_date_columns(df):
    new_columns = []
    for col in df.columns:
        col_str = str(col)
        if col_str[:4].isdigit() and '-' in col_str:
            new_columns.append(col_str[:10])
        else:
            new_columns.append(col_str)
    df.columns = new_columns
    return df

def get_workdays(end_date, width):
    days = []
    cur = end_date
    while len(days) < width:
        if chinese_calendar.is_workday(cur):
            days.append(cur.strftime('%Y-%m-%d'))
        cur -= timedelta(days=1)
    days.reverse()
    return days

def query_row_result(rows, keyword, n_days=0):
    """
    用户输入如果能转为数字则转为字符串后与所有code转数字再转字符串的结果比对，否则直接与名称精确比对。
    n_days用于打印前N日最大值。
    """
    keyword = str(keyword).strip()
    results = []
    # 判断是否为数字型代码
    try:
        keyword_num = str(int(keyword))
        is_code = True
    except Exception:
        is_code = False
    for row in rows:
        code_str = str(row['code'])
        try:
            code_num = str(int(code_str))
        except Exception:
            code_num = code_str
        if (is_code and keyword_num == code_num) or (not is_code and keyword == str(row['name'])):
            info = (
                f"代码={row['code']}，名称={row['name']}，"
                f"最大值={row.get('max_value', '无')}，"
                f"最小值={row.get('min_value', '无')}，"
                f"结束值={row.get('end_value', '无')}，"
                f"开始值={row.get('start_value', '无')}，"
                f"实际开始值={row.get('actual_value', '无')}，"
                f"最接近值={row.get('closest_value', '无')}，"
                f"前1组结束地址前N日的最高值：{row.get('n_max_value', '无')}，"
                f"第1组后N最大值逻辑：{row.get('n_max_is_max', '无')}，"
                f"开始日到结束日之间最高价/最低价小于M：{row.get('range_ratio_is_less', '无')}，"
                f"开始日到结束日之间连续累加值绝对值小于：{row.get('continuous_abs_is_less', '无')}，"
                f"开始日到结束日之间有效累加值绝对值小于：{row.get('valid_abs_is_less', '无')}，"
                f"前1组结束地址前1日涨跌幅：{row.get('prev_day_change', '无')}%，"
                f"前1组结束日涨跌幅：{row.get('end_day_change', '无')}%，"
                f"后一组结束地址值：{row.get('diff_end_value', '无')}, "
                f"\n"
                f"\n"
                f"连续累加值={row['continuous_results']}，"
                f"连续累加值长度：{row.get('continuous_len', '无')}, "
                f"连续累加值开始值：{row.get('continuous_start_value', '无')}, "
                f"连续累加值开始后1位值：{row.get('continuous_start_next_value', '无')}, "
                f"连续累加值开始后2位值：{row.get('continuous_start_next_next_value', '无')}, "
                f"连续累加值结束值：{row.get('continuous_end_value', '无')}, "
                f"连续累加值结束前1位值：{row.get('continuous_end_prev_value', '无')}, "
                f"连续累加值结束前2位值：{row.get('continuous_end_prev_prev_value', '无')}, "
                f"连续累加值前一半绝对值之和：{row.get('continuous_abs_sum_first_half', '无')}, "
                f"连续累加值后一半绝对值之和：{row.get('continuous_abs_sum_second_half', '无')}, "
                f"连续累加值前四分之一绝对值之和：{row.get('continuous_abs_sum_block1', '无')}, "
                f"连续累加值前四分之二绝对值之和：{row.get('continuous_abs_sum_block2', '无')}, "
                f"连续累加值前四分之三绝对值之和：{row.get('continuous_abs_sum_block3', '无')}, "
                f"连续累加值后四分之一绝对值之和：{row.get('continuous_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"有效累加值：{row.get('valid_sum_arr', '无')}, "
                f"有效累加值数组长度：{row.get('valid_sum_len', '无')}, "
                f"有效累加值正加值和：{row.get('valid_pos_sum', '无')}, "
                f"有效累加值负加值和：{row.get('valid_neg_sum', '无')}, "
                f"有效累加值前一半绝对值之和：{row.get('valid_abs_sum_first_half', '无')}, "
                f"有效累加值后一半绝对值之和：{row.get('valid_abs_sum_second_half', '无')}, "
                f"有效累加值前四分之1绝对值之和：{row.get('valid_abs_sum_block1', '无')}, "
                f"有效累加值前四分之1-2绝对值之和：{row.get('valid_abs_sum_block2', '无')}, "
                f"有效累加值前四分之2-3绝对值之和：{row.get('valid_abs_sum_block3', '无')}, "
                f"有效累加值后四分之1绝对值之和：{row.get('valid_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"向前最大日期={row['forward_max_date']}，向前最大连续累加值={row['forward_max_result']}，"
                f"向前最大有效累加值数组长度：{row.get('forward_max_valid_sum_len', '无')}, "
                f"向前最大有效累加值：{row.get('forward_max_valid_sum_arr', '无')}, "
                f"向前最大有效累加值正加值和：{row.get('forward_max_valid_pos_sum', '无')}, "
                f"向前最大有效累加值负加值和：{row.get('forward_max_valid_neg_sum', '无')}, "
                f"向前最大有效累加值数组前一半绝对值之和：{row.get('forward_max_valid_abs_sum_first_half', '无')}, "
                f"向前最大有效累加值数组后一半绝对值之和：{row.get('forward_max_valid_abs_sum_second_half', '无')}, "
                f"向前最大有效累加值数组前四分之1绝对值之和：{row.get('forward_max_valid_abs_sum_block1', '无')}, "
                f"向前最大有效累加值数组前四分之1-2绝对值之和：{row.get('forward_max_valid_abs_sum_block2', '无')}, "
                f"向前最大有效累加值数组前四分之2-3绝对值之和：{row.get('forward_max_valid_abs_sum_block3', '无')}, "
                f"向前最大有效累加值数组后四分之1绝对值之和：{row.get('forward_max_valid_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"向前最小日期={row['forward_min_date']}，向前最小连续累加值={row['forward_min_result']}，"
                f"向前最小有效累加值数组长度：{row.get('forward_min_valid_sum_len', '无')}, "
                f"向前最小有效累加值：{row.get('forward_min_valid_sum_arr', '无')}, "
                f"向前最小有效累加值正加值和：{row.get('forward_min_valid_pos_sum', '无')}, "
                f"向前最小有效累加值负加值和：{row.get('forward_min_valid_neg_sum', '无')}, "
                f"向前最小有效累加值数组前一半绝对值之和：{row.get('forward_min_valid_abs_sum_first_half', '无')}, "
                f"向前最小有效累加值数组后一半绝对值之和：{row.get('forward_min_valid_abs_sum_second_half', '无')}, "
                f"向前最小有效累加值数组前四分之1绝对值之和：{row.get('forward_min_valid_abs_sum_block1', '无')}, "
                f"向前最小有效累加值数组前四分之1-2绝对值之和：{row.get('forward_min_valid_abs_sum_block2', '无')}, "
                f"向前最小有效累加值数组前四分之2-3绝对值之和：{row.get('forward_min_valid_abs_sum_block3', '无')}, "
                f"向前最小有效累加值数组后四分之1绝对值之和：{row.get('forward_min_valid_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"递增值：{row.get('increment_value', '无')}, "
                f"后值大于结束地址值：{row.get('after_gt_end_value', '无')}, "
                f"后值大于前值返回值：{row.get('after_gt_start_value', '无')}, "
                f"操作值：{row.get('ops_value', '无')}, "
                f"持有天数：{row.get('hold_days', '无')}, "
                f"操作涨幅：{row.get('ops_change', '无')}%, "
                f"调整天数：{row.get('adjust_days', '无')}, "
                f"日均涨幅：{row.get('ops_incre_rate', '无')}%"
            )
            results.append(info)
    if not results:
        return f"未找到与'{keyword}'相关的股票信息。"
    return '\n'.join(results)
def show_params_table(parent, all_results, end_date=None, n_days=0, n_days_max=0, range_value=None, continuous_abs_threshold=None, as_widget=False, price_data=None):
    if not all_results or not all_results.get("dates"):
        QMessageBox.information(parent, "提示", "请先生成参数！")
        return None
    dates = all_results.get("dates", [])
    if not dates:
        QMessageBox.information(parent, "提示", "没有可用的日期数据！")
        return None

    # 新增：直接取第一个日期数据
    last_date_data = None
    if isinstance(dates, dict):
        # dates是dict，直接取第一个key的数据
        if dates:
            first_key = next(iter(dates.keys()))
            last_date_data = {"end_date": first_key, "stocks": dates.get(first_key, [])}
    else:
        # dates是list，直接取第一个元素
        if dates:
            last_date_data = dates[0]

    if not last_date_data or not last_date_data.get("stocks"):
        QMessageBox.information(parent, "提示", f"没有可用的股票数据！")
        return None

    stocks_data = last_date_data.get("stocks", [])

    headers = [
        '代码', '名称', '最大值', '最小值', '结束值', '开始值', '实际开始日期值', '最接近值',
        f'前1组结束地址后N日的最大值', '第1组后N最大值逻辑', 
        f'开始日到结束日之间最高价/最低价小于M',
        f'开始日到结束日之间连续累加值绝对值小于M',
        f'开始日到结束日之间有效累加值绝对值小于M',
        f'开始日到结束日之间向前最小连续累加值绝对值小于M',
        f'开始日到结束日之间向前最小有效累加值绝对值小于M',
        f'开始日到结束日之间向前最大连续累加值绝对值小于M',
        f'开始日到结束日之间向前最大有效累加值绝对值小于M',
        '前1组结束日地址值',
        '前1组结束地址前1日涨跌幅', '前1组结束日涨跌幅', '后1组结束地址值',
        '递增值', '后值大于结束地址值', '后值大于前值返回值', '操作值', '持有天数', '停盈停损操作涨幅', '调整天数', '停盈停损日均涨幅',
        '止盈止损递增涨幅', '止盈止损后值大于结束地址值涨幅', '止盈止损后值大于前值返回值涨幅', '止盈止损操作涨幅', '止盈止损日均涨幅',
        '止盈停损递增涨幅', '止盈停损后值大于结束地址值涨幅', '止盈停损后值大于前值返回值涨幅', '止盈停损操作涨幅', '止盈停损日均涨幅',
        '停盈止损递增涨幅', '停盈止损后值大于结束地址值涨幅', '停盈止损后值大于前值返回值涨幅', '停盈止损操作涨幅', '停盈止损日均涨幅',
        '创前新高1', '创前新高2', '创后新高1', '创后新高2', '创前新低1', '创前新低2', '创后新低1', '创后新低2'  # 新增两列
    ]
    table = QTableWidget(len(stocks_data), len(headers))
    table.setHorizontalHeaderLabels(headers)

    # 安装Ctrl+F搜索事件过滤器并保存引用，防止被回收
    table.search_filter = TableSearchFilter(table)
    table.installEventFilter(table.search_filter)

    def get_val(val):
        if isinstance(val, (list, tuple)) and len(val) > 1:
            val = val[1]
        if val is None or val == '' or (isinstance(val, float) and (math.isnan(val) or str(val).lower() == 'nan')):
            return ''
        # 如果是数值类型，保留两位小数
        if isinstance(val, (int, float)):
            return f"{val:.2f}"
        return val

    def get_percent(val):
        v = get_val(val)
        if v == '':
            return ''
        return f"{v}%"

    def get_bool(val):
        # 检查是否是统计行的特殊值（空字符串表示统计行中的布尔字段应该留空）
        if val == '':
            return ''
            
        # 直接处理布尔值，不经过get_val函数
        if isinstance(val, bool):
            return 'True' if val else 'False'
        # 如果是数值类型（0/1），转换为布尔值
        if isinstance(val, (int, float)):
            return 'True' if val != 0 else 'False'
        # 如果是字符串，尝试转换为布尔值
        if isinstance(val, str):
            v_lower = val.lower()
            if v_lower in ['true', '1', 'yes', 'on']:
                return 'True'
            elif v_lower in ['false', '0', 'no', 'off', '']:
                return 'False'
        # 其他情况，使用get_val处理
        v = get_val(val)
        if v == '':
            return 'False'
        # 如果get_val返回的是格式化后的数值字符串，转换回布尔值
        if isinstance(v, str) and v.replace('.', '').replace('0', '').isdigit():
            try:
                num_val = float(v)
                return 'True' if num_val != 0 else 'False'
            except:
                pass
        return 'True' if v else 'False'

    def get_ops_value(val):
        # val 是 [值, 天数] 或 None
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return val[0]
        return '' if val is None else val

    def get_ops_days(val):
        if isinstance(val, (list, tuple)) and len(val) == 2:
            return val[1]
        return '' if val is None else val

    def update_table(stocks_data):
        # 每次刷新表格时都排序
        stocks_data = sorted(stocks_data, key=lambda row: row.get('stock_idx', 0))
        table.setRowCount(len(stocks_data))
        for row_idx, row in enumerate(stocks_data):
            stock_idx = row.get('stock_idx', 0)
            code = row.get('code', '')
            name = row.get('name', '')
            table.setItem(row_idx, 0, QTableWidgetItem(str(code)))
            table.setItem(row_idx, 1, QTableWidgetItem(str(name)))
            table.setItem(row_idx, 2, QTableWidgetItem(str(get_val(row.get('max_value', '')))))
            table.setItem(row_idx, 3, QTableWidgetItem(str(get_val(row.get('min_value', '')))))
            table.setItem(row_idx, 4, QTableWidgetItem(str(get_val(row.get('end_value', '')))))
            table.setItem(row_idx, 5, QTableWidgetItem(str(get_val(row.get('start_value', '')))))
            table.setItem(row_idx, 6, QTableWidgetItem(str(get_val(row.get('actual_value', '')))))
            table.setItem(row_idx, 7, QTableWidgetItem(str(get_val(row.get('closest_value', '')))))
            table.setItem(row_idx, 8, QTableWidgetItem(str(get_val(row.get('n_days_max_value', '')))))
            table.setItem(row_idx, 9, QTableWidgetItem(get_bool(row.get('n_max_is_max', ''))))
            table.setItem(row_idx, 10, QTableWidgetItem(get_bool(row.get('range_ratio_is_less', ''))))
            table.setItem(row_idx, 11, QTableWidgetItem(get_bool(row.get('continuous_abs_is_less', ''))))
            table.setItem(row_idx, 12, QTableWidgetItem(get_bool(row.get('valid_abs_is_less', ''))))
            table.setItem(row_idx, 13, QTableWidgetItem(get_bool(row.get('forward_min_continuous_abs_is_less', ''))))
            table.setItem(row_idx, 14, QTableWidgetItem(get_bool(row.get('forward_min_valid_abs_is_less', ''))))
            table.setItem(row_idx, 15, QTableWidgetItem(get_bool(row.get('forward_max_continuous_abs_is_less', ''))))
            table.setItem(row_idx, 16, QTableWidgetItem(get_bool(row.get('forward_max_valid_abs_is_less', ''))))
            table.setItem(row_idx, 17, QTableWidgetItem(str(get_val(row.get('end_value', '')))))
            table.setItem(row_idx, 18, QTableWidgetItem(get_percent(row.get('prev_day_change', ''))))
            table.setItem(row_idx, 19, QTableWidgetItem(get_percent(row.get('end_day_change', ''))))
            table.setItem(row_idx, 20, QTableWidgetItem(str(get_val(row.get('diff_end_value', '')))))
            table.setItem(row_idx, 21, QTableWidgetItem(str(get_val(row.get('increment_value', '')))))
            table.setItem(row_idx, 22, QTableWidgetItem(str(get_val(row.get('after_gt_end_value', '')))))
            table.setItem(row_idx, 23, QTableWidgetItem(str(get_val(row.get('after_gt_start_value', '')))))
            table.setItem(row_idx, 24, QTableWidgetItem(str(get_val(row.get('ops_value', '')))))
            table.setItem(row_idx, 25, QTableWidgetItem(str(row.get('hold_days', ''))))
            table.setItem(row_idx, 26, QTableWidgetItem(get_percent(row.get('ops_change', ''))))
            table.setItem(row_idx, 27, QTableWidgetItem(str(get_val(row.get('adjust_days', '')))))
            table.setItem(row_idx, 28, QTableWidgetItem(get_percent(row.get('ops_incre_rate', ''))))
            table.setItem(row_idx, 29, QTableWidgetItem(get_percent(row.get('increment_change', ''))))
            table.setItem(row_idx, 30, QTableWidgetItem(get_percent(row.get('after_gt_end_change', ''))))
            table.setItem(row_idx, 31, QTableWidgetItem(get_percent(row.get('after_gt_start_change', ''))))
            table.setItem(row_idx, 32, QTableWidgetItem(get_percent(row.get('adjust_ops_change', ''))))
            table.setItem(row_idx, 33, QTableWidgetItem(get_percent(row.get('adjust_ops_incre_rate', ''))))
            # 止盈停损相关
            table.setItem(row_idx, 34, QTableWidgetItem(get_percent(row.get('take_and_stop_increment_change', ''))))
            table.setItem(row_idx, 35, QTableWidgetItem(get_percent(row.get('take_and_stop_after_gt_end_change', ''))))
            table.setItem(row_idx, 36, QTableWidgetItem(get_percent(row.get('take_and_stop_after_gt_start_change', ''))))
            table.setItem(row_idx, 37, QTableWidgetItem(get_percent(row.get('take_and_stop_change', ''))))
            table.setItem(row_idx, 38, QTableWidgetItem(get_percent(row.get('take_and_stop_incre_rate', ''))))
            table.setItem(row_idx, 39, QTableWidgetItem(get_percent(row.get('stop_and_take_increment_change', ''))))
            table.setItem(row_idx, 40, QTableWidgetItem(get_percent(row.get('stop_and_take_after_gt_end_change', ''))))
            table.setItem(row_idx, 41, QTableWidgetItem(get_percent(row.get('stop_and_take_after_gt_start_change', ''))))
            table.setItem(row_idx, 42, QTableWidgetItem(get_percent(row.get('stop_and_take_change', ''))))
            table.setItem(row_idx, 43, QTableWidgetItem(get_percent(row.get('stop_and_take_incre_rate', ''))))
            # 新增：创新高、创新低
            table.setItem(row_idx, 44, QTableWidgetItem(get_bool(row.get('start_with_new_before_high', ''))))
            table.setItem(row_idx, 45, QTableWidgetItem(get_bool(row.get('start_with_new_before_high2', ''))))
            table.setItem(row_idx, 46, QTableWidgetItem(get_bool(row.get('start_with_new_after_high', ''))))
            table.setItem(row_idx, 47, QTableWidgetItem(get_bool(row.get('start_with_new_after_high2', ''))))
            table.setItem(row_idx, 48, QTableWidgetItem(get_bool(row.get('start_with_new_before_low', ''))))
            table.setItem(row_idx, 49, QTableWidgetItem(get_bool(row.get('start_with_new_before_low2', ''))))
            table.setItem(row_idx, 50, QTableWidgetItem(get_bool(row.get('start_with_new_after_low', ''))))
            table.setItem(row_idx, 51, QTableWidgetItem(get_bool(row.get('start_with_new_after_low2', ''))))
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(50)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

    update_table(stocks_data)

    # --- 新增：恢复选中行 ---
    if hasattr(parent, 'last_selected_row_params') and parent.last_selected_row_params is not None:
        try:
            table.selectRow(parent.last_selected_row_params)
        except Exception:
            pass
    # --- 新增：保存选中行 ---
    def save_selected_row():
        parent.last_selected_row_params = table.currentRow()
    table.itemSelectionChanged.connect(save_selected_row)

    main_layout = QVBoxLayout()
    main_layout.addWidget(table)

    if as_widget:
        container = QWidget(parent)
        container.setLayout(main_layout)
        container.setMinimumSize(1200, 600)
        container.show()
        return container
    else:
        dialog = QDialog()
        dialog.setWindowTitle("参数明细")
        dialog.setLayout(main_layout)
        dialog.resize(1800, 500)
        dialog.show()
        return dialog

class FormulaExprEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumHeight(25)
        self.setMaximumHeight(120)
        self.setFixedWidth(400)  # 设置宽度为400px
        def adjust_formula_height():
            doc = self.document()
            line_count = doc.blockCount()
            font_metrics = self.fontMetrics()
            height = font_metrics.lineSpacing() * line_count + 12
            height = max(25, min(height, 120))
            self.setFixedHeight(height)
        self.textChanged.connect(adjust_formula_height)
        adjust_formula_height()  # 初始化高度

    def focusOutEvent(self, event):
        expr = self.toPlainText()
        if expr.strip():  # 只在有内容时校验
            try:
                compile(expr, '<string>', 'exec')
            except SyntaxError as e:
                QMessageBox.warning(self, "选股公式语法错误", f"选股公式存在语法错误，请检查！\n\n{e}")
        super().focusOutEvent(event)

def show_formula_select_table(parent, all_results=None, as_widget=True):
    # print("打开公式选股界面")
    # print(f"当前 last_formula_select_state: {getattr(parent, 'last_formula_select_state', {})}")
    
    # 创建滚动区域
    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("background-color: white; border: 1px solid #d0d0d0;")
    
    # 创建内容widget
    content_widget = QWidget()
    content_widget.setStyleSheet("background-color: white; border: 1px solid #d0d0d0;")
    layout = QVBoxLayout(content_widget)

    # 顶部公式输入区
    top_layout = QHBoxLayout()
    top_layout.setAlignment(Qt.AlignLeft)
    # 公式输入变更时同步到主界面变量

    # 选股数量label和输入框紧挨着
    select_count_label = QLabel("选股数量:")
    select_count_label.setStyleSheet("border: none;")
    select_count_spin = QSpinBox()
    select_count_spin.setFixedWidth(80)
    select_count_spin.setStyleSheet("border: 1px solid #d0d0d0;")
    select_count_label.setFixedWidth(80)
    select_count_layout = QHBoxLayout()
    select_count_layout.setSpacing(4)
    select_count_layout.setContentsMargins(0, 0, 0, 0)
    select_count_layout.addWidget(select_count_label)
    select_count_layout.addWidget(select_count_spin)
    select_count_widget = QWidget()
    select_count_widget.setLayout(select_count_layout)
    select_count_widget.setStyleSheet("border: none;")
    select_count_widget.setFixedWidth(200)
    select_count_layout.setAlignment(Qt.AlignLeft)

    sort_label = QLabel("排序方式:")
    sort_label.setFixedWidth(80)
    sort_label.setStyleSheet("border: none;")
    sort_combo = QComboBox()
    sort_combo.addItems(["最大值排序", "最小值排序"])
    sort_combo.setFixedWidth(80)
    sort_layout = QHBoxLayout()
    sort_layout.setSpacing(4)
    sort_layout.setContentsMargins(0, 0, 0, 0)
    sort_layout.addWidget(sort_label)
    sort_layout.addWidget(sort_combo)
    sort_layout.setAlignment(Qt.AlignLeft)
    sort_widget = QWidget()
    sort_widget.setLayout(sort_layout)

    # === 这里加上每次都同步主界面变量 ===
    if hasattr(parent, 'last_select_count'):
        select_count_spin.setValue(parent.last_select_count)
    if hasattr(parent, 'last_sort_mode'):
        idx = sort_combo.findText(parent.last_sort_mode)
        if idx >= 0:
            sort_combo.setCurrentIndex(idx)

    def sync_to_main():
        parent.last_select_count = select_count_spin.value()
        parent.last_sort_mode = sort_combo.currentText()
    select_count_spin.valueChanged.connect(sync_to_main)
    sort_combo.currentTextChanged.connect(sync_to_main)

    # 新增：操作值控件 - 盈损选择
    expr_label = QLabel("操作值：")
    expr_label.setFixedWidth(50)
    expr_label.setStyleSheet("border: none;")
    
    # 创建盈损选择容器
    profit_loss_container = QWidget()
    profit_loss_layout = QHBoxLayout(profit_loss_container)
    profit_loss_layout.setContentsMargins(0, 0, 0, 0)
    profit_loss_layout.setSpacing(5)
    
    # 盈选择框
    profit_label = QLabel("盈")
    profit_label.setFixedWidth(20)
    profit_label.setStyleSheet("border: none;")
    profit_combo = QComboBox()
    profit_combo.addItems(["INC", "AGE", "AGS"])
    profit_combo.setFixedWidth(50)
    profit_combo.setFixedHeight(20)
    
    # 损选择框
    loss_label = QLabel("损")
    loss_label.setFixedWidth(20)
    loss_label.setStyleSheet("border: none;")
    loss_combo = QComboBox()
    loss_combo.addItems(["INC", "AGE", "AGS"])
    loss_combo.setFixedWidth(50)
    loss_combo.setFixedHeight(20)
    
    # 添加到容器布局
    profit_loss_layout.addWidget(profit_label)
    profit_loss_layout.addWidget(profit_combo)
    profit_loss_layout.addWidget(loss_label)
    profit_loss_layout.addWidget(loss_combo)
    
    # 初始化选择值
    if hasattr(parent, 'last_profit_type'):
        profit_combo.setCurrentText(parent.last_profit_type)
    if hasattr(parent, 'last_loss_type'):
        loss_combo.setCurrentText(parent.last_loss_type)
    
    # 同步到主窗口
    def sync_profit_loss_to_main():
        if hasattr(parent, 'last_profit_type'):
            parent.last_profit_type = profit_combo.currentText()
        if hasattr(parent, 'last_loss_type'):
            parent.last_loss_type = loss_combo.currentText()
    
    profit_combo.currentTextChanged.connect(sync_profit_loss_to_main)
    loss_combo.currentTextChanged.connect(sync_profit_loss_to_main)
    
    # 直接添加到top_layout
    top_layout.addWidget(expr_label)
    top_layout.addWidget(profit_loss_container)

    select_btn = QPushButton("进行选股")
    select_btn.setFixedSize(100, 20)
    select_btn.setStyleSheet("""
        QPushButton {
            background-color: #4A90E2;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #357ABD;
        }
        QPushButton:pressed {
            background-color: #2D6DA3;
            padding-top: 2px;
            padding-left: 2px;
        }
    """)
    # 新增：查看结果按钮
    view_result_btn = QPushButton("查看结果")
    view_result_btn.setFixedSize(100, 20)
    view_result_btn.setStyleSheet(select_btn.styleSheet())

    # 新增：设置向前参数按钮
    set_forward_param_btn = QPushButton("设置向前参数")
    set_forward_param_btn.setFixedSize(100, 20)
    set_forward_param_btn.setStyleSheet(select_btn.styleSheet())

    # 新增：组合输出锁定勾选框
    lock_output_checkbox = QCheckBox("组合输出锁定")
    lock_output_checkbox.setFixedWidth(120)
    lock_output_checkbox.setStyleSheet("border: none;")
    # 默认不勾选
    lock_output_checkbox.setChecked(False)
    
    # 恢复状态
    if hasattr(parent, 'last_lock_output'):
        lock_output_checkbox.setChecked(parent.last_lock_output)
    
    def sync_lock_output_to_main():
        parent.last_lock_output = lock_output_checkbox.isChecked()
    lock_output_checkbox.stateChanged.connect(sync_lock_output_to_main)

    def on_set_forward_param_btn_clicked():
        abbr_map = get_window_abbr_map()
        round_map = get_abbr_round_map()  # 获取需要圆框勾选的变量映射
        class ForwardParamDialog(QWidget):
            def __init__(self, abbr_map, state=None, parent=None):
                super().__init__(parent)
                self.setWindowTitle("设置向前参数")
                # 设置窗口标志，使其行为类似对话框
                self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
                grid = QGridLayout(self)
                grid.setHorizontalSpacing(20)
                grid.setVerticalSpacing(10)
                self.widgets = {}
                keys = list(abbr_map.keys())
                for idx, zh_name in enumerate(keys):
                    col = idx % 4
                    row = idx // 4
                    group_widget = QWidget()
                    group_layout = QHBoxLayout()
                    group_layout.setContentsMargins(0, 0, 0, 0)
                    group_layout.setSpacing(5)
                    group_layout.setAlignment(Qt.AlignLeft)
                    enable_cb = QCheckBox()
                    enable_cb.setFixedWidth(15)

                    label = QLabel(zh_name)

                    # 添加圆框勾选框
                    round_check = None
                    if abbr_map[zh_name] in round_map.values():
                        round_check = QCheckBox()
                        round_check.setFixedWidth(15)
                        round_check.setStyleSheet("""
                            QCheckBox {
                                spacing: 0px;
                                padding: 0px;
                                border: none;
                                background: transparent;
                            }
                            QCheckBox::indicator {
                                width: 10px; height: 10px;
                                border-radius: 5px;
                                border: 1.2px solid #666;
                                background: white;
                                margin: 0px;
                                padding: 0px;
                            }
                            QCheckBox::indicator:checked {
                                background: #409EFF;
                                border: 1.2px solid #409EFF;
                            }
                        """)
                        label.setFixedWidth(230)
                    else:
                        label.setFixedWidth(250)

                    lower_edit = QLineEdit()
                    lower_edit.setPlaceholderText("下限")
                    lower_edit.setFixedWidth(50)
                    lower_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                    upper_edit = QLineEdit()
                    upper_edit.setPlaceholderText("上限")
                    upper_edit.setFixedWidth(50)
                    upper_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                    step_edit = QLineEdit()
                    step_edit.setPlaceholderText("步长")
                    step_edit.setFixedWidth(50)
                    step_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                    # 添加非负数验证器，允许为0
                    from PyQt5.QtGui import QDoubleValidator
                    validator = QDoubleValidator(0, 999999, 2)  # 最小值0，最大值999999，2位小数
                    step_edit.setValidator(validator)
                    direction_combo = QComboBox()
                    direction_combo.addItems(["右单向", "左单向", "全方向"])
                    direction_combo.setFixedWidth(60)
                    direction_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                    logic_check = QCheckBox()
                    logic_check.setFixedWidth(15)
                    logic_label = QLabel("含逻辑")
                    logic_label.setStyleSheet("border: none;")
                    
                    group_layout.addWidget(enable_cb)
                    if round_check:
                        group_layout.addWidget(round_check)
                    group_layout.addWidget(label)
                    # 为向前参数对话框中的变量控件添加悬浮提示
                    add_tooltip_to_variable(label, abbr_map[zh_name], self.parent())
                    group_layout.addWidget(lower_edit)
                    group_layout.addWidget(upper_edit)
                    group_layout.addWidget(step_edit)
                    group_layout.addWidget(direction_combo)
                    group_layout.addWidget(logic_check)
                    group_layout.addWidget(logic_label)
                    group_widget.setLayout(group_layout)
                    grid.addWidget(group_widget, row, col)
                    
                    widget_dict = {
                        "enable": enable_cb,
                        "lower": lower_edit,
                        "upper": upper_edit,
                        "step": step_edit,
                        "direction": direction_combo,
                        "logic": logic_check
                    }
                    if round_check:
                        widget_dict["round"] = round_check
                    
                    self.widgets[abbr_map[zh_name]] = widget_dict
                
                btn_ok = QPushButton("确定")
                btn_ok.setFixedWidth(80)
                btn_ok.setFixedHeight(32)
                btn_ok.setStyleSheet("font-size: 14px;")
                btn_ok.clicked.connect(self.accept)
                
                # 创建按钮布局
                button_layout = QHBoxLayout()
                button_layout.addStretch()
                button_layout.addWidget(btn_ok)
                
                grid.addLayout(button_layout, row+1, 0, 1, 4)
                # 设置拉伸策略：内容区不拉伸，只拉伸最右空白列和最下空白行
                for i in range(4):
                    grid.setColumnStretch(i, 0)
                grid.setColumnStretch(4, 1)
                # 在 grid 的最后一行加一个空白控件
                empty = QWidget()
                grid.addWidget(empty, row+2, 0, 1, 5)  # 5列，确保最右
                for i in range(row+2):
                    grid.setRowStretch(i, 0)
                grid.setRowStretch(row+2, 1)
                # 恢复state
                if hasattr(parent, 'forward_param_state') and parent.forward_param_state:
                    state = parent.forward_param_state
                if state:
                    for k, v in state.items():
                        if k in self.widgets:
                            w = self.widgets[k]
                            w["enable"].setChecked(v.get("enable", False))
                            w["lower"].setText(v.get("lower", ""))
                            w["upper"].setText(v.get("upper", ""))
                            w["step"].setText(v.get("step", ""))
                            idx = w["direction"].findText(v.get("direction", "右单向"))
                            if idx >= 0:
                                w["direction"].setCurrentIndex(idx)
                            w["logic"].setChecked(v.get("logic", False))
                            if "round" in w:
                                w["round"].setChecked(v.get("round", False))
                self.setLayout(grid)
                
                # 添加结果属性
                self.result = None
                
            def accept(self):
                """确定按钮的处理"""
                self.result = True
                self.close()
                
            def get_params(self):
                params = {}
                for k, w in self.widgets.items():
                    param_dict = {
                        "enable": w["enable"].isChecked(),
                        "lower": w["lower"].text(),
                        "upper": w["upper"].text(),
                        "step": w["step"].text(),
                        "direction": w["direction"].currentText(),
                        "logic": w["logic"].isChecked()
                    }
                    if "round" in w:
                        param_dict["round"] = w["round"].isChecked()
                    params[k] = param_dict
                return params
                
            def closeEvent(self, event):
                # 关闭窗口时也保存参数，相当于确定
                self.result = True
                params = self.get_params()
                if hasattr(self.parent(), 'forward_param_state'):
                    self.parent().forward_param_state = params
                    if hasattr(self.parent(), 'save_config'):
                        self.parent().save_config()
                super().closeEvent(event)

        # parent为主窗口实例
        dlg = ForwardParamDialog(abbr_map, state=getattr(parent, 'forward_param_state', None), parent=parent)
        # 固定窗口位置
        dlg.move(100, 300)
        dlg.show()
        # 等待窗口关闭
        while dlg.isVisible():
            QApplication.instance().processEvents()
        
        if dlg.result:
            params = dlg.get_params()
            parent.forward_param_state = params
            if hasattr(parent, 'save_config'):
                parent.save_config()

    set_forward_param_btn.clicked.connect(on_set_forward_param_btn_clicked)

    # 重新组织top_layout顺序
    for w in [select_count_widget, sort_label, sort_combo, select_btn, view_result_btn, set_forward_param_btn, lock_output_checkbox]:
        top_layout.addWidget(w)
    layout.addLayout(top_layout)

    # 获取变量缩写映射
    abbr_map = get_abbr_map()
    logic_map = get_abbr_logic_map()
    round_map = get_abbr_round_map()
    formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, parent, sort_combo)
    # 将lock_output_checkbox保存到formula_widget实例中
    formula_widget.lock_output_checkbox = lock_output_checkbox
    # 恢复状态
    if hasattr(parent, 'last_formula_select_state'):
        # print(f"恢复状态: {parent.last_formula_select_state}")
        formula_widget.set_state(parent.last_formula_select_state)
    else:
        print("没有恢复状态")
    layout.addWidget(formula_widget)
    parent.formula_widget = formula_widget  # 便于主界面访问
    # 选股结果缓存
    content_widget.selected_results = []
    content_widget.select_thread = None
    content_widget.current_table = None
    # 将结果窗口管理移到主窗口级别，避免tab切换时丢失引用
    if not hasattr(parent, 'formula_select_result_window'):
        parent.formula_select_result_window = None
    if not hasattr(parent, 'formula_select_result_table'):
        parent.formula_select_result_table = None
    # 选股逻辑
    def do_select():
        # 读取控件值
        formula_expr = formula_widget.generate_formula()
        parent.last_formula_expr = formula_expr  # 保存公式到主界面变量
        print(f"选股公式: {formula_expr}")
        if not formula_expr:
            QMessageBox.information(parent, "提示", "请先填写选股公式")
            return
        
        # 获取比较变量列表
        comparison_vars = [] 
        for comp in formula_widget.comparison_widgets:
            if comp['checkbox'].isChecked():
                var1 = comp['var1'].currentText()
                var2 = comp['var2'].currentText()
                var1_en = next((en for zh, en in formula_widget.abbr_map.items() if zh == var1), None)
                var2_en = next((en for zh, en in formula_widget.abbr_map.items() if zh == var2), None)
                if var1_en and var2_en:
                    comparison_vars.append((var1_en, var2_en))  # 以元组对的形式添加
    
        comparison_vars = list(comparison_vars)  # 转换为list
        print(f"comparison_vars: {comparison_vars}")
        select_count = select_count_spin.value()
        sort_mode = sort_combo.currentText()
        
        # 获取盈损参数
        profit_type = profit_combo.currentText()
        loss_type = loss_combo.currentText()
        
        all_param_result = parent.get_or_calculate_result(
            formula_expr=formula_expr,
            select_count=select_count,
            sort_mode=sort_mode,
            show_main_output=False,
            only_show_selected=False,  # 保持False以获取完整数据
            comparison_vars=comparison_vars,
            profit_type=profit_type,
            loss_type=loss_type
        )
        if all_param_result is None:
            # QMessageBox.information(parent, "提示", "请先上传数据文件！")
            return
        merged_results = all_param_result.get('dates', {})
        
        # 根据排序模式过滤结果
        filtered_results = {}
        for date, results in merged_results.items():
            # 排除统计行（stock_idx为-3, -2, -1的行）
            valid_results = [r for r in results if r.get('stock_idx', 0) >= 0]
            
            # 根据排序模式过滤score
            if sort_mode == "最大值排序":
                filtered_results[date] = [r for r in valid_results if r.get('score') is not None and r.get('score', 0) > 0]
            else:  # 最小值排序
                filtered_results[date] = [r for r in valid_results if r.get('score') is not None and r.get('score', 0) < 0]
            
            # 按score排序
            if sort_mode == "最大值排序":
                filtered_results[date].sort(key=lambda x: x['score'], reverse=True)
            else:  # 最小值排序
                filtered_results[date].sort(key=lambda x: x['score'])
            
            # 只保留指定数量的结果
            filtered_results[date] = filtered_results[date][:select_count]
        
        # 使用过滤后的结果
        merged_results = filtered_results
        if merged_results:
            first_date = list(merged_results.keys())[0]
            first_stocks = merged_results[first_date]
            stock_indices = [stock.get('stock_idx') for stock in first_stocks if 'stock_idx' in stock]
            print(f"选股第一个日期 {first_date} 的stock_idx: {stock_indices}")
        parent.all_param_result = all_param_result
        if not merged_results or not any(merged_results.values()):
            QMessageBox.information(parent, "提示", "没有选股结果。")
            return
        first_date = list(merged_results.keys())[0]
        stocks = merged_results[first_date]
        import math
        filtered = []
        for stock in stocks:
            score = stock.get('score')
            end_value = stock.get('end_value', [None, None])[1] if isinstance(stock.get('end_value'), (list, tuple)) else stock.get('end_value')
            hold_days = stock.get('hold_days', None)
            if score is not None and score != 0 and not (isinstance(end_value, float) and math.isnan(end_value)) and hold_days != -1:
                filtered.append(stock)
        reverse = sort_mode == "最大值排序"
        filtered.sort(key=lambda x: x['score'], reverse=reverse)
        selected_result = filtered[:select_count]
        if not selected_result:
            QMessageBox.information(parent, "提示", "没有选股结果。")
            return
        parent.last_formula_select_result_data = {'dates': {first_date: selected_result}}
        
        # 保存当前日期的索引到缓存中
        workdays_str = getattr(parent.init, 'workdays_str', [])
        if first_date in workdays_str:
            parent.last_selected_date_idx_for_navigation = workdays_str.index(first_date)
        
        table = show_formula_select_table_result(parent, parent.last_formula_select_result_data, getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), is_select_action=True)
        # 弹窗展示 - 使用主窗口级别的窗口管理
        if hasattr(parent, 'formula_select_result_window') and parent.formula_select_result_window is not None:
            parent.formula_select_result_window.close()
        result_window = QMainWindow()
        result_window.setWindowTitle("选股结果")
        flags = result_window.windowFlags()
        flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
        flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
        result_window.setWindowFlags(flags)
        central_widget = QWidget()
        layout_ = QVBoxLayout(central_widget)
        layout_.addWidget(table)
        
        # 添加导航按钮
        if hasattr(parent, 'all_param_result') and parent.all_param_result:
            # 创建按钮容器
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(10, 5, 10, 10)
            button_layout.setSpacing(10)
            
            # 获取当前日期和可用日期列表
            workdays_str = getattr(parent.init, 'workdays_str', [])
            
            # 使用缓存的日期索引，如果没有则使用第一个日期
            if hasattr(parent, 'last_selected_date_idx_for_navigation') and parent.last_selected_date_idx_for_navigation is not None:
                current_date_idx = parent.last_selected_date_idx_for_navigation
                if 0 <= current_date_idx < len(workdays_str):
                    current_date = workdays_str[current_date_idx]
                else:
                    current_date = workdays_str[0] if workdays_str else None
                    current_date_idx = 0
            else:
                current_dates = list(parent.all_param_result.get('dates', {}).keys())
                if current_dates and workdays_str:
                    current_date = current_dates[0]  # 当前显示的日期
                    current_date_idx = workdays_str.index(current_date) if current_date in workdays_str else -1
                else:
                    current_date = None
                    current_date_idx = -1
            
            if current_date is not None and current_date_idx >= 0:
                # 向左按钮
                left_btn = QPushButton("向左")
                left_btn.setFixedWidth(80)
                left_btn.setEnabled(current_date_idx > 0)  # 如果不是第一个交易日，则启用
                
                # 向右按钮
                right_btn = QPushButton("向右")
                right_btn.setFixedWidth(80)
                right_btn.setEnabled(current_date_idx < len(workdays_str) - 1)  # 如果不是最后一个交易日，则启用
                
                # 添加按钮到布局
                button_layout.addStretch()  # 左侧弹性空间
                button_layout.addWidget(left_btn)
                button_layout.addWidget(right_btn)
                button_layout.addStretch()  # 右侧弹性空间
                
                # 按钮点击事件
                def on_left_clicked():
                    if current_date_idx > 0:
                        target_date = workdays_str[current_date_idx - 1]
                        # 更新缓存的日期索引
                        parent.last_selected_date_idx_for_navigation = current_date_idx - 1
                        # 重新执行选股逻辑，使用新的日期
                        perform_stock_selection_for_date(parent, target_date)
                
                def on_right_clicked():
                    if current_date_idx < len(workdays_str) - 1:
                        target_date = workdays_str[current_date_idx + 1]
                        # 更新缓存的日期索引
                        parent.last_selected_date_idx_for_navigation = current_date_idx + 1
                        # 重新执行选股逻辑，使用新的日期
                        perform_stock_selection_for_date(parent, target_date)
                
                left_btn.clicked.connect(on_left_clicked)
                right_btn.clicked.connect(on_right_clicked)
                
                # 将按钮容器添加到主布局
                layout_.addWidget(button_container)
        
        result_window.setCentralWidget(central_widget)
        result_window.resize(1200, 450)
        result_window.show()
        parent.formula_select_result_window = result_window
        parent.formula_select_result_table = table
        # 新增：点击得分表头切换排序
        score_col = 5
        content_widget.score_sort_desc = True  # 默认降序
        def on_header_clicked(idx):
            if idx == score_col:
                content_widget.score_sort_desc = not getattr(content_widget, 'score_sort_desc', True)
                # 重新排序
                result_data = parent.last_formula_select_result_data
                merged_results = result_data.get('dates', {})
                if not merged_results or not any(merged_results.values()):
                    return
                first_date = list(merged_results.keys())[0]
                stocks = merged_results[first_date]
                reverse = content_widget.score_sort_desc
                stocks.sort(key=lambda x: x.get('score', 0), reverse=reverse)
                # 重新生成表格
                table2 = show_formula_select_table_result(parent, result_data, getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), is_select_action=True)
                # 替换弹窗内容
                win = parent.formula_select_result_window
                if win:
                    central_widget = win.centralWidget()
                    if central_widget:
                        layout = central_widget.layout()
                        if layout:
                            # 移除旧的表格，但保留按钮
                            for i in reversed(range(layout.count())):
                                item = layout.itemAt(i)
                                if item.widget():
                                    widget = item.widget()
                                    if widget == parent.formula_select_result_table:
                                        widget.setParent(None)
                                        break
                            
                            # 添加新的表格
                            layout.insertWidget(0, table2)
                            parent.formula_select_result_table = table2
                            table2.horizontalHeader().sectionClicked.connect(on_header_clicked)
        table.horizontalHeader().sectionClicked.connect(on_header_clicked)

    # 查看结果按钮逻辑
    def on_view_result():
        if not hasattr(parent, 'last_formula_select_result_data') or not parent.last_formula_select_result_data:
            QMessageBox.information(parent, "提示", "请先进行选股！")
            return
        # 只创建一个窗口，替换内容
        table = show_formula_select_table_result(parent, parent.last_formula_select_result_data, getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), is_select_action=True)
        show_formula_select_table_result_window(table, content_widget)

    select_btn.clicked.connect(do_select)
    view_result_btn.clicked.connect(on_view_result)


    # 设置滚动区域的内容
    scroll.setWidget(content_widget)
    return scroll

def calc_valid_sum(arr):
    arr = np.array([v for v in arr if v is not None], dtype=float)
    if len(arr) == 0:
        return []
    
    # 使用numpy向量化操作
    abs_arr = np.abs(arr)
    next_abs = np.roll(abs_arr, -1)
    next_abs[-1] = 0
    
    # 使用布尔索引和向量化操作
    mask = next_abs[:-1] > abs_arr[:-1]
    result = np.zeros_like(arr)
    result[:-1] = np.where(mask, arr[:-1], np.where(arr[1:] >= 0, arr[1:], -abs_arr[1:]))
    return result.tolist()


def format_stock_table(result):
    merged_results = result.get('dates', {})
    if not merged_results:
        return "没有选股结果。"
    lines = []
    # 表头
    lines.append("股票代码\t股票名称\t持有天数\t操作涨幅\t日均涨跌幅")
    for date, stocks in merged_results.items():
        for stock in stocks:
            code = stock.get('code', stock.get('stock_idx', ''))
            name = stock.get('name', '')
            hold_days = stock.get('hold_days', '')
            ops_change = stock.get('ops_change', '')
            ops_incre_rate = stock.get('ops_incre_rate', '')
            lines.append(f"{code}\t{name}\t{hold_days}\t{ops_change}\t{ops_incre_rate}")
    return "\n".join(lines)

def show_formula_select_table_result(parent, result, price_data=None, output_edit=None, is_select_action=False):
    # 导入CopyableTableWidget
    try:
        from ui.common_widgets import CopyableTableWidget
    except ImportError:
        # 如果导入失败，回退到QTableWidget
        CopyableTableWidget = QTableWidget
    
    merged_results = result.get('dates', {})
   
    headers = ["股票代码", "股票名称", "持有天数", "止盈止损涨幅", "止盈止损日均涨幅", "止盈停损涨幅", "止盈停损日均涨幅", "调整天数", "停盈停损涨幅", "停盈停损日均涨幅", "停盈止损涨幅", "停盈止损日均涨幅", "选股公式输出值"]
    if not merged_results or not any(merged_results.values()):
        # 返回一个只有表头的空表格
        table = CopyableTableWidget(0, len(headers), parent)
        table.setHorizontalHeaderLabels(headers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(50)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")
        if is_select_action:
            QMessageBox.information(parent, "提示", "无匹配结果")
        return table
    # 只展示第一个日期的数据
    first_date = list(merged_results.keys())[0]
    stocks = merged_results[first_date]
    # 过滤掉统计行（stock_idx为-1到-3的数据）
    stocks = [stock for stock in stocks if stock.get('stock_idx', 0) >= 0]
    if not stocks:
        table = CopyableTableWidget(0, len(headers), parent)
        table.setHorizontalHeaderLabels(headers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(50)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")
        return table
    table = CopyableTableWidget(len(stocks) + 2, len(headers), parent)  # 多两行：空行+均值行
    table.setHorizontalHeaderLabels(headers)
    hold_days_list = []
    ops_change_list = []
    ops_incre_rate_list = []
    adjust_ops_incre_rate_list = []
    adjust_days_list = []
    adjust_ops_change_list = []
    take_and_stop_change_list = []
    take_and_stop_incre_rate_list = []
    stop_and_take_change_list = []
    stop_and_take_incre_rate_list = []
    def safe_val(val):
        if val is None:
            return ''
        if isinstance(val, float) and math.isnan(val):
            return ''
        if isinstance(val, str) and val.strip().lower() == 'nan':
            return ''
        return val
    for row_idx, stock in enumerate(stocks):
        stock_idx = stock.get('stock_idx', None)
        # 优先从stock获取name，没有再查price_data
        code = stock.get('code', None)
        name = stock.get('name', None)
        hold_days = safe_val(stock.get('hold_days', ''))
        ops_change = safe_val(stock.get('ops_change', ''))
        ops_incre_rate = safe_val(stock.get('ops_incre_rate', ''))
        score = safe_val(stock.get('score', ''))
        adjust_ops_incre_rate = safe_val(stock.get('adjust_ops_incre_rate', ''))
        adjust_days = safe_val(stock.get('adjust_days', ''))
        adjust_ops_change = safe_val(stock.get('adjust_ops_change', ''))
        take_and_stop_change = safe_val(stock.get('take_and_stop_change', ''))
        take_and_stop_incre_rate = safe_val(stock.get('take_and_stop_incre_rate', ''))
        stop_and_take_change = safe_val(stock.get('stop_and_take_change', ''))
        stop_and_take_incre_rate = safe_val(stock.get('stop_and_take_incre_rate', ''))
        # 加%号显示
        ops_change_str = f"{ops_change}%" if ops_change != '' else ''
        ops_incre_rate_str = f"{ops_incre_rate}%" if ops_incre_rate != '' else ''
        adjust_ops_incre_rate_str = f"{adjust_ops_incre_rate}%" if adjust_ops_incre_rate != '' else ''
        adjust_ops_change_str = f"{adjust_ops_change}%" if adjust_ops_change != '' else ''
        take_and_stop_change_str = f"{take_and_stop_change}%" if take_and_stop_change != '' else ''
        take_and_stop_incre_rate_str = f"{take_and_stop_incre_rate}%" if take_and_stop_incre_rate != '' else ''
        stop_and_take_change_str = f"{stop_and_take_change}%" if stop_and_take_change != '' else ''
        stop_and_take_incre_rate_str = f"{stop_and_take_incre_rate}%" if stop_and_take_incre_rate != '' else ''

        table.setItem(row_idx, 0, QTableWidgetItem(str(code)))
        table.setItem(row_idx, 1, QTableWidgetItem(str(name)))
        table.setItem(row_idx, 2, QTableWidgetItem(str(hold_days)))
        table.setItem(row_idx, 3, QTableWidgetItem(adjust_ops_change_str))  # 止盈止损涨幅
        table.setItem(row_idx, 4, QTableWidgetItem(adjust_ops_incre_rate_str))  # 止盈止损日均涨幅
        table.setItem(row_idx, 5, QTableWidgetItem(take_and_stop_change_str))  # 止盈停损涨幅
        table.setItem(row_idx, 6, QTableWidgetItem(take_and_stop_incre_rate_str))  # 止盈停损日均涨幅
        table.setItem(row_idx, 7, QTableWidgetItem(str(adjust_days)))
        table.setItem(row_idx, 8, QTableWidgetItem(ops_change_str))  # 停盈停损涨幅
        table.setItem(row_idx, 9, QTableWidgetItem(ops_incre_rate_str))  # 停盈停损日均涨幅
        table.setItem(row_idx, 10, QTableWidgetItem(stop_and_take_change_str))  # 停盈止损涨幅
        table.setItem(row_idx, 11, QTableWidgetItem(stop_and_take_incre_rate_str))  # 停盈止损日均涨幅
        table.setItem(row_idx, 12, QTableWidgetItem(str(score)))
        # 收集用于均值计算的数据（只收集有效数值）
        try:
            if hold_days != '':
                v = float(hold_days)
                if not math.isnan(v):
                    hold_days_list.append(v)
        except Exception:
            pass
        try:
            if ops_change != '':
                v = float(ops_change)
                if not math.isnan(v):
                    ops_change_list.append(v)
        except Exception:
            pass
        try:
            if ops_incre_rate != '':
                v = float(ops_incre_rate)
                if not math.isnan(v):
                    ops_incre_rate_list.append(v)
        except Exception:
            pass
        try:
            if adjust_ops_incre_rate != '':
                v = float(adjust_ops_incre_rate)
                if not math.isnan(v):
                    adjust_ops_incre_rate_list.append(v)
        except Exception:
            pass
        try:
            if adjust_days != '':
                v = float(adjust_days)
                if not math.isnan(v):
                    adjust_days_list.append(v)
        except Exception:
            pass
        try:
            if adjust_ops_change != '':
                v = float(adjust_ops_change)
                if not math.isnan(v):
                    adjust_ops_change_list.append(v)
        except Exception:
            pass
        try:
            if take_and_stop_change != '':
                v = float(take_and_stop_change)
                if not math.isnan(v):
                    take_and_stop_change_list.append(v)
        except Exception:
            pass   
        try:
            if stop_and_take_change != '':
                v = float(stop_and_take_change)
                if not math.isnan(v):
                    stop_and_take_change_list.append(v)
        except Exception:
            pass
    # 插入空行
    empty_row_idx = len(stocks)
    for col in range(len(headers)):
        table.setItem(empty_row_idx, col, QTableWidgetItem(""))
    # 计算均值
    def safe_mean(lst):
        return round(sum(lst) / len(lst), 2) if lst else ''
    mean_hold_days = safe_mean(hold_days_list)
    mean_ops_change = safe_mean(ops_change_list)
    mean_ops_incre_rate = safe_mean(ops_incre_rate_list)
    mean_adjust_ops_incre_rate = safe_mean(adjust_ops_incre_rate_list)
    mean_adjust_days = safe_mean(adjust_days_list)
    mean_adjust_ops_change = safe_mean(adjust_ops_change_list)
    mean_take_and_stop_change = safe_mean(take_and_stop_change_list)
    mean_take_and_stop_incre_rate = safe_mean(take_and_stop_incre_rate_list)
    mean_stop_and_take_change = safe_mean(stop_and_take_change_list)
    mean_stop_and_take_incre_rate = safe_mean(stop_and_take_incre_rate_list)
    #print(f"mean_hold_days={mean_hold_days}, mean_adjust_ops_change={mean_adjust_ops_change}")
    #print(f"mean_hold_days={mean_adjust_days}, mean_adjust_ops_change={mean_ops_incre_rate}")
    # 计算日均涨幅均值
    mean_adjust_ops_incre_rate_daily = mean_adjust_ops_change / mean_hold_days if mean_adjust_ops_change != '' and mean_hold_days != '' and mean_hold_days != 0 else ''
    mean_ops_incre_rate_daily = mean_ops_change / mean_adjust_days if mean_ops_change != '' and mean_adjust_days != '' and mean_adjust_days != 0 else ''
    # 插入均值行
    mean_row_idx = len(stocks) + 1
    table.setItem(mean_row_idx, 0, QTableWidgetItem(""))
    table.setItem(mean_row_idx, 1, QTableWidgetItem(str(first_date)))
    table.setItem(mean_row_idx, 2, QTableWidgetItem(str(mean_hold_days)))
    table.setItem(mean_row_idx, 3, QTableWidgetItem(f"{mean_adjust_ops_change}%" if mean_adjust_ops_change != '' else ''))  # 止盈止损涨幅均值
    table.setItem(mean_row_idx, 4, QTableWidgetItem(f"{mean_adjust_ops_incre_rate_daily:.2f}%" if mean_adjust_ops_incre_rate_daily != '' else ''))  # 止盈止损日均涨幅均值
    table.setItem(mean_row_idx, 5, QTableWidgetItem(f"{mean_take_and_stop_change}%" if mean_take_and_stop_change != '' else ''))  # 止盈停损涨幅均值
    table.setItem(mean_row_idx, 6, QTableWidgetItem(f"{mean_take_and_stop_incre_rate:.2f}%" if mean_take_and_stop_incre_rate != '' else ''))  # 止盈停损日均涨幅均值
    table.setItem(mean_row_idx, 7, QTableWidgetItem(str(mean_adjust_days)))
    table.setItem(mean_row_idx, 8, QTableWidgetItem(f"{mean_ops_change}%" if mean_ops_change != '' else ''))  # 停盈停损涨幅均值
    table.setItem(mean_row_idx, 9, QTableWidgetItem(f"{mean_ops_incre_rate_daily:.2f}%" if mean_ops_incre_rate_daily != '' else ''))  # 停盈停损日均涨幅均值
    table.setItem(mean_row_idx, 10, QTableWidgetItem(f"{mean_stop_and_take_change}%" if mean_stop_and_take_change != '' else ''))  # 停盈止损涨幅均值
    table.setItem(mean_row_idx, 11, QTableWidgetItem(f"{mean_stop_and_take_incre_rate:.2f}%" if mean_stop_and_take_incre_rate != '' else ''))  # 停盈止损日均涨幅均值
    table.resizeColumnsToContents()
    table.horizontalHeader().setFixedHeight(50)
    table.horizontalHeader().setStyleSheet("font-size: 12px;")
    return table

def get_abbr_round_only_map():
    """获取只有圆框的变量映射"""
    abbrs = [
        #("非空停盈停损从下往上涨跌幅均值", "mean_non_nan"),
        ("含空停盈停损从下往上涨跌幅均值", "mean_with_nan"),
        ("停盈停损日均涨跌幅均值", "mean_daily_change"),
        ("停盈停损含空均值", "mean_daily_with_nan"),
        ("综合停盈停损日均涨幅", "comprehensive_stop_daily_change"),

        ("含空停盈止损从下往上涨跌幅均值", "mean_stop_and_take_with_nan"),
        ("停盈止损日均涨跌幅均值", "mean_stop_and_take_daily_change"),
        ("停盈止损含空均值", "mean_stop_and_take_daily_with_nan"),
        ("综合停盈止损日均涨幅", "comprehensive_stop_and_take_change"),

        #("非空止盈止损从下往上涨跌幅均值", "mean_adjust_non_nan"),
        ("含空止盈止损从下往上涨跌幅均值", "mean_adjust_with_nan"),
        ("止盈止损日均涨跌幅均值", "mean_adjust_daily_change"),
        ("止盈止损含空均值", "mean_adjust_daily_with_nan"),
        ("综合止盈止损日均涨幅", "comprehensive_daily_change"),

        ("含空止盈停损从下往上涨跌幅均值", "mean_take_and_stop_with_nan"),
        ("止盈停损日均涨跌幅均值", "mean_take_and_stop_daily_change"),
        ("止盈停损含空均值", "mean_take_and_stop_daily_with_nan"),
        ("综合止盈停损日均涨幅", "comprehensive_take_and_stop_change"),
        
        ("从下往上的第1个停盈停损涨跌幅含空均值", "bottom_first_with_nan"),
        ("从下往上的第2个停盈停损涨跌幅含空均值", "bottom_second_with_nan"),
        ("从下往上的第3个停盈停损涨跌幅含空均值", "bottom_third_with_nan"),
        ("从下往上的第4个停盈停损涨跌幅含空均值", "bottom_fourth_with_nan"),
        ("从下往上的第1个停盈止损涨跌幅含空均值", "bottom_first_stop_and_take_with_nan"),
        ("从下往上的第2个停盈止损涨跌幅含空均值", "bottom_second_stop_and_take_with_nan"),
        ("从下往上的第3个停盈止损涨跌幅含空均值", "bottom_third_stop_and_take_with_nan"),
        ("从下往上的第4个停盈止损涨跌幅含空均值", "bottom_fourth_stop_and_take_with_nan"),

        ("从下往上的第1个止盈止损涨跌幅含空均值", "adjust_bottom_first_with_nan"),
        ("从下往上的第2个止盈止损涨跌幅含空均值", "adjust_bottom_second_with_nan"),
        ("从下往上的第3个止盈止损涨跌幅含空均值", "adjust_bottom_third_with_nan"),
        ("从下往上的第4个止盈止损涨跌幅含空均值", "adjust_bottom_fourth_with_nan"),
        ("从下往上的第1个止盈停损涨跌幅含空均值", "bottom_first_take_and_stop_with_nan"),
        ("从下往上的第2个止盈停损涨跌幅含空均值", "bottom_second_take_and_stop_with_nan"),
        ("从下往上的第3个止盈停损涨跌幅含空均值", "bottom_third_take_and_stop_with_nan"),
        ("从下往上的第4个止盈停损涨跌幅含空均值", "bottom_fourth_take_and_stop_with_nan"),
        
        ("从下往上第N位止盈停损含空均值", "bottom_nth_take_and_stop_with_nan1"),
        ("从下往上第N位止盈停损含空均值", "bottom_nth_take_and_stop_with_nan2"),
        ("从下往上第N位止盈停损含空均值", "bottom_nth_take_and_stop_with_nan3"),
        ("从下往上第N位停盈停损含空均值", "bottom_nth_with_nan1"),
        ("从下往上第N位停盈停损含空均值", "bottom_nth_with_nan2"),
        ("从下往上第N位停盈停损含空均值", "bottom_nth_with_nan3"),

        ("从下往上第N位停盈止损含空均值", "bottom_nth_stop_and_take_with_nan1"),
        ("从下往上第N位停盈止损含空均值", "bottom_nth_stop_and_take_with_nan2"),
        ("从下往上第N位停盈止损含空均值", "bottom_nth_stop_and_take_with_nan3"),
        ("从下往上第N位止盈止损含空均值", "bottom_nth_adjust_with_nan1"),
        ("从下往上第N位止盈止损含空均值", "bottom_nth_adjust_with_nan2"),
        ("从下往上第N位止盈止损含空均值", "bottom_nth_adjust_with_nan3"),
        
    ]
    # 允许label重复，英文名唯一
    abbr_map = {}
    for zh, en in abbrs:
        abbr_map[(zh, en)] = en
    return abbr_map

def get_special_abbr_map():
    """获取特殊变量映射"""
    abbrs = [
        ("日期宽度", "width"),
        ("操作天数", "op_days"),
        ("止盈递增率", "increment_rate"),
        ("止盈后值大于结束值比例", "after_gt_end_ratio"),
        ("止盈后值大于前值比例", "after_gt_start_ratio"),
        ("止损递增率", "stop_loss_inc_rate"),
        ("止损后值大于结束值比例", "stop_loss_after_gt_end_ratio"),
        ("止损后值大于前值比例", "stop_loss_after_gt_start_ratio"),
        # 创新高/创新低相关参数 - 两组通用参数
        ("创前后新高低1开始日期距结束日期天数", "new_high_low1_start"),
        ("创前后新高低1日期范围", "new_high_low1_range"),
        ("创前后新高低1展宽期天数", "new_high_low1_span"),
        ("创前后新高低2开始日期距结束日期天数", "new_high_low2_start"),
        ("创前后新高低2日期范围", "new_high_low2_range"),
        ("创前后新高低2展宽期天数", "new_high_low2_span")
    ]
    return {zh: en for zh, en in abbrs}
class FormulaSelectWidget(QWidget):
    def __init__(self, abbr_map, abbr_logic_map, abbr_round_map, main_window, sort_combo=None):
        super().__init__()
        self.abbr_map = abbr_map
        self.abbr_logic_map = abbr_logic_map
        self.abbr_round_map = abbr_round_map
        self.abbr_round_only_map = get_abbr_round_only_map()  # 添加新的map
        self.special_abbr_map = get_special_abbr_map()  # 添加特殊map
        self.component_analysis_variables = get_component_analysis_variables()  # 添加组合分析元件变量列表
        self.var_widgets = {}
        self.comparison_widgets = []  # 存储所有比较控件
        self.main_window = main_window  # 保存主窗口引用
        self.sort_combo = sort_combo  # 保存排序方式（可选）
        self.init_ui()
        # 先恢复状态
        if hasattr(self.main_window, 'last_formula_select_state'):
            self.set_state(self.main_window.last_formula_select_state)
        # 再设置状态同步
        self._setup_state_sync()

    def _sync_to_main(self):
        """同步状态到主界面变量"""
        state = {}
        # 保存变量控件状态
        for en, widgets in self.var_widgets.items():
            item = {}
            if 'checkbox' in widgets:
                item['checked'] = widgets['checkbox'].isChecked()
            if 'round_checkbox' in widgets:
                item['round_checked'] = widgets['round_checkbox'].isChecked()
            if 'lower' in widgets:
                item['lower'] = widgets['lower'].text()
            if 'upper' in widgets:
                item['upper'] = widgets['upper'].text()
            if 'step' in widgets:
                item['step'] = widgets['step'].text()
            if 'direction' in widgets:
                item['direction'] = widgets['direction'].currentText()
            if 'logic_check' in widgets:
                item['logic_checked'] = widgets['logic_check'].isChecked()
            if 'n_input' in widgets:
                item['n_value'] = widgets['n_input'].text()
            state[en] = item
        # 保存比较控件状态
        comparison_state = []
        for comp in self.comparison_widgets:
            comparison_state.append({
                'checked': comp['checkbox'].isChecked(),  # 添加勾选框状态
                'var1': comp['var1'].currentText(),
                'lower': comp['lower'].text(),
                'upper': comp['upper'].text(),
                'var2': comp['var2'].currentText(),
                'step': comp['step'].text(),  # 新增：保存步长
                'direction': comp['direction'].currentText(),  # 新增：保存方向选择
                'logic_checked': comp['logic_check'].isChecked()  # 新增：保存含逻辑状态
            })
        state['comparison_widgets'] = comparison_state
        
        # 添加comparison_vars到状态中
        comparison_vars = []
        for comp in self.comparison_widgets:
            if comp['checkbox'].isChecked():
                var1 = comp['var1'].currentText()
                var2 = comp['var2'].currentText()
                var1_en = next((en for zh, en in self.abbr_map.items() if zh == var1), None)
                var2_en = next((en for zh, en in self.abbr_map.items() if zh == var2), None)
                if var1_en and var2_en:
                    comparison_vars.append((var1_en, var2_en))
        state['comparison_vars'] = comparison_vars
        
        self.main_window.last_formula_select_state = state
        if not hasattr(self, 'main_window'):
            return
        formula = self.generate_formula()
        if hasattr(self.main_window, 'formula_expr_edit'):
            self.main_window.formula_expr_edit.setPlainText(formula)
        self.main_window.last_formula_expr = formula

    def get_state(self):
        """导出所有控件的状态"""
        return getattr(self.main_window, 'last_formula_select_state', {})

    def set_state(self, state):
        """恢复控件状态"""
        if not state:
            return
        # 恢复变量控件状态
        for en, widgets in self.var_widgets.items():
            if en in state:
                data = state[en]
                if 'checkbox' in widgets and 'checked' in data:
                    widgets['checkbox'].setChecked(data['checked'])
                if 'round_checkbox' in widgets and 'round_checked' in data:
                    widgets['round_checkbox'].setChecked(data['round_checked'])
                if 'lower' in widgets and 'lower' in data:
                    widgets['lower'].setText(data['lower'])
                if 'upper' in widgets and 'upper' in data:
                    widgets['upper'].setText(data['upper'])
                if 'step' in widgets and 'step' in data:
                    widgets['step'].setText(data['step'])
                if 'direction' in widgets and 'direction' in data:
                    widgets['direction'].setCurrentText(data['direction'])
                if 'logic_check' in widgets and 'logic_checked' in data:
                    widgets['logic_check'].setChecked(data['logic_checked'])
                if 'n_input' in widgets and 'n_value' in data:
                    widgets['n_input'].setText(data['n_value'])
        # 先清除现有的比较控件
        for comp in self.comparison_widgets[:]:
            self.delete_comparison_widget(comp['widget'])
        # 然后根据保存的状态重新创建
        for comp_data in state.get('comparison_widgets', []):
            comp = self.add_comparison_widget()
            if comp:  # 确保 comp 不是 None
                QApplication.processEvents()
                comp['checkbox'].setChecked(comp_data.get('checked', True))
                var1_text = comp_data.get('var1', '')
                var2_text = comp_data.get('var2', '')
                if var1_text:
                    idx = comp['var1'].findText(var1_text)
                    if idx >= 0:
                        comp['var1'].setCurrentIndex(idx)
                if var2_text:
                    idx = comp['var2'].findText(var2_text)
                    if idx >= 0:
                        comp['var2'].setCurrentIndex(idx)
                comp['lower'].setText(comp_data.get('lower', ''))
                comp['upper'].setText(comp_data.get('upper', ''))
                # 新增：恢复步长、方向选择和含逻辑状态
                comp['step'].setText(comp_data.get('step', ''))
                direction_text = comp_data.get('direction', '')
                if direction_text:
                    idx = comp['direction'].findText(direction_text)
                    if idx >= 0:
                        comp['direction'].setCurrentIndex(idx)
                comp['logic_check'].setChecked(comp_data.get('logic_checked', False))
        # 恢复lock_output_checkbox状态
        if hasattr(self, 'lock_output_checkbox') and 'lock_output' in state:
            self.lock_output_checkbox.setChecked(state['lock_output'])

    def add_comparison_widget(self):
        # 创建比较控件容器
        comparison_widget = QWidget()
        comparison_widget.setFixedWidth(630)
        comparison_widget.setFixedHeight(45)  # 设置固定高度为35像素
        comparison_layout = QHBoxLayout(comparison_widget)
        comparison_layout.setContentsMargins(10, 10, 10, 10)
        comparison_layout.setSpacing(8)
        
        # 添加方框勾选框
        checkbox = QCheckBox()
        checkbox.setChecked(False)  # 默认不勾选
        checkbox.setFixedWidth(15)
        # checkbox.setStyleSheet("border: none;")
        comparison_layout.addWidget(checkbox)
        
        # 第一个变量下拉框
        var1_combo = QComboBox()
        var1_combo.addItems([zh for zh, _ in self.abbr_map.items()])
        var1_combo.setFixedWidth(165)
        var1_combo.setFixedHeight(20)
        var1_combo.view().setMinimumWidth(270)
        comparison_layout.addWidget(var1_combo)
        
        # 下限输入框
        lower_input = QLineEdit()
        lower_input.setPlaceholderText("下限")
        lower_input.setFixedWidth(30)
        comparison_layout.addWidget(lower_input)
        
        # 上限输入框
        upper_input = QLineEdit()
        upper_input.setPlaceholderText("上限")
        upper_input.setFixedWidth(30)
        comparison_layout.addWidget(upper_input)
        
        # 步长输入框
        step_edit = QLineEdit()
        step_edit.setPlaceholderText("步长")
        step_edit.setFixedWidth(30)
        step_edit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # 添加非负数验证器，允许为0
        from PyQt5.QtGui import QDoubleValidator
        validator = QDoubleValidator(0, 999999, 2)  # 最小值0，最大值999999，2位小数
        step_edit.setValidator(validator)
        comparison_layout.addWidget(step_edit)
        
        # 方向选择下拉框
        direction_combo = QComboBox()
        direction_combo.addItems(["右单向", "左单向", "全方向"])
        direction_combo.setFixedWidth(60)
        direction_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        comparison_layout.addWidget(direction_combo)
        
        # 含逻辑勾选框
        logic_check = QCheckBox()
        logic_check.setFixedWidth(15)
        comparison_layout.addWidget(logic_check)
        
        # 含逻辑标签
        logic_label = QLabel("含逻辑")
        logic_label.setStyleSheet("border: none;")
        comparison_layout.addWidget(logic_label)
        
        # 第二个变量下拉框
        var2_combo = QComboBox()
        var2_combo.addItems([zh for zh, _ in self.abbr_map.items()])
        var2_combo.setFixedWidth(165)
        var2_combo.view().setMinimumWidth(270)
        comparison_layout.addWidget(var2_combo)
        
        # 信号连接，确保任意内容变更都能同步状态
        checkbox.stateChanged.connect(self._sync_to_main)
        var1_combo.currentTextChanged.connect(self._sync_to_main)
        var2_combo.currentTextChanged.connect(self._sync_to_main)
        lower_input.textChanged.connect(self._sync_to_main)
        upper_input.textChanged.connect(self._sync_to_main)
        step_edit.textChanged.connect(self._sync_to_main)
        direction_combo.currentTextChanged.connect(self._sync_to_main)
        logic_check.stateChanged.connect(self._sync_to_main)
        
        # 删除按钮（右上角小x）
        delete_btn = QToolButton(comparison_widget)
        delete_btn.setText('×')
        delete_btn.setStyleSheet('QToolButton {color: #FF4D4F; font-weight: bold; font-size: 16px; border: none; background: transparent;} QToolButton:hover {color: #D9363E;}')
        delete_btn.setFixedSize(18, 18)
        delete_btn.clicked.connect(lambda: self.delete_comparison_widget(comparison_widget))
        
        # 用绝对定位放右上角
        comparison_widget.setLayout(comparison_layout)
        delete_btn.raise_()
        delete_btn.move(comparison_widget.width() - 22, 2)
        comparison_widget.resizeEvent = lambda event: delete_btn.move(comparison_widget.width() - 22, 2)
        
        # 添加到列表
        comp_dict = {
            'widget': comparison_widget,
            'checkbox': checkbox,  # 添加checkbox到字典
            'var1': var1_combo,
            'lower': lower_input,
            'upper': upper_input,
            'var2': var2_combo,
            'step': step_edit,
            'direction': direction_combo,
            'logic_check': logic_check
        }
        self.comparison_widgets.append(comp_dict)
        
        # 刷新比较控件和按钮位置
        parent_layout = self.layout().itemAt(0).widget().layout()  # grid_layout
        self._refresh_comparison_row(parent_layout)
        
        # 在末尾添加
        self._sync_to_main()
        return comp_dict

    def delete_comparison_widget(self, widget):
        # 从列表中移除
        for i, comp in enumerate(self.comparison_widgets):
            if comp['widget'] == widget:
                self.comparison_widgets.pop(i)
                break
        widget.setParent(None)
        widget.deleteLater()
        parent_layout = self.layout().itemAt(0).widget().layout()  # grid_layout
        self._refresh_comparison_row(parent_layout)
        # 在末尾添加
        self._sync_to_main()

    def _generate_special_result_combinations(self):
        """
        为四个特殊变量生成特定的9种result组合
        返回result变量列表的列表，每个组合包含排序方式信息
        """
        # 检查是否锁定输出
        lock_output = False
        if hasattr(self.main_window, 'last_lock_output'):
            lock_output = self.main_window.last_lock_output
        
        combinations = []
        
        # 检查这四个变量是否被勾选圆框
        var_states = {}
        for var in ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum']:
            if var in self.var_widgets:
                widgets = self.var_widgets[var]
                var_states[var] = widgets['round_checkbox'].isChecked() if 'round_checkbox' in widgets else False
            else:
                var_states[var] = False
        
        # 获取变量状态
        cont_pos_checked = var_states['cont_sum_pos_sum']
        cont_neg_checked = var_states['cont_sum_neg_sum']
        valid_pos_checked = var_states['valid_pos_sum']
        valid_neg_checked = var_states['valid_neg_sum']
        
        if lock_output:
            # 锁定输出模式：返回一个合并后的单一组合
            all_result_vars = []
            if cont_pos_checked:
                all_result_vars.append('cont_sum_pos_sum')
            if cont_neg_checked:
                all_result_vars.append('cont_sum_neg_sum')
            if valid_pos_checked:
                all_result_vars.append('valid_pos_sum')
            if valid_neg_checked:
                all_result_vars.append('valid_neg_sum')
            
            # 如果没有勾选基础变量，检查是否有向前参数
            if not all_result_vars:
                print("没有勾选基础变量，检查向前参数...")
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    for en, v in self.main_window.forward_param_state.items():
                        if v.get('round'):
                            # 检查是否是8个特殊向前参数变量
                            if en in ['forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
                                     'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
                                     'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
                                     'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum']:
                                all_result_vars.append(en)
            
            if all_result_vars:
                # 获取用户设置的排序方式
                user_sort_mode = None
                if self.sort_combo and self.sort_combo.currentText():
                    user_sort_mode = self.sort_combo.currentText()
                elif hasattr(self.main_window, 'last_sort_mode') and self.main_window.last_sort_mode:
                    user_sort_mode = self.main_window.last_sort_mode
                else:
                    user_sort_mode = '最大值排序'
                combinations.append({
                    'result_vars': all_result_vars,
                    'sort_modes': [user_sort_mode]
                })
        else:
            # 非锁定输出模式：生成9种组合
            # 组合1: 连续累加值正相加
            if cont_pos_checked:
                combinations.append({
                    'result_vars': ['cont_sum_pos_sum'],
                    'sort_modes': ['最大值排序']  # 正值用最大值排序
                })
            
            # 组合2: 连续累加值负相加
            if cont_neg_checked:
                combinations.append({
                    'result_vars': ['cont_sum_neg_sum'],
                    'sort_modes': ['最小值排序']  # 负值用最小值排序
                })
            
            # 组合3: 连续累加值正相加 + 连续累加值负相加
            if cont_pos_checked and cont_neg_checked:
                combinations.append({
                    'result_vars': ['cont_sum_pos_sum', 'cont_sum_neg_sum'],
                    'sort_modes': ['最大值排序', '最小值排序']  # 混合值需要两种排序
                })
            
            # 组合4: 有效累加值正相加
            if valid_pos_checked:
                combinations.append({
                    'result_vars': ['valid_pos_sum'],
                    'sort_modes': ['最大值排序']  # 正值用最大值排序
                })
            
            # 组合5: 有效累加值负相加
            if valid_neg_checked:
                combinations.append({
                    'result_vars': ['valid_neg_sum'],
                    'sort_modes': ['最小值排序']  # 负值用最小值排序
                })
            
            # 组合6: 有效累加值正相加 + 有效累加值负相加
            if valid_pos_checked and valid_neg_checked:
                combinations.append({
                    'result_vars': ['valid_pos_sum', 'valid_neg_sum'],
                    'sort_modes': ['最大值排序', '最小值排序']  # 混合值需要两种排序
                })
            
            # 组合7: 连续累加值正相加 + 有效累加值正相加
            if cont_pos_checked and valid_pos_checked:
                combinations.append({
                    'result_vars': ['cont_sum_pos_sum', 'valid_pos_sum'],
                    'sort_modes': ['最大值排序']  # 都是正值用最大值排序
                })
            
            # 组合8: 连续累加值负相加 + 有效累加值负相加
            if cont_neg_checked and valid_neg_checked:
                combinations.append({
                    'result_vars': ['cont_sum_neg_sum', 'valid_neg_sum'],
                    'sort_modes': ['最小值排序']  # 都是负值用最小值排序
                })
            
            # 组合9: 连续累加值正相加 + 连续累加值负相加 + 有效累加值正相加 + 有效累加值负相加
            if cont_pos_checked and cont_neg_checked and valid_pos_checked and valid_neg_checked:
                combinations.append({
                    'result_vars': ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum'],
                    'sort_modes': ['最大值排序', '最小值排序']  # 混合值需要两种排序
                })
            
            # 容错处理：如果没有勾选基础变量，检查是否有向前参数，如果有则让向前参数自行组成result
            if not combinations:
                print("没有勾选基础变量，检查向前参数...")
                # 收集8个特殊向前参数变量
                forward_result_vars = []
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    for en, v in self.main_window.forward_param_state.items():
                        if v.get('round'):
                            # 检查是否是8个特殊向前参数变量
                            if en in ['forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
                                     'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
                                     'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
                                     'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum']:
                                forward_result_vars.append(en)
                
                if forward_result_vars:
                    print(f"发现向前参数变量: {forward_result_vars}")
                    # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                    # 获取用户设置的排序方式
                    user_sort_mode = self.sort_combo.currentText() if self.sort_combo else (self.main_window.last_sort_mode if hasattr(self.main_window, 'last_sort_mode') else None)
                    if user_sort_mode is None:
                        raise ValueError("无法获取用户设置的排序方式：sort_combo为None且main_window没有last_sort_mode属性")
                    print(f"添加特殊向前组合时获取到的 user_sort_mode: {user_sort_mode}")
                    combinations.append({
                        'result_vars': forward_result_vars,
                        'sort_modes': [user_sort_mode]
                    })
                else:
                    print("没有发现向前参数变量")
        
        return combinations
    def generate_formula_list(self):
        """
        生成公式列表，用于组合分析，类似笛卡尔积
        根据步长和方向选项生成所有可能的组合
        支持含逻辑处理：当控件勾选含逻辑时，会在该控件的组合中添加一个True条件
        支持向前参数：forward_param_state中的参数也参与组合生成
        支持特殊排序：根据result变量的特性决定排序方式
        """
        # 检查是否锁定输出
        lock_output = False
        if hasattr(self.main_window, 'last_lock_output'):
            lock_output = self.main_window.last_lock_output
        
        formula_list = []
        
        # 收集需要参与组合的逻辑控件（所有逻辑控件都参与）
        logic_combination_vars = []
        logic_map = get_abbr_logic_map()
        
        # 遍历所有逻辑控件
        for en, widgets in self.var_widgets.items():
            if 'checkbox' in widgets and 'lower' not in widgets:
                if widgets['checkbox'].isChecked():
                    # 查找对应的中文名称
                    logic_zh = None
                    for zh, en_name in logic_map.items():
                        if en_name == en:
                            logic_zh = zh
                            break
                    
                    logic_combination_vars.append({
                        'var_name': en,
                        'zh_name': logic_zh or en
                    })
                    print(f"  添加逻辑控件到组合: {en} ({logic_zh or en})")
        
        # 收集需要组合的变量控件
        combination_vars = []
        for en, widgets in self.var_widgets.items():
                
            if 'lower' in widgets and 'upper' in widgets and 'step' in widgets and 'direction' in widgets:
                # 对于同时有圆框和方框的变量，需要方框勾选才参与组合
                # 对于只有方框的变量，只需要方框勾选
                should_include = widgets['checkbox'].isChecked()
                if should_include:
                    lower_text = widgets['lower'].text().strip()
                    upper_text = widgets['upper'].text().strip()
                    step_text = widgets['step'].text().strip()
                    direction = widgets['direction'].currentText()
                    has_logic = widgets.get('logic_check', None) and widgets['logic_check'].isChecked()
                    
                    if lower_text and upper_text:  # 只检查下限和上限，步长可以为空
                        try:
                            lower_val = float(lower_text)
                            upper_val = float(upper_text)
                            # 如果步长为空，设为0
                            if step_text:
                                step_val = float(step_text)
                            else:
                                step_val = 0
                            
                            print(f"  添加变量到组合: {en}, 含逻辑: {has_logic}")
                            combination_vars.append({
                                'var_name': en,
                                'lower': lower_val,
                                'upper': upper_val,
                                'step': step_val,
                                'direction': direction,
                                'has_logic': has_logic,
                                'is_comparison': False  # 标记为普通变量
                            })
                        except ValueError:
                            # 如果数值转换失败，跳过这个变量
                            continue
        
        # 收集向前参数，也参与组合生成
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
                if v.get('enable'):
                    lower_text = v.get('lower', '').strip()
                    upper_text = v.get('upper', '').strip()
                    step_text = v.get('step', '').strip()
                    direction = v.get('direction', '右单向')
                    has_logic = v.get('logic', False)
                    
                    print(f"  启用状态: {v.get('enable')}")
                    print(f"  下限: '{lower_text}', 上限: '{upper_text}', 步长: '{step_text}'")
                    
                    if lower_text and upper_text:  # 只检查下限和上限，步长可以为空
                        try:
                            lower_val = float(lower_text)
                            upper_val = float(upper_text)
                            # 如果步长为空，设为0
                            if step_text:
                                step_val = float(step_text)
                            else:
                                step_val = 0
                            
                            print(f"  添加向前参数到组合: {en} ({lower_val}, {upper_val}, {step_val})")
                            combination_vars.append({
                                'var_name': en,
                                'lower': lower_val,
                                'upper': upper_val,
                                'step': step_val,
                                'direction': direction,
                                'has_logic': has_logic,
                                'is_comparison': False  # 标记为普通变量
                            })
                        except ValueError as e:
                            print(f"  数值转换失败: {e}")
                            # 如果数值转换失败，跳过这个变量
                            continue
                    else:
                        print(f"  参数不完整，跳过")
        else:
            print("没有向前参数状态或状态为空")
        
        print(f"最终组合变量数量: {len(combination_vars)}")
        for var in combination_vars:
            print(f"  组合变量: {var['var_name']} ({var['lower']}, {var['upper']}, {var['step']})")
        
        # 收集圆框变量（这些在所有组合中都一样）
        # 特殊处理四个变量的result组合
        special_result_combinations = self._generate_special_result_combinations()
        print(f"generate_formula_list中特殊组合数量: {len(special_result_combinations)}")
        
        # 收集其他圆框变量（排除特殊变量和get_abbr_round_only_map中的变量）
        other_result_vars = []
        # 获取get_abbr_round_only_map中的变量名列表，用于排除
        round_only_vars = set()
        for (zh, en), en_val in self.abbr_round_only_map.items():
            round_only_vars.add(en_val)
        
        for en, widgets in self.var_widgets.items():
            # 排除特殊变量和get_abbr_round_only_map中的变量
            if (en not in ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum'] and 
                en not in round_only_vars):
                if 'round_checkbox' in widgets and widgets['round_checkbox'].isChecked():
                    other_result_vars.append(en)
        
        # 收集向前参数的圆框变量
        # 8个特殊向前参数变量（正负相加值）不参与组合，直接加到result
        special_forward_result_vars = []
        other_forward_result_vars = []
        
        # 检查是否有基础变量，如果没有基础变量，8个特殊向前参数变量已经在_generate_special_result_combinations中处理了
        has_basic_vars = any(
            widgets.get('round_checkbox', None) and widgets['round_checkbox'].isChecked()
            for en, widgets in self.var_widgets.items()
            if en in ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum']
        )
        
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
                if v.get('round'):
                    # 检查是否是8个特殊向前参数变量
                    if en in ['forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
                             'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
                             'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
                             'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum']:
                        # 只有当有基础变量时，才添加到special_forward_result_vars
                        # 如果没有基础变量，这些变量已经在_generate_special_result_combinations中处理了
                        if has_basic_vars:
                            special_forward_result_vars.append(en)
                    else:
                        other_forward_result_vars.append(en)
        else:
            print("没有向前参数状态或状态为空")
        
        # 将其他向前参数的圆框变量添加到other_result_vars
        other_result_vars.extend(other_forward_result_vars)
        
        # 收集比较控件条件
        comparison_conditions = []
        has_logic_comparison = False
        # 收集比较控件到combination_vars中，参与笛卡尔积
        for comp in self.comparison_widgets:
            if comp['checkbox'].isChecked():
                var1 = comp['var1'].currentText()
                lower = comp['lower'].text().strip()
                upper = comp['upper'].text().strip()
                step = comp['step'].text().strip()
                direction = comp['direction'].currentText()
                var2 = comp['var2'].currentText()
                has_logic = comp['logic_check'].isChecked()
                
                var1_en = next((en for zh, en in self.abbr_map.items() if zh == var1), None)
                var2_en = next((en for zh, en in self.abbr_map.items() if zh == var2), None)
                
                if lower and upper and var1_en and var2_en:
                    try:
                        # 如果步长为空，设为0
                        if step:
                            step_val = float(step)
                        else:
                            step_val = 0
                        lower_val = float(lower)
                        upper_val = float(upper)
                        
                        # 将比较控件也加入到combination_vars中，参与笛卡尔积
                        combination_vars.append({
                            'var1': var1_en,
                            'var2': var2_en,
                            'lower': lower_val,
                            'upper': upper_val,
                            'step': step_val,
                            'direction': direction,
                            'has_logic': has_logic,
                            'is_comparison': True  # 标记为比较控件
                        })
                        
                        if has_logic:
                            has_logic_comparison = True
                    except ValueError:
                        continue
        
        # 生成所有可能的组合
        print(f"lock_output: {lock_output}")
        
        # 初始化logic_conditions，避免未定义错误
        logic_conditions = []
        
        if lock_output:
            # 锁定输出时，结果部分只生成一种组合（所有勾选的result变量直接加号拼接）
            all_result_vars = []
            for special_combo in special_result_combinations:
                all_result_vars.extend(special_combo['result_vars'])
            all_result_vars.extend(other_result_vars)
            all_result_vars.extend(special_forward_result_vars)
            # 去重
            all_result_vars = list(dict.fromkeys(all_result_vars))
            
            # 排序方式：取主界面当前排序
            user_sort_mode = self.sort_combo.currentText() if self.sort_combo else (self.main_window.last_sort_mode if hasattr(self.main_window, 'last_sort_mode') else '最大值排序')
            
            if not combination_vars:
                # 如果没有需要组合的变量，只生成一个公式
                # 注意：逻辑控件条件在最后统一处理，这里不处理
                all_conditions = []
                if all_conditions:
                    cond_str = "if " + " and ".join(all_conditions) + ":"
                else:
                    cond_str = "if True:"
                result_expr = "result = " + " + ".join(all_result_vars) if all_result_vars else "result = 0"
                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                formula_list.append({
                    'formula': formula,
                    'sort_mode': user_sort_mode,
                    'result_vars': all_result_vars
                })
                
                # 如果有含逻辑的比较控件，额外生成一个if True的公式
                if has_logic_comparison:
                    true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                    formula_list.append({
                        'formula': true_formula,
                        'sort_mode': user_sort_mode,
                        'result_vars': all_result_vars
                    })
            else:
                # 如果有需要组合的变量，条件部分仍然进行笛卡尔积
                var_combinations = []
                
                for var_info in combination_vars:
                    is_comparison = var_info.get('is_comparison', False)
                    
                    if is_comparison:
                        # 比较控件
                        var1 = var_info['var1']
                        var2 = var_info['var2']
                        lower_val = var_info['lower']
                        upper_val = var_info['upper']
                        step_val = var_info['step']
                        direction = var_info['direction']
                        has_logic = var_info['has_logic']
                        
                        print(f"比较控件组合 - {var1} vs {var2}:")
                        print(f"  下限: {lower_val}, 上限: {upper_val}, 步长: {step_val}")
                        print(f"  方向: {direction}, 含逻辑: {has_logic}")
                    else:
                        # 普通变量
                        var_name = var_info['var_name']
                        lower_val = var_info['lower']
                        upper_val = var_info['upper']
                        step_val = var_info['step']
                        direction = var_info['direction']
                        has_logic = var_info['has_logic']
                    
                    combinations = []
                    
                    # 如果步长为0或空，生成单一组合
                    if step_val == 0 or step_val == '' or step_val is None:
                        combinations.append((round(lower_val, 2), round(upper_val, 2)))
                        print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                    else:
                        if direction == "右单向":
                            # 最大值不变，最小值按步长变化
                            current_lower = lower_val
                            # 根据步长正负调整循环条件
                            if step_val > 0:
                                while current_lower < upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            else:  # step_val < 0
                                while current_lower > upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                        
                        elif direction == "左单向":
                            # 最小值不变，最大值按步长变化
                            current_upper = upper_val
                            # 根据步长正负调整循环条件
                            if step_val > 0:
                                while current_upper > lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            else:  # step_val < 0
                                while current_upper < lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                        
                        elif direction == "全方向":
                            combinations = []
                            # 右单向：上限不变，下限不断加步长
                            current_lower = lower_val
                            if step_val > 0:
                                while current_lower < upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            else:
                                while current_lower > upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            # 左单向：下限不变，上限不断减步长
                            current_upper = upper_val
                            if step_val > 0:
                                while current_upper > lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            else:
                                while current_upper < lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            # 剔除重复项和下限=上限的情况
                            combinations = list({(a, b) for a, b in combinations if a != b})
                            combinations.sort()
                    
                    # 处理含逻辑：如果勾选了含逻辑，添加一个True条件
                    if has_logic:
                        combinations.append(('True', 'True'))
                    
                    if is_comparison:
                        var_combinations.append({
                            'var1': var1,
                            'var2': var2,
                            'combinations': combinations,
                            'is_comparison': True  # 标记为比较控件
                        })
                    else:
                        var_combinations.append({
                            'var_name': var_name,
                            'combinations': combinations,
                            'is_comparison': False  # 标记为普通变量
                        })
                
                # 生成笛卡尔积
                if var_combinations:
                    # 获取所有变量的组合数量
                    total_combinations = 1
                    for var_combo in var_combinations:
                        total_combinations *= len(var_combo['combinations'])
                    
                    print(f"锁定输出模式：总共 {total_combinations} 个组合")
                    
                    # 为每个条件组合生成公式
                    for i in range(total_combinations):
                        # 计算当前组合的索引
                        indices = []
                        temp = i
                        for var_combo in var_combinations:
                            indices.append(temp % len(var_combo['combinations']))
                            temp //= len(var_combo['combinations'])
                        
                        # 构建当前组合的条件 - 每个笛卡尔积组合都应该有独立的条件
                        current_conditions = logic_conditions.copy()  # 复制逻辑条件，避免引用问题
                        
                        print(f"生成锁定输出组合 {i+1} 的条件:")
                        print(f"  逻辑条件: {logic_conditions}")
                        print(f"  比较条件: []")
                        
                        for j, var_combo in enumerate(var_combinations):
                            combo_idx = indices[j]
                            lower_val, upper_val = var_combo['combinations'][combo_idx]
                            
                            print(f"  变量组合 {j+1}: ({lower_val}, {upper_val})")
                            
                            # 如果是True条件，跳过该变量（不添加任何条件）
                            if lower_val == 'True' and upper_val == 'True':
                                print(f"    跳过True条件")
                                continue
                            
                            if var_combo['is_comparison']:
                                # 比较控件：生成 v1 / v2 >= lower and v1 / v2 <= upper 的条件
                                var1 = var_combo['var1']
                                var2 = var_combo['var2']
                                comp_conditions = []
                                comp_conditions.append(f"{var1} / {var2} >= {lower_val}")
                                comp_conditions.append(f"{var1} / {var2} <= {upper_val}")
                                current_conditions.append(' and '.join(comp_conditions))
                                print(f"    添加比较条件: {' and '.join(comp_conditions)}")
                            else:
                                # 普通变量：生成 var >= lower and var <= upper 的条件
                                var_name = var_combo['var_name']
                                var_conditions = []
                                var_conditions.append(f"{var_name} >= {lower_val}")
                                var_conditions.append(f"{var_name} <= {upper_val}")
                                current_conditions.append(' and '.join(var_conditions))
                                print(f"    添加变量条件: {' and '.join(var_conditions)}")
                        
                        print(f"  最终条件: {current_conditions}")
                        
                        # 生成公式
                        if current_conditions:
                            cond_str = "if " + " and ".join(current_conditions) + ":"
                        else:
                            cond_str = "if True:"
                        
                        # 为每个特殊组合生成公式
                        if special_result_combinations:
                            print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                            for special_combo in special_result_combinations:
                                # 合并特殊组合和其他result变量
                                all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                                if all_result_vars:
                                    result_expr = "result = " + " + ".join(all_result_vars)
                                else:
                                    result_expr = "result = 0"
                                
                                # 为每个排序方式生成一个公式
                                for sort_mode in special_combo['sort_modes']:
                                    formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                                    formula_list.append({
                                        'formula': formula,
                                        'sort_mode': sort_mode,
                                        'result_vars': all_result_vars
                                    })
                        else:
                            # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                            print(f"没有特殊组合")
                            all_result_vars = other_result_vars + special_forward_result_vars
                            if all_result_vars:
                                result_expr = "result = " + " + ".join(all_result_vars)
                            else:
                                result_expr = "result = 0"
                            
                            # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                            # 获取用户设置的排序方式
                            user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                            print(f"user_sort_mode: {user_sort_mode}")
                            
                            # 生成一个公式
                            formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                            formula_list.append({
                                'formula': formula,
                                'sort_mode': user_sort_mode,
                                'result_vars': all_result_vars
                            })
            
            # 锁定输出模式下也需要进行逻辑控件组合处理
            if logic_combination_vars:
                print(f"锁定输出模式下进行逻辑控件组合处理")
                original_formula_list = formula_list.copy()
                formula_list = []
                
                # 锁定输出模式下，逻辑控件也只生成一个组合（所有勾选的逻辑条件用and连接）
                if logic_combination_vars:
                    print(f"锁定输出模式：有 {len(logic_combination_vars)} 个逻辑控件参与组合，只生成一个组合")
                    
                    # 收集所有勾选的逻辑控件条件
                    logic_conditions = [logic_var_info['var_name'] for logic_var_info in logic_combination_vars]
                    logic_condition_str = " and ".join(logic_conditions)
                    print(f"锁定输出模式逻辑控件组合: {logic_condition_str}")
                    
                    # 为每个公式添加逻辑控件条件
                    for formula_obj in original_formula_list:
                        original_formula = formula_obj['formula']
                        if 'if ' in original_formula:
                            # 找到if行的结束位置
                            if_end_pos = original_formula.find(':')
                            if if_end_pos != -1:
                                # 获取原始if条件
                                if_condition = original_formula[3:if_end_pos].strip()
                                
                                # 构建新的if条件 - 在原有条件基础上添加逻辑控件条件
                                if if_condition == 'True':
                                    new_condition = f"if {logic_condition_str}:"
                                else:
                                    new_condition = f"if {if_condition} and {logic_condition_str}:"
                                
                                # 完全重新构建公式
                                new_formula = new_condition + original_formula[if_end_pos + 1:]  # +1 跳过冒号
                                formula_obj['formula'] = new_formula
                                
                                print(f"  生成锁定输出逻辑组合公式: {logic_condition_str}")
                        formula_list.append(formula_obj)
                else:
                    # 没有逻辑控件，直接添加原公式
                    formula_list.extend(original_formula_list)
            
            for i, formula_obj in enumerate(formula_list):
                print(f"锁定输出公式 {i+1} (排序方式: {formula_obj['sort_mode']}):")
                print(formula_obj['formula'])
                print("-" * 50)
            return formula_list
        elif not combination_vars:
            # 如果没有需要组合的变量，为每个特殊result组合生成一个公式
            # 注意：逻辑控件条件在最后统一处理，这里不处理
            all_conditions = []
            if all_conditions:
                cond_str = "if " + " and ".join(all_conditions) + ":"
            else:
                cond_str = "if True:"
            
            # 为每个特殊组合生成公式
            if special_result_combinations:
                print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                for special_combo in special_result_combinations:
                    # 合并特殊组合和其他result变量
                    # 注意：8个特殊向前参数变量已经在special_combo['result_vars']中了（当没有基础变量时）
                    # 所以这里只需要添加其他result变量
                    all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                    if all_result_vars:
                        result_expr = "result = " + " + ".join(all_result_vars)
                    else:
                        result_expr = "result = 0"
                    
                    # 为每个排序方式生成一个公式
                    for sort_mode in special_combo['sort_modes']:
                        formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                        formula_list.append({
                            'formula': formula,
                            'sort_mode': sort_mode,
                            'result_vars': all_result_vars
                        })
                        
                        # 如果有含逻辑的比较控件，额外生成一个if True的公式
                        if has_logic_comparison:
                            true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                            formula_list.append({
                                'formula': true_formula,
                                'sort_mode': sort_mode,
                                'result_vars': all_result_vars
                            })
            else:
                # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                print(f"没有特殊组合")
                all_result_vars = other_result_vars + special_forward_result_vars
                if all_result_vars:
                    result_expr = "result = " + " + ".join(all_result_vars)
                else:
                    result_expr = "result = 0"
                
                # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参量，则按用户设置的排序
                # 获取用户设置的排序方式
                user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                print(f"user_sort_mode: {user_sort_mode}")
                
                # 生成一个公式
                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                formula_list.append({
                    'formula': formula,
                    'sort_mode': user_sort_mode,
                    'result_vars': all_result_vars
                })
                
                # 如果有含逻辑的比较控件，额外生成一个if True的公式
                if has_logic_comparison:
                    true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                    formula_list.append({
                        'formula': true_formula,
                        'sort_mode': user_sort_mode,
                        'result_vars': all_result_vars
                    })
        else:
            # 为每个变量生成组合
            var_combinations = []
            
            for var_info in combination_vars:
                is_comparison = var_info.get('is_comparison', False)
                
                if is_comparison:
                    # 比较控件
                    var1 = var_info['var1']
                    var2 = var_info['var2']
                    lower_val = var_info['lower']
                    upper_val = var_info['upper']
                    step_val = var_info['step']
                    direction = var_info['direction']
                    has_logic = var_info['has_logic']
                    
                    print(f"比较控件组合 - {var1} vs {var2}:")
                    print(f"  下限: {lower_val}, 上限: {upper_val}, 步长: {step_val}")
                    print(f"  方向: {direction}, 含逻辑: {has_logic}")
                else:
                    # 普通变量
                    var_name = var_info['var_name']
                    lower_val = var_info['lower']
                    upper_val = var_info['upper']
                    step_val = var_info['step']
                    direction = var_info['direction']
                    has_logic = var_info['has_logic']
                
                combinations = []
                
                # 如果步长为0或空，生成单一组合
                if step_val == 0 or step_val == '' or step_val is None:
                    combinations.append((round(lower_val, 2), round(upper_val, 2)))
                    print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                elif direction == "右单向":
                    # 最大值不变，最小值按步长变化
                    current_lower = lower_val
                    # 根据步长正负调整循环条件
                    if step_val > 0:
                        while current_lower < upper_val:
                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                            current_lower += step_val
                    else:  # step_val < 0
                        while current_lower > upper_val:
                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                            current_lower += step_val
                
                elif direction == "左单向":
                    # 最小值不变，最大值按步长变化
                    current_upper = upper_val
                    # 根据步长正负调整循环条件
                    if step_val > 0:
                        while current_upper > lower_val:
                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                            current_upper -= step_val
                    else:  # step_val < 0
                        while current_upper < lower_val:
                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                            current_upper -= step_val
                
                elif direction == "全方向":
                    combinations = []
                    # 右单向：上限不变，下限不断加步长
                    current_lower = lower_val
                    if step_val > 0:
                        while current_lower < upper_val:
                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                            current_lower += step_val
                    else:
                        while current_lower > upper_val:
                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                            current_lower += step_val
                    # 左单向：下限不变，上限不断减步长
                    current_upper = upper_val
                    if step_val > 0:
                        while current_upper > lower_val:
                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                            current_upper -= step_val
                    else:
                        while current_upper < lower_val:
                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                            current_upper -= step_val
                    # 剔除重复项和下限=上限的情况
                    combinations = list({(a, b) for a, b in combinations if a != b})
                    combinations.sort()
                
                # 处理含逻辑：如果勾选了含逻辑，添加一个True条件
                if has_logic:
                    combinations.append(('True', 'True'))
                
                if is_comparison:
                    var_combinations.append({
                        'var1': var1,
                        'var2': var2,
                        'combinations': combinations,
                        'is_comparison': True  # 标记为比较控件
                    })
                else:
                    var_combinations.append({
                        'var_name': var_name,
                        'combinations': combinations,
                        'is_comparison': False  # 标记为普通变量
                    })
            
            # 生成笛卡尔积
            if var_combinations:
                # 获取所有变量的组合数量
                total_combinations = 1
                for var_combo in var_combinations:
                    total_combinations *= len(var_combo['combinations'])
                
                print(f"非锁定输出模式：总共 {total_combinations} 个组合")
                
                # 为每个条件组合生成公式
                for i in range(total_combinations):
                    # 计算当前组合的索引
                    indices = []
                    temp = i
                    for var_combo in var_combinations:
                        indices.append(temp % len(var_combo['combinations']))
                        temp //= len(var_combo['combinations'])
                    
                    # 构建当前组合的条件
                    current_conditions = logic_conditions.copy()
                    
                    print(f"生成非锁定输出组合 {i+1} 的条件:")
                    print(f"  逻辑条件: {logic_conditions}")
                    print(f"  比较条件: []")
                    
                    for j, var_combo in enumerate(var_combinations):
                        combo_idx = indices[j]
                        lower_val, upper_val = var_combo['combinations'][combo_idx]
                        
                        print(f"  变量组合 {j+1}: ({lower_val}, {upper_val})")
                        
                        # 如果是True条件，跳过该变量（不添加任何条件）
                        if lower_val == 'True' and upper_val == 'True':
                            print(f"    跳过True条件")
                            continue
                        
                        if var_combo['is_comparison']:
                            # 比较控件：生成 v1 / v2 >= lower and v1 / v2 <= upper 的条件
                            var1 = var_combo['var1']
                            var2 = var_combo['var2']
                            comp_conditions = []
                            comp_conditions.append(f"{var1} / {var2} >= {lower_val}")
                            comp_conditions.append(f"{var1} / {var2} <= {upper_val}")
                            current_conditions.append(' and '.join(comp_conditions))
                            print(f"    添加比较条件: {' and '.join(comp_conditions)}")
                        else:
                            # 普通变量：生成 var >= lower and var <= upper 的条件
                            var_name = var_combo['var_name']
                            var_conditions = []
                            var_conditions.append(f"{var_name} >= {lower_val}")
                            var_conditions.append(f"{var_name} <= {upper_val}")
                            current_conditions.append(' and '.join(var_conditions))
                            print(f"    添加变量条件: {' and '.join(var_conditions)}")
                    
                    print(f"  最终条件: {current_conditions}")
                    
                    # 生成公式
                    if current_conditions:
                        cond_str = "if " + " and ".join(current_conditions) + ":"
                    else:
                        cond_str = "if True:"
                    
                    # 为每个特殊组合生成公式
                    if special_result_combinations:
                        print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                        for special_combo in special_result_combinations:
                            # 合并特殊组合和其他result变量
                            all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                            if all_result_vars:
                                result_expr = "result = " + " + ".join(all_result_vars)
                            else:
                                result_expr = "result = 0"
                            
                            # 为每个排序方式生成一个公式
                            for sort_mode in special_combo['sort_modes']:
                                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                                formula_list.append({
                                    'formula': formula,
                                    'sort_mode': sort_mode,
                                    'result_vars': all_result_vars
                                })
                    else:
                        # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                        print(f"没有特殊组合")
                        all_result_vars = other_result_vars + special_forward_result_vars
                        if all_result_vars:
                            result_expr = "result = " + " + ".join(all_result_vars)
                        else:
                            result_expr = "result = 0"
                        
                        # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                        # 获取用户设置的排序方式
                        user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                        print(f"user_sort_mode: {user_sort_mode}")
                        
                        # 生成一个公式
                        formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                        formula_list.append({
                            'formula': formula,
                            'sort_mode': user_sort_mode,
                            'result_vars': all_result_vars
                        })
        
        # 如果有逻辑控件参与组合，只生成一个组合（所有勾选的逻辑条件用and连接）
        if logic_combination_vars:
            print(f"有 {len(logic_combination_vars)} 个逻辑控件参与组合，只生成一个组合")
            
            # 收集所有勾选的逻辑控件条件
            logic_conditions = [logic_var_info['var_name'] for logic_var_info in logic_combination_vars]
            logic_condition_str = " and ".join(logic_conditions)
            print(f"逻辑控件组合: {logic_condition_str}")
            
            # 为每个公式添加逻辑控件条件
            for formula_obj in formula_list:
                original_formula = formula_obj['formula']
                if 'if ' in original_formula:
                    # 找到if行的结束位置
                    if_end_pos = original_formula.find(':')
                    if if_end_pos != -1:
                        # 获取原始if条件
                        if_condition = original_formula[3:if_end_pos].strip()
                        
                        # 构建新的if条件 - 在原有条件基础上添加逻辑控件条件
                        if if_condition == 'True':
                            new_condition = f"if {logic_condition_str}:"
                        else:
                            new_condition = f"if {if_condition} and {logic_condition_str}:"
                        
                        # 完全重新构建公式
                        new_formula = new_condition + original_formula[if_end_pos + 1:]  # +1 跳过冒号
                        formula_obj['formula'] = new_formula
                        
                        print(f"  生成逻辑组合公式: {logic_condition_str}")
        
        for i, formula_obj in enumerate(formula_list):
            print(f"公式 {i+1} (排序方式: {formula_obj['sort_mode']}):")
            print(formula_obj['formula'])
            print("-" * 50)
        return formula_list

    def optimize_formula_list(self, secondary_analysis_count=1):
        """
        生成优化公式列表，用于二次分析
        根据统计值生成优化的变量范围组合：
        - 下限固定为统计最小值，上限从统计最大值按步长减少到正值中值
        - 上限固定为统计最大值，下限从统计最小值按步长增加到负值中值
        步长值为 (正值中值 - 负值中值) / 4 的整数部分
        
        新增二次分析逻辑：
        - 当选择左单向时，最大值逐渐减步长，分析二次分析次数设置值（如果减超最小值停止）
        - 当选择右单向时，最小值逐渐加步长，分析设置的次数（如果加超最大值停止）
        - 当选择全方向时，两边各分析设置的二次分析次数，然后生成笛卡尔积组合
        """
        
        overall_stats = self.main_window.overall_stats
        if not overall_stats:
            print("没有可用的统计结果，无法进行优化")
            return []
        
        # 检查是否锁定输出
        lock_output = False
        if hasattr(self.main_window, 'last_lock_output'):
            lock_output = self.main_window.last_lock_output
        
        formula_list = []
        
        # 收集需要参与组合的逻辑控件（所有逻辑控件都参与）
        logic_combination_vars = []
        logic_map = get_abbr_logic_map()
        
        # 遍历所有逻辑控件
        for en, widgets in self.var_widgets.items():
            if 'checkbox' in widgets and 'lower' not in widgets:
                if widgets['checkbox'].isChecked():
                    # 查找对应的中文名称
                    logic_zh = None
                    for zh, en_name in logic_map.items():
                        if en_name == en:
                            logic_zh = zh
                            break
                    
                    logic_combination_vars.append({
                        'var_name': en,
                        'zh_name': logic_zh or en
                    })
                    print(f"  添加逻辑控件到优化组合: {en} ({logic_zh or en})")
        
        # 收集需要优化的变量控件
        optimization_vars = []
        abbr_map = get_abbr_map()
        
        for zh_name, variable_name in abbr_map.items():
            if variable_name in self.var_widgets:
                widgets = self.var_widgets[variable_name]
                if 'lower' in widgets and 'upper' in widgets and 'step' in widgets and 'direction' in widgets:
                    # 对于同时有圆框和方框的变量，需要方框勾选才参与组合
                    # 对于只有方框的变量，只需要方框勾选
                    should_include = widgets['checkbox'].isChecked()
                    if should_include:
                        # 获取统计值
                        max_key = f'{variable_name}_max'
                        min_key = f'{variable_name}_min'
                        positive_median_key = f'{variable_name}_positive_median'
                        negative_median_key = f'{variable_name}_negative_median'
                        
                        max_value = overall_stats.get(max_key)
                        min_value = overall_stats.get(min_key)
                        positive_median = overall_stats.get(positive_median_key)
                        negative_median = overall_stats.get(negative_median_key)
                        
                        # 获取当前输入框的值作为起始点
                        current_lower = float(widgets['lower'].text()) if widgets['lower'].text() else 0
                        current_upper = float(widgets['upper'].text()) if widgets['upper'].text() else 0
                        
                        # 获取步长值和方向
                        # 如果步长输入框为空，按单一条件处理（步长为0）
                        step_value = float(widgets['step'].text()) if widgets['step'].text() else 0
                        direction = widgets['direction'].currentText() if 'direction' in widgets else ""
                        
                        if max_value is not None and min_value is not None and step_value is not None and step_value >= 0:
                            has_logic = widgets.get('logic_check', None) and widgets['logic_check'].isChecked()
                            
                            print(f"  添加变量到优化组合: {variable_name}, 含逻辑: {has_logic}, 方向: {direction}")
                            print(f"    统计值: min={min_value}, max={max_value}, pos_median={positive_median}, neg_median={negative_median}, step={step_value}")
                            print(f"    当前输入值: lower={current_lower}, upper={current_upper}")
                            
                            optimization_vars.append({
                                'var_name': variable_name,
                                'current_lower': current_lower,
                                'current_upper': current_upper,
                                'positive_median': positive_median,
                                'negative_median': negative_median,
                                'step_value': step_value,
                                'direction': direction,
                                'has_logic': has_logic,
                                'is_comparison': False  # 标记为普通变量
                            })
        
        # 收集向前参数，也参与优化组合生成（使用中值优化逻辑）
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
                if v.get('enable'):
                    # 获取统计值
                    max_key = f'{en}_max'
                    min_key = f'{en}_min'
                    positive_median_key = f'{en}_positive_median'
                    negative_median_key = f'{en}_negative_median'
                    
                    max_value = overall_stats.get(max_key)
                    min_value = overall_stats.get(min_key)
                    positive_median = overall_stats.get(positive_median_key)
                    negative_median = overall_stats.get(negative_median_key)
                    
                    # 获取当前输入框的值作为起始点
                    lower_text = v.get('lower', '').strip()
                    upper_text = v.get('upper', '').strip()
                    step_text = v.get('step', '').strip()
                    
                    if lower_text and upper_text:  # 只检查下限和上限，步长可以为空
                        try:
                            current_lower = float(lower_text)
                            current_upper = float(upper_text)
                            # 如果步长为空，按单一条件处理（步长为0）
                            if step_text:
                                step_value = float(step_text)
                            else:
                                step_value = 0
                            
                            if max_value is not None and min_value is not None and step_value is not None and step_value >= 0:
                                has_logic = v.get('logic', False)
                                direction = v.get('direction', '右单向')
                                
                                print(f"  添加向前参数到优化组合: {en}, 方向: {direction}")
                                print(f"    统计值: min={min_value}, max={max_value}, pos_median={positive_median}, neg_median={negative_median}, step={step_value}")
                                print(f"    当前输入值: lower={current_lower}, upper={current_upper}")
                                
                                optimization_vars.append({
                                    'var_name': en,
                                    'current_lower': current_lower,
                                    'current_upper': current_upper,
                                    'positive_median': positive_median,
                                    'negative_median': negative_median,
                                    'step_value': step_value,
                                    'direction': direction,
                                    'has_logic': has_logic,
                                    'is_comparison': False  # 标记为普通变量
                                })
                        except ValueError as e:
                            print(f"  向前参数数值转换失败: {e}")
                            continue
                    else:
                        print(f"  向前参数不完整，跳过")
        
        print(f"优化组合变量数量: {len(optimization_vars)}")
        
        # 收集圆框变量（这些在所有组合中都一样）
        # 特殊处理四个变量的result组合
        special_result_combinations = self._generate_special_result_combinations()
        print(f"optimize_formula_list中特殊组合数量: {len(special_result_combinations)}")
        
        # 收集其他圆框变量（排除特殊变量和get_abbr_round_only_map中的变量）
        other_result_vars = []
        # 获取get_abbr_round_only_map中的变量名列表，用于排除
        round_only_vars = set()
        for (zh, en), en_val in self.abbr_round_only_map.items():
            round_only_vars.add(en_val)
        
        for en, widgets in self.var_widgets.items():
            # 排除特殊变量和get_abbr_round_only_map中的变量
            if (en not in ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum'] and 
                en not in round_only_vars):
                if 'round_checkbox' in widgets and widgets['round_checkbox'].isChecked():
                    other_result_vars.append(en)
        
        # 收集向前参数的圆框变量
        # 8个特殊向前参数变量（正负相加值）不参与组合，直接加到result
        special_forward_result_vars = []
        other_forward_result_vars = []
        
        # 检查是否有基础变量，如果没有基础变量，8个特殊向前参数变量已经在_generate_special_result_combinations中处理了
        has_basic_vars = any(
            widgets.get('round_checkbox', None) and widgets['round_checkbox'].isChecked()
            for en, widgets in self.var_widgets.items()
            if en in ['cont_sum_pos_sum', 'cont_sum_neg_sum', 'valid_pos_sum', 'valid_neg_sum']
        )
        
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
                if v.get('round'):
                    # 检查是否是8个特殊向前参数变量
                    if en in ['forward_min_valid_pos_sum', 'forward_min_valid_neg_sum',
                             'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
                             'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
                             'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum']:
                        # 只有当有基础变量时，才添加到special_forward_result_vars
                        # 如果没有基础变量，这些变量已经在_generate_special_result_combinations中处理了
                        if has_basic_vars:
                            special_forward_result_vars.append(en)
                    else:
                        other_forward_result_vars.append(en)
        
        # 将其他向前参数的圆框变量添加到other_result_vars
        other_result_vars.extend(other_forward_result_vars)
        
        # 收集比较控件条件
        comparison_conditions = []
        has_logic_comparison = False
        # 收集比较控件到optimization_vars中，参与优化组合（使用generate_formula_list的规则）
        for comp in self.comparison_widgets:
            if comp['checkbox'].isChecked():
                var1 = comp['var1'].currentText()
                lower = comp['lower'].text().strip()
                upper = comp['upper'].text().strip()
                step = comp['step'].text().strip()
                direction = comp['direction'].currentText()
                var2 = comp['var2'].currentText()
                has_logic = comp['logic_check'].isChecked()
                
                var1_en = next((en for zh, en in self.abbr_map.items() if zh == var1), None)
                var2_en = next((en for zh, en in self.abbr_map.items() if zh == var2), None)
                
                if lower and upper and var1_en and var2_en:
                    try:
                        # 如果步长为空，设为0
                        if step:
                            step_val = float(step)
                        else:
                            step_val = 0
                        lower_val = float(lower)
                        upper_val = float(upper)
                        
                        # 将比较控件也加入到optimization_vars中，参与优化组合
                        optimization_vars.append({
                            'var1': var1_en,
                            'var2': var2_en,
                            'lower': lower_val,
                            'upper': upper_val,
                            'step': step_val,
                            'direction': direction,
                            'has_logic': has_logic,
                            'is_comparison': True  # 标记为比较控件
                        })
                        
                        if has_logic:
                            has_logic_comparison = True
                    except ValueError:
                        continue
        # 生成优化组合
        print(f"lock_output: {lock_output}")
        # 初始化logic_conditions，避免未定义错误
        logic_conditions = []
        if lock_output:
            # 锁定输出时，结果部分只生成一种组合（所有勾选的result变量直接加号拼接）
            all_result_vars = []
            for special_combo in special_result_combinations:
                all_result_vars.extend(special_combo['result_vars'])
            all_result_vars.extend(other_result_vars)
            all_result_vars.extend(special_forward_result_vars)
            # 去重
            all_result_vars = list(dict.fromkeys(all_result_vars))
            
            # 排序方式：取主界面当前排序
            user_sort_mode = self.sort_combo.currentText() if self.sort_combo else (self.main_window.last_sort_mode if hasattr(self.main_window, 'last_sort_mode') else '最大值排序')
            
            if not optimization_vars:
                # 如果没有需要优化的变量，只生成一个公式
                all_conditions = []
                if all_conditions:
                    cond_str = "if " + " and ".join(all_conditions) + ":"
                else:
                    cond_str = "if True:"
                result_expr = "result = " + " + ".join(all_result_vars) if all_result_vars else "result = 0"
                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                formula_list.append({
                    'formula': formula,
                    'sort_mode': user_sort_mode,
                    'result_vars': all_result_vars
                })
                
                # 如果有含逻辑的比较控件，额外生成一个if True的公式
                if has_logic_comparison:
                    true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                    formula_list.append({
                        'formula': true_formula,
                        'sort_mode': user_sort_mode,
                        'result_vars': all_result_vars
                    })
            else:
                # 如果有需要优化的变量，生成优化组合
                var_combinations = []
                
                for var_info in optimization_vars:
                    is_comparison = var_info.get('is_comparison', False)
                    
                    if is_comparison:
                        # 比较控件 - 使用generate_formula_list的规则（不使用中值优化逻辑）
                        var1 = var_info['var1']
                        var2 = var_info['var2']
                        lower_val = var_info['lower']
                        upper_val = var_info['upper']
                        step_val = var_info['step']
                        direction = var_info['direction']
                        has_logic = var_info['has_logic']
                        
                        print(f"比较控件优化组合 - {var1} vs {var2}:")
                        print(f"  下限: {lower_val}, 上限: {upper_val}, 步长: {step_val}")
                        print(f"  方向: {direction}, 含逻辑: {has_logic}")
                        
                        # 比较控件使用标准组合生成逻辑（不使用中值优化）
                        combinations = []
                        
                        # 如果步长为0或空，生成单一组合
                        if step_val == 0 or step_val == '' or step_val is None:
                            combinations.append((round(lower_val, 2), round(upper_val, 2)))
                            print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                        else:
                            if direction == "右单向":
                                # 最大值不变，最小值按步长变化
                                current_lower = lower_val
                                # 根据步长正负调整循环条件
                                if step_val > 0:
                                    while current_lower < upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                else:  # step_val < 0
                                    while current_lower > upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                            
                            elif direction == "左单向":
                                # 最小值不变，最大值按步长变化
                                current_upper = upper_val
                                # 根据步长正负调整循环条件
                                if step_val > 0:
                                    while current_upper > lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                else:  # step_val < 0
                                    while current_upper < lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                            
                            elif direction == "全方向":
                                combinations = []
                                # 右单向：上限不变，下限不断加步长
                                current_lower = lower_val
                                if step_val > 0:
                                    while current_lower < upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                else:
                                    while current_lower > upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                # 左单向：下限不变，上限不断减步长
                                current_upper = upper_val
                                if step_val > 0:
                                    while current_upper > lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                else:
                                    while current_upper < lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                # 剔除重复项和下限=上限的情况
                                combinations = list({(a, b) for a, b in combinations if a != b})
                                combinations.sort()
                        
                        print(f"  比较控件 {var1} vs {var2} 生成 {len(combinations)} 个标准组合")
                        for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                            print(f"    组合 {i+1}: ({lower}, {upper})")
                        if len(combinations) > 5:
                            print(f"    ... 还有 {len(combinations) - 5} 个组合")
                    else:
                        # 普通变量 - 检查是否是abbr_map变量
                        var_name = var_info['var_name']
                        has_logic = var_info['has_logic']
                        
                        # 检查是否是abbr_map变量或向前参数（都需要使用中值优化逻辑）
                        is_abbr_map_var = var_name in [en for zh, en in abbr_map.items()]
                        is_forward_param = hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state and var_name in self.main_window.forward_param_state
                        should_use_median_optimization = is_abbr_map_var or is_forward_param
                        
                        if should_use_median_optimization:
                            # abbr_map变量和向前参数使用二次分析逻辑
                            current_lower = var_info['current_lower']
                            current_upper = var_info['current_upper']
                            step_value = var_info['step_value']
                            direction = var_info['direction']
                            
                            # 获取统计的最小值和最大值作为边界
                            max_value = overall_stats.get(f'{var_name}_max')
                            min_value = overall_stats.get(f'{var_name}_min')
                            
                            combinations = []
                            
                            # 如果步长为0，生成单一组合
                            if step_value == 0:
                                combinations.append((round(current_lower, 2), round(current_upper, 2)))
                                print(f"  步长为0，生成单一组合: ({round(current_lower, 2)}, {round(current_upper, 2)})")
                            else:
                                if direction == "左单向":
                                    # 最大值逐渐减步长，分析二次分析次数设置值
                                    current_upper_val = current_upper
                                    for i in range(secondary_analysis_count):
                                        if min_value is not None and current_upper_val < min_value:
                                            # 如果减超最小值停止
                                            break
                                        combinations.append((round(current_lower, 2), round(current_upper_val, 2)))
                                        current_upper_val -= step_value
                                    
                                    print(f"  左单向变量 {var_name} 生成 {len(combinations)} 个组合")
                                    for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                                        print(f"    组合 {i+1}: ({lower}, {upper})")
                                    if len(combinations) > 5:
                                        print(f"    ... 还有 {len(combinations) - 5} 个组合")
                                        
                                elif direction == "右单向":
                                    # 最小值逐渐加步长，分析设置的次数
                                    current_lower_val = current_lower
                                    for i in range(secondary_analysis_count):
                                        if max_value is not None and current_lower_val > max_value:
                                            # 如果加超最大值停止
                                            break
                                        combinations.append((round(current_lower_val, 2), round(current_upper, 2)))
                                        current_lower_val += step_value
                                    
                                    print(f"  右单向变量 {var_name} 生成 {len(combinations)} 个组合")
                                    for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                                        print(f"    组合 {i+1}: ({lower}, {upper})")
                                    if len(combinations) > 5:
                                        print(f"    ... 还有 {len(combinations) - 5} 个组合")
                                        
                                elif direction == "全方向":
                                    # 两边各分析设置的二次分析次数，然后生成笛卡尔积
                                    # 左方向：最大值逐渐减步长
                                    left_upper_values = []
                                    current_upper_val = current_upper
                                    for i in range(secondary_analysis_count):
                                        if min_value is not None and current_upper_val < min_value:
                                            break
                                        left_upper_values.append(round(current_upper_val, 2))
                                        current_upper_val -= step_value
                                    
                                    # 右方向：最小值逐渐加步长
                                    right_lower_values = []
                                    current_lower_val = current_lower
                                    for i in range(secondary_analysis_count):
                                        if max_value is not None and current_lower_val > max_value:
                                            break
                                        right_lower_values.append(round(current_lower_val, 2))
                                        current_lower_val += step_value
                                    
                                    # 生成笛卡尔积组合
                                    for left_upper in left_upper_values:
                                        for right_lower in right_lower_values:
                                            if right_lower <= left_upper:  # 确保下限不大于上限
                                                combinations.append((right_lower, left_upper))
                                    
                                    # 剔除重复项并排序
                                    combinations = list({(a, b) for a, b in combinations})
                                    combinations.sort()
                                    
                                    print(f"  全方向变量 {var_name} 生成 {len(combinations)} 个组合")
                                    print(f"    左单向上限值: {left_upper_values}")
                                    print(f"    右单向下限值: {right_lower_values}")
                                    for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                                        print(f"    组合 {i+1}: ({lower}, {upper})")
                                    if len(combinations) > 5:
                                        print(f"    ... 还有 {len(combinations) - 5} 个组合")
                        else:
                            # 非中值优化变量使用generate_formula_list的规则
                            lower_val = var_info['lower']
                            upper_val = var_info['upper']
                            step_val = var_info['step']
                            direction = var_info['direction']
                            
                            combinations = []
                            
                            # 如果步长为0或空，生成单一组合
                            if step_val == 0 or step_val == '' or step_val is None:
                                combinations.append((round(lower_val, 2), round(upper_val, 2)))
                                print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                            else:
                                if direction == "右单向":
                                    # 最大值不变，最小值按步长变化
                                    current_lower = lower_val
                                    # 根据步长正负调整循环条件
                                    if step_val > 0:
                                        while current_lower < upper_val:
                                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                            current_lower += step_val
                                    else:  # step_val < 0
                                        while current_lower > upper_val:
                                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                            current_lower += step_val
                                
                                elif direction == "左单向":
                                    # 最小值不变，最大值按步长变化
                                    current_upper = upper_val
                                    # 根据步长正负调整循环条件
                                    if step_val > 0:
                                        while current_upper > lower_val:
                                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                            current_upper -= step_val
                                    else:  # step_val < 0
                                        while current_upper < lower_val:
                                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                            current_upper -= step_val
                                
                                elif direction == "全方向":
                                    combinations = []
                                    # 右单向：上限不变，下限不断加步长
                                    current_lower = lower_val
                                    if step_val > 0:
                                        while current_lower < upper_val:
                                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                            current_lower += step_val
                                    else:
                                        while current_lower > upper_val:
                                            combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                            current_lower += step_val
                                    # 左单向：下限不变，上限不断减步长
                                    current_upper = upper_val
                                    if step_val > 0:
                                        while current_upper > lower_val:
                                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                            current_upper -= step_val
                                    else:
                                        while current_upper < lower_val:
                                            combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                            current_upper -= step_val
                                    # 剔除重复项和下限=上限的情况
                                    combinations = list({(a, b) for a, b in combinations if a != b})
                                    combinations.sort()
                            
                            print(f"  非中值优化变量 {var_name} 生成 {len(combinations)} 个标准组合")
                            for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                                print(f"    组合 {i+1}: ({lower}, {upper})")
                            if len(combinations) > 5:
                                print(f"    ... 还有 {len(combinations) - 5} 个组合")
                    
                    # 处理含逻辑：如果勾选了含逻辑，添加一个True条件
                    if has_logic:
                        combinations.append(('True', 'True'))
                    
                    if is_comparison:
                        var_combinations.append({
                            'var1': var1,
                            'var2': var2,
                            'combinations': combinations,
                            'is_comparison': True  # 标记为比较控件
                        })
                    else:
                        var_combinations.append({
                            'var_name': var_name,
                            'combinations': combinations,
                            'is_comparison': False  # 标记为普通变量
                        })
                
                # 生成笛卡尔积
                if var_combinations:
                    # 获取所有变量的组合数量
                    total_combinations = 1
                    for var_combo in var_combinations:
                        total_combinations *= len(var_combo['combinations'])
                    
                    print(f"锁定输出模式：总共 {total_combinations} 个优化组合")
                    
                    # 为每个条件组合生成公式
                    for i in range(total_combinations):
                        # 计算当前组合的索引
                        indices = []
                        temp = i
                        for var_combo in var_combinations:
                            indices.append(temp % len(var_combo['combinations']))
                            temp //= len(var_combo['combinations'])
                        
                        # 构建当前组合的条件 - 每个笛卡尔积组合都应该有独立的条件
                        current_conditions = logic_conditions.copy()  # 复制逻辑条件，避免引用问题
                        
                        print(f"生成锁定输出优化组合 {i+1} 的条件:")
                        print(f"  逻辑条件: {logic_conditions}")
                        print(f"  比较条件: []")
                        
                        for j, var_combo in enumerate(var_combinations):
                            combo_idx = indices[j]
                            lower_val, upper_val = var_combo['combinations'][combo_idx]
                            
                            print(f"  变量组合 {j+1}: ({lower_val}, {upper_val})")
                            
                            # 如果是True条件，跳过该变量（不添加任何条件）
                            if lower_val == 'True' and upper_val == 'True':
                                print(f"    跳过True条件")
                                continue
                            
                            if var_combo['is_comparison']:
                                # 比较控件：生成 v1 / v2 >= lower and v1 / v2 <= upper 的条件
                                var1 = var_combo['var1']
                                var2 = var_combo['var2']
                                comp_conditions = []
                                comp_conditions.append(f"{var1} / {var2} >= {lower_val}")
                                comp_conditions.append(f"{var1} / {var2} <= {upper_val}")
                                current_conditions.append(' and '.join(comp_conditions))
                                print(f"    添加比较条件: {' and '.join(comp_conditions)}")
                            else:
                                # 普通变量：生成 var >= lower and var <= upper 的条件
                                var_name = var_combo['var_name']
                                var_conditions = []
                                var_conditions.append(f"{var_name} >= {lower_val}")
                                var_conditions.append(f"{var_name} <= {upper_val}")
                                current_conditions.append(' and '.join(var_conditions))
                                print(f"    添加变量条件: {' and '.join(var_conditions)}")
                        
                        print(f"  最终条件: {current_conditions}")
                        
                        # 生成公式
                        if current_conditions:
                            cond_str = "if " + " and ".join(current_conditions) + ":"
                        else:
                            cond_str = "if True:"
                        
                        # 为每个特殊组合生成公式
                        if special_result_combinations:
                            print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                            for special_combo in special_result_combinations:
                                # 合并特殊组合和其他result变量
                                all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                                if all_result_vars:
                                    result_expr = "result = " + " + ".join(all_result_vars)
                                else:
                                    result_expr = "result = 0"
                                
                                # 为每个排序方式生成一个公式
                                for sort_mode in special_combo['sort_modes']:
                                    formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                                    formula_list.append({
                                        'formula': formula,
                                        'sort_mode': sort_mode,
                                        'result_vars': all_result_vars
                                    })
                        else:
                            # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                            print(f"没有特殊组合")
                            all_result_vars = other_result_vars + special_forward_result_vars
                            if all_result_vars:
                                result_expr = "result = " + " + ".join(all_result_vars)
                            else:
                                result_expr = "result = 0"
                            
                            # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                            # 获取用户设置的排序方式
                            user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                            print(f"user_sort_mode: {user_sort_mode}")
                            
                            # 生成一个公式
                            formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                            formula_list.append({
                                'formula': formula,
                                'sort_mode': user_sort_mode,
                                'result_vars': all_result_vars
                            })
            
            # 锁定输出模式下也需要进行逻辑控件组合处理
            if logic_combination_vars:
                print(f"锁定输出模式下进行逻辑控件组合处理")
                original_formula_list = formula_list.copy()
                formula_list = []
                
                # 锁定输出模式下，逻辑控件也只生成一个组合（所有勾选的逻辑条件用and连接）
                if logic_combination_vars:
                    print(f"锁定输出模式：有 {len(logic_combination_vars)} 个逻辑控件参与组合，只生成一个组合")
                    
                    # 收集所有勾选的逻辑控件条件
                    logic_conditions = [logic_var_info['var_name'] for logic_var_info in logic_combination_vars]
                    logic_condition_str = " and ".join(logic_conditions)
                    print(f"锁定输出模式逻辑控件组合: {logic_condition_str}")
                    
                    # 为每个公式添加逻辑控件条件
                    for formula_obj in original_formula_list:
                        original_formula = formula_obj['formula']
                        if 'if ' in original_formula:
                            # 找到if行的结束位置
                            if_end_pos = original_formula.find(':')
                            if if_end_pos != -1:
                                # 获取原始if条件
                                if_condition = original_formula[3:if_end_pos].strip()
                                
                                # 构建新的if条件 - 在原有条件基础上添加逻辑控件条件
                                if if_condition == 'True':
                                    new_condition = f"if {logic_condition_str}:"
                                else:
                                    new_condition = f"if {if_condition} and {logic_condition_str}:"
                                
                                # 完全重新构建公式
                                new_formula = new_condition + original_formula[if_end_pos + 1:]  # +1 跳过冒号
                                formula_obj['formula'] = new_formula
                                
                                print(f"  生成锁定输出逻辑组合公式: {logic_condition_str}")
                        formula_list.append(formula_obj)
                else:
                    # 没有逻辑控件，直接添加原公式
                    formula_list.extend(original_formula_list)
            
            for i, formula_obj in enumerate(formula_list):
                print(f"锁定输出优化公式 {i+1} (排序方式: {formula_obj['sort_mode']}):")
                print(formula_obj['formula'])
                print("-" * 50)
            return formula_list
        elif not optimization_vars:
            # 如果没有需要优化的变量，为每个特殊result组合生成一个公式
            # 注意：逻辑控件条件在最后统一处理，这里不处理
            all_conditions = []
            if all_conditions:
                cond_str = "if " + " and ".join(all_conditions) + ":"
            else:
                cond_str = "if True:"
            
            # 为每个特殊组合生成公式
            if special_result_combinations:
                print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                for special_combo in special_result_combinations:
                    # 合并特殊组合和其他result变量
                    # 注意：8个特殊向前参数变量已经在special_combo['result_vars']中了（当没有基础变量时）
                    # 所以这里只需要添加其他result变量
                    all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                    if all_result_vars:
                        result_expr = "result = " + " + ".join(all_result_vars)
                    else:
                        result_expr = "result = 0"
                    
                    # 为每个排序方式生成一个公式
                    for sort_mode in special_combo['sort_modes']:
                        formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                        formula_list.append({
                            'formula': formula,
                            'sort_mode': sort_mode,
                            'result_vars': all_result_vars
                        })
                        
                        # 如果有含逻辑的比较控件，额外生成一个if True的公式
                        if has_logic_comparison:
                            true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                            formula_list.append({
                                'formula': true_formula,
                                'sort_mode': sort_mode,
                                'result_vars': all_result_vars
                            })
            else:
                # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                print(f"没有特殊组合")
                all_result_vars = other_result_vars + special_forward_result_vars
                if all_result_vars:
                    result_expr = "result = " + " + ".join(all_result_vars)
                else:
                    result_expr = "result = 0"
                
                # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                # 获取用户设置的排序方式
                user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                print(f"user_sort_mode: {user_sort_mode}")
                
                # 生成一个公式
                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                formula_list.append({
                    'formula': formula,
                    'sort_mode': user_sort_mode,
                    'result_vars': all_result_vars
                })
                
                # 如果有含逻辑的比较控件，额外生成一个if True的公式
                if has_logic_comparison:
                    true_formula = f"if True:\n    {result_expr}\nelse:\n    result = 0"
                    formula_list.append({
                        'formula': true_formula,
                        'sort_mode': user_sort_mode,
                        'result_vars': all_result_vars
                    })
        else:
            # 为每个变量生成优化组合
            var_combinations = []
            
            for var_info in optimization_vars:
                is_comparison = var_info.get('is_comparison', False)
                
                if is_comparison:
                    # 比较控件 - 使用generate_formula_list的规则（不使用中值优化逻辑）
                    var1 = var_info['var1']
                    var2 = var_info['var2']
                    lower_val = var_info['lower']
                    upper_val = var_info['upper']
                    step_val = var_info['step']
                    direction = var_info['direction']
                    has_logic = var_info['has_logic']
                    
                    print(f"比较控件优化组合 - {var1} vs {var2}:")
                    print(f"  下限: {lower_val}, 上限: {upper_val}, 步长: {step_val}")
                    print(f"  方向: {direction}, 含逻辑: {has_logic}")
                    
                    # 比较控件使用标准组合生成逻辑（不使用中值优化）
                    combinations = []
                    
                    # 如果步长为0或空，生成单一组合
                    if step_val == 0 or step_val == '' or step_val is None:
                        combinations.append((round(lower_val, 2), round(upper_val, 2)))
                        print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                    else:
                        if direction == "右单向":
                            # 最大值不变，最小值按步长变化
                            current_lower = lower_val
                            # 根据步长正负调整循环条件
                            if step_val > 0:
                                while current_lower < upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            else:  # step_val < 0
                                while current_lower > upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                        
                        elif direction == "左单向":
                            # 最小值不变，最大值按步长变化
                            current_upper = upper_val
                            # 根据步长正负调整循环条件
                            if step_val > 0:
                                while current_upper > lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            else:  # step_val < 0
                                while current_upper < lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                        
                        elif direction == "全方向":
                            combinations = []
                            # 右单向：上限不变，下限不断加步长
                            current_lower = lower_val
                            if step_val > 0:
                                while current_lower < upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            else:
                                while current_lower > upper_val:
                                    combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                    current_lower += step_val
                            # 左单向：下限不变，上限不断减步长
                            current_upper = upper_val
                            if step_val > 0:
                                while current_upper > lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            else:
                                while current_upper < lower_val:
                                    combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                    current_upper -= step_val
                            # 剔除重复项和下限=上限的情况
                            combinations = list({(a, b) for a, b in combinations if a != b})
                            combinations.sort()
                    
                    print(f"  比较控件 {var1} vs {var2} 生成 {len(combinations)} 个标准组合")
                    for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                        print(f"    组合 {i+1}: ({lower}, {upper})")
                    if len(combinations) > 5:
                        print(f"    ... 还有 {len(combinations) - 5} 个组合")
                else:
                    # 普通变量 - 检查是否是abbr_map变量
                    var_name = var_info['var_name']
                    has_logic = var_info['has_logic']
                    
                    # 检查是否是abbr_map变量或向前参数（都需要使用中值优化逻辑）
                    is_abbr_map_var = var_name in [en for zh, en in abbr_map.items()]
                    is_forward_param = hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state and var_name in self.main_window.forward_param_state
                    should_use_median_optimization = is_abbr_map_var or is_forward_param
                    
                    if should_use_median_optimization:
                        # abbr_map变量使用中值优化逻辑
                        current_lower = var_info['current_lower']
                        current_upper = var_info['current_upper']
                        positive_median = var_info['positive_median']
                        negative_median = var_info['negative_median']
                        step_value = var_info['step_value']
                        
                        # 生成上限值列表：从当前上限按步长减少到正值中值为止
                        upper_values = []
                        if positive_median is not None and current_upper > positive_median:
                            if step_value > 0:  # 只有当步长大于0时才进行循环
                                upper_val = current_upper
                                while upper_val >= positive_median:
                                    upper_values.append(round(upper_val, 2))
                                    upper_val -= step_value
                            else:
                                # 如果步长为0，只使用当前上限
                                upper_values.append(round(current_upper, 2))
                        else:
                            # 如果正值中值为空或当前上限不大于正值中值，使用当前上限
                            upper_values.append(round(current_upper, 2))
                        
                        # 生成下限值列表：从当前下限按步长增加到负值中值为止
                        lower_values = []
                        if negative_median is not None and current_lower < negative_median:
                            if step_value > 0:  # 只有当步长大于0时才进行循环
                                lower_val = current_lower
                                while lower_val <= negative_median:
                                    lower_values.append(round(lower_val, 2))
                                    lower_val += step_value
                            else:
                                # 如果步长为0，只使用当前下限
                                lower_values.append(round(current_lower, 2))
                        else:
                            # 如果负值中值为空或当前下限不小于负值中值，使用当前下限
                            lower_values.append(round(current_lower, 2))
                        
                        # 生成组合
                        combinations = []
                        
                        # 如果正值中值和负值中值都为空，生成单一条件
                        if positive_median is None and negative_median is None:
                            combinations.append((round(current_lower, 2), round(current_upper, 2)))
                            print(f"  正值中值和负值中值都为空，生成单一条件: ({round(current_lower, 2)}, {round(current_upper, 2)})")
                        else:
                            # 生成笛卡尔积组合
                            for lower in lower_values:
                                for upper in upper_values:
                                    if lower <= upper:  # 确保下限不大于上限
                                        combinations.append((lower, upper))
                            
                            # 剔除重复项
                            combinations = list({(a, b) for a, b in combinations})
                            combinations.sort()
                        
                        print(f"  中值优化变量 {var_name} 生成 {len(combinations)} 个中值优化组合")
                        for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                            print(f"    组合 {i+1}: ({lower}, {upper})")
                        if len(combinations) > 5:
                            print(f"    ... 还有 {len(combinations) - 5} 个组合")
                    else:
                        # 非中值优化变量使用generate_formula_list的规则
                        # 对于非中值优化变量，使用与锁定模式一致的字段名
                        lower_val = var_info['current_lower']
                        upper_val = var_info['current_upper']
                        step_val = var_info['step_value']
                        # 非中值优化变量没有direction字段，使用默认值
                        direction = "全方向"
                        
                        combinations = []
                        
                        # 如果步长为0或空，生成单一组合
                        if step_val == 0 or step_val == '' or step_val is None:
                            combinations.append((round(lower_val, 2), round(upper_val, 2)))
                            print(f"  步长为0或空，生成单一组合: ({round(lower_val, 2)}, {round(upper_val, 2)})")
                        else:
                            if direction == "右单向":
                                # 最大值不变，最小值按步长变化
                                current_lower = lower_val
                                # 根据步长正负调整循环条件
                                if step_val > 0:
                                    while current_lower < upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                else:  # step_val < 0
                                    while current_lower > upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                            
                            elif direction == "左单向":
                                # 最小值不变，最大值按步长变化
                                current_upper = upper_val
                                # 根据步长正负调整循环条件
                                if step_val > 0:
                                    while current_upper > lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                else:  # step_val < 0
                                    while current_upper < lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                            
                            elif direction == "全方向":
                                combinations = []
                                # 右单向：上限不变，下限不断加步长
                                current_lower = lower_val
                                if step_val > 0:
                                    while current_lower < upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                else:
                                    while current_lower > upper_val:
                                        combinations.append((round(current_lower, 2), round(upper_val, 2)))
                                        current_lower += step_val
                                # 左单向：下限不变，上限不断减步长
                                current_upper = upper_val
                                if step_val > 0:
                                    while current_upper > lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                else:
                                    while current_upper < lower_val:
                                        combinations.append((round(lower_val, 2), round(current_upper, 2)))
                                        current_upper -= step_val
                                # 剔除重复项和下限=上限的情况
                                combinations = list({(a, b) for a, b in combinations if a != b})
                                combinations.sort()
                        
                        print(f"  非中值优化变量 {var_name} 生成 {len(combinations)} 个标准组合")
                        for i, (lower, upper) in enumerate(combinations[:5]):  # 只显示前5个
                            print(f"    组合 {i+1}: ({lower}, {upper})")
                        if len(combinations) > 5:
                            print(f"    ... 还有 {len(combinations) - 5} 个组合")
                
                # 处理含逻辑：如果勾选了含逻辑，添加一个True条件
                if has_logic:
                    combinations.append(('True', 'True'))
                
                if is_comparison:
                    var_combinations.append({
                        'var1': var1,
                        'var2': var2,
                        'combinations': combinations,
                        'is_comparison': True  # 标记为比较控件
                    })
                else:
                    var_combinations.append({
                        'var_name': var_name,
                        'combinations': combinations,
                        'is_comparison': False  # 标记为普通变量
                    })
            
            # 生成笛卡尔积
            if var_combinations:
                # 获取所有变量的组合数量
                total_combinations = 1
                for var_combo in var_combinations:
                    total_combinations *= len(var_combo['combinations'])
                
                print(f"非锁定输出模式：总共 {total_combinations} 个优化组合")
                
                # 为每个条件组合生成公式
                for i in range(total_combinations):
                    # 计算当前组合的索引
                    indices = []
                    temp = i
                    for var_combo in var_combinations:
                        indices.append(temp % len(var_combo['combinations']))
                        temp //= len(var_combo['combinations'])
                    
                    # 构建当前组合的条件
                    current_conditions = logic_conditions.copy()
                    
                    print(f"生成非锁定输出优化组合 {i+1} 的条件:")
                    print(f"  逻辑条件: {logic_conditions}")
                    print(f"  比较条件: []")
                    
                    for j, var_combo in enumerate(var_combinations):
                        combo_idx = indices[j]
                        lower_val, upper_val = var_combo['combinations'][combo_idx]
                        
                        print(f"  变量组合 {j+1}: ({lower_val}, {upper_val})")
                        
                        # 如果是True条件，跳过该变量（不添加任何条件）
                        if lower_val == 'True' and upper_val == 'True':
                            print(f"    跳过True条件")
                            continue
                        
                        if var_combo['is_comparison']:
                            # 比较控件：生成 v1 / v2 >= lower and v1 / v2 <= upper 的条件
                            var1 = var_combo['var1']
                            var2 = var_combo['var2']
                            comp_conditions = []
                            comp_conditions.append(f"{var1} / {var2} >= {lower_val}")
                            comp_conditions.append(f"{var1} / {var2} <= {upper_val}")
                            current_conditions.append(' and '.join(comp_conditions))
                            print(f"    添加比较条件: {' and '.join(comp_conditions)}")
                        else:
                            # 普通变量：生成 var >= lower and var <= upper 的条件
                            var_name = var_combo['var_name']
                            var_conditions = []
                            var_conditions.append(f"{var_name} >= {lower_val}")
                            var_conditions.append(f"{var_name} <= {upper_val}")
                            current_conditions.append(' and '.join(var_conditions))
                            print(f"    添加变量条件: {' and '.join(var_conditions)}")
                    
                    print(f"  最终条件: {current_conditions}")
                    
                    # 生成公式
                    if current_conditions:
                        cond_str = "if " + " and ".join(current_conditions) + ":"
                    else:
                        cond_str = "if True:"
                    
                    # 为每个特殊组合生成公式
                    if special_result_combinations:
                        print(f"有特殊组合 special_result_combinations :{special_result_combinations}")
                        for special_combo in special_result_combinations:
                            # 合并特殊组合和其他result变量
                            all_result_vars = special_combo['result_vars'] + other_result_vars + special_forward_result_vars
                            if all_result_vars:
                                result_expr = "result = " + " + ".join(all_result_vars)
                            else:
                                result_expr = "result = 0"
                            
                            # 为每个排序方式生成一个公式
                            for sort_mode in special_combo['sort_modes']:
                                formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                                formula_list.append({
                                    'formula': formula,
                                    'sort_mode': sort_mode,
                                    'result_vars': all_result_vars
                                })
                    else:
                        # 容错处理：当没有特殊组合时，也要处理向前参数和其他result变量
                        print(f"没有特殊组合")
                        all_result_vars = other_result_vars + special_forward_result_vars
                        if all_result_vars:
                            result_expr = "result = " + " + ".join(all_result_vars)
                        else:
                            result_expr = "result = 0"
                        
                        # 向前相关参数不区分最大最小排序，以基础参数为准，如果没有基础参数，则按用户设置的排序
                        # 获取用户设置的排序方式
                        user_sort_mode = self.sort_combo.currentText() if self.sort_combo else '最大值排序'
                        print(f"user_sort_mode: {user_sort_mode}")
                        
                        # 生成一个公式
                        formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
                        formula_list.append({
                            'formula': formula,
                            'sort_mode': user_sort_mode,
                            'result_vars': all_result_vars
                        })
        
        # 如果有逻辑控件参与组合，只生成一个组合（所有勾选的逻辑条件用and连接）
        if logic_combination_vars:
            print(f"有 {len(logic_combination_vars)} 个逻辑控件参与组合，只生成一个组合")
            
            # 收集所有勾选的逻辑控件条件
            logic_conditions = [logic_var_info['var_name'] for logic_var_info in logic_combination_vars]
            logic_condition_str = " and ".join(logic_conditions)
            print(f"逻辑控件组合: {logic_condition_str}")
            
            # 为每个公式添加逻辑控件条件
            for formula_obj in formula_list:
                original_formula = formula_obj['formula']
                if 'if ' in original_formula:
                    # 找到if行的结束位置
                    if_end_pos = original_formula.find(':')
                    if if_end_pos != -1:
                        # 获取原始if条件
                        if_condition = original_formula[3:if_end_pos].strip()
                        
                        # 构建新的if条件 - 在原有条件基础上添加逻辑控件条件
                        if if_condition == 'True':
                            new_condition = f"if {logic_condition_str}:"
                        else:
                            new_condition = f"if {if_condition} and {logic_condition_str}:"
                        
                        # 完全重新构建公式
                        new_formula = new_condition + original_formula[if_end_pos + 1:]  # +1 跳过冒号
                        formula_obj['formula'] = new_formula
                        
                        print(f"  生成逻辑组合公式: {logic_condition_str}")
        
        for i, formula_obj in enumerate(formula_list):
            print(f"优化公式 {i+1} (排序方式: {formula_obj['sort_mode']}):")
            print(formula_obj['formula'])
            print("-" * 50)
        return formula_list

    def generate_special_params_combinations(self):
        """
        生成特殊变量的组合参数
        特殊变量包括：日期宽度、操作天数、止盈递增率
        这些变量只有上下限和步长，按步长递增生成组合
        如果未勾选，则用主界面参数
        返回参数元组列表：[(width, op_days, increment_rate), ...]
        """
        special_combinations = []
        special_vars = {}
        
        # 先收集勾选的变量
        for en, widgets in self.var_widgets.items():
            if en in ['width', 'op_days', 'increment_rate', 'after_gt_end_ratio', 'after_gt_start_ratio', 'stop_loss_inc_rate', 'stop_loss_after_gt_end_ratio', 'stop_loss_after_gt_start_ratio']:
                if 'checkbox' in widgets and widgets['checkbox'].isChecked():
                    lower_text = widgets.get('lower', '').text().strip()
                    upper_text = widgets.get('upper', '').text().strip()
                    step_text = widgets.get('step', '').text().strip()
                    if lower_text and upper_text and step_text:
                        try:
                            if en in ['width', 'op_days']:
                                # 日期宽度和操作天数使用整数
                                lower_val = int(float(lower_text))
                                upper_val = int(float(upper_text))
                                step_val = int(float(step_text))
                                # 生成整数序列
                                values = list(range(lower_val, upper_val + 1, step_val))
                            else:
                                # 止盈递增率使用浮点数，保留两位小数
                                lower_val = float(lower_text)
                                upper_val = float(upper_text)
                                step_val = float(step_text)
                                values = [round(v, 2) for v in
                                         list(self._frange(lower_val, upper_val, step_val))]
                            
                            special_vars[en] = {'values': values}
                        except ValueError:
                            continue
        
        # 没勾选的基础特殊变量用主界面参数
        param_map = {
            'width': getattr(self.main_window, 'width_spin', None),
            'op_days': getattr(self.main_window, 'op_days_edit', None),
            'increment_rate': getattr(self.main_window, 'inc_rate_edit', None),
            'after_gt_end_ratio': getattr(self.main_window, 'after_gt_end_edit', None),
            'after_gt_start_ratio': getattr(self.main_window, 'after_gt_prev_edit', None),
            'stop_loss_inc_rate': getattr(self.main_window, 'stop_loss_inc_rate_edit', None),
            'stop_loss_after_gt_end_ratio': getattr(self.main_window, 'stop_loss_after_gt_end_edit', None),
            'stop_loss_after_gt_start_ratio': getattr(self.main_window, 'stop_loss_after_gt_start_edit', None)
        }
        
        for en in ['width', 'op_days', 'increment_rate', 'after_gt_end_ratio', 'after_gt_start_ratio', 'stop_loss_inc_rate', 'stop_loss_after_gt_end_ratio', 'stop_loss_after_gt_start_ratio']:
            if en not in special_vars:
                widget = param_map[en]
                if widget is not None:
                    try:
                        # 根据控件类型获取值
                        if hasattr(widget, 'value'):  # QSpinBox类型
                            val = widget.value()
                        elif hasattr(widget, 'text'):  # QLineEdit类型
                            val = widget.text()
                        else:
                            val = 30 if en == 'width' else 5 if en == 'op_days' else 0
                        
                        # 根据变量类型转换
                        if en in ['width', 'op_days']:
                            val = int(float(val))
                        else:
                            val = round(float(val), 2)
                    except (ValueError, AttributeError):
                        # 如果获取失败，使用默认值
                        val = 30 if en == 'width' else 5 if en == 'op_days' else 0
                else:
                    # 如果控件不存在，使用默认值
                    val = 30 if en == 'width' else 5 if en == 'op_days' else 0
                special_vars[en] = {'values': [val]}
        
        # 处理创新高/创新低参数，根据flag的勾选情况确定具体参数
        new_high_low_params = self._get_new_high_low_params_from_flags()
        special_vars.update(new_high_low_params)
        
        # 生成笛卡尔积
        width_values = special_vars['width']['values']
        op_days_values = special_vars['op_days']['values']
        increment_rate_values = special_vars['increment_rate']['values']
        after_gt_end_ratio_values = special_vars['after_gt_end_ratio']['values']
        after_gt_start_ratio_values = special_vars['after_gt_start_ratio']['values']
        stop_loss_inc_rate_values = special_vars['stop_loss_inc_rate']['values']
        stop_loss_after_gt_end_ratio_values = special_vars['stop_loss_after_gt_end_ratio']['values']
        stop_loss_after_gt_start_ratio_values = special_vars['stop_loss_after_gt_start_ratio']['values']
        
        # 创新高/创新低参数
        new_high_low1_start_values = special_vars.get('new_high_low1_start', {'values': [0]})['values']
        new_high_low1_range_values = special_vars.get('new_high_low1_range', {'values': [0]})['values']
        new_high_low1_span_values = special_vars.get('new_high_low1_span', {'values': [0]})['values']
        new_high_low2_start_values = special_vars.get('new_high_low2_start', {'values': [0]})['values']
        new_high_low2_range_values = special_vars.get('new_high_low2_range', {'values': [0]})['values']
        new_high_low2_span_values = special_vars.get('new_high_low2_span', {'values': [0]})['values']
        
        for width in width_values:
            for op_days in op_days_values:
                for increment_rate in increment_rate_values:
                    for after_gt_end_ratio in after_gt_end_ratio_values:
                        for after_gt_start_ratio in after_gt_start_ratio_values:
                            for stop_loss_inc_rate in stop_loss_inc_rate_values:
                                for stop_loss_after_gt_end_ratio in stop_loss_after_gt_end_ratio_values:
                                    for stop_loss_after_gt_start_ratio in stop_loss_after_gt_start_ratio_values:
                                        for new_high_low1_start in new_high_low1_start_values:
                                            for new_high_low1_range in new_high_low1_range_values:
                                                for new_high_low1_span in new_high_low1_span_values:
                                                    for new_high_low2_start in new_high_low2_start_values:
                                                        for new_high_low2_range in new_high_low2_range_values:
                                                            for new_high_low2_span in new_high_low2_span_values:
                                                                special_combinations.append((
                                                                    width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, 
                                                                    stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio,
                                                                    new_high_low1_start, new_high_low1_range, new_high_low1_span,
                                                                    new_high_low2_start, new_high_low2_range, new_high_low2_span
                                                                ))
        
        for i, combination in enumerate(special_combinations):
            print(f"组合 {i+1}: {combination}")
            print()
        
        return special_combinations

    def _get_new_high_low_params_from_flags(self):
        """
        根据创新高/创新低flag的勾选情况，确定具体使用哪个参数
        返回: 字典，键为通用参数名，值为参数值字典
        """
        new_high_low_params = {}
        
        # 定义flag到具体参数的映射
        flag_to_params = {
            'new_before_high_flag': {
                'new_high_low1_start': 'new_before_high_start',
                'new_high_low1_range': 'new_before_high_range', 
                'new_high_low1_span': 'new_before_high_span'
            },
            'new_before_high2_flag': {
                'new_high_low2_start': 'new_before_high2_start',
                'new_high_low2_range': 'new_before_high2_range',
                'new_high_low2_span': 'new_before_high2_span'
            },
            'new_after_high_flag': {
                'new_high_low1_start': 'new_after_high_start',
                'new_high_low1_range': 'new_after_high_range',
                'new_high_low1_span': 'new_after_high_span'
            },
            'new_after_high2_flag': {
                'new_high_low2_start': 'new_after_high2_start',
                'new_high_low2_range': 'new_after_high2_range',
                'new_high_low2_span': 'new_after_high2_span'
            },
            'new_before_low_flag': {
                'new_high_low1_start': 'new_before_low_start',
                'new_high_low1_range': 'new_before_low_range',
                'new_high_low1_span': 'new_before_low_span'
            },
            'new_before_low2_flag': {
                'new_high_low2_start': 'new_before_low2_start',
                'new_high_low2_range': 'new_before_low2_range',
                'new_high_low2_span': 'new_before_low2_span'
            },
            'new_after_low_flag': {
                'new_high_low1_start': 'new_after_low_start',
                'new_high_low1_range': 'new_after_low_range',
                'new_high_low1_span': 'new_after_low_span'
            },
            'new_after_low2_flag': {
                'new_high_low2_start': 'new_after_low2_start',
                'new_high_low2_range': 'new_after_low2_range',
                'new_high_low2_span': 'new_after_low2_span'
            }
        }
        
        # 按组分类检查flag被勾选情况
        group1_flags = ['new_before_high_flag', 'new_after_high_flag', 'new_before_low_flag', 'new_after_low_flag']
        group2_flags = ['new_before_high2_flag', 'new_after_high2_flag', 'new_before_low2_flag', 'new_after_low2_flag']
        
        # 检查第一组flag
        active_group1_flags = []
        for flag_name in group1_flags:
            flag_widget = getattr(self.main_window, flag_name + '_checkbox', None)
            if flag_widget and flag_widget.isChecked():
                active_group1_flags.append(flag_name)
                print(f"检测到勾选的第一组创新高/创新低标志: {flag_name}")
        
        # 检查第二组flag
        active_group2_flags = []
        for flag_name in group2_flags:
            flag_widget = getattr(self.main_window, flag_name + '_checkbox', None)
            if flag_widget and flag_widget.isChecked():
                active_group2_flags.append(flag_name)
                print(f"检测到勾选的第二组创新高/创新低标志: {flag_name}")
        
        # 如果没有勾选任何flag，返回空字典
        if not active_group1_flags and not active_group2_flags:
            print("没有勾选任何创新高/创新低标志")
            return new_high_low_params
        
        # 每组只使用第一个勾选的flag
        final_active_flags = []
        if active_group1_flags:
            final_active_flags.append(active_group1_flags[0])
            print(f"第一组使用第一个勾选的标志: {active_group1_flags[0]}")
        if active_group2_flags:
            final_active_flags.append(active_group2_flags[0])
            print(f"第二组使用第一个勾选的标志: {active_group2_flags[0]}")
        
        # 处理最终选中的flag
        for active_flag in final_active_flags:
            print(f"处理创新高/创新低标志: {active_flag}")
            param_mapping = flag_to_params[active_flag]
            
            # 检查对应的参数是否在特殊变量控件中被勾选
            for generic_param, specific_param in param_mapping.items():
                # 如果参数已经被处理过，跳过（避免覆盖）
                if generic_param in new_high_low_params:
                    print(f"参数 {generic_param} 已被处理，跳过")
                    continue
                    
                if generic_param in self.var_widgets:
                    widgets = self.var_widgets[generic_param]
                    if 'checkbox' in widgets and widgets['checkbox'].isChecked():
                        lower_text = widgets.get('lower', '').text().strip()
                        upper_text = widgets.get('upper', '').text().strip()
                        step_text = widgets.get('step', '').text().strip()
                        if lower_text and upper_text and step_text:
                            try:
                                # 创新高/创新低参数都是整数
                                lower_val = int(float(lower_text))
                                upper_val = int(float(upper_text))
                                step_val = int(float(step_text))
                                values = list(range(lower_val, upper_val + 1, step_val))
                                new_high_low_params[generic_param] = {'values': values}
                                print(f"添加创新高/创新低参数: {generic_param} = {values} (对应具体参数: {specific_param})")
                            except ValueError:
                                continue
                    else:
                        # 如果没有勾选，从主界面获取对应的具体参数值
                        specific_widget = getattr(self.main_window, specific_param + '_spin', None)
                        if specific_widget is not None:
                            try:
                                val = specific_widget.value()
                                new_high_low_params[generic_param] = {'values': [val]}
                                print(f"从主界面获取创新高/创新低参数: {generic_param} = {val} (对应具体参数: {specific_param})")
                            except (ValueError, AttributeError):
                                new_high_low_params[generic_param] = {'values': [0]}
                        else:
                            new_high_low_params[generic_param] = {'values': [0]}
        
        return new_high_low_params
    def _frange(self, start, stop, step):
        """生成浮点数区间"""
        vals = []
        v = start
        # 根据步长正负调整循环条件
        if step > 0:
            while v <= stop:
                vals.append(v)
                v += step
        else:  # step < 0
            while v >= stop:
                vals.append(v)
                v += step
        return vals

    def generate_formula(self):
        # 1. 收集所有条件
        conditions = []
        result_vars = []
        
        # 获取get_abbr_round_only_map中的变量名列表，用于排除
        round_only_vars = set()
        for (zh, en), en_val in self.abbr_round_only_map.items():
            round_only_vars.add(en_val)
        
        # 获取特殊变量列表，用于排除（日期宽度、操作天数、止盈递增率）
        special_abbr_map = get_special_abbr_map()
        special_vars = set(special_abbr_map.values())
        
        for en, widgets in self.var_widgets.items():
            # 排除特殊变量（日期宽度、操作天数、止盈递增率）
            if en in special_vars:
                continue
                
            # 只处理有下限/上限的数值变量
            if 'lower' in widgets and 'upper' in widgets:
                if widgets['checkbox'].isChecked():
                    conds = []
                    lower = widgets['lower'].text().strip()
                    upper = widgets['upper'].text().strip()
                    if lower:
                        conds.append(f"{en} >= {lower}")
                    if upper:
                        conds.append(f"{en} <= {upper}")
                    if conds:
                        # 该变量的条件用and连接
                        conditions.append(' and '.join(conds))
            # 逻辑变量
            elif 'checkbox' in widgets and 'lower' not in widgets:
                if widgets['checkbox'].isChecked():
                    conditions.append(f"{en}")
            # 如果有圆框且被勾选，且不是get_abbr_round_only_map中的变量，加入结果变量
            if 'round_checkbox' in widgets and widgets['round_checkbox'].isChecked() and en not in round_only_vars:
                result_vars.append(en)
                
        # 新增：向前参数勾选项也参与条件拼接
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
                # 排除特殊变量（日期宽度、操作天数、止盈递增率）
                if en in special_vars:
                    continue
                    
                # 方框勾选：参与条件拼接
                if v.get('enable'):
                    conds = []
                    lower = v.get('lower', '').strip()
                    upper = v.get('upper', '').strip()
                    # 变量名与公式变量名需一致，若abbr_map有映射则用英文名
                    var_name = en
                    if hasattr(self, 'abbr_map') and self.abbr_map:
                        zh_name = next((zh for zh, en2 in self.abbr_map.items() if en2 == en), None)
                        if zh_name:
                            var_name = en  # 这里en已是英文名
                    if lower:
                        conds.append(f"{var_name} >= {lower}")
                    if upper:
                        conds.append(f"{var_name} <= {upper}")
                    if conds:
                        conditions.append(' and '.join(conds))
                
                # 圆框勾选：独立于方框勾选，直接加入结果变量
                if v.get('round'):
                    var_name = en
                    if hasattr(self, 'abbr_map') and self.abbr_map:
                        zh_name = next((zh for zh, en2 in self.abbr_map.items() if en2 == en), None)
                        if zh_name:
                            var_name = en  # 这里en已是英文名
                    result_vars.append(var_name)
        # 2. 收集比较控件的条件
        for comp in self.comparison_widgets:
            # 只处理勾选的比较控件
            if comp['checkbox'].isChecked():
                var1 = comp['var1'].currentText()
                lower = comp['lower'].text().strip()
                upper = comp['upper'].text().strip()
                var2 = comp['var2'].currentText()
                var1_en = next((en for zh, en in self.abbr_map.items() if zh == var1), None)
                var2_en = next((en for zh, en in self.abbr_map.items() if zh == var2), None)
                comp_conds = []
                if lower and var1_en and var2_en:
                    comp_conds.append(f"{var1_en} / {var2_en} >= {lower}")
                if upper and var1_en and var2_en:
                    comp_conds.append(f"{var1_en} / {var2_en} <= {upper}")
                if comp_conds:
                    conditions.append(' and '.join(comp_conds))
        # 3. 连接条件，全部用and拼接
        if conditions:
            cond_str = "if " + " and ".join(conditions) + ":"
        else:
            cond_str = "if True:"
        # 4. 收集所有被圆框勾选的变量
        if result_vars:
            result_expr = "result = " + " + ".join(result_vars)
        else:
            result_expr = "result = 0"
        # 5. 生成完整公式
        formula = f"{cond_str}\n    {result_expr}\nelse:\n    result = 0"
        return formula

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)

        self.cols_per_row = 4  # 修正：确保变量控件布局可用

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 创建内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: white;")
        content_widget.setContentsMargins(0, 0, 0, 0)
        grid_layout = QGridLayout(content_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)
        grid_layout.setAlignment(Qt.AlignTop)

        # 创建条件组
        conditions_group = QGroupBox()
        conditions_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

        self.var_widgets = {}

        # 1. 先放逻辑变量控件在第一行
        logic_keys = list(self.abbr_logic_map.items())
        logic_per_row = 4
        logic_rows = (len(logic_keys) + logic_per_row - 1) // logic_per_row
        for idx, (zh, en) in enumerate(logic_keys):
            row = idx // logic_per_row
            col = idx % logic_per_row
            var_widget = QWidget()
            var_widget.setFixedHeight(35)
            var_layout = QHBoxLayout(var_widget)
            var_layout.setContentsMargins(10, 10, 10, 10)
            var_layout.setSpacing(8)
            var_layout.setAlignment(Qt.AlignLeft)
            checkbox = QCheckBox()
            checkbox.setFixedWidth(15)
            var_layout.addWidget(checkbox)
            name_label = QLabel(zh)
            name_label.setFixedWidth(273)
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            var_layout.addWidget(name_label)
            self.var_widgets[en] = {
                'checkbox': checkbox
            }
            grid_layout.addWidget(var_widget, row, col)

        # 2. 数值变量控件从logic_rows行开始，每行5个
        value_keys = list(self.abbr_map.items())
        # 排除向前参数
        window_abbrs = set(get_window_abbr_map().values())
        value_keys = [(zh, en) for zh, en in value_keys if en not in window_abbrs]
        self.value_keys = value_keys  # 记录变量控件顺序
        self.var_count = len(value_keys)
        current_row = logic_rows  # 当前行号
        current_col = 0  # 当前列号
        
        # 先放置普通变量控件
        for idx, (zh, en) in enumerate(value_keys):
            row = current_row
            col = current_col
            var_widget = QWidget()
            var_widget.setFixedHeight(35)
            var_layout = QHBoxLayout(var_widget)
            var_layout.setContentsMargins(10, 10, 10, 10)
            var_layout.setSpacing(8)
            var_layout.setAlignment(Qt.AlignLeft)
            checkbox = QCheckBox()
            checkbox.setFixedWidth(15)
            var_layout.addWidget(checkbox)
            
            # 只为abbr_round_map中的变量添加圆框
            need_round_checkbox = en in self.abbr_round_map.values()
            name_label = QLabel(zh)
            if need_round_checkbox:
                round_checkbox = QCheckBox()
                round_checkbox.setFixedWidth(15)
                round_checkbox.setStyleSheet("""
                    QCheckBox {
                        spacing: 0px;
                        padding: 0px;
                        border: none;
                        background: transparent;
                    }
                    QCheckBox::indicator {
                        width: 10px; height: 10px;
                        border-radius: 5px;
                        border: 1.2px solid #666;
                        background: white;
                        margin: 0px;
                        padding: 0px;
                    }
                    QCheckBox::indicator:checked {
                        background: #409EFF;
                        border: 1.2px solid #409EFF;
                    }
                """)
                var_layout.addWidget(round_checkbox)
                name_label.setFixedWidth(227)
            else:
                name_label.setFixedWidth(250)
            
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft)
            var_layout.addWidget(name_label)

            # 为普通变量控件添加悬浮提示
            add_tooltip_to_variable(name_label, en, self.main_window)

            # 添加下限输入框
            lower_input = QLineEdit()
            lower_input.setPlaceholderText("下限")
            lower_input.setFixedWidth(30)
            var_layout.addWidget(lower_input)

            # 添加上限输入框
            upper_input = QLineEdit()
            upper_input.setPlaceholderText("上限")
            upper_input.setFixedWidth(30)
            var_layout.addWidget(upper_input)

            # 添加步长输入框
            step_input = QLineEdit()
            step_input.setPlaceholderText("步长")
            step_input.setFixedWidth(30)
            # 添加非负数验证器，允许为0
            from PyQt5.QtGui import QDoubleValidator
            validator = QDoubleValidator(0, 999999, 2)  # 最小值0，最大值999999，2位小数
            step_input.setValidator(validator)
            var_layout.addWidget(step_input)

            # 添加方向下拉框
            direction_combo = QComboBox()
            direction_combo.addItems(["右单向", "左单向", "全方向"])
            direction_combo.setFixedWidth(60)
            direction_combo.setFixedHeight(15)
            var_layout.addWidget(direction_combo)

            # 添加含逻辑勾选框和标签
            logic_check = QCheckBox()
            logic_check.setFixedWidth(15)
            logic_label = QLabel("含逻辑")
            logic_label.setStyleSheet("border: none;")
            var_layout.addWidget(logic_check)
            var_layout.addWidget(logic_label)

            widget_dict = {
                'checkbox': checkbox,
                'lower': lower_input,
                'upper': upper_input,
                'step': step_input,
                'direction': direction_combo,
                'logic_check': logic_check
            }
            if need_round_checkbox:
                widget_dict['round_checkbox'] = round_checkbox
            self.var_widgets[en] = widget_dict
            grid_layout.addWidget(var_widget, row, col)
            
            # 更新行列号
            current_col += 1
            if current_col >= self.cols_per_row:
                current_row += 1
                current_col = 0

        # 紧接着放置特殊变量控件
        special_keys = list(self.special_abbr_map.items())
        for idx, (zh, en) in enumerate(special_keys):
            row = current_row
            col = current_col
            var_widget = QWidget()
            var_widget.setFixedHeight(35)
            var_layout = QHBoxLayout(var_widget)
            var_layout.setContentsMargins(10, 10, 10, 10)
            var_layout.setSpacing(8)
            var_layout.setAlignment(Qt.AlignLeft)
            
            # 添加方框勾选框
            checkbox = QCheckBox()
            checkbox.setFixedWidth(15)
            var_layout.addWidget(checkbox)
            
            # 添加label
            name_label = QLabel(zh)
            name_label.setFixedWidth(250)
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft)
            var_layout.addWidget(name_label)

            # 添加下限和上限输入框
            lower_input = QLineEdit()
            lower_input.setPlaceholderText("下限")
            lower_input.setFixedWidth(30)
            # 为日期宽度和操作天数添加整数验证器
            if en in ['width', 'op_days']:
                lower_input.setValidator(QIntValidator(0, 1000))
            var_layout.addWidget(lower_input)

            upper_input = QLineEdit()
            upper_input.setPlaceholderText("上限")
            upper_input.setFixedWidth(30)
            # 为日期宽度和操作天数添加整数验证器
            if en in ['width', 'op_days']:
                upper_input.setValidator(QIntValidator(0, 1000))
            var_layout.addWidget(upper_input)

            # 添加步长输入框
            step_input = QLineEdit()
            step_input.setPlaceholderText("步长")
            step_input.setFixedWidth(30)
            # 为日期宽度和操作天数添加整数验证器，允许为0
            if en in ['width', 'op_days']:
                step_input.setValidator(QIntValidator(1, 1000))
            else:
                # 为其他特殊变量添加非负数验证器
                from PyQt5.QtGui import QDoubleValidator
                validator = QDoubleValidator(0, 999999, 2)  # 最小值0，最大值999999，2位小数
                step_input.setValidator(validator)
            var_layout.addWidget(step_input)

            widget_dict = {
                'checkbox': checkbox,
                'lower': lower_input,
                'upper': upper_input,
                'step': step_input
            }

            self.var_widgets[en] = widget_dict
            grid_layout.addWidget(var_widget, row, col)
            
            # 更新行列号
            current_col += 1
            if current_col >= self.cols_per_row:
                current_row += 1
                current_col = 0

        # 3. 添加只有圆框的变量控件
        round_only_keys = list(self.abbr_round_only_map.items())
        for idx, ((zh, en), en_val) in enumerate(round_only_keys):
            row = current_row
            col = current_col
            var_widget = QWidget()
            var_widget.setFixedHeight(35)
            var_layout = QHBoxLayout(var_widget)
            var_layout.setContentsMargins(10, 10, 10, 10)
            var_layout.setSpacing(2)  # 更紧凑
            var_layout.setAlignment(Qt.AlignLeft)
            
            # 添加圆框勾选框
            round_checkbox = QCheckBox()
            round_checkbox.setFixedWidth(15)
            round_checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 0px;
                    padding: 0px;
                    border: none;
                    background: transparent;
                }
                QCheckBox::indicator {
                    width: 10px; height: 10px;
                    border-radius: 5px;
                    border: 1.2px solid #666;
                    background: white;
                    margin: 0px;
                    padding: 0px;
                }
                QCheckBox::indicator:checked {
                    background: #409EFF;
                    border: 1.2px solid #409EFF;
                }
            """)
            var_layout.addWidget(round_checkbox)
            
            # 添加label
            if en_val in self.component_analysis_variables:
                name_label = QLabel(zh)
                name_label.setFixedWidth(170)  # 更紧凑
            else:
                name_label = QLabel(zh)
                name_label.setFixedWidth(250)  # 保持原宽度
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft)
            var_layout.addWidget(name_label)

            # 为特定的变量添加N值输入框
            if en_val in self.component_analysis_variables:
                n_input = QLineEdit()
                n_input.setPlaceholderText("N")
                n_input.setFixedWidth(30)
                n_input.textChanged.connect(self._sync_to_main)  # 自动保存
                var_layout.addWidget(n_input)
                widget_dict = {
                    'round_checkbox': round_checkbox,
                    'n_input': n_input
                }
            else:
                widget_dict = {
                    'round_checkbox': round_checkbox
                }

            self.var_widgets[en_val] = widget_dict
            grid_layout.addWidget(var_widget, row, col)
            
            # 更新行列号
            current_col += 1
            if current_col >= self.cols_per_row:
                current_row += 1
                current_col = 0

        # 4. 比较控件和添加比较按钮放在最后
        self.comparison_widgets = []
        self.add_comparison_btn = QPushButton("添加比较")
        self.add_comparison_btn.setFixedSize(100, 30)
        self.add_comparison_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2D6DA3;
                padding-top: 2px;
                padding-left: 2px;
            }
        """)
        self.add_comparison_btn.clicked.connect(self.add_comparison_widget)
        self._refresh_comparison_row(grid_layout, logic_rows)
        conditions_group.setLayout(grid_layout)
        layout.addWidget(conditions_group)
        self.setLayout(layout)
        # 在末尾添加
        self._setup_state_sync()

    def _refresh_comparison_row(self, grid_layout=None, logic_rows=0):
        # 变量控件最后一行的行号
        last_var_row = (len(self.value_keys) - 1) // self.cols_per_row + logic_rows
        last_var_col = (len(self.value_keys) - 1) % self.cols_per_row
        # 计算 round_only 控件的行数
        round_only_count = len(self.abbr_round_only_map)
        round_only_rows = (round_only_count + self.cols_per_row - 1) // self.cols_per_row
        # 计算特殊变量控件的行数
        special_count = len(self.special_abbr_map)
        special_rows = (special_count + self.cols_per_row - 1) // self.cols_per_row
        # 新的比较区起始行：变量控件最后一行 + round_only 控件行数 + 特殊变量行数 + 2
        comparison_start_row = last_var_row + round_only_rows + special_rows + 3
        for comp in getattr(self, 'comparison_widgets', []):
            if hasattr(comp, 'widget'):
                comp['widget'].setParent(None)
        if hasattr(self, 'add_comparison_btn'):
            self.add_comparison_btn.setParent(None)
        # 判断变量控件最后一行是否有内容
        row = comparison_start_row
        col = 0
        for i, comp in enumerate(self.comparison_widgets):
            grid_layout.addWidget(comp['widget'], row, col)
            col += 1
            if col >= 4:  # 每行最多4个比较控件
                row += 1
                col = 0
        # 添加比较按钮单独占一行
        row += 1
        grid_layout.addWidget(self.add_comparison_btn, row, 0, 1, 2)

    def _setup_state_sync(self):
        """设置所有控件的状态同步"""
        # 变量控件状态同步
        for en, widgets in self.var_widgets.items():
            if 'checkbox' in widgets:
                widgets['checkbox'].stateChanged.connect(self._sync_to_main)
            if 'round_checkbox' in widgets:
                widgets['round_checkbox'].stateChanged.connect(self._sync_to_main)
            if 'lower' in widgets:
                widgets['lower'].textChanged.connect(self._sync_to_main)
            if 'upper' in widgets:
                widgets['upper'].textChanged.connect(self._sync_to_main)
            if 'step' in widgets:
                widgets['step'].textChanged.connect(self._sync_to_main)
            if 'direction' in widgets:
                widgets['direction'].currentTextChanged.connect(self._sync_to_main)
            if 'logic_check' in widgets:
                widgets['logic_check'].stateChanged.connect(self._sync_to_main)
            if 'n_input' in widgets:
                widgets['n_input'].textChanged.connect(self._sync_to_main)
        # lock_output_checkbox状态同步
        if hasattr(self, 'lock_output_checkbox'):
            self.lock_output_checkbox.stateChanged.connect(self._sync_to_main)

    def get_round_only_map_selected_vars(self):
        """
        获取get_abbr_round_only_map中勾选的变量列表
        """
        selected_vars = []
        
        for (zh, en), en_val in self.abbr_round_only_map.items():
            if en_val in self.var_widgets:
                widgets = self.var_widgets[en_val]
                if 'round_checkbox' in widgets and widgets['round_checkbox'].isChecked():
                    selected_vars.append(en_val)
        
        return selected_vars



def get_abbr_map():
    """获取变量缩写映射字典"""
    abbrs = [
        ("前1组结束日地址值", "end_value"), 
        ("前1组结束地址前N日的最高值", "n_days_max_value"), 
        ("前1组结束地址前1日涨跌幅", "prev_day_change"), ("前1组结束日涨跌幅", "end_day_change"), ("后一组结束地址值", "diff_end_value"),
        ("连续累加值数组非空数据长度", "continuous_len"), ("连续累加值正加值和", "cont_sum_pos_sum"), ("连续累加值负加值和", "cont_sum_neg_sum"), 
        ("连续累加值正加值的前一半累加值和", "cont_sum_pos_sum_first_half"), ("连续累加值正加值的后一半累加值和", "cont_sum_pos_sum_second_half"),
        ("连续累加值负加值的前一半累加值和", "cont_sum_neg_sum_first_half"), ("连续累加值负加值的后一半累加值和", "cont_sum_neg_sum_second_half"),
        ("连续累加值开始值", "continuous_start_value"), ("连续累加值开始后1位值", "continuous_start_next_value"),
        ("连续累加值开始后2位值", "continuous_start_next_next_value"), ("连续累加值结束值", "continuous_end_value"), ("连续累加值结束前1位值", "continuous_end_prev_value"), ("连续累加值结束前2位值", "continuous_end_prev_prev_value"),
        ("连续累加值数组前一半绝对值之和", "continuous_abs_sum_first_half"), ("连续累加值数组后一半绝对值之和", "continuous_abs_sum_second_half"),
        ("连续累加值数组前四分之一绝对值之和", "continuous_abs_sum_block1"), ("连续累加值数组前四分之1-2绝对值之和", "continuous_abs_sum_block2"),
        ("连续累加值数组前四分之2-3绝对值之和", "continuous_abs_sum_block3"), ("连续累加值数组后四分之一绝对值之和", "continuous_abs_sum_block4"),
        ("有效累加值正加值和", "valid_pos_sum"), ("有效累加值负加值和", "valid_neg_sum"), ("有效累加值数组非空数据长度", "valid_sum_len"),
        ("有效累加值数组前一半绝对值之和", "valid_abs_sum_first_half"), ("有效累加值数组后一半绝对值之和", "valid_abs_sum_second_half"),
        ("有效累加值数组前四分之1绝对值之和", "valid_abs_sum_block1"), ("有效累加值数组前四分之1-2绝对值之和", "valid_abs_sum_block2"),
        ("有效累加值数组前四分之2-3绝对值之和", "valid_abs_sum_block3"), ("有效累加值数组后四分之1绝对值之和", "valid_abs_sum_block4"),
    ]
    abbrs += list(get_window_abbr_map().items())
    return {zh: en for zh, en in abbrs}

def get_window_abbr_map():
    """获取窗口变量缩写映射字典"""
    abbrs = [
        ("向前最大连续累加值数组非空数据长度", "forward_max_result_len"),
        ("向前最大连续累加值开始值", "forward_max_continuous_start_value"), ("向前最大连续累加值开始后1位值", "forward_max_continuous_start_next_value"), 
        ("向前最大连续累加值开始后2位值", "forward_max_continuous_start_next_next_value"), ("向前最大连续累加值结束值", "forward_max_continuous_end_value"), 
        ("向前最大连续累加值结束前1位值", "forward_max_continuous_end_prev_value"), ("向前最大连续累加值结束前2位值", "forward_max_continuous_end_prev_prev_value"),
        ("向前最大连续累加值前一半绝对值之和", "forward_max_abs_sum_first_half"), ("向前最大连续累加值后一半绝对值之和", "forward_max_abs_sum_second_half"),
        ("向前最大连续累加值前四分之1绝对值之和", "forward_max_abs_sum_block1"), ("向前最大连续累加值前四分之1-2绝对值之和", "forward_max_abs_sum_block2"),
        ("向前最大连续累加值前四分之2-3绝对值之和", "forward_max_abs_sum_block3"), ("向前最大连续累加值后四分之1绝对值之和", "forward_max_abs_sum_block4"),
        ("向前最大连续累加值正加值和", "forward_max_cont_sum_pos_sum"), ("向前最大连续累加值负加值和", "forward_max_cont_sum_neg_sum"),
        
        ("向前最大有效累加值数组非空数据长度", "forward_max_valid_sum_len"), 
        ("向前最大有效累加值数组前一半绝对值之和", "forward_max_valid_abs_sum_first_half"), ("向前最大有效累加值数组后一半绝对值之和", "forward_max_valid_abs_sum_second_half"),
        ("向前最大有效累加值数组前四分之1绝对值之和", "forward_max_valid_abs_sum_block1"), ("向前最大有效累加值数组前四分之1-2绝对值之和", "forward_max_valid_abs_sum_block2"),
        ("向前最大有效累加值数组前四分之2-3绝对值之和", "forward_max_valid_abs_sum_block3"), ("向前最大有效累加值数组后四分之1绝对值之和", "forward_max_valid_abs_sum_block4"),
        ("向前最大有效累加值正加值和", "forward_max_valid_pos_sum"), ("向前最大有效累加值负加值和", "forward_max_valid_neg_sum"),
        
        ("向前最小连续累加值数组非空数据长度", "forward_min_result_len"),
        ("向前最小连续累加值开始值", "forward_min_continuous_start_value"), ("向前最小连续累加值开始后1位值", "forward_min_continuous_start_next_value"), 
        ("向前最小连续累加值开始后2位值", "forward_min_continuous_start_next_next_value"),("向前最小连续累加值结束值", "forward_min_continuous_end_value"), 
        ("向前最小连续累加值结束前1位值", "forward_min_continuous_end_prev_value"), ("向前最小连续累加值结束前2位值", "forward_min_continuous_end_prev_prev_value"),
        ("向前最小连续累加值前一半绝对值之和", "forward_min_abs_sum_first_half"), ("向前最小连续累加值后一半绝对值之和", "forward_min_abs_sum_second_half"),
        ("向前最小连续累加值前四分之1绝对值之和", "forward_min_abs_sum_block1"), ("向前最小连续累加值前四分之1-2绝对值之和", "forward_min_abs_sum_block2"),
        ("向前最小连续累加值前四分之2-3绝对值之和", "forward_min_abs_sum_block3"), ("向前最小连续累加值后四分之1绝对值之和", "forward_min_abs_sum_block4"),
        ("向前最小连续累加值正加值和", "forward_min_cont_sum_pos_sum"), ("向前最小连续累加值负加值和", "forward_min_cont_sum_neg_sum"),
        

        ("向前最小有效累加值数组非空数据长度", "forward_min_valid_sum_len"), 
        ("向前最小有效累加值数组前一半绝对值之和", "forward_min_valid_abs_sum_first_half"), ("向前最小有效累加值数组后一半绝对值之和", "forward_min_valid_abs_sum_second_half"),
        ("向前最小有效累加值数组前四分之1绝对值之和", "forward_min_valid_abs_sum_block1"), ("向前最小有效累加值数组前四分之1-2绝对值之和", "forward_min_valid_abs_sum_block2"),
        ("向前最小有效累加值数组前四分之2-3绝对值之和", "forward_min_valid_abs_sum_block3"), ("向前最小有效累加值数组后四分之1绝对值之和", "forward_min_valid_abs_sum_block4"),
        ("向前最小有效累加值正加值和", "forward_min_valid_pos_sum"), ("向前最小有效累加值负加值和", "forward_min_valid_neg_sum"),
        
    ]
    return {zh: en for zh, en in abbrs}

def get_abbr_logic_map():
    """获取变量缩写映射字典"""
    abbrs = [
        ("第1组后N最大值逻辑", "n_max_is_max"),
        ("开始日到结束日之间最高价/最低价小于M", "range_ratio_is_less"), 
        ("开始日到结束日之间连续累加值绝对值小于M", "continuous_abs_is_less"),
        ("开始日到结束日之间有效累加值绝对值小于M", "valid_abs_is_less"),
        ("开始日到结束日之间向前最小连续累加值绝对值小于M", "forward_min_continuous_abs_is_less"),
        ("开始日到结束日之间向前最小有效累加值绝对值小于M", "forward_min_valid_abs_is_less"),
        ("开始日到结束日之间向前最大连续累加值绝对值小于M", "forward_max_continuous_abs_is_less"),
        ("开始日到结束日之间向前最大有效累加值绝对值小于M", "forward_max_valid_abs_is_less"),
    ]
    return {zh: en for zh, en in abbrs}
def get_abbr_round_map():
    """只需要圆框勾选的变量映射"""
    abbrs = [
        ("有效累加值正加值和", "valid_pos_sum"),
        ("有效累加值负加值和", "valid_neg_sum"),
        ("连续累加值正加值和", "cont_sum_pos_sum"),
        ("连续累加值负加值和", "cont_sum_neg_sum"),
        ("向前最大连续累加值正加值和", "forward_max_cont_sum_pos_sum"),
        ("向前最大连续累加值负加值和", "forward_max_cont_sum_neg_sum"),
        ("向前最小连续累加值正加值和", "forward_min_cont_sum_pos_sum"),
        ("向前最小连续累加值负加值和", "forward_min_cont_sum_neg_sum"),
        ("向前最大有效累加值正加值和", "forward_max_valid_pos_sum"),
        ("向前最大有效累加值负加值和", "forward_max_valid_neg_sum"),
        ("向前最小有效累加值正加值和", "forward_min_valid_pos_sum"),
        ("向前最小有效累加值负加值和", "forward_min_valid_neg_sum"),
    ]
    return {zh: en for zh, en in abbrs}

def parse_formula_to_config(formula, abbr_map=None):
    """
    解析公式字符串，反推为控件配置字典。
    支持xxx >= a、xxx <= b、result = xxx + yyy、逻辑变量等。
    abbr_map: 可选，变量中文到英文映射（用于比较控件）
    """
    config = {}
    # 1. 匹配 xxx >= a
    for m in re.finditer(r'([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)', formula):
        var, lower = m.group(1), m.group(2)
        config.setdefault(var, {})['lower'] = lower
        config[var]['checked'] = True
    # 2. 匹配 xxx <= b
    for m in re.finditer(r'([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)', formula):
        var, upper = m.group(1), m.group(2)
        config.setdefault(var, {})['upper'] = upper
        config[var]['checked'] = True
    # 3. 匹配逻辑变量（if ... and VAR ...）
    # 先找出所有在if条件中的变量
    if_match = re.search(r'if\s*(.*?):', formula)
    if if_match:
        condition_text = if_match.group(1)
        logic_vars = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', condition_text)
        for var in logic_vars:
            # 排除常见关键字和已处理变量
            if var not in config and var not in {'if', 'else', 'result', 'and', 'or', 'not'}:
                config.setdefault(var, {})['checked'] = True
    # 4. 匹配 result = xxx + yyy
    m = re.search(r'result\s*=\s*([a-zA-Z0-9_]+(?:\s*\+\s*[a-zA-Z0-9_]+)*)', formula)
    if m:
        for var in re.findall(r'[a-zA-Z0-9_]+', m.group(1)):
            # 只勾选圆框，不勾选方框
            config.setdefault(var, {})['round_checked'] = True
    # 5. 匹配比较控件（如A >= 2 * B）
    for m in re.finditer(r'([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
        var1, lower, var2 = m.group(1), m.group(2), m.group(3)
        comp = {'var1': var1, 'lower': lower, 'upper': '', 'var2': var2}
        config.setdefault('comparison_widgets', []).append(comp)
    for m in re.finditer(r'([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
        var1, upper, var2 = m.group(1), m.group(2), m.group(3)
        comp = {'var1': var1, 'lower': '', 'upper': upper, 'var2': var2}
        config.setdefault('comparison_widgets', []).append(comp)
    return config

def calculate_analysis_result(valid_items):
    """
    计算分析结果，包含每个日期的详细数据和总体统计
    
    Args:
        valid_items: 包含股票数据的列表，每个元素是一个元组 (date_key, stocks)
        
    Returns:
        dict: 包含分析结果的字典，结构如下：
        {
            item： 是每天的选股结果，当天股票的均值
            'items': [
                {
                    'date': '日期',
                    'hold_days': '操作天数',
                    'ops_change': '持有涨跌幅',
                    'daily_change': '日均涨跌幅',
                    'non_nan_mean': '从下往上非空均值',
                    'with_nan_mean': '从下往上含空均值',
                    'adjust_non_nan_mean': '调幅从下往上非空均值',
                    'adjust_with_nan_mean': '调幅从下往上含空均值'
                },
                ...
            ],
            summary： 是统计每天选股结果均值的均值
            'summary': {
                'mean_hold_days': '持有天数均值',
                'mean_ops_change': '持有涨跌幅均值',
                'mean_daily_change': '日均涨跌幅均值',
                'mean_adjust_ops_incre_rate': '调天日均涨跌幅均值',
                'mean_non_nan': '调天从下往上非空均值均值',
                'mean_with_nan': '调天从下往上含空均值均值',
                'mean_daily_with_nan': '调天含空值均值',
                'max_change': '调天最大值',
                'min_change': '调天最小值',
                'mean_adjust_ops_incre_rate': '调幅日均涨跌幅均值',
                'mean_non_nan_adjust_ops_incre_rate': '调幅从下往上非空均值均值',
                'mean_with_nan_adjust_ops_incre_rate': '调幅从下往上含空均值均值',
                'mean_adjust_daily_with_nan': '调幅含空值均值',
                'max_adjust_ops_incre_rate': '调幅最大值',
                'min_adjust_ops_incre_rate': '调幅最小值',
                # 新增：根据N位控件值动态计算的变量
                'bottom_nth_non_nan1': '从下往上第N1位调天非空均值',
                'bottom_nth_non_nan2': '从下往上第N2位调天非空均值',
                'bottom_nth_non_nan3': '从下往上第N3位调天非空均值',
                'bottom_nth_with_nan1': '从下往上第N1位调天含空均值',
                'bottom_nth_with_nan2': '从下往上第N2位调天含空均值',
                'bottom_nth_with_nan3': '从下往上第N3位调天含空均值',
                'bottom_nth_adjust_non_nan1': '从下往上第N1位调幅非空均值',
                'bottom_nth_adjust_non_nan2': '从下往上第N2位调幅非空均值',
                'bottom_nth_adjust_non_nan3': '从下往上第N3位调幅非空均值',
                'bottom_nth_adjust_with_nan1': '从下往上第N1位调幅含空均值',
                'bottom_nth_adjust_with_nan2': '从下往上第N2位调幅含空均值',
                'bottom_nth_adjust_with_nan3': '从下往上第N3位调幅含空均值',
                # 新增：止盈率、止损率、持有率统计
                'total_stocks': '总股票数量',
                'hold_rate': '持有率（百分比）',
                'profit_rate': '止盈率（百分比）',
                'loss_rate': '止损率（百分比）',
                'hold_count': '持有股票数量',
                'profit_count': '止盈股票数量',
                'loss_count': '止损股票数量',
                # 新增：止盈、止损、持有中值
                'hold_median': '持有涨跌幅中位数',
                'profit_median': '止盈涨跌幅中位数',
                'loss_median': '止损涨跌幅中位数'
            }
        }
    """
    def safe_val(val):
        if val is None:
            return ''
        if isinstance(val, float) and math.isnan(val):
            return ''
        if isinstance(val, str) and val.strip().lower().startswith('nan'):
            return ''
        return val

    def safe_mean(lst, treat_nan_as_zero=False):
        if treat_nan_as_zero:
            # 将nan值视为0，计算所有值的平均
            vals = [0 if (isinstance(v, float) and math.isnan(v)) else v for v in lst]
            if not vals:
                return ''
            val = sum(vals) / len(vals)
        else:
            # 只计算非nan值的平均
            vals = [v for v in lst if not (isinstance(v, float) and math.isnan(v))]
            if not vals:
                return ''
            val = sum(vals) / len(vals)
        return float(Decimal(str(val)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    # 获取N位控件值 - 从主窗口状态中读取
    n_values = {}
    try:
        # 使用QApplication查找主窗口实例
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        main_window = None
        
        if app:
            # 遍历所有顶级窗口
            for widget in app.topLevelWidgets():
                try:
                    if hasattr(widget, 'component_analysis_n_values'):
                        main_window = widget
                        break
                except:
                    continue
        
        # 如果还是没找到，尝试从全局变量中查找
        if not main_window:
            import sys
            for module_name, module in sys.modules.items():
                if module and hasattr(module, '__dict__'):
                    for name, obj in module.__dict__.items():
                        try:
                            if hasattr(obj, 'component_analysis_n_values'):
                                main_window = obj
                                break
                        except:
                            continue
                if main_window:
                    break
        
        # 从主窗口读取N位控件值
        if main_window and hasattr(main_window, 'component_analysis_n_values'):
            n_values = main_window.component_analysis_n_values
        else:
            # 备用方案：从last_formula_select_state中读取
            if main_window and hasattr(main_window, 'last_formula_select_state'):
                last_state = main_window.last_formula_select_state
                if last_state and 'n_values' in last_state:
                    n_values = last_state['n_values']
                    print(f"从last_formula_select_state读取到N位控件值: {n_values}")
                else:
                    # 使用默认值
                    n_vars = ['bottom_nth_take_and_stop_with_nan1', 'bottom_nth_take_and_stop_with_nan2', 'bottom_nth_take_and_stop_with_nan3',
                        'bottom_nth_with_nan1', 'bottom_nth_with_nan2', 'bottom_nth_with_nan3',
                        'bottom_nth_stop_and_take_with_nan1', 'bottom_nth_stop_and_take_with_nan2', 'bottom_nth_stop_and_take_with_nan3',
                        'bottom_nth_adjust_with_nan1', 'bottom_nth_adjust_with_nan2', 'bottom_nth_adjust_with_nan3']
                    n_values = {var: 1 for var in n_vars}
                    print(f"使用默认N位控件值: {n_values}")
            else:
                # 使用默认值bottom_nth_non_nan1
                n_vars = ['bottom_nth_take_and_stop_with_nan1', 'bottom_nth_take_and_stop_with_nan2', 'bottom_nth_take_and_stop_with_nan3',
                    'bottom_nth_with_nan1', 'bottom_nth_with_nan2', 'bottom_nth_with_nan3',
                    'bottom_nth_stop_and_take_with_nan1', 'bottom_nth_stop_and_take_with_nan2', 'bottom_nth_stop_and_take_with_nan3',
                    'bottom_nth_adjust_with_nan1', 'bottom_nth_adjust_with_nan2', 'bottom_nth_adjust_with_nan3']
                n_values = {var: 1 for var in n_vars}
                print(f"使用默认N位控件值: {n_values}")
                
    except Exception as e:
        print(f"获取N位控件值时出错: {e}")
        # 使用默认值
        n_vars = ['bottom_nth_take_and_stop_with_nan1', 'bottom_nth_take_and_stop_with_nan2', 'bottom_nth_take_and_stop_with_nan3',
                 'bottom_nth_with_nan1', 'bottom_nth_with_nan2', 'bottom_nth_with_nan3',
                 'bottom_nth_stop_and_take_with_nan1', 'bottom_nth_stop_and_take_with_nan2', 'bottom_nth_stop_and_take_with_nan3',
                 'bottom_nth_adjust_with_nan1', 'bottom_nth_adjust_with_nan2', 'bottom_nth_adjust_with_nan3']
        n_values = {var: 1 for var in n_vars}
        print(f"出错后使用默认N位控件值: {n_values}")

    # 存储每个日期的详细数据
    items = []
    # 存储用于计算总体统计的数据
    hold_days_list = []
    ops_change_list = []
    daily_change_list = []
    daily_change_list_with_nan = []  # 新增：存储含空值的日均涨跌幅列表
    non_nan_mean_list = []
    with_nan_mean_list = []
    
    # 新增：调幅相关列表
    adjust_ops_incre_rate_list = []
    adjust_ops_incre_rate_list_with_nan = []  # 存储含空值的调幅日均涨跌幅列表
    take_and_stop_daily_with_nan_list = []
    stop_and_take_daily_with_nan_list = []
    adjust_non_nan_mean_list = []
    adjust_with_nan_mean_list = []
    # 新增：止盈停损相关列表
    take_and_stop_non_nan_mean_list = []
    take_and_stop_with_nan_mean_list = []
    stop_and_take_non_nan_mean_list = []
    stop_and_take_with_nan_mean_list = []

    take_and_stop_change_list = []
    stop_and_take_change_list = []
    # 新增：调整天数和止盈止损涨幅相关列表
    adjust_days_list = []
    adjust_ops_change_list = []
    take_and_stop_daily_change_list = []
    stop_and_take_daily_change_list = []
    adjust_daily_change_list = []
    adjust_daily_change_list_with_nan = []
    # 新增：统计止盈率、止损率、持有率
    total_stocks = 0
    hold_count = 0  # end_state = 0
    profit_count = 0  # end_state = 1
    loss_count = 0  # end_state = 2
    
    # 新增：收集止盈、止损、持有涨跌幅数组
    hold_changes = []  # end_state = 0 的 end_day_change
    profit_changes = []  # end_state = 1 的 take_profit
    loss_changes = []  # end_state = 2 的 stop_loss
    
    # 计算每个日期的数据
    for date_key, stocks in valid_items:
        hold_days_list_per_date = []
        ops_change_list_per_date = []
        ops_incre_rate_list_per_date = []
        adjust_ops_incre_rate_list_per_date = []
        adjust_days_list_per_date = []
        adjust_ops_change_list_per_date = []
        take_and_stop_change_list_per_date = []
        stop_and_take_change_list_per_date = []
        
        # 新增：收集股票索引用于调试
        stock_indices_per_date = []
        
        for stock in stocks:
            # 新增：统计end_state并收集涨跌幅数据
            try:
                end_state_raw = stock.get('end_state', '')
                end_state = safe_val(end_state_raw)
                
                if end_state != '' and end_state is not None:
                    end_state = int(float(end_state))
                    total_stocks += 1
                    
                    # 根据end_state收集相应的涨跌幅数据
                    if end_state == 0:
                        hold_count += 1
                        # 收集持有涨跌幅：只使用op_day_change
                        ops_change_raw = stock.get('ops_change', '')
                        ops_change = safe_val(ops_change_raw)
                        
                        if ops_change != '' and ops_change is not None:
                            try:
                                ops_change = float(ops_change)
                                if not math.isnan(ops_change):
                                    hold_changes.append(ops_change)
                                    print(f"stock_name = {stock.get('stock_name', '')}, 持有涨跌幅 = {ops_change}")
                            except (ValueError, TypeError):
                                pass
                    elif end_state == 1:
                        profit_count += 1
                        # 收集止盈涨跌幅
                        take_profit_raw = stock.get('take_profit', '')
                        take_profit = safe_val(take_profit_raw)
                        if take_profit != '' and take_profit is not None:
                            try:
                                take_profit = float(take_profit)
                                if not math.isnan(take_profit):
                                    profit_changes.append(take_profit)
                                    print(f"stock_name = {stock.get('stock_name', '')}, 止盈涨跌幅 = {take_profit}")
                            except (ValueError, TypeError):
                                pass
                    elif end_state == 2:
                        loss_count += 1
                        # 收集止损涨跌幅
                        stop_loss_raw = stock.get('stop_loss', '')
                        stop_loss = safe_val(stop_loss_raw)
                        if stop_loss != '' and stop_loss is not None:
                            try:
                                stop_loss = float(stop_loss)
                                if not math.isnan(stop_loss):
                                    loss_changes.append(stop_loss)
                                    print(f"stock_name = {stock.get('stock_name', '')}, 止损涨跌幅 = {stop_loss}")
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                print(f"Debug - 统计end_state时出错: {e}, end_state_raw: {end_state_raw}")
                pass
                
            try:
                v = safe_val(stock.get('hold_days', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        hold_days_list_per_date.append(v)
            except Exception:
                pass
            try:
                v = safe_val(stock.get('ops_change', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        ops_change_list_per_date.append(v)
                        # 收集对应的股票索引
                        stock_idx = stock.get('stock_idx', '未知')
                        stock_indices_per_date.append(stock_idx)
            except Exception:
                pass
            try:
                v = safe_val(stock.get('ops_incre_rate', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        ops_incre_rate_list_per_date.append(v)
            except Exception:
                pass
            # 新增：收集调幅日均涨跌幅
            try:
                v = safe_val(stock.get('adjust_ops_incre_rate', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        adjust_ops_incre_rate_list_per_date.append(v)
            except Exception:
                pass
            # 新增：收集调整天数
            try:
                v = safe_val(stock.get('adjust_days', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        adjust_days_list_per_date.append(v)
            except Exception:
                pass
            # 新增：收集止盈止损涨幅
            try:
                v = safe_val(stock.get('adjust_ops_change', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        adjust_ops_change_list_per_date.append(v)
            except Exception:
                pass
            # 新增：收集止盈停损涨幅
            try:
                v = safe_val(stock.get('take_and_stop_change', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        take_and_stop_change_list_per_date.append(v)
            except Exception:
                pass
            # 新增：收集停盈止损涨幅
            try:
                v = safe_val(stock.get('stop_and_take_change', ''))
                if v != '':
                    v = float(v)
                    if not math.isnan(v):
                        stop_and_take_change_list_per_date.append(v)
            except Exception:
                pass
        mean_hold_days = safe_mean(hold_days_list_per_date)
        mean_adjust_days = safe_mean(adjust_days_list_per_date)
        mean_adjust_ops_change = safe_mean(adjust_ops_change_list_per_date)
        mean_take_and_stop_change = safe_mean(take_and_stop_change_list_per_date)
        mean_stop_and_take_change = safe_mean(stop_and_take_change_list_per_date)
        mean_ops_change = safe_mean(ops_change_list_per_date)
        mean_ops_incre_rate = safe_mean(ops_incre_rate_list_per_date)
        
        mean_adjust_ops_incre_rate = safe_mean(adjust_ops_incre_rate_list_per_date)
        # 停盈停损日均涨跌幅
        #daily_change = mean_ops_incre_rate
        daily_change = round(mean_ops_change / mean_adjust_days, 2) if mean_ops_change != '' and mean_adjust_days != '' and mean_adjust_days != 0 else ''
        #print(f"mean_ops_change={mean_ops_change}, mean_adjust_days={mean_adjust_days}, daily_change={daily_change}")
        # 止盈止损日均涨跌幅
        adjust_daily_change = round(mean_adjust_ops_change / mean_hold_days, 2) if mean_adjust_ops_change != '' and mean_hold_days != '' and mean_hold_days != 0 else ''

        # 新增：处理止盈停损日均涨幅, 停盈止损日均涨幅
        take_and_stop_daily_change = round(mean_take_and_stop_change / mean_hold_days, 2) if mean_take_and_stop_change != '' and mean_hold_days != '' and mean_hold_days != 0 else ''
        stop_and_take_daily_change = round(mean_stop_and_take_change / mean_hold_days, 2) if mean_stop_and_take_change != '' and mean_hold_days != '' and mean_hold_days != 0 else ''
        
        if mean_hold_days != '':
            hold_days_list.append(mean_hold_days)
        if mean_ops_change != '':
            ops_change_list.append(mean_ops_change)
        if daily_change != '':
            daily_change_list.append(daily_change)
            daily_change_list_with_nan.append(daily_change)  # 添加到含空值列表
        else:
            daily_change_list_with_nan.append(0)  # 空值当作0处理
        
        if adjust_daily_change != '':
            adjust_daily_change_list.append(adjust_daily_change)
            adjust_daily_change_list_with_nan.append(adjust_daily_change)  # 添加到含空值列表
        else:
            adjust_daily_change_list_with_nan.append(0)  # 空值当作0处理

        if take_and_stop_daily_change != '':
            take_and_stop_daily_change_list.append(take_and_stop_daily_change)
        if stop_and_take_daily_change != '':
            stop_and_take_daily_change_list.append(stop_and_take_daily_change)

        # 新增：处理调幅日均涨跌幅
        if adjust_daily_change != '':
            adjust_ops_incre_rate_list.append(adjust_daily_change)
            adjust_ops_incre_rate_list_with_nan.append(adjust_daily_change)  # 添加到含空值列表
        else:
            adjust_ops_incre_rate_list_with_nan.append(0)  # 空值当作0处理

        # 新增：处理调整天数和止盈止损涨幅
        if mean_adjust_days != '':
            adjust_days_list.append(mean_adjust_days)
        if mean_adjust_ops_change != '':
            adjust_ops_change_list.append(mean_adjust_ops_change)
        # 新增：处理止盈停损涨幅, 停盈止损涨幅
        if mean_take_and_stop_change != '':
            take_and_stop_change_list.append(mean_take_and_stop_change)
        if mean_stop_and_take_change != '':
            stop_and_take_change_list.append(mean_stop_and_take_change)

        # 新增：处理止盈停损日均涨跌幅, 停盈止损日均涨跌幅
        if take_and_stop_daily_change != '':
            take_and_stop_daily_with_nan_list.append(take_and_stop_daily_change)
        if stop_and_take_daily_change != '':
            stop_and_take_daily_with_nan_list.append(stop_and_take_daily_change)

        # 添加到items列表
        items.append({
            'date': date_key,
            'hold_days': mean_hold_days,
            'ops_change': mean_ops_change,
            'daily_change': daily_change,
            'adjust_daily_change': adjust_daily_change,  # 新增：调幅日均涨跌幅
            'adjust_days': mean_adjust_days,  # 新增：调整天数
            'adjust_ops_change': mean_adjust_ops_change,  # 新增：止盈止损涨幅
            'non_nan_mean': '',  # 将在后面计算
            'with_nan_mean': '',  # 将在后面计算
            'adjust_non_nan_mean': '',  # 新增：调幅从下往上非空均值
            'adjust_with_nan_mean': '',  # 新增：调幅从下往上含空均值
            'take_and_stop_change': mean_take_and_stop_change, # 止盈停损涨幅
            'stop_and_take_change': mean_stop_and_take_change, # 停盈止损涨幅
            'take_and_stop_daily_change': take_and_stop_daily_change, # 止盈停损日均涨幅
            'stop_and_take_daily_change': stop_and_take_daily_change, # 停盈止损日均涨幅
            'take_and_stop_with_nan_mean': '', # 止盈停损含空均值
            'take_and_stop_non_nan_mean': '', # 止盈停损从下往上非空均值
            'stop_and_take_with_nan_mean': '', # 停盈止损含空均值
            'stop_and_take_non_nan_mean': '', # 停盈止损从下往上非空均值
        })
        
        # 调试打印：股票索引和ops_change列表
        # print(f"日期: {date_key}")
        # print(f"股票索引列表: {stock_indices_per_date}")
        # print(f"ops_change列表: {ops_change_list_per_date}")
        # print(f"ops_change列表长度: {len(ops_change_list_per_date)}")
        # print(f"股票索引列表长度: {len(stock_indices_per_date)}")
        # print("-" * 50)

    # 计算从下往上的均值
    n = len(items)
    for i in range(n):
        # 获取从当前位置到末尾的所有daily_change值
        sub_list = [item['daily_change'] for item in items[i:]]
        
        # 计算非空均值
        non_nan_sum = 0
        non_nan_len = 0
        for v in sub_list:
            if isinstance(v, str) and v == '':
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            try:
                v = float(v) if isinstance(v, str) else v
                non_nan_sum += v
                non_nan_len += 1
            except (ValueError, TypeError):
                continue
                
        if non_nan_len > 0:
            non_nan_mean = float(Decimal(str(non_nan_sum / non_nan_len)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            non_nan_mean = float('nan')
            
        # 计算含空均值 - 修改这里，确保分母包含所有值（包括空值）
        with_nan_vals = []
        for v in sub_list:
            if isinstance(v, str) and v == '':
                with_nan_vals.append(0)
            elif isinstance(v, float) and math.isnan(v):
                with_nan_vals.append(0)
            else:
                try:
                    v = float(v) if isinstance(v, str) else v
                    with_nan_vals.append(v)
                except (ValueError, TypeError):
                    with_nan_vals.append(0)
                    
        with_nan_mean = sum(with_nan_vals) / len(sub_list) if sub_list else float('nan')
        
        # 更新items中的值
        items[i]['non_nan_mean'] = non_nan_mean
        items[i]['with_nan_mean'] = with_nan_mean

        # 新增：计算调幅从下往上的均值
        adjust_sub_list = [item['adjust_daily_change'] for item in items[i:]]
        
        # 计算调幅非空均值
        adjust_non_nan_sum = 0
        adjust_non_nan_len = 0
        for v in adjust_sub_list:
            if isinstance(v, str) and v == '':
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            try:
                v = float(v) if isinstance(v, str) else v
                adjust_non_nan_sum += v
                adjust_non_nan_len += 1
            except (ValueError, TypeError):
                continue
                
        if adjust_non_nan_len > 0:
            adjust_non_nan_mean = float(Decimal(str(adjust_non_nan_sum / adjust_non_nan_len)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            adjust_non_nan_mean = float('nan')
            
        # 计算调幅含空均值
        adjust_with_nan_vals = []
        for v in adjust_sub_list:
            if isinstance(v, str) and v == '':
                adjust_with_nan_vals.append(0)
            elif isinstance(v, float) and math.isnan(v):
                adjust_with_nan_vals.append(0)
            else:
                try:
                    v = float(v) if isinstance(v, str) else v
                    adjust_with_nan_vals.append(v)
                except (ValueError, TypeError):
                    adjust_with_nan_vals.append(0)
                    
        adjust_with_nan_mean = sum(adjust_with_nan_vals) / len(adjust_sub_list) if adjust_sub_list else float('nan')

        # 更新items中的调幅值
        items[i]['adjust_non_nan_mean'] = adjust_non_nan_mean
        items[i]['adjust_with_nan_mean'] = adjust_with_nan_mean

        # 计算止盈停损含空均值
        take_and_stop_sub_list = [item['take_and_stop_daily_change'] for item in items[i:]]

        # 计算止盈停损非空均值
        take_and_stop_non_nan_sum = 0
        take_and_stop_non_nan_len = 0
        for v in take_and_stop_sub_list:
            if isinstance(v, str) and v == '':
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            try:
                v = float(v) if isinstance(v, str) else v
                take_and_stop_non_nan_sum += v
                take_and_stop_non_nan_len += 1
            except (ValueError, TypeError):
                continue
        if take_and_stop_non_nan_len > 0:
            take_and_stop_non_nan_mean = float(Decimal(str(take_and_stop_non_nan_sum / take_and_stop_non_nan_len)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            take_and_stop_non_nan_mean = float('nan')

        # 计算止盈停损含空均值
        take_and_stop_with_nan_vals = []
        for v in take_and_stop_sub_list:
            if isinstance(v, str) and v == '':
                take_and_stop_with_nan_vals.append(0)
            elif isinstance(v, float) and math.isnan(v):
                take_and_stop_with_nan_vals.append(0)
            else:
                try:
                    v = float(v) if isinstance(v, str) else v
                    take_and_stop_with_nan_vals.append(v)
                except (ValueError, TypeError):
                    take_and_stop_with_nan_vals.append(0)
                    
        take_and_stop_with_nan_mean = sum(take_and_stop_with_nan_vals) / len(take_and_stop_sub_list) if take_and_stop_sub_list else float('nan')   

        items[i]['take_and_stop_with_nan_mean'] = take_and_stop_with_nan_mean
        items[i]['take_and_stop_non_nan_mean'] = take_and_stop_non_nan_mean

        # 计算停盈止损含空均值
        stop_and_take_sub_list = [item['stop_and_take_daily_change'] for item in items[i:]]

        # 计算停盈止损非空均值
        stop_and_take_non_nan_sum = 0
        stop_and_take_non_nan_len = 0
        for v in stop_and_take_sub_list:
            if isinstance(v, str) and v == '':
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            try:
                v = float(v) if isinstance(v, str) else v
                stop_and_take_non_nan_sum += v
                stop_and_take_non_nan_len += 1
            except (ValueError, TypeError):
                continue
        if stop_and_take_non_nan_len > 0:
            stop_and_take_non_nan_mean = float(Decimal(str(stop_and_take_non_nan_sum / stop_and_take_non_nan_len)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            stop_and_take_non_nan_mean = float('nan')

        # 计算停盈止损含空均值
        stop_and_take_with_nan_vals = []
        for v in stop_and_take_sub_list:
            if isinstance(v, str) and v == '':
                stop_and_take_with_nan_vals.append(0)
            elif isinstance(v, float) and math.isnan(v):
                stop_and_take_with_nan_vals.append(0)
            else:
                try:
                    v = float(v) if isinstance(v, str) else v
                    stop_and_take_with_nan_vals.append(v)
                except (ValueError, TypeError):
                    stop_and_take_with_nan_vals.append(0)

        stop_and_take_with_nan_mean = sum(stop_and_take_with_nan_vals) / len(stop_and_take_sub_list) if stop_and_take_sub_list else float('nan')

        items[i]['stop_and_take_with_nan_mean'] = stop_and_take_with_nan_mean
        items[i]['stop_and_take_non_nan_mean'] = stop_and_take_non_nan_mean
        
        # 添加到均值列表
        non_nan_mean_list.append(non_nan_mean)
        with_nan_mean_list.append(with_nan_mean)
        adjust_non_nan_mean_list.append(adjust_non_nan_mean)
        adjust_with_nan_mean_list.append(adjust_with_nan_mean)
        take_and_stop_with_nan_mean_list.append(take_and_stop_with_nan_mean)
        take_and_stop_non_nan_mean_list.append(take_and_stop_non_nan_mean)
        stop_and_take_with_nan_mean_list.append(stop_and_take_with_nan_mean)
        stop_and_take_non_nan_mean_list.append(stop_and_take_non_nan_mean)

    # 计算总体统计
    # 预先计算重复使用的safe_mean值，避免重复调用
    mean_ops_change_val = safe_mean(ops_change_list)
    mean_adjust_ops_change_val = safe_mean(adjust_ops_change_list)
    adjust_days_val = safe_mean(adjust_days_list)
    hold_days_val = safe_mean(hold_days_list)
    mean_take_and_stop_change_val = safe_mean(take_and_stop_change_list)
    mean_stop_and_take_change_val = safe_mean(stop_and_take_change_list)
    summary = {
        'mean_hold_days': hold_days_val,
        'mean_ops_change': mean_ops_change_val,
        'comprehensive_stop_daily_change': round(mean_ops_change_val / adjust_days_val, 2) if mean_ops_change_val != '' and adjust_days_val != '' and adjust_days_val != 0 else '',
        'mean_adjust_ops_change': mean_adjust_ops_change_val,
        'comprehensive_daily_change': round(mean_adjust_ops_change_val / hold_days_val, 2) if mean_adjust_ops_change_val != '' and hold_days_val != '' and hold_days_val != 0 else '',
        'mean_daily_change': safe_mean(daily_change_list),
        'mean_adjust_daily_change': safe_mean(adjust_daily_change_list),
        'mean_non_nan': safe_mean(non_nan_mean_list),    # 停盈停损从下往上非空均值
        'mean_with_nan': safe_mean(with_nan_mean_list),  # 停盈停损从下往上含空均值
        'mean_daily_with_nan': safe_mean(daily_change_list_with_nan),  # 使用含空值的列表计算均值
        'max_change': max(daily_change_list) if daily_change_list else '',
        'min_change': min(daily_change_list) if daily_change_list else '',
        # 新增：调幅相关统计
        'mean_adjust_ops_incre_rate': safe_mean(adjust_ops_incre_rate_list),
        'mean_adjust_non_nan': safe_mean(adjust_non_nan_mean_list), # 止盈止损从下往上非空均值
        'mean_adjust_with_nan': safe_mean(adjust_with_nan_mean_list), # 止盈止损从下往上含空均值
        'mean_adjust_daily_with_nan': safe_mean(adjust_ops_incre_rate_list_with_nan),
        'max_adjust_ops_incre_rate': max(adjust_ops_incre_rate_list) if adjust_ops_incre_rate_list else '',
        'min_adjust_ops_incre_rate': min(adjust_ops_incre_rate_list) if adjust_ops_incre_rate_list else '',
        # 新增：止盈停损相关统计，停盈止损相关统计
        'mean_take_and_stop_change': mean_take_and_stop_change_val,
        'comprehensive_take_and_stop_change': round(mean_take_and_stop_change_val / hold_days_val, 2) if mean_take_and_stop_change_val != '' and hold_days_val != '' and hold_days_val != 0 else '',
        'mean_take_and_stop_daily_change': safe_mean(take_and_stop_daily_change_list),
        'mean_take_and_stop_non_nan': safe_mean(take_and_stop_non_nan_mean_list),
        'mean_take_and_stop_with_nan': safe_mean(take_and_stop_with_nan_mean_list),
        'mean_take_and_stop_daily_with_nan': safe_mean(take_and_stop_daily_with_nan_list),
        'mean_stop_and_take_change': mean_stop_and_take_change_val,
        'comprehensive_stop_and_take_change': round(mean_stop_and_take_change_val / hold_days_val, 2) if mean_stop_and_take_change_val != '' and hold_days_val != '' and hold_days_val != 0 else '',
        'mean_stop_and_take_daily_change': safe_mean(stop_and_take_daily_change_list),
        'mean_stop_and_take_non_nan': safe_mean(stop_and_take_non_nan_mean_list),
        'mean_stop_and_take_with_nan': safe_mean(stop_and_take_with_nan_mean_list),
        'mean_stop_and_take_daily_with_nan': safe_mean(stop_and_take_daily_with_nan_list),
        # 新增：调整天数和止盈止损涨幅统计
        'mean_adjust_days': adjust_days_val,
        # 添加从下往上的前1~4个的非空均值和含空均值
        'bottom_first_with_nan': items[-1]['with_nan_mean'] if len(items) > 0 else None,
        'bottom_second_with_nan': items[-2]['with_nan_mean'] if len(items) > 1 else None,
        'bottom_third_with_nan': items[-3]['with_nan_mean'] if len(items) > 2 else None,
        'bottom_fourth_with_nan': items[-4]['with_nan_mean'] if len(items) > 3 else None,
        'bottom_first_take_and_stop_with_nan': items[-1]['take_and_stop_with_nan_mean'] if len(items) > 0 else None,
        'bottom_second_take_and_stop_with_nan': items[-2]['take_and_stop_with_nan_mean'] if len(items) > 1 else None,
        'bottom_third_take_and_stop_with_nan': items[-3]['take_and_stop_with_nan_mean'] if len(items) > 2 else None,
        'bottom_fourth_take_and_stop_with_nan': items[-4]['take_and_stop_with_nan_mean'] if len(items) > 3 else None,
        # 新增：调幅从下往上的前1~4个的非空均值和含空均值
        'adjust_bottom_first_with_nan': items[-1]['adjust_with_nan_mean'] if len(items) > 0 else None,
        'adjust_bottom_second_with_nan': items[-2]['adjust_with_nan_mean'] if len(items) > 1 else None,
        'adjust_bottom_third_with_nan': items[-3]['adjust_with_nan_mean'] if len(items) > 2 else None,
        'adjust_bottom_fourth_with_nan': items[-4]['adjust_with_nan_mean'] if len(items) > 3 else None,
        'bottom_first_stop_and_take_with_nan': items[-1]['stop_and_take_with_nan_mean'] if len(items) > 0 else None,
        'bottom_second_stop_and_take_with_nan': items[-2]['stop_and_take_with_nan_mean'] if len(items) > 1 else None,
        'bottom_third_stop_and_take_with_nan': items[-3]['stop_and_take_with_nan_mean'] if len(items) > 2 else None,
        'bottom_fourth_stop_and_take_with_nan': items[-4]['stop_and_take_with_nan_mean'] if len(items) > 3 else None,
        # 新增：止盈率、止损率、持有率统计
        'total_stocks': total_stocks,
        'hold_rate': round(hold_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
        'profit_rate': round(profit_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
        'loss_rate': round(loss_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
        'hold_count': hold_count,
        'profit_count': profit_count,
        'loss_count': loss_count
    }
    
    # 新增：计算止盈、止损、持有中值
    
    # 计算中位数函数
    def calculate_median(values):
        if not values:
            return None
        try:
            return round(statistics.median(values), 2)
        except Exception as e:
            print(f"计算中位数时出错: {e}")
            return None
    # 计算各数组中位数
    hold_median = calculate_median(hold_changes)
    profit_median = calculate_median(profit_changes)
    loss_median = calculate_median(loss_changes)
    # 将中位数添加到summary中
    summary['hold_median'] = hold_median
    summary['profit_median'] = profit_median
    summary['loss_median'] = loss_median
    # 打印各数组用于校验
    # print(f"持有涨跌幅数组 (end_state=0, op_day_change): {sorted(hold_changes) if hold_changes else '空'}")
    # print(f"止盈涨跌幅数组 (end_state=1, take_profit): {sorted(profit_changes) if profit_changes else '空'}")
    # print(f"止损涨跌幅数组 (end_state=2, stop_loss): {sorted(loss_changes) if loss_changes else '空'}")
    # print(f"持有中位数: {hold_median}")
    # print(f"止盈中位数: {profit_median}")
    # print(f"止损中位数: {loss_median}")
    # 新增：根据N位控件值动态计算从下往上第N位的值
    if items:
        # 调天非空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_non_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['non_nan_mean']
            else:
                summary[var_name] = None

        # 止盈停损含空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_take_and_stop_with_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['take_and_stop_with_nan_mean']
            else:
                summary[var_name] = None

        # 停盈止损含空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_stop_and_take_with_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['stop_and_take_with_nan_mean']
            else:
                summary[var_name] = None
        
        # 调天含空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_with_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['with_nan_mean']
            else:
                summary[var_name] = None
        
        # 调幅非空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_adjust_non_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['adjust_non_nan_mean']
            else:
                summary[var_name] = None
        
        # 调幅含空均值
        for i in range(1, 4):
            var_name = f'bottom_nth_adjust_with_nan{i}'
            n = n_values.get(var_name, 1)
            if n > 0 and n <= len(items):
                summary[var_name] = items[-n]['adjust_with_nan_mean']
            else:
                summary[var_name] = None

    return {
        'items': items,
        'summary': summary
    }

def get_component_analysis_variables():
    """获取组合分析元件变量列表"""
    return [
        'bottom_nth_take_and_stop_with_nan1',
        'bottom_nth_take_and_stop_with_nan2', 
        'bottom_nth_take_and_stop_with_nan3',
        'bottom_nth_with_nan1',
        'bottom_nth_with_nan2',
        'bottom_nth_with_nan3',
        'bottom_nth_stop_and_take_with_nan1',
        'bottom_nth_stop_and_take_with_nan2',
        'bottom_nth_stop_and_take_with_nan3',
        'bottom_nth_adjust_with_nan1',
        'bottom_nth_adjust_with_nan2',
        'bottom_nth_adjust_with_nan3',
    ]

def add_tooltip_to_variable(name_label, variable_name, main_window):
    """
    为变量控件添加悬浮提示，显示该变量的统计信息
    
    Args:
        name_label: 要添加悬浮提示的标签控件
        variable_name: 变量名称
        main_window: 主窗口实例，用于访问 all_row_results
    """
    try:
        if hasattr(main_window, 'overall_stats') and main_window.overall_stats:
            overall_stats = main_window.overall_stats
            max_key = f'{variable_name}_max'
            min_key = f'{variable_name}_min'
            median_key = f'{variable_name}_median'
            positive_median_key = f'{variable_name}_positive_median'
            negative_median_key = f'{variable_name}_negative_median'
            stats_parts = []
            if max_key in overall_stats and overall_stats[max_key] is not None:
                formatted_max = format_overall_stat_value(overall_stats[max_key])
                overall_stats[max_key] = formatted_max  # 更新overall_stats中的值
                stats_parts.append(f"最大值: {formatted_max}")
            if min_key in overall_stats and overall_stats[min_key] is not None:
                formatted_min = format_overall_stat_value(overall_stats[min_key])
                overall_stats[min_key] = formatted_min  # 更新overall_stats中的值
                stats_parts.append(f"最小值: {formatted_min}")
            if median_key in overall_stats and overall_stats[median_key] is not None:
                formatted_median = format_overall_stat_value(overall_stats[median_key])
                overall_stats[median_key] = formatted_median  # 更新overall_stats中的值
                stats_parts.append(f"中值: {formatted_median}")
            if positive_median_key in overall_stats and overall_stats[positive_median_key] is not None:
                formatted_positive_median = format_overall_stat_value(overall_stats[positive_median_key])
                overall_stats[positive_median_key] = formatted_positive_median  # 更新overall_stats中的值
                stats_parts.append(f"正值中值: {formatted_positive_median}")
            if negative_median_key in overall_stats and overall_stats[negative_median_key] is not None:
                formatted_negative_median = format_overall_stat_value(overall_stats[negative_median_key])
                overall_stats[negative_median_key] = formatted_negative_median  # 更新overall_stats中的值
                stats_parts.append(f"负值中值: {formatted_negative_median}")
            if stats_parts:
                tooltip_widget = _create_tooltip_widget(stats_parts, variable_name, main_window, overall_stats)
                # 延迟显示定时器
                name_label._show_tooltip_timer = None
                name_label.enterEvent = lambda event, ln=name_label, tw=tooltip_widget: _delayed_show_custom_tooltip(event, ln, tw)
                name_label.leaveEvent = lambda event, tw=tooltip_widget: _cancel_show_and_delayed_hide(event, name_label, tw)
            else:
                name_label.setToolTip("暂无统计信息")
        else:
            name_label.setToolTip("暂无统计信息")
    except Exception as e:
        name_label.setToolTip("暂无统计信息")

from PyQt5.QtCore import QTimer

def _create_tooltip_widget(stats_parts, variable_name, main_window, overall_stats):
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
    from PyQt5.QtCore import Qt
    tooltip_widget = QWidget()
    tooltip_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
    tooltip_widget.setStyleSheet("""
        QWidget {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #555555;
            border-radius: 5px;
            padding: 5px;
        }
        QPushButton {
            background-color: #4a90e2;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
            color: white;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #357abd;
        }
    """)
    # 横向布局
    layout = QHBoxLayout(tooltip_widget)
    layout.setSpacing(10)
    layout.setContentsMargins(10, 10, 10, 10)
    # 统计信息一行
    stats_text = " , ".join(stats_parts)
    stats_label = QLabel(stats_text)
    stats_label.setWordWrap(False)
    stats_label.setStyleSheet("font-size: 12px; margin-bottom: 0px;")
    layout.addWidget(stats_label)
    # 按钮同一行
    optimize_button = QPushButton("二次优化设置")
    optimize_button.clicked.connect(lambda: _on_optimize_click_button(variable_name, main_window, overall_stats, tooltip_widget))
    layout.addWidget(optimize_button)
    # 鼠标进入/离开事件，配合延迟隐藏
    tooltip_widget.enterEvent = lambda event, tw=tooltip_widget: _cancel_hide_custom_tooltip(event, tw)
    tooltip_widget.leaveEvent = lambda event, tw=tooltip_widget: _delayed_hide_custom_tooltip(event, tw)
    tooltip_widget._hide_timer = None
    return tooltip_widget

def _show_custom_tooltip(event, name_label, tooltip_widget):
    # 获取label在屏幕上的位置，悬浮框显示在label的左下角
    label_global_pos = name_label.mapToGlobal(name_label.rect().bottomLeft())
    tooltip_widget.move(label_global_pos.x(), label_global_pos.y())  # 悬浮框左上角位于label左下角
    tooltip_widget.show()
    _cancel_hide_custom_tooltip(None, tooltip_widget)

def _delayed_hide_custom_tooltip(event, tooltip_widget):
    if hasattr(tooltip_widget, '_hide_timer') and tooltip_widget._hide_timer:
        tooltip_widget._hide_timer.stop()
    else:
        from PyQt5.QtCore import QTimer
        tooltip_widget._hide_timer = QTimer()
    tooltip_widget._hide_timer.setSingleShot(True)
    tooltip_widget._hide_timer.timeout.connect(tooltip_widget.hide)
    tooltip_widget._hide_timer.start(1000)  # 1秒后隐藏

def _cancel_hide_custom_tooltip(event, tooltip_widget):
    if hasattr(tooltip_widget, '_hide_timer') and tooltip_widget._hide_timer:
        tooltip_widget._hide_timer.stop()

def _on_optimize_click_button(variable_name, main_window, overall_stats, tooltip_widget):
    try:
        from PyQt5.QtWidgets import QMessageBox
        
        max_key = f'{variable_name}_max'
        min_key = f'{variable_name}_min'
        positive_median_key = f'{variable_name}_positive_median'
        negative_median_key = f'{variable_name}_negative_median'
        max_value = overall_stats.get(max_key)
        min_value = overall_stats.get(min_key)
        positive_median = overall_stats.get(positive_median_key)
        negative_median = overall_stats.get(negative_median_key)
        # 如果中值为空，按0处理
        positive_median = positive_median if positive_median is not None else 0
        negative_median = negative_median if negative_median is not None else 0
        # 步长默认为0
        step_value = 0
        if hasattr(main_window, 'formula_widget'):
            print("进入二次优化设置")
            formula_widget = main_window.formula_widget
            if hasattr(formula_widget, 'var_widgets') and variable_name in formula_widget.var_widgets:
                widgets = formula_widget.var_widgets[variable_name]
                if 'lower' in widgets and min_value is not None:
                    widgets['lower'].setText(str(min_value))
                if 'upper' in widgets and max_value is not None:
                    widgets['upper'].setText(str(max_value))
                if 'step' in widgets and step_value is not None:
                    widgets['step'].setText(str(step_value))
                if tooltip_widget:
                    tooltip_widget.hide()
                QMessageBox.information(main_window, "设置成功", 
                                      f"已为变量 {variable_name} 设置参数：\n"
                                      f"最小值: {min_value}\n"
                                      f"最大值: {max_value}\n"
                                      f"步长: {step_value}")
                return
            
        # 向前参数设置
        if hasattr(main_window, 'forward_param_state'):
            print("进入向前参数设置")
            forward_param_state = main_window.forward_param_state
            if variable_name in forward_param_state:
                
                # 如果向前参数窗口是打开的，更新窗口中的控件值
                for child in main_window.children():
                    if hasattr(child, 'widgets') and hasattr(child, 'setWindowTitle'):
                        if child.windowTitle() == "设置向前参数" and child.isVisible():
                            if variable_name in child.widgets:
                                widgets = child.widgets[variable_name]
                                if 'lower' in widgets and min_value is not None:
                                    widgets['lower'].setText(str(min_value))
                                if 'upper' in widgets and max_value is not None:
                                    widgets['upper'].setText(str(max_value))
                                if 'step' in widgets and step_value is not None:
                                    widgets['step'].setText(str(step_value))
                                break
                
                if tooltip_widget:
                    tooltip_widget.hide()
                QMessageBox.information(main_window, "设置成功", 
                                      f"已为变量 {variable_name} 设置参数：\n"
                                      f"最小值: {min_value}\n"
                                      f"最大值: {max_value}\n"
                                      f"步长: {step_value}")
                return
        QMessageBox.warning(main_window, "设置失败", f"未找到变量 {variable_name} 对应的控件")
    except Exception as e:
        QMessageBox.critical(main_window, "设置错误", f"设置参数时发生错误：{str(e)}")

def _on_optimize_click(event, name_label, variable_name, main_window, overall_stats):
    _on_optimize_click_button(variable_name, main_window, overall_stats, None)

def _delayed_show_custom_tooltip(event, name_label, tooltip_widget):
    # 鼠标进入时，0.5秒后才显示悬浮框
    def show_tooltip():
        _show_custom_tooltip(event, name_label, tooltip_widget)
    if hasattr(name_label, '_show_tooltip_timer') and name_label._show_tooltip_timer:
        name_label._show_tooltip_timer.stop()
    else:
        name_label._show_tooltip_timer = QTimer()
    name_label._show_tooltip_timer.setSingleShot(True)
    name_label._show_tooltip_timer.timeout.connect(show_tooltip)
    name_label._show_tooltip_timer.start(500)  # 0.5秒后显示

def _cancel_show_and_delayed_hide(event, name_label, tooltip_widget):
    # 鼠标离开时，取消显示定时器，并启动延迟隐藏
    if hasattr(name_label, '_show_tooltip_timer') and name_label._show_tooltip_timer:
        name_label._show_tooltip_timer.stop()
    _delayed_hide_custom_tooltip(event, tooltip_widget)