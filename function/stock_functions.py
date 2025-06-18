import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy, QDialog, QTabWidget, QMessageBox, QGridLayout, QDateEdit, QInputDialog, QAbstractItemView, QGroupBox, QCheckBox, QHeaderView, QScrollArea, QToolButton, QApplication, QMainWindow
from PyQt5.QtCore import QDate, QObject, QEvent, Qt
from PyQt5.QtGui import QDoubleValidator
import time

import math
import concurrent.futures
from multiprocessing import cpu_count
import re

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
    "连续累加值长度", "连续累加值正加和", "连续累加值负加和", "连续累加值开始值", "连续累加值开始后1位值", "连续累加值开始后2位值",
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

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_F:
            self.show_search_dialog()
            return True
        return super().eventFilter(obj, event)

    def show_search_dialog(self):
        text, ok = QInputDialog.getText(self.table, "搜索", "请输入要查找的内容：")
        if ok and text:
            self.search_table(text)

    def search_table(self, text):
        found = False
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text():
                    self.table.setCurrentCell(row, col)
                    self.table.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                    found = True
                    return
        if not found:
            QMessageBox.information(self.table, "提示", "未找到相关内容。")

def safe_val(val):
    import math
    if val is None:
        return ""
    if isinstance(val, float) and (math.isnan(val) or str(val).lower() == 'nan'):
        return ""
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
        max_len = max(row.get('continuous_len', 0) for row in stocks_data)
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
                code = price_data.iloc[stock_idx, 0]
                name = price_data.iloc[stock_idx, 1]
                # 实际开始日期值
                actual_value_val = row.get('actual_value', '')
                table1.setItem(row_idx, 0, QTableWidgetItem(str(code)))
                table1.setItem(row_idx, 1, QTableWidgetItem(str(name)))
                table1.setItem(row_idx, 2, QTableWidgetItem(str(safe_val(actual_value_val))))
                table1.setItem(row_idx, 3, QTableWidgetItem(str(safe_val(row.get('actual_value_date', '')))))
                results = row.get('continuous_results', [])
                for col_idx in range(max_len):
                    val = results[col_idx] if col_idx < len(results) else ""
                    table1.setItem(row_idx, 4 + col_idx, QTableWidgetItem(str(safe_val(val))))
                param_values = [
                    len(results),
                    row.get('cont_sum_pos_sum', ''),
                    row.get('cont_sum_neg_sum', ''),
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
                code = price_data.iloc[stock_idx, 0]
                name = price_data.iloc[stock_idx, 1]
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
                code = price_data.iloc[stock_idx, 0]
                name = price_data.iloc[stock_idx, 1]
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
    # 只创建一次窗口，后续只替换内容
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
    result_window.resize(450, 450)
    result_window.show()
    content_widget.result_window = result_window
    content_widget.result_table = table

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

def calc_continuous_sum_np(arr, start_idx, end_idx):
    np.set_printoptions(suppress=True, precision=4, linewidth=200, floatmode='fixed')
    if start_idx < end_idx:
        print("start_idx < end_idx, return []")
        return []
    if start_idx == end_idx:
        return [round(float(arr[start_idx]), 2)]
    # 正步长切片+反转，保证顺序和表格一致
    arr_slice = np.array(arr[end_idx:start_idx+1])[::-1]
    mask = ~np.isnan(arr_slice)
    if not np.any(mask):
        print("all nan in arr_slice, return []")
        return []
    arr_slice = arr_slice[mask]
    signs = np.sign(arr_slice)
    sign_changes = np.diff(signs) != 0
    
    # 使用numpy的cumsum和where来优化累加
    cumsum = np.cumsum(arr_slice)
    change_indices = np.where(sign_changes)[0] + 1
    
    if len(change_indices) == 0:
        return [round(float(cumsum[-1]), 2)]
        
    result = []
    last_idx = 0
    for idx in change_indices:
        result.append(round(float(cumsum[idx-1] - cumsum[last_idx-1] if last_idx > 0 else cumsum[idx-1]), 2))
        last_idx = idx
    
    result.append(round(float(cumsum[-1] - cumsum[last_idx-1] if last_idx > 0 else cumsum[-1]), 2))
    return result

def calc_continuous_sum_sliding(arr, start_idx, end_idx, prev_result=None, prev_start_idx=None, prev_end_idx=None):
    """
    使用滑动窗口优化的连续累加值计算
    arr: 完整数组
    start_idx: 当前起始索引
    end_idx: 当前结束索引
    prev_result: 上一次的计算结果
    prev_start_idx: 上一次的起始索引
    prev_end_idx: 上一次的结束索引
    """
    # print(f"start_idx: {start_idx}, end_idx: {end_idx}")
    if start_idx < end_idx:
        return []
    if start_idx == end_idx:
        return [round(float(arr[start_idx]), 2)]

    # 如果是第一次计算或索引变化超过1，使用完整计算
    if prev_result is None or abs(start_idx - prev_start_idx) > 1 or abs(end_idx - prev_end_idx) > 1:
        return calc_continuous_sum_np(arr, start_idx, end_idx)

    # 获取新增和移除的元素
    removed_elements = []
    new_elements = []
    
    removed_elements.append(arr[prev_start_idx])
    new_elements.append(arr[end_idx])

    # 如果只有一个元素变化，可以优化计算
    if len(new_elements) == 1 and len(removed_elements) == 1:
        # 这里可以实现增量计算逻辑
        # 由于连续累加值的计算比较复杂，需要根据具体业务逻辑来实现
        # 暂时回退到完整计算
        return calc_continuous_sum_np(arr, start_idx, end_idx)
    
    # 如果有多个元素变化，使用完整计算
    return calc_continuous_sum_np(arr, start_idx, end_idx)

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
        '递增值', '后值大于结束地址值', '后值大于前值返回值', '操作值', '持有天数', '操作涨幅', '调整天数', '日均涨幅',
        't+1递增值', 't+1后值大于结束地址值', 't+1后值大于前值返回值', 't+1操作值', 't+1持有天数', 't+1操作涨幅', 't+1调整天数', 't+1日均涨幅',
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
        return val

    def get_percent(val):
        v = get_val(val)
        if v == '':
            return ''
        return f"{v}%"

    def get_bool(val):
        v = get_val(val)
        if v == '':
            return 'False'
        return str(v)

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
            code = price_data.iloc[stock_idx, 0]
            name = price_data.iloc[stock_idx, 1]
            table.setItem(row_idx, 0, QTableWidgetItem(str(code)))
            table.setItem(row_idx, 1, QTableWidgetItem(str(name)))
            table.setItem(row_idx, 2, QTableWidgetItem(str(get_val(row.get('max_value', '')))))
            table.setItem(row_idx, 3, QTableWidgetItem(str(get_val(row.get('min_value', '')))))
            table.setItem(row_idx, 4, QTableWidgetItem(str(get_val(row.get('end_value', '')))))
            table.setItem(row_idx, 5, QTableWidgetItem(str(get_val(row.get('start_value', '')))))
            table.setItem(row_idx, 6, QTableWidgetItem(str(get_val(row.get('actual_value', '')))))
            table.setItem(row_idx, 7, QTableWidgetItem(str(get_val(row.get('closest_value', '')))))
            table.setItem(row_idx, 8, QTableWidgetItem(str(get_val(row.get('n_days_max_value', '')))))
            table.setItem(row_idx, 9, QTableWidgetItem(str(get_val(row.get('n_max_is_max', '')))))
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
            table.setItem(row_idx, 29, QTableWidgetItem(str(get_val(row.get('t1_increment_value', '')))))
            table.setItem(row_idx, 30, QTableWidgetItem(str(get_val(row.get('t1_after_gt_end_value', '')))))
            table.setItem(row_idx, 31, QTableWidgetItem(str(get_val(row.get('t1_after_gt_start_value', '')))))
            table.setItem(row_idx, 32, QTableWidgetItem(str(get_val(row.get('t1_ops_value', '')))))
            table.setItem(row_idx, 33, QTableWidgetItem(str(row.get('t1_hold_days', ''))))
            table.setItem(row_idx, 34, QTableWidgetItem(get_percent(row.get('t1_ops_change', ''))))
            table.setItem(row_idx, 35, QTableWidgetItem(str(get_val(row.get('t1_adjust_days', '')))))
            # 新增：创新高、创新低
            table.setItem(row_idx, 36, QTableWidgetItem(get_bool(row.get('start_with_new_before_high', ''))))
            table.setItem(row_idx, 37, QTableWidgetItem(get_bool(row.get('start_with_new_before_high2', ''))))
            table.setItem(row_idx, 38, QTableWidgetItem(get_bool(row.get('start_with_new_after_high', ''))))
            table.setItem(row_idx, 39, QTableWidgetItem(get_bool(row.get('start_with_new_after_high2', ''))))
            table.setItem(row_idx, 40, QTableWidgetItem(get_bool(row.get('start_with_new_before_low', ''))))
            table.setItem(row_idx, 41, QTableWidgetItem(get_bool(row.get('start_with_new_before_low2', ''))))
            table.setItem(row_idx, 42, QTableWidgetItem(get_bool(row.get('start_with_new_after_low', ''))))
            table.setItem(row_idx, 43, QTableWidgetItem(get_bool(row.get('start_with_new_after_low2', ''))))
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

    # 新增：操作值控件
    expr_label = QLabel("操作值")
    expr_label.setFixedWidth(50)
    expr_label.setStyleSheet("border: none;")
    expr_edit = parent.expr_edit if hasattr(parent, 'expr_edit') else None
    if expr_edit is None:
        from ui.stock_analysis_ui_v2 import ValidatedExprEdit
        expr_edit = ValidatedExprEdit()
        expr_edit.setPlainText("if INC != 0:\n    result = INC\nelse:\n    result = 0\n")
    expr_edit.setFixedWidth(120)
    expr_edit.setFixedHeight(20)
    # 初始化内容
    if hasattr(parent, 'last_expr') and parent.last_expr:
        expr_edit.setPlainText(parent.last_expr)
    def sync_expr_to_main():
        if hasattr(parent, 'last_expr'):
            parent.last_expr = expr_edit.toPlainText()
    expr_edit.textChanged.connect(sync_expr_to_main)
    # 直接添加到top_layout
    top_layout.addWidget(expr_label)
    top_layout.addWidget(expr_edit)

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

    def on_set_forward_param_btn_clicked():
        abbr_map = get_window_abbr_map()
        class ForwardParamDialog(QDialog):
            def __init__(self, abbr_map, state=None, parent=None):
                super().__init__(parent)
                self.setWindowTitle("设置向前参数")
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
                    direction_combo = QComboBox()
                    direction_combo.addItems(["右单向", "左单向", "全方向"])
                    direction_combo.setFixedWidth(60)
                    direction_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                    logic_check = QCheckBox()
                    logic_check.setFixedWidth(15)
                    logic_label = QLabel("含逻辑")
                    logic_label.setStyleSheet("border: none;")
                    group_layout.addWidget(enable_cb)
                    group_layout.addWidget(label)
                    group_layout.addWidget(lower_edit)
                    group_layout.addWidget(upper_edit)
                    group_layout.addWidget(step_edit)
                    group_layout.addWidget(direction_combo)
                    group_layout.addWidget(logic_check)
                    group_layout.addWidget(logic_label)
                    group_widget.setLayout(group_layout)
                    grid.addWidget(group_widget, row, col)
                    self.widgets[abbr_map[zh_name]] = {
                        "enable": enable_cb,
                        "lower": lower_edit,
                        "upper": upper_edit,
                        "step": step_edit,
                        "direction": direction_combo,
                        "logic": logic_check
                    }
                btn_ok = QPushButton("确定")
                btn_ok.setFixedWidth(80)
                btn_ok.setFixedHeight(32)
                btn_ok.setStyleSheet("font-size: 14px;")
                btn_ok.clicked.connect(self.accept)
                grid.addWidget(btn_ok, row+1, 0, 1, 4)
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
                self.setLayout(grid)
            def get_params(self):
                params = {}
                for k, w in self.widgets.items():
                    params[k] = {
                        "enable": w["enable"].isChecked(),
                        "lower": w["lower"].text(),
                        "upper": w["upper"].text(),
                        "step": w["step"].text(),
                        "direction": w["direction"].currentText(),
                        "logic": w["logic"].isChecked()
                    }
                return params
            def closeEvent(self, event):
                params = self.get_params()
                if hasattr(self.parent(), 'forward_param_state'):
                    self.parent().forward_param_state = params
                    if hasattr(self.parent(), 'save_config'):
                        self.parent().save_config()
                super().closeEvent(event)
        # parent为主窗口实例
        dlg = ForwardParamDialog(abbr_map, state=getattr(parent, 'forward_param_state', None), parent=parent)
        if dlg.exec_():
            params = dlg.get_params()
            parent.forward_param_state = params
            if hasattr(parent, 'save_config'):
                parent.save_config()

    set_forward_param_btn.clicked.connect(on_set_forward_param_btn_clicked)

    # 重新组织top_layout顺序
    for w in [select_count_widget, sort_label, sort_combo, select_btn, view_result_btn, set_forward_param_btn]:
        top_layout.addWidget(w)
    layout.addLayout(top_layout)

    # 获取变量缩写映射
    abbr_map = get_abbr_map()
    logic_map = get_abbr_logic_map()
    round_map = get_abbr_round_map()
    formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, parent)
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
    content_widget.result_window = None  # 新增：结果弹窗
    content_widget.result_table = None   # 新增：结果表格

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
        all_param_result = parent.get_or_calculate_result(
            formula_expr=formula_expr,
            select_count=select_count,
            sort_mode=sort_mode,
            show_main_output=False,
            only_show_selected=False,  # 保持False以获取完整数据
            comparison_vars=comparison_vars
        )
        if all_param_result is None:
            # QMessageBox.information(parent, "提示", "请先上传数据文件！")
            return
        merged_results = all_param_result.get('dates', {})
        
        # 根据排序模式过滤结果
        filtered_results = {}
        for date, results in merged_results.items():
            # 根据排序模式过滤score
            if sort_mode == "最大值排序":
                filtered_results[date] = [r for r in results if r.get('score') is not None and r.get('score', 0) > 0]
            else:  # 最小值排序
                filtered_results[date] = [r for r in results if r.get('score') is not None and r.get('score', 0) < 0]
            
            # 按score排序
            if sort_mode == "最大值排序":
                filtered_results[date].sort(key=lambda x: x['score'], reverse=True)
            else:  # 最小值排序
                filtered_results[date].sort(key=lambda x: x['score'])
            
            # 只保留指定数量的结果
            filtered_results[date] = filtered_results[date][:select_count]
        
        # 使用过滤后的结果
        merged_results = filtered_results
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
        parent.last_formula_select_result_data = {'dates': {first_date: selected_result}}
        table = show_formula_select_table_result(parent, parent.last_formula_select_result_data, getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), is_select_action=True)
        # 弹窗展示
        if hasattr(content_widget, 'result_window') and content_widget.result_window is not None:
            content_widget.result_window.close()
        result_window = QMainWindow()
        result_window.setWindowTitle("选股结果")
        flags = result_window.windowFlags()
        flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
        flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
        result_window.setWindowFlags(flags)
        central_widget = QWidget()
        layout_ = QVBoxLayout(central_widget)
        layout_.addWidget(table)
        result_window.setCentralWidget(central_widget)
        result_window.resize(450, 450)
        result_window.show()
        content_widget.result_window = result_window
        content_widget.result_table = table
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
                win = content_widget.result_window
                if win:
                    for i in reversed(range(win.layout().count())):
                        widget = win.layout().itemAt(i).widget()
                        if widget is not None:
                            widget.setParent(None)
                    win.layout().addWidget(table2)
                    content_widget.result_table = table2
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

