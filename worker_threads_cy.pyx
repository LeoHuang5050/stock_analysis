# distutils: language = c++
# cython: boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False
# distutils: extra_compile_args = -fopenmp
# distutils: extra_link_args = -fopenmp

import numpy as np
cimport numpy as np
from cython.parallel import prange
from libc.math cimport isnan, fabs, round
from libcpp.vector cimport vector

ctypedef np.float64_t DTYPE_t
cdef double NAN = float('nan')

cdef inline double round_to_2(double x) nogil:
    return round(x * 100.0) / 100.0

cdef void calc_continuous_sum(
    double[:] diff_slice,
    vector[double]& cont_sum
) nogil:
    cdef int n = diff_slice.shape[0]
    cdef double cur_sum = 0
    cdef double last_sign = 0
    cdef double v, sign
    cdef int i
    
    cont_sum.clear()
    
    for i in range(n):
        v = diff_slice[i]
        if isnan(v):
            continue
        sign = 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)
        if i == 0 or sign == last_sign or last_sign == 0:
            cur_sum += v
        else:
            cont_sum.push_back(round_to_2(cur_sum))
            cur_sum = v
        last_sign = sign
    
    if n > 0:
        cont_sum.push_back(round_to_2(cur_sum))

cdef list calc_valid_sum(list arr):
    cdef int n = len(arr)
    cdef list valid_sum_arr = []
    if n == 0:
        return valid_sum_arr
    cdef list abs_arr = [abs(v) for v in arr]
    cdef list next_abs = abs_arr[1:] + [0]
    cdef int i
    for i in range(n):
        if i < n - 1 and next_abs[i] > abs_arr[i]:
            valid_sum_arr.append(arr[i])
        elif i < n - 1:
            valid_sum_arr.append(arr[i+1] if arr[i+1] >= 0 else -abs_arr[i+1])
        else:
            valid_sum_arr.append(arr[i])
    return valid_sum_arr

cdef tuple calc_pos_neg_sum(list arr):
    cdef double pos_sum = 0.0
    cdef double neg_sum = 0.0
    cdef double v
    for v in arr:
        if v > 0:
            pos_sum += v
        elif v < 0:
            neg_sum += v
    return round_to_2(pos_sum), round_to_2(neg_sum)

