import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta
from decimal import Decimal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy, QDialog, QTabWidget, QMessageBox, QGridLayout, QDateEdit
from PyQt5.QtCore import QDate

import math

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
    "有效累加值第一块绝对值之和", "有效累加值第二块绝对值之和",
    "有效累加值第三块绝对值之和", "有效累加值第四块绝对值之和"
]
# 向前最大相关参数表头
forward_param_headers = [
    "向前最大日期", "向前最大有效累加值数组长度", "向前最大有效累加值", "向前最大有效累加值正加值和", "向前最大有效累加值负加值和",
    "向前最大有效累加值数组前一半绝对值之和", "向前最大有效累加值数组后一半绝对值之和",
    "向前最大有效累加值数组第一块绝对值之和", "向前最大有效累加值数组第二块绝对值之和",
    "向前最大有效累加值数组第三块绝对值之和", "向前最大有效累加值数组第四块绝对值之和"
]
# 向前最小相关参数表头
forward_min_param_headers = [
    "向前最小日期", "向前最小有效累加值数组长度", "向前最小有效累加值", "向前最小有效累加值正加值和", "向前最小有效累加值负加值和",
    "向前最小有效累加值数组前一半绝对值之和", "向前最小有效累加值数组后一半绝对值之和",
    "向前最小有效累加值数组第一块绝对值之和", "向前最小有效累加值数组第二块绝对值之和",
    "向前最小有效累加值数组第三块绝对值之和", "向前最小有效累加值数组第四块绝对值之和"
]

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

        table1 = QTableWidget(len(stocks_data), len(headers1))
        table2 = QTableWidget(len(stocks_data), len(headers2))
        table3 = QTableWidget(len(stocks_data), len(headers3))
        table4 = QTableWidget(len(stocks_data), len(headers4))

        table1.setHorizontalHeaderLabels(headers1)
        table2.setHorizontalHeaderLabels(headers2)
        table3.setHorizontalHeaderLabels(headers3)
        table4.setHorizontalHeaderLabels(headers4)

        def update_tables(stocks_data):
            # table1
            table1.setRowCount(len(stocks_data))
            for row_idx, row in enumerate(stocks_data):
                stock_idx = row.get('stock_idx', 0)
                code = price_data.iloc[stock_idx, 0]
                name = price_data.iloc[stock_idx, 1]
                table1.setItem(row_idx, 0, QTableWidgetItem(str(code)))
                table1.setItem(row_idx, 1, QTableWidgetItem(str(name)))
                table1.setItem(row_idx, 2, QTableWidgetItem(str(row.get('actual_value', [None, None])[1]) if row.get('actual_value') else ''))
                table1.setItem(row_idx, 3, QTableWidgetItem(str(row.get('start_value', [None, None])[0]) if row.get('start_value') else ''))
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

            # table2
            table2.setRowCount(len(stocks_data))
            for row_idx, row in enumerate(stocks_data):
                stock_idx = row.get('stock_idx', 0)
                code = price_data.iloc[stock_idx, 0]
                name = price_data.iloc[stock_idx, 1]
                table2.setItem(row_idx, 0, QTableWidgetItem(str(code)))
                table2.setItem(row_idx, 1, QTableWidgetItem(str(name)))
                valid_arr = row.get('valid_sum_arr', [])
                for col_idx in range(max_valid_len):
                    val = valid_arr[col_idx] if col_idx < len(valid_arr) else ""
                    table2.setItem(row_idx, 2 + col_idx, QTableWidgetItem(str(val)))
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
                    table2.setItem(row_idx, 2 + max_valid_len + i, QTableWidgetItem(str(val)))

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
                forward_param_values = [
                    row.get('forward_max_valid_sum_len', ''),
                    row.get('forward_max_valid_sum_arr', ''),
                    row.get('forward_max_valid_pos_sum', ''),
                    row.get('forward_max_valid_neg_sum', ''),
                    row.get('forward_max_valid_abs_sum_first_half', ''),
                    row.get('forward_max_valid_abs_sum_second_half', ''),
                    row.get('forward_max_valid_abs_sum_block1', ''),
                    row.get('forward_max_valid_abs_sum_block2', ''),
                    row.get('forward_max_valid_abs_sum_block3', ''),
                    row.get('forward_max_valid_abs_sum_block4', ''),
                ]
                for i, val in enumerate(forward_param_values):
                    table3.setItem(row_idx, 3 + max_forward_len + i, QTableWidgetItem(str(val)))

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
                forward_min_param_values = [
                    row.get('forward_min_valid_sum_len', ''),
                    row.get('forward_min_valid_sum_arr', ''),
                    row.get('forward_min_valid_pos_sum', ''),
                    row.get('forward_min_valid_neg_sum', ''),
                    row.get('forward_min_valid_abs_sum_first_half', ''),
                    row.get('forward_min_valid_abs_sum_second_half', ''),
                    row.get('forward_min_valid_abs_sum_block1', ''),
                    row.get('forward_min_valid_abs_sum_block2', ''),
                    row.get('forward_min_valid_abs_sum_block3', ''),
                    row.get('forward_min_valid_abs_sum_block4', ''),
                ]
                for i, val in enumerate(forward_min_param_values):
                    table4.setItem(row_idx, 3 + max_forward_min_len + i, QTableWidgetItem(str(val)))

            # 设置表格列宽自适应
            table1.resizeColumnsToContents()
            table2.resizeColumnsToContents()
            table3.resizeColumnsToContents()
            table4.resizeColumnsToContents()

            # 设置表头样式
            for table in [table1, table2, table3, table4]:
                table.horizontalHeader().setFixedHeight(50)
                table.horizontalHeader().setStyleSheet("font-size: 12px;")

        # 初始化表格内容
        update_tables(stocks_data)

        tab_widget.addTab(table1, f"连续累加值 ({end_date})")
        tab_widget.addTab(table2, f"有效累加值 ({end_date})")
        tab_widget.addTab(table3, f"向前最大连续累加值 ({end_date})")
        tab_widget.addTab(table4, f"向前最小连续累加值 ({end_date})")

        # 添加日期选择框
        date_picker = QDateEdit(parent)
        date_picker.setDisplayFormat("yyyy-MM-dd")
        date_picker.setCalendarPopup(True)
        date_list = [d['end_date'] for d in dates]
        date_picker.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
        date_picker.setFixedWidth(180)
        date_picker.setStyleSheet("font-size: 12px; height: 20px;")

        # 顶部布局
        top_layout = QHBoxLayout()
        top_layout.addStretch(1)
        top_layout.addWidget(QLabel("选择结束日期："))
        top_layout.addWidget(date_picker)

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(tab_widget)

        if as_widget:
            container = QWidget(parent)
            container.setLayout(main_layout)
            container.setMinimumSize(1200, 600)
            container.show()

            # 切换日期时刷新所有表格内容
            def on_date_changed():
                selected_date = date_picker.date().toString("yyyy-MM-dd")
                for d in dates:
                    if d['end_date'] == selected_date:
                        stocks_data = d['stocks']
                        break
                # 按stock_idx排序
                stocks_data = sorted(stocks_data, key=lambda row: row.get('stock_idx', 0))
                # 更新所有表格
                update_tables(stocks_data)
                # 更新tab标签
                tab_widget.setTabText(0, f"连续累加值 ({selected_date})")
                tab_widget.setTabText(1, f"有效累加值 ({selected_date})")
                tab_widget.setTabText(2, f"向前最大连续累加值 ({selected_date})")
                tab_widget.setTabText(3, f"向前最小连续累加值 ({selected_date})")

            date_picker.dateChanged.connect(on_date_changed)
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
                f"最大值=({row['max_value'][0]}, {row['max_value'][1]})，"
                f"最小值=({row['min_value'][0]}, {row['min_value'][1]})，"
                f"结束值=({row['end_value'][0]}, {row['end_value'][1]})，"
                f"开始值=({row['start_value'][0]}, {row['start_value'][1]})，"
                f"实际开始日期值=({row['actual_value'][0]}, {row['actual_value'][1]})，"
                f"最接近值=({row['closest_value'][0]}, {row['closest_value'][1]})，"
                f"前1组结束地址前{n_days}日的最高值：{row.get('n_max_value', '无')}，"
                f"前N最大值：{row.get('n_max_is_max', '无')}，"
                f"开始日到结束日之间最高价/最低价小于M：{row.get('range_ratio_is_less', '无')}，"
                f"开始日到结束日之间连续累加值绝对值小于：{row.get('abs_sum_is_less', '无')}，"
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
                f"有效累加值第一块绝对值之和：{row.get('valid_abs_sum_block1', '无')}, "
                f"有效累加值第二块绝对值之和：{row.get('valid_abs_sum_block2', '无')}, "
                f"有效累加值第三块绝对值之和：{row.get('valid_abs_sum_block3', '无')}, "
                f"有效累加值第四块绝对值之和：{row.get('valid_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"向前最大日期={row['forward_max_date']}，向前最大连续累加值={row['forward_max_result']}，"
                f"向前最大有效累加值数组长度：{row.get('forward_max_valid_sum_len', '无')}, "
                f"向前最大有效累加值：{row.get('forward_max_valid_sum_arr', '无')}, "
                f"向前最大有效累加值正加值和：{row.get('forward_max_valid_pos_sum', '无')}, "
                f"向前最大有效累加值负加值和：{row.get('forward_max_valid_neg_sum', '无')}, "
                f"向前最大有效累加值数组前一半绝对值之和：{row.get('forward_max_valid_abs_sum_first_half', '无')}, "
                f"向前最大有效累加值数组后一半绝对值之和：{row.get('forward_max_valid_abs_sum_second_half', '无')}, "
                f"向前最大有效累加值数组第一块绝对值之和：{row.get('forward_max_valid_abs_sum_block1', '无')}, "
                f"向前最大有效累加值数组第二块绝对值之和：{row.get('forward_max_valid_abs_sum_block2', '无')}, "
                f"向前最大有效累加值数组第三块绝对值之和：{row.get('forward_max_valid_abs_sum_block3', '无')}, "
                f"向前最大有效累加值数组第四块绝对值之和：{row.get('forward_max_valid_abs_sum_block4', '无')}, "
                f"\n"
                f"\n"
                f"向前最小日期={row['forward_min_date']}，向前最小连续累加值={row['forward_min_result']}，"
                f"向前最小有效累加值数组长度：{row.get('forward_min_valid_sum_len', '无')}, "
                f"向前最小有效累加值：{row.get('forward_min_valid_sum_arr', '无')}, "
                f"向前最小有效累加值正加值和：{row.get('forward_min_valid_pos_sum', '无')}, "
                f"向前最小有效累加值负加值和：{row.get('forward_min_valid_neg_sum', '无')}, "
                f"向前最小有效累加值数组前一半绝对值之和：{row.get('forward_min_valid_abs_sum_first_half', '无')}, "
                f"向前最小有效累加值数组后一半绝对值之和：{row.get('forward_min_valid_abs_sum_second_half', '无')}, "
                f"向前最小有效累加值数组第一块绝对值之和：{row.get('forward_min_valid_abs_sum_block1', '无')}, "
                f"向前最小有效累加值数组第二块绝对值之和：{row.get('forward_min_valid_abs_sum_block2', '无')}, "
                f"向前最小有效累加值数组第三块绝对值之和：{row.get('forward_min_valid_abs_sum_block3', '无')}, "
                f"向前最小有效累加值数组第四块绝对值之和：{row.get('forward_min_valid_abs_sum_block4', '无')}, "
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