def calc_continuous_sum_sliding_window(arr, window_size):
    """
    计算滑动窗口下每个窗口的连续同符号累加和（每个窗口内从头到尾的连续和序列）。
    arr: 一维np.ndarray或list
    window_size: 窗口宽度
    返回: list，每个元素为该窗口的连续和序列
    """
    arr = np.array(arr, dtype=float)
    n = len(arr)
    if n < window_size or window_size <= 0:
        return []
    results = []
    for i in range(n - window_size + 1):
        window = arr[i:i+window_size]
        # 计算窗口内的连续同符号累加和
        cont_sum = [window[0]]
        for j in range(1, window_size):
            if window[j] * window[j-1] > 0:
                cont_sum.append(cont_sum[-1] + window[j])
            else:
                cont_sum.append(window[j])
        results.append(cont_sum)
    return results

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
    merged_results = result.get('dates', {})
    headers = ["股票代码", "股票名称", "持有天数", "操作涨幅", "日均涨跌幅", "选股公式输出值"]
    if not merged_results or not any(merged_results.values()):
        # 返回一个只有表头的空表格
        table = QTableWidget(0, len(headers), parent)
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
    if not stocks:
        table = QTableWidget(0, len(headers), parent)
        table.setHorizontalHeaderLabels(headers)
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(50)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")
        return table
    table = QTableWidget(len(stocks) + 2, len(headers), parent)  # 多两行：空行+均值行
    table.setHorizontalHeaderLabels(headers)
    hold_days_list = []
    ops_change_list = []
    ops_incre_rate_list = []
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
        if price_data is not None and stock_idx is not None:
            code = price_data.iloc[stock_idx, 0]
            name = price_data.iloc[stock_idx, 1]
        else:
            code = stock.get('code', stock.get('stock_idx', ''))
            name = stock.get('name', '')
        hold_days = safe_val(stock.get('hold_days', ''))
        ops_change = safe_val(stock.get('ops_change', ''))
        ops_incre_rate = safe_val(stock.get('ops_incre_rate', ''))
        score = safe_val(stock.get('score', ''))
        # 加%号显示
        ops_change_str = f"{ops_change}%" if ops_change != '' else ''
        ops_incre_rate_str = f"{ops_incre_rate}%" if ops_incre_rate != '' else ''
        table.setItem(row_idx, 0, QTableWidgetItem(str(code)))
        table.setItem(row_idx, 1, QTableWidgetItem(str(name)))
        table.setItem(row_idx, 2, QTableWidgetItem(str(hold_days)))
        table.setItem(row_idx, 3, QTableWidgetItem(ops_change_str))
        table.setItem(row_idx, 4, QTableWidgetItem(ops_incre_rate_str))
        table.setItem(row_idx, 5, QTableWidgetItem(str(score)))
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
    # 计算日均涨跌幅列的值
    min_incre_rate = ''
    if mean_hold_days and mean_hold_days != 0 and mean_ops_change != '':
        calc1 = mean_ops_incre_rate if mean_ops_incre_rate != '' else float('inf')
        calc2 = mean_ops_change / mean_hold_days if mean_hold_days != 0 else float('inf')
        min_incre_rate = round(min(calc1, calc2), 2)
    # 插入均值行
    mean_row_idx = len(stocks) + 1
    table.setItem(mean_row_idx, 0, QTableWidgetItem(""))
    table.setItem(mean_row_idx, 1, QTableWidgetItem(str(first_date)))
    table.setItem(mean_row_idx, 2, QTableWidgetItem(str(mean_hold_days)))
    table.setItem(mean_row_idx, 3, QTableWidgetItem(f"{mean_ops_change}%" if mean_ops_change != '' else ''))
    table.setItem(mean_row_idx, 4, QTableWidgetItem(f"{min_incre_rate}%" if min_incre_rate != '' else ''))
    table.setItem(mean_row_idx, 5, QTableWidgetItem(""))
    table.resizeColumnsToContents()
    table.horizontalHeader().setFixedHeight(50)
    table.horizontalHeader().setStyleSheet("font-size: 12px;")
    return table

