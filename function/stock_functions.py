import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta
from decimal import Decimal
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
    "连续累加值长度", "连续累加值开始值", "连续累加值开始后1位值", "连续累加值开始后2位值",
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
                table1.setItem(row_idx, 2, QTableWidgetItem(str(actual_value_val)))
                table1.setItem(row_idx, 3, QTableWidgetItem(str(row.get('actual_value_date', ''))))
                results = row.get('continuous_results', [])
                for col_idx in range(max_len):
                    val = results[col_idx] if col_idx < len(results) else ""
                    table1.setItem(row_idx, 4 + col_idx, QTableWidgetItem(str(val)))
                param_values = [
                    len(results),
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
                    table1.setItem(row_idx, 4 + max_len + i, QTableWidgetItem(str(val)))
                # 空一列
                table1.setItem(row_idx, 4 + max_len + len(param_values), QTableWidgetItem(""))
                # 有效累加值内容
                valid_arr = row.get('valid_sum_arr', [])
                for col_idx in range(max_valid_len):
                    val = valid_arr[col_idx] if col_idx < len(valid_arr) else ""
                    table1.setItem(row_idx, 4 + max_len + len(param_values) + 1 + col_idx, QTableWidgetItem(str(val)))
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
                    table1.setItem(row_idx, 4 + max_len + len(param_values) + 1 + max_valid_len + i, QTableWidgetItem(str(val)))

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
                    table3.setItem(row_idx, 4 + max_forward_len + i, QTableWidgetItem(str(val)))

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
                    table4.setItem(row_idx, 4 + max_forward_min_len + i, QTableWidgetItem(str(val)))

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
        '前1组结束日地址值',
        '前1组结束地址前1日涨跌幅', '前1组结束日涨跌幅', '后1组结束地址值',
        '递增值', '后值大于结束地址值', '后值大于前值返回值', '操作值', '持有天数', '操作涨幅', '调整天数', '日均涨幅'
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
            table.setItem(row_idx, 12, QTableWidgetItem(str(get_val(row.get('end_value', '')))))
            table.setItem(row_idx, 13, QTableWidgetItem(get_percent(row.get('prev_day_change', ''))))
            table.setItem(row_idx, 14, QTableWidgetItem(get_percent(row.get('end_day_change', ''))))
            table.setItem(row_idx, 15, QTableWidgetItem(str(get_val(row.get('diff_end_value', '')))))
            table.setItem(row_idx, 16, QTableWidgetItem(str(get_val(row.get('increment_value', '')))))
            table.setItem(row_idx, 17, QTableWidgetItem(str(get_val(row.get('after_gt_end_value', '')))))
            table.setItem(row_idx, 18, QTableWidgetItem(str(get_val(row.get('after_gt_start_value', '')))))
            table.setItem(row_idx, 19, QTableWidgetItem(str(get_val(row.get('ops_value', '')))))
            table.setItem(row_idx, 20, QTableWidgetItem(str(row.get('hold_days', ''))))
            table.setItem(row_idx, 21, QTableWidgetItem(get_percent(row.get('ops_change', ''))))
            table.setItem(row_idx, 22, QTableWidgetItem(str(get_val(row.get('adjust_days', '')))))
            table.setItem(row_idx, 23, QTableWidgetItem(get_percent(row.get('ops_incre_rate', ''))))
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(50)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

    update_table(stocks_data)

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
    from PyQt5.QtWidgets import QMessageBox, QScrollArea
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
    select_count_layout.setContentsMargins(10, 10, 10, 10)
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

    # 变更时同步到主界面变量
    def sync_to_main():
        parent.last_select_count = select_count_spin.value()
        parent.last_sort_mode = sort_combo.currentText()
    select_count_spin.valueChanged.connect(sync_to_main)
    sort_combo.currentTextChanged.connect(sync_to_main)

    select_btn = QPushButton("进行选股")
    select_btn.setFixedSize(100, 50)
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
    view_result_btn.setFixedSize(100, 50)
    view_result_btn.setStyleSheet(select_btn.styleSheet())
    for w in [select_count_widget, sort_label, sort_combo, select_btn, view_result_btn]:
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
        select_count = select_count_spin.value()
        sort_mode = sort_combo.currentText()
        all_param_result = parent.get_or_calculate_result(
            formula_expr=formula_expr,
            select_count=select_count,
            sort_mode=sort_mode,
            show_main_output=False,
            only_show_selected=False
        )
        if all_param_result is None:
            # QMessageBox.information(parent, "提示", "请先上传数据文件！")
            return
        merged_results = all_param_result.get('dates', {})
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
        result_window.resize(410, 450)
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
            
        if hasattr(content_widget, 'result_window') and content_widget.result_window is not None:
            if content_widget.result_window.isVisible():
                content_widget.result_window.raise_()
                content_widget.result_window.activateWindow()
                return
            else:
                content_widget.result_window.close()
                
        # 重新弹窗
        result_window = QMainWindow()
        result_window.setWindowTitle("选股结果")
        flags = result_window.windowFlags()
        flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
        flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
        result_window.setWindowFlags(flags)
        central_widget = QWidget()
        layout_ = QVBoxLayout(central_widget)
        table = show_formula_select_table_result(parent, parent.last_formula_select_result_data, getattr(parent, 'init', None) and getattr(parent.init, 'price_data', None), is_select_action=True)
        layout_.addWidget(table)
        result_window.setCentralWidget(central_widget)
        result_window.resize(410, 450)
        result_window.show()
        content_widget.result_window = result_window
        content_widget.result_table = table

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
    headers = ["股票代码", "股票名称", "持有天数", "操作涨幅", "日均涨跌幅", "得分"]
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

class FormulaSelectWidget(QWidget):
    def __init__(self, abbr_map, abbr_logic_map, abbr_round_map, main_window):
        super().__init__()
        self.abbr_map = abbr_map
        self.abbr_logic_map = abbr_logic_map
        self.abbr_round_map = abbr_round_map
        self.var_widgets = {}
        self.comparison_widgets = []  # 存储所有比较控件
        self.main_window = main_window  # 保存主窗口引用
        self.init_ui()
        # 先恢复状态
        if hasattr(self.main_window, 'last_formula_select_state'):
            # print(f"恢复状态: {self.main_window.last_formula_select_state}")
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
        # print(f"保存状态: {state}")  # 添加打印语句
        self.main_window.last_formula_select_state = state
        # print(f"保存后的状态: {self.main_window.last_formula_select_state}")  # 添加打印语句
        """同步状态到主界面"""
        if not hasattr(self, 'main_window'):
            return
        # 生成公式
        formula = self.generate_formula()
        # 更新主界面的公式
        if hasattr(self.main_window, 'formula_expr_edit'):
            self.main_window.formula_expr_edit.setPlainText(formula)
        # 更新last_formula_expr
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
        # 先清除现有的比较控件
        for comp in self.comparison_widgets[:]:
            self.delete_comparison_widget(comp['widget'])
        # 然后根据保存的状态重新创建
        for comp_data in state.get('comparison_widgets', []):
            comp = self.add_comparison_widget()
            if comp:  # 确保 comp 不是 None
                # 等待下拉框选项加载完成
                QApplication.processEvents()
                # 设置勾选框状态
                comp['checkbox'].setChecked(comp_data.get('checked', True))  # 默认True保持向后兼容
                # 设置下拉框的值
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
                # 设置输入框的值
                comp['lower'].setText(comp_data.get('lower', ''))
                comp['upper'].setText(comp_data.get('upper', ''))

    def add_comparison_widget(self):
        # 创建比较控件容器
        comparison_widget = QWidget()
        comparison_widget.setFixedWidth(504)
        comparison_widget.setFixedHeight(35)  # 设置固定高度为35像素
        comparison_layout = QHBoxLayout(comparison_widget)
        comparison_layout.setContentsMargins(10, 10, 10, 10)
        comparison_layout.setSpacing(8)
        
        # 添加方框勾选框
        checkbox = QCheckBox()
        checkbox.setChecked(True)  # 默认勾选
        checkbox.setFixedWidth(15)
        # checkbox.setStyleSheet("border: none;")
        comparison_layout.addWidget(checkbox)
        
        # 第一个变量下拉框
        var1_combo = QComboBox()
        var1_combo.addItems([zh for zh, _ in self.abbr_map.items()])
        var1_combo.setFixedWidth(150)
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
        var2_combo.setFixedWidth(150)
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
        for col, (zh, en) in enumerate(logic_keys):
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
            grid_layout.addWidget(var_widget, 0, col)

        # 2. 数值变量控件从第一行开始，每行5个
        self.cols_per_row = 5
        value_keys = list(self.abbr_map.items())
        self.value_keys = value_keys  # 记录变量控件顺序
        self.var_count = len(value_keys)
        for idx, (zh, en) in enumerate(value_keys):
            row = idx // self.cols_per_row + 1  # 从第1行开始，因为第0行是逻辑变量
            col = idx % self.cols_per_row
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
            name_label = QLabel(zh)
            name_label.setFixedWidth(250)
            name_label.setStyleSheet("border: none;")
            name_label.setAlignment(Qt.AlignLeft)
            var_layout.addWidget(name_label)
            lower_input = QLineEdit()
            lower_input.setPlaceholderText("下限")
            lower_input.setFixedWidth(50)
            var_layout.addWidget(lower_input)
            upper_input = QLineEdit()
            upper_input.setPlaceholderText("上限")
            upper_input.setFixedWidth(50)
            var_layout.addWidget(upper_input)
            widget_dict = {
                'checkbox': checkbox,
                'lower': lower_input,
                'upper': upper_input
            }
            if need_round_checkbox:
                name_label.setFixedWidth(228)
                widget_dict['round_checkbox'] = round_checkbox
            self.var_widgets[en] = widget_dict
            grid_layout.addWidget(var_widget, row, col)
        # 3. 比较控件和添加比较按钮放在变量控件最后一行最后一列后面
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
        self._refresh_comparison_row(grid_layout)
        conditions_group.setLayout(grid_layout)
        layout.addWidget(conditions_group)
        self.setLayout(layout)
        # 在末尾添加
        self._setup_state_sync()

    def _refresh_comparison_row(self, grid_layout=None):
        last_var_row = (len(self.value_keys) - 1) // self.cols_per_row + 1
        last_var_col = (len(self.value_keys) - 1) % self.cols_per_row
        for comp in getattr(self, 'comparison_widgets', []):
            if hasattr(comp, 'widget'):
                comp['widget'].setParent(None)
        if hasattr(self, 'add_comparison_btn'):
            self.add_comparison_btn.setParent(None)
        # 修正：如果最后一行变量控件已满，比较控件和按钮应从下一行第0列开始
        start_col = last_var_col + 1
        row = last_var_row
        if start_col >= self.cols_per_row:
            row += 1
            start_col = 0
        col = start_col
        for i, comp in enumerate(self.comparison_widgets):
            grid_layout.addWidget(comp['widget'], row, col)
            col += 1
            if col >= self.cols_per_row:
                row += 1
                col = 0
        grid_layout.addWidget(self.add_comparison_btn, row, col)

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

def get_abbr_map():
    """获取变量缩写映射字典"""
    abbrs = [
        ("前1组结束日地址值", "end_value"), 
        ("前1组结束地址前N日的最高值", "n_days_max_value"), 
        ("前1组结束地址前1日涨跌幅", "prev_day_change"), ("前1组结束日涨跌幅", "end_day_change"), ("后一组结束地址值", "diff_end_value"),
        ("连续累加值数组非空数据长度", "continuous_len"), ("连续累加值开始值", "continuous_start_value"), ("连续累加值开始后1位值", "continuous_start_next_value"),
        ("连续累加值开始后2位值", "continuous_start_next_next_value"), ("连续累加值结束值", "continuous_end_value"), ("连续累加值结束前1位值", "continuous_end_prev_value"), ("连续累加值结束前2位值", "continuous_end_prev_prev_value"),
        ("连续累加值数组前一半绝对值之和", "continuous_abs_sum_first_half"), ("连续累加值数组后一半绝对值之和", "continuous_abs_sum_second_half"),
        ("连续累加值数组前四分之一绝对值之和", "continuous_abs_sum_block1"), ("连续累加值数组前四分之1-2绝对值之和", "continuous_abs_sum_block2"),
        ("连续累加值数组前四分之2-3绝对值之和", "continuous_abs_sum_block3"), ("连续累加值数组后四分之一绝对值之和", "continuous_abs_sum_block4"),
        ("有效累加值正加值和", "valid_pos_sum"), ("有效累加值负加值和", "valid_neg_sum"), ("有效累加值数组非空数据长度", "valid_sum_len"),
        ("有效累加值数组前一半绝对值之和", "valid_abs_sum_first_half"), ("有效累加值数组后一半绝对值之和", "valid_abs_sum_second_half"),
        ("有效累加值数组前四分之1绝对值之和", "valid_abs_sum_block1"), ("有效累加值数组前四分之1-2绝对值之和", "valid_abs_sum_block2"),
        ("有效累加值数组前四分之2-3绝对值之和", "valid_abs_sum_block3"), ("有效累加值数组后四分之1绝对值之和", "valid_abs_sum_block4"),
        ("向前最大有效累加值数组非空数据长度", "forward_max_valid_sum_len"), 
        ("向前最大有效累加值正加值和", "forward_max_valid_pos_sum"), ("向前最大有效累加值负加值和", "forward_max_valid_neg_sum"),
        ("向前最大有效累加值数组前一半绝对值之和", "forward_max_valid_abs_sum_first_half"), ("向前最大有效累加值数组后一半绝对值之和", "forward_max_valid_abs_sum_second_half"),
        ("向前最大有效累加值数组前四分之1绝对值之和", "forward_max_valid_abs_sum_block1"), ("向前最大有效累加值数组前四分之1-2绝对值之和", "forward_max_valid_abs_sum_block2"),
        ("向前最大有效累加值数组前四分之2-3绝对值之和", "forward_max_valid_abs_sum_block3"), ("向前最大有效累加值数组后四分之1绝对值之和", "forward_max_valid_abs_sum_block4"),
        ("向前最大连续累加值前一半绝对值之和", "forward_max_continuous_abs_sum_first_half"), ("向前最大连续累加值后一半绝对值之和", "forward_max_continuous_abs_sum_second_half"),
        ("向前最大连续累加值前四分之1绝对值之和", "forward_max_continuous_abs_sum_block1"), ("向前最大连续累加值前四分之1-2绝对值之和", "forward_max_continuous_abs_sum_block2"),
        ("向前最大连续累加值前四分之2-3绝对值之和", "forward_max_continuous_abs_sum_block3"), ("向前最大连续累加值后四分之1绝对值之和", "forward_max_continuous_abs_sum_block4"),
        ("向前最小有效累加值数组非空数据长度", "forward_min_valid_sum_len"), 
        ("向前最小有效累加值正加值和", "forward_min_valid_pos_sum"), ("向前最小有效累加值负加值和", "forward_min_valid_neg_sum"),
        ("向前最小有效累加值数组前一半绝对值之和", "forward_min_valid_abs_sum_first_half"), ("向前最小有效累加值数组后一半绝对值之和", "forward_min_valid_abs_sum_second_half"),
        ("向前最小有效累加值数组前四分之1绝对值之和", "forward_min_valid_abs_sum_block1"), ("向前最小有效累加值数组前四分之1-2绝对值之和", "forward_min_valid_abs_sum_block2"),
        ("向前最小有效累加值数组前四分之2-3绝对值之和", "forward_min_valid_abs_sum_block3"), ("向前最小有效累加值数组后四分之1绝对值之和", "forward_min_valid_abs_sum_block4"),
        ("向前最大连续累加值开始值", "forward_max_continuous_start_value"), ("向前最大连续累加值开始后1位值", "forward_max_continuous_start_next_value"), ("向前最大连续累加值开始后2位值", "forward_max_continuous_start_next_next_value"),
        ("向前最大连续累加值结束值", "forward_max_continuous_end_value"), ("向前最大连续累加值结束前1位值", "forward_max_continuous_end_prev_value"), ("向前最大连续累加值结束前2位值", "forward_max_continuous_end_prev_prev_value"),
        ("向前最小连续累加值开始值", "forward_min_continuous_start_value"), ("向前最小连续累加值开始后1位值", "forward_min_continuous_start_next_value"), ("向前最小连续累加值开始后2位值", "forward_min_continuous_start_next_next_value"),
        ("向前最小连续累加值结束值", "forward_min_continuous_end_value"), ("向前最小连续累加值结束前1位值", "forward_min_continuous_end_prev_value"), ("向前最小连续累加值结束前2位值", "forward_min_continuous_end_prev_prev_value"),
        ("向前最小连续累加值前一半绝对值之和", "forward_min_continuous_abs_sum_first_half"), ("向前最小连续累加值后一半绝对值之和", "forward_min_continuous_abs_sum_second_half"),
        ("向前最小连续累加值前四分之1绝对值之和", "forward_min_continuous_abs_sum_block1"), ("向前最小连续累加值前四分之1-2绝对值之和", "forward_min_continuous_abs_sum_block2"),
        ("向前最小连续累加值前四分之2-3绝对值之和", "forward_min_continuous_abs_sum_block3"), ("向前最小连续累加值后四分之1绝对值之和", "forward_min_continuous_abs_sum_block4"),
        ("向前最大连续累加值数组非空数据长度", "forward_max_result_len"),
        ("向前最小连续累加值数组非空数据长度", "forward_min_result_len")
    ]
    return {zh: en for zh, en in abbrs}


def get_abbr_logic_map():
    """获取变量缩写映射字典"""
    abbrs = [
        ("第1组后N最大值逻辑", "n_max_is_max"),
        ("开始日到结束日之间最高价/最低价小于M", "range_ratio_is_less"), 
        ("开始日到结束日之间连续累加值绝对值小于M", "continuous_abs_is_less")
    ]
    return {zh: en for zh, en in abbrs}

def get_abbr_round_map():
    """只需要圆框勾选的变量映射"""
    abbrs = [
        ("有效累加值正加值和", "valid_pos_sum"),
        ("有效累加值负加值和", "valid_neg_sum"),
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