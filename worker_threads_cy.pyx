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

cdef void calc_valid_sum_and_pos_neg(double[:] arr, double* valid_sum, int* valid_len, double* pos_sum, double* neg_sum) nogil:
    cdef int n = arr.shape[0]
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
        abs_v = fabs(v)
        next_abs = fabs(arr[i+1]) if i < n-1 else 0
        if i < n-1 and next_abs > abs_v:
            valid_sum[valid_idx] = v
        elif i < n-1:
            valid_sum[valid_idx] = arr[i+1] if arr[i+1] >= 0 else -fabs(arr[i+1])
        else:
            valid_sum[valid_idx] = v
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
    str formula_expr=None
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
    cdef np.ndarray[np.float64_t, ndim=1] cont_sum_np
    cdef double prev_day_change = NAN
    cdef double end_day_change = NAN
    cdef double n_days_max_value = NAN
    cdef double price_arr[100]
    cdef int n_valid, half_valid, q1_valid, q2_valid, q3_valid
    cdef double valid_abs_sum_first_half, valid_abs_sum_second_half
    cdef double valid_abs_sum_block1, valid_abs_sum_block2, valid_abs_sum_block3, valid_abs_sum_block4
    cdef double forward_max_valid_sum_arr[1000]
    cdef int forward_max_valid_sum_len
    cdef double forward_max_valid_pos_sum, forward_max_valid_neg_sum
    cdef double forward_min_valid_sum_arr[1000]
    cdef int forward_min_valid_sum_len
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
    cdef int n_increment
    cdef double v, prev_v
    cdef int k
    cdef object user_func = None
    cdef object score_func = None
    from worker_threads import make_user_func
    user_func = make_user_func(expr)
    score_func = make_user_func(formula_expr) if formula_expr else None
    
    # 初始化结果字典
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        all_results[end_date] = []
    
    # 单线程处理每个股票
    for i in range(stock_idx_arr_view.shape[0]):
        stock_idx = stock_idx_arr_view[i]
        
        # 处理每个日期窗口
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            # --- nogil 区域 ---
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
                            increment_value = v
                            increment_days = n
                            found = True
                            break
                    if not found:
                        fallback_idx = end_date_idx - op_days
                        if fallback_idx >= 0:
                            increment_value = price_data_view[stock_idx, fallback_idx]
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
                            after_gt_end_value = v
                            after_gt_end_days = n
                            found = True
                            break
                    if not found:
                        fallback_idx = end_date_idx - op_days
                        if fallback_idx >= 0:
                            after_gt_end_value = price_data_view[stock_idx, fallback_idx]
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
                        after_gt_start_value = v_prev
                        after_gt_start_days = n
                        found = True
                        break
                if not found:
                    fallback_idx = end_date_idx - op_days
                    if fallback_idx >= 0:
                        after_gt_start_value = price_data_view[stock_idx, fallback_idx]
                        after_gt_start_days = op_days

            # --- with gil 区域 ---
            py_cont_sum = list(cont_sum)
            cont_sum_np = np.array(py_cont_sum, dtype=np.float64)
            calc_valid_sum_and_pos_neg(
                cont_sum_np, valid_sum_arr, &valid_sum_len, &valid_pos_sum, &valid_neg_sum)
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
            for j in range(half):
                continuous_abs_sum_first_half += abs(py_cont_sum[j])
            for j in range(half, n):
                continuous_abs_sum_second_half += abs(py_cont_sum[j])
            for j in range(q1):
                continuous_abs_sum_block1 += abs(py_cont_sum[j])
            for j in range(q1, q2):
                continuous_abs_sum_block2 += abs(py_cont_sum[j])
            for j in range(q2, q3):
                continuous_abs_sum_block3 += abs(py_cont_sum[j])
            for j in range(q3, n):
                continuous_abs_sum_block4 += abs(py_cont_sum[j])
            continuous_abs_sum_first_half = round_to_2(continuous_abs_sum_first_half)
            continuous_abs_sum_second_half = round_to_2(continuous_abs_sum_second_half)
            continuous_abs_sum_block1 = round_to_2(continuous_abs_sum_block1)
            continuous_abs_sum_block2 = round_to_2(continuous_abs_sum_block2)
            continuous_abs_sum_block3 = round_to_2(continuous_abs_sum_block3)
            continuous_abs_sum_block4 = round_to_2(continuous_abs_sum_block4)

            # 计算向前最大连续累加值
            if is_forward:
                # 向前最大有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_max_valid_sum_len = len(forward_max_result) if forward_max_result else 0
                if forward_max_valid_sum_len > 0:
                    abs_arr = np.abs(forward_max_result)
                    half = int(round(forward_max_valid_sum_len / 2.0))
                    forward_max_valid_abs_sum_first_half = round_to_2(np.sum(abs_arr[:half]))
                    forward_max_valid_abs_sum_second_half = round_to_2(np.sum(abs_arr[half:]))
                    # 分四块
                    n = len(abs_arr)
                    q1 = int(round(n / 4.0))
                    q2 = int(round(n / 2.0))
                    q3 = int(round(3 * n / 4.0))
                    forward_max_valid_abs_sum_block1 = round_to_2(np.sum(abs_arr[:q1]))
                    forward_max_valid_abs_sum_block2 = round_to_2(np.sum(abs_arr[q1:q2]))
                    forward_max_valid_abs_sum_block3 = round_to_2(np.sum(abs_arr[q2:q3]))
                    forward_max_valid_abs_sum_block4 = round_to_2(np.sum(abs_arr[q3:]))
                else:
                    forward_max_valid_abs_sum_first_half = 0
                    forward_max_valid_abs_sum_second_half = 0
                    forward_max_valid_abs_sum_block1 = 0
                    forward_max_valid_abs_sum_block2 = 0
                    forward_max_valid_abs_sum_block3 = 0
                    forward_max_valid_abs_sum_block4 = 0

                # 向前最小有效累加值数组长度，前一半绝对值之和、后一半绝对值之和
                forward_min_valid_sum_len = len(forward_min_result) if forward_min_result else 0
                if forward_min_valid_sum_len > 0:
                    abs_arr = np.abs(forward_min_result)
                    half = int(round(forward_min_valid_sum_len / 2.0))
                    forward_min_valid_abs_sum_first_half = round_to_2(np.sum(abs_arr[:half]))
                    forward_min_valid_abs_sum_second_half = round_to_2(np.sum(abs_arr[half:]))
                    # 分四块
                    n = len(abs_arr)
                    q1 = int(round(n / 4.0))
                    q2 = int(round(n / 2.0))
                    q3 = int(round(3 * n / 4.0))
                    forward_min_valid_abs_sum_block1 = round_to_2(np.sum(abs_arr[:q1]))
                    forward_min_valid_abs_sum_block2 = round_to_2(np.sum(abs_arr[q1:q2]))
                    forward_min_valid_abs_sum_block3 = round_to_2(np.sum(abs_arr[q2:q3]))
                    forward_min_valid_abs_sum_block4 = round_to_2(np.sum(abs_arr[q3:]))
                else:
                    forward_min_valid_abs_sum_first_half = 0
                    forward_min_valid_abs_sum_second_half = 0
                    forward_min_valid_abs_sum_block1 = 0
                    forward_min_valid_abs_sum_block2 = 0
                    forward_min_valid_abs_sum_block3 = 0
                    forward_min_valid_abs_sum_block4 = 0

            else:
                forward_max_valid_sum_len = 0
                forward_max_valid_abs_sum_first_half = None
                forward_max_valid_abs_sum_second_half = None
                forward_max_valid_abs_sum_block1 = None
                forward_max_valid_abs_sum_block2 = None
                forward_max_valid_abs_sum_block3 = None
                forward_max_valid_abs_sum_block4 = None
                forward_min_valid_sum_len = 0
                forward_min_valid_abs_sum_first_half = None
                forward_min_valid_abs_sum_second_half = None
                forward_min_valid_abs_sum_block1 = None
                forward_min_valid_abs_sum_block2 = None
                forward_min_valid_abs_sum_block3 = None
                forward_min_valid_abs_sum_block4 = None

            # 计算正累加和和负累加和
            valid_pos_sum, valid_neg_sum = valid_pos_sum, valid_neg_sum
            forward_max_valid_pos_sum, forward_max_valid_neg_sum = valid_pos_sum, valid_neg_sum
            forward_min_valid_pos_sum, forward_min_valid_neg_sum = valid_pos_sum, valid_neg_sum
            
            # 连续累加值绝对值最大值判断
            if continuous_abs_threshold == continuous_abs_threshold and len(py_cont_sum) > 0:
                max_abs_val = max([abs(v) for v in py_cont_sum])
                continuous_abs_is_less = max_abs_val < continuous_abs_threshold
            else:
                continuous_abs_is_less = False
            
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
            price_arr = np.empty(100, dtype=np.float64)
            for j in range(window_len):
                price_arr[j] = price_data_view[stock_idx, end_date_idx + j]
            if len(price_arr) >= 3:
                if price_arr[2] != 0 and not isnan(price_arr[2]):
                    prev_day_change = round_to_2(((price_arr[1] - price_arr[2]) / price_arr[2]) * 100)
                if price_arr[1] != 0 and not isnan(price_arr[1]):
                    end_day_change = round_to_2(((price_arr[0] - price_arr[1]) / price_arr[1]) * 100)
            elif len(price_arr) == 2:
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
                valid_abs_sum_first_half += abs(valid_sum_arr[j])
            for j in range(half_valid, n_valid):
                valid_abs_sum_second_half += abs(valid_sum_arr[j])
            for j in range(q1_valid):
                valid_abs_sum_block1 += abs(valid_sum_arr[j])
            for j in range(q1_valid, q2_valid):
                valid_abs_sum_block2 += abs(valid_sum_arr[j])
            for j in range(q2_valid, q3_valid):
                valid_abs_sum_block3 += abs(valid_sum_arr[j])
            for j in range(q3_valid, n_valid):
                valid_abs_sum_block4 += abs(valid_sum_arr[j])
            valid_abs_sum_first_half = round_to_2(valid_abs_sum_first_half)
            valid_abs_sum_second_half = round_to_2(valid_abs_sum_second_half)
            valid_abs_sum_block1 = round_to_2(valid_abs_sum_block1)
            valid_abs_sum_block2 = round_to_2(valid_abs_sum_block2)
            valid_abs_sum_block3 = round_to_2(valid_abs_sum_block3)
            valid_abs_sum_block4 = round_to_2(valid_abs_sum_block4)

            # 主连续累加值的有效累加值及正负加和
            calc_valid_sum_and_pos_neg(
                cont_sum_np, valid_sum_arr, &valid_sum_len, &valid_pos_sum, &valid_neg_sum)

            # forward_max_result 的有效累加值及正负加和
            if len(forward_max_result) > 0:
                calc_valid_sum_and_pos_neg(
                    np.array(forward_max_result, dtype=np.float64),
                    forward_max_valid_sum_arr, &forward_max_valid_sum_len,
                    &forward_max_valid_pos_sum, &forward_max_valid_neg_sum)
            else:
                forward_max_valid_sum_len = 0
                forward_max_valid_pos_sum = 0
                forward_max_valid_neg_sum = 0

            # forward_min_result 的有效累加值及正负加和
            if len(forward_min_result) > 0:
                calc_valid_sum_and_pos_neg(
                    np.array(forward_min_result, dtype=np.float64),
                    forward_min_valid_sum_arr, &forward_min_valid_sum_len,
                    &forward_min_valid_pos_sum, &forward_min_valid_neg_sum)
            else:
                forward_min_valid_sum_len = 0
                forward_min_valid_pos_sum = 0
                forward_min_valid_neg_sum = 0

            # 计算向前最大连续累加值的分块和绝对值之和（全部在Cython区完成）
            forward_max_result_len = forward_max_result_c.size()
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
                    v = fabs(forward_max_result_c[j])
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

            # 计算向前最小连续累加值的分块和绝对值之和（全部在Cython区完成）
            forward_min_result_len = forward_min_result_c.size()
            forward_min_valid_abs_sum_first_half = 0
            forward_min_valid_abs_sum_second_half = 0
            forward_min_valid_abs_sum_block1 = 0
            forward_min_valid_abs_sum_block2 = 0
            forward_min_valid_abs_sum_block3 = 0
            forward_min_valid_abs_sum_block4 = 0
            if is_forward and forward_min_result_len > 0:
                n = forward_min_result_len
                half = int(round(n / 2.0))
                q1 = int(round(n / 4.0))
                q2 = int(round(n / 2.0))
                q3 = int(round(3 * n / 4.0))
                for j in range(n):
                    v = fabs(forward_min_result_c[j])
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
                forward_min_valid_abs_sum_first_half = round_to_2(forward_min_valid_abs_sum_first_half)
                forward_min_valid_abs_sum_second_half = round_to_2(forward_min_valid_abs_sum_second_half)
                forward_min_valid_abs_sum_block1 = round_to_2(forward_min_valid_abs_sum_block1)
                forward_min_valid_abs_sum_block2 = round_to_2(forward_min_valid_abs_sum_block2)
                forward_min_valid_abs_sum_block3 = round_to_2(forward_min_valid_abs_sum_block3)
                forward_min_valid_abs_sum_block4 = round_to_2(forward_min_valid_abs_sum_block4)
            else:
                forward_min_valid_abs_sum_first_half = 0
                forward_min_valid_abs_sum_second_half = 0
                forward_min_valid_abs_sum_block1 = 0
                forward_min_valid_abs_sum_block2 = 0
                forward_min_valid_abs_sum_block3 = 0
                forward_min_valid_abs_sum_block4 = 0

            # 先定义所有表达式可能用到的参数变量
            continuous_start_value = cont_sum[0] if cont_sum.size() > 0 else None
            continuous_start_next_value = cont_sum[1] if cont_sum.size() > 1 else None
            continuous_start_next_next_value = cont_sum[2] if cont_sum.size() > 2 else None
            continuous_end_value = cont_sum[cont_sum.size()-1] if cont_sum.size() > 0 else None
            continuous_end_prev_value = cont_sum[cont_sum.size()-2] if cont_sum.size() > 1 else None
            continuous_end_prev_prev_value = cont_sum[cont_sum.size()-3] if cont_sum.size() > 2 else None

            # 最后只在返回时转为Python对象
            forward_max_result = [forward_max_result_c[j] for j in range(forward_max_result_c.size())]
            forward_min_result = [forward_min_result_c[j] for j in range(forward_min_result_c.size())]

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
        
            # 新增：score 计算
            score = None
            if score_func is not None:
                try:
                    score = score_func(
                        inc_value, age_value, ags_value
                    )
                    # 当 score 有值且不等于 0 时打印
                    if score is not None and score != 0 and stock_idx == 0:
                        print(f'[SCORE] stock_idx={stock_idx}, score={score}')
                except Exception:
                    score = None
            
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
                
            row_result = {
                'stock_idx': stock_idx,
                'max_value': [date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None, max_price],
                'min_value': [date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None, min_price],
                'end_value': [date_columns[end_date_idx], end_value],
                'start_value': [date_columns[start_date_idx], start_value],
                'actual_value': [date_columns[actual_idx] if actual_idx >= 0 and actual_idx < num_dates else None, actual_value],
                'closest_value': [date_columns[end_date_idx + closest_idx_in_window] if closest_idx_in_window >= 0 else None, closest_value],
                'continuous_results': py_cont_sum,
                'continuous_len': len(py_cont_sum),
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
                'valid_sum_arr': [valid_sum_arr[j] for j in range(valid_sum_len)],
                'valid_sum_len': valid_sum_len,
                'valid_pos_sum': valid_pos_sum,
                'valid_neg_sum': valid_neg_sum,
                'forward_max_valid_sum_arr': forward_max_result,
                'forward_max_valid_sum_len': forward_max_valid_sum_len,
                'forward_max_valid_pos_sum': forward_max_valid_pos_sum,
                'forward_max_valid_neg_sum': forward_max_valid_neg_sum,
                'forward_min_valid_sum_arr': forward_min_result,
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
                'forward_max_date': date_columns[end_date_idx + max_idx_in_window] if max_idx_in_window >= 0 else None,
                'forward_min_date': date_columns[end_date_idx + min_idx_in_window] if min_idx_in_window >= 0 else None,
                'n_max_is_max': max_idx_in_window < n_days if n_days > 0 else False,
                'range_ratio_is_less': (max_price / min_price) < user_range_ratio if min_price is not None and min_price != 0 and not isnan(user_range_ratio) else False,
                'continuous_abs_is_less': continuous_abs_is_less,
                'n_days_max_value': None if isnan(n_days_max_value) else n_days_max_value,
                'prev_day_change': None if isnan(prev_day_change) else prev_day_change,
                'end_day_change': None if isnan(end_day_change) else end_day_change,
                'diff_end_value': diff_data_view[stock_idx, end_date_idx],
                'increment_value': None if isnan(increment_value) else round_to_2(increment_value),
                'after_gt_end_value': None if isnan(after_gt_end_value) else round_to_2(after_gt_end_value),
                'after_gt_start_value': None if isnan(after_gt_start_value) else round_to_2(after_gt_start_value),
                'ops_value': None if ops_value is None or isnan(ops_value) else round_to_2(ops_value),
                'hold_days': hold_days,
                'ops_change': ops_change,
                'adjust_days': adjust_days,
                'ops_incre_rate': ops_incre_rate,
                'score': score,
            }
            all_results[date_columns[end_date_idx]].append(row_result)
    
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