def get_abbr_round_only_map():
    """获取只有圆框的变量映射"""
    abbrs = [
        ("非空涨跌幅均值", "non_nan_mean"),
        ("含空涨跌幅均值", "with_nan_mean"),
        ("从下往上的第1个涨跌幅含空均值", "bottom_first_with_nan"),
        ("从下往上的第2个涨跌幅含空均值", "bottom_second_with_nan"),
        ("从下往上的第3个涨跌幅含空均值", "bottom_third_with_nan"),
        ("从下往上的第4个涨跌幅含空均值", "bottom_fourth_with_nan"),
        ("从下往上的第1个涨跌幅非空均值", "bottom_first_non_nan"),
        ("从下往上的第2个涨跌幅非空均值", "bottom_second_non_nan"),
        ("从下往上的第3个涨跌幅非空均值", "bottom_third_non_nan"),
        ("从下往上的第4个涨跌幅非空均值", "bottom_fourth_non_nan"),
        ("从下往上第N位非空均值", "bottom_nth_non_nan1"),
        ("从下往上第N位非空均值", "bottom_nth_non_nan2"),
        ("从下往上第N位非空均值", "bottom_nth_non_nan3"),
        ("从下往上第N位含空均值", "bottom_nth_with_nan1"),
        ("从下往上第N位含空均值", "bottom_nth_with_nan2"),
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
        ("递增率", "increment_rate"),
    ]
    return {zh: en for zh, en in abbrs}

