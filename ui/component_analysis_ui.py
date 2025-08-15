"""
组合分析UI模块
提供组合分析功能的独立界面
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton, 
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QCheckBox, QTabWidget, QSpinBox, QDialog, QScrollArea, QMainWindow, QLineEdit
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont
import pandas as pd
from datetime import datetime
import math
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
        self.is_three_stage_mode = False  # 三次分析模式标记
        self.three_stage_round_better = None  # 本轮是否优于上一轮（用于三次分析）
        self.best_param_condition_list = []  # 跟踪每个参数的最优条件，用于导出JSON
        self.no_better_result_list = []  # 跟踪每个参数的无最优结果情况，用于导出
        self.analysis_completed_callback = None  # 分析完成后的回调函数
        self.init_ui()
        
        # 连接勾选框状态改变信号
        self.continuous_sum_logic_checkbox.stateChanged.connect(self._on_continuous_sum_logic_changed)
        self.valid_sum_logic_checkbox.stateChanged.connect(self._on_valid_sum_logic_changed)
        self.generate_trading_plan_checkbox.stateChanged.connect(self._on_generate_trading_plan_changed)
    
    def log_three_analysis(self, message):
        """记录三次分析日志到文件"""
        try:
            with open('three_analysis_log.txt', 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception:
            pass
    
    def clear_three_analysis_log(self):
        """清空三次分析日志文件"""
        try:
            with open('three_analysis_log.txt', 'w', encoding='utf-8') as f:
                f.write('')  # 清空文件内容
        except Exception:
            pass
    
    def _generate_trading_plan_with_notification(self, top_one, is_three_stage_mode=False, round_index=None):
        """
        生成操盘方案并显示相应的提醒信息
        
        Args:
            top_one: 最优分析结果
            is_three_stage_mode: 是否为三次分析模式
            round_index: 三次分析的轮次索引
        """
        if not top_one:
            # 没有满足条件的结果，弹框提醒
            message = "没有满足条件的组合分析结果"
            QMessageBox.warning(self, "无满足条件结果", message)
            return False
            
        new_value = top_one.get('adjusted_value', None)
        if new_value is None:
            return False
            
        try:
            new_value_float = float(new_value)
        except (ValueError, TypeError):
            return False
            
        # 获取上次分析最优值和锁定最优值
        # 在三次分析模式下，使用保存的快照；在普通模式下，使用当前的last_adjusted_value
        if is_three_stage_mode:
            last_value = getattr(self, 'three_stage_initial_last_value', None)
        else:
            last_value = getattr(self.main_window, 'last_adjusted_value', None)
        locked_value = getattr(self.main_window, 'locked_adjusted_value', None)
        
        try:
            last_value_float = float(last_value) if last_value is not None else None
            locked_value_float = float(locked_value) if locked_value is not None else None
        except (ValueError, TypeError):
            last_value_float = None
            locked_value_float = None
        
        # 判断是否应该生成操盘方案
        should_generate = False
        threshold = None
        better_percent = 0.0
        
        if new_value_float > 0:
            try:
                better_percent = float(self.only_better_trading_plan_edit.text())
            except ValueError:
                better_percent = 0.0
            
            if last_value_float is not None:
                # 计算需要超过的阈值：上次分析最优值 * (百分比/100)
                threshold = last_value_float * (better_percent / 100)
                should_generate = new_value_float > threshold
            else:
                # 第一次生成时，直接生成
                should_generate = True
        
        # 构建提醒信息
        if should_generate:
            # 成功提示
            if last_value_float is not None:
                message = f"有最优方案出现！当前最优组合排序输出值：{new_value_float:.2f}，大于上次分析最优值：{last_value_float:.2f} 的 {better_percent}% = {threshold:.2f}"
            else:
                message = f"有最优方案出现！当前最优组合排序输出值：{new_value_float:.2f}，这是第一次分析"
            
            # 如果有锁定最优值，也提示是否大于锁定最优值
            if locked_value_float is not None:
                if new_value_float > locked_value_float:
                    message += f"\n\n且大于锁定最优值 {locked_value_float:.2f}"
                else:
                    message += f"\n\n但不大于锁定最优值 {locked_value_float:.2f}"
            
            # 在三次分析模式下，记录到日志；在普通模式下，弹框提示
            if is_three_stage_mode:
                round_info = f"第{round_index}次" if round_index is not None else ""
                self.log_three_analysis(f"【{round_info}】{message}")
                # 如果是最终轮次，也显示弹框提醒
                if round_index == "最终":
                    QMessageBox.information(self, "三次分析完成 - 最优方案提示", message)
            else:
                # 在连续分析模式下，不显示弹窗提示，只记录日志
                if getattr(self, 'is_auto_three_stage_mode', False):
                    self.log_three_analysis(f"连续分析组合分析阶段：{message}")
                else:
                    QMessageBox.information(self, "最优方案提示", message)
        else:
            # 失败提示
            if last_value_float is not None and threshold is not None:
                message = f"该组合分析最优方案的输出值 {new_value_float:.2f} 不大于上次分析最优值 {last_value_float:.2f} 的 {better_percent}% = {threshold:.2f}，此方案无效，不生成操盘方案"
                
                # 如果有锁定最优值，也提示是否大于锁定最优值
                if locked_value_float is not None:
                    if new_value_float > locked_value_float:
                        message += f"\n\n但大于锁定最优值 {locked_value_float:.2f}"
                    else:
                        message += f"\n\n且不大于锁定最优值 {locked_value_float:.2f}"
                
                # 在三次分析模式下，记录到日志；在普通模式下，弹框提示
                if is_three_stage_mode:
                    round_info = f"第{round_index}次" if round_index is not None else ""
                    self.log_three_analysis(f"【{round_info}】{message}")
                    # 如果是最终轮次，也显示弹框提醒
                    if round_index == "最终":
                        QMessageBox.warning(self, "三次分析完成 - 方案无效", message)
                else:
                    # 在连续分析模式下，不显示弹窗提示，只记录日志
                    if getattr(self, 'is_auto_three_stage_mode', False):
                        self.log_three_analysis(f"连续分析组合分析阶段：{message}")
                    else:
                        QMessageBox.warning(self, "方案无效", message)
        
        # 如果满足条件，生成操盘方案
        if should_generate and self.generate_trading_plan_checkbox.isChecked():
            self._add_top_result_to_trading_plan(top_one)
            
            # 更新锁定最优值
            if locked_value_float is None or new_value_float > locked_value_float:
                self.main_window.locked_adjusted_value = new_value_float
            
            # 更新显示
            self._update_last_best_value_display()
            
            return True
        
        return False
        
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
        
        # 二次分析次数设置控件
        self.secondary_analysis_count_label = QLabel("二次分析次数:")
        self.secondary_analysis_count_spin = QSpinBox()
        self.secondary_analysis_count_spin.setMinimum(1)
        self.secondary_analysis_count_spin.setMaximum(9999999)
        self.secondary_analysis_count_spin.setValue(1)  # 默认1次
        self.secondary_analysis_count_spin.setFixedWidth(45)
        
        # 恢复保存的二次分析次数
        if hasattr(self.main_window, 'last_component_secondary_analysis_count'):
            self.secondary_analysis_count_spin.setValue(self.main_window.last_component_secondary_analysis_count)
        
        # 绑定信号，变更时同步变量
        self.secondary_analysis_count_spin.valueChanged.connect(self._on_secondary_analysis_count_changed_save)
        
        # 功能按钮
        self.analyze_btn = QPushButton("点击分析")
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        
        self.optimize_btn = QPushButton("二次分析")
        self.optimize_btn.clicked.connect(self.on_optimize_clicked)
        
        self.three_stage_btn = QPushButton("三次分析")
        self.three_stage_btn.clicked.connect(self.on_three_stage_clicked)
        
        self.terminate_btn = QPushButton("终止分析")
        self.terminate_btn.clicked.connect(self.on_terminate_clicked)
        self.terminate_btn.setEnabled(False)  # 初始状态禁用
        
        # self.export_json_btn = QPushButton("导出最优方案(JSON)")
        # self.export_json_btn.clicked.connect(self.on_export_json)
        
        self.export_csv_btn = QPushButton("导出最优方案")
        self.export_csv_btn.clicked.connect(self.on_export_csv)
        
        # self.import_json_btn = QPushButton("导入方案")
        # self.import_json_btn.clicked.connect(self.on_import_json)

        self.import_csv_btn = QPushButton("导入方案")
        self.import_csv_btn.clicked.connect(self.on_import_csv)
        
        # 添加导出和导入三次分析结果按钮
        # self.export_three_stage_btn = QPushButton("导出三次分析结果")
        # self.export_three_stage_btn.clicked.connect(self.on_export_three_stage_clicked)
        
        # self.import_three_stage_btn = QPushButton("导入三次分析结果")
        # self.import_three_stage_btn.clicked.connect(self.on_import_three_stage_clicked)
        
        # 生成操盘方案勾选框
        self.generate_trading_plan_checkbox = QCheckBox("生成操盘方案")
        self.generate_trading_plan_checkbox.setChecked(False)  # 默认不勾选
        
        # 恢复生成操盘方案勾选框状态
        if hasattr(self.main_window, 'last_component_generate_trading_plan'):
            self.generate_trading_plan_checkbox.setChecked(self.main_window.last_component_generate_trading_plan)
        
        # 新增：组合-三次连续分析按钮
        self.auto_three_stage_btn = QPushButton("组合-三次连续分析")
        self.auto_three_stage_btn.clicked.connect(self.on_auto_three_stage_clicked)
        
        # 大于上次最优值才生成操盘方案输入框
        self.only_better_trading_plan_label = QLabel("大于上次最优值")
        self.only_better_trading_plan_edit = QLineEdit()
        self.only_better_trading_plan_edit.setPlaceholderText("0")
        self.only_better_trading_plan_edit.setText("0")  # 默认0%
        self.only_better_trading_plan_edit.setFixedWidth(30)
        self.only_better_trading_plan_percent_label = QLabel("%才生成操盘方案")
        
        # 恢复大于上次最优值才生成操盘方案输入框状态
        if hasattr(self.main_window, 'last_component_only_better_trading_plan_percent'):
            self.only_better_trading_plan_edit.setText(str(self.main_window.last_component_only_better_trading_plan_percent))
        
        # 绑定信号，变更时同步变量
        self.only_better_trading_plan_edit.textChanged.connect(self._on_only_better_trading_plan_percent_changed_save)
        
        # 添加持有率、止盈率、止损率区间输入框
        self.hold_rate_label = QLabel("持有率:")
        self.hold_rate_min_edit = QLineEdit()
        self.hold_rate_min_edit.setPlaceholderText("0")
        self.hold_rate_min_edit.setText("0")  # 默认下限0
        self.hold_rate_min_edit.setFixedWidth(30)
        
        self.hold_rate_separator = QLabel("~")
        self.hold_rate_separator.setFixedWidth(15)
        
        self.hold_rate_max_edit = QLineEdit()
        self.hold_rate_max_edit.setPlaceholderText("100")
        self.hold_rate_max_edit.setText("100")  # 默认上限100
        self.hold_rate_max_edit.setFixedWidth(30)
        
        # 恢复保存的持有率区间
        if hasattr(self.main_window, 'last_component_hold_rate_min'):
            self.hold_rate_min_edit.setText(str(self.main_window.last_component_hold_rate_min))
        if hasattr(self.main_window, 'last_component_hold_rate_max'):
            self.hold_rate_max_edit.setText(str(self.main_window.last_component_hold_rate_max))
        
        # 绑定信号，变更时同步变量
        self.hold_rate_min_edit.textChanged.connect(self._on_hold_rate_min_changed_save)
        self.hold_rate_max_edit.textChanged.connect(self._on_hold_rate_max_changed_save)
        
        self.profit_rate_label = QLabel("止盈率:")
        self.profit_rate_min_edit = QLineEdit()
        self.profit_rate_min_edit.setPlaceholderText("0")
        self.profit_rate_min_edit.setText("0")  # 默认下限0
        self.profit_rate_min_edit.setFixedWidth(30)
        
        self.profit_rate_separator = QLabel("~")
        self.profit_rate_separator.setFixedWidth(15)
        
        self.profit_rate_max_edit = QLineEdit()
        self.profit_rate_max_edit.setPlaceholderText("100")
        self.profit_rate_max_edit.setText("100")  # 默认上限100
        self.profit_rate_max_edit.setFixedWidth(30)
        
        # 恢复保存的止盈率区间
        if hasattr(self.main_window, 'last_component_profit_rate_min'):
            self.profit_rate_min_edit.setText(str(self.main_window.last_component_profit_rate_min))
        if hasattr(self.main_window, 'last_component_profit_rate_max'):
            self.profit_rate_max_edit.setText(str(self.main_window.last_component_profit_rate_max))
        
        # 绑定信号，变更时同步变量
        self.profit_rate_min_edit.textChanged.connect(self._on_profit_rate_min_changed_save)
        self.profit_rate_max_edit.textChanged.connect(self._on_profit_rate_max_changed_save)
        
        self.loss_rate_label = QLabel("止损率:")
        self.loss_rate_min_edit = QLineEdit()
        self.loss_rate_min_edit.setPlaceholderText("0")
        self.loss_rate_min_edit.setText("0")  # 默认下限0
        self.loss_rate_min_edit.setFixedWidth(30)
        
        self.loss_rate_separator = QLabel("~")
        self.loss_rate_separator.setFixedWidth(15)
        
        self.loss_rate_max_edit = QLineEdit()
        self.loss_rate_max_edit.setPlaceholderText("100")
        self.loss_rate_max_edit.setText("100")  # 默认上限100
        self.loss_rate_max_edit.setFixedWidth(30)
        
        # 恢复保存的止损率区间
        if hasattr(self.main_window, 'last_component_loss_rate_min'):
            self.loss_rate_min_edit.setText(str(self.main_window.last_component_loss_rate_min))
        if hasattr(self.main_window, 'last_component_loss_rate_max'):
            self.loss_rate_max_edit.setText(str(self.main_window.last_component_loss_rate_max))
        
        # 绑定信号，变更时同步变量
        self.loss_rate_min_edit.textChanged.connect(self._on_loss_rate_min_changed_save)
        self.loss_rate_max_edit.textChanged.connect(self._on_loss_rate_max_changed_save)
        
        # 综合止盈止损需大于输入框
        self.comprehensive_daily_change_label = QLabel("综合止盈止损需大于")
        self.comprehensive_daily_change_edit = QLineEdit()
        self.comprehensive_daily_change_edit.setPlaceholderText("0")
        self.comprehensive_daily_change_edit.setText("0")  # 默认0%
        self.comprehensive_daily_change_edit.setFixedWidth(30)
        self.comprehensive_daily_change_percent_label = QLabel("%")
        
        # 恢复综合止盈止损需大于输入框状态
        if hasattr(self.main_window, 'last_component_comprehensive_daily_change_threshold'):
            self.comprehensive_daily_change_edit.setText(str(self.main_window.last_component_comprehensive_daily_change_threshold))
        
        # 综合停盈停损需大于输入框
        self.comprehensive_stop_daily_change_label = QLabel("综合停盈停损需大于")
        self.comprehensive_stop_daily_change_edit = QLineEdit()
        self.comprehensive_stop_daily_change_edit.setPlaceholderText("0")
        self.comprehensive_stop_daily_change_edit.setText("0")  # 默认0%
        self.comprehensive_stop_daily_change_edit.setFixedWidth(30)
        self.comprehensive_stop_daily_change_percent_label = QLabel("%")
        
        # 恢复综合停盈停损需大于输入框状态
        if hasattr(self.main_window, 'last_component_comprehensive_stop_daily_change_threshold'):
            self.comprehensive_stop_daily_change_edit.setText(str(self.main_window.last_component_comprehensive_stop_daily_change_threshold))

        self.comprehensive_daily_change_edit.textChanged.connect(self._on_comprehensive_daily_change_threshold_changed_save)
        self.comprehensive_stop_daily_change_edit.textChanged.connect(self._on_comprehensive_stop_daily_change_threshold_changed_save)
        
        # 上次分析最优值显示标签
        self.last_best_value_label = QLabel("上次分析最优值：")
        self.last_best_value_display = QLabel("无")
        self.last_best_value_display.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # 新增：锁定最优值显示标签
        self.locked_best_value_label = QLabel("锁定最优值：")
        self.locked_best_value_display = QLabel("无")
        self.locked_best_value_display.setStyleSheet("color: #2196F3; font-weight: bold;")
        
        # 新增：分别的清空按钮
        self.clear_last_best_value_btn = QPushButton("清空上次")
        self.clear_last_best_value_btn.setFixedWidth(60)
        self.clear_last_best_value_btn.clicked.connect(self._on_clear_last_best_value)
        
        self.clear_locked_best_value_btn = QPushButton("清空锁定")
        self.clear_locked_best_value_btn.setFixedWidth(60)
        self.clear_locked_best_value_btn.clicked.connect(self._on_clear_locked_best_value)
        
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
        row_layout.addWidget(self.secondary_analysis_count_label)
        row_layout.addWidget(self.secondary_analysis_count_spin)
        row_layout.addWidget(self.analyze_btn)
        row_layout.addWidget(self.optimize_btn)
        row_layout.addWidget(self.three_stage_btn)
        row_layout.addWidget(self.auto_three_stage_btn)
        row_layout.addWidget(self.terminate_btn)
        # row_layout.addWidget(self.export_json_btn)
        row_layout.addWidget(self.export_csv_btn)
        # row_layout.addWidget(self.import_json_btn)
        row_layout.addWidget(self.import_csv_btn)
        # row_layout.addWidget(self.export_three_stage_btn)
        # row_layout.addWidget(self.import_three_stage_btn)
        row_layout.addWidget(self.generate_trading_plan_checkbox)
        row_layout.addWidget(self.only_better_trading_plan_label)
        row_layout.addWidget(self.only_better_trading_plan_edit)
        row_layout.addWidget(self.only_better_trading_plan_percent_label)
        row_layout.addWidget(self.hold_rate_label)
        row_layout.addWidget(self.hold_rate_min_edit)
        row_layout.addWidget(self.hold_rate_separator)
        row_layout.addWidget(self.hold_rate_max_edit)
        row_layout.addWidget(self.profit_rate_label)
        row_layout.addWidget(self.profit_rate_min_edit)
        row_layout.addWidget(self.profit_rate_separator)
        row_layout.addWidget(self.profit_rate_max_edit)
        row_layout.addWidget(self.loss_rate_label)
        row_layout.addWidget(self.loss_rate_min_edit)
        row_layout.addWidget(self.loss_rate_separator)
        row_layout.addWidget(self.loss_rate_max_edit)
        row_layout.addWidget(self.comprehensive_daily_change_label)
        row_layout.addWidget(self.comprehensive_daily_change_edit)
        row_layout.addWidget(self.comprehensive_daily_change_percent_label)
        row_layout.addWidget(self.comprehensive_stop_daily_change_label)
        row_layout.addWidget(self.comprehensive_stop_daily_change_edit)
        row_layout.addWidget(self.comprehensive_stop_daily_change_percent_label)
        row_layout.addWidget(self.last_best_value_label)
        row_layout.addWidget(self.last_best_value_display)
        row_layout.addWidget(self.locked_best_value_label)
        row_layout.addWidget(self.locked_best_value_display)
        row_layout.addWidget(self.clear_last_best_value_btn)
        row_layout.addWidget(self.clear_locked_best_value_btn)
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
            # 检查上一次执行的分析是否是三次分析
            if hasattr(self.main_window, 'last_analysis_was_three_stage') and self.main_window.last_analysis_was_three_stage:
                # 上一次是三次分析，将三次分析的全局top_three设置到本地，但不改变分析模式状态
                self.three_stage_global_top_three = self.main_window.cached_component_analysis_results
                print(f"恢复三次分析结果，长度 = {len(self.three_stage_global_top_three)}")
                # 恢复三次分析结果后，需要调用show_analysis_results来显示表格
                self.show_analysis_results([])
            else:
                # 上一次是普通分析，直接恢复结果
                self.set_cached_analysis_results(self.main_window.cached_component_analysis_results)
                print("恢复普通分析结果")
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
        
    def _on_secondary_analysis_count_changed_save(self):
        """保存二次分析次数变更"""
        self.main_window.last_component_secondary_analysis_count = self.secondary_analysis_count_spin.value()
        
    def _on_hold_rate_min_changed_save(self):
        """保存持有率最小值变更"""
        try:
            value = int(self.hold_rate_min_edit.text())
            self.main_window.last_component_hold_rate_min = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
        
    def _on_hold_rate_max_changed_save(self):
        """保存持有率最大值变更"""
        try:
            value = int(self.hold_rate_max_edit.text())
            self.main_window.last_component_hold_rate_max = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
        
    def _on_profit_rate_min_changed_save(self):
        """保存止盈率最小值变更"""
        try:
            value = int(self.profit_rate_min_edit.text())
            self.main_window.last_component_profit_rate_min = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
        
    def _on_profit_rate_max_changed_save(self):
        """保存止盈率最大值变更"""
        try:
            value = int(self.profit_rate_max_edit.text())
            self.main_window.last_component_profit_rate_max = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
        
    def _on_loss_rate_min_changed_save(self):
        """保存止损率最小值变更"""
        try:
            value = int(self.loss_rate_min_edit.text())
            self.main_window.last_component_loss_rate_min = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
        
    def _on_loss_rate_max_changed_save(self):
        """保存止损率最大值变更"""
        try:
            value = int(self.loss_rate_max_edit.text())
            self.main_window.last_component_loss_rate_max = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
            
    def _on_only_better_trading_plan_percent_changed_save(self):
        """保存大于上次最优值百分比变更"""
        try:
            value = float(self.only_better_trading_plan_edit.text())
            self.main_window.last_component_only_better_trading_plan_percent = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
    
    def _on_comprehensive_daily_change_threshold_changed_save(self):
        """保存综合止盈止损需大于阈值"""
        try:
            value = float(self.comprehensive_daily_change_edit.text())
            self.main_window.last_component_comprehensive_daily_change_threshold = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
    
    def _on_comprehensive_stop_daily_change_threshold_changed_save(self):
        """保存综合停盈停损需大于阈值"""
        try:
            value = float(self.comprehensive_stop_daily_change_edit.text())
            self.main_window.last_component_comprehensive_stop_daily_change_threshold = value
        except ValueError:
            pass  # 如果输入的不是有效数字，忽略
    
    def _set_buttons_enabled(self, enabled):
        """设置按钮启用/禁用状态"""
        self.analyze_btn.setEnabled(enabled)
        self.optimize_btn.setEnabled(enabled)
        self.three_stage_btn.setEnabled(enabled)
        self.auto_three_stage_btn.setEnabled(enabled)
        self.terminate_btn.setEnabled(not enabled)
    
    def _start_auto_three_stage_analysis(self):
        """开始组合-三次连续分析"""
        try:
            # 禁用相关按钮
            self._set_buttons_enabled(False)
            
            # 设置连续分析模式标识
            self.is_auto_three_stage_mode = True
            
            # 设置主窗口的三次分析标志，用于show_analysis_results的条件判断
            self.main_window.last_analysis_was_three_stage = True
            
            # 设置回调函数，确保组合分析完成后执行三次分析
            self.analysis_completed_callback = self._continue_with_three_stage
            
            # 先执行组合分析（传入连续分析模式参数）
            self.on_analyze_clicked(is_auto_mode=True)
            
        except Exception as e:
            print(f"开始连续分析失败: {e}")
            self._set_buttons_enabled(True)
            self.is_auto_three_stage_mode = False
    
    def _continue_with_three_stage(self):
        """继续执行三次分析"""
        try:
            # 检查是否在连续分析模式下，如果不是则直接返回
            if not getattr(self, 'is_auto_three_stage_mode', False):
                return
                
            # 检查组合分析是否完成
            if hasattr(self, 'analysis_terminated') and self.analysis_terminated:
                print("组合分析被终止，停止连续分析")
                self._set_buttons_enabled(True)
                self.is_auto_three_stage_mode = False
                return
            
            # 执行三次分析
            self.on_three_stage_clicked()
            
        except Exception as e:
            print(f"继续三次分析失败: {e}")
            self._set_buttons_enabled(True)
            self.is_auto_three_stage_mode = False
    
    def on_auto_three_stage_clicked(self):
        """组合-三次连续分析按钮点击处理"""
        self._start_auto_three_stage_analysis()
        
    def on_analyze_clicked(self, is_auto_mode=False):
        """
        执行组合分析
        
        Args:
            is_auto_mode: 是否为连续三次分析模式，默认为False（普通分析模式）
        """
        
        # 根据参数设置分析模式
        self.is_auto_three_stage_mode = is_auto_mode
        
        # 验证组合输出参数选择
        if not self._validate_abbr_round_only_selection():
            return
        
        # 验证组合分析输出值类别选择
        is_valid, error_message = self._validate_category_selection()
        if not is_valid:
            QMessageBox.warning(self, "提示", error_message)
            return
        
        # 清空最优参数条件列表，因为这是普通分析，不是三次分析
        if hasattr(self, 'best_param_condition_list'):
            self.best_param_condition_list.clear()
        if hasattr(self, 'no_better_result_list'):
            self.no_better_result_list.clear()
        
        # 根据分析模式设置主窗口的三次分析标志
        if is_auto_mode:
            # 连续三次分析模式：设置为True，因为后续会执行三次分析
            self.main_window.last_analysis_was_three_stage = True
        else:
            # 普通分析模式：设置为False
            self.main_window.last_analysis_was_three_stage = False
        
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
            n_vars = ['bottom_nth_take_and_stop_with_nan1', 'bottom_nth_take_and_stop_with_nan2', 'bottom_nth_take_and_stop_with_nan3',
                        'bottom_nth_with_nan1', 'bottom_nth_with_nan2', 'bottom_nth_with_nan3',
                        'bottom_nth_stop_and_take_with_nan1', 'bottom_nth_stop_and_take_with_nan2', 'bottom_nth_stop_and_take_with_nan3',
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
            if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
                # 连续分析模式：使用统一的按钮状态管理
                self._set_buttons_enabled(False)
            else:
                # 普通分析模式：使用原有的按钮状态管理
                self.analyze_btn.setEnabled(False)
                self.terminate_btn.setEnabled(True)
                self.optimize_btn.setEnabled(False)
                self.three_stage_btn.setEnabled(False)  # 禁用三次分析按钮
                self.auto_three_stage_btn.setEnabled(False)  # 禁用自动三次分析按钮
            
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
        if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
            # 连续分析模式：使用统一的按钮状态管理
            self._set_buttons_enabled(True)
            self.is_auto_three_stage_mode = False
        else:
            # 普通分析模式：使用原有的按钮状态管理
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            self.optimize_btn.setEnabled(True)
            self.three_stage_btn.setEnabled(True)  # 恢复三次分析按钮
            self.auto_three_stage_btn.setEnabled(True)  # 恢复自动三次分析按钮
        
        # 重置三次分析模式
        if hasattr(self, 'is_three_stage_mode'):
            self.is_three_stage_mode = False
            # 重置三次分析完成标识
            if hasattr(self, 'three_stage_completed'):
                self.three_stage_completed = False
            # 清空最优参数条件列表
            if hasattr(self, 'best_param_condition_list'):
                self.best_param_condition_list.clear()
                print("终止三次分析，清空最优参数条件列表")
        
    def on_optimize_clicked(self):
        """二次分析按钮点击处理"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            import time
            
            # 验证组合输出参数选择
            if not self._validate_abbr_round_only_selection():
                return
            
            # 验证组合分析输出值类别选择
            is_valid, error_message = self._validate_category_selection()
            if not is_valid:
                QMessageBox.warning(self, "提示", error_message)
                return
            
            # 记录开始时间
            start_time = time.time()
            
            # 检查是否有分析结果
            if not hasattr(self.main_window, 'overall_stats') or not self.main_window.overall_stats:
                QMessageBox.warning(self, "提示", "请先进行组合分析，获取最优结果后再进行二次分析！")
                return
                
            # 获取组合分析次数和二次分析次数
            analysis_count = self.analysis_count_spin.value()
            secondary_analysis_count = self.secondary_analysis_count_spin.value()
            
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
            
            # 保存当前设置
            self.main_window.last_component_analysis_start_date = start_date
            self.main_window.last_component_analysis_end_date = end_date
            self.main_window.last_component_analysis_count = analysis_count
            self.main_window.last_component_secondary_analysis_count = secondary_analysis_count
            
            # 创建临时的FormulaSelectWidget实例，避免访问已删除的控件
            from function.stock_functions import FormulaSelectWidget, get_abbr_map, get_abbr_logic_map, get_abbr_round_map
            
            # 获取映射数据
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            
            # 传入所有必需的参数
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
            
            # 恢复上次保存的公式选股状态
            if hasattr(self.main_window, 'last_formula_select_state'):
                temp_formula_widget.set_state(self.main_window.last_formula_select_state)
            
            # 使用优化公式列表方法，传入二次分析次数
            formula_list = temp_formula_widget.optimize_formula_list(secondary_analysis_count)
            
            # 计算耗时
            end_time = time.time()
            
            if not formula_list:
                QMessageBox.warning(self, "提示", "没有生成任何优化公式，请检查变量设置和统计结果！")
                temp_formula_widget.deleteLater()
                return
            
            # 保存优化信息到主窗口
            if formula_list:
                self.main_window.component_analysis_formula_list = formula_list
            
            # 检查公式列表长度并显示警告
            if len(formula_list) > 64:
                QMessageBox.warning(self, "提示", f"组合分析公式超过64个（当前{len(formula_list)}个），没二次优化效果！")
                temp_formula_widget.deleteLater()
                return
            
            # 生成特殊参数组合
            special_params_combinations = temp_formula_widget.generate_special_params_combinations()
            
            # 删除临时控件
            temp_formula_widget.deleteLater()
            
            # 显示进度信息
            total_analyses = len(formula_list) * len(special_params_combinations) * analysis_count
            self.show_message(f"生成了 {len(formula_list)} 个组合公式，开始执行二次分析，总共 {total_analyses} 次分析...")
            
            # 重置终止标志
            self.analysis_terminated = False
            
            # 切换按钮状态
            if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
                # 连续分析模式：使用统一的按钮状态管理
                self._set_buttons_enabled(False)
            else:
                # 普通分析模式：使用原有的按钮状态管理
                self.analyze_btn.setEnabled(False)
                self.terminate_btn.setEnabled(True)
                self.optimize_btn.setEnabled(False)
                self.three_stage_btn.setEnabled(False)  # 禁用三次分析按钮
                self.auto_three_stage_btn.setEnabled(False)  # 禁用自动三次分析按钮
            
            # 执行组合分析
            self.execute_component_analysis(formula_list, special_params_combinations, start_date, end_date)
                
        except Exception as e:
            print(f"二次分析出错: {e}")
            QMessageBox.critical(self, "错误", f"二次分析出错: {e}")
            # 恢复按钮状态
            if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
                # 连续分析模式：使用统一的按钮状态管理
                self._set_buttons_enabled(True)
                self.is_auto_three_stage_mode = False
            else:
                # 普通分析模式：使用原有的按钮状态管理
                self.analyze_btn.setEnabled(True)
                self.terminate_btn.setEnabled(False)
                self.optimize_btn.setEnabled(True)
        
    def on_three_stage_clicked(self):
        """三次分析按钮点击处理：
        1) 生成第一轮公式列表并打印
        2) 以此公式列表执行组合分析（流程同二次分析）
        """
        # 清空三次分析日志文件
        self.clear_three_analysis_log()
        
        # 清空最优参数条件列表，准备记录新的三次分析结果
        self.best_param_condition_list.clear()
        
        try:
            from PyQt5.QtWidgets import QMessageBox
            from function.stock_functions import FormulaSelectWidget, get_abbr_map, get_abbr_logic_map, get_abbr_round_map, get_sorted_params_from_widget

            # 验证组合输出参数选择
            if not self._validate_abbr_round_only_selection():
                return

            # 验证组合分析输出值类别选择
            is_valid, error_message = self._validate_category_selection()
            if not is_valid:
                QMessageBox.warning(self, "提示", error_message)
                return

            # 需要已有组合分析统计结果
            if not hasattr(self.main_window, 'overall_stats') or not self.main_window.overall_stats:
                QMessageBox.warning(self, "提示", "请先进行组合分析，获取最优结果后再进行三次分析！")
                return

            # 获取组合分析次数
            analysis_count = self.analysis_count_spin.value()

            # 结束日期与开始日期（同二次分析）
            end_date = self.main_window.date_picker.date().toString("yyyy-MM-dd")
            workdays = getattr(self.main_window.init, 'workdays_str', None)
            if not workdays:
                QMessageBox.warning(self, "数据错误", "没有可用的日期范围，请先上传数据文件！")
                return
    
            try:
                end_date_idx = workdays.index(end_date)
                start_date_idx = end_date_idx - (analysis_count - 1)
                if start_date_idx < 0:
                    QMessageBox.warning(self, "数据错误", f"组合分析次数 {analysis_count} 超出可用日期范围！\n当前结束日期索引: {end_date_idx}，需要开始日期索引: {start_date_idx}")
                    return
                start_date = workdays[start_date_idx]
            except ValueError:
                QMessageBox.warning(self, "日期错误", f"结束日期 {end_date} 不在交易日列表中！")
                return

            # 构建临时控件，用于恢复选择状态与生成特殊参数组合
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
            
            # 恢复选择状态，包括向前参数状态
            if hasattr(self.main_window, 'last_formula_select_state'):
                temp_formula_widget.set_state(self.main_window.last_formula_select_state)
            
            # 确保向前参数状态被正确恢复
            if hasattr(self.main_window, 'forward_param_state'):
                temp_formula_widget.main_window.forward_param_state = self.main_window.forward_param_state

            # 变量排序（优先输出参数）
            sorted_params = get_sorted_params_from_widget(temp_formula_widget)

            output_vars_ordered = [var_name for var_name, _ in sorted_params['output_params']]
            auxiliary_vars_ordered = [var_name for var_name, _ in sorted_params['auxiliary_params']]
            
            # 调试信息：打印获取到的参数
            log_message = f"获取到的输出参数: {output_vars_ordered}"
            print(log_message)
            self.log_three_analysis(log_message)
            log_message = f"获取到的辅助参数: {auxiliary_vars_ordered}"
            print(log_message)
            self.log_three_analysis(log_message)
            
            if not output_vars_ordered and not auxiliary_vars_ordered:
                QMessageBox.warning(self, "提示", "没有选中任何变量进行三次分析！")
                temp_formula_widget.deleteLater()
                return

            # 构建三次分析参数队列（输出参数优先，然后分析辅助参数）
            param_queue = []
            if output_vars_ordered:
                param_queue.extend(output_vars_ordered)
            if auxiliary_vars_ordered:
                param_queue.extend(auxiliary_vars_ordered)
            
            if not param_queue:
                QMessageBox.warning(self, "提示", "没有选中任何变量进行三次分析！")
                temp_formula_widget.deleteLater()
                return
                
            self.three_stage_param_queue = list(param_queue)
            self.three_stage_current_param_idx = 0
            # 选择本轮目标变量
            target_variable = self.three_stage_param_queue[self.three_stage_current_param_idx]
            log_message = f"三次分析目标变量: {self.three_stage_param_queue}"
            print(log_message)
            self.log_three_analysis(log_message)

            # 切换按钮状态：禁用点击分析和二次分析，启用终止分析
            if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
                # 连续分析模式：使用统一的按钮状态管理
                self._set_buttons_enabled(False)
            else:
                # 普通分析模式：使用原有的按钮状态管理
                self.analyze_btn.setEnabled(False)
                self.optimize_btn.setEnabled(False)
                self.three_stage_btn.setEnabled(False)
                self.terminate_btn.setEnabled(True)
                self.auto_three_stage_btn.setEnabled(False)  # 禁用自动三次分析按钮
            
            # 标记进入三次分析模式，并清空上一轮基准
            self.is_three_stage_mode = True
            # 设置主窗口的三次分析标志，用于show_analysis_results的条件判断
            self.main_window.last_analysis_was_three_stage = True
            self.main_window.three_stage_prev_best_value = getattr(self.main_window, 'last_adjusted_value', None)
            # 保存三次分析开始前的last_adjusted_value快照，用于最终判断是否生成操盘方案
            self.three_stage_initial_last_value = getattr(self.main_window, 'last_adjusted_value', None)
            self.three_stage_round_better = None
            self.three_stage_best_top_one = None
            # 维护当前参数名和每参数结果列表
            self.current_three_stage_variable = target_variable
            self.main_window.per_param_result_list = []

            # 跟踪每个参数的最优公式和条件，用于公式回退
            self.three_stage_param_best_formulas = {}
            self.three_stage_param_best_conditions = {}
            # 跟踪每个参数的最优条件，用于导出JSON
            self.best_param_condition_list = []
            # 跟踪全局最优公式，用于后续参数分析
            if hasattr(self.main_window, 'last_component_analysis_top1') and self.main_window.last_component_analysis_top1:
                top1_analysis = self.main_window.last_component_analysis_top1.get('analysis', {})
                if top1_analysis:
                    self.three_stage_current_best_overall_formula = top1_analysis.get('formula', 'if True:\n    result = 0\nelse:\n    result = 0')
                else:
                    self.three_stage_current_best_overall_formula = 'if True:\n    result = 0\nelse:\n    result = 0'
            else:
                print(f"没有last_component_analysis_top1")
                self.three_stage_current_best_overall_formula = 'if True:\n    result = 0\nelse:\n    result = 0'
            
            # 初始化参数特定的基准统计
            # 第一个参数使用当前的overall_stats作为基准
            if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                self.three_stage_param_baseline_stats = self.main_window.overall_stats.copy()
            else:
                self.three_stage_param_baseline_stats = None
            
            # 初始化日志去重集合
            self._logged_no_better_solutions = set()
            # 新增：三次分析完成标识
            self.three_stage_completed = False
            
            # 新增：记录三次分析开始时间
            self.three_stage_start_time = time.time()
            
            # 新增：记录三次分析总公式数量（初始为0，后续累加）
            self.three_stage_total_formulas = 0
            
            # 新增：初始化跳过完成标志
            self.three_stage_skipped_completed = False
            
            # 重置全局三次分析结果，避免被其他三次分析的最优结果占据
            if hasattr(self, 'three_stage_global_top_three'):
                self.three_stage_global_top_three.clear()
            else:
                self.three_stage_global_top_three = []
            print("重置三次分析全局结果列表，准备开始新的三次分析")

            # 1) 生成第一轮公式列表，并打印所有公式
            formula_list = self.generate_first_stage_formulas(target_variable, base_formula=self.three_stage_current_best_overall_formula)
            if not formula_list:
                QMessageBox.warning(self, "提示", "三次分析未生成任何公式！")
                temp_formula_widget.deleteLater()
                return

            # 使用组合分析得到的最优结果的参数组合快照
            # 从top1中获取，如果没有则使用当前生成的
            top1 = getattr(self.main_window, 'last_component_analysis_top1', None)
            if top1 and 'special_params_combinations' in top1:
                # 使用保存的单个参数组合
                single_params = top1['special_params_combinations']
                # 将单个参数组合转换为generate_special_params_combinations期望的格式
                special_params_combinations = [single_params]
                log_message = f"使用组合分析最优结果的参数组合快照：{single_params}"
                print(log_message)
                self.log_three_analysis(log_message)
            else:
                # 如果没有快照，则生成新的参数组合
                special_params_combinations = temp_formula_widget.generate_special_params_combinations()
                log_message = f"未找到参数组合快照，生成了 {len(special_params_combinations)} 个新的特殊参数组合"
                print(log_message)
                self.log_three_analysis(log_message)

            # 清理临时控件
            temp_formula_widget.deleteLater()

            # 记录三次分析必要上下文
            self.three_stage_round_index = 1
            self.three_stage_target_variable = target_variable
            self._three_stage_start_date = start_date
            self._three_stage_end_date = end_date
            self._three_stage_special_params_combinations = special_params_combinations

            # 启动第一轮（异步，完成后在execute_next_analysis中判断是否进入下一轮）
            self._start_three_stage_round(step_divisor=10)
            
        except Exception as e:
            log_message = f"三次分析执行出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
            QMessageBox.critical(self, "错误", f"三次分析执行出错: {e}")
            
            # 恢复按钮状态
            if hasattr(self, 'is_auto_three_stage_mode') and self.is_auto_three_stage_mode:
                # 连续分析模式：使用统一的按钮状态管理
                self._set_buttons_enabled(True)
                self.is_auto_three_stage_mode = False
            else:
                # 普通分析模式：使用原有的按钮状态管理
                self.analyze_btn.setEnabled(True)
                self.terminate_btn.setEnabled(False)
                self.optimize_btn.setEnabled(True)
                self.three_stage_btn.setEnabled(True)
                self.auto_three_stage_btn.setEnabled(True)
        
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

    def _start_three_stage_round(self, step_divisor: int):
        """启动三次分析的某一轮，依据步长除数生成公式并异步执行。"""
        try:
            target_variable = getattr(self, 'three_stage_target_variable', None)
            if not target_variable:
                log_message = "三次分析：缺少目标变量"
                print(log_message)
                self.log_three_analysis(log_message)
                return
            start_date = getattr(self, '_three_stage_start_date', None)
            end_date = getattr(self, '_three_stage_end_date', None)
            special_params_combinations = getattr(self, '_three_stage_special_params_combinations', [])

            # 生成当前轮公式，使用全局最优公式作为基础
            base_formula = getattr(self, 'three_stage_current_best_overall_formula', None)
            if not base_formula:
                base_formula = 'if True:\n    result = 0\nelse:\n    result = 0'
            
            # 开始新轮次时，清空日志去重集合
            if hasattr(self, '_logged_no_better_solutions'):
                self._logged_no_better_solutions.clear()
            
            formula_list = self.generate_first_stage_formulas(target_variable, step_divisor=step_divisor, base_formula=base_formula)
            if not formula_list:
                log_message = f"三次分析：第{getattr(self, 'three_stage_round_index', '?')}次未生成公式"
                print(log_message)
                self.log_three_analysis(log_message)
                # 如果没有生成公式，跳过当前参数或完成分析
                self._skip_to_next_parameter_or_complete()
            
            # 新增：累加三次分析总公式数量
            if hasattr(self, 'three_stage_total_formulas'):
                self.three_stage_total_formulas += len(formula_list)
            else:
                self.three_stage_total_formulas = len(formula_list)
            # 计算具体步长值 - 从overall_stats中获取当前变量的统计值
            target_variable = getattr(self, 'current_three_stage_variable', 'unknown')
            overall_stats = getattr(self.main_window, 'overall_stats', {})
            max_key = f"{target_variable}_max"
            min_key = f"{target_variable}_min"
            max_value = overall_stats.get(max_key, 0)
            min_value = overall_stats.get(min_key, 0)
            abs_max = max(abs(max_value), abs(min_value))
            actual_step = int(abs_max / step_divisor) if step_divisor > 0 else 1
            log_message = f"三次分析-目标参数{target_variable}第{getattr(self, 'three_stage_round_index', '?')}次 下限={min_value} 上限={max_value} 步长={actual_step} 生成的全部公式:"
            print(log_message)
            self.log_three_analysis(log_message)
            for idx, f in enumerate(formula_list, 1):
                formula_message = f"  [{idx}] {f['formula']}"
                print(formula_message)
                self.log_three_analysis(formula_message)

            # 启动该轮组合分析
            self.main_window.component_analysis_formula_list = formula_list
            self.main_window.component_analysis_special_params_combinations = special_params_combinations
            self.analysis_terminated = False
            log_message = f"执行三次分析第{getattr(self, 'three_stage_round_index', '?')}次"
            print(log_message)
            self.log_three_analysis(log_message)
            
            # 启动组合分析
            self.execute_component_analysis(formula_list, special_params_combinations, start_date, end_date)
            
        except Exception as e:
            log_message = f"启动三次分析某一轮出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
    
    def _skip_to_next_parameter_or_complete(self):
        """跳过当前参数或完成三次分析"""
        try:
            queue = getattr(self, 'three_stage_param_queue', [])
            idx = getattr(self, 'three_stage_current_param_idx', 0)
            
            if idx + 1 < len(queue):
                # 还有下一个参数，切换到下一个参数
                self.three_stage_current_param_idx = idx + 1
                next_var = queue[self.three_stage_current_param_idx]
                self.current_three_stage_variable = next_var
                self.three_stage_target_variable = next_var
                self.three_stage_round_index = 1
                
                # 切换到新参数时，清空日志去重集合
                if hasattr(self, '_logged_no_better_solutions'):
                    self._logged_no_better_solutions.clear()
                
                # 新参数直接使用当前的overall_stats作为基准
                if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                    self.three_stage_param_baseline_stats = self.main_window.overall_stats.copy()
                else:
                    print("没有overall_stats")
                    self.three_stage_param_baseline_stats = None
                
                log_message = f"【跳过】参数{queue[idx]}（无统计值），切换到下一个参数：{next_var}"
                print(log_message)
                self.log_three_analysis(log_message)
                
                # 启动下一个参数的第一轮分析
                self._start_three_stage_round(step_divisor=10)
            else:
                # 这是最后一个参数，完成三次分析
                log_message = f"【跳过】最后一个参数{queue[idx]}（无统计值），完成三次分析"
                print(log_message)
                self.log_three_analysis(log_message)
                # 设置跳过完成标志，防止重复调用
                self.three_stage_skipped_completed = True
                self._complete_three_stage_analysis()
                # 直接返回，防止主线程继续执行导致重复调用
                return
        except Exception as e:
            log_message = f"跳过参数时出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
            # 出错时也尝试完成分析
            self._complete_three_stage_analysis()
            # 直接返回，防止主线程继续执行导致重复调用
            return
    
    def _complete_three_stage_analysis(self):
        """完成三次分析"""
        try:
            # 设置三次分析完成标识
            self.three_stage_completed = True
            # 保持跳过完成标志，不要重置，防止重复调用
            # self.three_stage_skipped_completed = False
            
            # 计算三次分析总耗时
            if hasattr(self, 'three_stage_start_time'):
                three_stage_total_time = time.time() - self.three_stage_start_time
                if three_stage_total_time < 60:
                    three_stage_time_str = f"{three_stage_total_time:.1f}秒"
                elif three_stage_total_time < 3600:
                    minutes = int(three_stage_total_time // 60)
                    seconds = int(three_stage_total_time % 60)
                    three_stage_time_str = f"{minutes}分{seconds}秒"
                else:
                    hours = int(three_stage_total_time // 3600)
                    minutes = int((three_stage_total_time % 3600) // 60)
                    three_stage_time_str = f"{hours}小时{minutes}分"
                
                # 保存三次分析统计信息到主窗口
                self.main_window.last_three_stage_total_elapsed_time = three_stage_time_str
                self.main_window.last_three_stage_total_formulas = getattr(self, 'three_stage_total_formulas', 0)
            else:
                three_stage_time_str = "未知"
                self.main_window.last_three_stage_total_elapsed_time = three_stage_time_str
                self.main_window.last_three_stage_total_formulas = getattr(self, 'three_stage_total_formulas', 0)
            
            # 同步三次分析关键状态到主窗口，便于程序重启后继续导出
            if hasattr(self, 'three_stage_best_top_one'):
                self.main_window.three_stage_best_top_one = self.three_stage_best_top_one
            if hasattr(self, 'three_stage_param_best_conditions'):
                self.main_window.three_stage_param_best_conditions = self.three_stage_param_best_conditions
            if hasattr(self, 'best_param_condition_list'):
                self.main_window.best_param_condition_list = self.best_param_condition_list
            if hasattr(self, 'no_better_result_list'):
                self.main_window.no_better_result_list = self.no_better_result_list
            if hasattr(self, 'current_three_stage_variable'):
                self.main_window.current_three_stage_variable = self.current_three_stage_variable
            
            total_conditions = len(self.best_param_condition_list) + len(self.no_better_result_list)
            print(f"三次分析完成，总共记录了{len(self.best_param_condition_list)}个参数的最优条件，{len(self.no_better_result_list)}个参数的无最优结果")
            self.log_three_analysis(f"三次分析完成，总共记录了{len(self.best_param_condition_list)}个参数的最优条件，{len(self.no_better_result_list)}个参数的无最优结果")
            
            # 在展示结果之前，确保所有有最优条件的参数都被记录到best_param_condition_list
            self._ensure_all_best_conditions_recorded()
            
            # 展示最终的分析结果
            self._show_final_three_stage_results()
            
            # 恢复按钮状态
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            self.optimize_btn.setEnabled(True)
            self.three_stage_btn.setEnabled(True)
            self.auto_three_stage_btn.setEnabled(True)
            self.is_three_stage_mode = False
            
        except Exception as e:
            log_message = f"完成三次分析时出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
            # 出错时也要恢复按钮状态
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            self.optimize_btn.setEnabled(True)
            self.three_stage_btn.setEnabled(True)
            self.auto_three_stage_btn.setEnabled(True)
            self.is_three_stage_mode = False
    
    def _ensure_all_best_conditions_recorded(self):
        """确保所有有最优条件的参数都被记录到best_param_condition_list"""
        try:
            if hasattr(self, 'three_stage_param_best_conditions') and self.three_stage_param_best_conditions:
                # 检查哪些参数有最优条件但还没有被记录到best_param_condition_list
                recorded_params = set()
                for condition in self.best_param_condition_list:
                    for param_name in condition.keys():
                        recorded_params.add(param_name)
                
                # 遍历所有有最优条件的参数
                for param_name, best_conditions in self.three_stage_param_best_conditions.items():
                    if param_name not in recorded_params:
                        # 这个参数有最优条件但还没有被记录，现在记录它
                        best_output_value = best_conditions.get('output_value', '未知')
                        
                        # 获取当前参数的median值（从初始overall_stats快照中获取）
                        median_value = ''
                        positive_median_value = ''
                        negative_median_value = ''
                        if hasattr(self, 'three_stage_param_baseline_stats') and self.three_stage_param_baseline_stats:
                            median_key = f'{param_name}_median'
                            positive_median_key = f'{param_name}_positive_median'
                            negative_median_key = f'{param_name}_negative_median'
                            if median_key in self.three_stage_param_baseline_stats:
                                median_value = str(self.three_stage_param_baseline_stats[median_key])
                            if positive_median_key in self.three_stage_param_baseline_stats:
                                positive_median_value = str(self.three_stage_param_baseline_stats[positive_median_key])
                            if negative_median_key in self.three_stage_param_baseline_stats:
                                negative_median_value = str(self.three_stage_param_baseline_stats[negative_median_key])
                        
                        # 获取上下限值
                        lower_value = best_conditions.get('lower', '')
                        upper_value = best_conditions.get('upper', '')
                        if lower_value == '未知':
                            lower_value = ''
                        if upper_value == '未知':
                            upper_value = ''
                        
                        condition_text = f"最优条件为：下限{lower_value}，上限{upper_value}， 组合排序输出值为：{best_output_value}，{param_name}_median：{median_value}，{param_name}_positive_median：{positive_median_value}，{param_name}_negative_median：{negative_median_value}"
                        self.best_param_condition_list.append({param_name: condition_text})
                        print(f"补充记录参数{param_name}的最优条件：{condition_text}")
                        self.log_three_analysis(f"补充记录参数{param_name}的最优条件：{condition_text}")
                
                print(f"补充记录完成后，best_param_condition_list长度：{len(self.best_param_condition_list)}")
                self.log_three_analysis(f"补充记录完成后，best_param_condition_list长度：{len(self.best_param_condition_list)}")
        except Exception as e:
            log_message = f"确保所有最优条件记录时出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
    
    def _show_final_three_stage_results(self):
        """显示三次分析的最终结果"""
        try:
            # 优先使用全局的top_three，如果没有则直接传入空列表
            if hasattr(self, 'three_stage_global_top_three') and self.three_stage_global_top_three:
                print(f"三次分析完成：使用全局top_three展示结果，长度 = {len(self.three_stage_global_top_three)}")
                # 将三次分析的全局top_three保存到主窗口缓存，供tab切换时使用
                self.main_window.cached_component_analysis_results = self.three_stage_global_top_three
                # 标记这是三次分析的结果
                self.main_window.last_analysis_was_three_stage = True
                print(f"三次分析完成：使用全局top_three展示结果，长度 = {len(self.three_stage_global_top_three)}")
                self.show_analysis_results([])  # 传入空列表，让show_analysis_results使用全局top_three
            else:
                # 如果没有全局top_three，直接传入空列表，让show_analysis_results处理
                print("三次分析完成：没有全局top_three，传入空列表")
                self.show_analysis_results([])
            
            # 判断是否生成操盘方案
            final_top_one = None
            try:
                # 使用全局最优结果
                if hasattr(self, 'three_stage_global_top_three') and self.three_stage_global_top_three:
                    final_top_one = self.three_stage_global_top_three[0]  # 取全局最优
                elif hasattr(self, 'three_stage_current_best_top_one') and self.three_stage_current_best_top_one:
                    final_top_one = self.three_stage_current_best_top_one
                
                # 确保使用最优公式的 overall_stats
                if final_top_one:
                    self.main_window.overall_stats = final_top_one.get('overall_stats')
                    
                # 使用分离的方法处理操盘方案生成和提醒
                self._generate_trading_plan_with_notification(
                    final_top_one, 
                    is_three_stage_mode=True, 
                    round_index="最终"
                )
            except Exception as e:
                log_message = f"三次分析完成后生成操盘方案出错: {e}"
                print(log_message)
                self.log_three_analysis(log_message)
                    
        except Exception as e:
            log_message = f"显示三次分析最终结果时出错: {e}"
            print(log_message)
            self.log_three_analysis(log_message)
    
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
            self.optimize_btn.setEnabled(True)
            self.three_stage_btn.setEnabled(True)
            self.auto_three_stage_btn.setEnabled(True)
            return
            
        # 检查三次分析是否已经通过跳过方式完成，如果是则直接返回
        if hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode and getattr(self, 'three_stage_skipped_completed', False):
            print("三次分析已通过跳过方式完成，跳过execute_next_analysis")
            return
            
        if self.current_analysis_index >= self.total_analyses:
            # 所有分析完成
            # 在三次分析模式下，每次都处理结果更新top_three，但只在最后展示表格
            if hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode:
                # 三次分析模式：每次都处理结果更新缓存
                current_top_three = self.process_analysis_results(self.all_analysis_results)
                
                # 维护三次分析全局的top_three
                if not hasattr(self, 'three_stage_global_top_three'):
                    self.three_stage_global_top_three = []
                
                # 将当前轮次的结果合并到全局结果中
                if current_top_three:
                    # 合并当前轮次的结果到全局结果
                    for current_result in current_top_three:
                        # 检查是否已经存在相同的结果（基于adjusted_value和公式）
                        exists = False
                        for global_result in self.three_stage_global_top_three:
                            if (global_result.get('adjusted_value') == current_result.get('adjusted_value') and 
                                global_result.get('analysis', {}).get('formula') == current_result.get('analysis', {}).get('formula')):
                                exists = True
                                break
                        
                        if not exists:
                            self.three_stage_global_top_three.append(current_result)
                    
                    # 按adjusted_value排序，取前3个
                    self.three_stage_global_top_three.sort(key=lambda x: x.get('adjusted_value', 0), reverse=True)
                    self.three_stage_global_top_three = self.three_stage_global_top_three[:3]
                    
                    # 记录全局top_three的更新
                    round_index = getattr(self, 'three_stage_round_index', '?')
                    self.log_three_analysis(f"【三次分析第{round_index}次完成】全局top_three更新:")
                    for i, result in enumerate(self.three_stage_global_top_three):
                        self.log_three_analysis(f"  第{i+1}名: {result.get('adjusted_value', 'N/A')} - {result.get('analysis', {}).get('formula', 'N/A')}")
                
                # 调试：记录当前轮次的top_one信息到日志
                # if self.cached_analysis_results:
                #     current_top_one = self.cached_analysis_results[0]
                #     round_index = getattr(self, 'three_stage_round_index', '?')
                #     self.log_three_analysis(f"【三次分析第{round_index}轮完成】调试信息:")
                #     self.log_three_analysis(f"当前top_one的adjusted_value: {current_top_one.get('adjusted_value', 'N/A')}")
                #     self.log_three_analysis(f"当前top_one的完整内容: {current_top_one}")
            else:
                # 普通分析模式：直接展示结果
                # 标记这是普通分析的结果
                self.main_window.last_analysis_was_three_stage = False
                self.show_analysis_results(self.all_analysis_results)
            
            # 分析全部完成后，检查最优方案是否满足条件
            # 初始化变量，确保在所有情况下都被定义
            new_value = None
            new_value_float = None
            last_value = None
            last_value_float = None
            locked_value = None
            locked_value_float = None
            
            if self.cached_analysis_results:
                top_one = self.cached_analysis_results[0]
                
                # 获取新值和上次分析最优值
                new_value = top_one.get('adjusted_value', None)
                last_value = getattr(self.main_window, 'last_adjusted_value', None)
                locked_value = getattr(self.main_window, 'locked_adjusted_value', None)
                new_value_float = float(new_value) if new_value is not None else None
                last_value_float = float(last_value) if last_value is not None else None
                locked_value_float = float(locked_value) if locked_value is not None else None
                
                # 在三次分析模式下，计算本轮是否优于上一轮，并据此决定是否更新 overall_stats
                if self.is_three_stage_mode:
                    try:
                        prev_best = getattr(self.main_window, 'three_stage_prev_best_value', None)
                        prev_best_float = float(prev_best) if prev_best is not None else None
                    except Exception:
                        prev_best_float = None
                    is_better_this_round = False
                    if new_value_float is not None:
                        if prev_best_float is None:
                            is_better_this_round = True
                        else:
                            try:
                                # 以与展示一致的两位小数为准进行比较，避免浮点微小误差导致等值被判为更差
                                rounded_new = round(float(new_value_float), 2)
                                rounded_prev = round(float(prev_best_float), 2)
                                is_better_this_round = rounded_new >= rounded_prev
                            except Exception:
                                is_better_this_round = new_value_float >= prev_best_float
                    self.three_stage_round_better = is_better_this_round
                    if is_better_this_round:
                        self.main_window.overall_stats = top_one.get('overall_stats')
                        self.main_window.three_stage_prev_best_value = new_value_float
                        # 同步更新参数特定的基准统计，确保后续轮次使用最新的统计值
                        if hasattr(self, 'three_stage_param_baseline_stats'):
                            self.three_stage_param_baseline_stats = top_one.get('overall_stats')
                        # 更新全局最优公式
                        if hasattr(self, 'three_stage_current_best_overall_formula'):
                            self.three_stage_current_best_overall_formula = top_one.get('analysis', {}).get('formula', self.three_stage_current_best_overall_formula)
                        # 处理prev_best_float为None的情况
                        if prev_best_float is not None:
                            log_message = f"本次最优值 {new_value_float:.2f} 不小于上一次最优值 {prev_best_float:.2f}，更新 overall_stats"
                        else:
                            log_message = f"本次最优值 {new_value_float:.2f}，这是第一次分析，更新 overall_stats"
                        print(log_message)
                        self.log_three_analysis(log_message)
                        
                        # 记录更新后的overall_stats内容
                        # if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                        #     stats_log = f"更新后的overall_stats内容: {self.main_window.overall_stats}"
                        #     print(stats_log)
                        #     self.log_three_analysis(stats_log)
                        
                        # 记录更新统计值时候的top_one的公式
                        # try:
                        #     # 先打印top_one的完整结构，用于调试
                        #     print(f"调试：top_one的完整内容: {top_one}")
                        #     self.log_three_analysis(f"调试：top_one的完整内容: {top_one}")
                        #     if top_one and 'analysis' in top_one and 'formula' in top_one['analysis']:
                        #         formula_log = f"更新统计值时候的top_one公式: {top_one['analysis']['formula']}"
                        #         print(formula_log)
                        #         self.log_three_analysis(formula_log)
                        #     else:
                        #         # 如果结构不完整，记录详细信息
                        #         if not top_one:
                        #             debug_log = "调试：top_one为None或空"
                        #         elif 'analysis' not in top_one:
                        #             debug_log = f"调试：top_one中没有analysis字段，top_one的keys: {list(top_one.keys()) if top_one else 'None'}"
                        #         elif 'formula' not in top_one['analysis']:
                        #             debug_log = f"调试：top_one['analysis']中没有formula字段，analysis的keys: {list(top_one['analysis'].keys()) if top_one.get('analysis') else 'None'}"
                        #         else:
                        #             debug_log = "调试：未知原因导致无法获取formula"
                                
                        #         print(debug_log)
                        #         self.log_three_analysis(debug_log)
                        # except Exception as e:
                        #     error_log = f"记录top_one公式时出错: {e}"
                        #     print(error_log)
                        #     self.log_three_analysis(error_log)
                        
                        # 三次分析：记录该参数的最优上下限和公式
                        try:
                            # 直接从当前分析的参数角度提取上下限，而不是依赖formula_idx
                            param_name = getattr(self, 'current_three_stage_variable', '参数')
                            lower_val = upper_val = None
                            
                            # 从当前轮次的公式列表中查找包含当前参数的公式
                            if hasattr(self.main_window, 'component_analysis_formula_list'):
                                for formula_info in self.main_window.component_analysis_formula_list:
                                    if formula_info.get('variable') == param_name:
                                        lower_val = formula_info.get('lower')
                                        upper_val = formula_info.get('upper')
                                        break
                            
                            # 如果没找到，尝试从formula_idx获取（兼容性）
                            if lower_val is None and upper_val is None:
                                formula_idx = top_one.get('analysis', {}).get('formula_idx')
                                if formula_idx is not None:
                                    try:
                                        formula_info = self.main_window.component_analysis_formula_list[int(formula_idx) - 1]
                                        lower_val = formula_info.get('lower')
                                        upper_val = formula_info.get('upper')
                                    except Exception:
                                        pass
                            
                            # 保存当前参数的最优公式和条件
                            if param_name:
                                self.three_stage_param_best_formulas[param_name] = top_one
                                # 获取当前组合排序输出值
                                current_output_value = "未知"
                                if top_one and 'adjusted_value' in top_one:
                                    try:
                                        current_output_value = str(top_one.get('adjusted_value'))
                                    except Exception:
                                        current_output_value = "未知"
                                
                                self.three_stage_param_best_conditions[param_name] = {
                                    'lower': lower_val,
                                    'upper': upper_val,
                                    'round': getattr(self, 'three_stage_round_index', 1),
                                    'output_value': current_output_value
                                }
                                
                                # 记录当前轮次的最优结果到日志
                                try:
                                    if top_one and 'analysis' in top_one and 'formula' in top_one['analysis']:
                                        formula_log = f"参数{param_name}第{getattr(self, 'three_stage_round_index', 1)}次最优公式: {top_one['analysis']['formula']}"
                                        print(formula_log)
                                        self.log_three_analysis(formula_log)
                                except Exception as e:
                                    print(f"记录参数公式到日志时出错: {e}")
                            
                            msg = f"（{param_name}）最优结果：下限：{lower_val}，上限：{upper_val}"
                        except Exception:
                            msg = f"（{getattr(self, 'current_three_stage_variable', '参数')}）最优结果：上限：未知，下限：未知"
                        try:
                            if not hasattr(self.main_window, 'per_param_result_list') or self.main_window.per_param_result_list is None:
                                self.main_window.per_param_result_list = []
                            self.main_window.per_param_result_list.append(msg)
                            print(msg)
                            # 三次分析模式下：仅打印，不弹框，并标注轮次
                            try:
                                round_idx = int(getattr(self, 'three_stage_round_index', 1))
                            except Exception:
                                round_idx = 1
                            round_name = {1: '第一次', 2: '第二次', 3: '第三次'}.get(round_idx, f"第{round_idx}次")
                            log_message = f"三次分析：{round_name} {param_name} 下限：{lower_val}，上限：{upper_val}，有较优方案。上次分析最优值：{prev_best_float}，本次分析最优值：{new_value_float}"
                            print(log_message)
                            self.log_three_analysis(log_message)
                        except Exception:
                            pass
                    else:
                        # 处理prev_best_float为None的情况
                        if prev_best_float is not None:
                            log_message = f"本次最优值 {new_value_float:.2f} 小于上一次最优值 {prev_best_float:.2f}，不更新 overall_stats"
                        else:
                            log_message = f"本次最优值 {new_value_float:.2f}，这是第一次分析，不更新 overall_stats"
                        print(log_message)
                        self.log_three_analysis(log_message)
                        
                        # 记录当前overall_stats内容（未更新）
                        if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                            stats_log = f"当前overall_stats内容（未更新）: {self.main_window.overall_stats}"
                            print(stats_log)
                            self.log_three_analysis(stats_log)
                        
                        # 记录当前top_one的公式（未更新统计值）
                        if top_one and 'analysis' in top_one and 'formula' in top_one['analysis']:
                            formula_log = f"当前top_one公式（未更新统计值）: {top_one['analysis']['formula']}"
                            print(formula_log)
                            self.log_three_analysis(formula_log)
                        
                        # 三次分析：记录没有最优结果
                        try:
                            param_name = getattr(self, 'current_three_stage_variable', '参数')
                            msg = f"（{param_name}）没有最优结果"
                            if not hasattr(self.main_window, 'per_param_result_list') or self.main_window.per_param_result_list is None:
                                self.main_window.per_param_result_list = []
                            self.main_window.per_param_result_list.append(msg)
                            print(msg)
                            # 三次分析模式下：仅打印，不弹框
                            try:
                                # 直接从当前分析的参数角度提取上下限
                                param_name = getattr(self, 'current_three_stage_variable', '参数')
                                lower_val = upper_val = None
                                
                                # 从当前轮次的公式列表中查找包含当前参数的公式
                                if hasattr(self.main_window, 'component_analysis_formula_list'):
                                    for formula_info in self.main_window.component_analysis_formula_list:
                                        if formula_info.get('variable') == param_name:
                                            lower_val = formula_info.get('lower')
                                            upper_val = formula_info.get('upper')
                                            break
                                
                                # 如果没找到，尝试从formula_idx获取（兼容性）
                                if lower_val is None and upper_val is None:
                                    formula_idx = top_one.get('analysis', {}).get('formula_idx')
                                    if formula_idx is not None:
                                        try:
                                            formula_info = self.main_window.component_analysis_formula_list[int(formula_idx) - 1]
                                            lower_val = formula_info.get('lower')
                                            upper_val = formula_info.get('upper')
                                        except Exception:
                                            pass
                                try:
                                    round_idx = int(getattr(self, 'three_stage_round_index', 1))
                                except Exception:
                                    round_idx = 1
                                round_name = {1: '第一次', 2: '第二次', 3: '第三次'}.get(round_idx, f"第{round_idx}次")
                                
                                # 避免重复记录相同的日志信息
                                log_key = f"{param_name}_{round_idx}_{lower_val}_{upper_val}"
                                if not hasattr(self, '_logged_no_better_solutions'):
                                    self._logged_no_better_solutions = set()
                                
                                if log_key not in self._logged_no_better_solutions:
                                    log_message = f"三次分析：{param_name} 下限：{lower_val}，上限：{upper_val}，无较优方案。上次分析最优值：{prev_best_float}，本次分析最优值：{new_value_float}"
                                    print(log_message)
                                    self.log_three_analysis(log_message)
                                    self._logged_no_better_solutions.add(log_key)
                                    
                                    # 记录无最优结果到no_better_result_list，包含详细信息
                                    round_name = {1: '第一次', 2: '第二次', 3: '第三次'}.get(round_idx, f"第{round_idx}次")
                                    
                                    # 获取当前参数的median值（从初始overall_stats快照中获取）
                                    median_value = ''
                                    positive_median_value = ''
                                    negative_median_value = ''
                                    if hasattr(self, 'three_stage_param_baseline_stats') and self.three_stage_param_baseline_stats:
                                        median_key = f'{param_name}_median'
                                        positive_median_key = f'{param_name}_positive_median'
                                        negative_median_key = f'{param_name}_negative_median'
                                        if median_key in self.three_stage_param_baseline_stats:
                                            median_value = str(self.three_stage_param_baseline_stats[median_key])
                                        if positive_median_key in self.three_stage_param_baseline_stats:
                                            positive_median_value = str(self.three_stage_param_baseline_stats[positive_median_key])
                                        if negative_median_key in self.three_stage_param_baseline_stats:
                                            negative_median_value = str(self.three_stage_param_baseline_stats[negative_median_key])
                                    
                                    # 获取上下限值，如果没有则使用空字符串
                                    lower_value = lower_val if lower_val else ''
                                    upper_value = upper_val if upper_val else ''
                                    if lower_value == '未知':
                                        lower_value = ''
                                    if upper_value == '未知':
                                        upper_value = ''
                                    
                                    # 获取当前最优值（使用本次分析最优值，而不是上次分析最优值）
                                    current_best_value = new_value_float if new_value_float is not None else '未知'
                                    if current_best_value != '未知':
                                        current_best_value = f"{current_best_value:.2f}"
                                    
                                    no_better_text = f"无最优条件为：下限{lower_value}，上限{upper_value}， 组合排序输出值为：{current_best_value}，{param_name}_median：{median_value}，{param_name}_positive_median：{positive_median_value}，{param_name}_negative_median：{negative_median_value}"
                                    self.no_better_result_list.append({param_name: no_better_text})
                                    print(f"记录参数{param_name}的无最优结果：{no_better_text}")
                                    self.log_three_analysis(f"记录参数{param_name}的无最优结果：{no_better_text}")
                                
                                # 检查是否是最后一个参数，如果是最后一个参数且没有找到最优结果，则跳过公式回退
                                queue = getattr(self, 'three_stage_param_queue', [])
                                idx = getattr(self, 'three_stage_current_param_idx', 0)
                                is_last_param = (idx + 1 >= len(queue))
                                
                                if is_last_param:
                                    # 最后一个参数没有找到最优结果，跳过公式回退，直接完成分析
                                    log_message = f"三次分析：{param_name} 是最后一个参数且没有找到最优结果，跳过公式回退，直接完成分析"
                                    print(log_message)
                                    self.log_three_analysis(log_message)
                                    
                                    # 直接调用完成分析，避免流程中断
                                    self._complete_three_stage_analysis()
                                    return
                                else:
                                    # 公式回退：如果当前轮次没有找到更优方案，回退到上一轮的最优公式
                                    if param_name and param_name in self.three_stage_param_best_formulas:
                                        # 回退到该参数的最优公式
                                        best_formula = self.three_stage_param_best_formulas[param_name]
                                        best_conditions = self.three_stage_param_best_conditions[param_name]
                                        
                                        # 不要直接覆盖全局overall_stats，而是保存为参数特定的基准
                                        if best_formula.get('overall_stats'):
                                            self.three_stage_param_baseline_stats = best_formula.get('overall_stats')
                                        
                                        # 避免重复记录公式回退日志
                                        fallback_log_key = f"fallback_{param_name}_{round_idx}"
                                        if fallback_log_key not in self._logged_no_better_solutions:
                                            log_message = f"公式回退：{param_name} 回退到第{best_conditions['round']}次的最优公式（下限：{best_conditions['lower']}，上限：{best_conditions['upper']}）"
                                            print(log_message)
                                            self.log_three_analysis(log_message)
                                            self._logged_no_better_solutions.add(fallback_log_key)
                                    else:
                                        # 如果没有该参数的最优公式，回退到上次最优公式（不包含该参数条件）
                                        # 避免重复记录公式回退日志
                                        fallback_log_key = f"fallback_no_formula_{param_name}_{round_idx}"
                                        if fallback_log_key not in self._logged_no_better_solutions:
                                            # 处理prev_best_float为None的情况
                                            if prev_best_float is not None:
                                                log_message = f"公式回退：{param_name} 没有找到最优公式，回退到上次最优公式，上次最优公式值：{prev_best_float:.2f}"
                                            else:
                                                log_message = f"公式回退：{param_name} 没有找到最优公式，这是第一次分析，没有上次最优公式值"
                                            print(log_message)
                                            self.log_three_analysis(log_message)
                                            self._logged_no_better_solutions.add(fallback_log_key)
                                        
                                        # 确保使用全局最优的overall_stats作为基准
                                        if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                                            self.three_stage_param_baseline_stats = self.main_window.overall_stats.copy()
                            except Exception:
                                pass
                        except Exception:
                            pass
                else:
                    # 非三次分析模式按原逻辑直接更新
                    self.main_window.overall_stats = top_one.get('overall_stats')
                
                # 检查是否满足条件
                should_generate = False
                if new_value is not None:
                    try:
                        new_value_float = float(new_value)
                        if new_value_float > 0:
                            should_generate = True
                        else:
                            if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                                QMessageBox.warning(self, "方案无效", f"该组合分析最优方案的输出值 {new_value_float:.2f} 不大于0，此方案无效，不生成操盘方案")
                            should_generate = False
                    except Exception:
                        if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                            QMessageBox.warning(self, "方案无效", "该组合分析最优方案的输出值无效，此方案无效，不生成操盘方案")
                        should_generate = False
                else:
                    if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                        QMessageBox.warning(self, "方案无效", "该组合分析最优方案的输出值为空，此方案无效，不生成操盘方案")
                    should_generate = False
                
                # 如果输出值大于0，进一步判断是否满足百分比要求
                if should_generate:
                    try:
                        better_percent = float(self.only_better_trading_plan_edit.text())
                    except ValueError:
                        better_percent = 0.0
                    
                    # 判断是否大于上次分析最优值
                    if new_value is not None and last_value is not None:
                        try:
                            # 计算需要超过的阈值：上次分析最优值 * (1 + 百分比/100)
                            threshold = last_value_float * (better_percent / 100)
                            should_generate = new_value_float > threshold
                            if not should_generate:
                                # 构建提示信息
                                message = f"该组合分析最优方案的输出值 {new_value_float:.2f} 不大于上次分析最优值 {last_value_float:.2f} 的 {better_percent}% = {threshold:.2f}，此方案无效，不生成操盘方案"
                                
                                # 如果有锁定最优值，也提示是否大于锁定最优值
                                if locked_value_float is not None:
                                    if new_value_float > locked_value_float:
                                        message += f"\n\n但大于锁定最优值 {locked_value_float:.2f}"
                                    else:
                                        message += f"\n\n且不大于锁定最优值 {locked_value_float:.2f}"
                                
                                if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                                    QMessageBox.warning(self, "方案无效", message)
                        except Exception:
                            should_generate = True  # 转换失败时默认生成
                    elif new_value is not None and last_value is None:
                        # 第一次生成时，直接生成
                        should_generate = True
                    else:
                        should_generate = False
                
                # 如果满足所有条件，显示成功提示
                if should_generate:
                    # 处理last_value_float为None的情况
                    if last_value_float is not None:
                        message = f"有最优方案出现！当前最优组合排序输出值：{new_value_float:.2f}，大于上次分析最优值：{last_value_float:.2f} 的 {better_percent}% = {threshold:.2f}"
                    else:
                        message = f"有最优方案出现！当前最优组合排序输出值：{new_value_float:.2f}，这是第一次分析"
                    
                    # 如果有锁定最优值，也提示是否大于锁定最优值
                    if locked_value_float is not None:
                        if new_value_float > locked_value_float:
                            message += f"\n\n且大于锁定最优值 {locked_value_float:.2f}"
                        else:
                            message += f"\n\n但不大于锁定最优值 {locked_value_float:.2f}"
                    
                    if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                        QMessageBox.information(self, "最优方案提示", message)
                
                # 只有在普通模式下才即时生成操盘方案；三次分析模式下推迟到全部轮次结束后生成
                if not self.is_three_stage_mode:
                    if should_generate and self.generate_trading_plan_checkbox.isChecked():
                        self._add_top_result_to_trading_plan(top_one)
                    
                    # 更新锁定最优值
                    if locked_value_float is None or new_value_float > locked_value_float:
                        self.main_window.locked_adjusted_value = new_value_float
                    
                    # 更新显示
                    self._update_last_best_value_display()
                
                # 更新last_adjusted_value（只有在非三次分析模式或找到更优方案时才更新）
                if new_value is not None:
                    try:
                        new_value_float = float(new_value)
                        if not self.is_three_stage_mode or self.three_stage_round_better:
                            # 普通模式：每次都更新；三次分析模式：只有找到更优方案才更新
                            self.main_window.last_adjusted_value = new_value_float
                    except Exception:
                        # 转换失败时，如果last_value为None则设置，否则保持原值
                        if last_value is None:
                            self.main_window.last_adjusted_value = new_value
                    
                    # 更新显示
                    self._update_last_best_value_display()
            else:
                # 在三次分析模式和连续分析模式下，如果没有满足条件的结果，不弹框提示，只记录日志
                if not self.is_three_stage_mode and not getattr(self, 'is_auto_three_stage_mode', False):
                    self.show_analysis_results([])
                    QMessageBox.information(self, "分析完成", "没有满足条件的组合分析结果")
                elif self.is_three_stage_mode:
                    # 三次分析模式：记录到日志，但不弹框
                    log_message = f"三次分析第{getattr(self, 'three_stage_round_index', '?')}次：没有满足条件的组合分析结果"
                    print(log_message)
                    self.log_three_analysis(log_message)
                    
                    # 记录当前参数的无最优结果到no_better_result_list，包含详细信息
                    current_param = getattr(self, 'current_three_stage_variable', '参数')
                    round_name = {1: '第一次', 2: '第二次', 3: '第三次'}.get(getattr(self, 'three_stage_round_index', 1), f"第{getattr(self, 'three_stage_round_index', 1)}次")
                    
                    # 获取当前参数的median值（从初始overall_stats快照中获取）
                    median_value = ''
                    positive_median_value = ''
                    negative_median_value = ''
                    if hasattr(self, 'three_stage_param_baseline_stats') and self.three_stage_param_baseline_stats:
                        median_key = f'{current_param}_median'
                        positive_median_key = f'{current_param}_positive_median'
                        negative_median_key = f'{current_param}_negative_median'
                        if median_key in self.three_stage_param_baseline_stats:
                            median_value = str(self.three_stage_param_baseline_stats[median_key])
                        if positive_median_key in self.three_stage_param_baseline_stats:
                            positive_median_value = str(self.three_stage_param_baseline_stats[positive_median_key])
                        if negative_median_key in self.three_stage_param_baseline_stats:
                            negative_median_value = str(self.three_stage_param_baseline_stats[negative_median_key])
                    
                    # 获取上下限值，如果没有则使用空字符串
                    lower_value = ''
                    upper_value = ''
                    if hasattr(self.main_window, 'component_analysis_formula_list'):
                        for formula_info in self.main_window.component_analysis_formula_list:
                            if formula_info.get('variable') == current_param:
                                lower_value = formula_info.get('lower', '')
                                upper_value = formula_info.get('upper', '')
                                break
                    
                    if lower_value == '未知':
                        lower_value = ''
                    if upper_value == '未知':
                        upper_value = ''
                    
                    # 获取当前最优值（使用本次分析最优值，而不是从best_conditions中获取）
                    current_best_value = '未知'
                    if new_value is not None:
                        try:
                            new_value_float = float(new_value)
                            current_best_value = f"{new_value_float:.2f}"
                        except (ValueError, TypeError):
                            current_best_value = str(new_value)
                    # 如果new_value不可用，则尝试从best_conditions中获取作为备选
                    elif hasattr(self, 'three_stage_param_best_conditions') and current_param in self.three_stage_param_best_conditions:
                        best_conditions = self.three_stage_param_best_conditions[current_param]
                        if 'output_value' in best_conditions:
                            current_best_value = best_conditions['output_value']
                    
                    no_better_text = f"无最优条件为：下限{lower_value}，上限{upper_value}， 组合排序输出值为：{current_best_value}，{current_param}_median：{median_value}，{current_param}_positive_median：{positive_median_value}，{current_param}_negative_median：{negative_median_value}"
                    self.no_better_result_list.append({current_param: no_better_text})
                    print(f"记录参数{current_param}的无最优结果：{no_better_text}")
                    self.log_three_analysis(f"记录参数{current_param}的无最优结果：{no_better_text}")
                    
                    # 检查是否是最后一个参数，如果是且没有结果，则直接完成分析
                    queue = getattr(self, 'three_stage_param_queue', [])
                    idx = getattr(self, 'three_stage_current_param_idx', 0)
                    is_last_param = (idx + 1 >= len(queue))
                    
                    if is_last_param:
                        log_message = f"三次分析：{current_param} 是最后一个参数且没有满足条件的结果，直接完成分析"
                        print(log_message)
                        self.log_three_analysis(log_message)
                        
                        # 直接调用完成分析，避免流程中断
                        self._complete_three_stage_analysis()
                        return
                elif getattr(self, 'is_auto_three_stage_mode', False):
                    # 连续分析模式：记录到日志，但不弹框
                    log_message = "连续分析组合分析阶段：没有满足条件的组合分析结果"
                    print(log_message)
                    self.log_three_analysis(log_message)

            # 三次分析轮次推进（对当前参数）
            if self.is_three_stage_mode:
                try:
                    current_round = getattr(self, 'three_stage_round_index', 1)
                    # 只有在轮次小于3且满足条件时才继续递增
                    if current_round == 1 and self.three_stage_round_better:
                        self.three_stage_round_index = 2
                        self._start_three_stage_round(step_divisor=20)
                        return
                    if current_round == 2 and self.three_stage_round_better:
                        self.three_stage_round_index = 3
                        self._start_three_stage_round(step_divisor=40)
                        return
                except Exception as e:
                    log_message = f"三次分析轮次推进出错: {e}"
                    print(log_message)
                    self.log_three_analysis(log_message)
                # 当前参数三轮已结束：更新该参数的全局最优记录（用于后续参数切换时的基准）
                try:
                    if self.cached_analysis_results:
                        self.three_stage_best_top_one = self.cached_analysis_results[0]
                        # 注意：每一轮的最优结果已经记录到日志中了
                        # 这里只需要更新全局最优记录，用于后续参数切换时的基准
                        
                        # 记录当前参数的最优条件到best_param_condition_list
                        current_param = getattr(self, 'current_three_stage_variable', '未知参数')
                        if current_param in self.three_stage_param_best_conditions:
                            best_conditions = self.three_stage_param_best_conditions[current_param]
                            # 直接从best_conditions中获取输出值
                            best_output_value = best_conditions.get('output_value', '未知')
                            
                            # 获取当前参数的median值（从初始overall_stats快照中获取）
                            median_value = ''
                            positive_median_value = ''
                            negative_median_value = ''
                            if hasattr(self, 'three_stage_param_baseline_stats') and self.three_stage_param_baseline_stats:
                                median_key = f'{current_param}_median'
                                positive_median_key = f'{current_param}_positive_median'
                                negative_median_key = f'{current_param}_negative_median'
                                if median_key in self.three_stage_param_baseline_stats:
                                    median_value = str(self.three_stage_param_baseline_stats[median_key])
                                if positive_median_key in self.three_stage_param_baseline_stats:
                                    positive_median_value = str(self.three_stage_param_baseline_stats[positive_median_key])
                                if negative_median_key in self.three_stage_param_baseline_stats:
                                    negative_median_value = str(self.three_stage_param_baseline_stats[negative_median_key])
                            
                            # 获取上下限值，如果没有则使用空字符串
                            lower_value = best_conditions.get('lower', '')
                            upper_value = best_conditions.get('upper', '')
                            if lower_value == '未知':
                                lower_value = ''
                            if upper_value == '未知':
                                upper_value = ''
                            
                            condition_text = f"最优条件为：下限{lower_value}，上限{upper_value}， 组合排序输出值为：{best_output_value}，{current_param}_median：{median_value}，{current_param}_positive_median：{positive_median_value}，{current_param}_negative_median：{negative_median_value}"
                            self.best_param_condition_list.append({current_param: condition_text})
                            print(f"记录参数{current_param}的最优条件：{condition_text}")
                            self.log_three_analysis(f"记录参数{current_param}的最优条件：{condition_text}")
                except Exception:
                    pass
                
                # 切换到下一个参数（若有）
                try:
                    queue = getattr(self, 'three_stage_param_queue', [])
                    idx = getattr(self, 'three_stage_current_param_idx', 0)
                    if idx + 1 < len(queue):
                        # 准备下一参数的第一轮
                        self.three_stage_current_param_idx = idx + 1
                        next_var = queue[self.three_stage_current_param_idx]
                        self.current_three_stage_variable = next_var
                        self.three_stage_target_variable = next_var
                        self.three_stage_round_index = 1
                        # 基准值：优先使用上一参数的最优值，其次使用全局最优值
                        prev_param_best = None
                        if self.three_stage_best_top_one:
                            try:
                                prev_param_best = float(self.three_stage_best_top_one.get('adjusted_value', 0))
                            except Exception:
                                pass
                        
                        # 如果当前参数没有改善整体最优值，从其条件中移除该参数的条件
                        if hasattr(self, 'three_stage_current_best_overall_formula') and not self.three_stage_round_better:
                            # 移除未改善参数的条件
                            self.three_stage_current_best_overall_formula = self._modify_formula_for_variable(
                                self.three_stage_current_best_overall_formula, 
                                self.current_three_stage_variable, 
                                None, 
                                None
                            )
                        
                        # 注意：不再重置 three_stage_prev_best_value，保持全局最优值
                        self.three_stage_round_better = None
                        
                        # 切换到新参数时，清空日志去重集合
                        if hasattr(self, '_logged_no_better_solutions'):
                            self._logged_no_better_solutions.clear()
                        
                        # 新参数直接使用当前的overall_stats作为基准
                        # 在三次分析过程中，如果有较优结果，overall_stats会自动更新
                        if hasattr(self.main_window, 'overall_stats') and self.main_window.overall_stats:
                            self.three_stage_param_baseline_stats = self.main_window.overall_stats.copy()
                        else:
                            print("没有overall_stats")
                            self.three_stage_param_baseline_stats = None
                        
                        self._start_three_stage_round(step_divisor=10)
                        return
                except Exception as e:
                    log_message = f"三次分析切换参数出错: {e}"
                    print(log_message)
                    self.log_three_analysis(log_message)
                
                # 检查是否是最后一个参数的最后一轮
                queue = getattr(self, 'three_stage_param_queue', [])
                idx = getattr(self, 'three_stage_current_param_idx', 0)
                is_last_param = (idx + 1 >= len(queue))
                current_round = getattr(self, 'three_stage_round_index', 1)
                
                # 只有在最后一个参数的第三轮完成时才设置三次分析完成标识
                if is_last_param and current_round >= 3:
                    # 检查是否已经通过跳过方式完成，避免重复调用
                    if not getattr(self, 'three_stage_skipped_completed', False):
                        # 这是最后一个参数的最后一轮，完成三次分析
                        print(f"这是最后一个参数的最后一轮，完成三次分析, current_round: {current_round}")
                        # 设置跳过完成标志，防止重复调用
                        self.three_stage_skipped_completed = True
                        self._complete_three_stage_analysis()
                    else:
                        print("三次分析已通过跳过方式完成，跳过重复调用")

            # 恢复按钮状态（三次分析结束或普通模式）
            # 在三次分析模式下，只有在真正完成时才恢复按钮状态
            if not (hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode and not self.three_stage_completed):
                self.analyze_btn.setEnabled(True)
                self.terminate_btn.setEnabled(False)
                self.optimize_btn.setEnabled(True)
                self.three_stage_btn.setEnabled(True)  # 恢复三次分析按钮
                self.auto_three_stage_btn.setEnabled(True)  # 恢复连续分析按钮
                self.is_three_stage_mode = False
            
            # 检查是否有回调函数需要执行（用于连续分析模式）
            if hasattr(self, 'analysis_completed_callback') and self.analysis_completed_callback:
                callback = self.analysis_completed_callback
                self.analysis_completed_callback = None  # 清除回调，避免重复执行
                print("组合分析完成，执行回调：开始三次分析")
                callback()  # 执行三次分析
                return
            
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
        # 获取特殊参数组合，包含14个参数（8个基础参数 + 6个创新高/创新低参数）
        param_combination = self.special_params_combinations[param_idx]
        
        # 检查参数组合的格式，支持字典和元组/列表两种格式
        if isinstance(param_combination, dict):
            # 字典格式：直接从字典中获取值
            width = param_combination.get('width', 30)
            op_days = param_combination.get('op_days', 5)
            increment_rate = param_combination.get('increment_rate', 0.0)
            after_gt_end_ratio = param_combination.get('after_gt_end_ratio', 0.0)
            after_gt_start_ratio = param_combination.get('after_gt_start_ratio', 0.0)
            stop_loss_inc_rate = param_combination.get('stop_loss_inc_rate', 0.0)
            stop_loss_after_gt_end_ratio = param_combination.get('stop_loss_after_gt_end_ratio', 0.0)
            stop_loss_after_gt_start_ratio = param_combination.get('stop_loss_after_gt_start_ratio', 0.0)
            new_high_low1_start = param_combination.get('new_high_low1_start', 0)
            new_high_low1_range = param_combination.get('new_high_low1_range', 0)
            new_high_low1_span = param_combination.get('new_high_low1_span', 0)
            new_high_low2_start = param_combination.get('new_high_low2_start', 0)
            new_high_low2_range = param_combination.get('new_high_low2_range', 0)
            new_high_low2_span = param_combination.get('new_high_low2_span', 0)
        else:
            # 元组/列表格式：使用解包（向后兼容）
            width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio, new_high_low1_start, new_high_low1_range, new_high_low1_span, new_high_low2_start, new_high_low2_range, new_high_low2_span = param_combination
        
        # 根据第二组创新高/创新低flag的勾选情况决定width值
        # 如果有勾选第二组，则使用new_high_low2_start作为width
        if (self.main_window.new_before_high2_flag_checkbox.isChecked() or 
            self.main_window.new_after_high2_flag_checkbox.isChecked() or 
            self.main_window.new_before_low2_flag_checkbox.isChecked() or 
            self.main_window.new_after_low2_flag_checkbox.isChecked()):
            width = new_high_low2_start
            # 更新主界面width控件值为当前使用的width值
            self.main_window.width_spin.setValue(width)
        else:
            # 没有勾选第二组，检查解包得到的width是否有效
            if width <= 0:
                # 如果解包得到的width无效，使用主界面控件值
                width = self.main_window.width_spin.value()
            # 更新主界面width控件值为当前使用的width值
            self.main_window.width_spin.setValue(width)
 
        self.main_window.inc_rate_edit.setText(str(increment_rate))
        self.main_window.after_gt_end_edit.setText(str(after_gt_end_ratio))
        self.main_window.after_gt_prev_edit.setText(str(after_gt_start_ratio))
        self.main_window.stop_loss_inc_rate_edit.setText(str(stop_loss_inc_rate))
        self.main_window.stop_loss_after_gt_end_edit.setText(str(stop_loss_after_gt_end_ratio))
        self.main_window.stop_loss_after_gt_start_edit.setText(str(stop_loss_after_gt_start_ratio))

        # 打印当前执行的公式和参数
        print("正在执行分析，请不要切换界面导致分析中断...")
        print(f"\n{'='*80}")
        
        # 如果是三次分析模式，显示轮次和参数信息
        if hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode:
            round_index = getattr(self, 'three_stage_round_index', '?')
            target_variable = getattr(self, 'three_stage_target_variable', '?')
            # 获取参数类型和序号信息
            # 使用正确的方法判断参数类型，而不是简单的队列分割
            target_variable_type = "未知"
            if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
                # 检查是否为输出参数（在abbr_round_map中的变量）
                from function.stock_functions import get_abbr_round_map
                output_vars = set(get_abbr_round_map().values())
                if target_variable in output_vars:
                    target_variable_type = "输出参数"
                else:
                    target_variable_type = "辅助参数"
            elif hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                # 检查向前参数
                from function.stock_functions import get_abbr_round_map, get_abbr_map
                output_vars = set(get_abbr_round_map().values())
                abbr_vars = set(get_abbr_map().values())
                if target_variable in output_vars:
                    target_variable_type = "输出参数"
                elif target_variable in abbr_vars:
                    target_variable_type = "辅助参数"
            target_variable_index = getattr(self, 'three_stage_current_param_idx', 0) + 1
            total_params = len(getattr(self, 'three_stage_param_queue', []))
            
            # 获取当前参数的排序值
            sort_value = "未知"
            # 先检查last_formula_select_state（普通参数）
            if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
                if target_variable in self.main_window.last_formula_select_state:
                    var_state = self.main_window.last_formula_select_state[target_variable]
                    if 'sort' in var_state:
                        sort_value = var_state['sort']
            # 再检查forward_param_state（向前参数）
            if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                if target_variable in self.main_window.forward_param_state:
                    var_state = self.main_window.forward_param_state[target_variable]
                    if 'sort' in var_state:
                        sort_value = var_state['sort']
            
            print(f"【三次分析第{round_index}次】参数{target_variable_index}/{total_params}：{target_variable}（{target_variable_type}）排序值：{sort_value}")
        
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
        
        # 获取创新高/创新低类型
        new_high_low1_type, new_high_low2_type = self._get_new_high_low_types()
        
        print(f"  {new_high_low1_type}开始日期距结束日期天数: {new_high_low1_start}")
        print(f"  {new_high_low1_type}日期范围: {new_high_low1_range}")
        print(f"  {new_high_low1_type}展宽期天数: {new_high_low1_span}")
        print(f"  {new_high_low2_type}开始日期距结束日期天数: {new_high_low2_start}")
        print(f"  {new_high_low2_type}日期范围: {new_high_low2_range}")
        print(f"  {new_high_low2_type}展宽期天数: {new_high_low2_span}")
        print(f"{'='*80}")
        # 显示当前进度
        progress_msg = f"正在执行分析，请不要切换界面导致分析中断...\n"
        
        # 如果是三次分析模式，显示轮次和参数信息
        if hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode:
            round_index = getattr(self, 'three_stage_round_index', '?')
            target_variable = getattr(self, 'three_stage_target_variable', '?')
            # 获取参数类型和序号信息
            # 使用正确的方法判断参数类型，而不是简单的队列分割
            target_variable_type = "未知"
            if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
                # 检查是否为输出参数（在abbr_round_map中的变量）
                from function.stock_functions import get_abbr_round_map
                output_vars = set(get_abbr_round_map().values())
                if target_variable in output_vars:
                    target_variable_type = "输出参数"
                else:
                    target_variable_type = "辅助参数"
            elif hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                # 检查向前参数
                from function.stock_functions import get_abbr_round_map, get_abbr_map
                output_vars = set(get_abbr_round_map().values())
                abbr_vars = set(get_abbr_map().values())
                if target_variable in output_vars:
                    target_variable_type = "输出参数"
                elif target_variable in abbr_vars:
                    target_variable_type = "辅助参数"
            target_variable_index = getattr(self, 'three_stage_current_param_idx', 0) + 1
            total_params = len(getattr(self, 'three_stage_param_queue', []))
            
            # 获取当前参数的排序值
            sort_value = "未知"
            # 先检查last_formula_select_state（普通参数）
            if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
                if target_variable in self.main_window.last_formula_select_state:
                    var_state = self.main_window.last_formula_select_state[target_variable]
                    if 'sort' in var_state:
                        sort_value = var_state['sort']
            # 再检查forward_param_state（向前参数）
            if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                if target_variable in self.main_window.forward_param_state:
                    var_state = self.main_window.forward_param_state[target_variable]
                    if 'sort' in var_state:
                        sort_value = var_state['sort']
            
            progress_msg += f"【三次分析第{round_index}次】参数{target_variable_index}/{total_params}：{target_variable}（{target_variable_type}）排序值：{sort_value}\n"
        
        progress_msg += f"正在执行第 {self.current_analysis_index + 1}/{self.total_analyses} 次分析...\n"
        progress_msg += f"公式组合 {formula_idx + 1}/{len(self.formula_list)}\n"
        progress_msg += f"{formula}\n"
        progress_msg += f"排序方式: {sort_mode}\n"
        progress_msg += f"参数组合 {param_idx + 1}/{len(self.special_params_combinations)}\n"
        
        progress_msg += f"日期宽度={width}, 操作天数={op_days}, 递增值={increment_rate}, 后值大于结束值比例={after_gt_end_ratio}, 后值大于开始值比例={after_gt_start_ratio}, 止损递增值={stop_loss_inc_rate}, 止损后值大于结束值比例={stop_loss_after_gt_end_ratio}, 止损后值大于开始值比例={stop_loss_after_gt_start_ratio}, {new_high_low1_type}开始日期距结束日期天数={new_high_low1_start}, {new_high_low1_type}日期范围={new_high_low1_range}, {new_high_low1_type}展宽期天数={new_high_low1_span}, {new_high_low2_type}开始日期距结束日期天数={new_high_low2_start}, {new_high_low2_type}日期范围={new_high_low2_range}, {new_high_low2_type}展宽期天数={new_high_low2_span}"
        self.show_message(progress_msg)
        
        try:
            # 设置当前公式
            self.main_window.last_formula_expr = formula
            
            # 执行组合分析专用方法，直接传递参数
            result = self._execute_component_analysis_single(formula, width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio, sort_mode, new_high_low1_start, new_high_low1_range, new_high_low1_span, new_high_low2_start, new_high_low2_range, new_high_low2_span)
            
            # 再次检查是否被终止
            if self.analysis_terminated:
                return
            
            if result and not result.get('error', False):
                # 直接从result中获取valid_items用于计算统计结果
                merged_results = result.get('dates', {}) if result else {}
                valid_items = [(date_key, stocks) for date_key, stocks in merged_results.items()]
                
                # 调用calculate_analysis_result计算统计结果
                analysis_stats = calculate_analysis_result(valid_items)
                #print(f"_execute_single_analysis result overall_stats: {result.get('overall_stats')}")
                
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
                    'new_high_low1_start': new_high_low1_start,
                    'new_high_low1_range': new_high_low1_range,
                    'new_high_low1_span': new_high_low1_span,
                    'new_high_low2_start': new_high_low2_start,
                    'new_high_low2_range': new_high_low2_range,
                    'new_high_low2_span': new_high_low2_span,
                    'select_count': select_count,  # 添加选股数量
                    'result': result,
                    'valid_items': valid_items,
                    'analysis_stats': analysis_stats,  # 添加统计结果
                    'overall_stats': result.get('overall_stats'),
                    
                    # 添加更多控件值用于参数恢复
                    'start_option': self.main_window.start_option_combo.currentText(),
                    'shift_days': self.main_window.shift_spin.value(),
                    'is_forward': self.main_window.direction_checkbox.isChecked(),
                    'trade_mode': self.main_window.trade_mode_combo.currentText(),
                    'range_value': self.main_window.range_value_edit.text(),
                    'continuous_abs_threshold': self.main_window.continuous_abs_threshold_edit.text(),
                    'valid_abs_sum_threshold': self.main_window.valid_abs_sum_threshold_edit.text(),
                    'n_days': self.main_window.n_days_spin.value(),
                    'n_days_max': self.main_window.n_days_max_spin.value(),
                    'ops_change': self.main_window.ops_change_edit.text(),
                    
                    # 创新高/创新低相关参数
                    'new_before_high_start': self.main_window.new_before_high_start_spin.value(),
                    'new_before_high_range': self.main_window.new_before_high_range_spin.value(),
                    'new_before_high_span': self.main_window.new_before_high_span_spin.value(),
                    'new_before_high_logic': self.main_window.new_before_high_logic_combo.currentText(),
                    'new_before_high2_start': self.main_window.new_before_high2_start_spin.value(),
                    'new_before_high2_range': self.main_window.new_before_high2_range_spin.value(),
                    'new_before_high2_span': self.main_window.new_before_high2_span_spin.value(),
                    'new_before_high2_logic': self.main_window.new_before_high2_logic_combo.currentText(),
                    'new_after_high_start': self.main_window.new_after_high_start_spin.value(),
                    'new_after_high_range': self.main_window.new_after_high_range_spin.value(),
                    'new_after_high_span': self.main_window.new_after_high_span_spin.value(),
                    'new_after_high_logic': self.main_window.new_after_high_logic_combo.currentText(),
                    'new_after_high2_start': self.main_window.new_after_high2_start_spin.value(),
                    'new_after_high2_range': self.main_window.new_after_high2_range_spin.value(),
                    'new_after_high2_span': self.main_window.new_after_high2_span_spin.value(),
                    'new_after_high2_logic': self.main_window.new_after_high2_logic_combo.currentText(),
                    'new_before_low_start': self.main_window.new_before_low_start_spin.value(),
                    'new_before_low_range': self.main_window.new_before_low_range_spin.value(),
                    'new_before_low_span': self.main_window.new_before_low_span_spin.value(),
                    'new_before_low_logic': self.main_window.new_before_low_logic_combo.currentText(),
                    'new_before_low2_start': self.main_window.new_before_low2_start_spin.value(),
                    'new_before_low2_range': self.main_window.new_before_low2_range_spin.value(),
                    'new_before_low2_span': self.main_window.new_before_low2_span_spin.value(),
                    'new_before_low2_logic': self.main_window.new_before_low2_logic_combo.currentText(),
                    'new_after_low_start': self.main_window.new_after_low_start_spin.value(),
                    'new_after_low_range': self.main_window.new_after_low_range_spin.value(),
                    'new_after_low_span': self.main_window.new_after_low_span_spin.value(),
                    'new_after_low_logic': self.main_window.new_after_low_logic_combo.currentText(),
                    'new_after_low2_start': self.main_window.new_after_low2_start_spin.value(),
                    'new_after_low2_range': self.main_window.new_after_low2_range_spin.value(),
                    'new_after_low2_span': self.main_window.new_after_low2_span_spin.value(),
                    'new_after_low2_logic': self.main_window.new_after_low2_logic_combo.currentText(),
                    
                    # 创新高/创新低勾选状态
                    'new_before_high_flag': self.main_window.new_before_high_flag_checkbox.isChecked(),
                    'new_before_high2_flag': self.main_window.new_before_high2_flag_checkbox.isChecked(),
                    'new_after_high_flag': self.main_window.new_after_high_flag_checkbox.isChecked(),
                    'new_after_high2_flag': self.main_window.new_after_high2_flag_checkbox.isChecked(),
                    'new_before_low_flag': self.main_window.new_before_low_flag_checkbox.isChecked(),
                    'new_before_low2_flag': self.main_window.new_before_low2_flag_checkbox.isChecked(),
                    'new_after_low_flag': self.main_window.new_after_low_flag_checkbox.isChecked(),
                    'new_after_low2_flag': self.main_window.new_after_low2_flag_checkbox.isChecked(),

                    # 组合分析次数
                    'component_analysis_count': self.analysis_count_spin.value(),

                    # 操作值表达式
                    'expr': getattr(self.main_window, 'last_expr', '')
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
    
    def _execute_component_analysis_single(self, formula, width, op_days, increment_rate, after_gt_end_ratio, after_gt_start_ratio, stop_loss_inc_rate, stop_loss_after_gt_end_ratio, stop_loss_after_gt_start_ratio, sort_mode, new_high_low1_start=0, new_high_low1_range=0, new_high_low1_span=0, new_high_low2_start=0, new_high_low2_range=0, new_high_low2_span=0):
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

        profit_type = getattr(self.main_window, 'last_profit_type', 'INC')
        loss_type = getattr(self.main_window, 'last_loss_type', 'INC')
        
        # 准备创新高/创新低参数，保持传递结构一致
        new_high_low_params = {}
        
        # 第1组参数：根据勾选情况决定使用组合分析参数还是主界面控件值
        if self.main_window.new_before_high_flag_checkbox.isChecked():
            # 创前新高1被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_before_high_start': new_high_low1_start,
                'new_before_high_range': new_high_low1_range,
                'new_before_high_span': new_high_low1_span
            })
        
        if self.main_window.new_after_high_flag_checkbox.isChecked():
            # 创后新高1被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_after_high_start': new_high_low1_start,
                'new_after_high_range': new_high_low1_range,
                'new_after_high_span': new_high_low1_span
            })
        
        if self.main_window.new_before_low_flag_checkbox.isChecked():
            # 创前新低1被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_before_low_start': new_high_low1_start,
                'new_before_low_range': new_high_low1_range,
                'new_before_low_span': new_high_low1_span
            })
        
        if self.main_window.new_after_low_flag_checkbox.isChecked():
            # 创后新低1被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_after_low_start': new_high_low1_start,
                'new_after_low_range': new_high_low1_range,
                'new_after_low_span': new_high_low1_span
            })
        
        # 第2组参数：根据勾选情况决定使用组合分析参数还是主界面控件值
        if self.main_window.new_before_high2_flag_checkbox.isChecked():
            # 创前新高2被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_before_high2_start': new_high_low2_start,
                'new_before_high2_range': new_high_low2_range,
                'new_before_high2_span': new_high_low2_span
            })
        
        if self.main_window.new_after_high2_flag_checkbox.isChecked():
            # 创后新高2被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_after_high2_start': new_high_low2_start,
                'new_after_high2_range': new_high_low2_range,
                'new_after_high2_span': new_high_low2_span
            })
        
        if self.main_window.new_before_low2_flag_checkbox.isChecked():
            # 创前新低2被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_before_low2_start': new_high_low2_start,
                'new_before_low2_range': new_high_low2_range,
                'new_before_low2_span': new_high_low2_span
            })
        
        if self.main_window.new_after_low2_flag_checkbox.isChecked():
            # 创后新低2被勾选，使用组合分析参数
            new_high_low_params.update({
                'new_after_low2_start': new_high_low2_start,
                'new_after_low2_range': new_high_low2_range,
                'new_after_low2_span': new_high_low2_span
            })

        print(f"new_high_low_params = {new_high_low_params}")
        
        # 调用主窗口的计算方法，直接传递参数
        # 获取比较变量列表
        comparison_vars = []
        if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
            state = self.main_window.last_formula_select_state
            if 'comparison_vars' in state:
                comparison_vars = state['comparison_vars']
                print(f"组合分析从last_formula_select_state获取comparison_vars: {comparison_vars}")
        
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
            stop_loss_after_gt_start_ratio=stop_loss_after_gt_start_ratio,
            comparison_vars=comparison_vars,
            new_high_low_params=new_high_low_params,  # 直接传递
            profit_type=profit_type,
            loss_type=loss_type
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
    
    def process_analysis_results(self, all_analysis_results):
        """
        处理分析结果，提取top_three并更新缓存，但不展示表格
        这个方法专门用于三次分析过程中更新top_three结果
        """
        if not all_analysis_results:
            return None
        print(f"process_analysis_results length = {len(all_analysis_results)}")
        
        # 如果已经是top_three结构，直接使用
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
                    overall_stats = analysis.get('overall_stats')
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
                        # 从summary中提取comprehensive_stop_daily_change和comprehensive_daily_change
                        comprehensive_stop_daily_change = summary.get('comprehensive_stop_daily_change', '')
                        comprehensive_daily_change = summary.get('comprehensive_daily_change', '')
                        
                        # 检查是否满足所有条件
                        conditions_met = True
                        
                        # 条件2：检查comprehensive_daily_change和comprehensive_stop_daily_change是否满足阈值要求
                        try:
                            comprehensive_daily_change_threshold = float(self.comprehensive_daily_change_edit.text())
                        except ValueError:
                            comprehensive_daily_change_threshold = 0.0
                        
                        try:
                            comprehensive_stop_daily_change_threshold = float(self.comprehensive_stop_daily_change_edit.text())
                        except ValueError:
                            comprehensive_stop_daily_change_threshold = 0.0
                        
                        # 检查comprehensive_daily_change是否大于阈值
                        if comprehensive_daily_change != '' and not (isinstance(comprehensive_daily_change, float) and math.isnan(comprehensive_daily_change)):
                            try:
                                comprehensive_daily_change_float = float(comprehensive_daily_change)
                                if comprehensive_daily_change_float <= comprehensive_daily_change_threshold:
                                    conditions_met = False
                                    continue
                            except (ValueError, TypeError):
                                conditions_met = False
                                continue
                        else:
                            conditions_met = False
                            continue
                        
                        # 检查comprehensive_stop_daily_change是否大于阈值
                        if comprehensive_stop_daily_change != '' and not (isinstance(comprehensive_stop_daily_change, float) and math.isnan(comprehensive_stop_daily_change)):
                            try:
                                comprehensive_stop_daily_change_float = float(comprehensive_stop_daily_change)
                                if comprehensive_stop_daily_change_float <= comprehensive_stop_daily_change_threshold:
                                    conditions_met = False
                                    continue
                            except (ValueError, TypeError):
                                conditions_met = False
                                continue
                        else:
                            conditions_met = False
                            continue
                        
                        # 条件3：检查持有率、止盈率、止损率是否满足区间要求
                        try:
                            hold_rate_min = int(self.hold_rate_min_edit.text())
                        except ValueError:
                            hold_rate_min = 0
                        try:
                            hold_rate_max = int(self.hold_rate_max_edit.text())
                        except ValueError:
                            hold_rate_max = 100
                        try:
                            profit_rate_min = int(self.profit_rate_min_edit.text())
                        except ValueError:
                            profit_rate_min = 0
                        try:
                            profit_rate_max = int(self.profit_rate_max_edit.text())
                        except ValueError:
                            profit_rate_max = 100
                        try:
                            loss_rate_min = int(self.loss_rate_min_edit.text())
                        except ValueError:
                            loss_rate_min = 0
                        try:
                            loss_rate_max = int(self.loss_rate_max_edit.text())
                        except ValueError:
                            loss_rate_max = 100
                        
                        # 获取实际的率值
                        actual_hold_rate = summary.get('hold_rate', 0)
                        actual_profit_rate = summary.get('profit_rate', 0)
                        actual_loss_rate = summary.get('loss_rate', 0)
                        
                        # 检查是否满足区间要求
                        if actual_hold_rate < hold_rate_min or actual_hold_rate > hold_rate_max:
                            conditions_met = False
                            continue
                        if actual_profit_rate < profit_rate_min or actual_profit_rate > profit_rate_max:
                            conditions_met = False
                            continue
                        if actual_loss_rate < loss_rate_min or actual_loss_rate > loss_rate_max:
                            conditions_met = False
                            continue
                        
                        # 只有满足所有条件才添加到analysis_with_sum
                        if conditions_met:
                            analysis_with_sum.append({
                                'index': i,
                                'analysis': analysis,
                                'total_sum': total_sum,
                                'valid_count': valid_count,
                                'avg_sum': total_sum / valid_count,
                                'op_days': op_days,
                                'adjusted_value': adjusted_value,
                                'comprehensive_stop_daily_change': comprehensive_stop_daily_change,
                                'comprehensive_daily_change': comprehensive_daily_change,
                                'overall_stats': overall_stats
                            })
                analysis_with_sum.sort(key=lambda x: x['adjusted_value'], reverse=True)
                top_three = analysis_with_sum[:3]

        # 缓存top_three用于保存和恢复
        self.cached_analysis_results = top_three
        self.main_window.cached_component_analysis_results = top_three
        
        # 新增：保存最优top1到主窗口缓存
        if top_three:
            self.main_window.last_component_analysis_top1 = top_three[0]
            # 从最优结果的analysis中提取具体的参数组合，供三次分析使用
            top1_analysis = top_three[0].get('analysis', {})
            if top1_analysis:
                # 提取具体的参数值，构建单个参数组合
                single_params_combination = {
                    'width': top1_analysis.get('width', 30),
                    'op_days': top1_analysis.get('op_days', 5),
                    'increment_rate': top1_analysis.get('increment_rate', 0.0),
                    'after_gt_end_ratio': top1_analysis.get('after_gt_end_ratio', 0.0),
                    'after_gt_start_ratio': top1_analysis.get('after_gt_start_ratio', 0.0),
                    'stop_loss_inc_rate': top1_analysis.get('stop_loss_inc_rate', 0.0),
                    'stop_loss_after_gt_end_ratio': top1_analysis.get('stop_loss_after_gt_end_ratio', 0.0),
                    'stop_loss_after_gt_start_ratio': top1_analysis.get('stop_loss_after_gt_start_ratio', 0.0),
                    'new_high_low1_start': top1_analysis.get('new_high_low1_start', 0),
                    'new_high_low1_range': top1_analysis.get('new_high_low1_range', 0),
                    'new_high_low1_span': top1_analysis.get('new_high_low1_span', 0),
                    'new_high_low2_start': top1_analysis.get('new_high_low2_start', 0),
                    'new_high_low2_range': top1_analysis.get('new_high_low2_range', 0),
                    'new_high_low2_span': top1_analysis.get('new_high_low2_span', 0)
                }
                self.main_window.last_component_analysis_top1['special_params_combinations'] = single_params_combination
                print(f"已从最优结果中提取参数组合：{single_params_combination}")
        
        return top_three

    def show_analysis_results(self, all_analysis_results):
        """
        显示组合分析结果（只输出排序前3的单页表格）
        """
        # 检查是否在组合-连续三次分析模式中，且这是组合分析完成后的调用
        # 在组合-连续三次分析模式中，组合分析完成后只处理结果，不显示表格
        if (getattr(self, 'is_auto_three_stage_mode', False) and 
            not getattr(self.main_window, 'last_analysis_was_three_stage', False)):
            print("组合-连续三次分析模式：组合分析完成，只处理结果，不显示表格")
            if not all_analysis_results:
                self.show_message("没有有效的分析结果")
                return
            
            # 使用process_analysis_results处理结果并获取top_three
            top_three = self.process_analysis_results(all_analysis_results)
            if not top_three:
                return
            
            # 组合分析完成后，更新last_component_analysis_top1
            if top_three:
                self.main_window.last_component_analysis_top1 = top_three[0]
                print(f"组合分析完成，已更新last_component_analysis_top1: {top_three[0].get('adjusted_value', 'N/A')}")
            
            # 只处理结果，不显示表格，直接返回
            print("组合分析结果处理完成，等待三次分析完成后统一显示")
            return
        # 根据最后点击的分析类型来决定展示哪个top_three
        if hasattr(self.main_window, 'last_analysis_was_three_stage') and self.main_window.last_analysis_was_three_stage:
            # 最后点击的是三次分析，优先使用三次分析的全局top_three
            if hasattr(self, 'three_stage_global_top_three') and self.three_stage_global_top_three:
                print(f"最后点击的是三次分析：使用全局top_three，长度 = {len(self.three_stage_global_top_three)}")
                top_three = self.three_stage_global_top_three
            elif not all_analysis_results:
                # 没有传入结果且没有全局top_three
                self.show_message("没有有效的三次分析结果")
                return
            else:
                # 有传入结果，使用传入的结果
                print(f"最后点击的是三次分析，但有传入结果：使用传入结果，长度 = {len(all_analysis_results)}")
                top_three = self.process_analysis_results(all_analysis_results)
                if not top_three:
                    return
        else:
            # 最后点击的是普通分析，使用传入的结果
            if not all_analysis_results:
                self.show_message("没有有效的分析结果")
                return
            print(f"最后点击的是普通分析：show_analysis_results length = {len(all_analysis_results)}")
            
            # 使用process_analysis_results处理结果并获取top_three
            top_three = self.process_analysis_results(all_analysis_results)
            if not top_three:
                return
        
        # 清理旧内容
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 根据分析类型显示不同的统计信息
        if hasattr(self.main_window, 'last_analysis_was_three_stage') and self.main_window.last_analysis_was_three_stage:
            # 三次分析：显示三次分析的统计信息
            three_stage_formulas = getattr(self.main_window, 'last_three_stage_total_formulas', 0)
            three_stage_time = getattr(self.main_window, 'last_three_stage_total_elapsed_time', '未知')
            info_label = QLabel(f"三次分析公式合计: {three_stage_formulas} | 三次分析总耗时: {three_stage_time}")
        else:
            # 普通分析：显示组合分析的统计信息
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
            params_text.append(f"开始日期值选择: {analysis.get('start_option', '')}")
            params_text.append(f"交易方式: {analysis.get('trade_mode', '')}")
            params_text.append(f"操作值: {analysis.get('expr', '')}")
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
            restore_btn.clicked.connect(lambda checked, data=analysis: self.restore_formula_params(data))
            table.setCellWidget(row, 5, restore_btn)
            
        table.resizeColumnsToContents()
        # 设置列宽
        table.setColumnWidth(0, 150)  # 输出值列宽度
        table.setColumnWidth(1, 240)  # 输出参数列宽度
        table.setColumnWidth(2, 300)  # 选股公式列宽度
        table.setColumnWidth(3, 250)  # 选股参数列宽度
        table.setColumnWidth(4, 100)  # 查看详情按钮列宽度
        table.setColumnWidth(5, 100)  # 恢复参数按钮列宽度
        # 自动调整行高以适配多行公式
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)
        self.result_layout.addWidget(table)
        print(f"组合分析完成！输出前三名排序结果。")
        
        # 恢复按钮状态（在三次分析模式下，只有在真正完成时才恢复）
        if not (hasattr(self, 'is_three_stage_mode') and self.is_three_stage_mode and not self.three_stage_completed):
            self.analyze_btn.setEnabled(True)
            self.terminate_btn.setEnabled(False)
            self.optimize_btn.setEnabled(True)
            self.three_stage_btn.setEnabled(True)
            self.auto_three_stage_btn.setEnabled(True)

    def restore_formula_params(self, analysis_data):
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
                    
                    # 清空含逻辑选项
                    if 'logic_check' in widgets:
                        widgets['logic_check'].setChecked(False)
                        print(f"  重置含逻辑选项: {var_name}")
                    
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
                        print(f"  重置比较控件含逻辑选项")
                    print(f"  已重置比较控件")
                
                # 重置forward_param_state中的向前参数控件状态
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    for var_name, var_state in self.main_window.forward_param_state.items():
                        if isinstance(var_state, dict):
                            # 重置enable复选框状态
                            var_state['enable'] = False
                            # 重置round圆框状态
                            var_state['round'] = False
                            # 重置含逻辑选项
                            if 'logic' in var_state:
                                var_state['logic'] = False
                            # 清空上下限值和步长
                            var_state['lower'] = ''
                            var_state['upper'] = ''
                            if 'step' in var_state:
                                var_state['step'] = ''
                            print(f"重置向前参数: {var_name}")
                        elif isinstance(var_state, bool):
                            # 如果只是布尔值，重置为False
                            self.main_window.forward_param_state[var_name] = False
                            print(f"重置向前参数布尔值: {var_name} = False")
                
                # 恢复forward_param_state中的向前参数控件状态
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
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
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*/\s*([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)', formula):
                    var1, var2, lower = m.group(1), m.group(2), m.group(3)
                    comparison_vars.add(var1)
                    comparison_vars.add(var2)
                    print(f"找到比较控件: {var1} / {var2} >= {lower}")
                
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*/\s*([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)', formula):
                    var1, var2, upper = m.group(1), m.group(2), m.group(3)
                    comparison_vars.add(var1)
                    comparison_vars.add(var2)
                    print(f"找到比较控件: {var1} / {var2} <= {upper}")
                
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
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*/\s*([a-zA-Z0-9_]+)\s*>=\s*([\-\d\.]+)', formula):
                    var1, var2, lower = m.group(1), m.group(2), m.group(3)
                    zh_var1 = en2zh.get(var1, var1)
                    zh_var2 = en2zh.get(var2, var2)
                    existing = next((c for c in comparison_configs if c['var1'] == zh_var1 and c['var2'] == zh_var2), None)
                    if existing:
                        existing['lower'] = lower
                    else:
                        comparison_configs.append({'var1': zh_var1, 'lower': lower, 'upper': '', 'var2': zh_var2})
                # <=
                for m in re.finditer(r'([a-zA-Z0-9_]+)\s*/\s*([a-zA-Z0-9_]+)\s*<=\s*([\-\d\.]+)', formula):
                    var1, var2, upper = m.group(1), m.group(2), m.group(3)
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
                
                # 恢复新增的控件值
                # 开始日期值选择
                start_option = analysis_data.get('start_option', '')
                if start_option and hasattr(self.main_window, 'start_option_combo'):
                    try:
                        idx = self.main_window.start_option_combo.findText(start_option)
                        if idx >= 0:
                            self.main_window.start_option_combo.setCurrentIndex(idx)
                            print(f"设置开始日期值选择: {start_option}")
                    except:
                        pass
                
                # 前移天数
                shift_days = analysis_data.get('shift_days', '')
                if shift_days != '' and shift_days is not None and hasattr(self.main_window, 'shift_spin'):
                    try:
                        shift_days_int = int(shift_days)
                        self.main_window.shift_spin.setValue(shift_days_int)
                        print(f"设置前移天数: {shift_days_int}")
                    except:
                        pass
                
                # 是否计算向前
                is_forward = analysis_data.get('is_forward', False)
                if hasattr(self.main_window, 'direction_checkbox'):
                    try:
                        self.main_window.direction_checkbox.setChecked(is_forward)
                        print(f"设置是否计算向前: {is_forward}")
                    except:
                        pass
                
                # 交易方式
                trade_mode = analysis_data.get('trade_mode', '')
                if trade_mode and hasattr(self.main_window, 'trade_mode_combo'):
                    try:
                        idx = self.main_window.trade_mode_combo.findText(trade_mode)
                        if idx >= 0:
                            self.main_window.trade_mode_combo.setCurrentIndex(idx)
                            print(f"设置交易方式: {trade_mode}")
                    except:
                        pass
                
                # 操作涨幅
                ops_change = analysis_data.get('ops_change', '')
                if ops_change and hasattr(self.main_window, 'ops_change_edit'):
                    try:
                        self.main_window.ops_change_edit.setText(str(ops_change))
                        print(f"设置操作涨幅: {ops_change}")
                    except:
                        pass
                
                # 其他参数
                n_days = analysis_data.get('n_days', '')
                if n_days and hasattr(self.main_window, 'n_days_spin'):
                    try:
                        self.main_window.n_days_spin.setValue(int(n_days))
                        print(f"设置n_days: {n_days}")
                    except:
                        pass
                
                n_days_max = analysis_data.get('n_days_max', '')
                if n_days_max and hasattr(self.main_window, 'n_days_max_spin'):
                    try:
                        self.main_window.n_days_max_spin.setValue(int(n_days_max))
                        print(f"设置n_days_max: {n_days_max}")
                    except:
                        pass
                
                range_value = analysis_data.get('range_value', '')
                if range_value and hasattr(self.main_window, 'range_value_edit'):
                    try:
                        self.main_window.range_value_edit.setText(str(range_value))
                        print(f"设置range_value: {range_value}")
                    except:
                        pass
                
                continuous_abs_threshold = analysis_data.get('continuous_abs_threshold', '')
                if continuous_abs_threshold and hasattr(self.main_window, 'continuous_abs_threshold_edit'):
                    try:
                        self.main_window.continuous_abs_threshold_edit.setText(str(continuous_abs_threshold))
                        print(f"设置continuous_abs_threshold: {continuous_abs_threshold}")
                    except:
                        pass

                valid_abs_sum_threshold = analysis_data.get('valid_abs_sum_threshold', '')
                if valid_abs_sum_threshold and hasattr(self.main_window, 'valid_abs_sum_threshold_edit'):
                    try:
                        self.main_window.valid_abs_sum_threshold_edit.setText(str(valid_abs_sum_threshold))
                        print(f"设置valid_abs_sum_threshold: {valid_abs_sum_threshold}")
                    except:
                        pass
                
                # 创新高/创新低相关参数
                new_before_high_start = analysis_data.get('new_before_high_start', '')
                if new_before_high_start and hasattr(self.main_window, 'new_before_high_start_spin'):
                    try:
                        self.main_window.new_before_high_start_spin.setValue(int(new_before_high_start))
                        print(f"设置new_before_high_start: {new_before_high_start}")
                    except:
                        pass
                
                new_before_high_range = analysis_data.get('new_before_high_range', '')
                if new_before_high_range and hasattr(self.main_window, 'new_before_high_range_spin'):
                    try:
                        self.main_window.new_before_high_range_spin.setValue(int(new_before_high_range))
                        print(f"设置new_before_high_range: {new_before_high_range}")
                    except:
                        pass
                
                new_before_high_span = analysis_data.get('new_before_high_span', '')
                if new_before_high_span and hasattr(self.main_window, 'new_before_high_span_spin'):
                    try:
                        self.main_window.new_before_high_span_spin.setValue(int(new_before_high_span))
                        print(f"设置new_before_high_span: {new_before_high_span}")
                    except:
                        pass
                
                new_before_high_logic = analysis_data.get('new_before_high_logic', '')
                if new_before_high_logic and hasattr(self.main_window, 'new_before_high_logic_combo'):
                    try:
                        idx = self.main_window.new_before_high_logic_combo.findText(new_before_high_logic)
                        if idx >= 0:
                            self.main_window.new_before_high_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_before_high_logic: {new_before_high_logic}")
                    except:
                        pass
                
                # 创前新高2参数
                new_before_high2_start = analysis_data.get('new_before_high2_start', '')
                if new_before_high2_start and hasattr(self.main_window, 'new_before_high2_start_spin'):
                    try:
                        self.main_window.new_before_high2_start_spin.setValue(int(new_before_high2_start))
                        print(f"设置new_before_high2_start: {new_before_high2_start}")
                    except:
                        pass
                
                new_before_high2_range = analysis_data.get('new_before_high2_range', '')
                if new_before_high2_range and hasattr(self.main_window, 'new_before_high2_range_spin'):
                    try:
                        self.main_window.new_before_high2_range_spin.setValue(int(new_before_high2_range))
                        print(f"设置new_before_high2_range: {new_before_high2_range}")
                    except:
                        pass
                
                new_before_high2_span = analysis_data.get('new_before_high2_span', '')
                if new_before_high2_span and hasattr(self.main_window, 'new_before_high2_span_spin'):
                    try:
                        self.main_window.new_before_high2_span_spin.setValue(int(new_before_high2_span))
                        print(f"设置new_before_high2_span: {new_before_high2_span}")
                    except:
                        pass
                
                new_before_high2_logic = analysis_data.get('new_before_high2_logic', '')
                if new_before_high2_logic and hasattr(self.main_window, 'new_before_high2_logic_combo'):
                    try:
                        idx = self.main_window.new_before_high2_logic_combo.findText(new_before_high2_logic)
                        if idx >= 0:
                            self.main_window.new_before_high2_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_before_high2_logic: {new_before_high2_logic}")
                    except:
                        pass
                
                # 创后新高1参数
                new_after_high_start = analysis_data.get('new_after_high_start', '')
                if new_after_high_start and hasattr(self.main_window, 'new_after_high_start_spin'):
                    try:
                        self.main_window.new_after_high_start_spin.setValue(int(new_after_high_start))
                        print(f"设置new_after_high_start: {new_after_high_start}")
                    except:
                        pass
                
                new_after_high_range = analysis_data.get('new_after_high_range', '')
                if new_after_high_range and hasattr(self.main_window, 'new_after_high_range_spin'):
                    try:
                        self.main_window.new_after_high_range_spin.setValue(int(new_after_high_range))
                        print(f"设置new_after_high_range: {new_after_high_range}")
                    except:
                        pass
                
                new_after_high_span = analysis_data.get('new_after_high_span', '')
                if new_after_high_span and hasattr(self.main_window, 'new_after_high_span_spin'):
                    try:
                        self.main_window.new_after_high_span_spin.setValue(int(new_after_high_span))
                        print(f"设置new_after_high_span: {new_after_high_span}")
                    except:
                        pass
                
                new_after_high_logic = analysis_data.get('new_after_high_logic', '')
                if new_after_high_logic and hasattr(self.main_window, 'new_after_high_logic_combo'):
                    try:
                        idx = self.main_window.new_after_high_logic_combo.findText(new_after_high_logic)
                        if idx >= 0:
                            self.main_window.new_after_high_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_after_high_logic: {new_after_high_logic}")
                    except:
                        pass
                
                # 创后新高2参数
                new_after_high2_start = analysis_data.get('new_after_high2_start', '')
                if new_after_high2_start and hasattr(self.main_window, 'new_after_high2_start_spin'):
                    try:
                        self.main_window.new_after_high2_start_spin.setValue(int(new_after_high2_start))
                        print(f"设置new_after_high2_start: {new_after_high2_start}")
                    except:
                        pass
                
                new_after_high2_range = analysis_data.get('new_after_high2_range', '')
                if new_after_high2_range and hasattr(self.main_window, 'new_after_high2_range_spin'):
                    try:
                        self.main_window.new_after_high2_range_spin.setValue(int(new_after_high2_range))
                        print(f"设置new_after_high2_range: {new_after_high2_range}")
                    except:
                        pass
                
                new_after_high2_span = analysis_data.get('new_after_high2_span', '')
                if new_after_high2_span and hasattr(self.main_window, 'new_after_high2_span_spin'):
                    try:
                        self.main_window.new_after_high2_span_spin.setValue(int(new_after_high2_span))
                        print(f"设置new_after_high2_span: {new_after_high2_span}")
                    except:
                        pass
                
                new_after_high2_logic = analysis_data.get('new_after_high2_logic', '')
                if new_after_high2_logic and hasattr(self.main_window, 'new_after_high2_logic_combo'):
                    try:
                        idx = self.main_window.new_after_high2_logic_combo.findText(new_after_high2_logic)
                        if idx >= 0:
                            self.main_window.new_after_high2_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_after_high2_logic: {new_after_high2_logic}")
                    except:
                        pass
                
                # 创前新低1参数
                new_before_low_start = analysis_data.get('new_before_low_start', '')
                if new_before_low_start and hasattr(self.main_window, 'new_before_low_start_spin'):
                    try:
                        self.main_window.new_before_low_start_spin.setValue(int(new_before_low_start))
                        print(f"设置new_before_low_start: {new_before_low_start}")
                    except:
                        pass
                
                new_before_low_range = analysis_data.get('new_before_low_range', '')
                if new_before_low_range and hasattr(self.main_window, 'new_before_low_range_spin'):
                    try:
                        self.main_window.new_before_low_range_spin.setValue(int(new_before_low_range))
                        print(f"设置new_before_low_range: {new_before_low_range}")
                    except:
                        pass
                
                new_before_low_span = analysis_data.get('new_before_low_span', '')
                if new_before_low_span and hasattr(self.main_window, 'new_before_low_span_spin'):
                    try:
                        self.main_window.new_before_low_span_spin.setValue(int(new_before_low_span))
                        print(f"设置new_before_low_span: {new_before_low_span}")
                    except:
                        pass
                
                new_before_low_logic = analysis_data.get('new_before_low_logic', '')
                if new_before_low_logic and hasattr(self.main_window, 'new_before_low_logic_combo'):
                    try:
                        idx = self.main_window.new_before_low_logic_combo.findText(new_before_low_logic)
                        if idx >= 0:
                            self.main_window.new_before_low_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_before_low_logic: {new_before_low_logic}")
                    except:
                        pass
                
                # 创前新低2参数
                new_before_low2_start = analysis_data.get('new_before_low2_start', '')
                if new_before_low2_start and hasattr(self.main_window, 'new_before_low2_start_spin'):
                    try:
                        self.main_window.new_before_low2_start_spin.setValue(int(new_before_low2_start))
                        print(f"设置new_before_low2_start: {new_before_low2_start}")
                    except:
                        pass
                
                new_before_low2_range = analysis_data.get('new_before_low2_range', '')
                if new_before_low2_range and hasattr(self.main_window, 'new_before_low2_range_spin'):
                    try:
                        self.main_window.new_before_low2_range_spin.setValue(int(new_before_low2_range))
                        print(f"设置new_before_low2_range: {new_before_low2_range}")
                    except:
                        pass
                
                new_before_low2_span = analysis_data.get('new_before_low2_span', '')
                if new_before_low2_span and hasattr(self.main_window, 'new_before_low2_span_spin'):
                    try:
                        self.main_window.new_before_low2_span_spin.setValue(int(new_before_low2_span))
                        print(f"设置new_before_low2_span: {new_before_low2_span}")
                    except:
                        pass
                
                new_before_low2_logic = analysis_data.get('new_before_low2_logic', '')
                if new_before_low2_logic and hasattr(self.main_window, 'new_before_low2_logic_combo'):
                    try:
                        idx = self.main_window.new_before_low2_logic_combo.findText(new_before_low2_logic)
                        if idx >= 0:
                            self.main_window.new_before_low2_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_before_low2_logic: {new_before_low2_logic}")
                    except:
                        pass
                
                # 创后新低1参数
                new_after_low_start = analysis_data.get('new_after_low_start', '')
                if new_after_low_start and hasattr(self.main_window, 'new_after_low_start_spin'):
                    try:
                        self.main_window.new_after_low_start_spin.setValue(int(new_after_low_start))
                        print(f"设置new_after_low_start: {new_after_low_start}")
                    except:
                        pass
                
                new_after_low_range = analysis_data.get('new_after_low_range', '')
                if new_after_low_range and hasattr(self.main_window, 'new_after_low_range_spin'):
                    try:
                        self.main_window.new_after_low_range_spin.setValue(int(new_after_low_range))
                        print(f"设置new_after_low_range: {new_after_low_range}")
                    except:
                        pass
                
                new_after_low_span = analysis_data.get('new_after_low_span', '')
                if new_after_low_span and hasattr(self.main_window, 'new_after_low_span_spin'):
                    try:
                        self.main_window.new_after_low_span_spin.setValue(int(new_after_low_span))
                        print(f"设置new_after_low_span: {new_after_low_span}")
                    except:
                        pass
                
                new_after_low_logic = analysis_data.get('new_after_low_logic', '')
                if new_after_low_logic and hasattr(self.main_window, 'new_after_low_logic_combo'):
                    try:
                        idx = self.main_window.new_after_low_logic_combo.findText(new_after_low_logic)
                        if idx >= 0:
                            self.main_window.new_after_low_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_after_low_logic: {new_after_low_logic}")
                    except:
                        pass
                
                # 创后新低2参数
                new_after_low2_start = analysis_data.get('new_after_low2_start', '')
                if new_after_low2_start and hasattr(self.main_window, 'new_after_low2_start_spin'):
                    try:
                        self.main_window.new_after_low2_start_spin.setValue(int(new_after_low2_start))
                        print(f"设置new_after_low2_start: {new_after_low2_start}")
                    except:
                        pass
                
                new_after_low2_range = analysis_data.get('new_after_low2_range', '')
                if new_after_low2_range and hasattr(self.main_window, 'new_after_low2_range_spin'):
                    try:
                        self.main_window.new_after_low2_range_spin.setValue(int(new_after_low2_range))
                        print(f"设置new_after_low2_range: {new_after_low2_range}")
                    except:
                        pass
                
                new_after_low2_span = analysis_data.get('new_after_low2_span', '')
                if new_after_low2_span and hasattr(self.main_window, 'new_after_low2_span_spin'):
                    try:
                        self.main_window.new_after_low2_span_spin.setValue(int(new_after_low2_span))
                        print(f"设置new_after_low2_span: {new_after_low2_span}")
                    except:
                        pass
                
                new_after_low2_logic = analysis_data.get('new_after_low2_logic', '')
                if new_after_low2_logic and hasattr(self.main_window, 'new_after_low2_logic_combo'):
                    try:
                        idx = self.main_window.new_after_low2_logic_combo.findText(new_after_low2_logic)
                        if idx >= 0:
                            self.main_window.new_after_low2_logic_combo.setCurrentIndex(idx)
                            print(f"设置new_after_low2_logic: {new_after_low2_logic}")
                    except:
                        pass
                
                # 恢复创新高/创新低勾选状态
                new_before_high_flag = analysis_data.get('new_before_high_flag', False)
                if hasattr(self.main_window, 'new_before_high_flag_checkbox'):
                    try:
                        self.main_window.new_before_high_flag_checkbox.setChecked(new_before_high_flag)
                        print(f"设置new_before_high_flag: {new_before_high_flag}")
                    except:
                        pass
                
                new_before_high2_flag = analysis_data.get('new_before_high2_flag', False)
                if hasattr(self.main_window, 'new_before_high2_flag_checkbox'):
                    try:
                        self.main_window.new_before_high2_flag_checkbox.setChecked(new_before_high2_flag)
                        print(f"设置new_before_high2_flag: {new_before_high2_flag}")
                    except:
                        pass
                
                new_after_high_flag = analysis_data.get('new_after_high_flag', False)
                if hasattr(self.main_window, 'new_after_high_flag_checkbox'):
                    try:
                        self.main_window.new_after_high_flag_checkbox.setChecked(new_after_high_flag)
                        print(f"设置new_after_high_flag: {new_after_high_flag}")
                    except:
                        pass
                
                new_after_high2_flag = analysis_data.get('new_after_high2_flag', False)
                if hasattr(self.main_window, 'new_after_high2_flag_checkbox'):
                    try:
                        self.main_window.new_after_high2_flag_checkbox.setChecked(new_after_high2_flag)
                        print(f"设置new_after_high2_flag: {new_after_high2_flag}")
                    except:
                        pass
                
                new_before_low_flag = analysis_data.get('new_before_low_flag', False)
                if hasattr(self.main_window, 'new_before_low_flag_checkbox'):
                    try:
                        self.main_window.new_before_low_flag_checkbox.setChecked(new_before_low_flag)
                        print(f"设置new_before_low_flag: {new_before_low_flag}")
                    except:
                        pass
                
                new_before_low2_flag = analysis_data.get('new_before_low2_flag', False)
                if hasattr(self.main_window, 'new_before_low2_flag_checkbox'):
                    try:
                        self.main_window.new_before_low2_flag_checkbox.setChecked(new_before_low2_flag)
                        print(f"设置new_before_low2_flag: {new_before_low2_flag}")
                    except:
                        pass
                
                new_after_low_flag = analysis_data.get('new_after_low_flag', False)
                if hasattr(self.main_window, 'new_after_low_flag_checkbox'):
                    try:
                        self.main_window.new_after_low_flag_checkbox.setChecked(new_after_low_flag)
                        print(f"设置new_after_low_flag: {new_after_low_flag}")
                    except:
                        pass
                
                new_after_low2_flag = analysis_data.get('new_after_low2_flag', False)
                if hasattr(self.main_window, 'new_after_low2_flag_checkbox'):
                    try:
                        self.main_window.new_after_low2_flag_checkbox.setChecked(new_after_low2_flag)
                        print(f"设置new_after_low2_flag: {new_after_low2_flag}")
                    except:
                        pass

                # 恢复组合分析次数
                component_analysis_count = analysis_data.get('component_analysis_count', '')
                if component_analysis_count:
                    try:
                        count_val = int(float(component_analysis_count))
                        self.analysis_count_spin.setValue(count_val)
                        print(f"恢复组合分析次数: {count_val}")
                    except Exception as e:
                        print(f"恢复组合分析次数失败: {e}")
                
                # 恢复操作值表达式
                expr = analysis_data.get('expr', '')
                if expr:
                    try:
                        self.main_window.last_expr = expr
                        print(f"设置操作值表达式: {expr}")
                    except:
                        pass
                
                # 设置组合输出锁定勾选框为勾选状态
                try:
                    self.main_window.last_lock_output = True
                    print("设置组合输出锁定状态为: True")
                    
                    # 直接设置组合输出锁定勾选框控件状态
                    if hasattr(self.main_window, 'formula_widget') and self.main_window.formula_widget is not None:
                        if hasattr(self.main_window.formula_widget, 'lock_output_checkbox'):
                            self.main_window.formula_widget.lock_output_checkbox.setChecked(True)
                            print("设置组合输出锁定勾选框为: True")
                except:
                    pass

                # 恢复get_abbr_round_only_map的圆框勾选状态
                selected_vars_with_values = analysis_data.get('selected_vars_with_values', [])
                if selected_vars_with_values:
                    from function.stock_functions import get_abbr_round_only_map
                    abbr_round_only_map = get_abbr_round_only_map()
                    # 只处理英文名
                    selected_en_vars = set(var_name for var_name, _ in selected_vars_with_values)
                    for (zh, en), en_val in abbr_round_only_map.items():
                        if en_val in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[en_val]
                            if 'round_checkbox' in widgets:
                                widgets['round_checkbox'].setChecked(en_val in selected_en_vars)
                                print(f"恢复圆框变量 {en_val} 勾选状态: {en_val in selected_en_vars}")
                
                # 恢复n_values输入值（只恢复被勾选的变量）
                n_values = analysis_data.get('n_values', {})
                if n_values and selected_vars_with_values:
                    print(f"恢复n_values: {n_values}")
                    selected_var_names = set(var_name for var_name, _ in selected_vars_with_values)
                    for var_name, n_value in n_values.items():
                        # 只恢复在selected_vars_with_values中被勾选的变量
                        if var_name in selected_var_names and var_name in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var_name]
                            if 'n_input' in widgets:
                                widgets['n_input'].setText(str(n_value))
                                print(f"恢复n_input变量 {var_name} 输入值: {n_value}")
                
                # 清理临时控件
                temp_formula_widget.deleteLater()
                QMessageBox.information(self, "恢复成功", f"已成功恢复选股参数！\n公式: {formula}\n排序方式: {sort_mode}\n选股数量: {select_count}\n开始日期值选择: {analysis_data.get('start_option', '')}\n前移天数: {analysis_data.get('shift_days', '')}\n是否计算向前: {analysis_data.get('is_forward', False)}\n交易方式: {analysis_data.get('trade_mode', '')}\n操作值: {analysis_data.get('expr', '')}\n开始日到结束日之间最高价/最低价小于: {analysis_data.get('range_value', '')}\n开始日到结束日之间连续累加值绝对值小于: {analysis_data.get('continuous_abs_threshold', '')}\n开始日到结束日之间有效累加值绝对值小于: {analysis_data.get('valid_abs_sum_threshold', '')}\n第1组后N最大值逻辑: {analysis_data.get('n_days', '')}\n前1组结束地址后N日的最大值: {analysis_data.get('n_days_max', '')}\n操作涨幅: {analysis_data.get('ops_change', '')}\n日期宽度: {width}\n操作天数: {op_days}\n止盈递增率: {increment_rate}\n止盈后值大于结束值比例: {after_gt_end_ratio}\n止盈后值大于前值比例: {after_gt_start_ratio}\n止损递增率: {stop_loss_inc_rate}\n止损后值大于结束值比例: {stop_loss_after_gt_end_ratio}\n止损后值大于前值比例: {stop_loss_after_gt_start_ratio}")
                
                
            except Exception as e:
                QMessageBox.critical(self, "恢复失败", f"恢复选股参数失败：{e}")
                print(f"恢复失败详细错误: {e}")
                import traceback
                traceback.print_exc()

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
        
        table = CopyableTableWidget(row_count + 2, 23, self.result_area)  # 修正为23列
        table.setHorizontalHeaderLabels([
            "结束日期", 
            "持有天数", "止盈止损涨幅", "综合止盈止损日均涨幅", "止盈止损日均涨跌幅", "止盈止损从下往上含空均值", "止盈止损含空均值",
            "止盈停损涨幅", "综合止盈停损日均涨幅", "止盈停损日均涨跌幅", "止盈停损从下往上含空均值", "止盈停损含空均值",
            "调整天数", "停盈停损涨幅", "综合停盈停损日均涨幅", "停盈停损日均涨跌幅", "停盈停损从下往上含空均值", "停盈停损含空均值",
            "停盈止损涨幅", "综合停盈止损日均涨幅", "停盈止损日均涨跌幅", "停盈止损从下往上含空均值", "停盈止损含空均值"
        ])
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 设置第一行的均值数据
        if summary:
            table.setItem(0, 1, QTableWidgetItem(str(summary.get('mean_hold_days', ''))))
            # 止盈止损
            table.setItem(0, 2, QTableWidgetItem(f"{summary.get('mean_adjust_ops_change', '')}%" if summary.get('mean_adjust_ops_change', '') != '' else ''))
            table.setItem(0, 3, QTableWidgetItem(f"{summary.get('comprehensive_daily_change', '')}%" if summary.get('comprehensive_daily_change', '') != '' else ''))
            table.setItem(0, 4, QTableWidgetItem(f"{summary.get('mean_adjust_daily_change', '')}%" if summary.get('mean_adjust_daily_change', '') != '' else ''))
            table.setItem(0, 5, QTableWidgetItem(f"{summary.get('mean_adjust_with_nan', '')}%" if summary.get('mean_adjust_with_nan', '') != '' else ''))
            table.setItem(0, 6, QTableWidgetItem(f"{summary.get('mean_adjust_daily_with_nan', '')}%" if summary.get('mean_adjust_daily_with_nan', '') != '' else ''))

            # 止盈停损
            table.setItem(0, 7, QTableWidgetItem(f"{summary.get('mean_take_and_stop_change', '')}%" if summary.get('mean_take_and_stop_change', '') != '' else ''))
            table.setItem(0, 8, QTableWidgetItem(f"{summary.get('comprehensive_take_and_stop_change', '')}%" if summary.get('comprehensive_take_and_stop_change', '') != '' else ''))
            table.setItem(0, 9, QTableWidgetItem(f"{summary.get('mean_take_and_stop_daily_change', '')}%" if summary.get('mean_take_and_stop_daily_change', '') != '' else ''))
            table.setItem(0, 10, QTableWidgetItem(f"{summary.get('mean_take_and_stop_with_nan', '')}%" if summary.get('mean_take_and_stop_with_nan', '') != '' else ''))
            table.setItem(0, 11, QTableWidgetItem(f"{summary.get('mean_take_and_stop_daily_with_nan', '')}%" if summary.get('mean_take_and_stop_daily_with_nan', '') != '' else ''))

            table.setItem(0, 12, QTableWidgetItem(str(summary.get('mean_adjust_days', ''))))

            # 停盈停损
            table.setItem(0, 13, QTableWidgetItem(f"{summary.get('mean_ops_change', '')}%" if summary.get('mean_ops_change', '') != '' else ''))
            table.setItem(0, 14, QTableWidgetItem(f"{summary.get('comprehensive_stop_daily_change', '')}%" if summary.get('comprehensive_stop_daily_change', '') != '' else ''))
            table.setItem(0, 15, QTableWidgetItem(f"{summary.get('mean_daily_change', '')}%" if summary.get('mean_daily_change', '') != '' else ''))
            table.setItem(0, 16, QTableWidgetItem(f"{summary.get('mean_with_nan', '')}%" if summary.get('mean_with_nan', '') != '' else ''))
            table.setItem(0, 17, QTableWidgetItem(f"{summary.get('mean_daily_with_nan', '')}%" if summary.get('mean_daily_with_nan', '') != '' else ''))

            # 停盈止损
            table.setItem(0, 18, QTableWidgetItem(f"{summary.get('mean_stop_and_take_change', '')}%" if summary.get('mean_stop_and_take_change', '') != '' else ''))
            table.setItem(0, 19, QTableWidgetItem(f"{summary.get('comprehensive_stop_and_take_change', '')}%" if summary.get('comprehensive_stop_and_take_change', '') != '' else ''))
            table.setItem(0, 20, QTableWidgetItem(f"{summary.get('mean_stop_and_take_daily_change', '')}%" if summary.get('mean_stop_and_take_daily_change', '') != '' else ''))
            table.setItem(0, 21, QTableWidgetItem(f"{summary.get('mean_stop_and_take_with_nan', '')}%" if summary.get('mean_stop_and_take_with_nan', '') != '' else ''))
            table.setItem(0, 22, QTableWidgetItem(f"{summary.get('mean_stop_and_take_daily_with_nan', '')}%" if summary.get('mean_stop_and_take_daily_with_nan', '') != '' else ''))

        # 设置每行的数据
        for row_idx, item in enumerate(items):
            table.setItem(row_idx + 2, 0, QTableWidgetItem(str(item.get('date', ''))))
            table.setItem(row_idx + 2, 1, QTableWidgetItem(str(item.get('hold_days', ''))))
            # 止盈止损
            table.setItem(row_idx + 2, 2, QTableWidgetItem(f"{item.get('adjust_ops_change', '')}%" if item.get('adjust_ops_change', '') != '' else ''))
            table.setItem(row_idx + 2, 3, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 4, QTableWidgetItem(f"{item.get('adjust_daily_change', '')}%" if item.get('adjust_daily_change', '') != '' else ''))
            adjust_with_nan_mean = item.get('adjust_with_nan_mean', '')
            table.setItem(row_idx + 2, 5, QTableWidgetItem(f"{round(adjust_with_nan_mean, 2)}%" if adjust_with_nan_mean != '' and not (isinstance(adjust_with_nan_mean, float) and math.isnan(adjust_with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 6, QTableWidgetItem(""))  # 调幅含空值均值只在均值行

            # 止盈停损
            table.setItem(row_idx + 2, 7, QTableWidgetItem(f"{item.get('take_and_stop_change', '')}%" if item.get('take_and_stop_change', '') != '' else ''))
            table.setItem(row_idx + 2, 8, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 9, QTableWidgetItem(f"{item.get('take_and_stop_daily_change', '')}%" if item.get('take_and_stop_daily_change', '') != '' else ''))
            take_and_stop_with_nan_mean = item.get('take_and_stop_with_nan_mean', '')
            table.setItem(row_idx + 2, 10, QTableWidgetItem(f"{round(take_and_stop_with_nan_mean, 2)}%" if take_and_stop_with_nan_mean != '' and not (isinstance(take_and_stop_with_nan_mean, float) and math.isnan(take_and_stop_with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 11, QTableWidgetItem(""))

            table.setItem(row_idx + 2, 12, QTableWidgetItem(str(item.get('adjust_days', ''))))

            # 停盈停损
            table.setItem(row_idx + 2, 13, QTableWidgetItem(f"{item.get('ops_change', '')}%" if item.get('ops_change', '') != '' else ''))
            table.setItem(row_idx + 2, 14, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 15, QTableWidgetItem(f"{item.get('daily_change', '')}%" if item.get('daily_change', '') != '' else ''))
            with_nan_mean = item.get('with_nan_mean', '')
            table.setItem(row_idx + 2, 16, QTableWidgetItem(f"{round(with_nan_mean, 2)}%" if with_nan_mean != '' and not (isinstance(with_nan_mean, float) and math.isnan(with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 17, QTableWidgetItem(""))  # 含空值均值在summary中，这里暂时留空

            # 停盈止损
            table.setItem(row_idx + 2, 18, QTableWidgetItem(f"{item.get('stop_and_take_change', '')}%" if item.get('stop_and_take_change', '') != '' else ''))
            table.setItem(row_idx + 2, 19, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 20, QTableWidgetItem(f"{item.get('stop_and_take_daily_change', '')}%" if item.get('stop_and_take_daily_change', '') != '' else ''))
            stop_and_take_with_nan_mean = item.get('stop_and_take_with_nan_mean', '')
            table.setItem(row_idx + 2, 21, QTableWidgetItem(f"{round(stop_and_take_with_nan_mean, 2)}%" if stop_and_take_with_nan_mean != '' and not (isinstance(stop_and_take_with_nan_mean, float) and math.isnan(stop_and_take_with_nan_mean)) else ''))
            table.setItem(row_idx + 2, 22, QTableWidgetItem(""))

        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

        # 在表格最后一行插入止盈止损率统计，跨所有列
        row = table.rowCount()
        table.insertRow(row)
        
        # 获取动态文本
        profit_text, loss_text, profit_median_text, loss_median_text = self.get_profit_loss_text_by_category()
        print(f"profit_text = {profit_text}, loss_text = {loss_text}, profit_median_text = {profit_median_text}, loss_median_text = {loss_median_text}")
        
        # 检查是否返回了None（表示选择了不同类别）
        if profit_text is None or loss_text is None:
            # 如果选择了不同类别，不显示统计信息
            stats_text = f"总股票数: {summary.get('total_stocks', 0)} | 持有率: {summary.get('hold_rate', 0)}%"
        else:
            # 构建止盈止损率统计文本
            stats_text = f"总股票数: {summary.get('total_stocks', 0)} | "
            stats_text += f"持有率: {summary.get('hold_rate', 0)}% | "
            stats_text += f"{profit_text}: {summary.get('profit_rate', 0)}% | "
            stats_text += f"{loss_text}: {summary.get('loss_rate', 0)}%"
        
        item = QTableWidgetItem(stats_text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setToolTip(stats_text)
        table.setItem(row, 0, item)
        table.setSpan(row, 0, 1, table.columnCount())
        table.setWordWrap(True)
        table.resizeRowToContents(row)

        # 在总股票数下一行插入中位数统计，跨所有列
        row = table.rowCount()
        table.insertRow(row)
        
        # 构建中位数统计文本
        hold_median = summary.get('hold_median')
        profit_median = summary.get('profit_median')
        loss_median = summary.get('loss_median')
        
        if profit_median_text is None or loss_median_text is None:
            # 如果选择了不同类别，只显示持有中位数
            median_text = f"持有中位数: {hold_median}%" if hold_median is not None else "持有中位数: 无"
        else:
            median_text = f"持有中位数: {hold_median}%" if hold_median is not None else "持有中位数: 无"
            median_text += f" | {profit_median_text}: {profit_median}%" if profit_median is not None else f" | {profit_median_text}: 无"
            median_text += f" | {loss_median_text}: {loss_median}%" if loss_median is not None else f" | {loss_median_text}: 无"
        
        item = QTableWidgetItem(median_text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        item.setToolTip(median_text)
        table.setItem(row, 0, item)
        table.setSpan(row, 0, 1, table.columnCount())
        table.setWordWrap(True)
        table.resizeRowToContents(row)

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

        # 插入参数输出
        row = table.rowCount()
        params = [
            ("日期宽度", str(analysis.get('width', ''))),
            ("开始日期值选择", analysis.get('start_option', '')),
            ("前移天数", str(analysis.get('shift', ''))),
            ("操作天数", str(analysis.get('op_days', ''))),
            ("止盈递增率", f"{analysis.get('increment_rate', '')}%"),
            ("止盈后值大于结束值比例", f"{analysis.get('after_gt_end_ratio', '')}%"),
            ("止盈后值大于前值比例", f"{analysis.get('after_gt_start_ratio', '')}%"),
            ("止损递增率", f"{analysis.get('stop_loss_inc_rate', '')}%"),
            ("止损后值大于结束值比例", f"{analysis.get('stop_loss_after_gt_end_ratio', '')}%"),
            ("止损大于前值比例", f"{analysis.get('stop_loss_after_gt_start_ratio', '')}%"),
            ("操作涨幅", f"{analysis.get('ops_change', '')}%")
        ]
        for i, (label, value) in enumerate(params):
            table.insertRow(row + i)
            table.setItem(row + i, 0, QTableWidgetItem(label))
            table.setItem(row + i, 1, QTableWidgetItem(value))

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
        
        # 使用与操盘方案相同的命名逻辑生成默认文件名
        analysis = top1.get('analysis', {})
        params = self._collect_all_control_params()
        # 将特定参数添加到params中
        params.update({
            'width': analysis.get('width', ''),
            'sort_mode': analysis.get('sort_mode', ''),
            'op_days': analysis.get('op_days', ''),
            'increment_rate': analysis.get('increment_rate', ''),
            'after_gt_end_ratio': analysis.get('after_gt_end_ratio', ''),
            'after_gt_start_ratio': analysis.get('after_gt_start_ratio', ''),
            'stop_loss_inc_rate': analysis.get('stop_loss_inc_rate', ''),
            'stop_loss_after_gt_end_ratio': analysis.get('stop_loss_after_gt_end_ratio', ''),
            'stop_loss_after_gt_start_ratio': analysis.get('stop_loss_after_gt_start_ratio', ''),
            'expr': analysis.get('expr', ''),
            'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
            'n_values': analysis.get('n_values', [])
        })
        
        # 生成默认文件名
        default_filename = self._generate_default_plan_name(analysis, params, top1)
        
        # 确保文件名有正确的扩展名
        if not default_filename.endswith('.json'):
            default_filename += '.json'
        
        # 创建文件对话框并设置默认文件名
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import Qt
        dialog = QFileDialog(self, "导出最优方案")
        dialog.setDefaultSuffix("json")
        dialog.setNameFilter("JSON Files (*.json);;Text Files (*.txt)")
        dialog.selectFile(default_filename)
        
        # 尝试设置对话框的最小宽度以更好地显示长文件名
        dialog.setMinimumWidth(600)
        
        # 设置对话框模式以优化文件名显示
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        
        # 尝试设置对话框选项以改善文件名显示
        dialog.setOption(QFileDialog.DontConfirmOverwrite, False)
        
        if dialog.exec_() == QFileDialog.Accepted:
            file_path = dialog.selectedFiles()[0]
        else:
            return
        if not file_path:
            return
        if not (file_path.endswith('.json') or file_path.endswith('.txt')):
            file_path += '.json'
        try:
            import json
            
            # 如果是三次分析，添加最优参数条件信息到导出数据中
            export_data = top1.copy()
            if hasattr(self, 'best_param_condition_list') and self.best_param_condition_list:
                export_data['best_param_conditions'] = self.best_param_condition_list
                print(f"导出时添加三次分析的最优参数条件：{len(self.best_param_condition_list)}个参数")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已成功导出最优方案到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出最优方案失败：{e}")

    def on_export_csv(self):
        """导出最优方案为CSV文件（KV形式），包含三次分析结果"""
        top1 = getattr(self.main_window, 'last_component_analysis_top1', None)
        if not top1:
            QMessageBox.warning(self, "提示", "没有可导出的最优方案数据！")
            return
        
        # 使用与操盘方案相同的命名逻辑生成默认文件名
        analysis = top1.get('analysis', {})
        params = self._collect_all_control_params()
        # 将特定参数添加到params中
        params.update({
            'width': analysis.get('width', ''),
            'sort_mode': analysis.get('sort_mode', ''),
            'op_days': analysis.get('op_days', ''),
            'increment_rate': analysis.get('increment_rate', ''),
            'after_gt_end_ratio': analysis.get('after_gt_end_ratio', ''),
            'after_gt_start_ratio': analysis.get('after_gt_start_ratio', ''),
            'stop_loss_inc_rate': analysis.get('stop_loss_inc_rate', ''),
            'stop_loss_after_gt_end_ratio': analysis.get('stop_loss_after_gt_end_ratio', ''),
            'stop_loss_after_gt_start_ratio': analysis.get('stop_loss_after_gt_start_ratio', ''),
            'expr': analysis.get('expr', ''),
            'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
            'n_values': analysis.get('n_values', [])
        })
        
        # 生成默认文件名
        default_filename = self._generate_default_plan_name(analysis, params, top1)
        
        # 确保文件名有正确的扩展名
        if not default_filename.endswith('.csv'):
            default_filename += '.csv'
        
        # 创建文件对话框并设置默认文件名
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import Qt
        dialog = QFileDialog(self, "导出最优方案")
        dialog.setDefaultSuffix("csv")
        dialog.setNameFilter("CSV Files (*.csv);;Text Files (*.txt)")
        dialog.selectFile(default_filename)
        
        # 尝试设置对话框的最小宽度以更好地显示长文件名
        dialog.setMinimumWidth(600)
        
        # 设置对话框模式以优化文件名显示
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        
        # 尝试设置对话框选项以改善文件名显示
        dialog.setOption(QFileDialog.DontConfirmOverwrite, False)
        
        if dialog.exec_() == QFileDialog.Accepted:
            file_path = dialog.selectedFiles()[0]
        else:
            return
        if not file_path:
            return
        if not (file_path.endswith('.csv') or file_path.endswith('.txt')):
            file_path += '.csv'
        try:
            import csv
            
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 写入键值对格式的数据
                writer.writerow(['参数名', '参数值'])
                
                # 基础分析结果
                writer.writerow(['adjusted_value', top1.get('adjusted_value', '')])
                writer.writerow(['formula', analysis.get('formula', '')])
                
                # 恢复参数所需的核心参数
                if analysis:
                    writer.writerow(['width', analysis.get('width', '')])
                    writer.writerow(['op_days', analysis.get('op_days', '')])
                    writer.writerow(['increment_rate', analysis.get('increment_rate', '')])
                    writer.writerow(['after_gt_end_ratio', analysis.get('after_gt_end_ratio', '')])
                    writer.writerow(['after_gt_start_ratio', analysis.get('after_gt_start_ratio', '')])
                    writer.writerow(['stop_loss_inc_rate', analysis.get('stop_loss_inc_rate', '')])
                    writer.writerow(['stop_loss_after_gt_end_ratio', analysis.get('stop_loss_after_gt_end_ratio', '')])
                    writer.writerow(['stop_loss_after_gt_start_ratio', analysis.get('stop_loss_after_gt_start_ratio', '')])
                    writer.writerow(['sort_mode', analysis.get('sort_mode', '')])
                    writer.writerow(['select_count', analysis.get('select_count', 10)])
                    writer.writerow(['expr', analysis.get('expr', '')])
                    
                    # 创新高/创新低相关参数
                    writer.writerow(['start_option', analysis.get('start_option', '')])
                    writer.writerow(['shift_days', analysis.get('shift_days', '')])
                    writer.writerow(['is_forward', analysis.get('is_forward', False)])
                    writer.writerow(['trade_mode', analysis.get('trade_mode', '')])
                    writer.writerow(['ops_change', analysis.get('ops_change', '')])
                    writer.writerow(['n_days', analysis.get('n_days', '')])
                    writer.writerow(['n_days_max', analysis.get('n_days_max', '')])
                    writer.writerow(['range_value', analysis.get('range_value', '')])
                    writer.writerow(['continuous_abs_threshold', analysis.get('continuous_abs_threshold', '')])
                    writer.writerow(['valid_abs_sum_threshold', analysis.get('valid_abs_sum_threshold', '')])
                    
                    # 创新高/创新低参数
                    writer.writerow(['new_before_high_start', analysis.get('new_before_high_start', '')])
                    writer.writerow(['new_before_high_range', analysis.get('new_before_high_range', '')])
                    writer.writerow(['new_before_high_span', analysis.get('new_before_high_span', '')])
                    writer.writerow(['new_before_high_logic', analysis.get('new_before_high_logic', '')])
                    writer.writerow(['new_before_high_flag', analysis.get('new_before_high_flag', False)])
                    
                    writer.writerow(['new_before_high2_start', analysis.get('new_before_high2_start', '')])
                    writer.writerow(['new_before_high2_range', analysis.get('new_before_high2_range', '')])
                    writer.writerow(['new_before_high2_span', analysis.get('new_before_high2_span', '')])
                    writer.writerow(['new_before_high2_logic', analysis.get('new_before_high2_logic', '')])
                    writer.writerow(['new_before_high2_flag', analysis.get('new_before_high2_flag', False)])
                    
                    writer.writerow(['new_after_high_start', analysis.get('new_after_high_start', '')])
                    writer.writerow(['new_after_high_range', analysis.get('new_after_high_range', '')])
                    writer.writerow(['new_after_high_span', analysis.get('new_after_high_span', '')])
                    writer.writerow(['new_after_high_logic', analysis.get('new_after_high_logic', '')])
                    writer.writerow(['new_after_high_flag', analysis.get('new_after_high_flag', False)])
                    
                    writer.writerow(['new_after_high2_start', analysis.get('new_after_high2_start', '')])
                    writer.writerow(['new_after_high2_range', analysis.get('new_after_high2_range', '')])
                    writer.writerow(['new_after_high2_span', analysis.get('new_after_high2_span', '')])
                    writer.writerow(['new_after_high2_logic', analysis.get('new_after_high2_logic', '')])
                    writer.writerow(['new_after_high2_flag', analysis.get('new_after_high2_flag', False)])
                    
                    writer.writerow(['new_before_low_start', analysis.get('new_before_low_start', '')])
                    writer.writerow(['new_before_low_range', analysis.get('new_before_low_range', '')])
                    writer.writerow(['new_before_low_span', analysis.get('new_before_low_span', '')])
                    writer.writerow(['new_before_low_logic', analysis.get('new_before_low_logic', '')])
                    writer.writerow(['new_before_low_flag', analysis.get('new_before_low_flag', False)])
                    
                    writer.writerow(['new_before_low2_start', analysis.get('new_before_low2_start', '')])
                    writer.writerow(['new_before_low2_range', analysis.get('new_before_low2_range', '')])
                    writer.writerow(['new_before_low2_span', analysis.get('new_before_low2_span', '')])
                    writer.writerow(['new_before_low2_logic', analysis.get('new_before_low2_logic', '')])
                    writer.writerow(['new_before_low2_flag', analysis.get('new_before_low2_flag', False)])
                    
                    writer.writerow(['new_after_low_start', analysis.get('new_after_low_start', '')])
                    writer.writerow(['new_after_low_range', analysis.get('new_after_low_range', '')])
                    writer.writerow(['new_after_low_span', analysis.get('new_after_low_span', '')])
                    writer.writerow(['new_after_low_logic', analysis.get('new_after_low_logic', '')])
                    writer.writerow(['new_after_low_flag', analysis.get('new_after_low_flag', False)])
                    
                    writer.writerow(['new_after_low2_start', analysis.get('new_after_low2_start', '')])
                    writer.writerow(['new_after_low2_range', analysis.get('new_after_low2_range', '')])
                    writer.writerow(['new_after_low2_span', analysis.get('new_after_low2_span', '')])
                    writer.writerow(['new_after_low2_logic', analysis.get('new_after_low2_logic', '')])
                    writer.writerow(['new_after_low2_flag', analysis.get('new_after_low2_flag', False)])
                    
                    # 组合分析次数
                    writer.writerow(['component_analysis_count', analysis.get('component_analysis_count', '')])
                    
                    # 变量选择和n值
                    if analysis.get('selected_vars_with_values'):
                        writer.writerow(['selected_vars_with_values', str(analysis.get('selected_vars_with_values'))])
                    if analysis.get('n_values'):
                        writer.writerow(['n_values', str(analysis.get('n_values'))])
                
                # 只添加三次分析最优值
                best_value_formatted = None
                
                # 获取三次分析最优值（从全局top_three中获取第一个元素，更准确）
                if hasattr(self, 'three_stage_global_top_three') and self.three_stage_global_top_three:
                    # 从全局top_three中获取第一个元素（最优值）
                    best_value = self.three_stage_global_top_three[0].get('adjusted_value', '未知')
                    if best_value != '未知':
                        try:
                            best_value_float = float(best_value)
                            best_value_formatted = f"{best_value_float:.2f}"
                        except (ValueError, TypeError):
                            best_value_formatted = str(best_value)
                    else:
                        best_value_formatted = str(best_value)
                elif hasattr(self, 'three_stage_best_top_one') and self.three_stage_best_top_one:
                    # 如果没有全局top_three，则使用best_top_one作为备选
                    best_value = self.three_stage_best_top_one.get('adjusted_value', '未知')
                    if best_value != '未知':
                        try:
                            best_value_float = float(best_value)
                            best_value_formatted = f"{best_value_float:.2f}"
                        except (ValueError, TypeError):
                            best_value_formatted = str(best_value)
                    else:
                        best_value_formatted = str(best_value)
                
                # 如果有组合分析最优值，先输出组合分析最优值
                if hasattr(self, 'three_stage_initial_last_value') and self.three_stage_initial_last_value is not None:
                    writer.writerow([])  # 空行分隔
                    writer.writerow(['组合分析最优值', f"{self.three_stage_initial_last_value:.2f}"])
                
                # 写入三次分析最优值
                if best_value_formatted:
                    writer.writerow(['三次分析最优值', best_value_formatted])
                
                # 写入三次分析的最优方案数据（KV形式）
                print(f"三次分析的最优方案数据: {self.best_param_condition_list}")
                
                # 获取无最优结果的条件
                no_better_results = getattr(self.main_window, 'no_better_result_list', [])
                print(f"无最优结果的条件: {no_better_results}")
                
                # 将所有条件集合起来，统一按输出参数、辅助参数顺序输出
                all_conditions = []
                
                # 获取参数类型映射
                def is_output_param(param_name):
                    """判断参数是否为输出参数"""
                    try:
                        # 硬编码输出参数列表（基于get_abbr_round_map函数）
                        output_params = {
                            'valid_pos_sum', 'valid_neg_sum', 'cont_sum_pos_sum', 'cont_sum_neg_sum',
                            'forward_max_cont_sum_pos_sum', 'forward_max_cont_sum_neg_sum',
                            'forward_min_cont_sum_pos_sum', 'forward_min_cont_sum_neg_sum',
                            'forward_max_valid_pos_sum', 'forward_max_valid_neg_sum',
                            'forward_min_valid_pos_sum', 'forward_min_valid_neg_sum'
                        }
                        
                        # 检查是否在输出参数列表中
                        if param_name in output_params:
                            return True
                        
                        # 检查是否在主窗口的abbr_round_map中
                        if hasattr(self.main_window, 'abbr_round_map'):
                            if param_name in self.main_window.abbr_round_map.values():
                                print(f"参数 {param_name} 是输出参数")
                                return True
                        
                        # 检查是否在向前参数状态中且为输出参数
                        if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                            if param_name in self.main_window.forward_param_state:
                                # 这里需要检查是否为输出参数，暂时简化处理
                                # 可以根据实际需要进一步完善
                                return True
                        
                        return False
                    except Exception as e:
                        print(f"判断参数类型时出错: {e}")
                        return False
                
                # 添加有最优结果的条件
                if hasattr(self, 'best_param_condition_list') and self.best_param_condition_list:
                    for condition in self.best_param_condition_list:
                        for param_name, condition_text in condition.items():
                            sort_value = self._get_param_sort_value(param_name)
                            if sort_value is None:
                                sort_value = 999  # 如果没有序号，使用999作为默认值
                            
                            # 根据参数名称判断类型
                            param_type = 'output' if is_output_param(param_name) else 'auxiliary'
                            all_conditions.append((param_type, sort_value, param_name, condition_text, 'optimal'))
                
                # 添加无最优结果的条件
                if no_better_results:
                    for condition in no_better_results:
                        for param_name, condition_text in condition.items():
                            sort_value = self._get_param_sort_value(param_name)
                            if sort_value is None:
                                sort_value = 999  # 如果没有序号，使用999作为默认值
                            
                            # 根据参数名称判断类型
                            param_type = 'output' if is_output_param(param_name) else 'auxiliary'
                            all_conditions.append((param_type, sort_value, param_name, condition_text, 'no_optimal'))
                
                # 剔除重复参数：以最优条件参数为准，剔除无最优条件的相同参数
                # 收集所有有最优条件的参数名称
                optimal_param_names = set()
                for cond in all_conditions:
                    if cond[4] == 'optimal':  # condition_type == 'optimal'
                        optimal_param_names.add(cond[2])  # param_name
                
                # 剔除无最优条件中已经存在最优条件的参数
                filtered_conditions = []
                for cond in all_conditions:
                    param_name = cond[2]  # param_name
                    condition_type = cond[4]  # condition_type
                    
                    # 如果是有最优条件，直接保留
                    if condition_type == 'optimal':
                        filtered_conditions.append(cond)
                    # 如果是无最优条件，检查是否已经有最优条件
                    elif condition_type == 'no_optimal':
                        if param_name not in optimal_param_names:
                            # 没有最优条件，保留
                            filtered_conditions.append(cond)
                        else:
                            # 已经有最优条件，剔除
                            print(f"剔除重复参数 {param_name} 的无最优条件，因为已有最优条件")
                
                # 按类型和序号排序：先输出参数，再辅助参数
                # 先按类型分组，再在每组内按序号排序
                output_conditions = [cond for cond in filtered_conditions if cond[0] == 'output']
                auxiliary_conditions = [cond for cond in filtered_conditions if cond[0] == 'auxiliary']
                
                # 在每组内按序号排序
                output_conditions.sort(key=lambda x: x[1])
                auxiliary_conditions.sort(key=lambda x: x[1])
                # print(f"输出参数: {output_conditions}")
                # print(f"辅助参数: {auxiliary_conditions}")
                
                # 分别输出输出参数和辅助参数
                if output_conditions or auxiliary_conditions:
                    writer.writerow([])  # 空行分隔
                    writer.writerow(['三次分析序号', '参数名称', '最优值', '最优上限', '最优下限', '最优正中值', '最优负中值', '是否生成最优'])
                    
                    # 先输出输出参数
                    for i, (param_type, sort_value, param_name, condition_text, condition_type) in enumerate(output_conditions, 1):
                        if condition_type == 'optimal':
                            # 处理有最优结果的条件
                            # 从条件文本中提取信息
                            lower_match = re.search(r'下限(-?[\d\.]+)', condition_text)
                            upper_match = re.search(r'上限(-?[\d\.]+)', condition_text)
                            output_value_match = re.search(r'组合排序输出值为：([\d\.]+)', condition_text)
                            positive_median_match = re.search(rf'{re.escape(param_name)}_positive_median：(-?[\d\.]+)', condition_text)
                            negative_median_match = re.search(rf'{re.escape(param_name)}_negative_median：(-?[\d\.]+)', condition_text)
                            
                            # 格式化最优值为两位小数
                            optimal_value = ''
                            if output_value_match:
                                try:
                                    optimal_value = f"{float(output_value_match.group(1)):.2f}"
                                except (ValueError, TypeError):
                                    optimal_value = output_value_match.group(1)
                                    print(f"输出参数最优值转换失败，使用原始值：{optimal_value}")
                            else:
                                print(f"未找到最优值匹配，条件文本：{condition_text}")
                            
                            # 判断是否生成最优（根据条件类型判断，而不是最优值）
                            has_upper = upper_match.group(1) if upper_match else ''
                            has_lower = lower_match.group(1) if lower_match else ''
                            # 使用条件类型来判断是否生成最优，而不是最优值
                            is_optimal = '是' if condition_type == 'optimal' else '否'
                            
                            # 写入数据行
                            writer.writerow([
                                sort_value,  # 使用原始序号
                                param_name,
                                optimal_value,
                                has_upper,
                                has_lower,
                                positive_median_match.group(1) if positive_median_match else '',
                                negative_median_match.group(1) if negative_median_match else '',
                                is_optimal
                            ])
                        else:
                            # 处理无最优结果的条件（从无最优条件文本中提取信息）
                            # 添加调试信息
                            print(f"处理无最优结果条件，参数：{param_name}，条件文本：{condition_text}")
                            
                            # 从条件文本中提取信息
                            lower_match = re.search(r'下限(-?[\d\.]+)', condition_text)
                            upper_match = re.search(r'上限(-?[\d\.]+)', condition_text)
                            output_value_match = re.search(r'组合排序输出值为：([\d\.]+)', condition_text)
                            positive_median_match = re.search(rf'{re.escape(param_name)}_positive_median：(-?[\d\.]+)', condition_text)
                            negative_median_match = re.search(rf'{re.escape(param_name)}_negative_median：(-?[\d\.]+)', condition_text)
                            
                            # 添加调试信息
                            print(f"正则匹配结果 - lower_match: {lower_match}, upper_match: {upper_match}, output_value_match: {output_value_match}")
                            
                            # 格式化最优值为两位小数
                            optimal_value = ''
                            if output_value_match:
                                try:
                                    optimal_value = f"{float(output_value_match.group(1)):.2f}"
                                    print(f"成功提取最优值：{optimal_value}")
                                except (ValueError, TypeError):
                                    optimal_value = output_value_match.group(1)
                                    print(f"最优值转换失败，使用原始值：{optimal_value}")
                            else:
                                print(f"未找到最优值匹配，条件文本：{condition_text}")
                            
                            # 判断是否生成最优（根据最优值判断，而不是上下限）
                            has_upper = upper_match.group(1) if upper_match else ''
                            has_lower = lower_match.group(1) if lower_match else ''
                            # 使用最优值来判断是否生成最优，而不是上下限
                            is_optimal = '是' if condition_type == 'optimal' else '否'
                            
                            print(f"最终结果 - optimal_value: {optimal_value}, is_optimal: {is_optimal}")
                            
                            writer.writerow([
                                sort_value,  # 使用原始序号
                                param_name,
                                optimal_value,
                                has_upper,
                                has_lower,
                                positive_median_match.group(1) if positive_median_match else '',
                                negative_median_match.group(1) if negative_median_match else '',
                                is_optimal
                            ])
                    
                    # 再输出辅助参数
                    for i, (param_type, sort_value, param_name, condition_text, condition_type) in enumerate(auxiliary_conditions, 1):
                        if condition_type == 'optimal':
                            # 处理有最优结果的条件
                            # 从条件文本中提取信息
                            lower_match = re.search(r'下限(-?[\d\.]+)', condition_text)
                            upper_match = re.search(r'上限(-?[\d\.]+)', condition_text)
                            output_value_match = re.search(r'组合排序输出值为：([\d\.]+)', condition_text)
                            positive_median_match = re.search(rf'{re.escape(param_name)}_positive_median：(-?[\d\.]+)', condition_text)
                            negative_median_match = re.search(rf'{re.escape(param_name)}_negative_median：(-?[\d\.]+)', condition_text)
                            
                            # 格式化最优值为两位小数
                            optimal_value = ''
                            if output_value_match:
                                try:
                                    optimal_value = f"{float(output_value_match.group(1)):.2f}"
                                except (ValueError, TypeError):
                                    optimal_value = output_value_match.group(1)
                                    print(f"辅助参数最优值转换失败，使用原始值：{optimal_value}")
                            else:
                                print(f"未找到最优值匹配，条件文本：{condition_text}")
                            
                            # 判断是否生成最优（根据最优值判断，而不是上下限）
                            has_upper = upper_match.group(1) if upper_match else ''
                            has_lower = lower_match.group(1) if lower_match else ''
                            # 使用最优值来判断是否生成最优，而不是上下限
                            is_optimal = '是' if condition_type == 'optimal' else '否'
                            
                            # 写入数据行
                            writer.writerow([
                                sort_value,  # 使用原始序号
                                param_name,
                                optimal_value,
                                has_upper,
                                has_lower,
                                positive_median_match.group(1) if positive_median_match else '',
                                negative_median_match.group(1) if negative_median_match else '',
                                is_optimal
                            ])
                        else:
                            # 处理无最优结果的条件（从无最优条件文本中提取信息）
                            # 添加调试信息
                            print(f"处理辅助参数无最优结果条件，参数：{param_name}，条件文本：{condition_text}")
                            
                            # 从条件文本中提取信息
                            lower_match = re.search(r'下限(-?[\d\.]+)', condition_text)
                            upper_match = re.search(r'上限(-?[\d\.]+)', condition_text)
                            output_value_match = re.search(r'组合排序输出值为：([\d\.]+)', condition_text)
                            positive_median_match = re.search(rf'{re.escape(param_name)}_positive_median：(-?[\d\.]+)', condition_text)
                            negative_median_match = re.search(rf'{re.escape(param_name)}_negative_median：(-?[\d\.]+)', condition_text)
                            
                            # 添加调试信息
                            print(f"辅助参数正则匹配结果 - lower_match: {lower_match}, upper_match: {upper_match}, output_value_match: {output_value_match}")
                            
                            # 格式化最优值为两位小数
                            optimal_value = ''
                            if output_value_match:
                                try:
                                    optimal_value = f"{float(output_value_match.group(1)):.2f}"
                                    print(f"辅助参数成功提取最优值：{optimal_value}")
                                except (ValueError, TypeError):
                                    optimal_value = output_value_match.group(1)
                                    print(f"辅助参数最优值转换失败，使用原始值：{optimal_value}")
                            else:
                                print(f"辅助参数未找到最优值匹配，条件文本：{condition_text}")
                            
                            # 判断是否生成最优（根据最优值判断，而不是上下限）
                            has_upper = upper_match.group(1) if upper_match else ''
                            has_lower = lower_match.group(1) if lower_match else ''
                            # 使用最优值来判断是否生成最优，而不是上下限
                            is_optimal = '是' if condition_type == 'optimal' else '否'
                            
                            print(f"辅助参数最终结果 - optimal_value: {optimal_value}, is_optimal: {is_optimal}")
                            
                            writer.writerow([
                                sort_value,  # 使用原始序号
                                param_name,
                                optimal_value,
                                has_upper,
                                has_lower,
                                positive_median_match.group(1) if positive_median_match else '',
                                negative_median_match.group(1) if negative_median_match else '',
                                is_optimal
                            ])


                
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
            
            # 如果导入的数据包含最优参数条件，恢复它们
            if 'best_param_condition_list' in top1:
                self.best_param_condition_list = top1['best_param_condition_list']
                print(f"导入时恢复三次分析的最优参数条件：{len(self.best_param_condition_list)}个参数")
            
            all_analysis_results = [top1]
            self.show_analysis_results(all_analysis_results)
            # 自动恢复参数
            analysis = top1.get('analysis', {})
            self.restore_formula_params(analysis)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入最优方案失败：{e}")

    def on_import_csv(self):
        """导入CSV并自动恢复控件参数"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入CSV文件", "", "CSV Files (*.csv)")
        if not file_path:
            return
        try:
            import csv
            import ast
            
            # 存储导入的数据
            analysis_data = {}
            best_param_conditions = []
            
            # 添加文件读取的容错处理
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    for idx, row in enumerate(reader):
                        if idx == 0:  # 跳过标题行
                            continue
                        
                        if len(row) >= 2:
                            param_name = row[0].strip()
                            param_value = row[1].strip()
                            
                            # 处理不同类型的参数
                            if param_name.startswith('param_') and '_' in param_name:
                                # 三次分析的最优参数条件
                                parts = param_name.split('_')
                                if len(parts) >= 3:
                                    param_index = int(parts[1]) - 1
                                    if param_index >= len(best_param_conditions):
                                        best_param_conditions.append({})
                                    
                                    if 'best_conditions' not in best_param_conditions[param_index]:
                                        best_param_conditions[param_index]['best_conditions'] = {}
                                    
                                    if parts[2] in ['best_lower', 'best_upper', 'best_output']:
                                        best_param_conditions[param_index]['best_conditions'][parts[2]] = param_value
                                    else:
                                        best_param_conditions[param_index][parts[2]] = param_value
                            else:
                                # 普通参数
                                if param_name in ['selected_vars_with_values', 'n_values']:
                                    # 处理复杂数据类型
                                    try:
                                        if param_value and param_value != '':
                                            analysis_data[param_name] = ast.literal_eval(param_value)
                                        else:
                                            analysis_data[param_name] = [] if param_name == 'selected_vars_with_values' else {}
                                    except:
                                        # 如果解析失败，使用原始值
                                        analysis_data[param_name] = param_value
                                elif param_name in ['is_forward', 'new_before_high_flag', 'new_before_high2_flag', 
                                                   'new_after_high_flag', 'new_after_high2_flag', 
                                                   'new_before_low_flag', 'new_before_low2_flag', 
                                                   'new_after_low_flag', 'new_after_low2_flag']:
                                    # 布尔值参数
                                    analysis_data[param_name] = param_value.lower() in ['true', '1', 'yes', '是']
                                else:
                                    # 普通参数
                                    analysis_data[param_name] = param_value
                            
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        reader = csv.reader(f)
                        for idx, row in enumerate(reader):
                            if idx == 0:  # 跳过标题行
                                continue
                            
                            if len(row) >= 2:
                                param_name = row[0].strip()
                                param_value = row[1].strip()
                                
                                # 处理不同类型的参数（与上面相同的逻辑）
                                if param_name.startswith('param_') and '_' in param_name:
                                    # 三次分析的最优参数条件
                                    parts = param_name.split('_')
                                    if len(parts) >= 3:
                                        param_index = int(parts[1]) - 1
                                        if param_index >= len(best_param_conditions):
                                            best_param_conditions.append({})
                                        
                                        if 'best_conditions' not in best_param_conditions[param_index]:
                                            best_param_conditions[param_index]['best_conditions'] = {}
                                        
                                        if parts[2] in ['best_lower', 'best_upper', 'best_output']:
                                            best_param_conditions[param_index]['best_conditions'][parts[2]] = param_value
                                        else:
                                            best_param_conditions[param_index][parts[2]] = param_value
                                else:
                                    # 普通参数
                                    if param_name in ['selected_vars_with_values', 'n_values']:
                                        try:
                                            if param_value and param_value != '':
                                                analysis_data[param_name] = ast.literal_eval(param_value)
                                            else:
                                                analysis_data[param_name] = [] if param_name == 'selected_vars_with_values' else {}
                                        except:
                                            analysis_data[param_name] = param_value
                                    elif param_name in ['is_forward', 'new_before_high_flag', 'new_before_high2_flag', 
                                                       'new_after_high_flag', 'new_after_high2_flag', 
                                                       'new_before_low_flag', 'new_before_low2_flag', 
                                                       'new_after_low_flag', 'new_after_low2_flag']:
                                        analysis_data[param_name] = param_value.lower() in ['true', '1', 'yes', '是']
                                    else:
                                        analysis_data[param_name] = param_value
                                        
                except Exception as gbk_error:
                    QMessageBox.warning(self, "文件编码错误", 
                        f"无法读取CSV文件，请检查文件编码格式！\n错误信息：{gbk_error}")
                    return
            except Exception as read_error:
                QMessageBox.warning(self, "文件读取错误", 
                    f"无法读取CSV文件，请检查文件是否损坏！\n错误信息：{read_error}")
                return
            
            # 检查是否有足够的参数数据
            if not analysis_data:
                QMessageBox.warning(self, "提示", "导入失败，文件中没有找到有效的参数数据！")
                return
            
            # 恢复三次分析的最优参数条件（仅用于展示）
            if best_param_conditions:
                self.best_param_condition_list = best_param_conditions
                print(f"导入时恢复三次分析的最优参数条件：{len(best_param_conditions)}个参数")
            
            # 调用恢复参数的方法
            self.restore_formula_params(analysis_data)
            
            # 显示成功消息
            QMessageBox.information(self, "导入成功", f"已成功导入参数配置！\n共导入 {len(analysis_data)} 个参数")
            
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"导入CSV失败：{e}")
            print(f"导入失败详细错误: {e}")
            import traceback
            traceback.print_exc()
            
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
                
                # 恢复持有率、止盈率、止损率区间
                hold_rate_min_val = param_map.get('component_hold_rate_min', '')
                if hold_rate_min_val:
                    try:
                        hold_rate_val = int(float(hold_rate_min_val))
                        self.hold_rate_min_edit.setText(str(hold_rate_val))
                        print(f"更新持有率最小值: {hold_rate_val}")
                    except Exception as e:
                        print(f"更新持有率最小值失败: {e}")
                
                hold_rate_max_val = param_map.get('component_hold_rate_max', '')
                if hold_rate_max_val:
                    try:
                        hold_rate_val = int(float(hold_rate_max_val))
                        self.hold_rate_max_edit.setText(str(hold_rate_val))
                        print(f"更新持有率最大值: {hold_rate_val}")
                    except Exception as e:
                        print(f"更新持有率最大值失败: {e}")
                
                profit_rate_min_val = param_map.get('component_profit_rate_min', '')
                if profit_rate_min_val:
                    try:
                        profit_rate_val = int(float(profit_rate_min_val))
                        self.profit_rate_min_edit.setText(str(profit_rate_val))
                        print(f"更新止盈率最小值: {profit_rate_val}")
                    except Exception as e:
                        print(f"更新止盈率最小值失败: {e}")
                
                profit_rate_max_val = param_map.get('component_profit_rate_max', '')
                if profit_rate_max_val:
                    try:
                        profit_rate_val = int(float(profit_rate_max_val))
                        self.profit_rate_max_edit.setText(str(profit_rate_val))
                        print(f"更新止盈率最大值: {profit_rate_val}")
                    except Exception as e:
                        print(f"更新止盈率最大值失败: {e}")
                
                loss_rate_min_val = param_map.get('component_loss_rate_min', '')
                if loss_rate_min_val:
                    try:
                        loss_rate_val = int(float(loss_rate_min_val))
                        self.loss_rate_min_edit.setText(str(loss_rate_val))
                        print(f"更新止损率最小值: {loss_rate_val}")
                    except Exception as e:
                        print(f"更新止损率最小值失败: {e}")
                
                loss_rate_max_val = param_map.get('component_loss_rate_max', '')
                if loss_rate_max_val:
                    try:
                        loss_rate_val = int(float(loss_rate_max_val))
                        self.loss_rate_max_edit.setText(str(loss_rate_val))
                        print(f"更新止损率最大值: {loss_rate_val}")
                    except Exception as e:
                        print(f"更新止损率最大值失败: {e}")
                
                # 恢复大于上次最优值百分比
                better_percent_val = param_map.get('component_only_better_trading_plan_percent', '')
                if better_percent_val:
                    try:
                        better_percent_val_float = float(better_percent_val)
                        self.only_better_trading_plan_edit.setText(str(better_percent_val_float))
                        print(f"更新大于上次最优值百分比: {better_percent_val_float}")
                    except Exception as e:
                        print(f"更新大于上次最优值百分比失败: {e}")
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
        
    def get_profit_loss_text_by_category(self):
        """
        根据当前选中的变量类别动态生成止盈止损相关的文本
        返回: (profit_text, loss_text, profit_median_text, loss_median_text)
        """
        # 默认文本
        default_profit_text = "止盈率"
        default_loss_text = "止损率"
        default_profit_median_text = "止盈中位数"
        default_loss_median_text = "止损中位数"
        
        # 如果没有公式选择状态，返回默认文本
        if not hasattr(self.main_window, 'last_formula_select_state') or not self.main_window.last_formula_select_state:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
        # 获取当前选中的变量
        from function.stock_functions import get_abbr_round_only_map
        abbr_round_only_map = get_abbr_round_only_map()
        
        # 检查选中的变量属于哪个类别
        selected_vars = []
        for (zh, en), en_val in abbr_round_only_map.items():
            if en_val in self.main_window.last_formula_select_state:
                var_state = self.main_window.last_formula_select_state[en_val]
                if var_state.get('round_checked', False):  # 检查圆框是否勾选
                    selected_vars.append((zh, en_val))
        
        if not selected_vars:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
        # 根据选中的变量确定类别
        categories = set()
        for zh, en_val in selected_vars:
            if "停盈停损" in zh:
                categories.add("停盈停损")
            elif "停盈止损" in zh:
                categories.add("停盈止损")
            elif "止盈止损" in zh:
                categories.add("止盈止损")
            elif "止盈停损" in zh:
                categories.add("止盈停损")
        
        # 检查是否选择了多种不同类别
        if len(categories) > 1:
            return None, None, None, None
        
        if not categories:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
        category = list(categories)[0]
        
        # 根据类别返回相应的文本
        if category == "停盈停损":
            return "停盈率", "停损率", "停盈中位数", "停损中位数"
        elif category == "停盈止损":
            return "停盈率", "止损率", "停盈中位数", "止损中位数"
        elif category == "止盈止损":
            return "止盈率", "止损率", "止盈中位数", "止损中位数"
        elif category == "止盈停损":
            return "止盈率", "停损率", "止盈中位数", "停损中位数"
        else:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
    
    def _validate_category_selection(self):
        """
        验证组合分析输出值类别选择
        返回: (is_valid, error_message)
        """
        # 如果没有公式选择状态，返回有效
        if not hasattr(self.main_window, 'last_formula_select_state') or not self.main_window.last_formula_select_state:
            return True, None
        
        # 获取当前选中的变量
        from function.stock_functions import get_abbr_round_only_map
        abbr_round_only_map = get_abbr_round_only_map()
        
        # 检查选中的变量属于哪个类别
        selected_vars = []
        for (zh, en), en_val in abbr_round_only_map.items():
            if en_val in self.main_window.last_formula_select_state:
                var_state = self.main_window.last_formula_select_state[en_val]
                if var_state.get('round_checked', False):  # 检查圆框是否勾选
                    selected_vars.append((zh, en_val))
        
        if not selected_vars:
            return False, "请选择组合分析输出值"
        
        # 根据选中的变量确定类别
        categories = set()
        for zh, en_val in selected_vars:
            if "停盈停损" in zh:
                categories.add("停盈停损")
            elif "停盈止损" in zh:
                categories.add("停盈止损")
            elif "止盈止损" in zh:
                categories.add("止盈止损")
            elif "止盈停损" in zh:
                categories.add("止盈停损")
        
        # 检查是否选择了多种不同类别
        if len(categories) > 1:
            return False, "多重组合分析输出选择，请检查"
        
        return True, None

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
            
    def _generate_default_plan_name(self, analysis, params, result):
        """生成默认的操盘方案名称"""
        from datetime import datetime
        
        # 1. 开始值选择方式
        start_option = analysis.get('start_option', '')
        
        # 1.1. 日期宽度
        width = analysis.get('width', '')
        width_str = f"{width}" if width else ""
        
        # 2. 交易方式
        trade_mode = analysis.get('trade_mode', '')
        
        # 3. 创新低新高的一种（只会勾选其中一个）
        new_high_low_type = ""
        if params.get('new_before_high_flag', False):
            new_high_low_type = "创前新高1"
        elif params.get('new_before_high2_flag', False):
            new_high_low_type = "创前新高2"
        elif params.get('new_after_high_flag', False):
            new_high_low_type = "创后新高1"
        elif params.get('new_after_high2_flag', False):
            new_high_low_type = "创后新高2"
        elif params.get('new_before_low_flag', False):
            new_high_low_type = "创前新低1"
        elif params.get('new_before_low2_flag', False):
            new_high_low_type = "创前新低2"
        elif params.get('new_after_low_flag', False):
            new_high_low_type = "创后新低1"
        elif params.get('new_after_low2_flag', False):
            new_high_low_type = "创后新低2"
        
        # 4. 组合输出值
        adjusted_value = result.get('adjusted_value', 0)
        adjusted_value_str = f"{adjusted_value:.2f}" if adjusted_value else "0.00"
        
        # 5. 生成的日期（today 2025-7-7 这种格式，避免文件名中的非法字符）
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 6. 排序方式
        sort_mode = analysis.get('sort_mode', '')
        
        # 组合名称
        plan_name_parts = []
        if start_option:
            plan_name_parts.append(start_option)
        if width_str:
            plan_name_parts.append(width_str)
        if trade_mode:
            plan_name_parts.append(trade_mode)
        if new_high_low_type:
            plan_name_parts.append(new_high_low_type)
        if adjusted_value_str:
            plan_name_parts.append(adjusted_value_str)
        if today:
            plan_name_parts.append(today)
        if sort_mode:
            plan_name_parts.append(sort_mode)
        
        filename = "-".join(plan_name_parts) if plan_name_parts else "操盘方案"
        
        # 清理文件名中的非法字符
        import re
        # 替换Windows文件名中的非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '-', filename)
        # 移除多余的空格和连字符
        filename = re.sub(r'\s+', ' ', filename).strip()
        filename = re.sub(r'-+', '-', filename)
        
        return filename

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
                'after_gt_end_ratio': analysis.get('after_gt_end_ratio', ''),
                'after_gt_start_ratio': analysis.get('after_gt_start_ratio', ''),
                'stop_loss_inc_rate': analysis.get('stop_loss_inc_rate', ''),
                'stop_loss_after_gt_end_ratio': analysis.get('stop_loss_after_gt_end_ratio', ''),
                'stop_loss_after_gt_start_ratio': analysis.get('stop_loss_after_gt_start_ratio', ''),
                'expr': analysis.get('expr', ''),
                'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
                'n_values': analysis.get('n_values', [])
            })

            print(f"component_analysis_ui selected_vars_with_values: {params.get('selected_vars_with_values', [])}")
            
            # 确保component_analysis_count被正确添加到params中
            if 'component_analysis_count' not in params:
                params['component_analysis_count'] = analysis.get('component_analysis_count', '')
            
            # 生成默认的操盘方案名称
            plan_name = self._generate_default_plan_name(analysis, params, result)
            
            # 创建操盘方案
            trading_plan = {
                'plan_id': i + 1,
                'plan_name': plan_name,
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
            
        # 直接按adjusted_value排序，保持排序状态
        trading_plan_list.sort(key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
        
        return trading_plan_list
        
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
                'after_gt_end_ratio': analysis.get('after_gt_end_ratio', ''),
                'after_gt_start_ratio': analysis.get('after_gt_start_ratio', ''),
                'stop_loss_inc_rate': analysis.get('stop_loss_inc_rate', ''),
                'stop_loss_after_gt_end_ratio': analysis.get('stop_loss_after_gt_end_ratio', ''),
                'stop_loss_after_gt_start_ratio': analysis.get('stop_loss_after_gt_start_ratio', ''),
                'expr': analysis.get('expr', ''),
                'selected_vars_with_values': analysis.get('selected_vars_with_values', []),
                'n_values': analysis.get('n_values', [])
            })
            
            # 确保component_analysis_count被正确添加到params中
            if 'component_analysis_count' not in params:
                params['component_analysis_count'] = analysis.get('component_analysis_count', '')
            
            # 生成默认的操盘方案名称
            plan_name = self._generate_default_plan_name(analysis, params, top_result)
            
            # 创建操盘方案
            trading_plan = {
                'plan_id': len(self.main_window.trading_plan_list) + 1,
                'plan_name': plan_name,
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
            
            # 重新排序
            sorted_plan_list = sorted(self.main_window.trading_plan_list, key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
            
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
            'component_analysis_end_date', 'component_analysis_count', 'component_hold_rate_min', 'component_hold_rate_max', 'component_profit_rate_min', 'component_profit_rate_max', 'component_loss_rate_min', 'component_loss_rate_max', 'component_only_better_trading_plan_percent',
            'cpu_cores',
            'trade_mode',
            'stop_loss_inc_rate', 'stop_loss_after_gt_end_edit', 'stop_loss_after_gt_start_edit',
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
                # 特殊处理：组合分析率值区间参数
                elif k == 'component_hold_rate_min':
                    try:
                        v = int(self.hold_rate_min_edit.text())
                    except ValueError:
                        v = 0
                elif k == 'component_hold_rate_max':
                    try:
                        v = int(self.hold_rate_max_edit.text())
                    except ValueError:
                        v = 100
                elif k == 'component_profit_rate_min':
                    try:
                        v = int(self.profit_rate_min_edit.text())
                    except ValueError:
                        v = 0
                elif k == 'component_profit_rate_max':
                    try:
                        v = int(self.profit_rate_max_edit.text())
                    except ValueError:
                        v = 100
                elif k == 'component_loss_rate_min':
                    try:
                        v = int(self.loss_rate_min_edit.text())
                    except ValueError:
                        v = 0
                elif k == 'component_loss_rate_max':
                    try:
                        v = int(self.loss_rate_max_edit.text())
                    except ValueError:
                        v = 100
                elif k == 'component_only_better_trading_plan_percent':
                    try:
                        v = float(self.only_better_trading_plan_edit.text())
                    except ValueError:
                        v = 0.0
                elif k == 'component_analysis_count':
                    v = self.analysis_count_spin.value()
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
        

        
    def _update_last_best_value_display(self):
        """更新上次分析最优值显示"""
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
        
        # 更新锁定最优值显示
        locked_value = getattr(self.main_window, 'locked_adjusted_value', None)
        if locked_value is not None:
            try:
                # 尝试转换为浮点数并格式化显示
                locked_value_float = float(locked_value)
                self.locked_best_value_display.setText(f"{locked_value_float:.2f}")
            except (ValueError, TypeError):
                # 如果转换失败，直接显示原值
                self.locked_best_value_display.setText(str(locked_value))
        else:
            self.locked_best_value_display.setText("无")

    def _on_clear_last_best_value(self):
        """清空上次分析最优值"""
        self.main_window.last_adjusted_value = None
        self._update_last_best_value_display()
    
    def _on_clear_locked_best_value(self):
        """清空锁定最优值"""
        self.main_window.locked_adjusted_value = None
        self._update_last_best_value_display()
    
    def _get_new_high_low_types(self):
        """
        根据勾选情况获取创新高/创新低类型
        返回: (new_high_low1_type, new_high_low2_type)
        """
        new_high_low1_type = "未勾选创前后新高低1"
        new_high_low2_type = "未勾选创前后新高低2"
        
        # 检查哪个flag被勾选了
        if self.main_window.new_before_high_flag_checkbox.isChecked():
            new_high_low1_type = "创前新高1"
        elif self.main_window.new_after_high_flag_checkbox.isChecked():
            new_high_low1_type = "创后新高1"
        elif self.main_window.new_before_low_flag_checkbox.isChecked():
            new_high_low1_type = "创前新低1"
        elif self.main_window.new_after_low_flag_checkbox.isChecked():
            new_high_low1_type = "创后新低1"
            
        if self.main_window.new_before_high2_flag_checkbox.isChecked():
            new_high_low2_type = "创前新高2"
        elif self.main_window.new_after_high2_flag_checkbox.isChecked():
            new_high_low2_type = "创后新高2"
        elif self.main_window.new_before_low2_flag_checkbox.isChecked():
            new_high_low2_type = "创前新低2"
        elif self.main_window.new_after_low2_flag_checkbox.isChecked():
            new_high_low2_type = "创后新低2"
        
        return new_high_low1_type, new_high_low2_type

    def _validate_abbr_round_only_selection(self):
        """验证组合输出参数选择"""
        try:
            # 创建临时的公式选股控件来获取当前选择状态
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            
            # 创建临时控件（不显示界面）
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
            
            # 恢复保存的状态（如果有的话）
            if hasattr(self.main_window, 'last_formula_select_state'):
                temp_formula_widget.set_state(self.main_window.last_formula_select_state)
            
            # 获取get_abbr_round_only_map的勾选状态
            selected_vars = temp_formula_widget.get_round_only_map_selected_vars()
            
            # 清理临时控件
            temp_formula_widget.deleteLater()
            
            # 如果没有任何变量被勾选，则提示错误
            if not selected_vars:
                QMessageBox.warning(self, "提示", "没有选择组合输出参数，请检查！")
                return False
            
            # 检查选中的变量属于哪些类别
            categories = self._categorize_selected_vars(selected_vars)
            
            # 如果有多于一个类别被选中，则提示错误
            if len(categories) > 1:
                QMessageBox.warning(self, "提示", "组合输出多重选择，请检查！")
                return False
            
            return True
            
        except Exception as e:
            print(f"验证组合输出参数选择时出错: {e}")
            QMessageBox.warning(self, "错误", f"验证组合输出参数选择时出错: {e}")
            return False
    
    def _categorize_selected_vars(self, selected_vars):
        """将选中的变量按类别分组"""
        categories = set()
        
        for var in selected_vars:
            if any(keyword in var for keyword in ['mean_with_nan', 'mean_daily_change', 'comprehensive_stop_daily_change', 'bottom_first_with_nan', 'bottom_second_with_nan', 'bottom_third_with_nan', 'bottom_fourth_with_nan', 'bottom_nth_with_nan']):
                categories.add('停盈停损')
            elif any(keyword in var for keyword in ['mean_stop_and_take_with_nan', 'mean_stop_and_take_daily_change', 'comprehensive_stop_and_take_change', 'bottom_first_stop_and_take_with_nan', 'bottom_second_stop_and_take_with_nan', 'bottom_third_stop_and_take_with_nan', 'bottom_fourth_stop_and_take_with_nan', 'bottom_nth_stop_and_take_with_nan']):
                categories.add('停盈止损')
            elif any(keyword in var for keyword in ['mean_adjust_with_nan', 'mean_adjust_daily_change', 'comprehensive_daily_change', 'adjust_bottom_first_with_nan', 'adjust_bottom_second_with_nan', 'adjust_bottom_third_with_nan', 'adjust_bottom_fourth_with_nan', 'bottom_nth_adjust_with_nan']):
                categories.add('止盈止损')
            elif any(keyword in var for keyword in ['mean_take_and_stop_with_nan', 'mean_take_and_stop_daily_change', 'comprehensive_take_and_stop_change', 'bottom_first_take_and_stop_with_nan', 'bottom_second_take_and_stop_with_nan', 'bottom_third_take_and_stop_with_nan', 'bottom_fourth_take_and_stop_with_nan', 'bottom_nth_take_and_stop_with_nan']):
                categories.add('止盈停损')
        
        return categories

    def generate_first_stage_formulas(self, variable_name, step_divisor=10, base_formula=None):
        """
        生成三次分析第一轮的公式列表
        参数:
        - variable_name: 变量名称
        - step_divisor: 步长除数
        - base_formula: 基础公式，如果为None则使用默认公式
        返回: 公式列表
        """
        # 优先使用参数特定的基准统计，如果没有则使用全局统计
        overall_stats = None
        if hasattr(self, 'three_stage_param_baseline_stats') and self.three_stage_param_baseline_stats:
            overall_stats = self.three_stage_param_baseline_stats
        else:
            overall_stats = self.main_window.overall_stats
            
        if not overall_stats:
            log_message = f"没有可用的统计结果，无法对变量 {variable_name} 进行三次分析"
            print(log_message)
            self.log_three_analysis(log_message)
            return []

        max_key = f"{variable_name}_max"
        min_key = f"{variable_name}_min"
        max_value = overall_stats.get(max_key)
        min_value = overall_stats.get(min_key)
        
        # 调试信息：打印统计值获取情况
        # log_message = f"变量 {variable_name} 统计值获取情况: max_key={max_key}, min_key={min_key}, max_value={max_value}, min_value={min_value}"
        # print(log_message)
        # self.log_three_analysis(log_message)
        
        if max_value is None or min_value is None:
            log_message = f"变量 {variable_name} 缺少统计值，无法进行三次分析"
            print(log_message)
            self.log_three_analysis(log_message)
            return []

        abs_max = max(abs(max_value), abs(min_value))
        try:
            divisor = float(step_divisor) if step_divisor else 10.0
        except Exception:
            divisor = 10.0
        initial_step = int(abs_max / divisor)
        if initial_step <= 0:
            initial_step = 1

        print(f"=== 变量 {variable_name} 第一轮分析 ===")
        print(f"统计值: min={min_value}, max={max_value}")
        print(f"初始步长: {initial_step}")

        # 如果没有提供基础公式，优先使用last_formula_expr，否则使用默认公式
        if base_formula is None:
            if hasattr(self.main_window, 'last_formula_expr') and self.main_window.last_formula_expr:
                base_formula = self.main_window.last_formula_expr
                print(f"使用last_formula_expr作为基础公式")
            else:
                base_formula = "if True:\n    result = 0\nelse:\n    result = 0"
                print(f"使用默认公式作为基础公式")

        print(f"基础公式: {base_formula}")

        # 获取排序方式（与二次/组合分析保持一致）
        user_sort_mode = getattr(self.main_window, 'last_sort_mode', '最大值排序')

        # 获取二次分析次数限制，用于限制生成的公式数量
        secondary_analysis_count = getattr(self, 'secondary_analysis_count_spin', None)
        if secondary_analysis_count:
            max_formulas = secondary_analysis_count.value()
        else:
            max_formulas = 1  # 默认值
        
        # 生成全方向组合 = 左单向 + 右单向，然后去重并处理下限=上限的情况
        formulas = []
        pairs = set()

        # 参考二次分析的逻辑：生成笛卡尔积组合
        # 左方向：上限逐渐减步长，生成max_formulas个值
        left_upper_values = []
        current_upper_val = max_value
        for i in range(max_formulas):
            if min_value is not None and current_upper_val < min_value:
                break
            left_upper_values.append(round(current_upper_val, 2))
            current_upper_val -= initial_step
        
        # 右方向：下限逐渐加步长，生成max_formulas个值
        right_lower_values = []
        current_lower_val = min_value
        for i in range(max_formulas):
            if max_value is not None and current_lower_val > max_value:
                break
            right_lower_values.append(round(current_lower_val, 2))
            current_lower_val += initial_step
        
        # 生成笛卡尔积组合
        for left_upper in left_upper_values:
            for right_lower in right_lower_values:
                if right_lower <= left_upper:  # 确保下限不大于上限
                    pairs.add((right_lower, left_upper))
        
        # 统计生成的公式数量
        left_formula_count = len(left_upper_values)
        right_formula_count = len(right_lower_values)

        # 处理下限=上限的情况：生成一个公式 "参数 >= 下限 and 参数 <= 上限"
        if min_value == max_value:
            # 当上下限相等时，添加一个特殊的公式组合
            equal_bound_value = round(min_value, 2)
            pairs.add((equal_bound_value, equal_bound_value))

        for lower, upper in sorted(pairs):
            modified_formula = self._modify_formula_for_variable(base_formula, variable_name, lower, upper)
            formulas.append({
                'formula': modified_formula,
                'sort_mode': user_sort_mode,
                'variable': variable_name,
                'lower': lower,
                'upper': upper,
                'step': initial_step
            })

        print(f"生成了 {len(formulas)} 个公式组合")
        print("公式列表:")
        for i, formula_info in enumerate(formulas):
            print(f"  {i+1}. {variable_name} >= {formula_info['lower']} and {variable_name} <= {formula_info['upper']}")

        return formulas

    def _modify_formula_for_variable(self, base_formula, variable_name, lower, upper):
        """修改基础公式，替换指定变量的条件"""
        import re
        if_match = re.search(r'if\s*(.*?):', base_formula, re.DOTALL)
        else_match = re.search(r'else:\s*(.*)', base_formula, re.DOTALL)
        result_match = re.search(r'result\s*=\s*(.*?)(?:\n|$)', base_formula)

        base_conditions_str = if_match.group(1).strip() if if_match else "True"
        base_result_expr = result_match.group(1).strip() if result_match else "0"
        base_else_block = else_match.group(1).strip() if else_match else "result = 0"

        if base_conditions_str.startswith('(') and base_conditions_str.endswith(')'):
            base_conditions_str = base_conditions_str[1:-1].strip()

        # 修正正则转义，确保能正确匹配并移除目标变量已有的区间/单项条件
        pattern_single_cond = r'\b' + re.escape(variable_name) + r'\s*(?:>=|<=|==|!=|>|<)\s*[\-\d\.]+'
        pattern_range_cond1 = r'\b' + re.escape(variable_name) + r'\s*>=\s*[\-\d\.]+\s*and\s*\b' + re.escape(variable_name) + r'\s*<=\s*[\-\d\.]+'
        pattern_range_cond2 = r'\b' + re.escape(variable_name) + r'\s*<=\s*[\-\d\.]+\s*and\s*\b' + re.escape(variable_name) + r'\s*>=\s*[\-\d\.]+'
        pattern_logic_var = r'\b' + re.escape(variable_name) + r'\b(?!\s*(?:>=|<=|==|!=|>|<))'

        temp_conditions_str = base_conditions_str
        temp_conditions_str = re.sub(pattern_range_cond1, '', temp_conditions_str)
        temp_conditions_str = re.sub(pattern_range_cond2, '', temp_conditions_str)
        temp_conditions_str = re.sub(pattern_single_cond, '', temp_conditions_str)
        temp_conditions_str = re.sub(pattern_logic_var, '', temp_conditions_str)

        temp_conditions_str = re.sub(r'\s*and\s*and\s*', ' and ', temp_conditions_str).strip()
        temp_conditions_str = temp_conditions_str.strip(' and').strip()

        if not temp_conditions_str:
            current_conditions = ["True"]
        else:
            split_conditions = re.split(r'\s+and\s+', temp_conditions_str)
            current_conditions = [c.strip() for c in split_conditions if c.strip()]

        # 如果 lower 和 upper 为 None，表示要移除该变量的条件
        if lower is None and upper is None:
            # 移除该变量的所有条件，不添加新条件
            pass
        else:
            # 添加新的变量条件
            new_var_condition = f"{variable_name} >= {lower} and {variable_name} <= {upper}"
            if new_var_condition not in current_conditions:
                current_conditions.append(new_var_condition)

        # 如果存在其它条件，移除冗余的 True
        if "True" in current_conditions and len(current_conditions) > 1:
            current_conditions = [c for c in current_conditions if c != "True"]

        final_conditions_str = " and ".join(current_conditions)
        if final_conditions_str == "True":
            final_formula = f"if True:\n    result = {base_result_expr}\nelse:\n    {base_else_block}"
        else:
            final_formula = f"if {final_conditions_str}:\n    result = {base_result_expr}\nelse:\n    {base_else_block}"

        return final_formula

    def on_export_three_stage_clicked(self):
        """导出三次分析结果为Excel文件"""
        try:
            # 检查是否有最优参数条件
            if not hasattr(self.main_window, 'best_param_condition_list') or not self.main_window.best_param_condition_list:
                QMessageBox.warning(self, "提示", "没有可导出的最优参数条件数据！")
                return
            
            # 选择保存文件路径
            dialog = QFileDialog(self, "导出三次分析结果")
            dialog.setAcceptMode(QFileDialog.AcceptSave)
            dialog.setNameFilter("Excel文件 (*.xlsx)")
            dialog.setDefaultSuffix("xlsx")
            
            if dialog.exec_() != QFileDialog.Accepted:
                return
            
            file_path = dialog.selectedFiles()[0]
            if not file_path:
                return
            
            # 准备导出数据
            best_param_conditions = self.main_window.best_param_condition_list
            no_better_results = getattr(self.main_window, 'no_better_result_list', [])
            median_values = getattr(self, 'three_stage_param_baseline_stats', {})
            
            # 创建Excel文件
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 导出最优参数条件（包含sort_value、参数名称、最优值、上下限、中值）
                if best_param_conditions:
                    export_conditions = []
                    for i, condition in enumerate(best_param_conditions):
                        for param_name, condition_text in condition.items():
                            # 从条件文本中提取信息
                            lower_match = re.search(r'下限(-?[\d\.]+)', condition_text)
                            upper_match = re.search(r'上限(-?[\d\.]+)', condition_text)
                            output_value_match = re.search(r'组合排序输出值为：([\d\.]+)', condition_text)
                            # 修正median值的提取，匹配格式：参数名_median：数值
                            median_match = re.search(rf'{re.escape(param_name)}_median：(-?[\d\.]+)', condition_text)
                            # 提取正值中值和负值中值
                            positive_median_match = re.search(rf'{re.escape(param_name)}_positive_median：(-?[\d\.]+)', condition_text)
                            negative_median_match = re.search(rf'{re.escape(param_name)}_negative_median：(-?[\d\.]+)', condition_text)
                            
                            # 获取sort_value（参数对应的序号）
                            sort_value = self._get_param_sort_value(param_name)
                            
                            # 格式化最优值为两位小数
                            optimal_value = ''
                            if output_value_match:
                                try:
                                    optimal_value = f"{float(output_value_match.group(1)):.2f}"
                                except (ValueError, TypeError):
                                    optimal_value = output_value_match.group(1)
                            else:
                                optimal_value = ''
                            
                            # 添加调试信息
                            print(f"导出参数 {param_name} 的条件文本：{condition_text}")
                            print(f"  下限匹配：{lower_match.group(1) if lower_match else '未匹配'}")
                            print(f"  上限匹配：{upper_match.group(1) if upper_match else '未匹配'}")
                            print(f"  输出值匹配：{output_value_match.group(1) if output_value_match else '未匹配'}")
                            print(f"  中值匹配：{median_match.group(1) if median_match else '未匹配'}")
                            print(f"  正值中值匹配：{positive_median_match.group(1) if positive_median_match else '未匹配'}")
                            print(f"  负值中值匹配：{negative_median_match.group(1) if negative_median_match else '未匹配'}")
                            print(f"  格式化后的最优值：{optimal_value}")
                            
                            row_data = {
                                '三次分析序号': sort_value if sort_value is not None else i + 1,
                                '参数名称': param_name,
                                '最优值': optimal_value,
                                '最优上限': upper_match.group(1) if upper_match else '',
                                '最优下限': lower_match.group(1) if lower_match else '',
                                '最优中值': median_match.group(1) if median_match else '',
                                '正值中值': positive_median_match.group(1) if positive_median_match else '',
                                '负值中值': negative_median_match.group(1) if negative_median_match else ''
                            }
                            export_conditions.append(row_data)
                    
                    # 如果有无最优结果的条件，添加空行分隔，然后添加无最优结果的条件
                    if no_better_results:
                        # 添加空行分隔
                        empty_row = {
                            '三次分析序号': '',
                            '参数名称': '',
                            '最优值': '',
                            '最优上限': '',
                            '最优下限': '',
                            '最优中值': '',
                            '正值中值': '',
                            '负值中值': ''
                        }
                        export_conditions.append(empty_row)
                        
                        # 处理无最优结果的条件
                        for condition in no_better_results:
                            for param_name, condition_text in condition.items():
                                # 从条件文本中提取轮次信息
                                round_match = re.search(r'第([一二三])次分析无最优', condition_text)
                                round_num = round_match.group(1) if round_match else ''
                                round_map = {'一': '1', '二': '2', '三': '3'}
                                round_value = round_map.get(round_num, round_num)
                                
                                row_data = {
                                    '三次分析序号': round_value,
                                    '参数名称': param_name,
                                    '最优值': '无最优',
                                    '最优上限': '',
                                    '最优下限': '',
                                    '最优中值': '',
                                    '正值中值': '',
                                    '负值中值': ''
                                }
                                export_conditions.append(row_data)
                    
                    df_conditions = pd.DataFrame(export_conditions)
                    df_conditions.to_excel(writer, sheet_name='最优参数条件', index=False)
            
            QMessageBox.information(self, "导出成功", f"已成功导出三次分析结果到 {file_path}")
            
        except Exception as e:
            print(f"导出三次分析结果失败：{e}")
            QMessageBox.critical(self, "导出失败", f"导出三次分析结果失败：{e}")
    
    def _get_param_sort_value(self, param_name):
        """获取参数对应的sort_value（序号）"""
        try:
            # 先检查last_formula_select_state（普通参数）
            if hasattr(self.main_window, 'last_formula_select_state') and self.main_window.last_formula_select_state:
                if param_name in self.main_window.last_formula_select_state:
                    var_state = self.main_window.last_formula_select_state[param_name]
                    if 'sort' in var_state and var_state['sort'].strip():
                        try:
                            return int(var_state['sort'].strip())
                        except ValueError:
                            pass
            
            # 再检查forward_param_state（向前参数）
            if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                if param_name in self.main_window.forward_param_state:
                    var_state = self.main_window.forward_param_state[param_name]
                    if 'sort' in var_state and var_state['sort'].strip():
                        try:
                            return int(var_state['sort'].strip())
                        except ValueError:
                            pass
            
            # 如果都没有找到，返回None
            return None
            
        except Exception as e:
            print(f"获取参数 {param_name} 的sort_value时出错：{e}")
            return None
    
    def on_import_three_stage_clicked(self):
        """导入三次分析结果Excel文件"""
        try:
            # 选择要导入的文件
            dialog = QFileDialog(self, "导入三次分析结果")
            dialog.setAcceptMode(QFileDialog.AcceptOpen)
            dialog.setNameFilter("Excel文件 (*.xlsx)")
            
            if dialog.exec_() != QFileDialog.Accepted:
                return
            
            file_path = dialog.selectedFiles()[0]
            if not file_path:
                return
            
            # 读取Excel文件
            excel_file = pd.ExcelFile(file_path)
            
            # 读取最优参数条件
            if '最优参数条件' in excel_file.sheet_names:
                df_conditions = pd.read_excel(file_path, sheet_name='最优参数条件')
                best_param_conditions = []
                
                best_param_conditions = []
                no_better_results = []
                
                for _, row in df_conditions.iterrows():
                    param_name = row.get('参数名称', '')
                    sort_value = row.get('三次分析序号', '')
                    lower_value = row.get('最优下限', '')
                    upper_value = row.get('最优上限', '')
                    output_value = row.get('最优值', '')
                    median_value = row.get('最优中值', '')
                    positive_median_value = row.get('正值中值', '')
                    negative_median_value = row.get('负值中值', '')
                    
                    if param_name:
                        # 检查是否为无最优结果
                        if output_value == '无最优':
                            # 无最优结果的情况
                            condition_text = f"{param_name}：第{sort_value}次分析无最优"
                            no_better_results.append({param_name: condition_text})
                        else:
                            # 有最优结果的情况
                            # 重建条件文本，包含正值中值和负值中值
                            condition_text = f"最优条件为：下限{lower_value}，上限{upper_value}， 组合排序输出值为：{output_value}，{param_name}_median：{median_value}，{param_name}_positive_median：{positive_median_value}，{param_name}_negative_median：{negative_median_value}"
                            best_param_conditions.append({param_name: condition_text})
                            
                            # 恢复sort_value
                            if sort_value != '':
                                self._restore_param_sort_value(param_name, sort_value)
                
                # 保存到主窗口
                self.main_window.best_param_condition_list = best_param_conditions
                self.main_window.no_better_result_list = no_better_results
                print(f"导入最优参数条件：{len(best_param_conditions)}条，无最优结果：{len(no_better_results)}条")
            
            QMessageBox.information(self, "导入成功", f"已成功导入三次分析结果从 {file_path}")
            
        except Exception as e:
            print(f"导入三次分析结果失败：{e}")
            QMessageBox.critical(self, "导入失败", f"导入三次分析结果失败：{e}")
    

    


    def _restore_param_sort_value(self, param_name, sort_value):
        """恢复指定参数的sort_value"""
        try:
            # 创建临时的FormulaSelectWidget来访问参数控件
            from function.stock_functions import get_abbr_map, get_abbr_logic_map, get_abbr_round_map, FormulaSelectWidget
            
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            
            # 创建临时控件（不显示界面）
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
            
            # 恢复保存的状态（如果有的话）
            if hasattr(self.main_window, 'last_formula_select_state'):
                temp_formula_widget.set_state(self.main_window.last_formula_select_state)
            
            # 通过var_widgets访问参数控件
            if param_name in temp_formula_widget.var_widgets:
                widgets = temp_formula_widget.var_widgets[param_name]
                
                # 设置sort控件的值
                if 'sort' in widgets:
                    # 将sort_value转换为字符串并设置
                    widgets['sort'].setCurrentText(str(sort_value))
                    print(f"已恢复参数 {param_name} 的sort_value：{sort_value}")
                    
                    # 同步到主窗口状态
                    if hasattr(self.main_window, 'last_formula_select_state'):
                        if param_name not in self.main_window.last_formula_select_state:
                            self.main_window.last_formula_select_state[param_name] = {}
                        self.main_window.last_formula_select_state[param_name]['sort'] = str(sort_value)
                    
                    # 清理临时控件
                    temp_formula_widget.deleteLater()
                    return True
                else:
                    print(f"参数 {param_name} 没有sort控件")
                    temp_formula_widget.deleteLater()
                    return False
            else:
                print(f"未找到参数 {param_name} 对应的控件")
                temp_formula_widget.deleteLater()
                return False
                
        except Exception as e:
            print(f"恢复参数 {param_name} 的sort_value时出错：{e}")
            return False


class AnalysisDetailWindow(QMainWindow):
    def __init__(self, analysis_data, create_table_func, idx):
        super().__init__(None)
        self.setWindowTitle(f"组合分析结果详情 - 第{idx+1}行")
        self.setMinimumSize(2350, 800)
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