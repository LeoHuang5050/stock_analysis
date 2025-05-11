from PyQt5.QtWidgets import QMessageBox, QApplication
import pandas as pd
from decimal import Decimal

class ExtendParamHandler:
    def __init__(self, main_window):
        self.main_window = main_window

    def on_extend_clicked(self):
        if self.main_window.init.price_data is None:
            QMessageBox.warning(self.main_window, "提示", "请先上传文件！")
            return
            
        self.main_window.result_text.setText("正在生成扩展参数，请稍候...")
        QApplication.processEvents()
        
        # 直接获取base_param中的最大值和最小值
        max_in_range = self.main_window.max_value
        min_in_range = self.main_window.min_value
        max_date = self.main_window.max_date
        min_date = self.main_window.min_date

        # 计算最高价/最低价比值
        if min_in_range is not None and min_in_range != 0:
            ratio = max_in_range / min_in_range
        else:
            ratio = None

        # 获取用户输入
        try:
            user_value = float(self.main_window.range_value_edit.text())
        except Exception:
            user_value = None

        if user_value is not None and ratio is not None:
            is_ratio_less = ratio < user_value
        else:
            is_ratio_less = "无效"

        # 获取用户输入的绝对值阈值
        try:
            abs_sum_user_value = float(self.main_window.abs_sum_value_edit.text())
        except Exception:
            abs_sum_user_value = None

        # 获取结束日期
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        n_days = self.main_window.n_days_spin.value()
        
        # 获取价格数据
        price_data = self.main_window.init.price_data
        diff_data = self.main_window.init.diff_data
        
        # 获取日期索引
        end_idx = self.main_window.init.workdays_str.index(end_date)
        start_idx = max(0, end_idx - n_days + 1)
        date_range = self.main_window.init.workdays_str[start_idx:end_idx+1]
        
        # 获取第一行数据
        first_row = price_data.iloc[0]
        price_values = [first_row[d] for d in date_range if d in first_row.index]
        
        # 计算前N日最高值
        n_max_value = max([v for v in price_values if pd.notna(v)])
        self.main_window.n_max_value = n_max_value  # 记录前N日最大值

        # 直接读取基础参数最大值
        base_max_value = self.main_window.max_value

        # 判断前N最大值
        is_n_max = (n_max_value == base_max_value)
        
        # 获取结束日价格
        end_price = first_row[end_date]
        
        # 计算涨跌幅
        prev_date = self.main_window.init.workdays_str[end_idx-1]
        prev_prev_date = self.main_window.init.workdays_str[end_idx-2]
        
        prev_price = first_row[prev_date]
        prev_prev_price = first_row[prev_prev_date]
        
        # 计算前一日涨跌幅
        prev_day_change = ((prev_price - prev_prev_price) / prev_prev_price) * 100
        
        # 计算结束日涨跌幅
        end_day_change = ((end_price - prev_price) / prev_price) * 100
        
        # 获取后一组结束地址值
        diff_first_row = diff_data.iloc[0]
        diff_end_value = diff_first_row[end_date]
        
        # 获取diff_data区间数据
        diff_values = [diff_first_row[d] for d in date_range if d in diff_first_row.index and pd.notna(diff_first_row[d])]

        # 获取base_param中已算好的连续累加值
        continuous_results = self.main_window.continuous_results

        # 计算连续累加值的分段绝对值和（用Decimal保证精度）
        abs_sums_list = []
        for row in continuous_results:
            if row and isinstance(row, (list, tuple)):
                abs_arr = [abs(v) for v in row if v is not None]
                n = len(abs_arr)
                half = n // 2
                q1 = n // 4
                q2 = n // 2
                q3 = (3 * n) // 4
                abs_sums = {
                    '长度': n,
                    '前一半': sum(abs_arr[:half]),
                    '后一半': sum(abs_arr[half:]),
                    '前四分之一': sum(abs_arr[:q1]),
                    '前四分之二': sum(abs_arr[:q2]),
                    '前四分之三': sum(abs_arr[:q3]),
                    '后四分之一': sum(abs_arr[q3:]),
                }
            else:
                abs_sums = {
                    '长度': 0,
                    '前一半': '无效',
                    '后一半': '无效',
                    '前四分之一': '无效',
                    '前四分之二': '无效',
                    '前四分之三': '无效',
                    '后四分之一': '无效',
                }
            abs_sums_list.append(abs_sums)

        # 判断所有连续累加值的绝对值是否都小于用户输入
        if abs_sum_user_value is not None and continuous_results:
            is_abs_sum_less = all(abs(v) < abs_sum_user_value for v in continuous_results if v is not None)
        else:
            is_abs_sum_less = "无效"
        
        forward_max_date = self.main_window.forward_max_date
        forward_max_result = self.main_window.forward_max_result
        forward_min_date = self.main_window.forward_min_date
        forward_min_result = self.main_window.forward_min_result

        # 计算所有行的有效累加值
        base_valid_arr_list = [self.calc_valid_sum(row) for row in continuous_results]
        forward_max_valid_arr_list = [self.calc_valid_sum(row) for row in forward_max_result]
        forward_min_valid_arr_list = [self.calc_valid_sum(row) for row in forward_min_result]

        # 计算所有行的分段绝对值和
        base_valid_abs_list = [self.calc_abs_sums(arr) for arr in base_valid_arr_list]
        forward_max_valid_abs_list = [self.calc_abs_sums(arr) for arr in forward_max_valid_arr_list]
        forward_min_valid_abs_list = [self.calc_abs_sums(arr) for arr in forward_min_valid_arr_list]

        # 计算正加值和负加值
        base_pos_neg_list = [self.calc_pos_neg_sum(arr) for arr in base_valid_arr_list]
        forward_max_pos_neg_list = [self.calc_pos_neg_sum(arr) for arr in forward_max_valid_arr_list]
        forward_min_pos_neg_list = [self.calc_pos_neg_sum(arr) for arr in forward_min_valid_arr_list]

        # 显示结果
        self.main_window.result_text.setText(
            "基础数据的扩展参数: \n"
            f"区间最大值：{max_in_range}，日期：{max_date}\n"
            f"区间最小值：{min_in_range}，日期：{min_date}\n"
            f"前一组结束地址值：{end_price}\n"
            f"前N日最高值：{n_max_value}\n"
            f"前N最大值：{is_n_max}\n"
            f"区间最高价/最低价={ratio}，小于{user_value}：{is_ratio_less}\n"
            f"区间连续累加值绝对值全部小于{abs_sum_user_value}：{is_abs_sum_less}\n"
            f"前1组结束地址前1日涨跌幅：{prev_day_change:.2f}%\n"
            f"前一组结束日涨跌幅：{end_day_change:.2f}%\n"
            f"后一组结束地址值：{diff_end_value}\n"
            f"连续累加值：{continuous_results[1]}\n"
            f"向前最大开始日期：{forward_max_date} 结果：{forward_max_result[1] if forward_max_result else '无'}\n"
            f"向前最小开始日期：{forward_min_date} 结果：{forward_min_result[1] if forward_min_result else '无'}\n"
            "\n"
            "连续累加值的扩展参数: \n"
            "基本参数：\n"
            f"连续累加值开始值：{continuous_results[1][0] if continuous_results else '无'}\n"
            f"连续累加值开始后1位值：{continuous_results[1][1] if continuous_results else '无'}\n"
            f"连续累加值开始后2位值：{continuous_results[1][2] if continuous_results else '无'}\n"
            f"连续累加值结束值：{continuous_results[1][-1] if continuous_results else '无'}\n"
            f"连续累加值结束前1位值：{continuous_results[1][-2] if continuous_results else '无'}\n"
            f"连续累加值结束前2位值：{continuous_results[1][-3] if continuous_results else '无'}\n"
            f"连续累加值长度：{len(continuous_results[1]) if continuous_results else '无'}\n"
            "计算参数：\n"
            f"连续累加值前一半绝对值之和：{abs_sums_list[1]['前一半']}\n"
            f"连续累加值后一半绝对值之和：{abs_sums_list[1]['后一半']}\n"
            f"连续累加值前四分之一绝对值之和：{abs_sums_list[1]['前四分之一']}\n"
            f"连续累加值前四分之二绝对值之和：{abs_sums_list[1]['前四分之二']}\n"
            f"连续累加值前四分之三绝对值之和：{abs_sums_list[1]['前四分之三']}\n"
            f"连续累加值后四分之一绝对值之和：{abs_sums_list[1]['后四分之一']}\n"
            "有效累加值计算：\n"
            f"基础有效累加值：{', '.join([str(v) for v in base_valid_arr_list[1]]) if base_valid_arr_list else '无'}\n"
            f"向前最大有效累加值：{', '.join([str(v) for v in forward_max_valid_arr_list[1]]) if forward_max_valid_arr_list else '无'}\n"
            f"向前最小有效累加值：{', '.join([str(v) for v in forward_min_valid_arr_list[1]]) if forward_min_valid_arr_list else '无'}\n"
            "有效累加值正加值和负加值：\n"
            f"基础有效累加正加值：{base_pos_neg_list[1][0] if base_pos_neg_list else 0}，基础有效累加负加值：{base_pos_neg_list[1][1] if base_pos_neg_list else 0}\n"
            f"向前最大有效累加正加值：{forward_max_pos_neg_list[1][0] if forward_max_pos_neg_list else 0}，向前最大有效累加负加值：{forward_max_pos_neg_list[1][1] if forward_max_pos_neg_list else 0}\n"
            f"向前最小有效累加正加值：{forward_min_pos_neg_list[1][0] if forward_min_pos_neg_list else 0}，向前最小有效累加负加值：{forward_min_pos_neg_list[1][1] if forward_min_pos_neg_list else 0}\n"
            "有效累加值分段绝对值和：\n"
            f"基础有效累加值长度：{base_valid_abs_list[1]['长度']}\n"
            f"基础有效累加值前一半绝对值之和：{base_valid_abs_list[1]['前一半']}，基础有效累加值后一半绝对值之和：{base_valid_abs_list[1]['后一半']}\n"
            f"基础有效累加值前四分之一绝对值之和：{base_valid_abs_list[1]['前四分之一']}，基础有效累加值前四分之二绝对值之和：{base_valid_abs_list[1]['前四分之二']}，基础有效累加值前四分之三绝对值之和：{base_valid_abs_list[1]['前四分之三']}，基础有效累加值后四分之一绝对值之和：{base_valid_abs_list[1]['后四分之一']}\n"
            f"向前最大有效累加值长度：{forward_max_valid_abs_list[1]['长度']}\n"
            f"向前最大有效累加值前一半绝对值之和：{forward_max_valid_abs_list[1]['前一半']}，向前最大有效累加值后一半绝对值之和：{forward_max_valid_abs_list[1]['后一半']}\n"
            f"向前最大有效累加值前四分之一绝对值之和：{forward_max_valid_abs_list[1]['前四分之一']}，向前最大有效累加值前四分之二绝对值之和：{forward_max_valid_abs_list[1]['前四分之二']}，向前最大有效累加值前四分之三绝对值之和：{forward_max_valid_abs_list[1]['前四分之三']}，向前最大有效累加值后四分之一绝对值之和：{forward_max_valid_abs_list[1]['后四分之一']}\n"
            f"向前最小有效累加值长度：{forward_min_valid_abs_list[1]['长度']}\n"
            f"向前最小有效累加值前一半绝对值之和：{forward_min_valid_abs_list[1]['前一半']}，向前最小有效累加值后一半绝对值之和：{forward_min_valid_abs_list[1]['后一半']}\n"
            f"向前最小有效累加值前四分之一绝对值之和：{forward_min_valid_abs_list[1]['前四分之一']}，向前最小有效累加值前四分之二绝对值之和：{forward_min_valid_abs_list[1]['前四分之二']}，向前最小有效累加值前四分之三绝对值之和：{forward_min_valid_abs_list[1]['前四分之三']}，向前最小有效累加值后四分之一绝对值之和：{forward_min_valid_abs_list[1]['后四分之一']}\n"
        ) 

    @staticmethod
    def calc_valid_sum(arr):
        # arr为Decimal或float列表
        if not arr or len(arr) < 2:
            return []
        result = []
        for i in range(len(arr) - 1):
            cur = arr[i]
            nxt = arr[i + 1]
            if abs(nxt) > abs(cur):
                result.append(cur)
            else:
                result.append(abs(nxt) if cur >= 0 else -abs(nxt))
        # 最后一个元素，因为没有下一个元素可以比较，返回0
        result.append(0)
        return result

    @staticmethod
    def calc_pos_neg_sum(arr):
        # arr为有效累加值列表
        pos_sum = sum(v for v in arr if v > 0)
        neg_sum = sum(v for v in arr if v < 0)
        return pos_sum, neg_sum

    @staticmethod
    def calc_abs_sums(arr):
        # arr为有效累加值列表
        arr = [v for v in arr if v is not None]
        n = len(arr)
        if n == 0:
            return {
                '长度': 0,
                '前一半': '无效',
                '后一半': '无效',
                '前四分之一': '无效',
                '前四分之二': '无效',
                '前四分之三': '无效',
                '后四分之一': '无效',
            }
        abs_arr = [abs(v) for v in arr]
        half = n // 2
        q1 = n // 4
        q2 = n // 2
        q3 = (3 * n) // 4
        return {
            '长度': n,
            '前一半': sum(abs_arr[:half]),
            '后一半': sum(abs_arr[half:]),
            '前四分之一': sum(abs_arr[:q1]),
            '前四分之二': sum(abs_arr[:q2]),
            '前四分之三': sum(abs_arr[:q3]),
            '后四分之一': sum(abs_arr[q3:]),
        } 