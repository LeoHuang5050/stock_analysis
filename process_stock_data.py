import pandas as pd
import numpy as np

# 连续累加值计算
def calc_continuous_sum_np(arr, columns, start_date, end_date):
    """
    arr: 一行数据（Series 或 1D array）
    columns: 该行对应的列名（顺序与arr一致）
    start_date, end_date: 字符串，格式与表头一致
    返回：连续累加值列表（从右往左）
    """
    # 找到起止日期的列索引
    try:
        start_idx = columns.get_loc(start_date)
        end_idx = columns.get_loc(end_date)
    except Exception as e:
        print(f"找不到指定日期列：{e}")
        return []

    if start_idx <= end_idx:
        print(f"起始日期 {start_date} 必须在结束日期 {end_date} 的右侧（即更靠近表格右边）！")
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

def find_column_by_date(columns, date_str):
    # 返回第一个包含date_str的列名
    for col in columns:
        if date_str in str(col):
            return col
    raise ValueError(f"未找到包含 {date_str} 的列名")

def unify_date_columns(df):
    new_columns = []
    for col in df.columns:
        col_str = str(col)
        # 只处理形如 yyyy-mm-dd 的日期列
        if col_str[:4].isdigit() and '-' in col_str:
            new_columns.append(col_str[:10])
        else:
            new_columns.append(col_str)
    df.columns = new_columns
    return df

def process_stock_data():
    # 读取Excel文件
    # pd.read_excel('data.xlsx').to_csv('data.csv', index=False)
    pd.set_option('display.precision', 15)
    # pd.read_excel('data.xlsx')
    # df = pd.read_csv('data.csv')
    df = pd.read_excel('data.xlsx')    

    # 获取列名
    columns = df.columns.tolist()
    
    # 找到分隔列（空列）的索引
    separator_idx = None
    for i, col in enumerate(columns):
        if (pd.isna(col) or col == '' or str(col).startswith('Unnamed')):
            separator_idx = i
            break
    
    if separator_idx is None:
        raise ValueError("未找到分隔列")
    
    # 分割数据
    price_data = df.iloc[:, :separator_idx]
    diff_data = df.iloc[:, separator_idx+1:]

    # 统一日期列名
    price_data = unify_date_columns(price_data)
    diff_data = unify_date_columns(diff_data)
    
    # 打印每组数据的第一行内容
    print("价格数据第一行：")
    print(price_data.iloc[0])
    print("\n差价数据第一行：")
    print(diff_data.iloc[0])

    # 后续可以直接在内存中使用 price_data 和 diff_data 进行计算
    # 只保留数值型列（自动跳过代码、名称等非数值列）
    # 假设你要用2024-10-9到2024-10-20
    start_date = '2024-10-09'
    end_date = '2024-12-31'

    # 这里假设所有日期列都是数值型列
    for idx, row in diff_data.iterrows():
        result = calc_continuous_sum_np(row, diff_data.columns, start_date, end_date)
        print(f"第{idx+1}行从{end_date}到{start_date}的连续累加值：", result)

if __name__ == "__main__":
    process_stock_data() 