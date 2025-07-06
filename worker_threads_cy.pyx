# distutils: language = c++
# cython: boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False
# distutils: extra_compile_args = /openmp
# distutils: extra_link_args = /openmp

import numpy as np
cimport numpy as np
from libc.math cimport isnan, fabs, round, ceil
from libcpp.vector cimport vector
from libc.stdio cimport printf
from libc.errno cimport errno
from libc.string cimport strerror

ctypedef np.float64_t DTYPE_t
from libc.math cimport NAN

cdef inline double round_to_2(double x) nogil:
    return round(x * 100.0) / 100.0

cdef inline double round_to_2_nan(double x) nogil:
    cdef double result = round(x * 100.0) / 100.0
    if result == 0:
        return NAN
    return result

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
        if v == 0:
            sign = last_sign  # 0继承前一个数的符号
        else:
            sign = 1.0 if v > 0 else -1.0
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
        if isnan(v):
            continue
        abs_v = fabs(v)
        next_abs = fabs(arr[i+1]) if i < n-1 else 0
        sign_v = 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)
        if i < n-1 and next_abs > abs_v:
            valid_sum.push_back(v)
        elif i < n-1:
            valid_sum.push_back(sign_v * fabs(arr[i+1]))
        else:
            # 最后一个元素不做处理，不添加进valid_sum
            continue
        if valid_sum[valid_idx] > 0:
            pos_sum[0] += valid_sum[valid_idx]
        elif valid_sum[valid_idx] < 0:
            neg_sum[0] += valid_sum[valid_idx]
        valid_idx += 1
    valid_len[0] = valid_idx

cdef void calc_pos_neg_sum(vector[double]& arr, double* pos_sum, double* neg_sum) nogil:
    cdef int n = arr.size()
    cdef int i
    cdef double v
    pos_sum[0] = 0
    neg_sum[0] = 0
    for i in range(n):
        v = arr[i]
        if isnan(v):
            continue
        if v > 0:
            pos_sum[0] += v
        elif v < 0:
            neg_sum[0] += v