class FormulaSelectWidget(QWidget):
    def __init__(self, abbr_map, abbr_logic_map, abbr_round_map, main_window):
        super().__init__()
        self.abbr_map = abbr_map
        self.abbr_logic_map = abbr_logic_map
        self.abbr_round_map = abbr_round_map
        self.abbr_round_only_map = get_abbr_round_only_map()  # 添加新的map
        self.special_abbr_map = get_special_abbr_map()  # 添加特殊map
        self.var_widgets = {}
        self.comparison_widgets = []  # 存储所有比较控件
        self.main_window = main_window  # 保存主窗口引用
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
                'var2': comp['var2'].currentText()
            })
        state['comparison_widgets'] = comparison_state
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
        var1_combo.setFixedWidth(215)
        var1_combo.setFixedHeight(20)
        var1_combo.view().setMinimumWidth(270)
        comparison_layout.addWidget(var1_combo)
        
        # 下限输入框
        lower_input = QLineEdit()
        lower_input.setPlaceholderText("下限")
        lower_input.setFixedWidth(50)
        comparison_layout.addWidget(lower_input)
        
        # 上限输入框
        upper_input = QLineEdit()
        upper_input.setPlaceholderText("上限")
        upper_input.setFixedWidth(50)
        comparison_layout.addWidget(upper_input)
        
        # 第二个变量下拉框
        var2_combo = QComboBox()
        var2_combo.addItems([zh for zh, _ in self.abbr_map.items()])
        var2_combo.setFixedWidth(215)
        var2_combo.view().setMinimumWidth(270)
        comparison_layout.addWidget(var2_combo)
        
        # 信号连接，确保任意内容变更都能同步状态
        checkbox.stateChanged.connect(self._sync_to_main)
        var1_combo.currentTextChanged.connect(self._sync_to_main)
        var2_combo.currentTextChanged.connect(self._sync_to_main)
        lower_input.textChanged.connect(self._sync_to_main)
        upper_input.textChanged.connect(self._sync_to_main)
        
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
            'var2': var2_combo
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

    def generate_formula(self):
        # 1. 收集所有条件
        conditions = []
        for en, widgets in self.var_widgets.items():
            # 跳过只做传递的逻辑变量
            if en in ('start_with_new_before_high', 'start_with_new_before_high2', 
                      'start_with_new_after_high', 'start_with_new_after_high2', 
                      'start_with_new_before_low', 'start_with_new_before_low2',
                      'start_with_new_after_low', 'start_with_new_after_low2'):
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
        # 新增：向前参数勾选项也参与条件拼接
        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
            for en, v in self.main_window.forward_param_state.items():
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
                    comp_conds.append(f"{var1_en} >= {lower} * {var2_en}")
                if upper and var1_en and var2_en:
                    comp_conds.append(f"{var1_en} <= {upper} * {var2_en}")
                if comp_conds:
                    conditions.append(' and '.join(comp_conds))
        # 3. 连接条件，全部用and拼接
        if conditions:
            cond_str = "if " + " and ".join(conditions) + ":"
        else:
            cond_str = "if True:"
        # 4. 收集所有被圆框勾选的变量
        result_vars = []
        for en, widgets in self.var_widgets.items():
            # 跳过 get_abbr_round_only_map 中的变量
            if en in self.abbr_round_only_map.values():
                continue
            if 'round_checkbox' in widgets and widgets['round_checkbox'].isChecked():
                result_vars.append(en)
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
            var_layout.addWidget(lower_input)

            upper_input = QLineEdit()
            upper_input.setPlaceholderText("上限")
            upper_input.setFixedWidth(30)
            var_layout.addWidget(upper_input)

            # 添加步长输入框
            step_input = QLineEdit()
            step_input.setPlaceholderText("步长")
            step_input.setFixedWidth(30)
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
            if en_val in ['bottom_nth_non_nan1', 'bottom_nth_non_nan2', 'bottom_nth_non_nan3', 'bottom_nth_with_nan1', 'bottom_nth_with_nan2']:
                name_label = QLabel(zh)
                name_label.setFixedWidth(120)  # 更紧凑
            else:
                name_label = QLabel(zh)
                name_label.setFixedWidth(250)  # 保持原宽度
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft)
            var_layout.addWidget(name_label)

            # 为特定的变量添加N值输入框
            if en_val in ['bottom_nth_non_nan1', 'bottom_nth_non_nan2', 'bottom_nth_non_nan3', 'bottom_nth_with_nan1', 'bottom_nth_with_nan2']:
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
        comparison_start_row = last_var_row + round_only_rows + special_rows + 2
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

