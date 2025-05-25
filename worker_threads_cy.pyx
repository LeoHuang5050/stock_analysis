# distutils: language = c++
# cython: boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False
# distutils: extra_compile_args = /openmp
# distutils: extra_link_args = /openmp

import numpy as np
cimport numpy as np
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

cdef void calc_valid_sum_and_pos_neg(
    vector[double]& arr,
    vector[double]& valid_sum,
    int* valid_len,
    double* pos_sum,
    double* neg_sum
) nogil:
    cdef int n = arr.size()
    cdef int i
    cdef double v
    cdef double abs_v, next_abs
    cdef int valid_idx = 0
    pos_sum[0] = 0
    neg_sum[0] = 0
    if n == 0:
        valid_len[0] = 0
        return
    for i in range(n):
        v = arr[i]
        if isnan(v):  # 跳过 NaN 值
            continue
        abs_v = fabs(v)
        next_abs = fabs(arr[i+1]) if i < n-1 else 0
        if i < n-1 and next_abs > abs_v:
            valid_sum.push_back(v)
        elif i < n-1:
            valid_sum.push_back(arr[i+1] if arr[i+1] >= 0 else -fabs(arr[i+1]))
        else:
            valid_sum.push_back(v)
        if valid_sum[valid_idx] > 0:
            pos_sum[0] += valid_sum[valid_idx]
        elif valid_sum[valid_idx] < 0:
            neg_sum[0] += valid_sum[valid_idx]
        valid_idx += 1
    valid_len[0] = valid_idx