cdef void calc_pos_neg_sum_halves(
    vector[double]& arr,
    double* pos_sum_first_half,
    double* pos_sum_second_half,
    double* neg_sum_first_half,
    double* neg_sum_second_half
) nogil:
    cdef int n = arr.size()
    cdef int i, half
    cdef double v
    cdef vector[double] pos_values
    cdef vector[double] neg_values
    
    pos_sum_first_half[0] = 0
    pos_sum_second_half[0] = 0
    neg_sum_first_half[0] = 0
    neg_sum_second_half[0] = 0
    
    if n == 0:
        return
    
    # 分离正负值
    for i in range(n):
        v = arr[i]
        if isnan(v):
            continue
        if v > 0:
            pos_values.push_back(v)
        elif v < 0:
            neg_values.push_back(v)
    
    # 计算正值的分半累加
    if pos_values.size() > 0:
        half = int(round(pos_values.size() / 2.0))
        # 前一半
        for i in range(half):
            pos_sum_first_half[0] += pos_values[i]
        # 后一半
        for i in range(half, pos_values.size()):
            pos_sum_second_half[0] += pos_values[i]
    
    # 计算负值的分半累加
    if neg_values.size() > 0:
        half = int(round(neg_values.size() / 2.0))
        # 前一半
        for i in range(half):
            neg_sum_first_half[0] += neg_values[i]
        # 后一半
        for i in range(half, neg_values.size()):
            neg_sum_second_half[0] += neg_values[i]

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
    double valid_abs_sum_threshold,
    int n_days_max,
    int op_days,
    double inc_rate,
    double after_gt_end_ratio,
    double after_gt_start_ratio,
    double stop_loss_inc_rate,
    double stop_loss_after_gt_end_ratio,
    double stop_loss_after_gt_start_ratio,
    str expr,
    double ops_change_input=0.09,
    str formula_expr=None,
    int select_count=10,
    str sort_mode="最大值排序",
    bint trade_t1_mode=False,
    bint only_show_selected=False,
    int new_before_high_start=0,
    int new_before_high_range=0,
    int new_before_high_span=0,
    str new_before_high_logic="与",
    int new_before_high2_start=0,
    int new_before_high2_range=0,
    int new_before_high2_span=0,
    str new_before_high2_logic="与",
    int new_after_high_start=0,
    int new_after_high_range=0,
    int new_after_high_span=0,
    str new_after_high_logic="与",
    int new_after_high2_start=0,
    int new_after_high2_range=0,
    int new_after_high2_span=0,
    str new_after_high2_logic="与",
    int new_before_low_start=0,
    int new_before_low_range=0,
    int new_before_low_span=0,
    str new_before_low_logic="与",
    int new_before_low2_start=0,
    int new_before_low2_range=0,
    int new_before_low2_span=0,
    str new_before_low2_logic="与",
    int new_after_low_start=0,
    int new_after_low_range=0,
    int new_after_low_span=0,
    str new_after_low_logic="与",
    int new_after_low2_start=0,
    int new_after_low2_range=0,
    int new_after_low2_span=0,
    str new_after_low2_logic="与",
    bint start_with_new_before_high_flag=False,
    bint start_with_new_before_high2_flag=False,
    bint start_with_new_after_high_flag=False,
    bint start_with_new_after_high2_flag=False,
    bint start_with_new_before_low_flag=False,
    bint start_with_new_before_low2_flag=False,
    bint start_with_new_after_low_flag=False,
    bint start_with_new_after_low2_flag=False,
    list comparison_vars_list=None
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
    cdef double valid_pos_sum = NAN
    cdef double valid_neg_sum = NAN
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
    cdef int end_state = 0
    cdef double increment_threshold
    cdef double after_gt_end_threshold
    cdef double after_gt_start_threshold
    cdef double stop_loss_inc_threshold
    cdef double stop_loss_after_gt_end_threshold
    cdef double stop_loss_after_gt_start_threshold
    cdef double v
    cdef int k
    cdef object user_func = None
    from worker_threads import make_user_func, abbr_map
    user_func = make_user_func(expr)
    cdef double max_abs_val
    cdef double abs_v
    cdef bint continuous_abs_is_less
    cdef bint valid_abs_is_less
    cdef bint forward_max_continuous_abs_is_less
    cdef bint forward_max_valid_abs_is_less
    cdef bint forward_min_continuous_abs_is_less
    cdef bint forward_min_valid_abs_is_less
    cdef int new_before_high_start_idx, found_new_before_high, span_offset, check_idx
    cdef int new_before_high2_start_idx, found_new_before_high2
    cdef int new_after_high_start_idx, found_new_after_high
    cdef int new_after_high2_start_idx, found_new_after_high2
    cdef double cur_val, max_val, min_val
    cdef bint start_with_new_before_high, start_with_new_before_high2
    cdef bint start_with_new_after_high, start_with_new_after_high2

    cdef bint start_with_new_before_low, start_with_new_before_low2
    cdef bint start_with_new_after_low, start_with_new_after_low2
    cdef int new_before_low_start_idx, found_before_new_low
    cdef int new_before_low2_start_idx, found_new_before_low2
    cdef int new_after_low_start_idx, found_new_after_low
    cdef int new_after_low2_start_idx, found_new_after_low2
    cdef double cont_sum_pos_sum = NAN
    cdef double cont_sum_neg_sum = NAN  # 连续累加值正加和、负加和
    cdef double cont_sum_pos_sum_first_half = NAN
    cdef double cont_sum_pos_sum_second_half = NAN
    cdef double cont_sum_neg_sum_first_half = NAN
    cdef double cont_sum_neg_sum_second_half = NAN
    cdef double forward_max_cont_sum_pos_sum = NAN
    cdef double forward_max_cont_sum_neg_sum = NAN
    cdef double forward_min_cont_sum_pos_sum = NAN
    cdef double forward_min_cont_sum_neg_sum = NAN

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

    cdef double forward_max_price, forward_min_price
    cdef int forward_max_idx_in_window, forward_min_idx_in_window

    
    # 初始化结果字典
    for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
        end_date = date_columns[idx]
        all_results[end_date] = []
    
    # 单线程处理每个股票
    for i in range(stock_idx_arr_view.shape[0]):
        stock_idx = stock_idx_arr_view[i]
        if stock_idx == 0:
            printf(b"Calculating stock_idx=%d\n", stock_idx)
            printf(b"only_show_selected=%d\n", only_show_selected)
        for idx in range(end_date_start_idx, end_date_end_idx-1, -1):
            try:
                with nogil:
                    # --- 创前新高1起始条件判断 ---
                    if start_with_new_before_high_flag:
                        new_before_high_start_idx = idx + new_before_high_start
                        found_new_before_high = 0
                        if new_before_high_logic == "与":
                            found_new_before_high = 1
                            for span_offset in range(new_before_high_span):
                                check_idx = new_before_high_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                #if stock_idx == 3:
                                    #printf(b"new_before_high_start_idx=%d, span_offset=%d\n", new_before_high_start_idx, span_offset)
                                for k in range(check_idx + 1, check_idx + new_before_high_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                
                                #if stock_idx == 3:
                                    #printf(b"new_before_high and logic, cur_val=%f, max_val=%f\n", cur_val, max_val)
                                    #printf(b"New High Check: stock_idx=%d, span_offset=%d, new_high_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_before_high_span, check_idx, check_idx + new_before_high_range + 1, check_idx + 1)
                                if not has_valid_value or isnan(cur_val):
                                    found_new_before_high = 0
                                    continue
                                if cur_val <= max_val:
                                    found_new_before_high = 0
                                    break
                        else:
                            for span_offset in range(new_before_high_span):
                                check_idx = new_before_high_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                #if stock_idx == 3:
                                    #printf(b"new_before_high_start_idx=%d, span_offset=%d\n", new_before_high_start_idx, span_offset)
                                for k in range(check_idx + 1, check_idx + new_before_high_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    #if stock_idx == 3:
                                        #printf(b"k=%d, v=%d\n", k, v)
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                #if stock_idx == 3:
                                    #printf(b"new_before_high or logic, cur_val=%f, max_val=%f\n", cur_val, max_val)
                                    #printf(b"New High Check: stock_idx=%d, span_offset=%d, new_high_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_before_high_span, check_idx, check_idx + new_before_high_range + 1, check_idx + 1)
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val > max_val:
                                    found_new_before_high = 1
                                    break
                        start_with_new_before_high = found_new_before_high == 1
                        # 如果没有创前新高1，跳过后续计算
                        if not start_with_new_before_high:
                            continue

                    # --- 创前新高2起始条件判断 ---
                    if start_with_new_before_high2_flag:
                        new_before_high2_start_idx = idx + new_before_high2_start
                        found_new_before_high2 = 0
                        if new_before_high2_logic == "与":
                            found_new_before_high2 = 1
                            for span_offset in range(new_before_high2_span):
                                check_idx = new_before_high2_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_high2_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                
                                #if stock_idx == 2:
                                    #printf(b"new_before_high2 and logic, cur_val=%f, max_val=%f, has_valid_value=%d\n", cur_val, max_val, has_valid_value)
                                    #printf(b"New High2 Check: stock_idx=%d, span_offset=%d, new_high2_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_before_high2_span, check_idx, check_idx + new_before_high2_range + 1, check_idx + 1)
                                if not has_valid_value or isnan(cur_val):
                                    found_new_before_high2 = 0
                                    continue
                                if cur_val <= max_val:
                                    found_new_before_high2 = 0
                                    break
                        else:
                            for span_offset in range(new_before_high2_span):
                                check_idx = new_before_high2_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_high2_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                #if stock_idx == 2:
                                    #printf(b"new_before_high2 or logic, cur_val=%f, max_val=%f, has_valid_value=%d \n", cur_val, max_val, has_valid_value)
                                    #printf(b"New High2 Check: stock_idx=%d, span_offset=%d, new_high2_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_before_high2_span, check_idx, check_idx + new_before_high2_range + 1, check_idx + 1)
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val > max_val:
                                    found_new_before_high2 = 1
                                    break
                        start_with_new_before_high2 = found_new_before_high2 == 1

                        #if stock_idx == 2:
                            #printf(b"stock_idx=%d, start_with_new_before_high=%d, found_new_before_high=%d, start_with_new_before_high2=%d, found_new_before_high2=%d\n", stock_idx, start_with_new_before_high, found_new_before_high, start_with_new_before_high2, found_new_before_high2)
                        # 如果没有创前新高2，跳过后续计算
                        if not start_with_new_before_high2:
                            continue

                    
                    # --- 创后新高起始条件判断 --- 
                    if start_with_new_after_high_flag:
                        new_after_high_start_idx = idx + new_after_high_start + new_after_high_range
                        found_new_after_high = 0
                        if new_after_high_logic == "与":
                            found_new_after_high = 1
                            for span_offset in range(new_after_high_span):
                                check_idx = new_after_high_start_idx + span_offset 
                                #if stock_idx == 0:
                                    #printf(b"New After High1 Check: new_after_high_start_idx=%d, check_idx=%d, span_offset=%d, new_after_high_start=%d, new_after_high_range=%d\n",new_after_high_start_idx, check_idx, span_offset, new_after_high_start, new_after_high_range)
                                    #printf(b"New After High1 Check: stock_idx=%d, new_after_high_span=%d, range: %d ~ %d\n", stock_idx, new_after_high_span, check_idx - new_after_high_range, check_idx)
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_high_range, check_idx):
                                    #if stock_idx == 0:
                                        #printf(b"k = %d\n", k)
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                
                                #if stock_idx == 2:
                                    #printf(b"new_after_high and logic, cur_val=%f, max_val=%f, has_valid_value=%d\n", cur_val, max_val, has_valid_value)
                                    #printf(b"New After High Check: stock_idx=%d, span_offset=%d, new_high_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_after_high_span, check_idx, check_idx - new_after_high_range, check_idx)
                                if not has_valid_value or isnan(cur_val):
                                    found_new_after_high = 0
                                    continue
                                if cur_val <= max_val:
                                    found_new_after_high = 0
                                    break
                        else:
                            for span_offset in range(new_after_high_span):
                                check_idx = new_after_high_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                #if stock_idx == 2:
                                    #printf(b"New After High1 or Check: new_after_high_start_idx=%d, check_idx=%d, span_offset=%d, new_after_high_start=%d, new_after_high_range=%d\n",new_after_high_start_idx, check_idx, span_offset, new_after_high_start, new_after_high_range)
                                    #printf(b"New After High1 or Check: stock_idx=%d, new_after_high_span=%d, range: %d ~ %d\n", stock_idx, new_after_high_span, check_idx - new_after_high_range, check_idx)
                                for k in range(check_idx - new_after_high_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    #if stock_idx == 2:
                                        #printf(b"k = %d\n", k)
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                #if stock_idx == 2:
                                    #printf(b"new_after_high1 or logic, cur_val=%f, max_val=%f, has_valid_value=%d \n", cur_val, max_val, has_valid_value)
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val > max_val:
                                    found_new_after_high = 1
                                    break
                        start_with_new_after_high = found_new_after_high == 1
                        # 如果没有创后新高1，跳过后续计算
                        if not start_with_new_after_high:
                            continue

                    # --- 创后新高2起始条件判断 ---
                    if start_with_new_after_high2_flag:
                        new_after_high2_start_idx = idx + new_after_high2_start + new_after_high2_range
                        found_new_after_high2 = 0
                        if new_after_high2_logic == "与":
                            found_new_after_high2 = 1
                            for span_offset in range(new_after_high2_span):
                                check_idx = new_after_high2_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_high2_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                
                                #if stock_idx == 2:
                                    #printf(b"new_after_high2 and logic, cur_val=%f, max_val=%f, has_valid_value=%d\n", cur_val, max_val, has_valid_value)
                                    #printf(b"New After High2 Check: stock_idx=%d, span_offset=%d, new_high2_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_after_high2_span, check_idx, check_idx - new_after_high2_range, check_idx)
                                if not has_valid_value or isnan(cur_val):
                                    found_new_after_high2 = 0
                                    continue
                                if cur_val <= max_val:
                                    found_new_after_high2 = 0
                                    break
                        else:
                            for span_offset in range(new_after_high2_span):
                                check_idx = new_after_high2_start_idx + span_offset
                                cur_val = price_data_view[stock_idx, check_idx]
                                max_val = -1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_high2_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v > max_val:
                                        max_val = v
                                #if stock_idx == 2:
                                    #printf(b"new_after_high2 or logic, cur_val=%f, max_val=%f, has_valid_value=%d \n", cur_val, max_val, has_valid_value)
                                    #printf(b"New After High2 Check: stock_idx=%d, span_offset=%d, new_high2_span=%d, check_idx=%d, range: %d ~ %d\n", stock_idx, span_offset, new_after_high2_span, check_idx, check_idx - new_after_high2_range, check_idx)
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val > max_val:
                                    found_new_after_high2 = 1
                                    break
                        start_with_new_after_high2 = found_new_after_high2 == 1
                        # 如果没有创后新高2，跳过后续计算
                        if not start_with_new_after_high2:
                            continue

                    #if stock_idx == 2:
                        #printf(b"stock_idx=%d, start_with_new_after_high=%d, found_new_after_high=%d, start_with_new_after_high2=%d, found_new_after_high2=%d\n", stock_idx, start_with_new_after_high, found_new_after_high, start_with_new_after_high2, found_new_after_high2)

                    # --- 创前新低1起始条件判断 ---
                    if start_with_new_before_low_flag:
                        new_before_low_start_idx = idx + new_before_low_start
                        found_before_new_low = 0
                        if new_before_low_logic == "与":
                            found_before_new_low = 1
                            for span_offset in range(new_before_low_span):
                                check_idx = new_before_low_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_before_low_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_low_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    found_before_new_low = 0
                                    break
                                if cur_val >= min_val:
                                    found_before_new_low = 0
                                    break
                        else:  # "或"逻辑
                            for span_offset in range(new_before_low_span):
                                check_idx = new_before_low_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_before_low_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_low_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val < min_val:
                                    found_before_new_low = 1
                                    break
                        start_with_new_before_low = found_before_new_low == 1
                        # 如果没有创前新低1，跳过后续计算
                        if not start_with_new_before_low:
                            continue

                    # --- 创前新低2起始条件判断 ---
                    if start_with_new_before_low2_flag:
                        new_before_low2_start_idx = idx + new_before_low2_start
                        found_new_before_low2 = 0
                        if new_before_low2_logic == "与":
                            found_new_before_low2 = 1
                            for span_offset in range(new_before_low2_span):
                                check_idx = new_before_low2_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_before_low2_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_low2_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    found_new_before_low2 = 0
                                    break
                                if cur_val >= min_val:
                                    found_new_before_low2 = 0
                                    break
                        else:  # "或"逻辑
                            for span_offset in range(new_before_low2_span):
                                check_idx = new_before_low2_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_before_low2_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx + 1, check_idx + new_before_low2_range + 1):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val < min_val:
                                    found_new_before_low2 = 1
                                    break
                        start_with_new_before_low2 = found_new_before_low2 == 1
                        # 如果没有创前新低2，跳过后续计算
                        if not start_with_new_before_low2:
                            continue

                    # --- 创后新低1起始条件判断 ---
                    if start_with_new_after_low_flag:
                        new_after_low_start_idx = idx + new_after_low_start + new_after_low_range
                        found_new_after_low = 0
                        if new_after_low_logic == "与":
                            found_new_after_low = 1
                            for span_offset in range(new_after_low_span):
                                check_idx = new_after_low_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_after_low_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_low_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    found_new_after_low = 0
                                    break
                                if cur_val >= min_val:
                                    found_new_after_low = 0
                                    break
                        else:  # "或"逻辑
                            for span_offset in range(new_after_low_span):
                                check_idx = new_after_low_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_after_low_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_low_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val < min_val:
                                    found_new_after_low = 1
                                    break
                        start_with_new_after_low = found_new_after_low == 1
                        # 如果没有创后新低1，跳过后续计算
                        if not start_with_new_after_low:
                            continue

                    # --- 创后新低2起始条件判断 ---
                    if start_with_new_after_low2:
                        new_after_low2_start_idx = idx + new_after_low2_start + new_after_low2_range
                        found_new_after_low2 = 0
                        if new_after_low2_logic == "与":
                            found_new_after_low2 = 1
                            for span_offset in range(new_after_low2_span):
                                check_idx = new_after_low2_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_after_low2_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_low2_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    found_new_after_low2 = 0
                                    break
                                if cur_val >= min_val:
                                    found_new_after_low2 = 0
                                    break
                        else:  # "或"逻辑
                            for span_offset in range(new_after_low2_span):
                                check_idx = new_after_low2_start_idx + span_offset
                                if check_idx >= price_data_view.shape[1] or check_idx + new_after_low2_range >= price_data_view.shape[1]:
                                    continue
                                cur_val = price_data_view[stock_idx, check_idx]
                                min_val = 1e308
                                has_valid_value = 0
                                for k in range(check_idx - new_after_low2_range, check_idx):
                                    v = price_data_view[stock_idx, k]
                                    if isnan(v) or v == 0:
                                        continue
                                    has_valid_value = 1
                                    if v < min_val:
                                        min_val = v
                                if not has_valid_value or isnan(cur_val):
                                    continue
                                if cur_val < min_val:
                                    found_new_after_low2 = 1
                                    break
                        start_with_new_after_low2 = found_new_after_low2 == 1
                        # 如果没有创后新低2，跳过后续计算
                        if not start_with_new_after_low2:
                            continue
                    # 原有的with nogil内容
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
                        for j in range(1, window_len):  # j=0为结束日自身，跳过
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
                    # 计算连续累加值正加和与负加和
                    calc_pos_neg_sum(cont_sum, &cont_sum_pos_sum, &cont_sum_neg_sum)

                    cont_sum_pos_sum = round_to_2_nan(cont_sum_pos_sum)
                    cont_sum_neg_sum = round_to_2_nan(cont_sum_neg_sum)

                    # 计算连续累加值正负加值的前一半、后一半累加值
                    calc_pos_neg_sum_halves(cont_sum, &cont_sum_pos_sum_first_half, &cont_sum_pos_sum_second_half, &cont_sum_neg_sum_first_half, &cont_sum_neg_sum_second_half)

                    cont_sum_pos_sum_first_half = round_to_2_nan(cont_sum_pos_sum_first_half)
                    cont_sum_pos_sum_second_half = round_to_2_nan(cont_sum_pos_sum_second_half)
                    cont_sum_neg_sum_first_half = round_to_2_nan(cont_sum_neg_sum_first_half)
                    cont_sum_neg_sum_second_half = round_to_2_nan(cont_sum_neg_sum_second_half)

                    # 计算向前最大连续累加值
                    if is_forward and actual_idx > 0:
                        forward_max_price = -1e308
                        forward_min_price = 1e308
                        forward_max_idx_in_window = -1
                        forward_min_idx_in_window = -1
                        window = price_data_view[stock_idx, end_date_idx:actual_idx]
                        for j in range(window.shape[0]):
                            v = window[j]
                            if not isnan(v):
                                if v > forward_max_price:
                                    forward_max_price = v
                                    forward_max_idx_in_window = j
                                if v < forward_min_price:
                                    forward_min_price = v
                                    forward_min_idx_in_window = j
                        forward_max_date_idx = end_date_idx + forward_max_idx_in_window if forward_max_idx_in_window >= 0 else -1
                        forward_min_date_idx = end_date_idx + forward_min_idx_in_window if forward_min_idx_in_window >= 0 else -1

                        # 2. 计算向前最大连续累加值
                        if forward_max_idx_in_window >= 0:
                            calc_continuous_sum(
                                diff_data_view[stock_idx, end_date_idx:forward_max_date_idx][::-1],
                                forward_max_result_c
                            )
                        else:
                            forward_max_result_c.clear()

                        # 3. 计算向前最小连续累加值
                        if forward_min_idx_in_window >= 0:
                            calc_continuous_sum(
                                diff_data_view[stock_idx, end_date_idx:forward_min_date_idx][::-1],
                                forward_min_result_c
                            )
                        else:
                            forward_min_result_c.clear()
                    else:
                        forward_max_result_c.clear()
                        forward_min_result_c.clear()

                    #计算向前最大最小连续累加值正加和与负加和
                    calc_pos_neg_sum(forward_max_result_c, &forward_max_cont_sum_pos_sum, &forward_max_cont_sum_neg_sum)
                    forward_max_cont_sum_pos_sum = round_to_2_nan(forward_max_cont_sum_pos_sum)
                    forward_max_cont_sum_neg_sum = round_to_2_nan(forward_max_cont_sum_neg_sum)

                    calc_pos_neg_sum(forward_min_result_c, &forward_min_cont_sum_pos_sum, &forward_min_cont_sum_neg_sum)
                    forward_min_cont_sum_pos_sum = round_to_2_nan(forward_min_cont_sum_pos_sum)
                    forward_min_cont_sum_neg_sum = round_to_2_nan(forward_min_cont_sum_neg_sum)
                    # 递增值计算逻辑
                    increment_value = NAN
                    increment_days = -1
                    after_gt_end_value = NAN
                    after_gt_end_days = -1
                    after_gt_start_value = NAN
                    after_gt_start_days = -1
                    increment_change = NAN
                    after_gt_end_change = NAN
                    after_gt_start_change = NAN
                
                    if op_days > 0:
                        end_value = price_data_view[stock_idx, end_date_idx]
                        if not isnan(end_value):
                            # 递增值
                            found = False
                            for n, k in enumerate(range(end_date_idx - 1, end_date_idx - op_days - 1, -1), 1):
                                if k < 0:
                                    break
                                v = price_data_view[stock_idx, k]
                                if isnan(v) or (trade_t1_mode and n == 1):
                                    continue
                                increment_threshold = end_value * inc_rate * n
                                stop_loss_inc_threshold = end_value * stop_loss_inc_rate * n
                                if increment_threshold != 0 and (v - end_value) > increment_threshold:
                                    increment_value = round_to_2(v)
                                    increment_days = n
                                    increment_change = inc_rate * n * 100
                                    found = True
                                    end_state = 1
                                    break
                                #if stock_idx == 2164:
                                    #printf("stock_idx=%d, n=%d, v=%.2f, end_value=%.2f, stop_loss_inc_rate=%.4f, stop_loss_inc_threshold=%.2f\n", 
                                           #stock_idx, n, v, end_value, stop_loss_inc_rate, stop_loss_inc_threshold)
                                if stop_loss_inc_threshold != 0 and (v - end_value) < stop_loss_inc_threshold:
                                    increment_value = round_to_2(v)
                                    increment_days = n
                                    increment_change = stop_loss_inc_rate * n * 100
                                    found = True
                                    end_state = 2
                                    break
                            if not found:
                                increment_value = NAN
                                increment_days = -1
                                increment_change = NAN

                            # after_gt_end_value 计算（方向：end_date_idx-1 向 end_date_idx-op_days）
                            found = False
                            for n, k in enumerate(range(end_date_idx - 1, end_date_idx - op_days - 1, -1), 1):
                                if k < 0:
                                    break
                                v = price_data_view[stock_idx, k]
                                if isnan(v) or (trade_t1_mode and n == 1):
                                    continue
                                after_gt_end_threshold = end_value * after_gt_end_ratio
                                # 计算止损阈值
                                stop_loss_after_gt_end_threshold = end_value * stop_loss_after_gt_end_ratio
                                #if stock_idx == 2164:
                                    #printf("stock_idx=%d, n=%d, v=%.2f, end_value=%.2f, after_gt_end_ratio=%.4f, after_gt_end_threshold=%.2f\n", 
                                           #stock_idx, n, v, end_value, after_gt_end_ratio, after_gt_end_threshold)
                                if after_gt_end_ratio != 0 and (v - end_value) > after_gt_end_threshold:
                                    after_gt_end_value = round_to_2(v)
                                    after_gt_end_days = n
                                    after_gt_end_change = after_gt_end_ratio * 100
                                    found = True
                                    end_state = 1
                                    break

                                #if stock_idx == 2164:
                                    #printf("stock_idx=%d, n=%d, v=%.2f, end_value=%.2f, stop_loss_after_gt_end_ratio=%.4f, stop_loss_after_gt_end_threshold=%.2f\n", 
                                           #stock_idx, n, v, end_value, stop_loss_after_gt_end_ratio, stop_loss_after_gt_end_threshold)
                                if stop_loss_after_gt_end_ratio != 0 and (v - end_value) < stop_loss_after_gt_end_threshold:
                                    after_gt_end_value = round_to_2(v)
                                    after_gt_end_days = n
                                    after_gt_end_change = stop_loss_after_gt_end_ratio * 100
                                    found = True
                                    end_state = 2
                                    break
                            if not found:
                                after_gt_end_value = NAN
                                after_gt_end_days = -1
                            # after_gt_start_value 计算（方向：end_date_idx 向 end_date_idx-op_days，判断k和k-1）
                            found = False
                            for n, k in enumerate(range(end_date_idx, end_date_idx - op_days, -1), 1):
                                if k - 1 < 0 or k >= num_dates:
                                    continue
                                v_now = price_data_view[stock_idx, k]
                                v_prev = price_data_view[stock_idx, k - 1]
                                if isnan(v_now) or isnan(v_prev) or (trade_t1_mode and n == 1):
                                    continue
                                after_gt_start_threshold = v_now * after_gt_start_ratio
                                # 计算止损阈值
                                stop_loss_after_gt_start_threshold = v_now * stop_loss_after_gt_start_ratio
                                if after_gt_start_ratio != 0 and (v_prev - v_now) > after_gt_start_threshold:
                                    after_gt_start_value = round_to_2(v_prev)
                                    after_gt_start_days = n
                                    # 计算 after_gt_start_change：满足条件那一天的前一天价格与结束日价格的关系
                                    if n == 1:
                                        after_gt_start_change = after_gt_start_ratio * 100
                                    else:
                                        after_gt_start_change = round_to_2(((1 + (v_now - end_value) / end_value) * (1 + after_gt_start_ratio) - 1) * 100)
                                    #if stock_idx == 5377:
                                        #printf("stock_idx=%d, n=%d, v_now=%.2f, v_prev=%.2f, end_value=%.2f, after_gt_start_ratio=%.4f, after_gt_start_change=%.2f\n", 
                                            #stock_idx, n, v_now, v_prev, end_value, after_gt_start_ratio, after_gt_start_change)
                                    end_state = 1
                                    found = True
                                    break
                                
                                if stop_loss_after_gt_start_ratio != 0 and (v_prev - v_now) < stop_loss_after_gt_start_threshold:
                                    after_gt_start_value = round_to_2(v_prev)
                                    after_gt_start_days = n
                                    # 计算 after_gt_start_change：满足条件那一天的前一天价格与结束日价格的关系
                                    if n == 1:
                                        after_gt_start_change = stop_loss_after_gt_start_ratio * 100
                                    else:
                                        after_gt_start_change = round_to_2(((1 + (v_now - end_value) / end_value) * (1 + stop_loss_after_gt_start_ratio) - 1) * 100)
                                    end_state = 2
                                    found = True
                                    break
                                
                            
                            if not found:
                                after_gt_start_value = NAN
                                after_gt_start_days = -1
                                after_gt_start_change = NAN

                    #if stock_idx == 5377:
                        #printf("stock_idx=%d, increment_value=%.2f, increment_days=%d, after_gt_end_value=%.2f, after_gt_end_days=%d, after_gt_start_value=%.2f, after_gt_start_days=%d, increment_change=%.2f, after_gt_end_change=%.2f, after_gt_start_change=%.2f\n", 
                               #stock_idx, increment_value, increment_days, after_gt_end_value, after_gt_end_days, after_gt_start_value, after_gt_start_days, increment_change, after_gt_end_change, after_gt_start_change)
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
                    q1 = <int>ceil(n / 4.0)
                    continuous_abs_sum_first_half = 0
                    continuous_abs_sum_second_half = 0
                    continuous_abs_sum_block1 = 0
                    continuous_abs_sum_block2 = 0
                    continuous_abs_sum_block3 = 0
                    continuous_abs_sum_block4 = 0
                    # 前一半
                    for j in range(half):
                        continuous_abs_sum_first_half += fabs(cont_sum[j])
                    # 后一半
                    for j in range(n - half, n):
                        continuous_abs_sum_second_half += fabs(cont_sum[j])
                    # block1: 前q1
                    for j in range(min(q1, n)):
                        continuous_abs_sum_block1 += fabs(cont_sum[j])
                    # block2: q1~2q1
                    for j in range(q1, min(2*q1, n)):
                        continuous_abs_sum_block2 += fabs(cont_sum[j])
                    # block4: 从后往前q1
                    for j in range(n-1, max(n-1-q1, -1), -1):
                        continuous_abs_sum_block4 += fabs(cont_sum[j])
                    # block3: 再往前q1
                    for j in range(n-1-q1, max(n-1-2*q1, -1), -1):
                        continuous_abs_sum_block3 += fabs(cont_sum[j])
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
                            q1 = <int>ceil(n / 4.0)
                            forward_max_abs_sum_first_half = 0
                            forward_max_abs_sum_second_half = 0
                            forward_max_abs_sum_block1 = 0
                            forward_max_abs_sum_block2 = 0
                            forward_max_abs_sum_block3 = 0
                            forward_max_abs_sum_block4 = 0
                            # 前一半
                            for j in range(half):
                                forward_max_abs_sum_first_half += fabs(forward_max_result_c[j])
                            # 后一半
                            for j in range(n - half, n):
                                forward_max_abs_sum_second_half += fabs(forward_max_result_c[j])
                            # block1: 前q1
                            for j in range(min(q1, n)):
                                forward_max_abs_sum_block1 += fabs(forward_max_result_c[j])
                            # block2: q1~2q1
                            for j in range(q1, min(2*q1, n)):
                                forward_max_abs_sum_block2 += fabs(forward_max_result_c[j])
                            # block4: 从后往前q1
                            for j in range(n-1, max(n-1-q1, -1), -1):
                                forward_max_abs_sum_block4 += fabs(forward_max_result_c[j])
                            # block3: 再往前q1
                            for j in range(n-1-q1, max(n-1-2*q1, -1), -1):
                                forward_max_abs_sum_block3 += fabs(forward_max_result_c[j])
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
                            q1 = <int>ceil(n / 4.0)
                            forward_min_abs_sum_first_half = 0
                            forward_min_abs_sum_second_half = 0
                            forward_min_abs_sum_block1 = 0
                            forward_min_abs_sum_block2 = 0
                            forward_min_abs_sum_block3 = 0
                            forward_min_abs_sum_block4 = 0
                            # 前一半
                            for j in range(half):
                                forward_min_abs_sum_first_half += fabs(forward_min_result_c[j])
                            # 后一半
                            for j in range(n - half, n):
                                forward_min_abs_sum_second_half += fabs(forward_min_result_c[j])
                            # block1: 前q1
                            for j in range(min(q1, n)):
                                forward_min_abs_sum_block1 += fabs(forward_min_result_c[j])
                            # block2: q1~2q1
                            for j in range(q1, min(2*q1, n)):
                                forward_min_abs_sum_block2 += fabs(forward_min_result_c[j])
                            # block4: 从后往前q1
                            for j in range(n-1, max(n-1-q1, -1), -1):
                                forward_min_abs_sum_block4 += fabs(forward_min_result_c[j])
                            # block3: 再往前q1
                            for j in range(n-1-q1, max(n-1-2*q1, -1), -1):
                                forward_min_abs_sum_block3 += fabs(forward_min_result_c[j])
                            forward_min_abs_sum_first_half = round_to_2(forward_min_abs_sum_first_half)
                            forward_min_abs_sum_second_half = round_to_2(forward_min_abs_sum_second_half)
                            forward_min_abs_sum_block1 = round_to_2(forward_min_abs_sum_block1)
                            forward_min_abs_sum_block2 = round_to_2(forward_min_abs_sum_block2)
                            forward_min_abs_sum_block3 = round_to_2(forward_min_abs_sum_block3)
                            forward_min_abs_sum_block4 = round_to_2(forward_min_abs_sum_block4)
                        else:
                            forward_min_abs_sum_first_half = NAN
                            forward_min_abs_sum_second_half = NAN
                            forward_min_abs_sum_block1 = NAN
                            forward_min_abs_sum_block2 = NAN
                            forward_min_abs_sum_block3 = NAN
                            forward_min_abs_sum_block4 = NAN

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
                    forward_max_valid_sum_vec.clear()
                    if forward_max_result_c.size() > 0:
                        calc_valid_sum_and_pos_neg(
                            forward_max_result_c,
                            forward_max_valid_sum_vec, &forward_max_valid_sum_len,
                            &forward_max_valid_pos_sum, &forward_max_valid_neg_sum)
                        forward_max_valid_pos_sum = round_to_2_nan(forward_max_valid_pos_sum)
                        forward_max_valid_neg_sum = round_to_2_nan(forward_max_valid_neg_sum)
                    else:
                        forward_max_valid_sum_len = 0
                        forward_max_valid_pos_sum = NAN
                        forward_max_valid_neg_sum = NAN

                    # 向前最小有效累加值的正负加和
                    forward_min_valid_sum_vec.clear()
                    if forward_min_result_c.size() > 0:
                        calc_valid_sum_and_pos_neg(
                            forward_min_result_c,
                            forward_min_valid_sum_vec, &forward_min_valid_sum_len,
                            &forward_min_valid_pos_sum, &forward_min_valid_neg_sum)
                        # 添加 round_to_2 处理
                        forward_min_valid_pos_sum = round_to_2_nan(forward_min_valid_pos_sum)
                        forward_min_valid_neg_sum = round_to_2_nan(forward_min_valid_neg_sum)
                    else:
                        forward_min_valid_sum_len = 0
                        forward_min_valid_pos_sum = NAN
                        forward_min_valid_neg_sum = NAN

                    # 连续累加值绝对值最大值判断
                    max_abs_val = 0
                    if continuous_abs_threshold > 0 and cont_sum.size() > 0:
                        for j in range(cont_sum.size()):
                            abs_v = fabs(cont_sum[j])
                            if abs_v > max_abs_val:
                                max_abs_val = abs_v
                        continuous_abs_is_less = max_abs_val < continuous_abs_threshold
                    else:
                        continuous_abs_is_less = False

                    # 有效累加值绝对值最大值判断
                    valid_max_abs_val = 0
                    if valid_abs_sum_threshold > 0 and valid_sum_len > 0:
                        for j in range(valid_sum_len):
                            abs_v = fabs(valid_sum_vec[j])
                            if abs_v > valid_max_abs_val:
                                valid_max_abs_val = abs_v
                        valid_abs_is_less = valid_max_abs_val < valid_abs_sum_threshold
                    else:
                        valid_abs_is_less = False

                    # 向前最小连续累加值绝对值最大值判断
                    forward_min_max_abs_val = 0
                    if continuous_abs_threshold > 0 and forward_min_result_c.size() > 0:
                        for j in range(forward_min_result_c.size()):
                            abs_v = fabs(forward_min_result_c[j])
                            if abs_v > forward_min_max_abs_val:
                                forward_min_max_abs_val = abs_v
                        forward_min_continuous_abs_is_less = forward_min_max_abs_val < continuous_abs_threshold
                    else:
                        forward_min_continuous_abs_is_less = False

                    # 向前最小有效累加值绝对值最大值判断
                    forward_min_valid_max_abs_val = 0
                    if valid_abs_sum_threshold > 0 and forward_min_valid_sum_len > 0:
                        for j in range(forward_min_valid_sum_len):
                            abs_v = fabs(forward_min_valid_sum_vec[j])
                            if abs_v > forward_min_valid_max_abs_val:
                                forward_min_valid_max_abs_val = abs_v
                        forward_min_valid_abs_is_less = forward_min_valid_max_abs_val < valid_abs_sum_threshold
                    else:
                        forward_min_valid_abs_is_less = False

                    # 向前最大连续累加值绝对值最大值判断
                    forward_max_max_abs_val = 0
                    if continuous_abs_threshold > 0 and forward_max_result_c.size() > 0:
                        for j in range(forward_max_result_c.size()):
                            abs_v = fabs(forward_max_result_c[j])
                            if abs_v > forward_max_max_abs_val:
                                forward_max_max_abs_val = abs_v
                        forward_max_continuous_abs_is_less = forward_max_max_abs_val < continuous_abs_threshold
                    else:
                        forward_max_continuous_abs_is_less = False

                    # 向前最小有效累加值绝对值最大值判断
                    forward_max_valid_max_abs_val = 0
                    if valid_abs_sum_threshold > 0 and forward_max_valid_sum_len > 0:
                        for j in range(forward_max_valid_sum_len):
                            abs_v = fabs(forward_max_valid_sum_vec[j])
                            if abs_v > forward_max_valid_max_abs_val:
                                forward_max_valid_max_abs_val = abs_v
                        forward_max_valid_abs_is_less = forward_max_valid_max_abs_val < valid_abs_sum_threshold
                    else:
                        forward_max_valid_abs_is_less = False
                
                    
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
                    if valid_sum_len > 0:
                        valid_abs_sum_first_half = 0
                        valid_abs_sum_second_half = 0
                        valid_abs_sum_block1 = 0
                        valid_abs_sum_block2 = 0
                        valid_abs_sum_block3 = 0
                        valid_abs_sum_block4 = 0
                        n_valid = valid_sum_len
                        half_valid = int(round(n_valid / 2.0))
                        q1 = <int>ceil(n_valid / 4.0)
                        # 前一半
                        for j in range(half_valid):
                            valid_abs_sum_first_half += fabs(valid_sum_vec[j])
                        # 后一半
                        for j in range(n_valid - half_valid, n_valid):
                            valid_abs_sum_second_half += fabs(valid_sum_vec[j])
                        # block1: 前q1
                        for j in range(min(q1, n_valid)):
                            valid_abs_sum_block1 += fabs(valid_sum_vec[j])
                        # block2: q1~2q1
                        for j in range(q1, min(2*q1, n_valid)):
                            valid_abs_sum_block2 += fabs(valid_sum_vec[j])
                        # block4: 从后往前q1
                        for j in range(n_valid-1, max(n_valid-1-q1, -1), -1):
                            valid_abs_sum_block4 += fabs(valid_sum_vec[j])
                        # block3: 再往前q1
                        for j in range(n_valid-1-q1, max(n_valid-1-2*q1, -1), -1):
                            valid_abs_sum_block3 += fabs(valid_sum_vec[j])
                        valid_abs_sum_first_half = round_to_2(valid_abs_sum_first_half)
                        valid_abs_sum_second_half = round_to_2(valid_abs_sum_second_half)
                        valid_abs_sum_block1 = round_to_2(valid_abs_sum_block1)
                        valid_abs_sum_block2 = round_to_2(valid_abs_sum_block2)
                        valid_abs_sum_block3 = round_to_2(valid_abs_sum_block3)
                        valid_abs_sum_block4 = round_to_2(valid_abs_sum_block4)
                    else:
                        valid_abs_sum_first_half = NAN
                        valid_abs_sum_second_half = NAN
                        valid_abs_sum_block1 = NAN
                        valid_abs_sum_block2 = NAN
                        valid_abs_sum_block3 = NAN
                        valid_abs_sum_block4 = NAN

                    # 计算向前最大有效连续累加值的分块和绝对值之和（全部在Cython区完成）
                    forward_max_valid_abs_sum_first_half = 0
                    forward_max_valid_abs_sum_second_half = 0
                    forward_max_valid_abs_sum_block1 = 0
                    forward_max_valid_abs_sum_block2 = 0
                    forward_max_valid_abs_sum_block3 = 0
                    forward_max_valid_abs_sum_block4 = 0
                    if is_forward and forward_max_valid_sum_len > 0:
                        n = forward_max_valid_sum_len
                        half = int(round(n / 2.0))
                        q1 = <int>ceil(n / 4.0)
                        # 前一半
                        for j in range(half):
                            forward_max_valid_abs_sum_first_half += fabs(forward_max_valid_sum_vec[j])
                        # 后一半
                        for j in range(n - half, n):
                            forward_max_valid_abs_sum_second_half += fabs(forward_max_valid_sum_vec[j])
                        # block1: 前q1
                        for j in range(min(q1, n)):
                            forward_max_valid_abs_sum_block1 += fabs(forward_max_valid_sum_vec[j])
                        # block2: q1~2q1
                        for j in range(q1, min(2*q1, n)):
                            forward_max_valid_abs_sum_block2 += fabs(forward_max_valid_sum_vec[j])
                        # block4: 从后往前q1
                        for j in range(n-1, max(n-1-q1, -1), -1):
                            forward_max_valid_abs_sum_block4 += fabs(forward_max_valid_sum_vec[j])
                        # block3: 再往前q1
                        for j in range(n-1-q1, max(n-1-2*q1, -1), -1):
                            forward_max_valid_abs_sum_block3 += fabs(forward_max_valid_sum_vec[j])
                        forward_max_valid_abs_sum_first_half = round_to_2(forward_max_valid_abs_sum_first_half)
                        forward_max_valid_abs_sum_second_half = round_to_2(forward_max_valid_abs_sum_second_half)
                        forward_max_valid_abs_sum_block1 = round_to_2(forward_max_valid_abs_sum_block1)
                        forward_max_valid_abs_sum_block2 = round_to_2(forward_max_valid_abs_sum_block2)
                        forward_max_valid_abs_sum_block3 = round_to_2(forward_max_valid_abs_sum_block3)
                        forward_max_valid_abs_sum_block4 = round_to_2(forward_max_valid_abs_sum_block4)
                    else:
                        forward_max_valid_abs_sum_first_half = NAN
                        forward_max_valid_abs_sum_second_half = NAN
                        forward_max_valid_abs_sum_block1 = NAN
                        forward_max_valid_abs_sum_block2 = NAN
                        forward_max_valid_abs_sum_block3 = NAN
                        forward_max_valid_abs_sum_block4 = NAN

                    # 计算向前最小有效连续累加值的分块和绝对值之和（全部在Cython区完成）
                    forward_min_valid_abs_sum_first_half = 0
                    forward_min_valid_abs_sum_second_half = 0
                    forward_min_valid_abs_sum_block1 = 0
                    forward_min_valid_abs_sum_block2 = 0
                    forward_min_valid_abs_sum_block3 = 0
                    forward_min_valid_abs_sum_block4 = 0
                    if is_forward and forward_min_valid_sum_len > 0:
                        n = forward_min_valid_sum_len
                        half = int(round(n / 2.0))
                        q1 = <int>ceil(n / 4.0)
                        # 前一半
                        for j in range(half):
                            forward_min_valid_abs_sum_first_half += fabs(forward_min_valid_sum_vec[j])
                        # 后一半
                        for j in range(n - half, n):
                            forward_min_valid_abs_sum_second_half += fabs(forward_min_valid_sum_vec[j])
                        # block1: 前q1
                        for j in range(min(q1, n)):
                            forward_min_valid_abs_sum_block1 += fabs(forward_min_valid_sum_vec[j])
                        # block2: q1~2q1
                        for j in range(q1, min(2*q1, n)):
                            forward_min_valid_abs_sum_block2 += fabs(forward_min_valid_sum_vec[j])
                        # block4: 从后往前q1
                        for j in range(n-1, max(n-1-q1, -1), -1):
                            forward_min_valid_abs_sum_block4 += fabs(forward_min_valid_sum_vec[j])
                        # block3: 再往前q1
                        for j in range(n-1-q1, max(n-1-2*q1, -1), -1):
                            forward_min_valid_abs_sum_block3 += fabs(forward_min_valid_sum_vec[j])
                        forward_min_valid_abs_sum_first_half = round_to_2(forward_min_valid_abs_sum_first_half)
                        forward_min_valid_abs_sum_second_half = round_to_2(forward_min_valid_abs_sum_second_half)
                        forward_min_valid_abs_sum_block1 = round_to_2(forward_min_valid_abs_sum_block1)
                        forward_min_valid_abs_sum_block2 = round_to_2(forward_min_valid_abs_sum_block2)
                        forward_min_valid_abs_sum_block3 = round_to_2(forward_min_valid_abs_sum_block3)
                        forward_min_valid_abs_sum_block4 = round_to_2(forward_min_valid_abs_sum_block4)
                    else:
                        forward_min_valid_abs_sum_first_half = NAN
                        forward_min_valid_abs_sum_second_half = NAN
                        forward_min_valid_abs_sum_block1 = NAN
                        forward_min_valid_abs_sum_block2 = NAN
                        forward_min_valid_abs_sum_block3 = NAN
                        forward_min_valid_abs_sum_block4 = NAN

                    if valid_pos_sum == 0:
                        valid_pos_sum = NAN
                    if valid_neg_sum == 0:
                        valid_neg_sum = NAN
                    valid_pos_sum = round_to_2(valid_pos_sum)
                    valid_neg_sum = round_to_2(valid_neg_sum)

                # with gil

                start_with_new_before_high_py = bool(start_with_new_before_high)
                start_with_new_before_high2_py = bool(start_with_new_before_high2)
                start_with_new_after_high_py = bool(start_with_new_after_high)
                start_with_new_after_high2_py = bool(start_with_new_after_high2)
                start_with_new_before_low_py = bool(start_with_new_before_low)
                start_with_new_before_low2_py = bool(start_with_new_before_low2)
                start_with_new_after_low_py = bool(start_with_new_after_low)
                start_with_new_after_low2_py = bool(start_with_new_after_low2)

                # 计算range_ratio_is_less
                range_ratio_is_less = False
                if min_price is not None and min_price != 0 and not isnan(user_range_ratio):
                    range_ratio_is_less = (max_price / min_price) < user_range_ratio

                # 计算日期索引和n_max_is_max
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
                # 连续累加值基本参数
                continuous_start_value = cont_sum[0] if cont_sum.size() > 0 else None
                continuous_start_next_value = cont_sum[1] if cont_sum.size() > 1 else None
                continuous_start_next_next_value = cont_sum[2] if cont_sum.size() > 2 else None
                continuous_end_value = cont_sum[cont_sum.size()-1] if cont_sum.size() > 0 else None
                continuous_end_prev_value = cont_sum[cont_sum.size()-2] if cont_sum.size() > 1 else None
                continuous_end_prev_prev_value = cont_sum[cont_sum.size()-3] if cont_sum.size() > 2 else None


                # 向前最大连续累加值相关参数
                forward_max_continuous_start_value = forward_max_result_c[0] if forward_max_result_c.size() > 0 else None
                forward_max_continuous_start_next_value = forward_max_result_c[1] if forward_max_result_c.size() > 1 else None
                forward_max_continuous_start_next_next_value = forward_max_result_c[2] if forward_max_result_c.size() > 2 else None
                forward_max_continuous_end_value = forward_max_result_c[forward_max_result_c.size()-1] if forward_max_result_c.size() > 0 else None
                forward_max_continuous_end_prev_value = forward_max_result_c[forward_max_result_c.size()-2] if forward_max_result_c.size() > 1 else None
                forward_max_continuous_end_prev_prev_value = forward_max_result_c[forward_max_result_c.size()-3] if forward_max_result_c.size() > 2 else None

                # 向前最小连续累加值相关参数
                forward_min_continuous_start_value = forward_min_result_c[0] if forward_min_result_c.size() > 0 else None
                forward_min_continuous_start_next_value = forward_min_result_c[1] if forward_min_result_c.size() > 1 else None
                forward_min_continuous_start_next_next_value = forward_min_result_c[2] if forward_min_result_c.size() > 2 else None
                forward_min_continuous_end_value = forward_min_result_c[forward_min_result_c.size()-1] if forward_min_result_c.size() > 0 else None
                forward_min_continuous_end_prev_value = forward_min_result_c[forward_min_result_c.size()-2] if forward_min_result_c.size() > 1 else None
                forward_min_continuous_end_prev_prev_value = forward_min_result_c[forward_min_result_c.size()-3] if forward_min_result_c.size() > 2 else None

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
                        adjust_ops_value = increment_change
                        
                    elif result_value == 'after_gt_end_value':
                        ops_value = after_gt_end_value
                        hold_days = after_gt_end_days
                        adjust_ops_value = after_gt_end_change
                    elif result_value == 'after_gt_start_value':
                        ops_value = after_gt_start_value
                        hold_days = after_gt_start_days
                        adjust_ops_value = after_gt_start_change
                    else:
                        ops_value = result_value
                        hold_days = None
                        adjust_ops_value = None

                except Exception as e:
                    ops_value = None
                    hold_days = None
                    adjust_ops_value = None

                # 新增：计算操作涨幅、调整天数、日均涨幅
                ops_change = None
                adjust_days = None
                ops_incre_rate = None
                end_value_for_ops = end_value if not isnan(end_value) else None

                # 操作涨幅
                if ops_value is not None and not isnan(ops_value) and hold_days is not None and hold_days != -1 and not isnan(hold_days) and end_value_for_ops not in (None, 0):
                    try:
                        ops_change = round_to_2((ops_value - end_value_for_ops) / end_value_for_ops * 100)
                    except Exception:
                        ops_change = None  

                # 当操作值为空值的情况
                else:
                    hold_days = op_days
                    op_days_when_ops_value_nan = min(hold_days, end_date_idx)
                    if end_date_idx - hold_days >= 0:
                        op_idx_when_ops_value_nan = end_date_idx - hold_days
                    else:
                        hold_days = end_date_idx
                        op_idx_when_ops_value_nan = 0
                    try:
                        ops_change = round_to_2((price_data_view[stock_idx, op_idx_when_ops_value_nan] - end_value_for_ops) / end_value_for_ops * 100)
                    except Exception:
                        ops_change = None  

                # 调整天数
                if ops_change is not None and ops_change_input is not None and hold_days is not None:
                    try:
                        if ops_change > ops_change_input and hold_days == 1:
                            adjust_days = 2
                        elif hold_days == 1:
                            adjust_days = 1
                        else:
                            adjust_days = hold_days + 1
                    except Exception:
                        adjust_days = None

                # 调天日均涨幅
                if ops_change is not None and adjust_days not in (None, 0):
                    try:
                        ops_incre_rate = round_to_2(ops_change / adjust_days)
                    except Exception:
                        ops_incre_rate = None

                 # 当stock_idx=0时打印相关参数
                if stock_idx == 0:
                    print(f"stock_idx={stock_idx}, ops_change={ops_change}, adjust_days={adjust_days}, ops_incre_rate={ops_incre_rate}")
                    

                # 调幅日均涨幅： 调整涨幅 / 持有天数
                # 确定除数：如果持有天数小于操作天数的一半，使用操作天数的一半来计算
                # 确保使用浮点数除法，避免整数除法的问题
                op_days_half = float(op_days) / 2.0
                if hold_days is not None and hold_days < op_days_half:
                    # 使用传统四舍五入，而不是银行家舍入
                    # 例如：op_days=3时，3/2=1.5，四舍五入为2
                    # 例如：op_days=1时，1/2=0.5，四舍五入为1
                    divisor = int(op_days_half + 0.5)
                else:
                    divisor = hold_days
                
                if adjust_ops_value is not None and not isnan(adjust_ops_value):
                    adjust_ops_incre_rate = round_to_2(adjust_ops_value / divisor)
                else:
                    if ops_change is not None and hold_days is not None and hold_days != 0:
                        adjust_ops_incre_rate = round_to_2(ops_change / divisor)
                    else:
                        adjust_ops_incre_rate = None

                # 当stock_idx=5366时打印相关参数
                #if stock_idx == 5377:
                    #print(f"stock_idx={stock_idx}, hold_days={hold_days}, op_days={op_days}, divisor={divisor}, adjust_ops_value={adjust_ops_value}, ops_change={ops_change}, adjust_ops_incre_rate={adjust_ops_incre_rate}")
                    #print(f"op_days_half = {op_days_half}")

                # 新增：score 计算
                score = None
                if formula_expr is not None:
                    # 预先计算所有需要的变量
                    def safe_formula_val(val):
                        import math
                        if val is None:
                            return 0
                        if isinstance(val, float) and (math.isnan(val) or str(val).lower() == 'nan'):
                            return 0
                        return val

                    formula_vars = {
                        'max_value': safe_formula_val(max_price),
                        'max_value_date': max_value_date,
                        'min_value': safe_formula_val(min_price),
                        'min_value_date': min_value_date,
                        'end_value': safe_formula_val(end_value),
                        'end_value_date': end_value_date,
                        'start_value': safe_formula_val(start_value),
                        'start_value_date': start_value_date,
                        'actual_value': safe_formula_val(actual_value),
                        'actual_value_date': actual_value_date,
                        'closest_value': safe_formula_val(closest_value),
                        'closest_value_date': closest_value_date,
                        'continuous_results': py_cont_sum,
                        'continuous_len': safe_formula_val(continuous_len),
                        'continuous_start_value': safe_formula_val(continuous_start_value),
                        'continuous_start_next_value': safe_formula_val(continuous_start_next_value),
                        'continuous_start_next_next_value': safe_formula_val(continuous_start_next_next_value),
                        'continuous_end_value': safe_formula_val(continuous_end_value),
                        'continuous_end_prev_value': safe_formula_val(continuous_end_prev_value),
                        'continuous_end_prev_prev_value': safe_formula_val(continuous_end_prev_prev_value),
                        'continuous_abs_sum_first_half': safe_formula_val(continuous_abs_sum_first_half),
                        'continuous_abs_sum_second_half': safe_formula_val(continuous_abs_sum_second_half),
                        'continuous_abs_sum_block1': safe_formula_val(continuous_abs_sum_block1),
                        'continuous_abs_sum_block2': safe_formula_val(continuous_abs_sum_block2),
                        'continuous_abs_sum_block3': safe_formula_val(continuous_abs_sum_block3),
                        'continuous_abs_sum_block4': safe_formula_val(continuous_abs_sum_block4),
                        'forward_max_result': forward_max_result,
                        'forward_max_continuous_start_value': safe_formula_val(forward_max_continuous_start_value),
                        'forward_max_continuous_start_next_value': safe_formula_val(forward_max_continuous_start_next_value),
                        'forward_max_continuous_start_next_next_value': safe_formula_val(forward_max_continuous_start_next_next_value),
                        'forward_max_continuous_end_value': safe_formula_val(forward_max_continuous_end_value),
                        'forward_max_continuous_end_prev_value': safe_formula_val(forward_max_continuous_end_prev_value),
                        'forward_max_continuous_end_prev_prev_value': safe_formula_val(forward_max_continuous_end_prev_prev_value),
                        'forward_max_abs_sum_first_half': safe_formula_val(forward_max_abs_sum_first_half),
                        'forward_max_abs_sum_second_half': safe_formula_val(forward_max_abs_sum_second_half),
                        'forward_max_abs_sum_block1': safe_formula_val(forward_max_abs_sum_block1),
                        'forward_max_abs_sum_block2': safe_formula_val(forward_max_abs_sum_block2),
                        'forward_max_abs_sum_block3': safe_formula_val(forward_max_abs_sum_block3),
                        'forward_max_abs_sum_block4': safe_formula_val(forward_max_abs_sum_block4),
                        'forward_min_result': forward_min_result,
                        'forward_min_continuous_start_value': safe_formula_val(forward_min_continuous_start_value),
                        'forward_min_continuous_start_next_value': safe_formula_val(forward_min_continuous_start_next_value),
                        'forward_min_continuous_start_next_next_value': safe_formula_val(forward_min_continuous_start_next_next_value),
                        'forward_min_continuous_end_value': safe_formula_val(forward_min_continuous_end_value),
                        'forward_min_continuous_end_prev_value': safe_formula_val(forward_min_continuous_end_prev_value),
                        'forward_min_continuous_end_prev_prev_value': safe_formula_val(forward_min_continuous_end_prev_prev_value),
                        'forward_min_abs_sum_first_half': safe_formula_val(forward_min_abs_sum_first_half),
                        'forward_min_abs_sum_second_half': safe_formula_val(forward_min_abs_sum_second_half),
                        'forward_min_abs_sum_block1': safe_formula_val(forward_min_abs_sum_block1),
                        'forward_min_abs_sum_block2': safe_formula_val(forward_min_abs_sum_block2),
                        'forward_min_abs_sum_block3': safe_formula_val(forward_min_abs_sum_block3),
                        'forward_min_abs_sum_block4': safe_formula_val(forward_min_abs_sum_block4),
                        'valid_sum_arr': py_valid_sum_arr,
                        'valid_sum_len': safe_formula_val(valid_sum_len),
                        'valid_pos_sum': safe_formula_val(valid_pos_sum),
                        'valid_neg_sum': safe_formula_val(valid_neg_sum),
                        'forward_max_valid_sum_arr': forward_max_valid_sum_arr,
                        'forward_max_valid_sum_len': safe_formula_val(forward_max_valid_sum_len),
                        'forward_max_valid_pos_sum': safe_formula_val(forward_max_valid_pos_sum),
                        'forward_max_valid_neg_sum': safe_formula_val(forward_max_valid_neg_sum),
                        'forward_min_valid_sum_arr': forward_min_valid_sum_arr,
                        'forward_min_valid_sum_len': safe_formula_val(forward_min_valid_sum_len),
                        'forward_min_valid_pos_sum': safe_formula_val(forward_min_valid_pos_sum),
                        'forward_min_valid_neg_sum': safe_formula_val(forward_min_valid_neg_sum),
                        'valid_abs_sum_first_half': safe_formula_val(valid_abs_sum_first_half),
                        'valid_abs_sum_second_half': safe_formula_val(valid_abs_sum_second_half),
                        'valid_abs_sum_block1': safe_formula_val(valid_abs_sum_block1),
                        'valid_abs_sum_block2': safe_formula_val(valid_abs_sum_block2),
                        'valid_abs_sum_block3': safe_formula_val(valid_abs_sum_block3),
                        'valid_abs_sum_block4': safe_formula_val(valid_abs_sum_block4),
                        'forward_max_valid_abs_sum_first_half': safe_formula_val(forward_max_valid_abs_sum_first_half),
                        'forward_max_valid_abs_sum_second_half': safe_formula_val(forward_max_valid_abs_sum_second_half),
                        'forward_max_valid_abs_sum_block1': safe_formula_val(forward_max_valid_abs_sum_block1),
                        'forward_max_valid_abs_sum_block2': safe_formula_val(forward_max_valid_abs_sum_block2),
                        'forward_max_valid_abs_sum_block3': safe_formula_val(forward_max_valid_abs_sum_block3),
                        'forward_max_valid_abs_sum_block4': safe_formula_val(forward_max_valid_abs_sum_block4),
                        'forward_min_valid_abs_sum_first_half': safe_formula_val(forward_min_valid_abs_sum_first_half),
                        'forward_min_valid_abs_sum_second_half': safe_formula_val(forward_min_valid_abs_sum_second_half),
                        'forward_min_valid_abs_sum_block1': safe_formula_val(forward_min_valid_abs_sum_block1),
                        'forward_min_valid_abs_sum_block2': safe_formula_val(forward_min_valid_abs_sum_block2),
                        'forward_min_valid_abs_sum_block3': safe_formula_val(forward_min_valid_abs_sum_block3),
                        'forward_min_valid_abs_sum_block4': safe_formula_val(forward_min_valid_abs_sum_block4),
                        'forward_max_date': forward_max_date_str,
                        'forward_min_date': forward_min_date_str,
                        'n_max_is_max': n_max_is_max_result,
                        'range_ratio_is_less': range_ratio_is_less,
                        'continuous_abs_is_less': continuous_abs_is_less,
                        'valid_abs_is_less': valid_abs_is_less,
                        'forward_min_continuous_abs_is_less': forward_min_continuous_abs_is_less,
                        'forward_min_valid_abs_is_less': forward_min_valid_abs_is_less,
                        'forward_max_continuous_abs_is_less': forward_max_continuous_abs_is_less,
                        'forward_max_valid_abs_is_less': forward_max_valid_abs_is_less,
                        'n_days_max_value': safe_formula_val(n_days_max_value),
                        'prev_day_change': safe_formula_val(prev_day_change),
                        'end_day_change': safe_formula_val(end_day_change),
                        'diff_end_value': diff_data_view[stock_idx, end_date_idx],
                        'increment_value': safe_formula_val(increment_value),
                        'after_gt_end_value': safe_formula_val(after_gt_end_value),
                        'after_gt_start_value': safe_formula_val(after_gt_start_value),
                        'ops_value': safe_formula_val(ops_value),
                        'increment_change': safe_formula_val(increment_change),
                        'after_gt_end_change': safe_formula_val(after_gt_end_change),
                        'after_gt_start_change': safe_formula_val(after_gt_start_change),
                        'adjust_ops_value': safe_formula_val(adjust_ops_value),
                        'adjust_ops_incre_rate': safe_formula_val(adjust_ops_incre_rate),
                        'hold_days': safe_formula_val(hold_days),
                        'ops_change': safe_formula_val(ops_change),
                        'adjust_days': safe_formula_val(adjust_days),
                        'ops_incre_rate': safe_formula_val(ops_incre_rate),
                        'forward_max_result_len': safe_formula_val(forward_max_result_len),
                        'forward_min_result_len': safe_formula_val(forward_min_result_len),
                        'cont_sum_pos_sum': safe_formula_val(cont_sum_pos_sum),
                        'cont_sum_neg_sum': safe_formula_val(cont_sum_neg_sum),
                        'cont_sum_pos_sum_first_half': safe_formula_val(cont_sum_pos_sum_first_half),
                        'cont_sum_pos_sum_second_half': safe_formula_val(cont_sum_pos_sum_second_half),
                        'cont_sum_neg_sum_first_half': safe_formula_val(cont_sum_neg_sum_first_half),
                        'cont_sum_neg_sum_second_half': safe_formula_val(cont_sum_neg_sum_second_half),
                        'forward_max_cont_sum_pos_sum': safe_formula_val(forward_max_cont_sum_pos_sum),
                        'forward_max_cont_sum_neg_sum': safe_formula_val(forward_max_cont_sum_neg_sum),
                        'forward_min_cont_sum_pos_sum': safe_formula_val(forward_min_cont_sum_pos_sum),
                        'forward_min_cont_sum_neg_sum': safe_formula_val(forward_min_cont_sum_neg_sum),
                        'start_with_new_before_high': start_with_new_before_high_py,
                        'start_with_new_before_high2': start_with_new_before_high2_py,
                        'start_with_new_after_high': start_with_new_after_high_py,
                        'start_with_new_after_high2': start_with_new_after_high2_py,
                        'start_with_new_before_low': start_with_new_before_low_py,
                        'start_with_new_before_low2': start_with_new_before_low2_py,
                        'start_with_new_after_low': start_with_new_after_low_py,
                        'start_with_new_after_low2': start_with_new_after_low2_py,
                    }

                    # 在执行公式前检查每对比较变量
                    should_exec_formula = True  # 添加flag控制是否执行公式
                    if comparison_vars_list:
                        for var_pair in comparison_vars_list:
                            var1, var2 = var_pair  # 解包元组对
                            var1_value = formula_vars.get(var1, 0)
                            var2_value = formula_vars.get(var2, 0)
                            # 如果一对变量都为0，设置flag为False
                            if var1_value == 0 and var2_value == 0:
                                #print(f"stock_idx: {stock_idx}, var1: {var1}, var2: {var2}, var1_value: {var1_value}, var2_value: {var2_value}")
                                should_exec_formula = False
                                score = 0
                                break
                    
                    try:
                        # 根据flag决定是否执行选股公式
                        if should_exec_formula:
                            exec(formula_expr, {}, formula_vars)
                            score = formula_vars.get('result', None)
                            if score is not None and score != 0:
                                score = round_to_2(score)
                                
                    except Exception as e:
                        import traceback
                        print(f"[calculate_batch_cy] 执行公式异常: {e}")
                        print(f"公式内容: {formula_expr}")
                        print(traceback.format_exc())
                        score = None
                
                #print(f"stock_idx={stock_idx}, cont_sum_pos_sum={cont_sum_pos_sum}, valid_pos_sum={valid_pos_sum}, forward_min_cont_sum_pos_sum={forward_min_cont_sum_pos_sum}")
                if only_show_selected:
                    if score is not None and score != 0 and not isnan(end_value) and hold_days != -1:
                        # 根据排序模式过滤score
                        if (sort_mode == "最大值排序" and score > 0) or (sort_mode == "最小值排序" and score < 0):
                            row_result = {
                                'stock_idx': stock_idx,
                                'max_value': max_price,
                                'max_value_date': max_value_date,
                                'min_value': min_price,
                                'min_value_date': min_value_date,
                                'end_value': end_value,
                                'end_value_date': end_value_date,
                                'start_value': start_value,
                                'start_value_date': start_value_date,
                                'actual_value': actual_value,
                                'actual_value_date': actual_value_date,
                                'closest_value': closest_value,
                                'closest_value_date': closest_value_date,
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
                                'forward_max_continuous_start_value': forward_max_continuous_start_value,
                                'forward_max_continuous_start_next_value': forward_max_continuous_start_next_value,
                                'forward_max_continuous_start_next_next_value': forward_max_continuous_start_next_next_value,
                                'forward_max_continuous_end_value': forward_max_continuous_end_value,
                                'forward_max_continuous_end_prev_value': forward_max_continuous_end_prev_value,
                                'forward_max_continuous_end_prev_prev_value': forward_max_continuous_end_prev_prev_value,
                                'forward_max_abs_sum_first_half': forward_max_abs_sum_first_half,
                                'forward_max_abs_sum_second_half': forward_max_abs_sum_second_half,
                                'forward_max_abs_sum_block1': forward_max_abs_sum_block1,
                                'forward_max_abs_sum_block2': forward_max_abs_sum_block2,
                                'forward_max_abs_sum_block3': forward_max_abs_sum_block3,
                                'forward_max_abs_sum_block4': forward_max_abs_sum_block4,
                                'forward_min_result': forward_min_result,
                                'forward_min_continuous_start_value': forward_min_continuous_start_value,
                                'forward_min_continuous_start_next_value': forward_min_continuous_start_next_value,
                                'forward_min_continuous_start_next_next_value': forward_min_continuous_start_next_next_value,
                                'forward_min_continuous_end_value': forward_min_continuous_end_value,
                                'forward_min_continuous_end_prev_value': forward_min_continuous_end_prev_value,
                                'forward_min_continuous_end_prev_prev_value': forward_min_continuous_end_prev_prev_value,
                                'forward_min_abs_sum_first_half': forward_min_abs_sum_first_half,
                                'forward_min_abs_sum_second_half': forward_min_abs_sum_second_half,
                                'forward_min_abs_sum_block1': forward_min_abs_sum_block1,
                                'forward_min_abs_sum_block2': forward_min_abs_sum_block2,
                                'forward_min_abs_sum_block3': forward_min_abs_sum_block3,
                                'forward_min_abs_sum_block4': forward_min_abs_sum_block4,
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
                                'valid_abs_is_less': valid_abs_is_less,
                                'forward_min_continuous_abs_is_less': forward_min_continuous_abs_is_less,
                                'forward_min_valid_abs_is_less': forward_min_valid_abs_is_less,
                                'forward_max_continuous_abs_is_less': forward_max_continuous_abs_is_less,
                                'forward_max_valid_abs_is_less': forward_max_valid_abs_is_less,
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
                                'increment_change': increment_change,
                                'after_gt_end_change': after_gt_end_change,
                                'after_gt_start_change': after_gt_start_change,
                                'adjust_ops_value': adjust_ops_value,
                                'adjust_ops_incre_rate': adjust_ops_incre_rate,
                                'score': score,
                                'forward_max_result_len': forward_max_result_len,
                                'forward_min_result_len': forward_min_result_len,
                                'cont_sum_pos_sum': cont_sum_pos_sum,
                                'cont_sum_neg_sum': cont_sum_neg_sum,
                                'cont_sum_pos_sum_first_half': safe_formula_val(cont_sum_pos_sum_first_half),
                                'cont_sum_pos_sum_second_half': safe_formula_val(cont_sum_pos_sum_second_half),
                                'cont_sum_neg_sum_first_half': safe_formula_val(cont_sum_neg_sum_first_half),
                                'cont_sum_neg_sum_second_half': safe_formula_val(cont_sum_neg_sum_second_half),
                                'forward_max_cont_sum_pos_sum': forward_max_cont_sum_pos_sum,
                                'forward_max_cont_sum_neg_sum': forward_max_cont_sum_neg_sum,
                                'forward_min_cont_sum_pos_sum': forward_min_cont_sum_pos_sum,
                                'forward_min_cont_sum_neg_sum': forward_min_cont_sum_neg_sum,
                                'start_with_new_before_high': start_with_new_before_high_py,
                                'start_with_new_before_high2': start_with_new_before_high2_py,
                                'start_with_new_after_high': start_with_new_after_high_py,
                                'start_with_new_after_high2': start_with_new_after_high2_py,
                                'start_with_new_before_low': start_with_new_before_low_py,
                                'start_with_new_before_low2': start_with_new_before_low2_py,
                                'start_with_new_after_low': start_with_new_after_low_py,
                                'start_with_new_after_low2': start_with_new_after_low2_py,
                                'end_state': end_state
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
                    if stock_idx == 0:
                        print(f"only_show_selected = {only_show_selected}， cont_sum_pos_sum_first_half = {cont_sum_pos_sum_first_half}")
                    row_result = {
                            'stock_idx': stock_idx,
                            'max_value': max_price,
                            'max_value_date': max_value_date,
                            'min_value': min_price,
                            'min_value_date': min_value_date,
                            'end_value': end_value,
                            'end_value_date': end_value_date,
                            'start_value': start_value,
                            'start_value_date': start_value_date,
                            'actual_value': actual_value,
                            'actual_value_date': actual_value_date,
                            'closest_value': closest_value,
                            'closest_value_date': closest_value_date,
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
                            'forward_max_continuous_start_value': forward_max_continuous_start_value,
                            'forward_max_continuous_start_next_value': forward_max_continuous_start_next_value,
                            'forward_max_continuous_start_next_next_value': forward_max_continuous_start_next_next_value,
                            'forward_max_continuous_end_value': forward_max_continuous_end_value,
                            'forward_max_continuous_end_prev_value': forward_max_continuous_end_prev_value,
                            'forward_max_continuous_end_prev_prev_value': forward_max_continuous_end_prev_prev_value,
                            'forward_max_abs_sum_first_half': forward_max_abs_sum_first_half,
                            'forward_max_abs_sum_second_half': forward_max_abs_sum_second_half,
                            'forward_max_abs_sum_block1': forward_max_abs_sum_block1,
                            'forward_max_abs_sum_block2': forward_max_abs_sum_block2,
                            'forward_max_abs_sum_block3': forward_max_abs_sum_block3,
                            'forward_max_abs_sum_block4': forward_max_abs_sum_block4,
                            'forward_min_result': forward_min_result,
                            'forward_min_continuous_start_value': forward_min_continuous_start_value,
                            'forward_min_continuous_start_next_value': forward_min_continuous_start_next_value,
                            'forward_min_continuous_start_next_next_value': forward_min_continuous_start_next_next_value,
                            'forward_min_continuous_end_value': forward_min_continuous_end_value,
                            'forward_min_continuous_end_prev_value': forward_min_continuous_end_prev_value,
                            'forward_min_continuous_end_prev_prev_value': forward_min_continuous_end_prev_prev_value,
                            'forward_min_abs_sum_first_half': forward_min_abs_sum_first_half,
                            'forward_min_abs_sum_second_half': forward_min_abs_sum_second_half,
                            'forward_min_abs_sum_block1': forward_min_abs_sum_block1,
                            'forward_min_abs_sum_block2': forward_min_abs_sum_block2,
                            'forward_min_abs_sum_block3': forward_min_abs_sum_block3,
                            'forward_min_abs_sum_block4': forward_min_abs_sum_block4,
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
                            'valid_abs_is_less': valid_abs_is_less,
                            'forward_min_continuous_abs_is_less': forward_min_continuous_abs_is_less,
                            'forward_min_valid_abs_is_less': forward_min_valid_abs_is_less,
                            'forward_max_continuous_abs_is_less': forward_max_continuous_abs_is_less,
                            'forward_max_valid_abs_is_less': forward_max_valid_abs_is_less,
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
                            'increment_change': increment_change,
                            'after_gt_end_change': after_gt_end_change,
                            'after_gt_start_change': after_gt_start_change,
                            'adjust_ops_value': adjust_ops_value,
                            'adjust_ops_incre_rate': adjust_ops_incre_rate,
                            'score': score,
                            'forward_max_result_len': forward_max_result_len,
                            'forward_min_result_len': forward_min_result_len,
                            'cont_sum_pos_sum': cont_sum_pos_sum,
                            'cont_sum_neg_sum': cont_sum_neg_sum,
                            'cont_sum_pos_sum_first_half': safe_formula_val(cont_sum_pos_sum_first_half),
                            'cont_sum_pos_sum_second_half': safe_formula_val(cont_sum_pos_sum_second_half),
                            'cont_sum_neg_sum_first_half': safe_formula_val(cont_sum_neg_sum_first_half),
                            'cont_sum_neg_sum_second_half': safe_formula_val(cont_sum_neg_sum_second_half),
                            'forward_max_cont_sum_pos_sum': forward_max_cont_sum_pos_sum,
                            'forward_max_cont_sum_neg_sum': forward_max_cont_sum_neg_sum,
                            'forward_min_cont_sum_pos_sum': forward_min_cont_sum_pos_sum,
                            'forward_min_cont_sum_neg_sum': forward_min_cont_sum_neg_sum,
                            'start_with_new_before_high': start_with_new_before_high_py,
                            'start_with_new_before_high2': start_with_new_before_high2_py,
                            'start_with_new_after_high': start_with_new_after_high_py,
                            'start_with_new_after_high2': start_with_new_after_high2_py,
                            'start_with_new_before_low': start_with_new_before_low_py,
                            'start_with_new_before_low2': start_with_new_before_low2_py,
                            'start_with_new_after_low': start_with_new_after_low_py,
                            'start_with_new_after_low2': start_with_new_after_low2_py,
                            'end_state': end_state
                        }
                    all_results[date_columns[end_date_idx]].append(row_result)
            except Exception as e:
                import traceback
                print(f"[calculate_batch_cy] stock_idx={stock_idx}, idx={idx} 发生异常: {e}")
                print(traceback.format_exc())
                
    return all_results