def get_abbr_map():
    """获取变量缩写映射字典"""
    abbrs = [
        ("前1组结束日地址值", "end_value"), 
        ("前1组结束地址前N日的最高值", "n_days_max_value"), 
        ("前1组结束地址前1日涨跌幅", "prev_day_change"), ("前1组结束日涨跌幅", "end_day_change"), ("后一组结束地址值", "diff_end_value"),
        ("连续累加值数组非空数据长度", "continuous_len"), ("连续累加值正加值和", "cont_sum_pos_sum"), ("连续累加值负加值和", "cont_sum_neg_sum"), ("连续累加值开始值", "continuous_start_value"), ("连续累加值开始后1位值", "continuous_start_next_value"),
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
        ("向前最大有效累加值数组非空数据长度", "forward_max_valid_sum_len"), 
        ("向前最大有效累加值正加值和", "forward_max_valid_pos_sum"), ("向前最大有效累加值负加值和", "forward_max_valid_neg_sum"),
        ("向前最大有效累加值数组前一半绝对值之和", "forward_max_valid_abs_sum_first_half"), ("向前最大有效累加值数组后一半绝对值之和", "forward_max_valid_abs_sum_second_half"),
        ("向前最大有效累加值数组前四分之1绝对值之和", "forward_max_valid_abs_sum_block1"), ("向前最大有效累加值数组前四分之1-2绝对值之和", "forward_max_valid_abs_sum_block2"),
        ("向前最大有效累加值数组前四分之2-3绝对值之和", "forward_max_valid_abs_sum_block3"), ("向前最大有效累加值数组后四分之1绝对值之和", "forward_max_valid_abs_sum_block4"),
        ("向前最大连续累加值前一半绝对值之和", "forward_max_abs_sum_first_half"), ("向前最大连续累加值后一半绝对值之和", "forward_max_abs_sum_second_half"),
        ("向前最大连续累加值前四分之1绝对值之和", "forward_max_abs_sum_block1"), ("向前最大连续累加值前四分之1-2绝对值之和", "forward_max_abs_sum_block2"),
        ("向前最大连续累加值前四分之2-3绝对值之和", "forward_max_abs_sum_block3"), ("向前最大连续累加值后四分之1绝对值之和", "forward_max_abs_sum_block4"),
        ("向前最小有效累加值数组非空数据长度", "forward_min_valid_sum_len"), 
        ("向前最小有效累加值正加值和", "forward_min_valid_pos_sum"), ("向前最小有效累加值负加值和", "forward_min_valid_neg_sum"),
        ("向前最小有效累加值数组前一半绝对值之和", "forward_min_valid_abs_sum_first_half"), ("向前最小有效累加值数组后一半绝对值之和", "forward_min_valid_abs_sum_second_half"),
        ("向前最小有效累加值数组前四分之1绝对值之和", "forward_min_valid_abs_sum_block1"), ("向前最小有效累加值数组前四分之1-2绝对值之和", "forward_min_valid_abs_sum_block2"),
        ("向前最小有效累加值数组前四分之2-3绝对值之和", "forward_min_valid_abs_sum_block3"), ("向前最小有效累加值数组后四分之1绝对值之和", "forward_min_valid_abs_sum_block4"),
        ("向前最大连续累加值开始值", "forward_max_continuous_start_value"), ("向前最大连续累加值开始后1位值", "forward_max_continuous_start_next_value"), ("向前最大连续累加值开始后2位值", "forward_max_continuous_start_next_next_value"),
        ("向前最大连续累加值结束值", "forward_max_continuous_end_value"), ("向前最大连续累加值结束前1位值", "forward_max_continuous_end_prev_value"), ("向前最大连续累加值结束前2位值", "forward_max_continuous_end_prev_prev_value"),
        ("向前最小连续累加值开始值", "forward_min_continuous_start_value"), ("向前最小连续累加值开始后1位值", "forward_min_continuous_start_next_value"), ("向前最小连续累加值开始后2位值", "forward_min_continuous_start_next_next_value"),
        ("向前最小连续累加值结束值", "forward_min_continuous_end_value"), ("向前最小连续累加值结束前1位值", "forward_min_continuous_end_prev_value"), ("向前最小连续累加值结束前2位值", "forward_min_continuous_end_prev_prev_value"),
        ("向前最小连续累加值前一半绝对值之和", "forward_min_abs_sum_first_half"), ("向前最小连续累加值后一半绝对值之和", "forward_min_abs_sum_second_half"),
        ("向前最小连续累加值前四分之1绝对值之和", "forward_min_abs_sum_block1"), ("向前最小连续累加值前四分之1-2绝对值之和", "forward_min_abs_sum_block2"),
        ("向前最小连续累加值前四分之2-3绝对值之和", "forward_min_abs_sum_block3"), ("向前最小连续累加值后四分之1绝对值之和", "forward_min_abs_sum_block4"),
        ("向前最大连续累加值数组非空数据长度", "forward_max_result_len"),
        ("向前最小连续累加值数组非空数据长度", "forward_min_result_len"),
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
            'items': [
                {
                    'date': '日期',
                    'hold_days': '操作天数',
                    'ops_change': '持有涨跌幅',
                    'daily_change': '日均涨跌幅',
                    'non_nan_mean': '从下往上非空均值',
                    'with_nan_mean': '从下往上含空均值'
                },
                ...
            ],
            'summary': {
                'mean_hold_days': '操作天数均值',
                'mean_ops_change': '持有涨跌幅均值',
                'mean_daily_change': '日均涨跌幅均值',
                'mean_non_nan': '从下往上非空均值均值',
                'mean_with_nan': '从下往上含空均值均值',
                'mean_daily_with_nan': '日均涨跌幅含空均值',
                'max_change': '最大涨跌幅',
                'min_change': '最小涨跌幅'
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

    # 存储每个日期的详细数据
    items = []
    # 存储用于计算总体统计的数据
    hold_days_list = []
    ops_change_list = []
    daily_change_list = []
    daily_change_list_with_nan = []  # 新增：存储含空值的日均涨跌幅列表
    non_nan_mean_list = []
    with_nan_mean_list = []
    
    # 计算每个日期的数据
    for date_key, stocks in valid_items:
        hold_days_list_per_date = []
        ops_change_list_per_date = []
        ops_incre_rate_list_per_date = []
        
        for stock in stocks:
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

        mean_hold_days = safe_mean(hold_days_list_per_date)
        mean_ops_change = safe_mean(ops_change_list_per_date)
        mean_ops_incre_rate = safe_mean(ops_incre_rate_list_per_date)
        
        daily_change = ''
        if mean_hold_days and mean_hold_days != 0 and mean_ops_change != '':
            calc1 = mean_ops_incre_rate if mean_ops_incre_rate != '' else float('inf')
            calc2 = mean_ops_change / mean_hold_days if mean_hold_days != 0 else float('inf')
            daily_change = round(min(calc1, calc2), 2)
            
        if mean_hold_days != '':
            hold_days_list.append(mean_hold_days)
        if mean_ops_change != '':
            ops_change_list.append(mean_ops_change)
        if daily_change != '':
            daily_change_list.append(daily_change)
            daily_change_list_with_nan.append(daily_change)  # 添加到含空值列表
        else:
            daily_change_list_with_nan.append(0)  # 空值当作0处理
            
        # 添加到items列表
        items.append({
            'date': date_key,
            'hold_days': mean_hold_days,
            'ops_change': mean_ops_change,
            'daily_change': daily_change,
            'non_nan_mean': '',  # 将在后面计算
            'with_nan_mean': ''  # 将在后面计算
        })

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
        
        # 添加到均值列表
        non_nan_mean_list.append(non_nan_mean)
        with_nan_mean_list.append(with_nan_mean)

    # 计算总体统计
    summary = {
        'mean_hold_days': safe_mean(hold_days_list),
        'mean_ops_change': safe_mean(ops_change_list),
        'mean_daily_change': safe_mean(daily_change_list),
        'mean_non_nan': safe_mean(non_nan_mean_list),
        'mean_with_nan': safe_mean(with_nan_mean_list),  # 保持为从下往上含空均值
        'mean_daily_with_nan': safe_mean(daily_change_list_with_nan),  # 使用含空值的列表计算均值
        'max_change': max(daily_change_list) if daily_change_list else '',
        'min_change': min(daily_change_list) if daily_change_list else '',
        # 添加从下往上的前1~4个的非空均值和含空均值
        'bottom_first_with_nan': items[-1]['with_nan_mean'] if len(items) > 0 else None,
        'bottom_second_with_nan': items[-2]['with_nan_mean'] if len(items) > 1 else None,
        'bottom_third_with_nan': items[-3]['with_nan_mean'] if len(items) > 2 else None,
        'bottom_fourth_with_nan': items[-4]['with_nan_mean'] if len(items) > 3 else None,
        'bottom_first_non_nan': items[-1]['non_nan_mean'] if len(items) > 0 else None,
        'bottom_second_non_nan': items[-2]['non_nan_mean'] if len(items) > 1 else None,
        'bottom_third_non_nan': items[-3]['non_nan_mean'] if len(items) > 2 else None,
        'bottom_fourth_non_nan': items[-4]['non_nan_mean'] if len(items) > 3 else None
    }

    return {
        'items': items,
        'summary': summary
    }