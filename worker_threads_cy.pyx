# cython: boundscheck=False, wraparound=False, cdivision=True
import numpy as np
cimport numpy as np

def calculate_batch_cy(
    np.ndarray[np.float64_t, ndim=2] price_data,
    list date_columns,
    int width,
    str start_option,
    int shift_days,
    int end_date_start_idx,
    int end_date_end_idx,
    np.ndarray[np.float64_t, ndim=2] diff_data,
    np.ndarray[np.int32_t, ndim=1] stock_idx_arr
):
    cdef int num_stocks = price_data.shape[0]
    cdef int num_dates = price_data.shape[1]
    cdef int stock_idx, idx, end_date_idx, start_date_idx
    cdef double max_price, min_price, new_value, old_value, end_value, start_value, actual_value, closest_value
    cdef int max_idx_in_window, min_idx_in_window, closest_idx_in_window
    cdef int i, window_len, base_idx, actual_idx
    cdef np.ndarray[np.float64_t, ndim=1] price_slice
    cdef np.ndarray[np.float64_t, ndim=1] diff_slice
    cdef dict all_results = {}
    cdef object max_date, min_date, start_date, end_date, code, name, actual_date, closest_date
    cdef int n
    cdef list cont_sum = []
    cdef double cur_sum = 0
    cdef double last_sign = 0
    cdef list prev_cont_sum = None
    cdef int prev_start = -1
    cdef int prev_end = -1

    # 初始化结果字典，为每个end_date创建空列表
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        all_results[end_date] = []

    for i in range(stock_idx_arr.shape[0]):
        stock_idx = stock_idx_arr[i]
        global_idx = stock_idx
        max_price = min_price = np.nan
        max_idx_in_window = min_idx_in_window = -1
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            end_date_idx = idx
            end_date = date_columns[end_date_idx]
            start_date_idx = end_date_idx + width
            start_date = date_columns[start_date_idx]
            price_slice = price_data[stock_idx, end_date_idx:start_date_idx+1]
            window_len = price_slice.shape[0]
            if window_len == 0 or np.isnan(price_slice).all():
                max_price = min_price = np.nan
                max_idx_in_window = min_idx_in_window = -1
            else:
                max_price = np.nanmax(price_slice)
                min_price = np.nanmin(price_slice)
                max_idx_in_window = int(np.where(price_slice == max_price)[0][0])
                min_idx_in_window = int(np.where(price_slice == min_price)[0][0])
            end_value = price_data[stock_idx, end_date_idx]
            start_value = price_data[stock_idx, start_date_idx]
            # 最接近值
            if np.isnan(end_value):
                closest_value = np.nan
                closest_idx_in_window = -1
            else:
                mask = ~np.isnan(price_slice)
                if mask.sum() > 0:
                    diffs = np.abs(price_slice[mask] - end_value)
                    min_idx = np.argmin(diffs)
                    valid_indices = np.where(mask)[0]
                    closest_value = price_slice[mask][min_idx]
                    closest_idx_in_window = int(valid_indices[min_idx])
                else:
                    closest_value = np.nan
                    closest_idx_in_window = -1
            # 实际开始值索引
            if start_option == "最大值":
                base_idx = end_date_idx + max_idx_in_window if max_idx_in_window >= 0 else -1
            elif start_option == "最小值":
                base_idx = end_date_idx + min_idx_in_window if min_idx_in_window >= 0 else -1
            elif start_option == "接近值":
                base_idx = end_date_idx + closest_idx_in_window if closest_idx_in_window >= 0 else -1
            else:
                base_idx = start_date_idx
            actual_idx = base_idx - shift_days if base_idx >= 0 else -1
            actual_value = price_data[stock_idx, actual_idx] if actual_idx >= 0 and actual_idx < num_dates else np.nan
            # 全量计算连续累加值，修正切片方向
            if actual_idx >= 0 and actual_idx >= end_date_idx:
                diff_slice = diff_data[stock_idx, end_date_idx:actual_idx+1][::-1]
            else:
                diff_slice = np.array([])
            n = diff_slice.shape[0]
            cont_sum = []
            cur_sum = 0
            last_sign = 0
            for i in range(n):
                v = diff_slice[i]
                if np.isnan(v):
                    continue
                sign = 1 if v > 0 else (-1 if v < 0 else 0)
                if i == 0 or sign == last_sign or last_sign == 0:
                    cur_sum += v
                else:
                    cont_sum.append(round(cur_sum, 2))
                    cur_sum = v
                last_sign = sign
            if n > 0:
                cont_sum.append(round(cur_sum, 2))
            
            row_result = {
                'stock_idx': stock_idx,
                'max_value': [date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None, max_price],
                'min_value': [date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None, min_price],
                'end_value': [end_date, end_value],
                'start_value': [start_date, start_value],
                'actual_value': [date_columns[actual_idx] if actual_idx >= 0 and actual_idx < num_dates else None, actual_value],
                'closest_value': [date_columns[end_date_idx + closest_idx_in_window] if closest_idx_in_window >= 0 else None, closest_value],
                'continuous_results': cont_sum,
                'continuous_start_value': cont_sum[0] if len(cont_sum) > 0 else None,
                'continuous_start_next_value': cont_sum[1] if len(cont_sum) > 1 else None,
                'continuous_start_next_next_value': cont_sum[2] if len(cont_sum) > 2 else None,
                'continuous_end_value': cont_sum[len(cont_sum)-1] if len(cont_sum) > 0 else None,
                'continuous_end_prev_value': cont_sum[len(cont_sum)-2] if len(cont_sum) > 1 else None,
                'continuous_end_prev_prev_value': cont_sum[len(cont_sum)-3] if len(cont_sum) > 2 else None
            }
            
            # 将结果添加到对应end_date的列表中
            all_results[end_date].append(row_result)
    
    # 将字典转换为列表，保持end_date的顺序
    sorted_results = []
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        if end_date in all_results:
            sorted_results.append({
                'end_date': end_date,
                'stocks': all_results[end_date]
            })
    
    return sorted_results 