def show_params_table(parent, all_results, n_days=0, range_value=None, abs_sum_value=None, as_widget=False):
    if not all_results or not all_results.get("dates"):
        QMessageBox.information(parent, "提示", "请先生成参数！")
        return None

    # 获取最后一个end_date的数据
    dates = all_results.get("dates", [])
    if not dates:
        QMessageBox.information(parent, "提示", "没有可用的日期数据！")
        return None

    last_date_data = dates[-1]
    end_date = last_date_data.get("end_date")
    stocks_data = last_date_data.get("stocks", [])

    if not stocks_data:
        QMessageBox.information(parent, "提示", f"日期 {end_date} 没有股票数据！")
        return None

    dialog = QDialog()
    dialog.setWindowTitle("参数明细")
    layout = QVBoxLayout(dialog)
    label = QLabel("参数明细")
    layout.addWidget(label)

    headers = [
        '代码', '名称', '最大值', '最小值', '结束值', '开始值', '实际开始日期值', '最接近值',
        f'前1组结束地址前{n_days}日的最高值', '前N最大值',
        f'开始日到结束日之间最高价/最低价小于{range_value}',
        f'开始日到结束日之间连续累加值绝对值小于{abs_sum_value}',
        '前1组结束地址前1日涨跌幅', '前1组结束日涨跌幅', '后1组结束地址值',
        '递增值', '后值大于结束地址值', '后值大于前值返回值', '操作值', '持有天数', '操作涨幅', '调整天数', '日均涨幅'
    ]
    table = QTableWidget(len(stocks_data), len(headers))
    table.setHorizontalHeaderLabels(headers)

    def get_val(val):
        # 如果是元组或列表，取第2个元素（数值部分），否则原样返回
        if isinstance(val, (list, tuple)) and len(val) > 1:
            val = val[1]
        # None或nan都返回空字符串
        if val is None or val == '' or (isinstance(val, float) and math.isnan(val)):
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

    for row_idx, row in enumerate(stocks_data):
        table.setItem(row_idx, 0, QTableWidgetItem(str(get_val(row.get('code', '')))))
        table.setItem(row_idx, 1, QTableWidgetItem(str(get_val(row.get('name', '')))))
        table.setItem(row_idx, 2, QTableWidgetItem(str(get_val(row.get('max_value', '')))))
        table.setItem(row_idx, 3, QTableWidgetItem(str(get_val(row.get('min_value', '')))))
        table.setItem(row_idx, 4, QTableWidgetItem(str(get_val(row.get('end_value', '')))))
        table.setItem(row_idx, 5, QTableWidgetItem(str(get_val(row.get('start_value', '')))))
        table.setItem(row_idx, 6, QTableWidgetItem(str(get_val(row.get('actual_value', '')))))
        table.setItem(row_idx, 7, QTableWidgetItem(str(get_val(row.get('closest_value', '')))))
        table.setItem(row_idx, 8, QTableWidgetItem(str(get_val(row.get('n_max_value', '')))))
        table.setItem(row_idx, 9, QTableWidgetItem(get_bool(row.get('n_max_is_max', ''))))
        table.setItem(row_idx, 10, QTableWidgetItem(get_bool(row.get('range_ratio_is_less', ''))))
        table.setItem(row_idx, 11, QTableWidgetItem(get_bool(row.get('abs_sum_is_less', ''))))
        table.setItem(row_idx, 12, QTableWidgetItem(get_percent(row.get('prev_day_change', ''))))
        table.setItem(row_idx, 13, QTableWidgetItem(get_percent(row.get('end_day_change', ''))))
        table.setItem(row_idx, 14, QTableWidgetItem(str(get_val(row.get('diff_end_value', '')))))
        table.setItem(row_idx, 15, QTableWidgetItem(str(get_val(row.get('increment_value', '')))))
        table.setItem(row_idx, 16, QTableWidgetItem(str(get_val(row.get('after_gt_end_value', '')))))
        table.setItem(row_idx, 17, QTableWidgetItem(str(get_val(row.get('after_gt_start_value', '')))))
        table.setItem(row_idx, 18, QTableWidgetItem(str(get_val(row.get('ops_value', '')))))
        table.setItem(row_idx, 19, QTableWidgetItem(str(get_val(row.get('hold_days', '')))))
        table.setItem(row_idx, 20, QTableWidgetItem(get_percent(row.get('ops_change', ''))))
        table.setItem(row_idx, 21, QTableWidgetItem(str(get_val(row.get('adjust_days', '')))))
        table.setItem(row_idx, 22, QTableWidgetItem(get_percent(row.get('ops_incre_rate', ''))))

    if as_widget:
        return table  # 直接返回QTableWidget
    else:
        dialog = QDialog()
        dialog.setWindowTitle("参数明细")
        layout = QVBoxLayout(dialog)
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.resize(1800, 500)
        dialog.show()
        return dialog
    
class FormulaExprEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setPlaceholderText("点击输入/编辑选股公式")
        self.setFixedSize(200, 25)  # 宽200，高25

    def mousePressEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑选股公式")
        dialog.resize(1000, 750)  # 设置弹窗大小
        layout = QVBoxLayout(dialog)
        tip_label = QLabel(
            "示例:\n"
            "if (\n"
            "    abs(CEV) < 3 and\n"
            "    abs(CEPV) < 3 and\n"
            "    abs(CEPPV) < 3000 and\n"
            "    abs(NMAX) < 3000 and\n"
            "    abs(CSV) > 150 and\n"
            "    abs(CEPV) > 0 and\n"
            "    abs(CEPPV) > 0 and\n"
            "    CASFH > 3 * CASSH\n"
            "):\n"
            "    result = VNS + VPS\n"
            "else:\n"
            "    result = 0\n"
            "\n"
        )
        tip_label.setStyleSheet("color:gray; background-color: #f0f0f0; border-radius: 4px;")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.toPlainText())
        layout.addWidget(text_edit)
        btn_ok = QPushButton("确定")
        layout.addWidget(btn_ok)
        def on_ok():
            expr_text = text_edit.toPlainText()
            try:
                compile(expr_text, '<string>', 'exec')
                self.setText(expr_text)
                dialog.accept()
            except SyntaxError as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(dialog, "语法错误", f"表达式存在语法错误，请检查！\n\n{e}")
        btn_ok.clicked.connect(on_ok)
        dialog.exec_()