def calculate_batch_cy(
    np.ndarray[DTYPE_t, ndim=2] price_data,
    list date_columns,
    int width,
    str start_option,
    int shift_days,
    int end_date_start_idx,
    int end_date_end_idx,
    np.ndarray[DTYPE_t, ndim=2] diff_data,
    np.ndarray[np.int32_t, ndim=1] stock_idx_arr,
    bint is_forward,
    int n_days,
    double user_range_ratio,
    double continuous_abs_threshold,
    int n_days_max,
    int op_days,
    double inc_rate,
    double after_gt_end_ratio,
    double after_gt_start_ratio,
    str expr,
    double ops_change_input=0.09,
    str formula_expr=None,
    int select_count=10,
    str sort_mode="最大值排序",
    bint only_show_selected=False
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
    cdef double valid_sum_arr[1000]
    cdef int valid_sum_len
    cdef double valid_pos_sum, valid_neg_sum
    cdef double prev_day_change = NAN
    cdef double end_day_change = NAN
    cdef double n_days_max_value = NAN
    cdef double price_arr[1000]
    cdef int n_valid, half_valid, q1_valid, q2_valid, q3_valid
    cdef double valid_abs_sum_first_half, valid_abs_sum_second_half
    cdef double valid_abs_sum_block1, valid_abs_sum_block2, valid_abs_sum_block3, valid_abs_sum_block4
    cdef vector[double] valid_sum_vec
    cdef vector[double] forward_max_valid_sum_vec
    cdef vector[double] forward_min_valid_sum_vec
    cdef double forward_max_valid_pos_sum, forward_max_valid_neg_sum
    cdef double forward_min_valid_pos_sum, forward_min_valid_neg_sum
    cdef double increment_value = NAN
    cdef double after_gt_end_value = NAN
    cdef double after_gt_start_value = NAN
    cdef int increment_days = -1
    cdef int after_gt_end_days = -1
    cdef int after_gt_start_days = -1
    cdef double increment_threshold
    cdef double after_gt_end_threshold
    cdef double after_gt_start_threshold
    cdef double v
    cdef int k
    cdef object user_func = None
    from worker_threads import make_user_func, abbr_map
    user_func = make_user_func(expr)
    cdef double max_abs_val
    cdef double abs_v
    cdef bint continuous_abs_is_less

    # 计算向前最大最小连续累加值的分块和绝对值之和（只针对 forward_max_result_c 和 forward_min_result_c，不涉及有效累加值）
    cdef int forward_max_result_len
    cdef double forward_max_abs_sum_first_half
    cdef double forward_max_abs_sum_second_half
    cdef double forward_max_abs_sum_block1
    cdef double forward_max_abs_sum_block2
    cdef double forward_max_abs_sum_block3
    cdef double forward_max_abs_sum_block4

    # 向前最小连续累加值绝对值
    cdef int forward_min_result_len
    cdef double forward_min_abs_sum_first_half
    cdef double forward_min_abs_sum_second_half
    cdef double forward_min_abs_sum_block1
    cdef double forward_min_abs_sum_block2
    cdef double forward_min_abs_sum_block3
    cdef double forward_min_abs_sum_block4

    # 向前最大有效累加值相关计算
    cdef int forward_max_valid_sum_len
    cdef double forward_max_valid_abs_sum_first_half
    cdef double forward_max_valid_abs_sum_second_half
    cdef double forward_max_valid_abs_sum_block1
    cdef double forward_max_valid_abs_sum_block2
    cdef double forward_max_valid_abs_sum_block3
    cdef double forward_max_valid_abs_sum_block4

    # 向前最小有效累加值相关计算
    cdef int forward_min_valid_sum_len
    cdef double forward_min_valid_abs_sum_first_half
    cdef double forward_min_valid_abs_sum_second_half
    cdef double forward_min_valid_abs_sum_block1
    cdef double forward_min_valid_abs_sum_block2
    cdef double forward_min_valid_abs_sum_block3
    cdef double forward_min_valid_abs_sum_block4

    
    # 初始化结果字典
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        all_results[end_date] = []
    
    # 单线程处理每个股票
    for i in range(stock_idx_arr_view.shape[0]):
        stock_idx = stock_idx_arr_view[i]
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            try:
                with nogil:
                    end_date_idx = idx
                    start_date_idx = end_date_idx + width
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
                    if is_forward and max_idx_in_window >= 0 and end_date_idx + max_idx_in_window >= end_date_idx:
                        calc_continuous_sum(
                            diff_data_view[stock_idx, end_date_idx:end_date_idx + max_idx_in_window + 1][::-1],
                            forward_max_result_c
                        )
                    else:
                        forward_max_result_c.clear()

                    # 计算向前最小连续累加值
                    if is_forward and min_idx_in_window >= 0 and end_date_idx + min_idx_in_window >= end_date_idx:
                        calc_continuous_sum(
                            diff_data_view[stock_idx, end_date_idx:end_date_idx + min_idx_in_window + 1][::-1],
                            forward_min_result_c
                        )
                    else:
                        forward_min_result_c.clear() 

                    # 递增值计算逻辑
                    increment_value = NAN
                    increment_days = -1
                    after_gt_end_value = NAN
                    after_gt_end_days = -1
                    after_gt_start_value = NAN
                    after_gt_start_days = -1
                    if op_days > 0:
                        end_value = price_data_view[stock_idx, end_date_idx]
                        if not isnan(end_value):
                            # 递增值
                            found = False
                            for n, k in enumerate(range(end_date_idx - 1, end_date_idx - op_days - 1, -1), 1):
                                if k < 0:
                                    break
                                v = price_data_view[stock_idx, k]
                                if isnan(v):
                                    continue
                                increment_threshold = end_value * inc_rate * n
                                if increment_threshold != 0 and (v - end_value) > increment_threshold:
                                    increment_value = round_to_2(v)
                                    increment_days = n
                                    found = True
                                    break
                            if not found:
                                fallback_idx = end_date_idx - op_days
                                if fallback_idx >= 0:
                                    increment_value = round_to_2(price_data_view[stock_idx, fallback_idx])
                                    increment_days = op_days
                        # after_gt_end_value 计算（方向：end_date_idx-1 向 end_date_idx-op_days）
                        if not isnan(end_value):
                            found = False
                            for n, k in enumerate(range(end_date_idx - 1, end_date_idx - op_days - 1, -1), 1):
                                if k < 0:
                                    break
                                v = price_data_view[stock_idx, k]
                                if isnan(v):
                                    continue
                                after_gt_end_threshold = end_value * after_gt_end_ratio
                                if after_gt_end_ratio != 0 and (v - end_value) > after_gt_end_threshold:
                                    after_gt_end_value = round_to_2(v)
                                    after_gt_end_days = n
                                    found = True
                                    break
                            if not found:
                                fallback_idx = end_date_idx - op_days
                                if fallback_idx >= 0:
                                    after_gt_end_value = round_to_2(price_data_view[stock_idx, fallback_idx])
                                    after_gt_end_days = op_days
                        # after_gt_start_value 计算（方向：end_date_idx 向 end_date_idx-op_days，判断k和k-1）
                        found = False
                        for n, k in enumerate(range(end_date_idx, end_date_idx - op_days, -1), 1):
                            if k - 1 < 0 or k >= num_dates:
                                continue
                            v_now = price_data_view[stock_idx, k]
                            v_prev = price_data_view[stock_idx, k - 1]
                            if isnan(v_now) or isnan(v_prev):
                                continue
                            after_gt_start_threshold = v_now * after_gt_start_ratio
                            if after_gt_start_ratio != 0 and (v_prev - v_now) > after_gt_start_threshold:
                                after_gt_start_value = round_to_2(v_prev)
                                after_gt_start_days = n
                                found = True
                                break
                        if not found:
                            fallback_idx = end_date_idx - op_days
                            if fallback_idx >= 0:
                                after_gt_start_value = round_to_2(price_data_view[stock_idx, fallback_idx])
                                after_gt_start_days = op_days

                    # 处理NAN值
                    if isnan(increment_value):
                        increment_value = NAN
                    if isnan(after_gt_end_value):
                        after_gt_end_value = NAN
                    if isnan(after_gt_start_value):
                        after_gt_start_value = NAN

                    # 主连续累加值的有效累加值及正负加和
                    valid_sum_vec.clear()
                    calc_valid_sum_and_pos_neg(
                        cont_sum, valid_sum_vec, &valid_sum_len, &valid_pos_sum, &valid_neg_sum)
                    
                    n = cont_sum.size()
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
                    for j in range(half):
                        continuous_abs_sum_first_half += fabs(cont_sum[j])
                    for j in range(half, n):
                        continuous_abs_sum_second_half += fabs(cont_sum[j])
                    for j in range(q1):
                        continuous_abs_sum_block1 += fabs(cont_sum[j])
                    for j in range(q1, q2):
                        continuous_abs_sum_block2 += fabs(cont_sum[j])
                    for j in range(q2, q3):
                        continuous_abs_sum_block3 += fabs(cont_sum[j])
                    for j in range(q3, n):
                        continuous_abs_sum_block4 += fabs(cont_sum[j])
                    continuous_abs_sum_first_half = round_to_2(continuous_abs_sum_first_half)
                    continuous_abs_sum_second_half = round_to_2(continuous_abs_sum_second_half)
                    continuous_abs_sum_block1 = round_to_2(continuous_abs_sum_block1)
                    continuous_abs_sum_block2 = round_to_2(continuous_abs_sum_block2)
                    continuous_abs_sum_block3 = round_to_2(continuous_abs_sum_block3)
                    continuous_abs_sum_block4 = round_to_2(continuous_abs_sum_block4)

                    # 计算向前最大最小连续累加值
                    if is_forward:
                        # 向前最大连续累加值绝对值数组长度，前一半绝对值之和、后一半绝对值之和
                        forward_max_result_len = forward_max_result_c.size()
                        if forward_max_result_len > 0:
                            n = forward_max_result_len
                            half = int(round(n / 2.0))
                            q1 = int(round(n / 4.0))
                            q2 = int(round(n / 2.0))
                            q3 = int(round(3 * n / 4.0))
                            
                            forward_max_abs_sum_first_half = 0
                            forward_max_abs_sum_second_half = 0
                            forward_max_abs_sum_block1 = 0
                            forward_max_abs_sum_block2 = 0
                            forward_max_abs_sum_block3 = 0
                            forward_max_abs_sum_block4 = 0
                            
                            for j in range(n):
                                abs_v = fabs(forward_max_result_c[j])
                                if j < half:
                                    forward_max_abs_sum_first_half += abs_v
                                else:
                                    forward_max_abs_sum_second_half += abs_v
                                if j < q1:
                                    forward_max_abs_sum_block1 += abs_v
                                elif j < q2:
                                    forward_max_abs_sum_block2 += abs_v
                                elif j < q3:
                                    forward_max_abs_sum_block3 += abs_v
                                else:
                                    forward_max_abs_sum_block4 += abs_v
                            
                            forward_max_abs_sum_first_half = round_to_2(forward_max_abs_sum_first_half)
                            forward_max_abs_sum_second_half = round_to_2(forward_max_abs_sum_second_half)
                            forward_max_abs_sum_block1 = round_to_2(forward_max_abs_sum_block1)
                            forward_max_abs_sum_block2 = round_to_2(forward_max_abs_sum_block2)
                            forward_max_abs_sum_block3 = round_to_2(forward_max_abs_sum_block3)
                            forward_max_abs_sum_block4 = round_to_2(forward_max_abs_sum_block4)
                        else:
                            forward_max_abs_sum_first_half = NAN
                            forward_max_abs_sum_second_half = NAN
                            forward_max_abs_sum_block1 = NAN
                            forward_max_abs_sum_block2 = NAN
                            forward_max_abs_sum_block3 = NAN
                            forward_max_abs_sum_block4 = NAN

                        # 向前最小有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                        forward_min_result_len = forward_min_result_c.size()
                        if forward_min_result_len > 0:
                            n = forward_min_result_len
                            half = int(round(n / 2.0))
                            q1 = int(round(n / 4.0))
                            q2 = int(round(n / 2.0))
                            q3 = int(round(3 * n / 4.0))
                            
                            forward_min_abs_sum_first_half = 0
                            forward_min_abs_sum_second_half = 0
                            forward_min_abs_sum_block1 = 0
                            forward_min_abs_sum_block2 = 0
                            forward_min_abs_sum_block3 = 0
                            forward_min_abs_sum_block4 = 0
                            
                            for j in range(n):
                                abs_v = fabs(forward_min_result_c[j])
                                if j < half:
                                    forward_min_abs_sum_first_half += abs_v
                                else:
                                    forward_min_abs_sum_second_half += abs_v
                                if j < q1:
                                    forward_min_abs_sum_block1 += abs_v
                                elif j < q2:
                                    forward_min_abs_sum_block2 += abs_v
                                elif j < q3:
                                    forward_min_abs_sum_block3 += abs_v
                                else:
                                    forward_min_abs_sum_block4 += abs_v
                            
                            forward_min_abs_sum_first_half = round_to_2(forward_min_abs_sum_first_half)
                            forward_min_abs_sum_second_half = round_to_2(forward_min_abs_sum_second_half)
                            forward_min_abs_sum_block1 = round_to_2(forward_min_abs_sum_block1)
                            forward_min_abs_sum_block2 = round_to_2(forward_min_abs_sum_block2)
                            forward_min_abs_sum_block3 = round_to_2(forward_min_abs_sum_block3)
                            forward_min_abs_sum_block4 = round_to_2(forward_min_abs_sum_block4)

                    else:
                        forward_max_sum_len = 0
                        forward_max_abs_sum_first_half = NAN
                        forward_max_abs_sum_second_half = NAN
                        forward_max_abs_sum_block1 = NAN
                        forward_max_abs_sum_block2 = NAN
                        forward_max_abs_sum_block3 = NAN
                        forward_max_abs_sum_block4 = NAN
                        forward_min_sum_len = 0
                        forward_min_abs_sum_first_half = NAN
                        forward_min_abs_sum_second_half = NAN
                        forward_min_abs_sum_block1 = NAN
                        forward_min_abs_sum_block2 = NAN
                        forward_min_abs_sum_block3 = NAN
                        forward_min_abs_sum_block4 = NAN

                    # 计算正累加和和负累加和
                    # 向前最大有效累加值的正负加和
                    if forward_max_result_c.size() > 0:
                        forward_max_valid_sum_vec.clear()
                        calc_valid_sum_and_pos_neg(
                            forward_max_result_c,
                            forward_max_valid_sum_vec, &forward_max_valid_sum_len,
                            &forward_max_valid_pos_sum, &forward_max_valid_neg_sum)
                        forward_max_valid_pos_sum = round_to_2(forward_max_valid_pos_sum)
                        forward_max_valid_neg_sum = round_to_2(forward_max_valid_neg_sum)
                    else:
                        forward_max_valid_sum_len = 0
                        forward_max_valid_pos_sum = 0
                        forward_max_valid_neg_sum = 0

                    # 向前最小有效累加值的正负加和
                    if forward_min_result_c.size() > 0:
                        forward_min_valid_sum_vec.clear()
                        calc_valid_sum_and_pos_neg(
                            forward_min_result_c,
                            forward_min_valid_sum_vec, &forward_min_valid_sum_len,
                            &forward_min_valid_pos_sum, &forward_min_valid_neg_sum)
                        # 添加 round_to_2 处理
                        forward_min_valid_pos_sum = round_to_2(forward_min_valid_pos_sum)
                        forward_min_valid_neg_sum = round_to_2(forward_min_valid_neg_sum)
                    else:
                        forward_min_valid_sum_len = 0
                        forward_min_valid_pos_sum = 0
                        forward_min_valid_neg_sum = 0

                    # 连续累加值绝对值最大值判断
                    max_abs_val = 0
                    if continuous_abs_threshold == continuous_abs_threshold and cont_sum.size() > 0:
                        for j in range(cont_sum.size()):
                            abs_v = fabs(cont_sum[j])
                            if abs_v > max_abs_val:
                                max_abs_val = abs_v
                        continuous_abs_is_less = max_abs_val < continuous_abs_threshold
                    else:
                        continuous_abs_is_less = False
                
                    
                    # 计算continuous_len
                    continuous_len = cont_sum.size()
                    
                    # 前n_days_max区间最大值
                    n_days_max_value = NAN
                    if n_days_max > 0 and end_date_idx + n_days_max <= num_dates:
                        maxv = -1e308
                        for j in range(n_days_max):
                            v = price_data_view[stock_idx, end_date_idx + j]
                            if not isnan(v) and v > maxv:
                                maxv = v
                        n_days_max_value = maxv if maxv > -1e308 else NAN
                    
                    # 计算结束地址前1日涨跌幅和结束日涨跌幅
                    prev_day_change = NAN
                    end_day_change = NAN
                    
                    for j in range(window_len):
                        price_arr[j] = price_data_view[stock_idx, end_date_idx + j]
                    
                    # 在nogil区域之前计算长度
                    price_arr_len = window_len
                    
                    if price_arr_len >= 3:
                        if price_arr[2] != 0 and not isnan(price_arr[2]):
                            prev_day_change = round_to_2(((price_arr[1] - price_arr[2]) / price_arr[2]) * 100)
                        if price_arr[1] != 0 and not isnan(price_arr[1]):
                            end_day_change = round_to_2(((price_arr[0] - price_arr[1]) / price_arr[1]) * 100)
                    elif price_arr_len == 2:
                        if price_arr[1] != 0 and not isnan(price_arr[1]):
                            end_day_change = round_to_2(((price_arr[0] - price_arr[1]) / price_arr[1]) * 100)
                    
                    # 有效累加值分块绝对值之和
                    valid_abs_sum_first_half = 0
                    valid_abs_sum_second_half = 0
                    valid_abs_sum_block1 = 0
                    valid_abs_sum_block2 = 0
                    valid_abs_sum_block3 = 0
                    valid_abs_sum_block4 = 0
                    n_valid = valid_sum_len
                    half_valid = int(round(n_valid / 2.0))
                    q1_valid = int(round(n_valid / 4.0))
                    q2_valid = int(round(n_valid / 2.0))
                    q3_valid = int(round(3 * n_valid / 4.0))
                    for j in range(half_valid):
                        valid_abs_sum_first_half += fabs(valid_sum_vec[j])
                    for j in range(half_valid, n_valid):
                        valid_abs_sum_second_half += fabs(valid_sum_vec[j])
                    for j in range(q1_valid):
                        valid_abs_sum_block1 += fabs(valid_sum_vec[j])
                    for j in range(q1_valid, q2_valid):
                        valid_abs_sum_block2 += fabs(valid_sum_vec[j])
                    for j in range(q2_valid, q3_valid):
                        valid_abs_sum_block3 += fabs(valid_sum_vec[j])
                    for j in range(q3_valid, n_valid):
                        valid_abs_sum_block4 += fabs(valid_sum_vec[j])
                    valid_abs_sum_first_half = round_to_2(valid_abs_sum_first_half)
                    valid_abs_sum_second_half = round_to_2(valid_abs_sum_second_half)
                    valid_abs_sum_block1 = round_to_2(valid_abs_sum_block1)
                    valid_abs_sum_block2 = round_to_2(valid_abs_sum_block2)
                    valid_abs_sum_block3 = round_to_2(valid_abs_sum_block3)
                    valid_abs_sum_block4 = round_to_2(valid_abs_sum_block4)

                    # 计算向前最大有效连续累加值的分块和绝对值之和（全部在Cython区完成）
                    forward_max_valid_abs_sum_first_half = 0
                    forward_max_valid_abs_sum_second_half = 0
                    forward_max_valid_abs_sum_block1 = 0
                    forward_max_valid_abs_sum_block2 = 0
                    forward_max_valid_abs_sum_block3 = 0
                    forward_max_valid_abs_sum_block4 = 0
                    if is_forward and forward_max_result_len > 0:
                        n = forward_max_result_len
                        half = int(round(n / 2.0))
                        q1 = int(round(n / 4.0))
                        q2 = int(round(n / 2.0))
                        q3 = int(round(3 * n / 4.0))
                        for j in range(n):
                            v = fabs(forward_max_valid_sum_vec[j])
                            if j < half:
                                forward_max_valid_abs_sum_first_half += v
                            else:
                                forward_max_valid_abs_sum_second_half += v
                            if j < q1:
                                forward_max_valid_abs_sum_block1 += v
                            elif j < q2:
                                forward_max_valid_abs_sum_block2 += v
                            elif j < q3:
                                forward_max_valid_abs_sum_block3 += v
                            else:
                                forward_max_valid_abs_sum_block4 += v
                        forward_max_valid_abs_sum_first_half = round_to_2(forward_max_valid_abs_sum_first_half)
                        forward_max_valid_abs_sum_second_half = round_to_2(forward_max_valid_abs_sum_second_half)
                        forward_max_valid_abs_sum_block1 = round_to_2(forward_max_valid_abs_sum_block1)
                        forward_max_valid_abs_sum_block2 = round_to_2(forward_max_valid_abs_sum_block2)
                        forward_max_valid_abs_sum_block3 = round_to_2(forward_max_valid_abs_sum_block3)
                        forward_max_valid_abs_sum_block4 = round_to_2(forward_max_valid_abs_sum_block4)
                    else:
                        forward_max_valid_abs_sum_first_half = 0
                        forward_max_valid_abs_sum_second_half = 0
                        forward_max_valid_abs_sum_block1 = 0
                        forward_max_valid_abs_sum_block2 = 0
                        forward_max_valid_abs_sum_block3 = 0
                        forward_max_valid_abs_sum_block4 = 0

                    # 计算向前最小有效连续累加值的分块和绝对值之和（全部在Cython区完成）
                    if is_forward and forward_min_result_len > 0:
                        n = forward_min_result_len
                        half = <int>(round(n / 2.0))
                        q1 = <int>(round(n / 4.0))
                        q2 = <int>(round(n / 2.0))
                        q3 = <int>(round(3 * n / 4.0))
                        for j in range(n):
                            v = fabs(forward_min_valid_sum_vec[j])
                            if j < half:
                                forward_min_valid_abs_sum_first_half += v
                            else:
                                forward_min_valid_abs_sum_second_half += v
                            if j < q1:
                                forward_min_valid_abs_sum_block1 += v
                            elif j < q2:
                                forward_min_valid_abs_sum_block2 += v
                            elif j < q3:
                                forward_min_valid_abs_sum_block3 += v
                            else:
                                forward_min_valid_abs_sum_block4 += v
                    else:
                        forward_min_valid_abs_sum_first_half = 0
                        forward_min_valid_abs_sum_second_half = 0
                        forward_min_valid_abs_sum_block1 = 0
                        forward_min_valid_abs_sum_block2 = 0
                        forward_min_valid_abs_sum_block3 = 0
                        forward_min_valid_abs_sum_block4 = 0
                    valid_pos_sum = round_to_2(valid_pos_sum)
                    valid_neg_sum = round_to_2(valid_neg_sum)

                    
                # with gil
                # 计算range_ratio_is_less
                range_ratio_is_less = False
                if min_price is not None and min_price != 0 and not isnan(user_range_ratio):
                    range_ratio_is_less = (max_price / min_price) < user_range_ratio

                # 计算日期索引和n_max_is_max
                forward_max_date_idx = end_date_idx + max_idx_in_window if max_idx_in_window >= 0 else -1
                forward_min_date_idx = end_date_idx + min_idx_in_window if min_idx_in_window >= 0 else -1
                n_max_is_max_result = max_idx_in_window < n_days if n_days > 0 else False

                # 计算所有日期和值的组合
                max_value_date = date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None
                min_value_date = date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None
                end_value_date = date_columns[end_date_idx]
                start_value_date = date_columns[start_date_idx]
                actual_value_date = date_columns[actual_idx] if actual_idx >= 0 and actual_idx < num_dates else None
                closest_value_date = date_columns[end_date_idx + closest_idx_in_window] if closest_idx_in_window >= 0 else None
                
                # 计算日期字符串
                forward_max_date_str = date_columns[forward_max_date_idx] if forward_max_date_idx >= 0 else None
                forward_min_date_str = date_columns[forward_min_date_idx] if forward_min_date_idx >= 0 else None

                forward_min_valid_abs_sum_first_half = round_to_2(forward_min_valid_abs_sum_first_half)
                forward_min_valid_abs_sum_second_half = round_to_2(forward_min_valid_abs_sum_second_half)
                forward_min_valid_abs_sum_block1 = round_to_2(forward_min_valid_abs_sum_block1)
                forward_min_valid_abs_sum_block2 = round_to_2(forward_min_valid_abs_sum_block2)
                forward_min_valid_abs_sum_block3 = round_to_2(forward_min_valid_abs_sum_block3)
                forward_min_valid_abs_sum_block4 = round_to_2(forward_min_valid_abs_sum_block4)

                # 先定义所有表达式可能用到的参数变量
                continuous_start_value = cont_sum[0] if cont_sum.size() > 0 else None
                continuous_start_next_value = cont_sum[1] if cont_sum.size() > 1 else None
                continuous_start_next_next_value = cont_sum[2] if cont_sum.size() > 2 else None
                continuous_end_value = cont_sum[cont_sum.size()-1] if cont_sum.size() > 0 else None
                continuous_end_prev_value = cont_sum[cont_sum.size()-2] if cont_sum.size() > 1 else None
                continuous_end_prev_prev_value = cont_sum[cont_sum.size()-3] if cont_sum.size() > 2 else None

                # 最后只在返回时转为Python对象
                py_cont_sum = list(cont_sum)
                forward_max_result = [forward_max_result_c[j] for j in range(forward_max_result_c.size())]
                forward_min_result = [forward_min_result_c[j] for j in range(forward_min_result_c.size())]
                
                forward_max_valid_sum_arr = [forward_max_valid_sum_vec[j] for j in range(forward_max_valid_sum_vec.size())]
                forward_min_valid_sum_arr = [forward_min_valid_sum_vec[j] for j in range(forward_min_valid_sum_vec.size())]
                py_valid_sum_arr = [valid_sum_vec[j] for j in range(valid_sum_vec.size())]
                
                # 递增值等都算好后，计算 ops_value
                inc_value = increment_value
                age_value = after_gt_end_value
                ags_value = after_gt_start_value
                try:
                    result_value = user_func(inc_value, age_value, ags_value)
                    # 判断 result_value 是哪个变量，自动取 value 和 days
                    if result_value == 'increment_value':
                        ops_value = increment_value
                        hold_days = increment_days
                    elif result_value == 'after_gt_end_value':
                        ops_value = after_gt_end_value
                        hold_days = after_gt_end_days
                    elif result_value == 'after_gt_start_value':
                        ops_value = after_gt_start_value
                        hold_days = after_gt_start_days
                    else:
                        ops_value = result_value
                        hold_days = None
                except Exception as e:
                    ops_value = None
                    hold_days = None
                
                # 新增：计算操作涨幅、调整天数、日均涨幅
                ops_change = None
                adjust_days = None
                ops_incre_rate = None
                end_value_for_ops = end_value if not isnan(end_value) else None
                if ops_value is not None and end_value_for_ops not in (None, 0):
                    try:
                        ops_change = round_to_2((ops_value - end_value_for_ops) / end_value_for_ops * 100)
                    except Exception:
                        ops_change = None
                if ops_change is not None and ops_change_input is not None and hold_days is not None:
                    try:
                        if ops_change > ops_change_input and hold_days == 1:
                            adjust_days = round_to_2(op_days / 3.0)
                        else:
                            adjust_days = hold_days + 1
                    except Exception:
                        adjust_days = None
                if ops_change is not None and adjust_days not in (None, 0):
                    try:
                        ops_incre_rate = round_to_2(ops_change / adjust_days)
                    except Exception:
                        ops_incre_rate = None

                # 新增：score 计算
                score = None
                if formula_expr is not None:
                    # 预先计算所有需要的变量
                    formula_vars = {
                        'max_value': max_price,
                        'min_value': min_price,
                        'end_value': end_value,
                        'start_value': start_value,
                        'actual_value': actual_value,
                        'closest_value': closest_value,
                        'n_days_max_value': n_days_max_value,
                        'n_max_is_max': n_max_is_max_result,
                        'range_ratio_is_less': range_ratio_is_less,
                        'continuous_abs_is_less': continuous_abs_is_less,
                        'prev_day_change': prev_day_change,
                        'end_day_change': end_day_change,
                        'diff_end_value': diff_data_view[stock_idx, end_date_idx],
                        'continuous_results': py_cont_sum,
                        'continuous_len': continuous_len,
                        'continuous_start_value': continuous_start_value,
                        'continuous_start_next_value': continuous_start_next_value,
                        'continuous_start_next_next_value': continuous_start_next_next_value,
                        'continuous_end_value': continuous_end_value,
                        'continuous_end_prev_value': continuous_end_prev_value,
                        'continuous_end_prev_prev_value': continuous_end_prev_prev_value,
                        'continuous_abs_sum_first_half': continuous_abs_sum_first_half,
                        'continuous_abs_sum_second_half': continuous_abs_sum_second_half,
                        'continuous_abs_sum_block1': continuous_abs_sum_block1,
                        'continuous_abs_sum_block2': continuous_abs_sum_block2,
                        'continuous_abs_sum_block3': continuous_abs_sum_block3,
                        'continuous_abs_sum_block4': continuous_abs_sum_block4,
                        'valid_sum_arr': py_valid_sum_arr,
                        'valid_sum_len': valid_sum_len,
                        'valid_pos_sum': valid_pos_sum,
                        'valid_neg_sum': valid_neg_sum,
                        'valid_abs_sum_first_half': valid_abs_sum_first_half,
                        'valid_abs_sum_second_half': valid_abs_sum_second_half,
                        'valid_abs_sum_block1': valid_abs_sum_block1,
                        'valid_abs_sum_block2': valid_abs_sum_block2,
                        'valid_abs_sum_block3': valid_abs_sum_block3,
                        'valid_abs_sum_block4': valid_abs_sum_block4,
                        'forward_max_date': forward_max_date_str,
                        'forward_max_result': forward_max_result,
                        'forward_max_valid_sum_len': forward_max_valid_sum_len,
                        'forward_max_valid_sum_arr': forward_max_valid_sum_arr,
                        'forward_max_valid_pos_sum': forward_max_valid_pos_sum,
                        'forward_max_valid_neg_sum': forward_max_valid_neg_sum,
                        'forward_max_valid_abs_sum_first_half': forward_max_valid_abs_sum_first_half,
                        'forward_max_valid_abs_sum_second_half': forward_max_valid_abs_sum_second_half,
                        'forward_max_valid_abs_sum_block1': forward_max_valid_abs_sum_block1,
                        'forward_max_valid_abs_sum_block2': forward_max_valid_abs_sum_block2,
                        'forward_max_valid_abs_sum_block3': forward_max_valid_abs_sum_block3,
                        'forward_max_valid_abs_sum_block4': forward_max_valid_abs_sum_block4,
                        'forward_min_date': forward_min_date_str,
                        'forward_min_result': forward_min_result,
                        'forward_min_valid_sum_len': forward_min_valid_sum_len,
                        'forward_min_valid_sum_arr': forward_min_valid_sum_arr,
                        'forward_min_valid_pos_sum': forward_min_valid_pos_sum,
                        'forward_min_valid_neg_sum': forward_min_valid_neg_sum,
                        'forward_min_valid_abs_sum_first_half': forward_min_valid_abs_sum_first_half,
                        'forward_min_valid_abs_sum_second_half': forward_min_valid_abs_sum_second_half,
                        'forward_min_valid_abs_sum_block1': forward_min_valid_abs_sum_block1,
                        'forward_min_valid_abs_sum_block2': forward_min_valid_abs_sum_block2,
                        'forward_min_valid_abs_sum_block3': forward_min_valid_abs_sum_block3,
                        'forward_min_valid_abs_sum_block4': forward_min_valid_abs_sum_block4,
                        'increment_value': increment_value,
                        'after_gt_end_value': after_gt_end_value,
                        'after_gt_start_value': after_gt_start_value,
                        'ops_value': ops_value,
                        'hold_days': hold_days,
                        'ops_change': ops_change,
                        'adjust_days': adjust_days,
                        'ops_incre_rate': ops_incre_rate
                    }
                    
                    try:
                        exec(formula_expr, {}, formula_vars)
                        score = formula_vars.get('result', None)
                        if score is not None and score != 0:
                            score = round_to_2(score)
                    except Exception as e:
                        score = None
                if stock_idx == 0:
                    print(f'only_show_selected: {only_show_selected}')
                if only_show_selected:
                    if score is not None and score != 0 and not isnan(end_value) and hold_days != -1:
                        row_result = {
                            'stock_idx': stock_idx,
                            'max_value': [max_value_date, max_price],
                            'min_value': [min_value_date, min_price],
                            'end_value': [end_value_date, end_value],
                            'start_value': [start_value_date, start_value],
                            'actual_value': [actual_value_date, actual_value],
                            'closest_value': [closest_value_date, closest_value],
                            'continuous_results': py_cont_sum,
                            'continuous_len': continuous_len,
                            'continuous_start_value': continuous_start_value,
                            'continuous_start_next_value': continuous_start_next_value,
                            'continuous_start_next_next_value': continuous_start_next_next_value,
                            'continuous_end_value': continuous_end_value,
                            'continuous_end_prev_value': continuous_end_prev_value,
                            'continuous_end_prev_prev_value': continuous_end_prev_prev_value,
                            'continuous_abs_sum_first_half': continuous_abs_sum_first_half,
                            'continuous_abs_sum_second_half': continuous_abs_sum_second_half,
                            'continuous_abs_sum_block1': continuous_abs_sum_block1,
                            'continuous_abs_sum_block2': continuous_abs_sum_block2,
                            'continuous_abs_sum_block3': continuous_abs_sum_block3,
                            'continuous_abs_sum_block4': continuous_abs_sum_block4,
                            'forward_max_result': forward_max_result,
                            'forward_min_result': forward_min_result,
                            'valid_sum_arr': py_valid_sum_arr,
                            'valid_sum_len': valid_sum_len,
                            'valid_pos_sum': valid_pos_sum,
                            'valid_neg_sum': valid_neg_sum,
                            'forward_max_valid_sum_arr': forward_max_valid_sum_arr,
                            'forward_max_valid_sum_len': forward_max_valid_sum_len,
                            'forward_max_valid_pos_sum': forward_max_valid_pos_sum,
                            'forward_max_valid_neg_sum': forward_max_valid_neg_sum,
                            'forward_min_valid_sum_arr': forward_min_valid_sum_arr,
                            'forward_min_valid_sum_len': forward_min_valid_sum_len,
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
                            'forward_max_date': forward_max_date_str,
                            'forward_min_date': forward_min_date_str,
                            'n_max_is_max': n_max_is_max_result,
                            'range_ratio_is_less': range_ratio_is_less,
                            'continuous_abs_is_less': continuous_abs_is_less,
                            'n_days_max_value': n_days_max_value,
                            'prev_day_change': prev_day_change,
                            'end_day_change': end_day_change,
                            'diff_end_value': diff_data_view[stock_idx, end_date_idx],
                            'increment_value': increment_value,
                            'after_gt_end_value': after_gt_end_value,
                            'after_gt_start_value': after_gt_start_value,
                            'ops_value': ops_value,
                            'hold_days': hold_days,
                            'ops_change': ops_change,
                            'adjust_days': adjust_days,
                            'ops_incre_rate': ops_incre_rate,
                            'score': score,
                        }
                        current_stocks = all_results.get(date_columns[end_date_idx], [])
                        current_stocks.append(row_result)
                        # 按score排序
                        if sort_mode == "最大值排序":
                            current_stocks.sort(key=lambda x: x['score'], reverse=True)
                        else:  # 最小值排序
                            current_stocks.sort(key=lambda x: x['score'])
                        # 只保留指定数量的结果
                        all_results[date_columns[end_date_idx]] = current_stocks[:select_count]
                else:
                    row_result = {
                            'stock_idx': stock_idx,
                            'max_value': [max_value_date, max_price],
                            'min_value': [min_value_date, min_price],
                            'end_value': [end_value_date, end_value],
                            'start_value': [start_value_date, start_value],
                            'actual_value': [actual_value_date, actual_value],
                            'closest_value': [closest_value_date, closest_value],
                            'continuous_results': py_cont_sum,
                            'continuous_len': continuous_len,
                            'continuous_start_value': continuous_start_value,
                            'continuous_start_next_value': continuous_start_next_value,
                            'continuous_start_next_next_value': continuous_start_next_next_value,
                            'continuous_end_value': continuous_end_value,
                            'continuous_end_prev_value': continuous_end_prev_value,
                            'continuous_end_prev_prev_value': continuous_end_prev_prev_value,
                            'continuous_abs_sum_first_half': continuous_abs_sum_first_half,
                            'continuous_abs_sum_second_half': continuous_abs_sum_second_half,
                            'continuous_abs_sum_block1': continuous_abs_sum_block1,
                            'continuous_abs_sum_block2': continuous_abs_sum_block2,
                            'continuous_abs_sum_block3': continuous_abs_sum_block3,
                            'continuous_abs_sum_block4': continuous_abs_sum_block4,
                            'forward_max_result': forward_max_result,
                            'forward_min_result': forward_min_result,
                            'valid_sum_arr': py_valid_sum_arr,
                            'valid_sum_len': valid_sum_len,
                            'valid_pos_sum': valid_pos_sum,
                            'valid_neg_sum': valid_neg_sum,
                            'forward_max_valid_sum_arr': forward_max_valid_sum_arr,
                            'forward_max_valid_sum_len': forward_max_valid_sum_len,
                            'forward_max_valid_pos_sum': forward_max_valid_pos_sum,
                            'forward_max_valid_neg_sum': forward_max_valid_neg_sum,
                            'forward_min_valid_sum_arr': forward_min_valid_sum_arr,
                            'forward_min_valid_sum_len': forward_min_valid_sum_len,
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
                            'forward_max_date': forward_max_date_str,
                            'forward_min_date': forward_min_date_str,
                            'n_max_is_max': n_max_is_max_result,
                            'range_ratio_is_less': range_ratio_is_less,
                            'continuous_abs_is_less': continuous_abs_is_less,
                            'n_days_max_value': n_days_max_value,
                            'prev_day_change': prev_day_change,
                            'end_day_change': end_day_change,
                            'diff_end_value': diff_data_view[stock_idx, end_date_idx],
                            'increment_value': increment_value,
                            'after_gt_end_value': after_gt_end_value,
                            'after_gt_start_value': after_gt_start_value,
                            'ops_value': ops_value,
                            'hold_days': hold_days,
                            'ops_change': ops_change,
                            'adjust_days': adjust_days,
                            'ops_incre_rate': ops_incre_rate,
                            'score': score,
                        }
                    all_results[date_columns[end_date_idx]].append(row_result)
            except Exception as e:
                import traceback
                print(f"[calculate_batch_cy] stock_idx={stock_idx}, idx={idx} 发生异常: {e}")
                print(traceback.format_exc())
                
    return all_results