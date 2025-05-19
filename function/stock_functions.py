import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta
from decimal import Decimal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QLineEdit, QSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy, QDialog, QTabWidget, QMessageBox, QGridLayout

import math

def show_continuous_sum_table(parent, all_results, as_widget=False):
    try:
        if not all_results:
            print("all_results 为空，return None")
            if not as_widget:
                QMessageBox.information(parent, "提示", "请先生成参数！")
            return None

        tab_widget = QTabWidget(parent)  # 直接以parent为父
        # 统计最大长度
        max_len = max(len(row.get('continuous_results', [])) for row in all_results)
        max_valid_len = max(len(row.get('valid_sum_arr', [])) for row in all_results)
        max_forward_len = max(len(row.get('forward_max_result', [])) for row in all_results)
        max_forward_min_len = max(len(row.get('forward_min_result', [])) for row in all_results)
        n_val = max(max_len, max_valid_len, max_forward_len, max_forward_min_len)

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

        # 连续累加值tab
        headers1 = ['代码', '名称', '实际开始日期值', '计算开始日期'] + [f'连续累加值{i+1}' for i in range(max_len)] + param_headers
        table1 = QTableWidget(len(all_results), len(headers1))
        table1.setHorizontalHeaderLabels(headers1)

        for row_idx, row in enumerate(all_results):
            table1.setItem(row_idx, 0, QTableWidgetItem(str(row.get('code', ''))))
            table1.setItem(row_idx, 1, QTableWidgetItem(str(row.get('name', ''))))
            actual_value = row.get('actual_value', [None, None])
            start_value = row.get('start_value', [None, None])
            table1.setItem(row_idx, 2, QTableWidgetItem(str(actual_value[1]) if actual_value else ''))
            table1.setItem(row_idx, 3, QTableWidgetItem(str(start_value[0]) if start_value else ''))
            results = row.get('continuous_results', [])
            for col_idx in range(max_len):
                val = results[col_idx] if col_idx < len(results) else ""
                table1.setItem(row_idx, 4 + col_idx, QTableWidgetItem(str(val)))
            param_values = [
                row.get('continuous_len', ''),
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

        # 有效累加值tab
        headers2 = ['代码', '名称'] + [f'有效累加值{i+1}' for i in range(max_valid_len)] + valid_param_headers
        table2 = QTableWidget(len(all_results), len(headers2))
        table2.setHorizontalHeaderLabels(headers2)

        for row_idx, row in enumerate(all_results):
            table2.setItem(row_idx, 0, QTableWidgetItem(str(row.get('code', ''))))
            table2.setItem(row_idx, 1, QTableWidgetItem(str(row.get('name', ''))))
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

        # 向前最大连续累加值tab
        headers3 = ['代码', '名称', '向前最大日期'] + [f'向前最大连续累加值{i+1}' for i in range(max_forward_len)] + [h for h in forward_param_headers if h != "向前最大日期"]
        table3 = QTableWidget(len(all_results), len(headers3))
        table3.setHorizontalHeaderLabels(headers3)

        for row_idx, row in enumerate(all_results):
            table3.setItem(row_idx, 0, QTableWidgetItem(str(row.get('code', ''))))
            table3.setItem(row_idx, 1, QTableWidgetItem(str(row.get('name', ''))))
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

        # 向前最小连续累加值tab
        headers4 = ['代码', '名称', '向前最小日期'] + [f'向前最小连续累加值{i+1}' for i in range(max_forward_min_len)] + [h for h in forward_min_param_headers if h != "向前最小日期"]
        table4 = QTableWidget(len(all_results), len(headers4))
        table4.setHorizontalHeaderLabels(headers4)

        for row_idx, row in enumerate(all_results):
            table4.setItem(row_idx, 0, QTableWidgetItem(str(row.get('code', ''))))
            table4.setItem(row_idx, 1, QTableWidgetItem(str(row.get('name', ''))))
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

        tab_widget.addTab(table1, "连续累加值")
        tab_widget.addTab(table2, "有效累加值")
        tab_widget.addTab(table3, "向前最大连续累加值")
        tab_widget.addTab(table4, "向前最小连续累加值")

        table1.resizeColumnsToContents()
        table2.resizeColumnsToContents()
        table3.resizeColumnsToContents()
        table4.resizeColumnsToContents()

        if as_widget:
            tab_widget.setMinimumSize(1200, 600)
            tab_widget.show()
            return tab_widget
        else:
            dialog = QWidget()
            layout = QVBoxLayout(dialog)
            layout.addWidget(tab_widget)
            dialog.setLayout(layout)
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
    """
    arr: 一行数据（Series 或 1D array）
    columns: 该行对应的列名（顺序与arr一致）
    start_idx, end_idx: 均为索引，允许相等
    返回：连续累加值列表（从右往左）
    """
    if start_idx < end_idx:
        print(f"起始索引 {start_idx} 必须在结束索引 {end_idx} 的右侧（即更靠近表格右边）！")
        return []
    if start_idx == end_idx:
        return [round(float(arr[start_idx]), 2)]  # 只返回该列的单个值，保留两位小数
    # 只允许从右往左（从end_idx到start_idx，包含两端）
    arr_slice = arr[end_idx:start_idx+1][::-1]
    arr_slice = [float(v) for v in arr_slice]
    result = []
    if len(arr_slice) == 0:
        return result
    temp_sum = arr_slice[0]
    sign = arr_slice[0] >= 0
    for v in arr_slice[1:]:
        if (v >= 0) == sign:
            temp_sum += v
        else:
            result.append(round(temp_sum, 2))  # 保留两位小数
            temp_sum = v
            sign = v >= 0
    result.append(round(temp_sum, 2))  # 保留两位小数
    return result

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
    if not all_results:
        QMessageBox.information(parent, "提示", "请先生成参数！")
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
    table = QTableWidget(len(all_results), len(headers))
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

    for row_idx, row in enumerate(all_results):
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
        select_count = select_count_spin.value()
        sort_mode = sort_combo.currentText()
        output_edit.setText("正在选股...")
        from worker_threads import SelectStockThread
        thread = SelectStockThread(all_results, formula_expr, select_count, sort_mode)
        widget.select_thread = thread  # 防止被回收
        def on_finished(selected):
            widget.selected_results = selected
            output_edit.setText("选股完成！")
        thread.finished.connect(on_finished)
        thread.start()

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