def show_formula_select_table(parent, all_results, as_widget=True):
    if not all_results or not all_results.get("dates"):
        QMessageBox.information(parent, "提示", "请先生成参数！")
        return None

    # 获取最后一个end_date的数据
    dates = all_results.get("dates", [])
    if not dates:
        QMessageBox.information(parent, "提示", "没有可用的日期数据！")
        return None

    last_date_data = dates[-1]
    end_date = last_date_data.get("end_date")
    stocks_data = last_date_data.get("stocks", [])

    if not stocks_data:
        QMessageBox.information(parent, "提示", f"日期 {end_date} 没有股票数据！")
        return None

    widget = QWidget(parent)
    widget.setStyleSheet("background-color: white; border: 1px solid #d0d0d0;")  # 设置白色背景和浅灰边框
    layout = QVBoxLayout(widget)

    # 顶部公式输入区
    top_layout = QHBoxLayout()
    formula_label = QLabel("选股公式:")
    formula_label.setStyleSheet("border: none;")
    top_layout.addWidget(formula_label)
    formula_input = FormulaExprEdit()
    top_layout.addWidget(formula_input, 3)

    select_count_label = QLabel("选股数量:")
    select_count_label.setStyleSheet("border: none;")  # 去掉边框
    select_count_spin = QSpinBox()
    select_count_spin.setMinimum(1)
    select_count_spin.setMaximum(100)
    select_count_spin.setValue(10)
    sort_label = QLabel("排序方式:")
    sort_label.setStyleSheet("border: none;")  # 去掉边框
    sort_combo = QComboBox()
    sort_combo.addItems(["最大值排序", "最小值排序"])
    select_btn = QPushButton("进行选股")
    select_btn.setFixedSize(100, 50)
    select_btn.setStyleSheet("background-color: #f0f0f0; border: none;")  # 设置与主界面一致的背景色
    result_btn = QPushButton("查看结果")
    result_btn.setFixedSize(100, 50)
    result_btn.setStyleSheet("background-color: #f0f0f0; border: none;")  # 设置与主界面一致的背景色
    for w in [select_count_label, select_count_spin, sort_label, sort_combo, select_btn, result_btn]:
        top_layout.addWidget(w)
    layout.addLayout(top_layout)

    # 缩写说明区（表格排列，每行5列）
    abbrs = [
        ("前N最大值", "NMAX"), ("前N最大值是否区间最大", "NMAXISMAX"), ("前1组结束日涨跌幅", "EDC"), ("后一组结束地址值", "DEV"), ("区间比值", "RRL"),
        ("绝对值", "ASL"), ("连续累加值开始值", "CSV"), ("连续累加值开始后1位值", "CSNV"), ("连续累加值结束值", "CEV"), ("连续累加值结束前1位值", "CEPV"),
        ("连续累加值结束前2位值", "CEPPV"), ("连续累加值长度", "CL"), ("连续累加值前一半绝对值之和", "CASFH"), ("连续累加值后一半绝对值之和", "CASSH"), ("连续累加值前四分之一绝对值之和", "CASB1"),
        ("连续累加值前四分之二绝对值之和", "CASB2"), ("连续累加值前四分之三绝对值之和", "CASB3"), ("连续累加值后四分之一绝对值之和", "CASB4"), ("有效累加值正加值和", "VPS"), ("有效累加值负加值和", "VNS"),
        ("有效累加值数组长度", "VSL"), ("有效累加值前一半绝对值之和", "VASFH"), ("有效累加值后一半绝对值之和", "VASSH"), ("有效累加值第一块绝对值之和", "VASB1"), ("有效累加值第二块绝对值之和", "VASB2"),
        ("有效累加值第三块绝对值之和", "VASB3"), ("有效累加值第四块绝对值之和", "VASB4"), ("向前最大日期", "FMD"), ("向前最大连续累加值", "FMR"), ("向前最大有效累加值数组长度", "FMVSL"),
        ("向前最大有效累加值正加值和", "FMVPS"), ("向前最大有效累加值负加值和", "FMVNS"), ("向前最大有效累加值数组前一半绝对值之和", "FMVASFH"), ("向前最大有效累加值数组后一半绝对值之和", "FMVASSH"), ("向前最大有效累加值数组第一块绝对值之和", "FMVASB1"),
        ("向前最大有效累加值数组第二块绝对值之和", "FMVASB2"), ("向前最大有效累加值数组第三块绝对值之和", "FMVASB3"), ("向前最大有效累加值数组第四块绝对值之和", "FMVASB4"), ("递增值", "INC"), ("后值大于结束地址值", "AGE"),
        ("后值大于前值", "AGS"), ("操作值", "OPS"), ("持有天数", "HD"), ("操作涨幅", "OPC"), ("调整天数", "ADJ"), ("日均涨幅", "OIR")
    ]
    abbr_grid = QGridLayout()
    abbr_grid.setSpacing(8)
    for idx, (zh, en) in enumerate(abbrs):
        row = idx // 5
        col = idx % 5
        label = QLabel(f"{zh} ({en})")
        label.setStyleSheet('color:gray;')
        abbr_grid.addWidget(label, row, col)
    abbr_widget = QWidget()
    abbr_widget.setLayout(abbr_grid)
    layout.addWidget(abbr_widget)

    # 输出区（用于提示和结果展示）
    output_edit = QTextEdit()
    output_edit.setReadOnly(True)
    output_edit.setMinimumHeight(180)
    layout.addWidget(output_edit)

    # 选股结果缓存
    widget.selected_results = []
    widget.select_thread = None

    # 选股逻辑
    def do_select():
        formula_expr = formula_input.toPlainText()
        if not formula_expr:
            output_edit.setText("请输入选股公式！")
            return

        try:
            # 编译表达式以检查语法
            compile(formula_expr, '<string>', 'exec')
        except SyntaxError as e:
            output_edit.setText(f"公式语法错误：{e}")
            return

        select_count = select_count_spin.value()
        sort_type = sort_combo.currentText()

        # 创建选股线程
        class SelectThread(QThread):
            finished = pyqtSignal(list)

            def __init__(self, stocks_data, formula_expr, select_count, sort_type):
                super().__init__()
                self.stocks_data = stocks_data
                self.formula_expr = formula_expr
                self.select_count = select_count
                self.sort_type = sort_type

            def run(self):
                selected = []
                for row in self.stocks_data:
                    try:
                        # 创建局部变量字典
                        local_vars = {
                            'NMAX': row.get('n_max_value', 0),
                            'NMAXISMAX': row.get('n_max_is_max', False),
                            'EDC': row.get('end_day_change', 0),
                            'DEV': row.get('diff_end_value', 0),
                            'RRL': row.get('range_ratio_is_less', False),
                            'ASL': row.get('abs_sum_is_less', False),
                            'CSV': row.get('continuous_start_value', 0),
                            'CSNV': row.get('continuous_start_next_value', 0),
                            'CEV': row.get('continuous_end_value', 0),
                            'CEPV': row.get('continuous_end_prev_value', 0),
                            'CEPPV': row.get('continuous_end_prev_prev_value', 0),
                            'CL': row.get('continuous_len', 0),
                            'CASFH': row.get('continuous_abs_sum_first_half', 0),
                            'CASSH': row.get('continuous_abs_sum_second_half', 0),
                            'CASB1': row.get('continuous_abs_sum_block1', 0),
                            'CASB2': row.get('continuous_abs_sum_block2', 0),
                            'CASB3': row.get('continuous_abs_sum_block3', 0),
                            'CASB4': row.get('continuous_abs_sum_block4', 0),
                            'VPS': row.get('valid_pos_sum', 0),
                            'VNS': row.get('valid_neg_sum', 0),
                            'VSL': row.get('valid_sum_len', 0),
                            'VASFH': row.get('valid_abs_sum_first_half', 0),
                            'VASSH': row.get('valid_abs_sum_second_half', 0),
                            'VASB1': row.get('valid_abs_sum_block1', 0),
                            'VASB2': row.get('valid_abs_sum_block2', 0),
                            'VASB3': row.get('valid_abs_sum_block3', 0),
                            'VASB4': row.get('valid_abs_sum_block4', 0),
                            'FMD': row.get('forward_max_date', ''),
                            'FMR': row.get('forward_max_result', []),
                            'FMVSL': row.get('forward_max_valid_sum_len', 0),
                            'FMVPS': row.get('forward_max_valid_pos_sum', 0),
                            'FMVNS': row.get('forward_max_valid_neg_sum', 0),
                            'FMVASFH': row.get('forward_max_valid_abs_sum_first_half', 0),
                            'FMVASSH': row.get('forward_max_valid_abs_sum_second_half', 0),
                            'FMVASB1': row.get('forward_max_valid_abs_sum_block1', 0),
                            'FMVASB2': row.get('forward_max_valid_abs_sum_block2', 0),
                            'FMVASB3': row.get('forward_max_valid_abs_sum_block3', 0),
                            'FMVASB4': row.get('forward_max_valid_abs_sum_block4', 0),
                            'INC': row.get('increment_value', 0),
                            'AGE': row.get('after_gt_end_value', 0),
                            'AGS': row.get('after_gt_start_value', 0),
                            'OPS': row.get('ops_value', 0),
                            'HD': row.get('hold_days', 0),
                            'OPC': row.get('ops_change', 0),
                            'ADJ': row.get('adjust_days', 0),
                            'OIR': row.get('ops_incre_rate', 0),
                            'result': None
                        }

                        # 执行公式
                        exec(self.formula_expr, {}, local_vars)
                        score = local_vars['result']

                        if score is not None and score != 0:
                            selected.append({
                                'code': row.get('code', ''),
                                'name': row.get('name', ''),
                                'hold_days': row.get('hold_days', 0),
                                'ops_change': row.get('ops_change', 0),
                                'ops_incre_rate': row.get('ops_incre_rate', 0),
                                'score': score
                            })
                    except Exception as e:
                        print(f"处理股票 {row.get('code', '')} 时出错：{e}")
                        continue

                # 根据分数排序
                selected.sort(key=lambda x: x['score'], reverse=True)
                # 根据排序方式调整
                if self.sort_type == "最小值排序":
                    selected.reverse()
                # 截取指定数量
                selected = selected[:self.select_count]
                self.finished.emit(selected)

        def on_finished(selected):
            widget.selected_results = selected
            output_edit.setText(f"选股完成，共选出 {len(selected)} 只股票")

        # 创建并启动线程
        widget.select_thread = SelectThread(stocks_data, formula_expr, select_count, sort_type)
        widget.select_thread.finished.connect(on_finished)
        widget.select_thread.start()
        output_edit.setText("正在选股，请稍候...")

    def show_selected():
        selected = getattr(widget, 'selected_results', [])
        if not selected:
            output_edit.setText("请先进行选股！")
            return
        # 构造表格文本
        headers = ["代码", "名称", "持有天数", "操作涨幅", "日均涨幅", "得分"]
        lines = ["\t".join(headers)]
        for row in selected:
            line = "\t".join(str(row.get(k, "")) for k in ["code", "name", "hold_days", "ops_change", "ops_incre_rate", "score"])
            lines.append(line)
        output_edit.setText("\n".join(lines))

    select_btn.clicked.connect(do_select)
    result_btn.clicked.connect(show_selected)

    return widget

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