def calculate_batch_cy(
    np.ndarray[DTYPE_t, ndim=2] price_data,
    list date_columns,
    int width,
    str start_option,
    int shift_days,
    int end_date_start_idx,
    int end_date_end_idx,
    np.ndarray[DTYPE_t, ndim=2] diff_data,
    np.ndarray[np.int32_t, ndim=1] stock_idx_arr
):
    cdef int num_stocks = price_data.shape[0]
    cdef int num_dates = price_data.shape[1]
    cdef int stock_idx, idx, end_date_idx, start_date_idx
    cdef double max_price, min_price, end_value, start_value, actual_value, closest_value
    cdef int max_idx_in_window, min_idx_in_window, closest_idx_in_window
    cdef int i, j, window_len, base_idx, actual_idx
    cdef dict all_results = {}
    cdef vector[double] cont_sum
    cdef vector[double] forward_max_result_c, forward_min_result_c
    cdef double[:, :] price_data_view = price_data
    cdef double[:, :] diff_data_view = diff_data
    cdef int[:] stock_idx_arr_view = stock_idx_arr
    cdef double min_diff, diff
    cdef int n, half, q1, q2, q3
    cdef double continuous_abs_sum_first_half, continuous_abs_sum_second_half
    cdef double continuous_abs_sum_block1, continuous_abs_sum_block2, continuous_abs_sum_block3, continuous_abs_sum_block4
    
    # 初始化结果字典
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        all_results[end_date] = []
    
    # 并行处理每个股票
    for i in prange(stock_idx_arr_view.shape[0], nogil=True):
        stock_idx = stock_idx_arr_view[i]
        
        # 处理每个日期窗口
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            with gil:
                end_date = date_columns[idx]
                end_date_idx = idx
                start_date_idx = end_date_idx + width
                start_date = date_columns[start_date_idx]
                max_price = -1e308
                min_price = 1e308
                max_date = None
                min_date = None
            
            # 计算窗口内的最大最小值
            max_price = -1e308
            min_price = 1e308
            max_idx_in_window = -1
            min_idx_in_window = -1
            window_len = width + 1
            
            for j in range(window_len):
                if not isnan(price_data_view[stock_idx, end_date_idx + j]):
                    if price_data_view[stock_idx, end_date_idx + j] > max_price:
                        max_price = price_data_view[stock_idx, end_date_idx + j]
                        max_idx_in_window = j
                    if price_data_view[stock_idx, end_date_idx + j] < min_price:
                        min_price = price_data_view[stock_idx, end_date_idx + j]
                        min_idx_in_window = j
            
            with gil:
                if max_idx_in_window >= 0:
                    max_date = date_columns[end_date_idx + max_idx_in_window]
                else:
                    max_date = None
                if min_idx_in_window >= 0:
                    min_date = date_columns[end_date_idx + min_idx_in_window]
                else:
                    min_date = None
            
            end_value = price_data_view[stock_idx, end_date_idx]
            start_value = price_data_view[stock_idx, start_date_idx]
            
            # 计算最接近值
            closest_value = NAN
            closest_idx_in_window = -1
            if not isnan(end_value):
                min_diff = 1e308
                for j in range(window_len):
                    if not isnan(price_data_view[stock_idx, end_date_idx + j]):
                        diff = fabs(price_data_view[stock_idx, end_date_idx + j] - end_value)
                        if diff < min_diff:
                            min_diff = diff
                            closest_value = price_data_view[stock_idx, end_date_idx + j]
                            closest_idx_in_window = j
            
            # 确定实际开始值索引
            with gil:
                if start_option == "最大值":
                    base_idx = end_date_idx + max_idx_in_window if max_idx_in_window >= 0 else -1
                elif start_option == "最小值":
                    base_idx = end_date_idx + min_idx_in_window if min_idx_in_window >= 0 else -1
                elif start_option == "接近值":
                    base_idx = end_date_idx + closest_idx_in_window if closest_idx_in_window >= 0 else -1
                else:
                    base_idx = start_date_idx
            
            actual_idx = base_idx - shift_days if base_idx >= 0 else -1
            actual_value = price_data_view[stock_idx, actual_idx] if actual_idx >= 0 and actual_idx < num_dates else NAN
            
            # 计算连续累加值
            if actual_idx >= 0 and actual_idx >= end_date_idx:
                calc_continuous_sum(diff_data_view[stock_idx, end_date_idx:actual_idx+1][::-1], cont_sum)
            else:
                cont_sum.clear()

            # 计算向前最大连续累加值
            if max_idx_in_window >= 0 and end_date_idx + max_idx_in_window >= end_date_idx:
                calc_continuous_sum(
                    diff_data_view[stock_idx, end_date_idx:end_date_idx + max_idx_in_window + 1][::-1],
                    forward_max_result_c
                )
            else:
                forward_max_result_c.clear()

            # 计算向前最小连续累加值
            if min_idx_in_window >= 0 and end_date_idx + min_idx_in_window >= end_date_idx:
                calc_continuous_sum(
                    diff_data_view[stock_idx, end_date_idx:end_date_idx + min_idx_in_window + 1][::-1],
                    forward_min_result_c
                )
            else:
                forward_min_result_c.clear()

            with gil:
                py_cont_sum = list(cont_sum)
                forward_max_result = list(forward_max_result_c)
                forward_min_result = list(forward_min_result_c)
                n = len(py_cont_sum)
                half = int(round(n / 2.0))
                q1 = int(round(n / 4.0))
                q2 = int(round(n / 2.0))
                q3 = int(round(3 * n / 4.0))
                continuous_abs_sum_first_half = 0
                continuous_abs_sum_second_half = 0
                continuous_abs_sum_block1 = 0
                continuous_abs_sum_block2 = 0
                continuous_abs_sum_block3 = 0
                continuous_abs_sum_block4 = 0
                for i in range(half):
                    continuous_abs_sum_first_half += abs(py_cont_sum[i])
                for i in range(half, n):
                    continuous_abs_sum_second_half += abs(py_cont_sum[i])
                for i in range(q1):
                    continuous_abs_sum_block1 += abs(py_cont_sum[i])
                for i in range(q1, q2):
                    continuous_abs_sum_block2 += abs(py_cont_sum[i])
                for i in range(q2, q3):
                    continuous_abs_sum_block3 += abs(py_cont_sum[i])
                for i in range(q3, n):
                    continuous_abs_sum_block4 += abs(py_cont_sum[i])
                continuous_abs_sum_first_half = round_to_2(continuous_abs_sum_first_half)
                continuous_abs_sum_second_half = round_to_2(continuous_abs_sum_second_half)
                continuous_abs_sum_block1 = round_to_2(continuous_abs_sum_block1)
                continuous_abs_sum_block2 = round_to_2(continuous_abs_sum_block2)
                continuous_abs_sum_block3 = round_to_2(continuous_abs_sum_block3)
                continuous_abs_sum_block4 = round_to_2(continuous_abs_sum_block4)

                # 有效累加值计算
                valid_sum_arr = calc_valid_sum(py_cont_sum)
                forward_max_valid_sum_arr = calc_valid_sum(forward_max_result)
                forward_min_valid_sum_arr = calc_valid_sum(forward_min_result)

                # 计算 valid_sum_arr 的分块绝对值之和
                n_valid = len(valid_sum_arr)
                half_valid = int(round(n_valid / 2.0))
                q1_valid = int(round(n_valid / 4.0))
                q2_valid = int(round(n_valid / 2.0))
                q3_valid = int(round(3 * n_valid / 4.0))
                valid_abs_sum_first_half = 0
                valid_abs_sum_second_half = 0
                valid_abs_sum_block1 = 0
                valid_abs_sum_block2 = 0
                valid_abs_sum_block3 = 0
                valid_abs_sum_block4 = 0
                for i in range(half_valid):
                    valid_abs_sum_first_half += abs(valid_sum_arr[i])
                for i in range(half_valid, n_valid):
                    valid_abs_sum_second_half += abs(valid_sum_arr[i])
                for i in range(q1_valid):
                    valid_abs_sum_block1 += abs(valid_sum_arr[i])
                for i in range(q1_valid, q2_valid):
                    valid_abs_sum_block2 += abs(valid_sum_arr[i])
                for i in range(q2_valid, q3_valid):
                    valid_abs_sum_block3 += abs(valid_sum_arr[i])
                for i in range(q3_valid, n_valid):
                    valid_abs_sum_block4 += abs(valid_sum_arr[i])
                valid_abs_sum_first_half = round_to_2(valid_abs_sum_first_half)
                valid_abs_sum_second_half = round_to_2(valid_abs_sum_second_half)
                valid_abs_sum_block1 = round_to_2(valid_abs_sum_block1)
                valid_abs_sum_block2 = round_to_2(valid_abs_sum_block2)
                valid_abs_sum_block3 = round_to_2(valid_abs_sum_block3)
                valid_abs_sum_block4 = round_to_2(valid_abs_sum_block4)

                # 计算 forward_max_valid_sum_arr 的分块绝对值之和
                n_fmax_valid = len(forward_max_valid_sum_arr)
                half_fmax_valid = int(round(n_fmax_valid / 2.0))
                q1_fmax_valid = int(round(n_fmax_valid / 4.0))
                q2_fmax_valid = int(round(n_fmax_valid / 2.0))
                q3_fmax_valid = int(round(3 * n_fmax_valid / 4.0))
                forward_max_valid_abs_sum_first_half = 0
                forward_max_valid_abs_sum_second_half = 0
                forward_max_valid_abs_sum_block1 = 0
                forward_max_valid_abs_sum_block2 = 0
                forward_max_valid_abs_sum_block3 = 0
                forward_max_valid_abs_sum_block4 = 0
                for i in range(half_fmax_valid):
                    forward_max_valid_abs_sum_first_half += abs(forward_max_valid_sum_arr[i])
                for i in range(half_fmax_valid, n_fmax_valid):
                    forward_max_valid_abs_sum_second_half += abs(forward_max_valid_sum_arr[i])
                for i in range(q1_fmax_valid):
                    forward_max_valid_abs_sum_block1 += abs(forward_max_valid_sum_arr[i])
                for i in range(q1_fmax_valid, q2_fmax_valid):
                    forward_max_valid_abs_sum_block2 += abs(forward_max_valid_sum_arr[i])
                for i in range(q2_fmax_valid, q3_fmax_valid):
                    forward_max_valid_abs_sum_block3 += abs(forward_max_valid_sum_arr[i])
                for i in range(q3_fmax_valid, n_fmax_valid):
                    forward_max_valid_abs_sum_block4 += abs(forward_max_valid_sum_arr[i])
                forward_max_valid_abs_sum_first_half = round_to_2(forward_max_valid_abs_sum_first_half)
                forward_max_valid_abs_sum_second_half = round_to_2(forward_max_valid_abs_sum_second_half)
                forward_max_valid_abs_sum_block1 = round_to_2(forward_max_valid_abs_sum_block1)
                forward_max_valid_abs_sum_block2 = round_to_2(forward_max_valid_abs_sum_block2)
                forward_max_valid_abs_sum_block3 = round_to_2(forward_max_valid_abs_sum_block3)
                forward_max_valid_abs_sum_block4 = round_to_2(forward_max_valid_abs_sum_block4)

                # 计算 forward_min_valid_sum_arr 的分块绝对值之和
                n_fmin_valid = len(forward_min_valid_sum_arr)
                half_fmin_valid = int(round(n_fmin_valid / 2.0))
                q1_fmin_valid = int(round(n_fmin_valid / 4.0))
                q2_fmin_valid = int(round(n_fmin_valid / 2.0))
                q3_fmin_valid = int(round(3 * n_fmin_valid / 4.0))
                forward_min_valid_abs_sum_first_half = 0
                forward_min_valid_abs_sum_second_half = 0
                forward_min_valid_abs_sum_block1 = 0
                forward_min_valid_abs_sum_block2 = 0
                forward_min_valid_abs_sum_block3 = 0
                forward_min_valid_abs_sum_block4 = 0
                for i in range(half_fmin_valid):
                    forward_min_valid_abs_sum_first_half += abs(forward_min_valid_sum_arr[i])
                for i in range(half_fmin_valid, n_fmin_valid):
                    forward_min_valid_abs_sum_second_half += abs(forward_min_valid_sum_arr[i])
                for i in range(q1_fmin_valid):
                    forward_min_valid_abs_sum_block1 += abs(forward_min_valid_sum_arr[i])
                for i in range(q1_fmin_valid, q2_fmin_valid):
                    forward_min_valid_abs_sum_block2 += abs(forward_min_valid_sum_arr[i])
                for i in range(q2_fmin_valid, q3_fmin_valid):
                    forward_min_valid_abs_sum_block3 += abs(forward_min_valid_sum_arr[i])
                for i in range(q3_fmin_valid, n_fmin_valid):
                    forward_min_valid_abs_sum_block4 += abs(forward_min_valid_sum_arr[i])
                forward_min_valid_abs_sum_first_half = round_to_2(forward_min_valid_abs_sum_first_half)
                forward_min_valid_abs_sum_second_half = round_to_2(forward_min_valid_abs_sum_second_half)
                forward_min_valid_abs_sum_block1 = round_to_2(forward_min_valid_abs_sum_block1)
                forward_min_valid_abs_sum_block2 = round_to_2(forward_min_valid_abs_sum_block2)
                forward_min_valid_abs_sum_block3 = round_to_2(forward_min_valid_abs_sum_block3)
                forward_min_valid_abs_sum_block4 = round_to_2(forward_min_valid_abs_sum_block4)

                # 计算正累加和和负累加和
                valid_pos_sum, valid_neg_sum = calc_pos_neg_sum(valid_sum_arr)
                forward_max_valid_pos_sum, forward_max_valid_neg_sum = calc_pos_neg_sum(forward_max_valid_sum_arr)
                forward_min_valid_pos_sum, forward_min_valid_neg_sum = calc_pos_neg_sum(forward_min_valid_sum_arr)

                row_result = {
                    'stock_idx': stock_idx,
                    'max_value': [date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None, max_price],
                    'min_value': [date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None, min_price],
                    'end_value': [end_date, end_value],
                    'start_value': [start_date, start_value],
                    'actual_value': [date_columns[actual_idx] if actual_idx >= 0 and actual_idx < num_dates else None, actual_value],
                    'closest_value': [date_columns[end_date_idx + closest_idx_in_window] if closest_idx_in_window >= 0 else None, closest_value],
                    'continuous_results': py_cont_sum,
                    'continuous_len': len(py_cont_sum),
                    'continuous_start_value': cont_sum[0] if cont_sum.size() > 0 else None,
                    'continuous_start_next_value': cont_sum[1] if cont_sum.size() > 1 else None,
                    'continuous_start_next_next_value': cont_sum[2] if cont_sum.size() > 2 else None,
                    'continuous_end_value': cont_sum[cont_sum.size()-1] if cont_sum.size() > 0 else None,
                    'continuous_end_prev_value': cont_sum[cont_sum.size()-2] if cont_sum.size() > 1 else None,
                    'continuous_end_prev_prev_value': cont_sum[cont_sum.size()-3] if cont_sum.size() > 2 else None,
                    'continuous_abs_sum_first_half': continuous_abs_sum_first_half,
                    'continuous_abs_sum_second_half': continuous_abs_sum_second_half,
                    'continuous_abs_sum_block1': continuous_abs_sum_block1,
                    'continuous_abs_sum_block2': continuous_abs_sum_block2,
                    'continuous_abs_sum_block3': continuous_abs_sum_block3,
                    'continuous_abs_sum_block4': continuous_abs_sum_block4,
                    'forward_max_result': forward_max_result,
                    'forward_min_result': forward_min_result,
                    'valid_sum_arr': valid_sum_arr,
                    'valid_sum_len': len(valid_sum_arr),
                    'valid_pos_sum': valid_pos_sum,
                    'valid_neg_sum': valid_neg_sum,
                    'forward_max_valid_sum_arr': forward_max_valid_sum_arr,
                    'forward_max_valid_sum_len': len(forward_max_valid_sum_arr),
                    'forward_max_valid_pos_sum': forward_max_valid_pos_sum,
                    'forward_max_valid_neg_sum': forward_max_valid_neg_sum,
                    'forward_min_valid_sum_arr': forward_min_valid_sum_arr,
                    'forward_min_valid_sum_len': len(forward_min_valid_sum_arr),
                    'forward_min_valid_pos_sum': forward_min_valid_pos_sum,
                    'forward_min_valid_neg_sum': forward_min_valid_neg_sum,
                    'valid_abs_sum_first_half': valid_abs_sum_first_half,
                    'valid_abs_sum_second_half': valid_abs_sum_second_half,
                    'valid_abs_sum_block1': valid_abs_sum_block1,
                    'valid_abs_sum_block2': valid_abs_sum_block2,
                    'valid_abs_sum_block3': valid_abs_sum_block3,
                    'valid_abs_sum_block4': valid_abs_sum_block4,
                    'forward_max_valid_abs_sum_first_half': forward_max_valid_abs_sum_first_half,
                    'forward_max_valid_abs_sum_second_half': forward_max_valid_abs_sum_second_half,
                    'forward_max_valid_abs_sum_block1': forward_max_valid_abs_sum_block1,
                    'forward_max_valid_abs_sum_block2': forward_max_valid_abs_sum_block2,
                    'forward_max_valid_abs_sum_block3': forward_max_valid_abs_sum_block3,
                    'forward_max_valid_abs_sum_block4': forward_max_valid_abs_sum_block4,
                    'forward_min_valid_abs_sum_first_half': forward_min_valid_abs_sum_first_half,
                    'forward_min_valid_abs_sum_second_half': forward_min_valid_abs_sum_second_half,
                    'forward_min_valid_abs_sum_block1': forward_min_valid_abs_sum_block1,
                    'forward_min_valid_abs_sum_block2': forward_min_valid_abs_sum_block2,
                    'forward_min_valid_abs_sum_block3': forward_min_valid_abs_sum_block3,
                    'forward_min_valid_abs_sum_block4': forward_min_valid_abs_sum_block4,
                    'forward_max_date': max_date,
                    'forward_min_date': min_date,
                }
                all_results[end_date].append(row_result)
    
    # 将字典转换为有序列表
    sorted_results = []
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        if end_date in all_results:
            sorted_results.append({
                'end_date': end_date,
                'stocks': all_results[end_date]
            })
    
    return sorted_results