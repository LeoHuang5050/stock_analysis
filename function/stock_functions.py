import numpy as np
import pandas as pd
import chinese_calendar
from datetime import datetime, timedelta

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
    start_date, end_date: 字符串，格式与表头一致
    返回：连续累加值列表（从右往左）
    """

    if start_idx <= end_idx:
        print(f"起始日期 {start_idx} 必须在结束日期 {end_idx} 的右侧（即更靠近表格右边）！")
        return []

    # 只允许从右往左（从end_date到start_date，包含两端）
    arr_slice = arr[end_idx:start_idx+1][::-1]

    arr_slice = np.array(arr_slice, dtype=np.float64)
    result = []
    if arr_slice.size == 0:
        return result
    temp_sum = arr_slice[0]
    sign = arr_slice[0] >= 0
    for v in arr_slice[1:]:
        if (v >= 0) == sign:
            temp_sum += v
        else:
            result.append(temp_sum)
            temp_sum = v
            sign = v >= 0
    result.append(temp_sum)
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