"""
组合分析UI模块
提供组合分析功能的独立界面
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton, 
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QCheckBox, QTabWidget, QSpinBox, QDialog, QScrollArea, QMainWindow
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont
import pandas as pd
from datetime import datetime
from function.stock_functions import show_formula_select_table, calculate_analysis_result, get_abbr_map, get_abbr_logic_map, get_abbr_round_map, FormulaSelectWidget
from ui.common_widgets import CopyableTableWidget
import time
import re


class ComponentAnalysisWidget(QWidget):
    """组合分析界面组件"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cached_analysis_results = None
        self.analysis_terminated = False  # 添加终止标志
        self.init_ui()
        
        # 连接勾选框状态改变信号
        self.continuous_sum_logic_checkbox.stateChanged.connect(self._on_continuous_sum_logic_changed)
        self.valid_sum_logic_checkbox.stateChanged.connect(self._on_valid_sum_logic_changed)
        self.generate_trading_plan_checkbox.stateChanged.connect(self._on_generate_trading_plan_changed)
        self.only_better_trading_plan_checkbox.stateChanged.connect(self._on_only_better_trading_plan_changed)
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 顶部参数控件
        row_layout = QHBoxLayout()
        
        # 日期选择控件
        self.start_date_label = QLabel("结束日期开始日:")
        self.start_date_picker = QDateEdit(calendarPopup=True)
        
        # 使用保存的日期值或默认值
        if hasattr(self.main_window, 'last_component_analysis_start_date'):
            self.start_date_picker.setDate(QDate.fromString(
                self.main_window.last_component_analysis_start_date, "yyyy-MM-dd"))
        else:
            self.start_date_picker.setDate(self.main_window.date_picker.date())
            
        self.end_date_label = QLabel("结束日期结束日:")
        self.end_date_picker = QDateEdit(calendarPopup=True)
        
        if hasattr(self.main_window, 'last_component_analysis_end_date'):
            self.end_date_picker.setDate(QDate.fromString(
                self.main_window.last_component_analysis_end_date, "yyyy-MM-dd"))
        else:
            self.end_date_picker.setDate(self.main_window.date_picker.date())
            
        # 绑定信号，变更时同步变量
        self.start_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
        self.end_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
        
        # 添加勾选框
        self.continuous_sum_logic_checkbox = QCheckBox("连续累加值正负相加值含逻辑")
        self.continuous_sum_logic_checkbox.setChecked(False)  # 默认不勾选
        
        self.valid_sum_logic_checkbox = QCheckBox("有效累加值正负相加值含逻辑")
        self.valid_sum_logic_checkbox.setChecked(False)  # 默认不勾选
        
        # 组合分析次数设置控件
        self.analysis_count_label = QLabel("组合分析次数:")
        self.analysis_count_spin = QSpinBox()
        self.analysis_count_spin.setMinimum(1)
        self.analysis_count_spin.setMaximum(1000)
        self.analysis_count_spin.setValue(1)  # 默认1次
        self.analysis_count_spin.setFixedWidth(45)
        
        # 恢复保存的分析次数
        if hasattr(self.main_window, 'last_component_analysis_count'):
            self.analysis_count_spin.setValue(self.main_window.last_component_analysis_count)
        
        # 绑定信号，变更时同步变量
        self.analysis_count_spin.valueChanged.connect(self._on_analysis_count_changed_save)
        
        # 功能按钮
        self.analyze_btn = QPushButton("点击分析")
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        
        self.terminate_btn = QPushButton("终止分析")
        self.terminate_btn.clicked.connect(self.on_terminate_clicked)
        self.terminate_btn.setEnabled(False)  # 初始状态禁用
        
        self.export_json_btn = QPushButton("导出最优方案")
        self.export_json_btn.clicked.connect(self.on_export_json)
        
        self.import_json_btn = QPushButton("导入方案")
        self.import_json_btn.clicked.connect(self.on_import_json)
        
        # 生成操盘方案勾选框
        self.generate_trading_plan_checkbox = QCheckBox("生成操盘方案")
        self.generate_trading_plan_checkbox.setChecked(False)  # 默认不勾选
        
        # 恢复生成操盘方案勾选框状态
        if hasattr(self.main_window, 'last_component_generate_trading_plan'):
            self.generate_trading_plan_checkbox.setChecked(self.main_window.last_component_generate_trading_plan)
        
        # 大于上次最优值才生成操盘方案勾选框
        self.only_better_trading_plan_checkbox = QCheckBox("大于上次最优值才生成操盘方案")
        self.only_better_trading_plan_checkbox.setChecked(False)  # 默认不勾选
        
        # 恢复大于上次最优值才生成操盘方案勾选框状态
        if hasattr(self.main_window, 'last_component_only_better_trading_plan'):
            self.only_better_trading_plan_checkbox.setChecked(self.main_window.last_component_only_better_trading_plan)
        
        # 上次最优值显示标签
        self.last_best_value_label = QLabel("上次最优值：")
        self.last_best_value_display = QLabel("无")
        self.last_best_value_display.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # 新增：清空按钮
        self.clear_best_value_btn = QPushButton("清空")
        self.clear_best_value_btn.setFixedWidth(40)
        self.clear_best_value_btn.clicked.connect(self._on_clear_best_value)
        
        # 更新上次最优值显示
        self._update_last_best_value_display()
        
        # 添加控件到布局
        # row_layout.addWidget(self.start_date_label)
        # row_layout.addWidget(self.start_date_picker)
        # row_layout.addWidget(self.end_date_label)
        # row_layout.addWidget(self.end_date_picker)
        # row_layout.addWidget(self.continuous_sum_logic_checkbox)
        # row_layout.addWidget(self.valid_sum_logic_checkbox)
        row_layout.addWidget(self.analysis_count_label)
        row_layout.addWidget(self.analysis_count_spin)
        row_layout.addWidget(self.analyze_btn)
        row_layout.addWidget(self.terminate_btn)
        row_layout.addWidget(self.export_json_btn)
        row_layout.addWidget(self.import_json_btn)
        row_layout.addWidget(self.generate_trading_plan_checkbox)
        row_layout.addWidget(self.only_better_trading_plan_checkbox)
        row_layout.addWidget(self.last_best_value_label)
        row_layout.addWidget(self.last_best_value_display)
        row_layout.addWidget(self.clear_best_value_btn)
        row_layout.addStretch()
        
        layout.addLayout(row_layout)
        
        # 输出区
        self.result_area = QWidget()
        self.result_layout = QVBoxLayout(self.result_area)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(0)
        
        # 默认显示文本区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        self.result_text.setText("请点击'点击分析'按钮开始组合分析...")
        self.result_layout.addWidget(self.result_text)
        
        layout.addWidget(self.result_area)
        
        # 新增：优先从主窗口恢复
        if hasattr(self.main_window, 'cached_component_analysis_results') and self.main_window.cached_component_analysis_results:
            self.set_cached_analysis_results(self.main_window.cached_component_analysis_results)
        else:
            print("没有缓存结果")
        
        # 更新上次最优值显示
        self._update_last_best_value_display()
        
    def _on_analysis_date_changed_save(self):
        """保存日期变更"""
        self.main_window.last_component_analysis_start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        self.main_window.last_component_analysis_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
        
    def _on_analysis_count_changed_save(self):
        """保存分析次数变更"""
        self.main_window.last_component_analysis_count = self.analysis_count_spin.value()
        
    def on_analyze_clicked(self):
        
        # 获取组合分析次数
        analysis_count = self.analysis_count_spin.value()
        
        # 获取结束日期（使用主界面的date_picker）
        end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
        
        # 根据组合分析次数计算开始日期
        workdays = getattr(self.main_window.init, 'workdays_str', None)
        if not workdays:
            QMessageBox.warning(self, "数据错误", "没有可用的日期范围，请先上传数据文件！")
            return
            
        try:
            # 获取结束日期在workdays中的索引
            end_date_idx = workdays.index(end_date)
            # 根据分析次数计算开始日期索引
            start_date_idx = end_date_idx - (analysis_count - 1)
            
            # 检查索引是否有效
            if start_date_idx < 0:
                QMessageBox.warning(self, "数据错误", f"组合分析次数 {analysis_count} 超出可用日期范围！\n当前结束日期索引: {end_date_idx}，需要开始日期索引: {start_date_idx}")
                return
                
            # 获取开始日期
            start_date = workdays[start_date_idx]
            
        except ValueError:
            QMessageBox.warning(self, "日期错误", f"结束日期 {end_date} 不在交易日列表中！")
            return
        
        # 获取勾选框状态
        continuous_sum_logic = self.continuous_sum_logic_checkbox.isChecked()
        valid_sum_logic = self.valid_sum_logic_checkbox.isChecked()
        generate_trading_plan = self.generate_trading_plan_checkbox.isChecked()
        
        # 如果勾选了生成操盘方案，检查列表长度
        if generate_trading_plan:
            # 确保主窗口有trading_plan_list属性
            if not hasattr(self.main_window, 'trading_plan_list'):
                self.main_window.trading_plan_list = []
            
            # 检查列表长度是否小于6
            if len(self.main_window.trading_plan_list) >= 6:
                QMessageBox.warning(self, "提示", "操盘方案已满（最多6个），请先进行删除！")
                return
        
        # 生成组合公式列表
        formula_list = []
        
        try:
            # 直接创建临时的公式选股控件，不依赖主窗口中的引用
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            
            # 创建临时控件（不显示界面）
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
            
            # 恢复保存的状态（如果有的话）
            if hasattr(self.main_window, 'last_formula_select_state'):
                temp_formula_widget.set_state(self.main_window.last_formula_select_state)
            
            # 获取get_abbr_round_only_map的勾选状态
            selected_round_only_vars = temp_formula_widget.get_round_only_map_selected_vars()
            print(f"获取到的get_abbr_round_only_map勾选变量: {selected_round_only_vars}")
            
            # 获取N位控件值
            n_values = {}
            n_vars = ['bottom_nth_non_nan1', 'bottom_nth_non_nan2', 'bottom_nth_non_nan3',
                     'bottom_nth_with_nan1', 'bottom_nth_with_nan2', 'bottom_nth_with_nan3',
                     'bottom_nth_adjust_non_nan1', 'bottom_nth_adjust_non_nan2', 'bottom_nth_adjust_non_nan3',
                     'bottom_nth_adjust_with_nan1', 'bottom_nth_adjust_with_nan2', 'bottom_nth_adjust_with_nan3']
            
            for var_name in n_vars:
                try:
                    if var_name in temp_formula_widget.var_widgets:
                        widgets = temp_formula_widget.var_widgets[var_name]
                        if 'n_input' in widgets and widgets['n_input'] is not None:
                            n_text = widgets['n_input'].text().strip()
                            if n_text:
                                try:
                                    n_values[var_name] = int(n_text)
                                except ValueError:
                                    n_values[var_name] = 1  # 默认值为1
                            else:
                                n_values[var_name] = 1  # 默认值为1
                        else:
                            n_values[var_name] = 1  # 默认值为1
                    else:
                        n_values[var_name] = 1  # 默认值为1
                except:
                    n_values[var_name] = 1  # 默认值为1
            
            print(f"获取到的N位控件值: {n_values}")
            
            # 检查是否选择了组合分析输出值
            if not selected_round_only_vars:
                QMessageBox.warning(self, "提示", "请先选择组合分析输出值！\n")
                return
            
            # 生成公式列表
            formula_list = temp_formula_widget.generate_formula_list()
            print(f"生成了 {len(formula_list)} 个组合公式")
            
            # 生成特殊参数组合
            special_params_combinations = temp_formula_widget.generate_special_params_combinations()
            print(f"生成了 {len(special_params_combinations)} 个特殊参数组合")
            
            # 清理临时控件
            temp_formula_widget.deleteLater()
            
        except Exception as e:
            print(f"生成组合公式列表时出错: {e}")
            self.show_message(f"生成组合公式列表时出错: {e}")
            return
        
        # 将公式列表和特殊参数组合保存到主窗口，供后续使用
        if formula_list:
            self.main_window.component_analysis_formula_list = formula_list
            self.main_window.component_analysis_special_params_combinations = special_params_combinations
            self.main_window.component_analysis_selected_round_only_vars = selected_round_only_vars  # 保存勾选状态
            self.main_window.component_analysis_n_values = n_values  # 保存N位控件值
            self.show_message(f"成功生成 {len(formula_list)} 个组合公式和 {len(special_params_combinations)} 个特殊参数组合，开始执行组合分析...")
            
            # 检查数据文件是否已上传
            if not hasattr(self.main_window.init, 'price_data') or self.main_window.init.price_data is None:
                QMessageBox.warning(self, "数据错误", "没有可用的日期范围，请先上传数据文件！")
                return
            
            # 重置终止标志
            self.analysis_terminated = False
            
            # 切换按钮状态
            self.analyze_btn.setEnabled(False)
            self.terminate_btn.setEnabled(True)
            
            # 开始执行组合分析
            self.execute_component_analysis(formula_list, special_params_combinations, start_date, end_date)
        else:
            self.show_message("未生成任何组合公式，请检查参数设置！")
            return
            
        # 显示组合分析界面
        # self.show_component_analysis_interface()
        
    def on_terminate_clicked(self):
        """终止分析按钮点击处理"""
        self.analysis_terminated = True
        self.show_message("分析已终止")
        
        # 切换按钮状态
        self.analyze_btn.setEnabled(True)
        self.terminate_btn.setEnabled(False)
        
    def execute_component_analysis(self, formula_list, special_params_combinations, start_date, end_date):
        """
        执行组合分析
        对每个公式和每个特殊参数组合执行一次自动分析
        使用异步方式，等待上一次分析完成后再执行下一次
        """
        try:
            # 记录开始时间
            self.analysis_start_time = time.time()
            
            # 计算总的分析次数（考虑排序方式）
            total_analyses = len(formula_list) * len(special_params_combinations)
            current_analysis = 0
            
            # 存储所有分析结果
            all_analysis_results = []
            
            # 显示进度信息
            self.show_message(f"开始执行组合分析，总共 {total_analyses} 次分析...")
            
            # 使用异步方式执行分析
            self.current_analysis_index = 0
            self.total_analyses = total_analyses
            self.formula_list = formula_list
            self.special_params_combinations = special_params_combinations
            self.all_analysis_results = all_analysis_results
            self.start_date = start_date
            self.end_date = end_date
            self.component_analysis_completed_index = -1  # 组合分析专用的完成标记
            
            # 开始第一次分析
            self.execute_next_analysis()
            
        except Exception as e:
            print(f"组合分析执行出错: {e}")
            self.show_message(f"组合分析执行出错: {e}")
    
    def check_analysis_completed(self):
        """
        检查上一次分析是否完成，使用组合分析专用的完成标记
        """
        return self.component_analysis_completed_index == (self.current_analysis_index - 1)
    
    def execute_next_analysis(self):
        """
        执行下一次分析
        """
        # 检查是否被终止
        if self.analysis_terminated:
            # 恢复按钮状态
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            return
            
        if self.current_analysis_index >= self.total_analyses:
            # 所有分析完成
            self.show_analysis_results(self.all_analysis_results)
            
            # 检查是否有更优结果（用于弹框提示，独立于勾选框状态）
            if self.cached_analysis_results:
                top_one = self.cached_analysis_results[0]
                new_value = top_one.get('adjusted_value', None)
                last_value = getattr(self.main_window, 'last_adjusted_value', None)
                
                if new_value is not None and last_value is not None:
                    try:
                        new_value_float = float(new_value)
                        last_value_float = float(last_value)
                        if new_value_float > last_value_float:
                            QMessageBox.information(self, "最优方案提示", f"有最优方案出现！当前最优组合排序输出值：{new_value_float:.2f}，上次最优：{last_value_float:.2f}")
                    except Exception:
                        pass  # 转换失败时不处理
            
            # 只在分析全部完成后，且勾选生成操盘方案时，添加一次方案
            if self.generate_trading_plan_checkbox.isChecked() and self.cached_analysis_results:
                top_one = self.cached_analysis_results[0]
                # 比较top_one的adjusted_value与上次的last_adjusted_value
                new_value = top_one.get('adjusted_value', None)
                last_value = getattr(self.main_window, 'last_adjusted_value', None)
                
                # 第一步：判断是否要生成操盘方案
                should_generate = True
                
                # 第二步：如果勾选了"更优才生成"，则进一步判断是否更优
                if self.only_better_trading_plan_checkbox.isChecked():
                    if new_value is not None and last_value is not None:
                        try:
                            new_value_float = float(new_value)
                            last_value_float = float(last_value)
                            should_generate = new_value_float > last_value_float
                        except Exception:
                            should_generate = True  # 转换失败时默认生成
                    elif new_value is not None and last_value is None:
                        # 第一次生成时，直接生成
                        should_generate = True
                    else:
                        should_generate = False
                # 如果没有勾选"更优才生成"，则直接生成（should_generate保持为True）
                
                # 根据should_generate决定是否生成操盘方案
                if should_generate:
                    # 生成操盘方案
                    self._add_top_result_to_trading_plan(top_one)
                    # 更新上次最优值显示
                    self._update_last_best_value_display()
                
                # 更新last_adjusted_value（只有在新的值大于上次的值时才更新）
                if new_value is not None:
                    try:
                        new_value_float = float(new_value)
                        last_value_float = float(last_value) if last_value is not None else None
                        
                        # 只有当新值大于上次值时才更新
                        if last_value_float is None or new_value_float > last_value_float:
                            self.main_window.last_adjusted_value = new_value_float
                            # 更新上次最优值显示
                            self._update_last_best_value_display()
                    except Exception:
                        # 转换失败时，如果last_value为None则设置，否则保持原值
                        if last_value is None:
                            self.main_window.last_adjusted_value = new_value
                            # 更新上次最优值显示
                            self._update_last_best_value_display()
            
            # 恢复按钮状态
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            return
        
        # 如果是第一次分析，直接执行
        if self.current_analysis_index == 0:
            self._execute_single_analysis()
        else:
            # 检查上一次分析是否完成
            if self.check_analysis_completed():
                self._execute_single_analysis()
            else:
                # 上一次分析还未完成，继续等待
                print(f"等待上一次分析完成...")
                QTimer.singleShot(2000, self.execute_next_analysis)  # 2秒后再次检查
    
    def _execute_single_analysis(self):
        """
        执行单次分析
        """
        # 检查是否被终止
        if self.analysis_terminated:
            return
            
        # 计算当前公式和参数索引
        formula_idx = self.current_analysis_index // len(self.special_params_combinations)
        param_idx = self.current_analysis_index % len(self.special_params_combinations)
        
        formula_obj = self.formula_list[formula_idx]
        formula = formula_obj['formula']
        sort_mode = formula_obj['sort_mode']
        width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio = self.special_params_combinations[param_idx]
        # 打印当前执行的公式和参数
        print("正在执行分析，请不要切换界面导致分析中断...")
        print(f"\n{'='*80}")
        print(f"正在执行第 {self.current_analysis_index + 1}/{self.total_analyses} 次分析")
        print(f"公式组合 {formula_idx + 1}/{len(self.formula_list)}:")
        print(formula)
        print(f"排序方式: {sort_mode}")
        print(f"参数组合 {param_idx + 1}/{len(self.special_params_combinations)}:")
        print(f"  日期宽度: {width}")
        print(f"  操作天数: {op_days}")
        print(f"  止盈递增值: {increment_rate}")
        print(f"  止盈后值大于结束值比例: {after_gt_end_ratio}")
        print(f"  止盈后值大于开始值比例: {after_gt_start_ratio}")
        print(f"  止损递增值: {stop_loss_inc_rate}")
        print(f"  止损后值大于结束值比例: {stop_loss_after_gt_end_ratio}")
        print(f"  止损后值大于开始值比例: {stop_loss_after_gt_start_ratio}")
        print(f"{'='*80}")
        # 显示当前进度
        progress_msg = f"正在执行分析，请不要切换界面导致分析中断...\n"
        progress_msg += f"正在执行第 {self.current_analysis_index + 1}/{self.total_analyses} 次分析...\n"
        progress_msg += f"公式组合 {formula_idx + 1}/{len(self.formula_list)}\n"
        progress_msg += f"{formula}\n"
        progress_msg += f"排序方式: {sort_mode}\n"
        progress_msg += f"参数组合 {param_idx + 1}/{len(self.special_params_combinations)}\n"
        progress_msg += f"日期宽度={width}, 操作天数={op_days}, 递增值={increment_rate}, 后值大于结束值比例={after_gt_end_ratio}, 后值大于开始值比例={after_gt_start_ratio}, 止损递增值={stop_loss_inc_rate}, 止损后值大于结束值比例={stop_loss_after_gt_end_ratio}, 止损后值大于开始值比例={stop_loss_after_gt_start_ratio}"
        self.show_message(progress_msg)
        
        try:
            # 设置当前公式
            self.main_window.last_formula_expr = formula
            
            # 执行组合分析专用方法，直接传递参数
            result = self._execute_component_analysis_single(formula, width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio, sort_mode)
            
            # 再次检查是否被终止
            if self.analysis_terminated:
                return
            
            if result and not result.get('error', False):
                # 直接从result中获取valid_items用于计算统计结果
                merged_results = result.get('dates', {}) if result else {}
                valid_items = [(date_key, stocks) for date_key, stocks in merged_results.items()]
                
                # 调用calculate_analysis_result计算统计结果
                analysis_stats = calculate_analysis_result(valid_items)
                
                # 获取选股数量
                select_count = getattr(self.main_window, 'last_select_count', 10)
                
                # 收集分析结果
                analysis_info = {
                    'formula_idx': formula_idx + 1,
                    'param_idx': param_idx + 1,
                    'formula': formula,
                    'sort_mode': sort_mode,
                    'width': width,
                    'op_days': op_days,
                    'increment_rate': increment_rate,
                    'after_gt_end_ratio': after_gt_end_ratio,
                    'after_gt_start_ratio': after_gt_start_ratio,
                    'stop_loss_inc_rate': stop_loss_inc_rate,
                    'stop_loss_after_gt_end_ratio': stop_loss_after_gt_end_ratio,
                    'stop_loss_after_gt_start_ratio': stop_loss_after_gt_start_ratio,
                    'select_count': select_count,  # 添加选股数量
                    'result': result,
                    'valid_items': valid_items,
                    'analysis_stats': analysis_stats  # 添加统计结果
                }
                self.all_analysis_results.append(analysis_info)
                
                print(f"第 {self.current_analysis_index + 1} 次分析完成")
            else:
                error_msg = result.get('message', '分析失败') if result else '分析失败'
                print(f"第 {self.current_analysis_index + 1} 次分析失败: {error_msg}")
                self.show_message(f"第 {self.current_analysis_index + 1} 次分析失败: {error_msg}")
        except Exception as e:
            print(f"第 {self.current_analysis_index + 1} 次分析出错: {e}")
        
        # 标记当前分析完成（在索引增加之前）
        self.component_analysis_completed_index = self.current_analysis_index
        
        # 增加索引，准备执行下一次分析
        self.current_analysis_index += 1
        
        # 使用QTimer延迟执行下一次分析，确保当前分析完全完成
        QTimer.singleShot(3000, self.execute_next_analysis)  # 3秒后执行下一次分析
    
    def _execute_component_analysis_single(self, formula, width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio, sort_mode):
        """
        执行单次组合分析
        专门为组合分析创建的方法，避免依赖自动分析子界面的控件
        """
        from PyQt5.QtWidgets import QMessageBox
        from datetime import datetime
        
        # 使用传入的日期范围，而不是从控件获取
        start_date = self.start_date
        end_date = self.end_date
        
        # 校验日期是否在范围内
        workdays = getattr(self.main_window.init, 'workdays_str', None)
        if not workdays:
            return {
                'error': True,
                'message': "没有可用的日期范围，请先上传数据文件！"
            }

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        workday_first = datetime.strptime(workdays[0], "%Y-%m-%d").date()
        workday_last = datetime.strptime(workdays[-1], "%Y-%m-%d").date()
        
        if start_dt > end_dt:
            return {
                'error': True,
                'message': "结束日要大于开始日"
            }
            
        # 自动调整日期：如果start_date不是交易日，则往日期增大的方向找到第一个可用交易日
        if start_date not in workdays:
            print(f"start_date not in workdays: {start_date}")
            if start_dt > workday_last:
                start_date = workdays[-1]
            else:
                for d in workdays:
                    if d >= start_date:
                        start_date = d
                        break
            
        start_date_idx = workdays.index(start_date)
        if start_date_idx - width < 0 and width < len(workdays):
            print(f"start_date_idx - width < 0 and width < len(workdays): {start_date}")
            start_date = workdays[width]
            
        # 自动调整日期：如果end_date不是交易日，则往日期减小的方向找到第一个可用交易日
        if end_date not in workdays:
            print(f"end_date not in workdays: {end_date}")
            if end_dt < workday_first:
                end_date = start_date
            else:
                for d in reversed(workdays):
                    if d <= end_date:
                        end_date = d
                        break
        
        # 检查创新高新低日期宽度
        # 创新高参数
        new_before_high_flag = self.main_window.new_before_high_flag_checkbox.isChecked()
        new_before_high2_flag = self.main_window.new_before_high2_flag_checkbox.isChecked()
        new_after_high_flag = self.main_window.new_after_high_flag_checkbox.isChecked()
        new_after_high2_flag = self.main_window.new_after_high2_flag_checkbox.isChecked()
        new_before_low_flag = self.main_window.new_before_low_flag_checkbox.isChecked()
        new_before_low2_flag = self.main_window.new_before_low2_flag_checkbox.isChecked()
        new_after_low_flag = self.main_window.new_after_low_flag_checkbox.isChecked()
        new_after_low2_flag = self.main_window.new_after_low2_flag_checkbox.isChecked()

        nh_start = self.main_window.new_before_high_start_spin.value()
        nh_range = self.main_window.new_before_high_range_spin.value()
        nh_span = self.main_window.new_before_high_span_spin.value()
        nh_total = nh_start + nh_range + nh_span
        if new_before_high_flag and start_date_idx - nh_total < 0:
            return {
                'error': True,
                'message': "创前新高1日期范围超出数据范围，请调整结束日期开始日！"
            }
        
        # 创前新高2参数
        nh2_start = self.main_window.new_before_high2_start_spin.value()
        nh2_range = self.main_window.new_before_high2_range_spin.value()
        nh2_span = self.main_window.new_before_high2_span_spin.value()
        nh2_total = nh2_start + nh2_range + nh2_span
        if new_before_high2_flag and start_date_idx - nh2_total < 0:
            return {
                'error': True,
                'message': "创前新高2日期范围超出数据范围，请调整结束日期开始日！"
            }
        
        # 创后新高1参数
        new_after_high_start = self.main_window.new_after_high_start_spin.value()
        new_after_high_range = self.main_window.new_after_high_range_spin.value()
        new_after_high_span = self.main_window.new_after_high_span_spin.value()
        new_after_high_total = new_after_high_start + new_after_high_range + new_after_high_span
        if new_after_high_flag and start_date_idx - new_after_high_total < 0:
            return {
                'error': True,
                'message': "创后新高1日期范围超出数据范围，请调整结束日期开始日！"
            }

        # 创后新高2参数
        new_after_high2_start = self.main_window.new_after_high2_start_spin.value()
        new_after_high2_range = self.main_window.new_after_high2_range_spin.value()
        new_after_high2_span = self.main_window.new_after_high2_span_spin.value()
        new_after_high2_total = new_after_high2_start + new_after_high2_range + new_after_high2_span
        if new_after_high2_flag and start_date_idx - new_after_high2_total < 0:
            return {
                'error': True,
                'message': "创后新高2日期范围超出数据范围，请调整结束日期开始日！"
            }
            
        # 创前新低1参数
        nl_start = self.main_window.new_before_low_start_spin.value()
        nl_range = self.main_window.new_before_low_range_spin.value()
        nl_span = self.main_window.new_before_low_span_spin.value()
        nl_total = nl_start + nl_range + nl_span
        if new_before_low_flag and start_date_idx - nl_total < 0:
            return {
                'error': True,
                'message': "创新低日期范围超出数据范围，请调整结束日期开始日！"
            }
        
        # 创前新低2参数
        nh2_start = self.main_window.new_before_high2_start_spin.value()
        nh2_range = self.main_window.new_before_high2_range_spin.value()
        nh2_span = self.main_window.new_before_high2_span_spin.value()
        nh2_total = nh2_start + nh2_range + nh2_span
        if new_before_high2_flag and start_date_idx - nh2_total < 0:
            return {
                'error': True,
                'message': "创前新高2日期范围超出数据范围，请调整结束日期开始日！"
            }

        # 创后新低1参数
        new_after_low_start = self.main_window.new_after_low_start_spin.value()
        new_after_low_range = self.main_window.new_after_low_range_spin.value()
        new_after_low_span = self.main_window.new_after_low_span_spin.value()
        new_after_low_total = new_after_low_start + new_after_low_range + new_after_low_span
        if new_after_low_flag and start_date_idx - new_after_low_total < 0:
            return {
                'error': True,
                'message': "创后新低1日期范围超出数据范围，请调整结束日期开始日！"
            }
        
        # 创后新低2参数
        new_after_low2_start = self.main_window.new_after_low2_start_spin.value()
        new_after_low2_range = self.main_window.new_after_low2_range_spin.value()
        new_after_low2_span = self.main_window.new_after_low2_span_spin.value()
        new_after_low2_total = new_after_low2_start + new_after_low2_range + new_after_low2_span
        if new_after_low2_flag and start_date_idx - new_after_low2_total < 0:
            return {
                'error': True,
                'message': "创后新低2日期范围超出数据范围，请调整结束日期开始日！"
            }
        
        # 获取选股数量和排序方式
        select_count = getattr(self.main_window, 'last_select_count', 10)
        # 调用主窗口的计算方法，直接传递参数
        result = self.main_window.get_or_calculate_result(
            formula_expr=formula, 
            show_main_output=False, 
            only_show_selected=True, 
            is_auto_analysis=True,
            select_count=select_count,
            sort_mode=sort_mode,
            end_date_start=start_date,
            end_date_end=end_date,
            width=int(float(width)),
            op_days=op_days,
            inc_rate=increment_rate,
            after_gt_end_ratio=after_gt_end_ratio,
            after_gt_start_ratio=after_gt_start_ratio,
            stop_loss_inc_rate=stop_loss_inc_rate,
            stop_loss_after_gt_end_ratio=stop_loss_after_gt_end_ratio,
            stop_loss_after_gt_start_ratio=stop_loss_after_gt_start_ratio
        )
        
        if result:
            merged_results = result.get('dates', {}) if result else {}
            valid_items = [(date_key, stocks) for date_key, stocks in merged_results.items()]
            
            return result
        else:
            return {
                'error': True,
                'message': "计算失败，请检查参数设置"
            }
    
    def show_analysis_results(self, all_analysis_results):
        """
        显示组合分析结果（只输出排序前3的单页表格）
        """
        if not all_analysis_results:
            self.show_message("没有有效的分析结果")
            return
        print(f"show_analysis_results length = {len(all_analysis_results)}")
        # 如果已经是top_three结构，直接展示
        if isinstance(all_analysis_results, list) and all_analysis_results and isinstance(all_analysis_results[0], dict) and 'analysis' in all_analysis_results[0]:
            top_three = all_analysis_results
        else:
            # 处理get_abbr_round_only_map的勾选情况，获取top_three
            top_three = []
            selected_vars = getattr(self.main_window, 'component_analysis_selected_round_only_vars', [])
            if selected_vars:
                import math
                analysis_with_sum = []
                for i, analysis in enumerate(all_analysis_results):
                    analysis_stats = analysis.get('analysis_stats')
                    if not analysis_stats:
                        continue
                    summary = analysis_stats.get('summary', {})
                    if not summary:
                        continue
                    total_sum = 0
                    valid_count = 0
                    selected_vars_with_values = []
                    for var_name in selected_vars:
                        if var_name in summary:
                            value = summary[var_name]
                            if value != '' and not (isinstance(value, float) and math.isnan(value)):
                                try:
                                    value_float = float(value)
                                    total_sum += value_float
                                    valid_count += 1
                                    selected_vars_with_values.append((var_name, value_float))
                                except (ValueError, TypeError):
                                    continue
                    if valid_count > 0:
                        op_days = analysis.get('op_days', 1)
                        try:
                            op_days = int(op_days)
                        except (ValueError, TypeError):
                            op_days = 1
                        adjusted_value = total_sum / (1 + (op_days - 1) / 100)
                        # 将selected_vars_with_values添加到analysis中
                        analysis['selected_vars_with_values'] = selected_vars_with_values
                        # 获取n_values
                        n_values = getattr(self.main_window, 'component_analysis_n_values', {})
                        analysis['n_values'] = n_values
                        analysis_with_sum.append({
                            'index': i,
                            'analysis': analysis,
                            'total_sum': total_sum,
                            'valid_count': valid_count,
                            'avg_sum': total_sum / valid_count,
                            'op_days': op_days,
                            'adjusted_value': adjusted_value
                        })
                analysis_with_sum.sort(key=lambda x: x['adjusted_value'], reverse=True)
                top_three = analysis_with_sum[:3]

        # 缓存top_three用于保存和恢复
        self.cached_analysis_results = top_three
        self.main_window.cached_component_analysis_results = top_three
        
        # 清理旧内容
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 计算组合次数和真实耗时
        total_combinations = len(getattr(self.main_window, 'component_analysis_formula_list', [])) * len(getattr(self.main_window, 'component_analysis_special_params_combinations', []))
        
        # 计算真实耗时
        if hasattr(self, 'analysis_start_time'):
            real_time = time.time() - self.analysis_start_time
            if real_time < 60:
                time_str = f"{real_time:.1f}秒"
            elif real_time < 3600:
                minutes = int(real_time // 60)
                seconds = int(real_time % 60)
                time_str = f"{minutes}分{seconds}秒"
            else:
                hours = int(real_time // 3600)
                minutes = int((real_time % 3600) // 60)
                time_str = f"{hours}小时{minutes}分"
                # 保存格式化后的时间字符串和组合次数到主窗口
            self.main_window.last_component_total_elapsed_time = time_str
            self.main_window.last_component_total_combinations = total_combinations
        else:
            # 没有计算，从主窗口恢复总耗时和组合次数
            if hasattr(self.main_window, 'last_component_total_elapsed_time') and self.main_window.last_component_total_elapsed_time:
                time_str = self.main_window.last_component_total_elapsed_time
            else:
                time_str = "未知"
            if hasattr(self.main_window, 'last_component_total_combinations') and self.main_window.last_component_total_combinations:
                total_combinations = self.main_window.last_component_total_combinations
        
        info_label = QLabel(f"组合合计: {total_combinations} | 总耗时: {time_str}")
        info_label.setStyleSheet("font-size: 13px; color: #333; padding: 6px 10px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 3px;")
        self.result_layout.addWidget(info_label)
        # 输出top_three的单页表格
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QVBoxLayout, QDialog, QScrollArea
        from PyQt5.QtCore import Qt
        table = QTableWidget(len(top_three), 6, self.result_area)  # 修改为6列：输出值、输出参数、选股公式、选股参数、操作1、操作2
        table.setHorizontalHeaderLabels([
            "组合分析排序输出值", "输出参数", "选股公式", "选股参数", "", ""
        ])
        
        def show_analysis_detail(analysis_data, idx=None):
            if idx is None:
                idx = 0
            
            # 使用主窗口级别的窗口管理，避免tab切换时丢失引用
            if not hasattr(self.main_window, 'component_analysis_detail_window'):
                self.main_window.component_analysis_detail_window = None
            
            # 如果已有窗口，检查窗口是否仍然有效
            if self.main_window.component_analysis_detail_window is not None:
                try:
                    window = self.main_window.component_analysis_detail_window
                    # 检查窗口是否仍然存在（没有被销毁）
                    if hasattr(window, 'isVisible') and window.isVisible():
                        # 如果窗口最小化，则恢复显示
                        if window.isMinimized():
                            window.showNormal()
                        # 确保窗口在最前面
                        window.raise_()
                        window.activateWindow()
                        return
                    else:
                        # 窗口不可见，清理引用
                        self.main_window.component_analysis_detail_window = None
                except Exception:
                    # 窗口对象已失效，清理引用
                    self.main_window.component_analysis_detail_window = None
            
            # 创建新窗口
            window = AnalysisDetailWindow(analysis_data, self.create_component_result_table, idx)
            window.show()
            self.main_window.component_analysis_detail_window = window
            
            # 连接窗口关闭事件，清理引用
            def on_window_destroyed():
                if hasattr(self.main_window, 'component_analysis_detail_window'):
                    self.main_window.component_analysis_detail_window = None
            
            window.destroyed.connect(on_window_destroyed)
        
        def restore_formula_params(analysis_data):
            """恢复选股参数到选股控件"""
            try:
                # 获取当前组合的公式和参数
                formula = analysis_data.get('formula', '')
                width = analysis_data.get('width', '')
                op_days = analysis_data.get('op_days', '')
                increment_rate = analysis_data.get('increment_rate', '')
                after_gt_end_ratio = analysis_data.get('after_gt_end_ratio', '')
                after_gt_start_ratio = analysis_data.get('after_gt_start_ratio', '')
                stop_loss_inc_rate = analysis_data.get('stop_loss_inc_rate', '')
                stop_loss_after_gt_end_ratio = analysis_data.get('stop_loss_after_gt_end_ratio', '')
                stop_loss_after_gt_start_ratio = analysis_data.get('stop_loss_after_gt_start_ratio', '')
                sort_mode = analysis_data.get('sort_mode', '')
                select_count = analysis_data.get('select_count', 10)  # 获取选股数量
                
                print(f"开始恢复公式: {formula}")
                print(f"选股数量: {select_count}")
                
                # 创建临时的公式选股控件
                from function.stock_functions import get_abbr_map, get_abbr_logic_map, get_abbr_round_map, FormulaSelectWidget
                abbr_map = get_abbr_map()
                logic_map = get_abbr_logic_map()
                round_map = get_abbr_round_map()
                
                temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
                
                # 打印所有可用的变量控件
                print(f"可用的变量控件: {list(temp_formula_widget.var_widgets.keys())}")
                
                # 特别检查continuous_end_value控件的结构
                if 'continuous_end_value' in temp_formula_widget.var_widgets:
                    continuous_widgets = temp_formula_widget.var_widgets['continuous_end_value']
                    print(f"continuous_end_value控件结构: {list(continuous_widgets.keys())}")
                    for key, widget in continuous_widgets.items():
                        print(f"  {key}: {type(widget).__name__}")
                else:
                    print("continuous_end_value控件不存在")
                
                # 检查其他几个变量控件的结构作为对比
                for var_name in ['end_value', 'start_value', 'high_value', 'low_value']:
                    if var_name in temp_formula_widget.var_widgets:
                        widgets = temp_formula_widget.var_widgets[var_name]
                        print(f"{var_name}控件结构: {list(widgets.keys())}")
                    else:
                        print(f"{var_name}控件不存在")
                
                # 获取get_abbr_round_only_map中的变量名列表，用于排除重置
                from function.stock_functions import get_abbr_round_only_map
                round_only_vars = set()
                for (zh, en), en_val in get_abbr_round_only_map().items():
                    round_only_vars.add(en_val)
                
                # 重置所有控件状态（但不包括get_abbr_round_only_map的勾选状态）
                for var_name, widgets in temp_formula_widget.var_widgets.items():
                    print(f"重置变量控件: {var_name}")
                    
                    # 取消勾选所有复选框（但不包括round_checkbox，即get_abbr_round_only_map）
                    if 'checkbox' in widgets:
                        widgets['checkbox'].setChecked(False)
                    
                    # 对于get_abbr_round_only_map中的变量，不清空round_checkbox，保持勾选状态
                    if var_name in round_only_vars:
                        print(f"  跳过重置get_abbr_round_only_map变量: {var_name}")
                        continue
                    
                    # 清空round_checkbox（非get_abbr_round_only_map变量）
                    if 'round_checkbox' in widgets:
                        widgets['round_checkbox'].setChecked(False)
                        print(f"  重置round_checkbox: {var_name}")
                    
                    # 清空输入框
                    if 'lower' in widgets:
                        widgets['lower'].setText('')
                    if 'upper' in widgets:
                        widgets['upper'].setText('')
                    if 'lower_input' in widgets:
                        widgets['lower_input'].setText('')
                    if 'upper_input' in widgets:
                        widgets['upper_input'].setText('')
                    
                    # 清空其他输入框
                    if 'step' in widgets:
                        widgets['step'].setText('')
                    if 'n_input' in widgets:
                        widgets['n_input'].setText('')
                    
                    print(f"  已重置控件: {var_name}")
                
                # 重置比较控件状态
                print("重置比较控件状态")
                for comp in temp_formula_widget.comparison_widgets:
                    print(f"重置比较控件")
                    # 取消勾选复选框
                    if 'checkbox' in comp:
                        comp['checkbox'].setChecked(False)
                    # 清空输入框
                    if 'lower' in comp:
                        comp['lower'].setText('')
                    if 'upper' in comp:
                        comp['upper'].setText('')
                    if 'step' in comp:
                        comp['step'].setText('')
                    # 重置下拉框到默认值
                    if 'var1' in comp and comp['var1'].count() > 0:
                        comp['var1'].setCurrentIndex(0)
                    if 'var2' in comp and comp['var2'].count() > 0:
                        comp['var2'].setCurrentIndex(0)
                    if 'direction' in comp and comp['direction'].count() > 0:
                        comp['direction'].setCurrentIndex(0)
                    # 取消勾选逻辑复选框
                    if 'logic_check' in comp:
                        comp['logic_check'].setChecked(False)
                    print(f"  已重置比较控件")
                
                # 重置forward_param_state中的向前参数控件状态
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    print(f"重置forward_param_state: {self.main_window.forward_param_state}")
                    for var_name, var_state in self.main_window.forward_param_state.items():
                        if isinstance(var_state, dict):
                            # 重置enable复选框状态
                            var_state['enable'] = False
                            # 重置round圆框状态
                            var_state['round'] = False
                            # 清空上下限值
                            var_state['lower'] = ''
                            var_state['upper'] = ''
                            print(f"重置向前参数: {var_name}")
                        elif isinstance(var_state, bool):
                            # 如果只是布尔值，重置为False
                            self.main_window.forward_param_state[var_name] = False
                            print(f"重置向前参数布尔值: {var_name} = False")
                
                # 恢复forward_param_state中的向前参数控件状态
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    print(f"恢复forward_param_state: {self.main_window.forward_param_state}")
                    for var_name, var_state in self.main_window.forward_param_state.items():
                        if var_name in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var_name]
                            if isinstance(var_state, dict):
                                # 恢复enable复选框状态
                                if 'enable' in var_state and 'checkbox' in widgets:
                                    widgets['checkbox'].setChecked(var_state['enable'])
                                    print(f"恢复向前参数复选框: {var_name} = {var_state['enable']}")
                                # 恢复round圆框状态
                                if 'round' in var_state and 'round_checkbox' in widgets:
                                    widgets['round_checkbox'].setChecked(var_state['round'])
                                    print(f"恢复向前参数圆框: {var_name} = {var_state['round']}")
                                # 恢复上下限值
                                if 'lower' in var_state and 'lower' in widgets:
                                    widgets['lower'].setText(str(var_state['lower']))
                                    print(f"恢复向前参数下限: {var_name} = {var_state['lower']}")
                                if 'upper' in var_state and 'upper' in widgets:
                                    widgets['upper'].setText(str(var_state['upper']))
                                    print(f"恢复向前参数上限: {var_name} = {var_state['upper']}")
                            elif isinstance(var_state, bool) and 'checkbox' in widgets:
                                # 如果只是布尔值，直接设置复选框
                                widgets['checkbox'].setChecked(var_state)
                                print(f"恢复向前参数复选框: {var_name} = {var_state}")
                
                # 解析公式并设置控件状态
                
                # 先找出所有比较控件的变量，避免被当作普通上下限处理
                comparison_vars = set()
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
                    var1, lower, var2 = m.group(1), m.group(2), m.group(3)
                    comparison_vars.add(var1)
                    comparison_vars.add(var2)
                    print(f"找到比较控件: {var1} >= {lower} * {var2}")
                
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
                    var1, upper, var2 = m.group(1), m.group(2), m.group(3)
                    comparison_vars.add(var1)
                    comparison_vars.add(var2)
                    print(f"找到比较控件: {var1} <= {upper} * {var2}")
                
                # 记录已处理的变量，避免重复处理
                processed_vars = set()
                
                # 获取forward_param_state中的控件列表
                forward_widgets = {}
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    forward_widgets = self.main_window.forward_param_state
                    print(f"forward_param_state中的控件: {list(forward_widgets.keys())}")
                
                # 1. 匹配 xxx >= a（排除比较控件的变量）
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)', formula):
                    var, lower = m.group(1), m.group(2)
                    # 检查是否是比较控件的变量
                    if var not in comparison_vars:
                        print(f"找到下限条件: {var} >= {lower}")
                        # 先检查是否在普通控件列表中
                        if var in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var]
                            # 直接设置控件状态，但需要检查键是否存在
                            if 'checkbox' in widgets:
                                widgets['checkbox'].setChecked(True)
                                print(f"勾选变量控件: {var}")
                            if 'lower' in widgets:
                                widgets['lower'].setText(str(lower))
                                print(f"设置下限值: {var} = {lower}")
                                # 验证设置是否成功
                                actual_value = widgets['lower'].text()
                                print(f"验证下限值设置: {var} 实际值 = '{actual_value}'")
                            processed_vars.add(var)  # 标记为已处理
                        # 再检查是否在forward_param_state中
                        elif var in forward_widgets:
                            print(f"找到forward_param_state中的下限条件: {var} >= {lower}")
                            var_state = forward_widgets[var]
                            if isinstance(var_state, dict):
                                # 对于条件变量，enable直接设为true
                                print(f"设置forward_param_state下限复选框为true: {var}")
                                # 实际设置需要在主窗口的forward_param_state中更新
                                if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                    if isinstance(self.main_window.forward_param_state[var], dict):
                                        self.main_window.forward_param_state[var]['enable'] = True
                                        self.main_window.forward_param_state[var]['lower'] = lower
                                        print(f"已更新forward_param_state下限: {var} enable=True, lower={lower}")
                            elif isinstance(var_state, bool):
                                print(f"forward_param_state布尔值下限变量: {var} = {var_state}")
                            processed_vars.add(var)  # 标记为已处理
                        else:
                            print(f"变量 {var} 不在控件列表中")
                    else:
                        print(f"跳过比较控件变量的下限条件: {var} >= {lower}")
                
                # 2. 匹配 xxx <= b（排除比较控件的变量）
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)', formula):
                    var, upper = m.group(1), m.group(2)
                    # 检查是否是比较控件的变量
                    if var not in comparison_vars:
                        print(f"找到上限条件: {var} <= {upper}")
                        # 先检查是否在普通控件列表中
                        if var in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var]
                            # 直接设置控件状态，但需要检查键是否存在
                            if 'checkbox' in widgets:
                                widgets['checkbox'].setChecked(True)
                                print(f"勾选变量控件: {var}")
                            if 'upper' in widgets:
                                widgets['upper'].setText(str(upper))
                                print(f"设置上限值: {var} = {upper}")
                                # 验证设置是否成功
                                actual_value = widgets['upper'].text()
                                print(f"验证上限值设置: {var} 实际值 = '{actual_value}'")
                            processed_vars.add(var)  # 标记为已处理
                        # 再检查是否在forward_param_state中
                        elif var in forward_widgets:
                            print(f"找到forward_param_state中的上限条件: {var} <= {upper}")
                            var_state = forward_widgets[var]
                            if isinstance(var_state, dict):
                                # 对于条件变量，enable直接设为true
                                print(f"设置forward_param_state上限复选框为true: {var}")
                                # 实际设置需要在主窗口的forward_param_state中更新
                                if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                    if isinstance(self.main_window.forward_param_state[var], dict):
                                        self.main_window.forward_param_state[var]['enable'] = True
                                        self.main_window.forward_param_state[var]['upper'] = upper
                                        print(f"已更新forward_param_state上限: {var} enable=True, upper={upper}")
                            elif isinstance(var_state, bool):
                                print(f"forward_param_state布尔值上限变量: {var} = {var_state}")
                            processed_vars.add(var)  # 标记为已处理
                        else:
                            print(f"变量 {var} 不在控件列表中")
                    else:
                        print(f"跳过比较控件变量的上限条件: {var} <= {upper}")
                
                # 3. 匹配逻辑变量（if ... and VAR ...）
                if_match = re.search(r'if\s*(.*?):', formula)
                if if_match:
                    condition_text = if_match.group(1)
                    print(f"if条件文本: {condition_text}")
                    logic_vars = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', condition_text)
                    print(f"从if条件中提取的变量: {logic_vars}")
                    
                    for var in logic_vars:
                        print(f"处理if条件中的变量: {var}")
                        
                        # 先检查是否是比较控件变量
                        if var in comparison_vars:
                            print(f"跳过比较控件变量作为逻辑变量: {var}")
                            continue
                        
                        # 再检查是否是关键字
                        if var in {'if', 'else', 'result', 'and', 'or', 'not'}:
                            print(f"跳过关键字: {var}")
                            continue
                        
                        # 检查是否已经通过上下限处理过
                        if var in processed_vars:
                            print(f"跳过已处理的变量控件: {var}")
                            continue
                        
                        # 最后检查是否是有效的控件变量
                        if var in temp_formula_widget.var_widgets:
                            print(f"找到逻辑变量: {var}")
                            widgets = temp_formula_widget.var_widgets[var]
                            # 直接设置控件状态，但需要检查键是否存在
                            if 'checkbox' in widgets:
                                widgets['checkbox'].setChecked(True)
                                print(f"勾选逻辑变量控件: {var}")
                        # 检查是否在forward_param_state中
                        elif var in forward_widgets:
                            print(f"找到forward_param_state中的逻辑变量: {var}")
                            var_state = forward_widgets[var]
                            if isinstance(var_state, dict):
                                # 对于条件变量，enable直接设为true
                                print(f"设置forward_param_state逻辑变量复选框为true: {var}")
                                # 实际设置需要在主窗口的forward_param_state中更新
                                if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                    if isinstance(self.main_window.forward_param_state[var], dict):
                                        self.main_window.forward_param_state[var]['enable'] = True
                                        print(f"已更新forward_param_state逻辑变量: {var} enable=True")
                            elif isinstance(var_state, bool):
                                print(f"forward_param_state布尔值逻辑变量: {var} = {var_state}")
                        else:
                            print(f"跳过非控件变量: {var}")
                
                # 4. 匹配 result = xxx + yyy
                m = re.search(r'result\s*=\s*([a-zA-Z0-9_]+(?:\s*\+\s*[a-zA-Z0-9_]+)*)', formula)
                if m:
                    result_text = m.group(1)
                    print(f"result表达式: {result_text}")
                    result_vars = re.findall(r'[a-zA-Z0-9_]+', result_text)
                    print(f"从result中提取的变量: {result_vars}")
                    
                    for var in result_vars:
                        print(f"处理result变量: {var}")
                        # 先检查是否在普通控件列表中
                        if var in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var]
                            # 直接设置圆框控件状态，但需要检查键是否存在
                            if 'round_checkbox' in widgets:
                                widgets['round_checkbox'].setChecked(True)
                                print(f"勾选圆框控件: {var}")
                        # 再检查是否在forward_param_state中
                        elif var in forward_widgets:
                            print(f"找到forward_param_state中的变量: {var}")
                            var_state = forward_widgets[var]
                            if isinstance(var_state, dict):
                                # 对于result变量，round直接设为true
                                print(f"设置forward_param_state圆框为true: {var}")
                                # 这里应该直接设置round为true，而不是读取现有值
                                # 实际设置需要在主窗口的forward_param_state中更新
                                if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                    if isinstance(self.main_window.forward_param_state[var], dict):
                                        self.main_window.forward_param_state[var]['round'] = True
                                        print(f"已更新forward_param_state圆框: {var} = True")
                            elif isinstance(var_state, bool):
                                print(f"forward_param_state布尔值变量: {var} = {var_state}")
                        else:
                            print(f"result变量 {var} 不在控件列表中")
                
                # 5. 处理比较控件
                from function.stock_functions import get_abbr_map
                abbr_map = get_abbr_map()  # {中文: 英文}
                en2zh = {en: zh for zh, en in abbr_map.items()}
                comparison_configs = []
                # >=
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
                    var1, lower, var2 = m.group(1), m.group(2), m.group(3)
                    zh_var1 = en2zh.get(var1, var1)
                    zh_var2 = en2zh.get(var2, var2)
                    existing = next((c for c in comparison_configs if c['var1'] == zh_var1 and c['var2'] == zh_var2), None)
                    if existing:
                        existing['lower'] = lower
                    else:
                        comparison_configs.append({'var1': zh_var1, 'lower': lower, 'upper': '', 'var2': zh_var2})
                # <=
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)\s*\*\s*([a-zA-Z0-9_]+)', formula):
                    var1, upper, var2 = m.group(1), m.group(2), m.group(3)
                    zh_var1 = en2zh.get(var1, var1)
                    zh_var2 = en2zh.get(var2, var2)
                    existing = next((c for c in comparison_configs if c['var1'] == zh_var1 and c['var2'] == zh_var2), None)
                    if existing:
                        existing['upper'] = upper
                    else:
                        comparison_configs.append({'var1': zh_var1, 'lower': '', 'upper': upper, 'var2': zh_var2})
                
                # 将比较控件配置应用到实际的比较控件上
                if comparison_configs:
                    print(f"开始应用比较控件配置: {comparison_configs}")
                    
                    # 遍历所有比较控件配置
                    for i, config in enumerate(comparison_configs):
                        var1 = config['var1']
                        var2 = config['var2']
                        lower = config['lower']
                        upper = config['upper']
                        
                        print(f"处理比较控件配置 {i+1}: {var1} vs {var2}, 下限: {lower}, 上限: {upper}")
                        
                        # 检查是否有足够的比较控件
                        if i < len(temp_formula_widget.comparison_widgets):
                            comp = temp_formula_widget.comparison_widgets[i]
                            print(f"找到比较控件 {i+1}")
                            
                            # 勾选复选框
                            if 'checkbox' in comp:
                                comp['checkbox'].setChecked(True)
                                print(f"  勾选比较控件复选框")
                            
                            # 设置下限
                            if lower and 'lower' in comp:
                                comp['lower'].setText(str(lower))
                                print(f"  设置下限: {lower}")
                            
                            # 设置上限
                            if upper and 'upper' in comp:
                                comp['upper'].setText(str(upper))
                                print(f"  设置上限: {upper}")
                            
                            # 设置var1下拉框
                            if 'var1' in comp:
                                var1_combo = comp['var1']
                                var1_zh = None
                                for zh, en in abbr_map.items():
                                    if en == var1:
                                        var1_zh = zh
                                        break
                                if var1_zh:
                                    var1_combo.setCurrentText(var1_zh)
                                    print(f"  设置var1: {var1_zh}")
                                else:
                                    print(f"  未找到var1的中文名称: {var1}")
                            # 设置var2下拉框
                            if 'var2' in comp:
                                var2_combo = comp['var2']
                                var2_zh = None
                                for zh, en in abbr_map.items():
                                    if en == var2:
                                        var2_zh = zh
                                        break
                                if var2_zh:
                                    var2_combo.setCurrentText(var2_zh)
                                    print(f"  设置var2: {var2_zh}")
                                else:
                                    print(f"  未找到var2的中文名称: {var2}")
                        else:
                            print(f"比较控件 {i+1} 不存在，跳过")
                    
                    # 保存比较控件配置到状态中
                    comparison_state = {
                        'comparison_widgets': comparison_configs
                    }
                    print(f"保存比较控件配置到状态: {comparison_state}")
                
                # 获取当前状态
                current_state = temp_formula_widget.get_state()
                #print(f"获取到的状态: {current_state}")
                
                # 检查状态中是否包含变量控件的上下限
                #for var_name, var_state in current_state.items():
                    #if isinstance(var_state, dict) and 'lower' in var_state:
                        #print(f"状态中的下限: {var_name} = {var_state['lower']}")
                    #if isinstance(var_state, dict) and 'upper' in var_state:
                        #print(f"状态中的上限: {var_name} = {var_state['upper']}")
                
                # 如果有比较控件配置，添加到状态中
                if comparison_configs:
                    current_state['comparison_widgets'] = comparison_configs
                    print(f"添加比较控件配置到状态中")
                
                # 更新主窗口的last_formula_select_state
                self.main_window.last_formula_select_state = current_state
                print(f"已保存状态到主窗口: {len(current_state)} 个变量")
                
                # 验证状态是否正确保存
                saved_state = getattr(self.main_window, 'last_formula_select_state', {})
                
                # 更新主窗口的排序方式
                self.main_window.last_sort_mode = sort_mode
                
                # 更新主窗口的参数
                if width:
                    try:
                        self.main_window.width_spin.setValue(int(float(width)))
                        print(f"设置日期宽度: {width}")
                    except:
                        pass
                if op_days:
                    try:
                        self.main_window.op_days_edit.setText(str(op_days))
                        print(f"设置操作天数: {op_days}")
                    except:
                        pass
                if increment_rate:
                    try:
                        self.main_window.inc_rate_edit.setText(str(increment_rate))
                        print(f"设置止盈递增率: {increment_rate}")
                    except:
                        pass
                if after_gt_end_ratio:
                    try:
                        self.main_window.after_gt_end_edit.setText(str(after_gt_end_ratio))
                        print(f"设置止盈后值大于结束值比例: {after_gt_end_ratio}")
                    except:
                        pass
                if after_gt_start_ratio:
                    try:
                        self.main_window.after_gt_prev_edit.setText(str(after_gt_start_ratio))
                        print(f"设置止盈后值大于前值比例: {after_gt_start_ratio}")
                    except:
                        pass
                if stop_loss_inc_rate:
                    try:
                        self.main_window.stop_loss_inc_rate_edit.setText(str(stop_loss_inc_rate))
                        print(f"设置止损递增率: {stop_loss_inc_rate}")
                    except:
                        pass
                if stop_loss_after_gt_end_ratio:
                    try:
                        self.main_window.stop_loss_after_gt_end_edit.setText(str(stop_loss_after_gt_end_ratio))
                        print(f"设置止损后值大于结束值比例: {stop_loss_after_gt_end_ratio}")
                    except:
                        pass
                if stop_loss_after_gt_start_ratio:
                    try:
                        self.main_window.stop_loss_after_gt_start_edit.setText(str(stop_loss_after_gt_start_ratio))
                        print(f"设置止损后值大于前值比例: {stop_loss_after_gt_start_ratio}")
                    except:
                        pass
                
                # 恢复选股数量
                if select_count:
                    try:
                        self.main_window.last_select_count = int(select_count)
                        print(f"设置选股数量: {select_count}")
                    except:
                        pass
                
                # 清理临时控件
                temp_formula_widget.deleteLater()
                
                QMessageBox.information(self, "恢复成功", f"已成功恢复选股参数！\n公式: {formula}\n排序方式: {sort_mode}\n 选股数量: {select_count}\n日期宽度: {width}\n操作天数: {op_days}\n止盈递增率: {increment_rate}\n止盈后值大于结束值比例: {after_gt_end_ratio}\n止盈后值大于前值比例: {after_gt_start_ratio}\n止损递增率: {stop_loss_inc_rate}\n止损后值大于结束值比例: {stop_loss_after_gt_end_ratio}\n止损后值大于前值比例: {stop_loss_after_gt_start_ratio}")
                
            except Exception as e:
                QMessageBox.critical(self, "恢复失败", f"恢复选股参数失败：{e}")
                print(f"恢复失败详细错误: {e}")
                import traceback
                traceback.print_exc()
        
        for row, item in enumerate(top_three):
            analysis = item['analysis']
            table.setItem(row, 0, QTableWidgetItem(f"{item['adjusted_value']:.2f}"))
            # 输出参数：显示勾选的get_abbr_round_only_map控件名称
            selected_vars_with_values = analysis.get('selected_vars_with_values', [])
            if selected_vars_with_values:
                from function.stock_functions import get_abbr_round_only_map
                abbr_map = get_abbr_round_only_map()
                # 获取n_values用于替换第N位
                n_values = analysis.get('n_values', {})
                print(f"n_values: {n_values}")
                # 直接使用selected_vars_with_values中的变量名和值
                output_params = []
                output_params_sum = 0
                for var_name, value in selected_vars_with_values:
                    for (zh, en) in abbr_map.keys():
                        if en == var_name:
                            # 处理第N位变量
                            if "第N位" in zh:
                                n_value = n_values.get(var_name, "N")
                                zh_display = zh.replace("第N位", f"第{n_value}位")
                            else:
                                zh_display = zh
                            
                            # 直接使用预计算的值
                            output_params_sum += value
                            # 显示参数名称和数值
                            output_params.append(f"{zh_display}: {value:.2f}")
                            break
                # 输出参数文本
                output_params_text = "\n".join(output_params)
                # 在最后一行加上总和
                if output_params:
                    output_params_text += f"\n总和: {output_params_sum:.2f}"
                else:
                    output_params_text = "无勾选参数"
                output_params_item = QTableWidgetItem(output_params_text)
                output_params_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                output_params_item.setToolTip(output_params_text)
                table.setItem(row, 1, output_params_item)
            else:
                output_params_text = "无勾选参数"
            
            output_params_item = QTableWidgetItem(output_params_text)
            output_params_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            output_params_item.setToolTip(output_params_text)
            table.setItem(row, 1, output_params_item)
            
            # 第3列：选股公式
            formula = analysis.get('formula', '')
            formula_item = QTableWidgetItem(formula)
            formula_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            formula_item.setToolTip(formula)
            table.setItem(row, 2, formula_item)
            
            # 第4列：选股参数（按指定顺序分行输出）
            params_text = []
            params_text.append(f"选股数量: {analysis.get('select_count', 10)}")
            params_text.append(f"排序方式: {analysis.get('sort_mode', '')}")
            params_text.append(f"日期宽度: {analysis.get('width', '')}")
            params_text.append(f"操作天数: {analysis.get('op_days', '')}")
            params_text.append(f"止盈递增率: {analysis.get('increment_rate', '')}")
            params_text.append(f"止盈后值大于结束值比例: {analysis.get('after_gt_end_ratio', '')}")
            params_text.append(f"止盈后值大于前值比例: {analysis.get('after_gt_start_ratio', '')}")
            params_text.append(f"止损递增率: {analysis.get('stop_loss_inc_rate', '')}")
            params_text.append(f"止损后值大于结束值比例: {analysis.get('stop_loss_after_gt_end_ratio', '')}")
            params_text.append(f"止损后值大于前值比例: {analysis.get('stop_loss_after_gt_start_ratio', '')}")
            
            params_item = QTableWidgetItem("\n".join(params_text))
            params_item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            params_item.setToolTip("\n".join(params_text))
            table.setItem(row, 3, params_item)
            
            # 添加查看分析结果按钮（第5列，列名为空）
            view_btn = QPushButton("查看详情")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            view_btn.clicked.connect(lambda checked, data=analysis, idx=row: show_analysis_detail(data, idx))
            table.setCellWidget(row, 4, view_btn)
            
            # 添加恢复参数按钮（第6列）
            restore_btn = QPushButton("恢复参数")
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            restore_btn.clicked.connect(lambda checked, data=analysis: restore_formula_params(data))
            table.setCellWidget(row, 5, restore_btn)
            
        table.resizeColumnsToContents()
        # 设置列宽
        table.setColumnWidth(0, 150)  # 输出值列宽度
        table.setColumnWidth(1, 200)  # 输出参数列宽度
        table.setColumnWidth(2, 300)  # 选股公式列宽度
        table.setColumnWidth(3, 250)  # 选股参数列宽度
        table.setColumnWidth(4, 100)  # 查看详情按钮列宽度
        table.setColumnWidth(5, 100)  # 恢复参数按钮列宽度
        # 自动调整行高以适配多行公式
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)
        self.result_layout.addWidget(table)
        print(f"组合分析完成！输出前三名排序结果。")
        # 新增：保存最优top1到主窗口缓存
        if top_three:
            self.main_window.last_component_analysis_top1 = top_three[0]

    def create_component_result_table(self, analysis):
        """为单个组合分析结果创建类似主界面的表格"""
        import math
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QLabel
        from ui.common_widgets import CopyableTableWidget
        
        result = analysis.get('analysis_stats')
        if not result:
            error_label = QLabel("无分析结果数据")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            return error_label

        # 检查result的结构
        if not isinstance(result, dict):
            error_label = QLabel(f"分析结果数据格式错误: {type(result)}")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            return error_label

        items = result.get('items', [])
        summary = result.get('summary', {})
        
        if not items and not summary:
            error_label = QLabel("分析结果数据为空")
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            return error_label

        formula = analysis.get('formula', '')
        row_count = len(items)
        
        table = CopyableTableWidget(row_count + 2, 15, self.result_area)
        table.setHorizontalHeaderLabels([
            "结束日期", "操作天数", "持有涨跌幅", 
            "调天日均涨跌幅", "调天从下往上非空均值", "调天从下往上含空均值", "调天含空值均值", "调天最大值", "调天最小值",
            "调幅日均涨跌幅", "调幅从下往上非空均值", "调幅从下往上含空均值", "调幅含空值均值", "调幅最大值", "调幅最小值", "调幅含空值均值"
        ])
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 设置第一行的均值数据
        if summary:
            table.setItem(0, 1, QTableWidgetItem(str(summary.get('mean_hold_days', ''))))
            table.setItem(0, 2, QTableWidgetItem(f"{summary.get('mean_ops_change', '')}%" if summary.get('mean_ops_change', '') != '' else ''))
            table.setItem(0, 3, QTableWidgetItem(f"{summary.get('mean_daily_change', '')}%" if summary.get('mean_daily_change', '') != '' else ''))
            table.setItem(0, 4, QTableWidgetItem(f"{summary.get('mean_non_nan', '')}%" if summary.get('mean_non_nan', '') != '' else ''))
            table.setItem(0, 5, QTableWidgetItem(f"{summary.get('mean_with_nan', '')}%" if summary.get('mean_with_nan', '') != '' else ''))
            table.setItem(0, 6, QTableWidgetItem(f"{summary.get('mean_daily_with_nan', '')}%" if summary.get('mean_daily_with_nan', '') != '' else ''))
            table.setItem(0, 7, QTableWidgetItem(f"{summary.get('max_change', '')}%" if summary.get('max_change', '') != '' else ''))
            table.setItem(0, 8, QTableWidgetItem(f"{summary.get('min_change', '')}%" if summary.get('min_change', '') != '' else ''))
            table.setItem(0, 9, QTableWidgetItem(f"{summary.get('mean_adjust_ops_incre_rate', '')}%" if summary.get('mean_adjust_ops_incre_rate', '') != '' else ''))
            table.setItem(0, 10, QTableWidgetItem(f"{summary.get('mean_adjust_non_nan', '')}%" if summary.get('mean_adjust_non_nan', '') != '' else ''))
            table.setItem(0, 11, QTableWidgetItem(f"{summary.get('mean_adjust_with_nan', '')}%" if summary.get('mean_adjust_with_nan', '') != '' else ''))
            table.setItem(0, 12, QTableWidgetItem(f"{summary.get('mean_adjust_daily_with_nan', '')}%" if summary.get('mean_adjust_daily_with_nan', '') != '' else ''))
            table.setItem(0, 13, QTableWidgetItem(f"{summary.get('max_adjust_ops_incre_rate', '')}%" if summary.get('max_adjust_ops_incre_rate', '') != '' else ''))
            table.setItem(0, 14, QTableWidgetItem(f"{summary.get('min_adjust_ops_incre_rate', '')}%" if summary.get('min_adjust_ops_incre_rate', '') != '' else ''))

        # 设置每行的数据
        for row_idx, item in enumerate(items):
            table.setItem(row_idx + 2, 0, QTableWidgetItem(str(item.get('date', ''))))
            table.setItem(row_idx + 2, 1, QTableWidgetItem(str(item.get('hold_days', ''))))
            table.setItem(row_idx + 2, 2, QTableWidgetItem(f"{item.get('ops_change', '')}%" if item.get('ops_change', '') != '' else ''))
            table.setItem(row_idx + 2, 3, QTableWidgetItem(f"{item.get('daily_change', '')}%" if item.get('daily_change', '') != '' else ''))
            non_nan_mean = item.get('non_nan_mean', '')
            table.setItem(row_idx + 2, 4, QTableWidgetItem(f"{round(non_nan_mean, 2)}%" if non_nan_mean != '' and not (isinstance(non_nan_mean, float) and math.isnan(non_nan_mean)) else ''))
            with_nan_mean = item.get('with_nan_mean', '')
            table.setItem(row_idx + 2, 5, QTableWidgetItem(f"{round(with_nan_mean, 2)}%" if with_nan_mean != '' and not (isinstance(with_nan_mean, float) and math.isnan(with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 6, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 7, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 8, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 9, QTableWidgetItem(f"{item.get('adjust_daily_change', '')}%" if item.get('adjust_daily_change', '') != '' else ''))
            adjust_non_nan_mean = item.get('adjust_non_nan_mean', '')
            table.setItem(row_idx + 2, 10, QTableWidgetItem(f"{round(adjust_non_nan_mean, 2)}%" if adjust_non_nan_mean != '' and not (isinstance(adjust_non_nan_mean, float) and math.isnan(adjust_non_nan_mean)) else ''))
            adjust_with_nan_mean = item.get('adjust_with_nan_mean', '')
            table.setItem(row_idx + 2, 11, QTableWidgetItem(f"{round(adjust_with_nan_mean, 2)}%" if adjust_with_nan_mean != '' and not (isinstance(adjust_with_nan_mean, float) and math.isnan(adjust_with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 12, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 13, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 14, QTableWidgetItem(""))

        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

        # 在表格最后一行插入公式
        if formula:
            row = table.rowCount()
            item = QTableWidgetItem(f"选股公式:\n{formula}")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            item.setToolTip(item.text())
            table.setItem(row, 0, item)
            table.setSpan(row, 0, 1, table.columnCount())
            table.setWordWrap(True)
            table.resizeRowToContents(row)

        # 不再插入参数输出行
        # row = table.rowCount()
        # params = [
        #     ("日期宽度", str(analysis.get('width', ''))),
        #     ("操作天数", str(analysis.get('op_days', ''))),
        #     ("止盈递增率", f"{analysis.get('increment_rate', '')}%"),
        #     ("排序方式", analysis.get('sort_mode', ''))
        # ]
        # for i, (label, value) in enumerate(params):
        #     table.insertRow(row + i)
        #     table.setItem(row + i, 0, QTableWidgetItem(label))
        #     table.setItem(row + i, 1, QTableWidgetItem(value))

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 150)
        for i in range(1, table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        return table
        
    def show_component_analysis_interface(self):
        """显示组合分析界面"""
        # 清理旧内容
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 显示公式选股界面
        all_results = getattr(self.main_window, 'all_row_results', None)
        table = show_formula_select_table(self.main_window, all_results, as_widget=True)
        if table:
            table.setMinimumSize(1200, 600)
            self.result_layout.addWidget(table)
        else:
            self.result_text.setText("没有可展示的组合分析结果。")
            self.result_layout.addWidget(self.result_text)
            
    def show_message(self, message):
        """显示消息"""
        # 临时隐藏当前显示的内容（包括表格），但不删除
        for i in range(self.result_layout.count()):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setVisible(False)
        
        # 确保文本区域可见并显示消息
        self.result_text.setVisible(True)
        self.result_text.setText(message)
        
        # 如果文本区域不在布局中，添加它
        if self.result_text.parent() is None:
            self.result_layout.addWidget(self.result_text)
        else:
            # 如果已经在布局中，确保它在最前面
            self.result_layout.removeWidget(self.result_text)
            self.result_layout.addWidget(self.result_text)
        
    def on_export_json(self):
        """导出最优方案为json文件"""
        top1 = getattr(self.main_window, 'last_component_analysis_top1', None)
        if not top1:
            QMessageBox.warning(self, "提示", "没有可导出的最优方案数据！")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出最优方案", "", "JSON Files (*.json);;Text Files (*.txt)")
        if not file_path:
            return
        if not (file_path.endswith('.json') or file_path.endswith('.txt')):
            file_path += '.json'
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(top1, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已成功导出最优方案到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出最优方案失败：{e}")

    def on_import_json(self):
        """导入最优方案json文件并恢复展示"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入最优方案", "", "JSON Files (*.json);;Text Files (*.txt)")
        if not file_path:
            return
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                top1 = json.load(f)
            all_analysis_results = [top1]
            self.show_analysis_results(all_analysis_results)
            QMessageBox.information(self, "导入成功", "已成功导入最优方案！")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入最优方案失败：{e}")

    def on_import_csv(self):
        """导入CSV并自动恢复控件参数"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入CSV文件", "", "CSV Files (*.csv)")
        if not file_path:
            return
        try:
            import csv
            headers = []
            data_rows = []
            param_map = {}
            
            # 添加文件读取的容错处理
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    for idx, row in enumerate(reader):
                        if idx == 0:
                            headers = row
                            # 立即检查头部格式
                            if len(headers) < 6:
                                QMessageBox.warning(self, "文件格式错误", 
                                    "导入失败，请检查文件是否是组合分析导出文件！")
                                return
                            continue
                        if row and row[0].startswith('#') and ':' in row[0]:
                            k, v = row[0][1:].split(':', 1)
                            param_map[k.strip()] = v.strip()
                        else:
                            data_rows.append(row)
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        reader = csv.reader(f)
                        for idx, row in enumerate(reader):
                            if idx == 0:
                                headers = row
                                if len(headers) < 6:
                                    QMessageBox.warning(self, "文件格式错误", 
                                        "导入失败，请检查文件是否是组合分析导出文件！")
                                    return
                                continue
                            if row and row[0].startswith('#') and ':' in row[0]:
                                k, v = row[0][1:].split(':', 1)
                                param_map[k.strip()] = v.strip()
                            else:
                                data_rows.append(row)
                except Exception as gbk_error:
                    QMessageBox.warning(self, "文件编码错误", 
                        f"无法读取CSV文件，请检查文件编码格式！\n错误信息：{gbk_error}")
                    return
            except Exception as read_error:
                QMessageBox.warning(self, "文件读取错误", 
                    f"无法读取CSV文件，请检查文件是否损坏！\n错误信息：{read_error}")
                return
            
            # 检查文件格式是否符合组合分析导出文件特征
            if not self._validate_import_file_format_csv(headers):
                QMessageBox.warning(self, "文件格式错误", 
                    "导入失败，请检查文件是否是组合分析导出文件！")
                return
            
            # 恢复控件
            self._restore_main_window_params(param_map)
            # 更新组合分析界面控件 - 传递param_map参数
            self._update_main_window_controls(param_map)
            # 展示表格
            self._show_imported_analysis_from_data(headers, data_rows)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入CSV失败：{e}")
            
    def _validate_import_file_format(self, df):
        """验证Excel文件格式是否符合组合分析导出文件特征"""
        try:
            # 检查必需的列是否存在
            required_columns = [
                "组合分析排序输出值", "公式", "日期宽度", "操作天数", "止盈递增率", "排序方式"
            ]
            
            # 获取DataFrame的列名
            columns = df.columns.tolist()
            
            # 检查是否包含所有必需的列
            missing_columns = []
            for col in required_columns:
                if col not in columns:
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"缺少必需的列: {missing_columns}")
                return False
            
            # 检查是否有数据行（排除参数行）
            data_rows = 0
            for i, row in df.iterrows():
                first_cell = str(row.iloc[0])
                if not first_cell.startswith('#') or ':' not in first_cell:
                    data_rows += 1
            
            if data_rows == 0:
                print("没有找到有效的数据行")
                return False
            
            # 检查第一行数据是否包含数值（组合分析排序输出值应该是数值）
            for i, row in df.iterrows():
                first_cell = str(row.iloc[0])
                if not first_cell.startswith('#') or ':' not in first_cell:
                    try:
                        float(first_cell)  # 尝试转换为数值
                        break
                    except ValueError:
                        print(f"第一列数据不是有效数值: {first_cell}")
                        return False
            
            print("文件格式验证通过")
            return True
            
        except Exception as e:
            print(f"文件格式验证失败: {e}")
            return False
    
    def _validate_import_file_format_csv(self, headers):
        """验证CSV文件格式是否符合组合分析导出文件特征"""
        try:
            # 检查必需的列是否存在
            required_columns = [
                "组合分析排序输出值", "公式", "日期宽度", "操作天数", "止盈递增率", "排序方式"
            ]
            
            # 检查是否包含所有必需的列
            missing_columns = []
            for col in required_columns:
                if col not in headers:
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"缺少必需的列: {missing_columns}")
                return False
            
            print("CSV文件格式验证通过")
            return True
            
        except Exception as e:
            print(f"CSV文件格式验证失败: {e}")
            return False
    
    def _restore_main_window_params(self, param_map):
        """根据参数字典自动恢复主界面控件内容（优先操作控件本身）"""
        for k, v in param_map.items():
            try:
                if k == 'last_formula_expr':
                    continue
                # 防止v为方法对象
                if callable(v):
                    print(f"警告：{k} 的值是方法对象，跳过")
                    continue
                    
                # 特殊处理：width 参数直接设置到 width_spin 控件
                if k == 'width' and hasattr(self.main_window, 'width_spin'):
                    try:
                        width_val = int(float(v))
                        self.main_window.width_spin.setValue(width_val)
                        print(f"恢复width参数: {width_val}")
                    except (ValueError, TypeError) as e:
                        print(f"width参数恢复失败: {e}")
                # 组合分析日期参数
                elif k == 'component_analysis_start_date':
                    setattr(self.main_window, 'last_component_analysis_start_date', v)
                    print(f"恢复日期参数: last_component_analysis_start_date = {v}")
                elif k == 'component_analysis_end_date':
                    setattr(self.main_window, 'last_component_analysis_end_date', v)
                    print(f"恢复日期参数: last_component_analysis_end_date = {v}")
                    print(f"调试：设置后立即检查值: {getattr(self.main_window, 'last_component_analysis_end_date', 'NOT_FOUND')}")
                # 特殊处理：after_gt_end_edit 和 after_gt_prev_edit
                elif k == 'after_gt_end_edit' and hasattr(self.main_window, 'after_gt_end_edit'):
                    try:
                        self.main_window.after_gt_end_edit.setText(str(v))
                        print(f"恢复特殊LineEdit: after_gt_end_edit = {v}")
                    except Exception as e:
                        print(f"恢复after_gt_end_edit失败: {e}")
                elif k == 'after_gt_prev_edit' and hasattr(self.main_window, 'after_gt_prev_edit'):
                    try:
                        self.main_window.after_gt_prev_edit.setText(str(v))
                        print(f"恢复特殊LineEdit: after_gt_prev_edit = {v}")
                    except Exception as e:
                        print(f"恢复after_gt_prev_edit失败: {e}")
                # LineEdit - 优先处理，避免被当作直接控件名
                elif hasattr(self.main_window, k + '_edit'):
                    try:
                        edit_name = k + '_edit'
                        self.main_window.__getattribute__(edit_name).setText(str(v))
                        print(f"恢复LineEdit: {edit_name} = {v}")
                    except Exception as e:
                        print(f"LineEdit {k + '_edit'} 恢复失败: {e}")
                # SpinBox
                elif hasattr(self.main_window, k + '_spin'):
                    try:
                        spin_name = k + '_spin'
                        spin_val = int(float(v))
                        self.main_window.__getattribute__(spin_name).setValue(spin_val)
                        print(f"恢复SpinBox: {spin_name} = {spin_val}")
                    except Exception as e:
                        print(f"SpinBox {k + '_spin'} 恢复失败: {e}")
                # ComboBox
                elif hasattr(self.main_window, k + '_combo'):
                    try:
                        combo = getattr(self.main_window, k + '_combo')
                        idx = combo.findText(str(v))
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                            print(f"恢复ComboBox: {k + '_combo'} = {v}")
                        else:
                            print(f"ComboBox {k + '_combo'} 未找到选项: {v}")
                    except Exception as e:
                        print(f"ComboBox {k + '_combo'} 恢复失败: {e}")
                # CheckBox
                elif hasattr(self.main_window, k + '_checkbox'):
                    try:
                        checkbox = getattr(self.main_window, k + '_checkbox')
                        is_checked = v in ['True', 'true', '1', True]
                        checkbox.setChecked(is_checked)
                        print(f"恢复CheckBox: {k + '_checkbox'} = {is_checked}")
                    except Exception as e:
                        print(f"CheckBox {k + '_checkbox'} 恢复失败: {e}")
                # 其他直接属性（如forward_param_state等）
                elif k in ['last_formula_select_state', 'forward_param_state']:
                    try:
                        import ast
                        parsed_value = ast.literal_eval(v)
                        setattr(self.main_window, k, parsed_value)
                    except Exception as e:
                        print(f"复杂属性 {k} 恢复失败: {e}")
                # 数值属性需要类型转换
                elif k in ['last_select_count', 'last_sort_mode']:
                    try:
                        if k == 'last_select_count':
                            # 确保是整数
                            int_val = int(float(v))
                            setattr(self.main_window, k, int_val)
                            print(f"恢复数值属性: {k} = {int_val}")
                        else:
                            setattr(self.main_window, k, v)
                            print(f"恢复属性: {k} = {v}")
                    except Exception as e:
                        print(f"数值属性 {k} 恢复失败: {e}")
                # 直接控件名（如 after_gt_end_edit）
                elif hasattr(self.main_window, k):
                    try:
                        attr_value = getattr(self.main_window, k)
                        if hasattr(attr_value, 'setText'):
                            attr_value.setText(str(v))
                            print(f"恢复直接控件: {k} = {v}")
                        elif hasattr(attr_value, 'setValue'):
                            attr_value.setValue(int(float(v)))
                            print(f"恢复直接控件: {k} = {v}")
                        elif hasattr(attr_value, 'setCurrentText'):
                            attr_value.setCurrentText(str(v))
                            print(f"恢复直接控件: {k} = {v}")
                        elif hasattr(attr_value, 'setChecked'):
                            is_checked = v in ['True', 'true', '1', True]
                            attr_value.setChecked(is_checked)
                            print(f"恢复直接控件: {k} = {v}")
                        else:
                            # 不是控件对象，是普通属性
                            setattr(self.main_window, k, v)
                            print(f"恢复直接属性: {k} = {v}")
                    except Exception as e:
                        print(f"直接控件/属性 {k} 恢复失败: {e}")
                else:
                    # 尝试设置为普通属性，但保护重要系统属性
                    protected_attrs = {
                        'cached_table_data', 'cached_component_analysis_results',
                        'component_analysis_formula_list', 'component_analysis_special_params_combinations',
                        'component_analysis_selected_round_only_vars', 'component_analysis_n_values',
                        'all_row_results', 'analysis_table_cache_data'
                    }
                    if k not in protected_attrs:
                        try:
                            setattr(self.main_window, k, v)
                            print(f"恢复普通属性: {k} = {v}")
                        except Exception as e:
                            print(f"普通属性 {k} 恢复失败: {e}")
                    else:
                        print(f"跳过保护属性: {k}")
            except Exception as e:
                print(f"恢复控件 {k} 失败: {e}")
                
        # 恢复逻辑已经完成，不需要再次更新控件
        print("参数恢复完成")

    def _update_main_window_controls(self, param_map=None):
        """更新主窗口控件显示（只更新组合分析界面特有的控件）"""
        try:
            # 组合分析日期参数 - 直接从导入的参数中获取，而不是从主窗口属性获取
            if param_map is not None:
                # 从导入的参数中直接获取
                start_date_val = param_map.get('component_analysis_start_date', '')
                if start_date_val and start_date_val != '2000-01-01':
                    try:
                        qdate = QDate.fromString(str(start_date_val), "yyyy-MM-dd")
                        if qdate.isValid():
                            self.start_date_picker.setDate(qdate)
                            print(f"更新组合分析开始日期: {start_date_val}")
                    except Exception as e:
                        print(f"更新组合分析开始日期失败: {e}")
                        
                end_date_val = param_map.get('component_analysis_end_date', '')
                if end_date_val and end_date_val != '2000-01-01':
                    try:
                        qdate = QDate.fromString(str(end_date_val), "yyyy-MM-dd")
                        if qdate.isValid():
                            self.end_date_picker.setDate(qdate)
                            print(f"更新组合分析结束日期: {end_date_val}")
                    except Exception as e:
                        print(f"更新组合分析结束日期失败: {e}")
                else:
                    print("没有组合分析结束日期")
                    
                # 恢复组合分析次数
                analysis_count_val = param_map.get('component_analysis_count', '')
                if analysis_count_val:
                    try:
                        count_val = int(float(analysis_count_val))
                        self.analysis_count_spin.setValue(count_val)
                        print(f"更新组合分析次数: {count_val}")
                    except Exception as e:
                        print(f"更新组合分析次数失败: {e}")
            else:
                # 兼容旧方式：从主窗口属性获取（用于其他场景）
                if hasattr(self.main_window, 'last_component_analysis_start_date'):
                    start_date_val = getattr(self.main_window, 'last_component_analysis_start_date', '')
                    if not callable(start_date_val) and start_date_val and start_date_val != '2000-01-01':
                        try:
                            qdate = QDate.fromString(str(start_date_val), "yyyy-MM-dd")
                            if qdate.isValid():
                                self.start_date_picker.setDate(qdate)
                                print(f"更新组合分析开始日期: {start_date_val}")
                        except Exception as e:
                            print(f"更新组合分析开始日期失败: {e}")
                            
                if hasattr(self.main_window, 'last_component_analysis_end_date'):
                    end_date_val = getattr(self.main_window, 'last_component_analysis_end_date', '')
                    if not callable(end_date_val) and end_date_val and end_date_val != '2000-01-01':
                        try:
                            qdate = QDate.fromString(str(end_date_val), "yyyy-MM-dd")
                            if qdate.isValid():
                                self.end_date_picker.setDate(qdate)
                                print(f"更新组合分析结束日期: {end_date_val}")
                        except Exception as e:
                            print(f"更新组合分析结束日期失败: {e}")
                    else:
                        print("没有组合分析开始日期1")
                else:
                    print("没有组合分析结束日期2")
                        
            print("组合分析界面控件更新完成")
        except Exception as e:
            print(f"更新组合分析界面控件失败: {e}")

    def _show_imported_analysis_from_data(self, headers, data_rows):
        """展示导入的分析表格数据（不含参数行）"""
        # 清理旧内容
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 创建表格
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
        table = QTableWidget(len(data_rows), len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        for i, row in enumerate(data_rows):
            for j, cell in enumerate(row):
                item = QTableWidgetItem(str(cell))
                table.setItem(i, j, item)
        table.resizeColumnsToContents()
        for i in range(table.rowCount()):
            table.resizeRowToContents(i)
        self.result_layout.addWidget(table)
        
        # 将导入的数据转换为cached_analysis_results格式
        self._convert_imported_data_to_cached_results(headers, data_rows)
        
    def _convert_imported_data_to_cached_results(self, headers, data_rows):
        """将导入的表格数据转换为cached_analysis_results格式"""
        try:
            # 检查是否是组合分析结果格式（包含"组合分析排序输出值"列）
            if "组合分析排序输出值" in headers:
                cached_results = []
                for i, row in enumerate(data_rows):
                    if len(row) >= 6:  # 确保有足够的列
                        try:
                            adjusted_value = float(row[0])  # 组合分析排序输出值
                            formula = row[1]  # 公式
                            width = row[2]  # 日期宽度
                            op_days = row[3]  # 操作天数
                            increment_rate = row[4]  # 止盈递增率
                            sort_mode = row[5]  # 排序方式
                            
                            # 创建符合cached_analysis_results格式的数据
                            analysis_info = {
                                'index': i,
                                'analysis': {
                                    'formula': formula,
                                    'width': width,
                                    'op_days': op_days,
                                    'increment_rate': increment_rate,
                                    'sort_mode': sort_mode
                                },
                                'adjusted_value': adjusted_value,
                                'total_sum': adjusted_value,  # 简化处理
                                'valid_count': 1,
                                'avg_sum': adjusted_value,
                                'op_days': int(op_days) if op_days.isdigit() else 1
                            }
                            cached_results.append(analysis_info)
                        except (ValueError, IndexError) as e:
                            print(f"转换第{i}行数据失败: {e}")
                            continue
                
                # 保存到缓存
                self.cached_analysis_results = cached_results
                self.main_window.cached_component_analysis_results = cached_results
                print(f"成功转换并缓存 {len(cached_results)} 条组合分析结果")
            else:
                print("导入的数据不是组合分析结果格式")
        except Exception as e:
            print(f"转换导入数据失败: {e}")

    def _on_continuous_sum_logic_changed(self, state):
        """连续累加值正负相加值含逻辑状态改变"""
        self.main_window.last_component_continuous_sum_logic = (state == Qt.Checked)
        
    def _on_valid_sum_logic_changed(self, state):
        """有效累加值正负相加值含逻辑状态改变"""
        self.main_window.last_component_valid_sum_logic = (state == Qt.Checked)

    def get_cached_analysis_results(self):
        return getattr(self, 'cached_analysis_results', None)

    def set_cached_analysis_results(self, results):
        self.cached_analysis_results = results
        # 同步到主窗口
        self.main_window.cached_component_analysis_results = results
        # 保存总耗时到主窗口
        if results and isinstance(results, dict) and 'total_elapsed_time' in results:
            self.main_window.last_component_total_elapsed_time = results['total_elapsed_time']
        if results:
            self.show_analysis_results(results)
        # 更新上次最优值显示
        self._update_last_best_value_display()
            
    def on_generate_trading_plan(self):
        """生成操盘方案"""
        if not self.cached_analysis_results:
            QMessageBox.warning(self, "提示", "请先执行组合分析，生成分析结果后再生成操盘方案！")
            return
            
        try:
            # 生成操盘方案列表
            trading_plan_list = self._generate_trading_plan_list()
            
            # 保存到主窗口
            self.main_window.trading_plan_list = trading_plan_list
            
            # 显示操盘方案
            self._show_trading_plan(trading_plan_list)
            
            QMessageBox.information(self, "成功", f"已生成 {len(trading_plan_list)} 个操盘方案！")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成操盘方案失败：{e}")
            
    def _generate_trading_plan_list(self):
        """根据组合分析结果生成操盘方案列表"""
        trading_plan_list = []
        
        for i, result in enumerate(self.cached_analysis_results):
            analysis = result['analysis']
            
            # 收集所有控件参数
            params = self._collect_all_control_params()
            
            # 将特定参数添加到params中
            params.update({
                'width': analysis.get('width', ''),
                'sort_mode': analysis.get('sort_mode', ''),
                'op_days': analysis.get('op_days', ''),
                'increment_rate': analysis.get('increment_rate', ''),
                'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
                'n_values': analysis.get('n_values', [])
            })

            print(f"component_analysis_ui selected_vars_with_values: {params.get('selected_vars_with_values', [])}")
            
            # 创建操盘方案
            trading_plan = {
                'plan_id': i + 1,
                'formula': analysis.get('formula', ''),
                'params': params,
                'adjusted_value': result.get('adjusted_value', 0),
                'total_sum': result.get('total_sum', 0),
                'valid_count': result.get('valid_count', 0),
                'avg_sum': result.get('avg_sum', 0),
                'generate_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'description': f"操盘方案{i+1}：基于{analysis.get('sort_mode', '')}排序，日期宽度{analysis.get('width', '')}，操作天数{analysis.get('op_days', '')}，止盈递增率{analysis.get('increment_rate', '')}%"
            }
            
            trading_plan_list.append(trading_plan)
            
        # 排序后设置plan_name，确保索引一致
        sorted_plan_list = sorted(trading_plan_list, key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
        for plan in sorted_plan_list:
            if 'plan_name' not in plan:
                plan['plan_name'] = "操盘方案"
        
        return sorted_plan_list
        
    def _show_trading_plan(self, trading_plan_list):
        """显示操盘方案"""
        # 清理旧内容
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                
        # 创建操盘方案表格
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
        from PyQt5.QtCore import Qt
        
        headers = ["方案ID", "排序方式", "日期宽度", "操作天数", "止盈递增率", "调整值", "总分", "有效数", "平均分", "生成时间", "描述"]
        table = QTableWidget(len(trading_plan_list), len(headers), self.result_area)
        table.setHorizontalHeaderLabels(headers)
        
        for row, plan in enumerate(trading_plan_list):
            params = plan.get('params', {})
            table.setItem(row, 0, QTableWidgetItem(str(plan['plan_id'])))
            table.setItem(row, 1, QTableWidgetItem(str(params.get('sort_mode', ''))))
            table.setItem(row, 2, QTableWidgetItem(str(params.get('width', ''))))
            table.setItem(row, 3, QTableWidgetItem(str(params.get('op_days', ''))))
            table.setItem(row, 4, QTableWidgetItem(f"{params.get('increment_rate', '')}%"))
            table.setItem(row, 5, QTableWidgetItem(f"{plan['adjusted_value']:.2f}"))
            table.setItem(row, 6, QTableWidgetItem(f"{plan['total_sum']:.2f}"))
            table.setItem(row, 7, QTableWidgetItem(str(plan['valid_count'])))
            table.setItem(row, 8, QTableWidgetItem(f"{plan['avg_sum']:.2f}"))
            table.setItem(row, 9, QTableWidgetItem(str(plan['generate_time'])))
            
            # 描述列需要特殊处理，因为可能很长
            desc_item = QTableWidgetItem(str(plan['description']))
            desc_item.setToolTip(plan['description'])
            table.setItem(row, 10, desc_item)
            
        table.resizeColumnsToContents()
        # 设置最后一列（按钮列）的固定宽度
        table.setColumnWidth(6, 100)  # 按钮列宽度设为100px
        # 自动调整行高以适配多行公式
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)
            
        self.result_layout.addWidget(table)
        
        # 添加保存操盘方案按钮
        save_plan_btn = QPushButton("保存操盘方案")
        save_plan_btn.clicked.connect(self._save_trading_plan)
        self.result_layout.addWidget(save_plan_btn)
        
    def _save_trading_plan(self):
        """保存操盘方案到文件"""
        if not hasattr(self.main_window, 'trading_plan_list') or not self.main_window.trading_plan_list:
            QMessageBox.warning(self, "提示", "没有可保存的操盘方案！")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "保存操盘方案", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        if not file_path.endswith('.json'):
            file_path += '.json'
            
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.main_window.trading_plan_list, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", f"操盘方案已保存到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存操盘方案失败：{e}")

    def _add_top_result_to_trading_plan(self, top_result):
        """将排序第一的结果添加到操盘方案列表"""
        try:
            # 确保主窗口有trading_plan_list属性
            if not hasattr(self.main_window, 'trading_plan_list'):
                self.main_window.trading_plan_list = []
            
            # 从top_result中获取数据
            analysis = top_result['analysis']
            
            # 收集所有控件参数
            params = self._collect_all_control_params()
            
            # 将特定参数添加到params中
            params.update({
                'width': analysis.get('width', ''),
                'sort_mode': analysis.get('sort_mode', ''),
                'op_days': analysis.get('op_days', ''),
                'increment_rate': analysis.get('increment_rate', ''),
                'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
                'n_values': analysis.get('n_values', [])
            })
            
            # 创建操盘方案
            trading_plan = {
                'plan_id': len(self.main_window.trading_plan_list) + 1,
                'formula': analysis.get('formula', ''),
                'params': params,
                'adjusted_value': top_result.get('adjusted_value', 0),
                'total_sum': top_result.get('total_sum', 0),
                'valid_count': top_result.get('valid_count', 0),
                'avg_sum': top_result.get('avg_sum', 0),
                'generate_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'description': f"操盘方案{len(self.main_window.trading_plan_list) + 1}：基于{analysis.get('sort_mode', '')}排序，日期宽度{analysis.get('width', '')}，操作天数{analysis.get('op_days', '')}，止盈递增率{analysis.get('increment_rate', '')}%"
            }
            
            # 添加到操盘方案列表
            self.main_window.trading_plan_list.append(trading_plan)
            
            # 重新排序并更新所有plan_name
            sorted_plan_list = sorted(self.main_window.trading_plan_list, key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
            for plan in sorted_plan_list:
                if 'plan_name' not in plan:
                    plan['plan_name'] = "操盘方案"
            
            self.main_window.trading_plan_list = sorted_plan_list
            
            print(f"已添加操盘方案：{trading_plan['description']}")
            print(f"当前操盘方案数量：{len(self.main_window.trading_plan_list)}")
            
        except Exception as e:
            print(f"添加操盘方案失败：{e}")
            
    def _collect_all_control_params(self):
        """收集所有控件参数"""
        params = {}
        
        # 参考导出功能的config_keys，排除不需要的参数
        config_keys = [
            'date', 'width', 'start_option', 'shift', 'inc_rate', 'op_days', 'after_gt_end_edit',
            'after_gt_prev_edit', 'n_days', 'n_days_max', 'range_value', 'continuous_abs_threshold',
            'ops_change', 'expr', 'last_select_count', 'last_sort_mode', 'direction',
            'analysis_start_date', 'analysis_end_date', 'component_analysis_start_date',
            'component_analysis_end_date', 'cpu_cores',
            'trade_mode',
            'new_before_high_start', 'new_before_high_range', 'new_before_high_span',
            'new_before_low_start', 'new_before_low_range', 'new_before_low_span',
            'valid_abs_sum_threshold', 'new_before_high_logic', 'new_before_high2_start',
            'new_before_high2_range', 'new_before_high2_span', 'new_before_high2_logic',
            'new_after_high_start', 'new_after_high_range', 'new_after_high_span', 'new_after_high_logic',
            'new_after_high2_start', 'new_after_high2_range', 'new_after_high2_span', 'new_after_high2_logic',
            'new_before_low_start', 'new_before_low_range', 'new_before_low_span', 'new_before_low_logic',
            'new_before_low2_start', 'new_before_low2_range', 'new_before_low2_span', 'new_before_low2_logic',
            'new_after_low_start', 'new_after_low_range', 'new_after_low_span', 'new_after_low_logic',
            'new_after_low2_start', 'new_after_low2_range', 'new_after_low2_span', 'new_after_low2_logic',
            'new_before_high_flag', 'new_before_high2_flag', 'new_after_high_flag', 'new_after_high2_flag',
            'new_before_low_flag', 'new_before_low2_flag', 'new_after_low_flag', 'new_after_low2_flag'
        ]
        
        for k in config_keys:
            try:
                v = None
                # 特殊处理：width 参数直接查找 width_spin 控件
                if k == 'width' and hasattr(self.main_window, 'width_spin'):
                    v = self.main_window.width_spin.value()
                # 特殊处理：组合分析日期参数
                elif k == 'component_analysis_start_date' and hasattr(self.main_window, 'last_component_analysis_start_date'):
                    v = getattr(self.main_window, 'last_component_analysis_start_date', '')
                elif k == 'component_analysis_end_date' and hasattr(self.main_window, 'last_component_analysis_end_date'):
                    v = getattr(self.main_window, 'last_component_analysis_end_date', '')
                # LineEdit - 优先处理，避免被当作直接控件名
                elif hasattr(self.main_window, k + '_edit'):
                    edit_name = k + '_edit'
                    v = getattr(self.main_window, edit_name).text()
                # SpinBox
                elif hasattr(self.main_window, k + '_spin'):
                    spin_name = k + '_spin'
                    v = getattr(self.main_window, spin_name).value()
                # ComboBox
                elif hasattr(self.main_window, k + '_combo'):
                    combo_name = k + '_combo'
                    v = getattr(self.main_window, combo_name).currentText()
                # CheckBox
                elif hasattr(self.main_window, k + '_checkbox'):
                    checkbox_name = k + '_checkbox'
                    v = getattr(self.main_window, checkbox_name).isChecked()
                # 直接控件名（如 after_gt_end_edit）
                elif hasattr(self.main_window, k):
                    attr_value = getattr(self.main_window, k)
                    # 检查是否是控件对象，获取其值
                    if hasattr(attr_value, 'text'):
                        v = attr_value.text()
                    elif hasattr(attr_value, 'value'):
                        v = attr_value.value()
                    elif hasattr(attr_value, 'currentText'):
                        v = attr_value.currentText()
                    elif hasattr(attr_value, 'isChecked'):
                        v = attr_value.isChecked()
                    else:
                        # 不是控件对象，是普通属性
                        v = attr_value
                
                # 确保v不是方法对象
                if v is not None and not callable(v):
                    params[k] = v
                    
            except Exception as e:
                print(f"收集参数 {k} 失败: {e}")
                continue
                
        # 添加forward_param_state
        if hasattr(self.main_window, 'forward_param_state'):
            params['forward_param_state'] = self.main_window.forward_param_state
                
        return params

    def _on_generate_trading_plan_changed(self, state):
        """生成操盘方案勾选框状态改变"""
        self.main_window.last_component_generate_trading_plan = (state == Qt.Checked)
        
    def _on_only_better_trading_plan_changed(self, state):
        """大于上次最优值才生成操盘方案勾选框状态改变"""
        self.main_window.last_component_only_better_trading_plan = (state == Qt.Checked)
        
    def _update_last_best_value_display(self):
        """更新上次最优值显示"""
        last_value = getattr(self.main_window, 'last_adjusted_value', None)
        if last_value is not None:
            try:
                # 尝试转换为浮点数并格式化显示
                last_value_float = float(last_value)
                self.last_best_value_display.setText(f"{last_value_float:.2f}")
            except (ValueError, TypeError):
                # 如果转换失败，直接显示原值
                self.last_best_value_display.setText(str(last_value))
        else:
            self.last_best_value_display.setText("无")

    def _on_clear_best_value(self):
        """清空上次最优值"""
        self.main_window.last_adjusted_value = None
        self._update_last_best_value_display()


class AnalysisDetailWindow(QMainWindow):
    def __init__(self, analysis_data, create_table_func, idx):
        super().__init__(None)
        self.setWindowTitle(f"组合分析结果详情 - 第{idx+1}行")
        self.setMinimumSize(1600, 800)
        flags = self.windowFlags()
        flags &= ~Qt.WindowStaysOnTopHint
        flags |= Qt.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        detail_table = create_table_func(analysis_data)
        scroll_layout.addWidget(detail_table)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        self.setCentralWidget(scroll_area)