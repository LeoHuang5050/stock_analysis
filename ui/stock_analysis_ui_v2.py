import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDateEdit, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QLineEdit, QDialog, QMessageBox, QFrame, QStackedLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QDate, QItemSelectionModel
from PyQt5.QtGui import QKeySequence, QGuiApplication, QIntValidator, QPixmap, QDoubleValidator, QValidator
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler
from function.stock_functions import show_continuous_sum_table, EXPR_PLACEHOLDER_TEXT, calculate_analysis_result
from ui.common_widgets import CopyableTableWidget
import gc
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
import math
import json
import os
from decimal import Decimal, ROUND_HALF_UP
from multiprocessing import cpu_count
from datetime import datetime
from ui.component_analysis_ui import ComponentAnalysisWidget
from ui.trading_plan_ui import TradingPlanWidget

class Tab4SpaceTextEdit(QTextEdit):
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            self.insertPlainText('    ')
        else:
            super().keyPressEvent(event)

class ExprLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑组合表达式")
        layout = QVBoxLayout(dialog)
        tip_label = QLabel(
            "INC:递增值，AGE:后值大于结束地址值，AGS:后值大于前值返回值\n"
            "需要严格按照python表达式规则填入。\n"
            "规则提醒：\n"
            "1. 每个条件、赋值、if/else等都要符合python语法缩进（建议用4个空格）。\n"
            "2. 赋值用=，判断用==，不等于用!=。\n"
            "3. 逻辑与用and，或用or，非用not。\n"
            "4. 代码块必须用冒号结尾（如if/else/for/while等）。\n"
            "5. result变量必须在表达式中赋值，作为最终输出。\n"
            "6. 支持多行表达式，注意缩进和语法。\n"
            "示例：\n"
            "if INC != 0:\n    result = INC\nelse:\n    result = 0\n"
        )
        tip_label.setStyleSheet("color:gray;")
        layout.addWidget(tip_label)
        text_edit = Tab4SpaceTextEdit()
        text_edit.setPlainText(self.text())
        layout.addWidget(text_edit)
        btn_ok = QPushButton("确定")
        layout.addWidget(btn_ok)
        def on_ok():
            expr_text = text_edit.toPlainText()
            try:
                compile(expr_text, '<string>', 'exec')
                self.setText(expr_text)
                # 不再同步到主界面 formula_expr_edit，避免操作值公式和选股公式混淆
                dialog.accept()
            except SyntaxError as e:
                QMessageBox.warning(dialog, "语法错误", f"表达式存在语法错误，请检查！\n\n{e}")
        btn_ok.clicked.connect(on_ok)
        dialog.exec_()

class ExprEditDialog(QDialog):
    def __init__(self, initial_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑操作值表达式")
        layout = QVBoxLayout(self)
        tip_label = QLabel(EXPR_PLACEHOLDER_TEXT)
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color:gray;")
        layout.addWidget(tip_label)
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)
        btn_ok = QPushButton("确定")
        layout.addWidget(btn_ok)
        btn_ok.clicked.connect(self.accept)
    def get_text(self):
        return self.text_edit.toPlainText()

class ValidatedExprEdit(QTextEdit):
    def focusOutEvent(self, event):
        expr = self.toPlainText()
        try:
            compile(expr, '<string>', 'exec')
        except SyntaxError as e:
            QMessageBox.warning(self, "表达式语法错误", f"表达式存在语法错误，请检查！\n\n{e}")
        super().focusOutEvent(event)

class NonPositiveValidator(QValidator):
    """自定义验证器，只允许输入非正数（0或负数）"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def validate(self, input_str, pos):
        if not input_str:
            return QValidator.Acceptable, input_str, pos
        
        # 允许负号开头
        if input_str == '-':
            return QValidator.Intermediate, input_str, pos
        
        # 允许小数点
        if input_str == '.':
            return QValidator.Intermediate, input_str, pos
        
        # 允许负号后跟小数点
        if input_str == '-.':
            return QValidator.Intermediate, input_str, pos
        
        try:
            value = float(input_str)
            # 只允许非正数（0或负数）
            if value <= 0:
                return QValidator.Acceptable, input_str, pos
            else:
                return QValidator.Invalid, input_str, pos
        except ValueError:
            # 检查是否是有效的数字格式（中间状态）
            import re
            pattern = r'^-?\d*\.?\d*$'
            if re.match(pattern, input_str):
                return QValidator.Intermediate, input_str, pos
            else:
                return QValidator.Invalid, input_str, pos

class StockAnalysisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        # 初始化变量
        self.last_formula_expr = ''
        self.last_expr = ''  # 新增：操作值表达式缓存
        self.last_select_count = 10
        self.last_sort_mode = '最大值排序'
        self.last_formula_select_state = {}  # 初始化公式选股状态
        self.last_analysis_start_date = ''
        self.last_analysis_end_date = ''
        self.cached_component_analysis_results = None
        self.init_ui()
        self.connect_signals()
        # 默认最大化显示
        self.showMaximized()
        # 统一缓存变量
        self.last_end_date = None
        self.last_calculate_result = None
        # 加载参数
        self.load_config()

    def init_ui(self):
        # 设置窗口标题为当前exe文件名（不带扩展名）
        exe_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.setWindowTitle(exe_name)
        # 移除固定大小设置
        # self.setFixedSize(1200, 800)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # 顶部参数输入区
        top_widget = QWidget()
        top_grid = QGridLayout(top_widget)
        top_grid.setHorizontalSpacing(20)
        top_widget.setLayout(top_grid)
        col_widths = [170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170]

        # 第一行控件
        self.label = QLabel("请上传数据文件：")
        self.upload_btn = QPushButton("上传数据文件")
        self.date_label = QLabel("请选择结束日期：")
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setDisplayFormat("yyyy/M/d")
        # 设置默认值为今天
        self.date_picker.setDate(QDate.currentDate())
        # 绑定日期修正事件
        self.date_picker.editingFinished.connect(self._fix_date_range)

        # CPU核心数控件
        cpu_widget = QWidget()
        cpu_layout = QHBoxLayout()
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(5)
        cpu_layout.setAlignment(Qt.AlignLeft)
        self.cpu_label = QLabel("允许CPU运行核心数")
        self.cpu_spin = QSpinBox()
        self.cpu_spin.setMinimum(1)
        # 获取实际CPU核心数
        max_cores = cpu_count()
        self.cpu_spin.setMaximum(max_cores)  # 设置为实际CPU核心数
        self.cpu_spin.setValue(min(10, max_cores))  # 默认值设为4或实际核心数（取较小值）
        self.cpu_spin.setFixedWidth(60)
        self.cpu_max_label = QLabel(f"当前CPU配置最大可设置: {max_cores}")
        self.cpu_max_label.setStyleSheet("font-weight: bold;")

        # 问号图标及提示
        self.cpu_help_label = QLabel()
        self.cpu_help_label.setText("❓")
        self.cpu_help_label.setStyleSheet("color: #0078d7; font-size: 16px;")
        self.cpu_help_label.setToolTip("增大CPU核心数一定程度上会加快计算速度，但是可能根据电脑不同引发异常，请根据实际情况设置")
        self.cpu_help_label.setEnabled(True)
        self.cpu_help_label.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_spin)
        cpu_layout.addWidget(self.cpu_max_label)
        cpu_layout.addWidget(self.cpu_help_label)
        cpu_widget.setLayout(cpu_layout)

        # 日期宽度控件
        width_widget = QWidget()
        width_layout = QHBoxLayout()
        width_layout.setContentsMargins(0, 0, 0, 0)
        width_layout.setSpacing(5)
        width_layout.setAlignment(Qt.AlignLeft)
        self.width_label = QLabel("请选择日期宽度")
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(100)
        self.width_spin.setValue(0)
        self.width_spin.setFixedWidth(30)
        width_layout.addWidget(self.width_label)
        width_layout.addWidget(self.width_spin)
        width_widget.setLayout(width_layout)

        # 开始日期值选择控件
        start_option_widget = QWidget()
        start_option_layout = QHBoxLayout()
        start_option_layout.setContentsMargins(0, 0, 0, 0)
        start_option_layout.setSpacing(5)
        start_option_layout.setAlignment(Qt.AlignLeft)
        self.start_option_label = QLabel("开始日期值选择")
        self.start_option_combo = QComboBox()
        self.start_option_combo.addItems(["开始值", "最大值", "最小值", "接近值"])
        self.start_option_combo.setFixedWidth(80)
        start_option_layout.addWidget(self.start_option_label)
        start_option_layout.addWidget(self.start_option_combo)
        start_option_widget.setLayout(start_option_layout)

        # 前移天数控件
        shift_widget = QWidget()
        shift_layout = QHBoxLayout()
        shift_layout.setContentsMargins(0, 0, 0, 0)
        shift_layout.setSpacing(5)
        shift_layout.setAlignment(Qt.AlignLeft)
        self.shift_label = QLabel("前移天数")
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(-1)
        self.shift_spin.setMaximum(1)
        self.shift_spin.setValue(0)
        self.shift_spin.setFixedWidth(60)
        shift_layout.addWidget(self.shift_label)
        shift_layout.addWidget(self.shift_spin)
        shift_widget.setLayout(shift_layout)

        self.direction_checkbox = QCheckBox("是否计算向前")
        self.range_label = QLabel("开始日到结束日之间最高价/最低价小于")
        self.range_value_edit = QLineEdit()
        # 创建连续累加值绝对值小于控件
        abs_sum_widget = QWidget()
        abs_sum_layout = QHBoxLayout()
        abs_sum_layout.setContentsMargins(0, 0, 0, 0)
        abs_sum_layout.setSpacing(5)
        abs_sum_layout.setAlignment(Qt.AlignLeft)
        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        self.continuous_abs_threshold_edit = QLineEdit()
        self.continuous_abs_threshold_edit.setFixedWidth(60)
        abs_sum_layout.addWidget(self.abs_sum_label)
        abs_sum_layout.addWidget(self.continuous_abs_threshold_edit)
        abs_sum_widget.setLayout(abs_sum_layout)
        
        # 新增：有效累加值绝对值小于控件
        self.valid_abs_sum_label = QLabel("开始日到结束日之间有效累加值绝对值小于")
        self.valid_abs_sum_threshold_edit = QLineEdit()
        
        # 第一行全部控件
        top_grid.addWidget(self.label, 0, 0)
        top_grid.addWidget(self.upload_btn, 0, 1)
        top_grid.addWidget(self.date_label, 0, 2)
        top_grid.addWidget(self.date_picker, 0, 3)
        top_grid.addWidget(width_widget, 0, 4)
        top_grid.addWidget(start_option_widget, 0, 5)
        top_grid.addWidget(shift_widget, 0, 6)
        top_grid.addWidget(self.direction_checkbox, 0, 7)
        top_grid.addWidget(self.range_label, 0, 9)
        top_grid.addWidget(self.range_value_edit, 0, 10)
        top_grid.addWidget(abs_sum_widget, 0, 11)
       

        # 第二行
        # 新增"前1组结束地址后N日的最大值"
        self.n_days_label1 = QLabel("第1组后N最大值逻辑")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(0)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(0)

        self.n_days_label2 = QLabel("前1组结束地址后N日的最大值")
        self.n_days_max_spin = QSpinBox()
        self.n_days_max_spin.setMinimum(0)
        self.n_days_max_spin.setMaximum(100)
        self.n_days_max_spin.setValue(0)

        op_days_widget = QWidget()
        op_days_layout = QHBoxLayout()
        op_days_layout.setContentsMargins(0, 0, 0, 0)
        op_days_layout.setSpacing(5)
        op_days_layout.setAlignment(Qt.AlignLeft)
        self.op_days_label = QLabel("操作天数")
        self.op_days_edit = QLineEdit()
        self.op_days_edit.setMaximumWidth(30)
        self.op_days_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.op_days_edit.setValidator(QIntValidator(0, 400))
        op_days_layout.addWidget(self.op_days_label)
        op_days_layout.addWidget(self.op_days_edit)
        op_days_widget.setMaximumWidth(90)
        op_days_widget.setLayout(op_days_layout)

        # 止盈递增率
        self.inc_rate_label = QLabel("止盈递增率")
        self.inc_rate_edit = QLineEdit()
        self.inc_rate_edit.setFixedWidth(30)
        self.inc_rate_unit = QLabel("%")
        inc_rate_widget = QWidget()
        inc_rate_layout = QHBoxLayout()
        inc_rate_layout.setContentsMargins(0, 0, 0, 0)
        inc_rate_layout.setSpacing(0)
        inc_rate_layout.setAlignment(Qt.AlignLeft)
        inc_rate_layout.addWidget(QLabel("止盈递增率"))
        inc_rate_layout.addWidget(self.inc_rate_edit)
        inc_rate_layout.addWidget(QLabel("%"))
        inc_rate_widget.setLayout(inc_rate_layout)
        inc_rate_widget.setMaximumWidth(100)

        # 止盈后值大于结束值比例
        self.after_gt_end_label = QLabel("止盈后值大于结束值比例")
        self.after_gt_end_edit = QLineEdit()
        self.after_gt_end_edit.setFixedWidth(30)
        self.after_gt_end_unit = QLabel("%")
        after_gt_end_widget = QWidget()
        after_gt_end_layout = QHBoxLayout()
        after_gt_end_layout.setContentsMargins(0, 0, 0, 0)
        after_gt_end_layout.setSpacing(0)
        after_gt_end_layout.setAlignment(Qt.AlignLeft)
        after_gt_end_layout.addWidget(QLabel("止盈后值大于结束值比例"))
        after_gt_end_layout.addWidget(self.after_gt_end_edit)
        after_gt_end_layout.addWidget(QLabel("%"))
        after_gt_end_widget.setLayout(after_gt_end_layout)
        after_gt_end_widget.setMaximumWidth(175)

        # 止盈后值大于前值比例
        self.after_gt_start_label = QLabel("止盈后值大于前值比例")
        self.after_gt_prev_edit = QLineEdit()
        self.after_gt_prev_edit.setFixedWidth(30)
        self.after_gt_prev_unit = QLabel("%")
        after_gt_prev_widget = QWidget()
        after_gt_prev_layout = QHBoxLayout()
        after_gt_prev_layout.setContentsMargins(0, 0, 0, 0)
        after_gt_prev_layout.setSpacing(0)
        after_gt_prev_layout.setAlignment(Qt.AlignLeft)
        after_gt_prev_layout.addWidget(self.after_gt_start_label)
        after_gt_prev_layout.addWidget(self.after_gt_prev_edit)
        after_gt_prev_layout.addWidget(QLabel("%"))
        after_gt_prev_widget.setLayout(after_gt_prev_layout)
        after_gt_prev_widget.setMaximumWidth(155)

        # 止损递增率
        self.stop_loss_inc_rate_label = QLabel("止损递增率")
        self.stop_loss_inc_rate_edit = QLineEdit()
        self.stop_loss_inc_rate_edit.setFixedWidth(30)
        # 添加非正数验证器（允许0和负数）
        self.stop_loss_inc_rate_edit.setValidator(NonPositiveValidator())
        stop_loss_inc_rate_widget = QWidget()
        stop_loss_inc_rate_layout = QHBoxLayout()
        stop_loss_inc_rate_layout.setContentsMargins(0, 0, 0, 0)
        stop_loss_inc_rate_layout.setSpacing(0)
        stop_loss_inc_rate_layout.setAlignment(Qt.AlignLeft)
        stop_loss_inc_rate_layout.addWidget(QLabel("止损递增率"))
        stop_loss_inc_rate_layout.addWidget(self.stop_loss_inc_rate_edit)
        stop_loss_inc_rate_layout.addWidget(QLabel("%"))
        stop_loss_inc_rate_widget.setLayout(stop_loss_inc_rate_layout)
        stop_loss_inc_rate_widget.setMaximumWidth(100)

        # 止损后值大于结束值比例
        self.stop_loss_after_gt_end_label = QLabel("止损后值大于结束值比例")
        self.stop_loss_after_gt_end_edit = QLineEdit()
        self.stop_loss_after_gt_end_edit.setFixedWidth(30)
        # 添加非正数验证器（允许0和负数）
        self.stop_loss_after_gt_end_edit.setValidator(NonPositiveValidator())
        stop_loss_after_gt_end_widget = QWidget()
        stop_loss_after_gt_end_layout = QHBoxLayout()
        stop_loss_after_gt_end_layout.setContentsMargins(0, 0, 0, 0)
        stop_loss_after_gt_end_layout.setSpacing(0)
        stop_loss_after_gt_end_layout.setAlignment(Qt.AlignLeft)
        stop_loss_after_gt_end_layout.addWidget(QLabel("止损后值大于结束值比例"))
        stop_loss_after_gt_end_layout.addWidget(self.stop_loss_after_gt_end_edit)
        stop_loss_after_gt_end_layout.addWidget(QLabel("%"))
        stop_loss_after_gt_end_widget.setLayout(stop_loss_after_gt_end_layout)
        stop_loss_after_gt_end_widget.setMaximumWidth(175)

        # 止损大于前值比例
        self.stop_loss_after_gt_start_label = QLabel("止损大于前值比例")
        self.stop_loss_after_gt_start_edit = QLineEdit()
        self.stop_loss_after_gt_start_edit.setFixedWidth(30)
        # 添加非正数验证器（允许0和负数）
        self.stop_loss_after_gt_start_edit.setValidator(NonPositiveValidator())
        stop_loss_after_gt_start_widget = QWidget()
        stop_loss_after_gt_start_layout = QHBoxLayout()
        stop_loss_after_gt_start_layout.setContentsMargins(0, 0, 0, 0)
        stop_loss_after_gt_start_layout.setSpacing(0)
        stop_loss_after_gt_start_layout.setAlignment(Qt.AlignLeft)
        stop_loss_after_gt_start_layout.addWidget(QLabel("止损大于前值比例"))
        stop_loss_after_gt_start_layout.addWidget(self.stop_loss_after_gt_start_edit)
        stop_loss_after_gt_start_layout.addWidget(QLabel("%"))
        stop_loss_after_gt_start_widget.setLayout(stop_loss_after_gt_start_layout)
        stop_loss_after_gt_start_widget.setMaximumWidth(155)

        # 操作涨幅
        self.ops_change_label = QLabel("操作涨幅")
        self.ops_change_edit = QLineEdit()
        self.ops_change_edit.setMaximumWidth(20)
        ops_change_widget = QWidget()
        ops_change_layout = QHBoxLayout()
        ops_change_layout.setContentsMargins(0, 0, 0, 0)
        ops_change_layout.setSpacing(0)
        ops_change_layout.setAlignment(Qt.AlignLeft)
        ops_change_layout.addWidget(self.ops_change_label)
        ops_change_layout.addWidget(self.ops_change_edit)
        ops_change_layout.addWidget(QLabel("%"))
        ops_change_widget.setLayout(ops_change_layout)
        ops_change_widget.setMaximumWidth(100)

        # 开始日到结束日之间有效累加值绝对值小于
        self.valid_abs_sum_label = QLabel("开始日到结束日之间有效累加值绝对值小于")
        self.valid_abs_sum_threshold_edit = QLineEdit()

        # 控件位置布局
        top_grid.addWidget(self.n_days_label1, 1, 0)
        top_grid.addWidget(self.n_days_spin, 1, 1)

        top_grid.addWidget(self.n_days_label2, 1, 2)
        top_grid.addWidget(self.n_days_max_spin, 1, 3)

        top_grid.addWidget(op_days_widget, 1, 4)
        top_grid.addWidget(inc_rate_widget, 1, 5)
        top_grid.addWidget(after_gt_end_widget, 1, 6)
        top_grid.addWidget(after_gt_prev_widget, 1, 7)
        top_grid.addWidget(stop_loss_inc_rate_widget, 1, 8)
        top_grid.addWidget(stop_loss_after_gt_end_widget, 1, 9)
        top_grid.addWidget(stop_loss_after_gt_start_widget, 1, 10)

        # 第三行：操作涨幅、有效累加值绝对值小于、CPU核心数
        top_grid.addWidget(ops_change_widget, 2, 8)
        top_grid.addWidget(self.valid_abs_sum_label, 2, 9)
        top_grid.addWidget(self.valid_abs_sum_threshold_edit, 2, 10)
        top_grid.addWidget(cpu_widget, 2, 11)  # 添加CPU核心数控件

        # 添加交易方式下拉框
        trade_mode_widget = QWidget()
        trade_mode_layout = QHBoxLayout()
        trade_mode_layout.setContentsMargins(0, 0, 0, 0)
        trade_mode_layout.setSpacing(5)
        trade_mode_layout.setAlignment(Qt.AlignLeft)
        self.trade_mode_label = QLabel("交易方式")
        self.trade_mode_combo = QComboBox()
        self.trade_mode_combo.addItems(["T+0", "T+1"])
        self.trade_mode_combo.setFixedWidth(60)
        trade_mode_layout.addWidget(self.trade_mode_label)
        trade_mode_layout.addWidget(self.trade_mode_combo)
        trade_mode_widget.setLayout(trade_mode_layout)
        top_grid.addWidget(trade_mode_widget, 0, 8)

        # 第四行：创前新高1和创前新低相关控件
        # 创前新高1开始日期天数
        self.new_before_high_flag_checkbox = QCheckBox()
        new_before_high_start_widget = QWidget()
        new_before_high_start_layout = QHBoxLayout()
        new_before_high_start_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high_start_layout.setSpacing(5)
        new_before_high_start_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high_start_label = QLabel("创前新高1开始日期距结束日期天数")
        self.new_before_high_start_spin = QSpinBox()
        self.new_before_high_start_spin.setMinimum(0)
        self.new_before_high_start_spin.setValue(0)
        self.new_before_high_start_spin.setFixedWidth(60)
        new_before_high_start_layout.addWidget(self.new_before_high_flag_checkbox)
        new_before_high_start_layout.addWidget(self.new_before_high_start_label)
        new_before_high_start_layout.addWidget(self.new_before_high_start_spin)
        new_before_high_start_widget.setLayout(new_before_high_start_layout)

        # 创前新高1日期范围
        new_before_high_range_widget = QWidget()
        new_before_high_range_layout = QHBoxLayout()
        new_before_high_range_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high_range_layout.setSpacing(5)
        new_before_high_range_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high_range_label = QLabel("创前新高1日期范围")
        self.new_before_high_range_spin = QSpinBox()
        self.new_before_high_range_spin.setMinimum(1)
        self.new_before_high_range_spin.setValue(0)
        self.new_before_high_range_spin.setFixedWidth(60)
        new_before_high_range_layout.addWidget(self.new_before_high_range_label)
        new_before_high_range_layout.addWidget(self.new_before_high_range_spin)
        new_before_high_range_widget.setLayout(new_before_high_range_layout)

        # 创前新高1展宽期天数
        new_before_high_span_widget = QWidget()
        new_before_high_span_layout = QHBoxLayout()
        new_before_high_span_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high_span_layout.setSpacing(5)
        new_before_high_span_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high_span_label = QLabel("创前新高1展宽期天数")
        self.new_before_high_span_spin = QSpinBox()
        self.new_before_high_span_spin.setMinimum(1)
        self.new_before_high_span_spin.setValue(0)
        self.new_before_high_span_spin.setFixedWidth(60)
        new_before_high_span_layout.addWidget(self.new_before_high_span_label)
        new_before_high_span_layout.addWidget(self.new_before_high_span_spin)
        new_before_high_span_widget.setLayout(new_before_high_span_layout)

        # 创前新高1与或下拉框
        new_before_high_logic_widget = QWidget()
        new_before_high_logic_layout = QHBoxLayout()
        new_before_high_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high_logic_layout.setSpacing(5)
        new_before_high_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high_logic_label = QLabel("创前新高1与或")
        self.new_before_high_logic_combo = QComboBox()
        self.new_before_high_logic_combo.addItems(["与", "或"])
        self.new_before_high_logic_combo.setFixedWidth(60)
        new_before_high_logic_layout.addWidget(self.new_before_high_logic_label)
        new_before_high_logic_layout.addWidget(self.new_before_high_logic_combo)
        new_before_high_logic_widget.setLayout(new_before_high_logic_layout)

        # 创前新高2开始日期距结束日期天数
        self.new_before_high2_flag_checkbox = QCheckBox()
        new_before_high2_start_widget = QWidget()
        new_before_high2_start_layout = QHBoxLayout()
        new_before_high2_start_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high2_start_layout.setSpacing(5)
        new_before_high2_start_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high2_start_label = QLabel("创前新高2开始日期距结束日期天数")
        self.new_before_high2_start_spin = QSpinBox()
        self.new_before_high2_start_spin.setMinimum(0)
        self.new_before_high2_start_spin.setValue(0)
        self.new_before_high2_start_spin.setFixedWidth(60)
        new_before_high2_start_layout.addWidget(self.new_before_high2_flag_checkbox)
        new_before_high2_start_layout.addWidget(self.new_before_high2_start_label)
        new_before_high2_start_layout.addWidget(self.new_before_high2_start_spin)
        new_before_high2_start_widget.setLayout(new_before_high2_start_layout)

        # 创前新高2日期范围
        new_before_high2_range_widget = QWidget()
        new_before_high2_range_layout = QHBoxLayout()
        new_before_high2_range_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high2_range_layout.setSpacing(5)
        new_before_high2_range_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high2_range_label = QLabel("创前新高2日期范围")
        self.new_before_high2_range_spin = QSpinBox()
        self.new_before_high2_range_spin.setMinimum(1)
        self.new_before_high2_range_spin.setValue(0)
        self.new_before_high2_range_spin.setFixedWidth(60)
        new_before_high2_range_layout.addWidget(self.new_before_high2_range_label)
        new_before_high2_range_layout.addWidget(self.new_before_high2_range_spin)
        new_before_high2_range_widget.setLayout(new_before_high2_range_layout)

        # 创前新高2展宽期天数
        new_before_high2_span_widget = QWidget()
        new_before_high2_span_layout = QHBoxLayout()
        new_before_high2_span_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high2_span_layout.setSpacing(5)
        new_before_high2_span_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high2_span_label = QLabel("创前新高2展宽期天数")
        self.new_before_high2_span_spin = QSpinBox()
        self.new_before_high2_span_spin.setMinimum(1)
        self.new_before_high2_span_spin.setValue(0)
        self.new_before_high2_span_spin.setFixedWidth(60)
        new_before_high2_span_layout.addWidget(self.new_before_high2_span_label)
        new_before_high2_span_layout.addWidget(self.new_before_high2_span_spin)
        new_before_high2_span_widget.setLayout(new_before_high2_span_layout)

        # 创前新高2与或下拉框
        new_before_high2_logic_widget = QWidget()
        new_before_high2_logic_layout = QHBoxLayout()
        new_before_high2_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_before_high2_logic_layout.setSpacing(5)
        new_before_high2_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_before_high2_logic_label = QLabel("创前新高2与或")
        self.new_before_high2_logic_combo = QComboBox()
        self.new_before_high2_logic_combo.addItems(["与", "或"])
        self.new_before_high2_logic_combo.setFixedWidth(60)
        new_before_high2_logic_layout.addWidget(self.new_before_high2_logic_label)
        new_before_high2_logic_layout.addWidget(self.new_before_high2_logic_combo)
        new_before_high2_logic_widget.setLayout(new_before_high2_logic_layout)

        top_grid.addWidget(new_before_high_start_widget, 2, 0)
        top_grid.addWidget(new_before_high_range_widget, 2, 1)
        top_grid.addWidget(new_before_high_span_widget, 2, 2)
        top_grid.addWidget(new_before_high_logic_widget, 2, 3)
        top_grid.addWidget(new_before_high2_start_widget, 2, 4)
        top_grid.addWidget(new_before_high2_range_widget, 2, 5)
        top_grid.addWidget(new_before_high2_span_widget, 2, 6)
        top_grid.addWidget(new_before_high2_logic_widget, 2, 7)

        # 第四行：创前新高1和创前新低相关控件
        # 创前新高1开始日期天数
        self.new_after_high_flag_checkbox = QCheckBox()
        new_after_high_start_widget = QWidget()
        new_after_high_start_layout = QHBoxLayout()
        new_after_high_start_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high_start_layout.setSpacing(5)
        new_after_high_start_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high_start_label = QLabel("创后新高1开始日期距结束日期天数")
        self.new_after_high_start_spin = QSpinBox()
        self.new_after_high_start_spin.setMinimum(0)
        self.new_after_high_start_spin.setValue(0)
        self.new_after_high_start_spin.setFixedWidth(60)
        new_after_high_start_layout.addWidget(self.new_after_high_flag_checkbox)
        new_after_high_start_layout.addWidget(self.new_after_high_start_label)
        new_after_high_start_layout.addWidget(self.new_after_high_start_spin)
        new_after_high_start_widget.setLayout(new_after_high_start_layout)

        # 创前新高1日期范围
        new_after_high_range_widget = QWidget()
        new_after_high_range_layout = QHBoxLayout()
        new_after_high_range_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high_range_layout.setSpacing(5)
        new_after_high_range_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high_range_label = QLabel("创后新高1日期范围")
        self.new_after_high_range_spin = QSpinBox()
        self.new_after_high_range_spin.setMinimum(1)
        self.new_after_high_range_spin.setValue(0)
        self.new_after_high_range_spin.setFixedWidth(60)
        new_after_high_range_layout.addWidget(self.new_after_high_range_label)
        new_after_high_range_layout.addWidget(self.new_after_high_range_spin)
        new_after_high_range_widget.setLayout(new_after_high_range_layout)

        # 创前新高1展宽期天数
        new_after_high_span_widget = QWidget()
        new_after_high_span_layout = QHBoxLayout()
        new_after_high_span_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high_span_layout.setSpacing(5)
        new_after_high_span_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high_span_label = QLabel("创后新高1展宽期天数")
        self.new_after_high_span_spin = QSpinBox()
        self.new_after_high_span_spin.setMinimum(1)
        self.new_after_high_span_spin.setValue(0)
        self.new_after_high_span_spin.setFixedWidth(60)
        new_after_high_span_layout.addWidget(self.new_after_high_span_label)
        new_after_high_span_layout.addWidget(self.new_after_high_span_spin)
        new_after_high_span_widget.setLayout(new_after_high_span_layout)

        # 创前新高1与或下拉框
        new_after_high_logic_widget = QWidget()
        new_after_high_logic_layout = QHBoxLayout()
        new_after_high_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high_logic_layout.setSpacing(5)
        new_after_high_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high_logic_label = QLabel("创后新高1与或")
        self.new_after_high_logic_combo = QComboBox()
        self.new_after_high_logic_combo.addItems(["与", "或"])
        self.new_after_high_logic_combo.setFixedWidth(60)
        new_after_high_logic_layout.addWidget(self.new_after_high_logic_label)
        new_after_high_logic_layout.addWidget(self.new_after_high_logic_combo)
        new_after_high_logic_widget.setLayout(new_after_high_logic_layout)

        # 创前新高2开始日期距结束日期天数
        self.new_after_high2_flag_checkbox = QCheckBox()
        new_after_high2_start_widget = QWidget()
        new_after_high2_start_layout = QHBoxLayout()
        new_after_high2_start_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high2_start_layout.setSpacing(5)
        new_after_high2_start_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high2_start_label = QLabel("创后新高2开始日期距结束日期天数")
        self.new_after_high2_start_spin = QSpinBox()
        self.new_after_high2_start_spin.setMinimum(0)
        self.new_after_high2_start_spin.setValue(0)
        self.new_after_high2_start_spin.setFixedWidth(60)
        new_after_high2_start_layout.addWidget(self.new_after_high2_flag_checkbox)
        new_after_high2_start_layout.addWidget(self.new_after_high2_start_label)
        new_after_high2_start_layout.addWidget(self.new_after_high2_start_spin)
        new_after_high2_start_widget.setLayout(new_after_high2_start_layout)

        # 创前新高2日期范围
        new_after_high2_range_widget = QWidget()
        new_after_high2_range_layout = QHBoxLayout()
        new_after_high2_range_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high2_range_layout.setSpacing(5)
        new_after_high2_range_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high2_range_label = QLabel("创后新高2日期范围")
        self.new_after_high2_range_spin = QSpinBox()
        self.new_after_high2_range_spin.setMinimum(1)
        self.new_after_high2_range_spin.setValue(0)
        self.new_after_high2_range_spin.setFixedWidth(60)
        new_after_high2_range_layout.addWidget(self.new_after_high2_range_label)
        new_after_high2_range_layout.addWidget(self.new_after_high2_range_spin)
        new_after_high2_range_widget.setLayout(new_after_high2_range_layout)

        # 创前新高2展宽期天数
        new_after_high2_span_widget = QWidget()
        new_after_high2_span_layout = QHBoxLayout()
        new_after_high2_span_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high2_span_layout.setSpacing(5)
        new_after_high2_span_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high2_span_label = QLabel("创后新高2展宽期天数")
        self.new_after_high2_span_spin = QSpinBox()
        self.new_after_high2_span_spin.setMinimum(1)
        self.new_after_high2_span_spin.setValue(0)
        self.new_after_high2_span_spin.setFixedWidth(60)
        new_after_high2_span_layout.addWidget(self.new_after_high2_span_label)
        new_after_high2_span_layout.addWidget(self.new_after_high2_span_spin)
        new_after_high2_span_widget.setLayout(new_after_high2_span_layout)

        # 创前新高2与或下拉框
        new_after_high2_logic_widget = QWidget()
        new_after_high2_logic_layout = QHBoxLayout()
        new_after_high2_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_after_high2_logic_layout.setSpacing(5)
        new_after_high2_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_after_high2_logic_label = QLabel("创后新高2与或")
        self.new_after_high2_logic_combo = QComboBox()
        self.new_after_high2_logic_combo.addItems(["与", "或"])
        self.new_after_high2_logic_combo.setFixedWidth(60)
        new_after_high2_logic_layout.addWidget(self.new_after_high2_logic_label)
        new_after_high2_logic_layout.addWidget(self.new_after_high2_logic_combo)
        new_after_high2_logic_widget.setLayout(new_after_high2_logic_layout)

        top_grid.addWidget(new_after_high_start_widget, 3, 0)
        top_grid.addWidget(new_after_high_range_widget, 3, 1)
        top_grid.addWidget(new_after_high_span_widget, 3, 2)
        top_grid.addWidget(new_after_high_logic_widget, 3, 3)
        top_grid.addWidget(new_after_high2_start_widget, 3, 4)
        top_grid.addWidget(new_after_high2_range_widget, 3, 5)
        top_grid.addWidget(new_after_high2_span_widget, 3, 6)
        top_grid.addWidget(new_after_high2_logic_widget, 3, 7)

        # 创新低开始日期天数
        self.new_before_low_flag_checkbox = QCheckBox()
        new_before_low_start_widget = QWidget()
        new_before_low_start_layout = QHBoxLayout()
        new_before_low_start_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low_start_layout.setSpacing(5)
        new_before_low_start_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low_start_label = QLabel("创前新低1开始日期距结束日期天数")
        self.new_before_low_start_spin = QSpinBox()
        self.new_before_low_start_spin.setMinimum(0)
        self.new_before_low_start_spin.setValue(0)
        self.new_before_low_start_spin.setFixedWidth(60)
        new_before_low_start_layout.addWidget(self.new_before_low_flag_checkbox)
        new_before_low_start_layout.addWidget(self.new_before_low_start_label)
        new_before_low_start_layout.addWidget(self.new_before_low_start_spin)
        new_before_low_start_widget.setLayout(new_before_low_start_layout)

        # 创新低日期范围
        new_before_low_range_widget = QWidget()
        new_before_low_range_layout = QHBoxLayout()
        new_before_low_range_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low_range_layout.setSpacing(5)
        new_before_low_range_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low_range_label = QLabel("创前新低1日期范围")
        self.new_before_low_range_spin = QSpinBox()
        self.new_before_low_range_spin.setMinimum(1)
        self.new_before_low_range_spin.setValue(0)
        self.new_before_low_range_spin.setFixedWidth(60)
        new_before_low_range_layout.addWidget(self.new_before_low_range_label)
        new_before_low_range_layout.addWidget(self.new_before_low_range_spin)
        new_before_low_range_widget.setLayout(new_before_low_range_layout)

        # 创新低展宽期天数
        new_before_low_span_widget = QWidget()
        new_before_low_span_layout = QHBoxLayout()
        new_before_low_span_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low_span_layout.setSpacing(5)
        new_before_low_span_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low_span_label = QLabel("创前新低1展宽期天数")
        self.new_before_low_span_spin = QSpinBox()
        self.new_before_low_span_spin.setMinimum(1)
        self.new_before_low_span_spin.setValue(0)
        self.new_before_low_span_spin.setFixedWidth(60)
        new_before_low_span_layout.addWidget(self.new_before_low_span_label)
        new_before_low_span_layout.addWidget(self.new_before_low_span_spin)
        new_before_low_span_widget.setLayout(new_before_low_span_layout)

        # 创前创新低1与或下拉框
        new_before_low_logic_widget = QWidget()
        new_before_low_logic_layout = QHBoxLayout()
        new_before_low_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low_logic_layout.setSpacing(5)
        new_before_low_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low_logic_label = QLabel("创前新低1与或")
        self.new_before_low_logic_combo = QComboBox()
        self.new_before_low_logic_combo.addItems(["与", "或"])
        self.new_before_low_logic_combo.setFixedWidth(60)
        new_before_low_logic_layout.addWidget(self.new_before_low_logic_label)
        new_before_low_logic_layout.addWidget(self.new_before_low_logic_combo)
        new_before_low_logic_widget.setLayout(new_before_low_logic_layout)

        # 创前创新低2开始日期距结束日期天数
        self.new_before_low2_flag_checkbox = QCheckBox()
        new_before_low2_start_widget = QWidget()
        new_before_low2_start_layout = QHBoxLayout()
        new_before_low2_start_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low2_start_layout.setSpacing(5)
        new_before_low2_start_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low2_start_label = QLabel("创前新低2开始日期距结束日期天数")
        self.new_before_low2_start_spin = QSpinBox()
        self.new_before_low2_start_spin.setMinimum(0)
        self.new_before_low2_start_spin.setValue(0)
        self.new_before_low2_start_spin.setFixedWidth(60)
        new_before_low2_start_layout.addWidget(self.new_before_low2_flag_checkbox)
        new_before_low2_start_layout.addWidget(self.new_before_low2_start_label)
        new_before_low2_start_layout.addWidget(self.new_before_low2_start_spin)
        new_before_low2_start_widget.setLayout(new_before_low2_start_layout)

        # 创前创新低2日期范围
        new_before_low2_range_widget = QWidget()
        new_before_low2_range_layout = QHBoxLayout()
        new_before_low2_range_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low2_range_layout.setSpacing(5)
        new_before_low2_range_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low2_range_label = QLabel("创前新低2日期范围")
        self.new_before_low2_range_spin = QSpinBox()
        self.new_before_low2_range_spin.setMinimum(1)
        self.new_before_low2_range_spin.setValue(0)
        self.new_before_low2_range_spin.setFixedWidth(60)
        new_before_low2_range_layout.addWidget(self.new_before_low2_range_label)
        new_before_low2_range_layout.addWidget(self.new_before_low2_range_spin)
        new_before_low2_range_widget.setLayout(new_before_low2_range_layout)

        # 创前创新低2展宽期天数
        new_before_low2_span_widget = QWidget()
        new_before_low2_span_layout = QHBoxLayout()
        new_before_low2_span_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low2_span_layout.setSpacing(5)
        new_before_low2_span_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low2_span_label = QLabel("创前新低2展宽期天数")
        self.new_before_low2_span_spin = QSpinBox()
        self.new_before_low2_span_spin.setMinimum(1)
        self.new_before_low2_span_spin.setValue(0)
        self.new_before_low2_span_spin.setFixedWidth(60)
        new_before_low2_span_layout.addWidget(self.new_before_low2_span_label)
        new_before_low2_span_layout.addWidget(self.new_before_low2_span_spin)
        new_before_low2_span_widget.setLayout(new_before_low2_span_layout)

        # 创前创新低2与或下拉框
        new_before_low2_logic_widget = QWidget()
        new_before_low2_logic_layout = QHBoxLayout()
        new_before_low2_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_before_low2_logic_layout.setSpacing(5)
        new_before_low2_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_before_low2_logic_label = QLabel("创前新低2与或")
        self.new_before_low2_logic_combo = QComboBox()
        self.new_before_low2_logic_combo.addItems(["与", "或"])
        self.new_before_low2_logic_combo.setFixedWidth(60)
        new_before_low2_logic_layout.addWidget(self.new_before_low2_logic_label)
        new_before_low2_logic_layout.addWidget(self.new_before_low2_logic_combo)
        new_before_low2_logic_widget.setLayout(new_before_low2_logic_layout)

        # 创后创新低1开始日期距结束日期天数
        self.new_after_low_flag_checkbox = QCheckBox()
        new_after_low_start_widget = QWidget()
        new_after_low_start_layout = QHBoxLayout()
        new_after_low_start_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low_start_layout.setSpacing(5)
        new_after_low_start_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low_start_label = QLabel("创后新低1开始日期距结束日期天数")
        self.new_after_low_start_spin = QSpinBox()
        self.new_after_low_start_spin.setMinimum(0)
        self.new_after_low_start_spin.setValue(0)
        self.new_after_low_start_spin.setFixedWidth(60)
        new_after_low_start_layout.addWidget(self.new_after_low_flag_checkbox)
        new_after_low_start_layout.addWidget(self.new_after_low_start_label)
        new_after_low_start_layout.addWidget(self.new_after_low_start_spin)
        new_after_low_start_widget.setLayout(new_after_low_start_layout)

        # 创后创新低1日期范围
        new_after_low_range_widget = QWidget()
        new_after_low_range_layout = QHBoxLayout()
        new_after_low_range_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low_range_layout.setSpacing(5)
        new_after_low_range_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low_range_label = QLabel("创后新低1日期范围")
        self.new_after_low_range_spin = QSpinBox()
        self.new_after_low_range_spin.setMinimum(1)
        self.new_after_low_range_spin.setValue(0)
        self.new_after_low_range_spin.setFixedWidth(60)
        new_after_low_range_layout.addWidget(self.new_after_low_range_label)
        new_after_low_range_layout.addWidget(self.new_after_low_range_spin)
        new_after_low_range_widget.setLayout(new_after_low_range_layout)

        # 创后创新低1展宽期天数
        new_after_low_span_widget = QWidget()
        new_after_low_span_layout = QHBoxLayout()
        new_after_low_span_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low_span_layout.setSpacing(5)
        new_after_low_span_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low_span_label = QLabel("创后新低1展宽期天数")
        self.new_after_low_span_spin = QSpinBox()
        self.new_after_low_span_spin.setMinimum(1)
        self.new_after_low_span_spin.setValue(0)
        self.new_after_low_span_spin.setFixedWidth(60)
        new_after_low_span_layout.addWidget(self.new_after_low_span_label)
        new_after_low_span_layout.addWidget(self.new_after_low_span_spin)
        new_after_low_span_widget.setLayout(new_after_low_span_layout)

        # 创后创新低1与或下拉框
        new_after_low_logic_widget = QWidget()
        new_after_low_logic_layout = QHBoxLayout()
        new_after_low_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low_logic_layout.setSpacing(5)
        new_after_low_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low_logic_label = QLabel("创后新低1与或")
        self.new_after_low_logic_combo = QComboBox()
        self.new_after_low_logic_combo.addItems(["与", "或"])
        self.new_after_low_logic_combo.setFixedWidth(60)
        new_after_low_logic_layout.addWidget(self.new_after_low_logic_label)
        new_after_low_logic_layout.addWidget(self.new_after_low_logic_combo)
        new_after_low_logic_widget.setLayout(new_after_low_logic_layout)

        # 创后创新低2开始日期距结束日期天数
        self.new_after_low2_flag_checkbox = QCheckBox()
        new_after_low2_start_widget = QWidget()
        new_after_low2_start_layout = QHBoxLayout()
        new_after_low2_start_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low2_start_layout.setSpacing(5)
        new_after_low2_start_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low2_start_label = QLabel("创后新低2开始日期距结束日期天数")
        self.new_after_low2_start_spin = QSpinBox()
        self.new_after_low2_start_spin.setMinimum(0)
        self.new_after_low2_start_spin.setValue(0)
        self.new_after_low2_start_spin.setFixedWidth(60)
        new_after_low2_start_layout.addWidget(self.new_after_low2_flag_checkbox)
        new_after_low2_start_layout.addWidget(self.new_after_low2_start_label)
        new_after_low2_start_layout.addWidget(self.new_after_low2_start_spin)
        new_after_low2_start_widget.setLayout(new_after_low2_start_layout)

        # 创后创新低2日期范围
        new_after_low2_range_widget = QWidget()
        new_after_low2_range_layout = QHBoxLayout()
        new_after_low2_range_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low2_range_layout.setSpacing(5)
        new_after_low2_range_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low2_range_label = QLabel("创后新低2日期范围")
        self.new_after_low2_range_spin = QSpinBox()
        self.new_after_low2_range_spin.setMinimum(1)
        self.new_after_low2_range_spin.setValue(0)
        self.new_after_low2_range_spin.setFixedWidth(60)
        new_after_low2_range_layout.addWidget(self.new_after_low2_range_label)
        new_after_low2_range_layout.addWidget(self.new_after_low2_range_spin)
        new_after_low2_range_widget.setLayout(new_after_low2_range_layout)

        # 创后创新低2展宽期天数
        new_after_low2_span_widget = QWidget()
        new_after_low2_span_layout = QHBoxLayout()
        new_after_low2_span_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low2_span_layout.setSpacing(5)
        new_after_low2_span_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low2_span_label = QLabel("创后新低2展宽期天数")
        self.new_after_low2_span_spin = QSpinBox()
        self.new_after_low2_span_spin.setMinimum(1)
        self.new_after_low2_span_spin.setValue(0)
        self.new_after_low2_span_spin.setFixedWidth(60)
        new_after_low2_span_layout.addWidget(self.new_after_low2_span_label)
        new_after_low2_span_layout.addWidget(self.new_after_low2_span_spin)
        new_after_low2_span_widget.setLayout(new_after_low2_span_layout)

        # 创后创新低2与或下拉框
        new_after_low2_logic_widget = QWidget()
        new_after_low2_logic_layout = QHBoxLayout()
        new_after_low2_logic_layout.setContentsMargins(0, 0, 0, 0)
        new_after_low2_logic_layout.setSpacing(5)
        new_after_low2_logic_layout.setAlignment(Qt.AlignLeft)
        self.new_after_low2_logic_label = QLabel("创后新低2与或")
        self.new_after_low2_logic_combo = QComboBox()
        self.new_after_low2_logic_combo.addItems(["与", "或"])
        self.new_after_low2_logic_combo.setFixedWidth(60)
        new_after_low2_logic_layout.addWidget(self.new_after_low2_logic_label)
        new_after_low2_logic_layout.addWidget(self.new_after_low2_logic_combo)
        new_after_low2_logic_widget.setLayout(new_after_low2_logic_layout)

        top_grid.addWidget(new_before_low_start_widget, 4, 0)
        top_grid.addWidget(new_before_low_range_widget, 4, 1)
        top_grid.addWidget(new_before_low_span_widget, 4, 2)
        top_grid.addWidget(new_before_low_logic_widget, 4, 3)
        top_grid.addWidget(new_before_low2_start_widget, 4, 4)
        top_grid.addWidget(new_before_low2_range_widget, 4, 5)
        top_grid.addWidget(new_before_low2_span_widget, 4, 6)
        top_grid.addWidget(new_before_low2_logic_widget, 4, 7)

        top_grid.addWidget(new_after_low_start_widget, 5, 0)
        top_grid.addWidget(new_after_low_range_widget, 5, 1)
        top_grid.addWidget(new_after_low_span_widget, 5, 2)
        top_grid.addWidget(new_after_low_logic_widget, 5, 3)
        top_grid.addWidget(new_after_low2_start_widget, 5, 4)
        top_grid.addWidget(new_after_low2_range_widget, 5, 5)
        top_grid.addWidget(new_after_low2_span_widget, 5, 6)
        top_grid.addWidget(new_after_low2_logic_widget, 5, 7)

        # 查询区控件
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("根据代码/名称查询")
        self.query_btn = QPushButton("股票参数信息")
        query_widget = QWidget()
        query_layout = QHBoxLayout()
        query_layout.setContentsMargins(0, 0, 0, 0)
        query_layout.setSpacing(0)
        query_layout.setAlignment(Qt.AlignLeft)
        query_layout.addWidget(self.query_input)
        query_layout.addWidget(self.query_btn)
        query_widget.setLayout(query_layout)
     
        # 输出区：用QStackedLayout管理result_text和表格
        self.output_area = QWidget()
        self.output_stack = QStackedLayout(self.output_area)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.output_stack.addWidget(self.result_text)  # index 0: 文字提示
        self.table_widget = None  # 先不加表格
        # 添加标签页切换事件处理
        self.output_stack.currentChanged.connect(self.on_output_stack_changed)
        main_layout.addWidget(top_widget)
        main_layout.addWidget(self.output_area, stretch=1)

        # 最后一行添加底部功能按钮
        self.continuous_sum_btn = QPushButton("连续累加值")
        self.continuous_sum_btn.setFixedSize(100, 50)
        self.param_show_btn = QPushButton("参数显示")
        self.param_show_btn.setFixedSize(100, 50)
        self.formula_select_btn = QPushButton("公式选股")
        self.formula_select_btn.setFixedSize(100, 50)
        self.auto_analysis_btn = QPushButton("自动分析")
        self.auto_analysis_btn.setFixedSize(100, 50)
        self.op_stat_btn = QPushButton("操作统计")
        self.op_stat_btn.setFixedSize(100, 50)
        self.component_analysis_btn = QPushButton("组合分析")
        self.component_analysis_btn.setFixedSize(100, 50)
        self.trading_plan_btn = QPushButton("操盘方案")
        self.trading_plan_btn.setFixedSize(100, 50)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.continuous_sum_btn)
        btn_layout.addWidget(self.param_show_btn)
        btn_layout.addWidget(self.formula_select_btn)
        btn_layout.addWidget(self.auto_analysis_btn)
        btn_layout.addWidget(self.op_stat_btn)
        btn_layout.addWidget(self.component_analysis_btn)
        btn_layout.addWidget(self.trading_plan_btn)
        btn_layout.addStretch()  # 按钮靠左
        main_layout.addLayout(btn_layout)

        # 设置左表格所有参数列都不拉伸
        for i in range(15):  # 控件列
            top_grid.setColumnStretch(i, 0)
        top_grid.setColumnStretch(15, 1)  # 最右侧空白列拉伸

        # 设置输入控件不随窗口拉伸
        for widget in [
            self.range_value_edit, self.continuous_abs_threshold_edit, self.query_input,
            self.op_days_edit, self.inc_rate_edit, self.after_gt_end_edit, self.after_gt_prev_edit, self.ops_change_edit,
            self.n_days_spin, self.n_days_max_spin, self.width_spin, self.shift_spin, self.start_option_combo
        ]:
            if hasattr(widget, 'setSizePolicy'):
                widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            if hasattr(widget, 'setMaximumWidth'):
                widget.setMaximumWidth(120)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        # self.query_btn.clicked.connect(self.on_query_param)
        self.continuous_sum_btn.clicked.connect(self.on_continuous_sum_btn_clicked)
        self.param_show_btn.clicked.connect(self.on_param_show_btn_clicked)
        self.formula_select_btn.clicked.connect(self.on_formula_select_clicked)
        self.auto_analysis_btn.clicked.connect(self.on_auto_analysis_btn_clicked)
        self.op_stat_btn.clicked.connect(self.on_op_stat_btn_clicked)
        self.component_analysis_btn.clicked.connect(self.on_component_analysis_btn_clicked)
        self.trading_plan_btn.clicked.connect(self.show_trading_plan_interface)

    def on_query_param(self):
        # 查询参数信息
        keyword = self.query_input.text().strip()
        if not keyword:
            self.result_text.setText("请输入股票代码或名称进行查询！")
            return
        rows = getattr(self, 'all_row_results', None)
        if not rows:
            self.result_text.setText("请先计算基础参数！")
            return
        from function.stock_functions import query_row_result
        n_days = self.n_days_spin.value()  # 获取spinbox的值
        result = query_row_result(rows, keyword, n_days)
        self.result_text.setText(result) 

    def clear_result_area(self):
        # 移除表格控件，只保留result_text
        if self.table_widget is not None:
            self.output_stack.removeWidget(self.table_widget)
            self.table_widget.deleteLater()
            self.table_widget = None
        self.output_stack.setCurrentWidget(self.result_text)

    def on_continuous_sum_btn_clicked(self):
        if self.init.price_data is None:
            self.result_text.setText("请先上传数据文件！")
            self.output_stack.setCurrentWidget(self.result_text)
            return
        # 优先用公式选股缓存的all_param_result
        all_param_result = getattr(self, 'all_param_result', None)
        if all_param_result is None:
            self.result_text.setText("请先进行选股！")
            self.output_stack.setCurrentWidget(self.result_text)
            return
        merged_results = all_param_result.get('dates', {})
        if merged_results is None or not merged_results:
            self.result_text.setText("获取连续累加值失败，请检查参数设置！")
            self.output_stack.setCurrentWidget(self.result_text)
            self.last_end_date = self.date_picker.date().toString("yyyy-MM-dd")
            self.last_calculate_result = None
            return
        all_results = {
            "dates": [
                {
                    "end_date": date,
                    "stocks": stocks
                }
                for date, stocks in merged_results.items()
            ]
        }
        self.clear_result_area()
        table = show_continuous_sum_table(self, all_results, self.init.price_data, as_widget=True)
        if table:
            table.setMinimumSize(1200, 600)
            self.table_widget = table
            self.output_stack.addWidget(table)
            self.output_stack.setCurrentWidget(table)
        else:
            self.result_text.setText("没有可展示的连续累加值数据。")
            self.output_stack.setCurrentWidget(self.result_text)

    def on_param_show_btn_clicked(self):
        if self.init.price_data is None:
            self.result_text.setText("请先上传数据文件！")
            self.output_stack.setCurrentWidget(self.result_text)
            return
        # 优先用公式选股缓存的all_param_result
        all_param_result = getattr(self, 'all_param_result', None)
        if all_param_result is None:
            self.result_text.setText("请先进行选股！")
            self.output_stack.setCurrentWidget(self.result_text)
            return
        merged_results = all_param_result.get('dates', {})
        if merged_results is None or not merged_results:
            self.result_text.setText("获取参数明细失败，请检查参数设置！")
            self.output_stack.setCurrentWidget(self.result_text)
            self.last_end_date = self.date_picker.date().toString("yyyy-MM-dd")
            self.last_calculate_result = None
            return
        all_results = {
            "dates": [
                {
                    "end_date": date,
                    "stocks": stocks
                }
                for date, stocks in merged_results.items()
            ]
        }
        self.clear_result_area()
        from function.stock_functions import show_params_table
        params = {}
        params['n_days_max'] = self.n_days_max_spin.value()
        end_date = self.date_picker.date().toString("yyyy-MM-dd")
        table = show_params_table(
            parent=self,
            all_results=all_results,
            end_date=end_date,
            n_days=self.n_days if hasattr(self, 'n_days') else 0,
            n_days_max=params['n_days_max'],
            range_value=getattr(self, 'range_value', None),
            continuous_abs_threshold=getattr(self, 'continuous_abs_threshold', None),
            as_widget=True,
            price_data=self.init.price_data
        )
        if table:
            table.setMinimumSize(1200, 600)
            self.table_widget = table
            self.output_stack.addWidget(table)
            self.output_stack.setCurrentWidget(table)
        else:
            self.result_text.setText("没有可展示的参数明细数据。")
            self.output_stack.setCurrentWidget(self.result_text)

    def on_formula_select_clicked(self):
        all_results = getattr(self, 'all_row_results', None)
        from function.stock_functions import show_formula_select_table
        self.clear_result_area()
        table = show_formula_select_table(self, all_results, as_widget=True)
        # 设置公式输入框内容为上次的last_formula_expr
        if table:
            # 查找公式输入框（FormulaExprEdit）并设置内容
            for child in table.findChildren(type(table)):
                pass  # 占位，防止findChildren报错
            table.setMinimumSize(1200, 600)
            self.table_widget = table
            self.output_stack.addWidget(table)
            self.output_stack.setCurrentWidget(table)
        else:
            self.result_text.setText("没有可展示的公式选股结果。")
            self.output_stack.setCurrentWidget(self.result_text)

    def show_text_output(self, text):
        self.result_text.setText(text)
        self.output_stack.setCurrentWidget(self.result_text)

    def on_output_stack_changed(self, index):
        """标签页切换事件处理"""
        # 如果当前是公式选股界面，保存状态
        if hasattr(self, 'formula_widget') and self.formula_widget is not None:
            state = self.formula_widget.get_state()
            self.last_formula_select_state = state
            # print(f"保存状态: {state}")

    def get_or_calculate_result(self, formula_expr=None, select_count=None, sort_mode=None, 
                                show_main_output=True, only_show_selected=None, is_auto_analysis=False, 
                                end_date_start=None, end_date_end=None, end_date=None, comparison_vars=None, width=None, op_days=None, 
                                inc_rate=None, after_gt_end_ratio=None, after_gt_start_ratio=None,
                                stop_loss_inc_rate=None, stop_loss_after_gt_end_ratio=None, stop_loss_after_gt_start_ratio=None,
                                new_high_low_params=None, profit_type="INC", loss_type="INC"):
        # 直接在此处校验创新高/创新低日期范围
        workdays = getattr(self.init, 'workdays_str', None)
        # 如果没有传入end_date，则从控件获取
        if end_date is None:
            end_date = self.date_picker.date().toString("yyyy-MM-dd")
        if hasattr(self.init, 'workdays_str'):
            if not self.init.workdays_str:
                QMessageBox.warning(self, "提示", "请先上传数据文件！")
                return None
            date_str = self.date_picker.date().toString("yyyy-MM-dd")
            if date_str not in self.init.workdays_str:
                QMessageBox.warning(self, "提示", "只能选择交易日！")
                return None
        
        if not is_auto_analysis:
            try:
                end_idx = workdays.index(end_date)
            except Exception:
                end_idx = None
            if end_idx is not None:
                # 创新高参数
                nh_start = self.new_before_high_start_spin.value()
                nh_range = self.new_before_high_range_spin.value()
                nh_span = self.new_before_high_span_spin.value()
                nh_total = nh_start + nh_range + nh_span
                if end_idx - nh_total < 0:
                    QMessageBox.warning(self, "提示", "创前新高1日期范围超出数据范围，请调整！")
                    return None
                
                # 创前新高2参数
                nh2_start = self.new_before_high2_start_spin.value()
                nh2_range = self.new_before_high2_range_spin.value()
                nh2_span = self.new_before_high2_span_spin.value()
                nh2_total = nh2_start + nh2_range + nh2_span
                if end_idx - nh2_total < 0:
                    QMessageBox.warning(self, "提示", "创前新高2日期范围超出数据范围，请调整！")
                    return None
                
                # 创后新高1参数
                new_after_high_start = self.new_after_high_start_spin.value()
                new_after_high_range = self.new_after_high_range_spin.value()
                new_after_high_span = self.new_after_high_span_spin.value()
                new_after_high_total = new_after_high_start + new_after_high_range + new_after_high_span
                if end_idx - new_after_high_total < 0:
                    QMessageBox.warning(self, "提示", "创后新高1日期范围超出数据范围，请调整！")
                    return None

                # 创后新高2参数
                new_after_high2_start = self.new_after_high2_start_spin.value()
                new_after_high2_range = self.new_after_high2_range_spin.value()
                new_after_high2_span = self.new_after_high2_span_spin.value()
                new_after_high2_total = new_after_high2_start + new_after_high2_range + new_after_high2_span
                if end_idx - new_after_high2_total < 0:
                    QMessageBox.warning(self, "提示", "创后新高2日期范围超出数据范围，请调整！")
                    return None
                    
                # 创前新低1参数
                nl_start = self.new_before_low_start_spin.value()
                nl_range = self.new_before_low_range_spin.value()
                nl_span = self.new_before_low_span_spin.value()
                nl_total = nl_start + nl_range + nl_span
                if end_idx - nl_total < 0:
                    QMessageBox.warning(self, "提示", "创新低日期范围超出数据范围，请调整！")
                    return None
                
                # 创前新低2参数
                nh2_start = self.new_before_high2_start_spin.value()
                nh2_range = self.new_before_high2_range_spin.value()
                nh2_span = self.new_before_high2_span_spin.value()
                nh2_total = nh2_start + nh2_range + nh2_span
                if end_idx - nh2_total < 0:
                    QMessageBox.warning(self, "提示", "创前新高2日期范围超出数据范围，请调整！")
                    return None

                # 创后新低1参数
                new_after_low_start = self.new_after_low_start_spin.value()
                new_after_low_range = self.new_after_low_range_spin.value()
                new_after_low_span = self.new_after_low_span_spin.value()
                new_after_low_total = new_after_low_start + new_after_low_range + new_after_low_span
                if end_idx - new_after_low_total < 0:
                    QMessageBox.warning(self, "提示", "创后新低1日期范围超出数据范围，请调整！")
                    return None
                
                # 创后新低2参数
                new_after_low2_start = self.new_after_low2_start_spin.value()
                new_after_low2_range = self.new_after_low2_range_spin.value()
                new_after_low2_span = self.new_after_low2_span_spin.value()
                new_after_low2_total = new_after_low2_start + new_after_low2_range + new_after_low2_span
                if end_idx - new_after_low2_total < 0:
                    QMessageBox.warning(self, "提示", "创后新低2日期范围超出数据范围，请调整！")
                    return None
         
        current_formula = formula_expr if formula_expr is not None else (
            self.formula_expr_edit.toPlainText() if hasattr(self, 'formula_expr_edit') else ''
        )

        print(f"current_formula = {current_formula}")
    
        # 每次都强制重新计算
        # 收集所有参数
        params = {}
        # 获取end_date_start和end_date_end
        if is_auto_analysis and end_date_start is not None and end_date_end is not None:
            params['end_date_start'] = end_date_start
            params['end_date_end'] = end_date_end
        else:
            params['end_date_start'] = end_date
            params['end_date_end'] = end_date
        # 使用传入的参数值，如果没有传入则使用控件值
        params['width'] = width if width is not None else self.width_spin.value()
        params['start_option'] = self.start_option_combo.currentText()
        params['shift_days'] = self.shift_spin.value()
        params['is_forward'] = self.direction_checkbox.isChecked()
        params['n_days'] = self.n_days_spin.value()
        params['n_days_max'] = self.n_days_max_spin.value()
        params['range_value'] = self.range_value_edit.text()
        params['continuous_abs_threshold'] = self.continuous_abs_threshold_edit.text()
        params['op_days'] = str(op_days) if op_days is not None else self.op_days_edit.text()
        params['inc_rate'] = str(inc_rate) if inc_rate is not None else self.inc_rate_edit.text()
        params['after_gt_end_ratio'] = str(after_gt_end_ratio) if after_gt_end_ratio is not None else self.after_gt_end_edit.text()
        params['after_gt_start_ratio'] = str(after_gt_start_ratio) if after_gt_start_ratio is not None else self.after_gt_prev_edit.text()
        # 止损参数直接使用输入值，因为验证器已确保输入为非正数
                # 获取参数值
        stop_loss_inc_rate_val = stop_loss_inc_rate if stop_loss_inc_rate is not None else float(self.stop_loss_inc_rate_edit.text() or 0)
        stop_loss_after_gt_end_ratio_val = stop_loss_after_gt_end_ratio if stop_loss_after_gt_end_ratio is not None else float(self.stop_loss_after_gt_end_edit.text() or 0)
        stop_loss_after_gt_start_ratio_val = stop_loss_after_gt_start_ratio if stop_loss_after_gt_start_ratio is not None else float(self.stop_loss_after_gt_start_edit.text() or 0)
        
        # 如果参数大于0，统一设置为0
        if stop_loss_inc_rate_val > 0:
            stop_loss_inc_rate_val = 0
        if stop_loss_after_gt_end_ratio_val > 0:
            stop_loss_after_gt_end_ratio_val = 0
        if stop_loss_after_gt_start_ratio_val > 0:
            stop_loss_after_gt_start_ratio_val = 0
        
        params['stop_loss_inc_rate'] = str(stop_loss_inc_rate_val)
        params['stop_loss_after_gt_end_ratio'] = str(stop_loss_after_gt_end_ratio_val)
        params['stop_loss_after_gt_start_ratio'] = str(stop_loss_after_gt_start_ratio_val)
        
        params['trade_mode'] = self.trade_mode_combo.currentText()
        # 选股公式、数量、排序方式参数
        params['expr'] = self.last_expr  # 新增：操作值表达式
        params['select_count'] = select_count if select_count is not None else 10
        params['sort_mode'] = sort_mode if sort_mode else self.last_sort_mode
        params['ops_change'] = self.ops_change_edit.text()
        # 选股计算公式
        params['formula_expr'] = current_formula
        # 新增：创新高/创新低相关SpinBox参数
        # 如果有传递的new_high_low_params，使用传递的参数更新勾选的控件值
        if new_high_low_params and is_auto_analysis:
            # 更新勾选的创新高/创新低控件值
            if 'new_before_high_start' in new_high_low_params:
                self.new_before_high_start_spin.setValue(new_high_low_params['new_before_high_start'])
                self.new_before_high_range_spin.setValue(new_high_low_params['new_before_high_range'])
                self.new_before_high_span_spin.setValue(new_high_low_params['new_before_high_span'])
            if 'new_before_high2_start' in new_high_low_params:
                self.new_before_high2_start_spin.setValue(new_high_low_params['new_before_high2_start'])
                self.new_before_high2_range_spin.setValue(new_high_low_params['new_before_high2_range'])
                self.new_before_high2_span_spin.setValue(new_high_low_params['new_before_high2_span'])
            if 'new_after_high_start' in new_high_low_params:
                self.new_after_high_start_spin.setValue(new_high_low_params['new_after_high_start'])
                self.new_after_high_range_spin.setValue(new_high_low_params['new_after_high_range'])
                self.new_after_high_span_spin.setValue(new_high_low_params['new_after_high_span'])
            if 'new_after_high2_start' in new_high_low_params:
                self.new_after_high2_start_spin.setValue(new_high_low_params['new_after_high2_start'])
                self.new_after_high2_range_spin.setValue(new_high_low_params['new_after_high2_range'])
                self.new_after_high2_span_spin.setValue(new_high_low_params['new_after_high2_span'])
            if 'new_before_low_start' in new_high_low_params:
                self.new_before_low_start_spin.setValue(new_high_low_params['new_before_low_start'])
                self.new_before_low_range_spin.setValue(new_high_low_params['new_before_low_range'])
                self.new_before_low_span_spin.setValue(new_high_low_params['new_before_low_span'])
            if 'new_before_low2_start' in new_high_low_params:
                self.new_before_low2_start_spin.setValue(new_high_low_params['new_before_low2_start'])
                self.new_before_low2_range_spin.setValue(new_high_low_params['new_before_low2_range'])
                self.new_before_low2_span_spin.setValue(new_high_low_params['new_before_low2_span'])
            if 'new_after_low_start' in new_high_low_params:
                self.new_after_low_start_spin.setValue(new_high_low_params['new_after_low_start'])
                self.new_after_low_range_spin.setValue(new_high_low_params['new_after_low_range'])
                self.new_after_low_span_spin.setValue(new_high_low_params['new_after_low_span'])
            if 'new_after_low2_start' in new_high_low_params:
                self.new_after_low2_start_spin.setValue(new_high_low_params['new_after_low2_start'])
                self.new_after_low2_range_spin.setValue(new_high_low_params['new_after_low2_range'])
                self.new_after_low2_span_spin.setValue(new_high_low_params['new_after_low2_span'])
        
        # 收集创新高/创新低参数（使用更新后的控件值）
        params['new_before_high_start'] = self.new_before_high_start_spin.value()
        params['new_before_high_range'] = self.new_before_high_range_spin.value()
        params['new_before_high_span'] = self.new_before_high_span_spin.value()
        # 新增：创前新高2相关参数
        params['new_before_high2_start'] = self.new_before_high2_start_spin.value()
        params['new_before_high2_range'] = self.new_before_high2_range_spin.value()
        params['new_before_high2_span'] = self.new_before_high2_span_spin.value()
        params['new_before_high2_logic'] = self.new_before_high2_logic_combo.currentText()
        # 新增：创后新高1相关参数
        params['new_after_high_start'] = self.new_after_high_start_spin.value()
        params['new_after_high_range'] = self.new_after_high_range_spin.value()
        params['new_after_high_span'] = self.new_after_high_span_spin.value()
        params['new_after_high_logic'] = self.new_after_high_logic_combo.currentText()
        # 新增：创后新高2相关参数
        params['new_after_high2_start'] = self.new_after_high2_start_spin.value()
        params['new_after_high2_range'] = self.new_after_high2_range_spin.value()
        params['new_after_high2_span'] = self.new_after_high2_span_spin.value()
        params['new_after_high2_logic'] = self.new_after_high2_logic_combo.currentText()
        # 新增：创前新低1相关参数
        params['new_before_low_start'] = self.new_before_low_start_spin.value()
        params['new_before_low_range'] = self.new_before_low_range_spin.value()
        params['new_before_low_span'] = self.new_before_low_span_spin.value()
        params['new_before_low_logic'] = self.new_before_low_logic_combo.currentText()
        # 新增：创前新低2相关参数
        params['new_before_low2_start'] = self.new_before_low2_start_spin.value()
        params['new_before_low2_range'] = self.new_before_low2_range_spin.value()
        params['new_before_low2_span'] = self.new_before_low2_span_spin.value()
        params['new_before_low2_logic'] = self.new_before_low2_logic_combo.currentText()
        # 新增：创后新低1相关参数
        params['new_after_low_start'] = self.new_after_low_start_spin.value()
        params['new_after_low_range'] = self.new_after_low_range_spin.value()
        params['new_after_low_span'] = self.new_after_low_span_spin.value()
        params['new_after_low_logic'] = self.new_after_low_logic_combo.currentText()
        # 新增：创后新低2相关参数
        params['new_after_low2_start'] = self.new_after_low2_start_spin.value()
        params['new_after_low2_range'] = self.new_after_low2_range_spin.value()
        params['new_after_low2_span'] = self.new_after_low2_span_spin.value()
        params['new_after_low2_logic'] = self.new_after_low2_logic_combo.currentText()
        params['comparison_vars'] = comparison_vars
        
        # 添加盈损参数
        params['profit_type'] = profit_type
        params['loss_type'] = loss_type

        
        if only_show_selected is not None:
            params['only_show_selected'] = only_show_selected
        # 添加CPU核心数参数
        params['max_cores'] = self.cpu_spin.value()
        # 添加公式选股逻辑控件的勾选状态
        state = getattr(self, 'last_formula_select_state', {})
        params['start_with_new_before_high_flag'] = self.new_before_high_flag_checkbox.isChecked()
        params['start_with_new_before_high2_flag'] = self.new_before_high2_flag_checkbox.isChecked()
        params['start_with_new_after_high_flag'] = self.new_after_high_flag_checkbox.isChecked()
        params['start_with_new_after_high2_flag'] = self.new_after_high2_flag_checkbox.isChecked()
        params['start_with_new_before_low_flag'] = self.new_before_low_flag_checkbox.isChecked()
        params['start_with_new_before_low2_flag'] = self.new_before_low2_flag_checkbox.isChecked()
        params['start_with_new_after_low_flag'] = self.new_after_low_flag_checkbox.isChecked()
        params['start_with_new_after_low2_flag'] = self.new_after_low2_flag_checkbox.isChecked()
        params['valid_abs_sum_threshold'] = self.valid_abs_sum_threshold_edit.text()
        params['new_before_high_logic'] = self.new_before_high_logic_combo.currentText()
        print(f"select_count={params['select_count']}, sort_mode={params['sort_mode']}, width={params['width']}, op_days={params['op_days']}, increment_rate={params['inc_rate']}, after_gt_end_ratio={params['after_gt_end_ratio']}, after_gt_start_ratio={params['after_gt_start_ratio']}, stop_loss_inc_rate={params['stop_loss_inc_rate']}, stop_loss_after_gt_end_ratio={params['stop_loss_after_gt_end_ratio']}, stop_loss_after_gt_start_ratio={params['stop_loss_after_gt_start_ratio']}")
        result = self.base_param.on_calculate_clicked(params)
        if result is None:
            if show_main_output:
                self.result_text.setText("请先上传数据文件！")
                self.output_stack.setCurrentWidget(self.result_text)
            self.last_end_date = end_date
            # 只有非组合分析才保存公式，组合分析的公式一直在变化，不需要保存
            if not is_auto_analysis:
                self.last_formula_expr = current_formula
            self.last_calculate_result = None
            return None
        self.last_end_date = end_date
        # 只有非组合分析才保存公式，组合分析的公式一直在变化，不需要保存
        if not is_auto_analysis:
            self.last_formula_expr = current_formula
        self.last_calculate_result = result
        return self.last_calculate_result

    def create_analysis_table(self, valid_items, start_date, end_date):
        formula = getattr(self, 'last_formula_expr', '')
        if formula is None:
            formula = ''
        formula = formula.strip()
        row_count = len(valid_items)
        table = CopyableTableWidget(row_count + 2, 23, self.analysis_widget)  # 修正为13列
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

        # 使用新的分析结果计算函数
        result = calculate_analysis_result(valid_items)
        
        # 设置第一行的均值数据
        summary = result['summary']
        table.setItem(0, 1, QTableWidgetItem(str(summary['mean_hold_days'])))
        # 止盈止损
        table.setItem(0, 2, QTableWidgetItem(f"{summary['mean_adjust_ops_change']}%" if summary['mean_adjust_ops_change'] != '' else ''))
        table.setItem(0, 3, QTableWidgetItem(f"{summary['comprehensive_daily_change']}%" if summary['comprehensive_daily_change'] != '' else ''))
        table.setItem(0, 4, QTableWidgetItem(f"{summary['mean_adjust_daily_change']}%" if summary.get('mean_adjust_daily_change', '') != '' else ''))
        table.setItem(0, 5, QTableWidgetItem(f"{summary['mean_adjust_with_nan']}%" if summary['mean_adjust_with_nan'] != '' else ''))
        table.setItem(0, 6, QTableWidgetItem(f"{summary['mean_adjust_daily_with_nan']}%" if summary.get('mean_adjust_daily_with_nan', '') != '' else ''))

        # 止盈停损
        table.setItem(0, 7, QTableWidgetItem(f"{summary['mean_take_and_stop_change']}%" if summary['mean_take_and_stop_change'] != '' else ''))
        table.setItem(0, 8, QTableWidgetItem(f"{summary['comprehensive_take_and_stop_change']}%" if summary['comprehensive_take_and_stop_change'] != '' else ''))
        table.setItem(0, 9, QTableWidgetItem(f"{summary['mean_take_and_stop_daily_change']}%" if summary['mean_take_and_stop_daily_change'] != '' else ''))
        table.setItem(0, 10, QTableWidgetItem(f"{summary['mean_take_and_stop_with_nan']}%" if summary['mean_take_and_stop_with_nan'] != '' else ''))
        table.setItem(0, 11, QTableWidgetItem(f"{summary['mean_take_and_stop_daily_with_nan']}%" if summary['mean_take_and_stop_daily_with_nan'] != '' else ''))

        table.setItem(0, 12, QTableWidgetItem(str(summary['mean_adjust_days'])))

        # 停盈停损
        table.setItem(0, 13, QTableWidgetItem(f"{summary['mean_ops_change']}%" if summary['mean_ops_change'] != '' else ''))
        table.setItem(0, 14, QTableWidgetItem(f"{summary['comprehensive_stop_daily_change']}%" if summary['comprehensive_stop_daily_change'] != '' else ''))
        table.setItem(0, 15, QTableWidgetItem(f"{summary['mean_daily_change']}%" if summary['mean_daily_change'] != '' else ''))
        table.setItem(0, 16, QTableWidgetItem(f"{summary['mean_with_nan']}%" if summary['mean_with_nan'] != '' else ''))
        table.setItem(0, 17, QTableWidgetItem(f"{summary['mean_daily_with_nan']}%" if summary['mean_daily_with_nan'] != '' else ''))

        # 停盈止损
        table.setItem(0, 18, QTableWidgetItem(f"{summary['mean_stop_and_take_change']}%" if summary['mean_stop_and_take_change'] != '' else ''))
        table.setItem(0, 19, QTableWidgetItem(f"{summary['comprehensive_stop_and_take_change']}%" if summary['comprehensive_stop_and_take_change'] != '' else ''))
        table.setItem(0, 20, QTableWidgetItem(f"{summary['mean_stop_and_take_daily_change']}%" if summary['mean_stop_and_take_daily_change'] != '' else ''))
        table.setItem(0, 21, QTableWidgetItem(f"{summary['mean_stop_and_take_with_nan']}%" if summary['mean_stop_and_take_with_nan'] != '' else ''))
        table.setItem(0, 22, QTableWidgetItem(f"{summary['mean_stop_and_take_daily_with_nan']}%" if summary['mean_stop_and_take_daily_with_nan'] != '' else ''))

        # 设置每行的数据
        for row_idx, item in enumerate(result['items']):
            table.setItem(row_idx + 2, 0, QTableWidgetItem(item['date']))
            table.setItem(row_idx + 2, 1, QTableWidgetItem(str(item['hold_days'])))
            # 止盈止损
            table.setItem(row_idx + 2, 2, QTableWidgetItem(f"{item['adjust_ops_change']}%" if item['adjust_ops_change'] != '' else ''))
            table.setItem(row_idx + 2, 3, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 4, QTableWidgetItem(f"{item['adjust_daily_change']}%" if item['adjust_daily_change'] != '' else ''))
            table.setItem(row_idx + 2, 5, QTableWidgetItem(f"{round(item['adjust_with_nan_mean'],2)}%" if not math.isnan(item['adjust_with_nan_mean']) else ''))
            table.setItem(row_idx + 2, 6, QTableWidgetItem(""))  # 调幅含空值均值只在均值行

            # 止盈停损
            table.setItem(row_idx + 2, 7, QTableWidgetItem(f"{item['take_and_stop_change']}%" if item['take_and_stop_change'] != '' else ''))
            table.setItem(row_idx + 2, 8, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 9, QTableWidgetItem(f"{item['take_and_stop_daily_change']}%" if item['take_and_stop_daily_change'] != '' else ''))
            table.setItem(row_idx + 2, 10, QTableWidgetItem(f"{round(item['take_and_stop_with_nan_mean'],2)}%" if not math.isnan(item['take_and_stop_with_nan_mean']) else ''))
            table.setItem(row_idx + 2, 11, QTableWidgetItem(""))

            table.setItem(row_idx + 2, 12, QTableWidgetItem(str(item['adjust_days'])))

            # 停盈停损
            table.setItem(row_idx + 2, 13, QTableWidgetItem(f"{item['ops_change']}%" if item['ops_change'] != '' else ''))
            table.setItem(row_idx + 2, 14, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 15, QTableWidgetItem(f"{item['daily_change']}%" if item['daily_change'] != '' else ''))
            table.setItem(row_idx + 2, 16, QTableWidgetItem(f"{round(item['with_nan_mean'],2)}%" if not math.isnan(item['with_nan_mean']) else ''))
            table.setItem(row_idx + 2, 17, QTableWidgetItem(""))  # 含空值均值在summary中，这里暂时留空

            # 停盈止损
            table.setItem(row_idx + 2, 18, QTableWidgetItem(f"{item['stop_and_take_change']}%" if item['stop_and_take_change'] != '' else ''))
            table.setItem(row_idx + 2, 19, QTableWidgetItem(""))
            table.setItem(row_idx + 2, 20, QTableWidgetItem(f"{item['stop_and_take_daily_change']}%" if item['stop_and_take_daily_change'] != '' else ''))
            table.setItem(row_idx + 2, 21, QTableWidgetItem(f"{round(item['stop_and_take_with_nan_mean'],2)}%" if not math.isnan(item['stop_and_take_with_nan_mean']) else ''))
            table.setItem(row_idx + 2, 22, QTableWidgetItem(""))

        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

        # 在表格最后一行插入止盈止损率统计，跨所有列
        row = table.rowCount()
        table.insertRow(row)
        
        # 根据当前选中的变量类别动态生成文本
        profit_text, loss_text, profit_median_text, loss_median_text = self.get_profit_loss_text_by_category()
        
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

        # 在表格最后一行插入公式，跨所有列
        if formula:
            row = table.rowCount()
            table.insertRow(row)
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
            ("日期宽度", str(self.width_spin.value())),
            ("开始日期值选择", self.start_option_combo.currentText()),
            ("前移天数", str(self.shift_spin.value())),
            ("操作天数", self.op_days_edit.text()),
            ("止盈递增率", f"{self.inc_rate_edit.text()}%"),
            ("止盈后值大于结束值比例", f"{self.after_gt_end_edit.text()}%"),
            ("止盈后值大于前值比例", f"{self.after_gt_prev_edit.text()}%"),
            ("止损递增率", f"{self.stop_loss_inc_rate_edit.text()}%"),
            ("止损后值大于结束值比例", f"{self.stop_loss_after_gt_end_edit.text()}%"),
            ("止损大于前值比例", f"{self.stop_loss_after_gt_start_edit.text()}%"),
            ("操作涨幅", f"{self.ops_change_edit.text()}%")
        ]
        for i, (label, value) in enumerate(params):
            table.insertRow(row + i)
            table.setItem(row + i, 0, QTableWidgetItem(label))
            table.setItem(row + i, 1, QTableWidgetItem(value))

        # 设置第一列宽度为固定150px，其他列自适应
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 150)
        
        # 设置其他列自适应宽度，确保列名完全显示
        for i in range(1, table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        return table

    def show_cached_analysis_table(self):
        """所见即所得，展示上一次缓存的QTableWidget表格"""
        # 清理旧内容
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        if hasattr(self, 'cached_analysis_table') and self.cached_analysis_table is not None:
            self.analysis_result_layout.addWidget(self.cached_analysis_table)

    def on_generate_analysis(self):
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QMessageBox, QLabel
        formula = getattr(self, 'last_formula_expr', '')
        if formula is None:
            formula = ''
        formula = formula.strip()
        if not formula:
            self.analysis_result_text.setText("请先设置选股公式")
            return
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
        # 校验日期是否在范围内
        workdays = getattr(self.init, 'workdays_str', None)
        if not workdays:
            QMessageBox.warning(self, "日期错误", "没有可用的日期范围，请先上传数据文件！")
            return

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        workday_first = datetime.strptime(workdays[0], "%Y-%m-%d").date()
        workday_last = datetime.strptime(workdays[-1], "%Y-%m-%d").date()
        if start_dt > end_dt:
            QMessageBox.information(self, "提示", "结束日要大于开始日")
            return
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
            
        width = self.width_spin.value()
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
        # print(f"自动调整后的end_date: {end_date}")
        # 检查创新高新低日期宽度
        # 创新高参数
        new_before_high_flag = self.new_before_high_flag_checkbox.isChecked()
        new_before_high2_flag = self.new_before_high2_flag_checkbox.isChecked()
        new_after_high_flag = self.new_after_high_flag_checkbox.isChecked()
        new_after_high2_flag = self.new_after_high2_flag_checkbox.isChecked()
        new_before_low_flag = self.new_before_low_flag_checkbox.isChecked()
        new_before_low2_flag = self.new_before_low2_flag_checkbox.isChecked()
        new_after_low_flag = self.new_after_low_flag_checkbox.isChecked()
        new_after_low2_flag = self.new_after_low2_flag_checkbox.isChecked()

        nh_start = self.new_before_high_start_spin.value()
        nh_range = self.new_before_high_range_spin.value()
        nh_span = self.new_before_high_span_spin.value()
        nh_total = nh_start + nh_range + nh_span
        if new_before_high_flag and start_date_idx - nh_total < 0:
            QMessageBox.warning(self, "提示", "创前新高1日期范围超出数据范围，请调整结束日期开始日！")
            return None
        
        # 创前新高2参数
        nh2_start = self.new_before_high2_start_spin.value()
        nh2_range = self.new_before_high2_range_spin.value()
        nh2_span = self.new_before_high2_span_spin.value()
        nh2_total = nh2_start + nh2_range + nh2_span
        if new_before_high2_flag and start_date_idx - nh2_total < 0:
            QMessageBox.warning(self, "提示", "创前新高2日期范围超出数据范围，请调整结束日期开始日！")
            return None
        
        # 创后新高1参数
        new_after_high_start = self.new_after_high_start_spin.value()
        new_after_high_range = self.new_after_high_range_spin.value()
        new_after_high_span = self.new_after_high_span_spin.value()
        new_after_high_total = new_after_high_start + new_after_high_range + new_after_high_span
        if new_after_high_flag and start_date_idx - new_after_high_total < 0:
            QMessageBox.warning(self, "提示", "创后新高1日期范围超出数据范围，请调整结束日期开始日！")
            return None

        # 创后新高2参数
        new_after_high2_start = self.new_after_high2_start_spin.value()
        new_after_high2_range = self.new_after_high2_range_spin.value()
        new_after_high2_span = self.new_after_high2_span_spin.value()
        new_after_high2_total = new_after_high2_start + new_after_high2_range + new_after_high2_span
        if new_after_high2_flag and start_date_idx - new_after_high2_total < 0:
            QMessageBox.warning(self, "提示", "创后新高2日期范围超出数据范围，请调整结束日期开始日！")
            return None
            
        # 创前新低1参数
        nl_start = self.new_before_low_start_spin.value()
        nl_range = self.new_before_low_range_spin.value()
        nl_span = self.new_before_low_span_spin.value()
        nl_total = nl_start + nl_range + nl_span
        if new_before_low_flag and start_date_idx - nl_total < 0:
            QMessageBox.warning(self, "提示", "创新低日期范围超出数据范围，请调整结束日期开始日！")
            return None
        
        # 创前新低2参数
        nh2_start = self.new_before_high2_start_spin.value()
        nh2_range = self.new_before_high2_range_spin.value()
        nh2_span = self.new_before_high2_span_spin.value()
        nh2_total = nh2_start + nh2_range + nh2_span
        if new_before_high2_flag and start_date_idx - nh2_total < 0:
            QMessageBox.warning(self, "提示", "创前新高2日期范围超出数据范围，请调整结束日期开始日！")
            return None

        # 创后新低1参数
        new_after_low_start = self.new_after_low_start_spin.value()
        new_after_low_range = self.new_after_low_range_spin.value()
        new_after_low_span = self.new_after_low_span_spin.value()
        new_after_low_total = new_after_low_start + new_after_low_range + new_after_low_span
        if new_after_low_flag and start_date_idx - new_after_low_total < 0:
            QMessageBox.warning(self, "提示", "创后新低1日期范围超出数据范围，请调整结束日期开始日！")
            return None
        
        # 创后新低2参数
        new_after_low2_start = self.new_after_low2_start_spin.value()
        new_after_low2_range = self.new_after_low2_range_spin.value()
        new_after_low2_span = self.new_after_low2_span_spin.value()
        new_after_low2_total = new_after_low2_start + new_after_low2_range + new_after_low2_span
        if new_after_low2_flag and start_date_idx - new_after_low2_total < 0:
            QMessageBox.warning(self, "提示", "创后新低2日期范围超出数据范围，请调整结束日期开始日！")
            return None

        # 获取选股数量和排序方式
        select_count = getattr(self, 'last_select_count', 10)
        sort_mode = getattr(self, 'last_sort_mode', '最大值排序')
        profit_type = getattr(self, 'last_profit_type', 'INC')
        loss_type = getattr(self, 'last_loss_type', 'INC')
        
        # 获取比较变量列表 - 参考选股的do_select()函数
        comparison_vars = []
        # 从last_formula_select_state中获取比较变量
        if hasattr(self, 'last_formula_select_state') and self.last_formula_select_state:
            state = self.last_formula_select_state
            if 'comparison_vars' in state:
                comparison_vars = state['comparison_vars']
                print(f"从last_formula_select_state获取comparison_vars: {comparison_vars}")
        
        # 如果没有从状态中获取到，尝试从当前公式选股控件获取
        if not comparison_vars and hasattr(self, 'formula_select_widget') and self.formula_select_widget is not None:
            for comp in self.formula_select_widget.comparison_widgets:
                if comp['checkbox'].isChecked():
                    var1 = comp['var1'].currentText()
                    var2 = comp['var2'].currentText()
                    var1_en = next((en for zh, en in self.formula_select_widget.abbr_map.items() if zh == var1), None)
                    var2_en = next((en for zh, en in self.formula_select_widget.abbr_map.items() if zh == var2), None)
                    if var1_en and var2_en:
                        comparison_vars.append((var1_en, var2_en))  # 以元组对的形式添加
            print(f"从formula_select_widget获取comparison_vars: {comparison_vars}")
        
        comparison_vars = list(comparison_vars)  # 转换为list
        print(f"最终自动分析comparison_vars: {comparison_vars}")
        
        result = self.get_or_calculate_result(
            formula_expr=formula, 
            show_main_output=False, 
            only_show_selected=True, 
            is_auto_analysis=True,
            select_count=select_count,
            sort_mode=sort_mode,
            end_date_start=start_date,
            end_date_end=end_date,
            comparison_vars=comparison_vars,
            profit_type=profit_type,
            loss_type=loss_type
        )
        self.last_auto_analysis_result = result  # 新增：只给自动分析用
        merged_results = result.get('dates', {}) if result else {}
        valid_items = [(date_key, stocks) for date_key, stocks in merged_results.items()]
        # 缓存数据
        self.analysis_table_cache_data = {
            "valid_items": valid_items,
            "start_date": start_date,
            "end_date": end_date
        }
        # 清理旧内容
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 创建新表格
        table = self.create_analysis_table(valid_items, start_date, end_date)
        self.analysis_result_layout.addWidget(table)
        # 保存表格数据和跨列信息
        span_info = []
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                span = table.span(row, col)
                if span.rowCount() > 1 or span.columnCount() > 1:
                    span_info.append({
                        'row': row,
                        'col': col,
                        'row_span': span.rowCount(),
                        'col_span': span.columnCount()
                    })
        
        self.cached_table_data = {
            "headers": [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())],
            "data": [[table.item(i, j).text() if table.item(i, j) else "" for j in range(table.columnCount())] for i in range(table.rowCount())],
            "formula": formula,
            "span_info": span_info
        }

    def on_auto_analysis_btn_clicked(self):
        self.clear_result_area()
        # 创建自动分析子界面整体widget
        self.analysis_widget = QWidget()
        layout = QVBoxLayout(self.analysis_widget)
        # 顶部参数控件
        row_layout = QHBoxLayout()
        self.start_date_label = QLabel("结束日期开始日:")
        self.start_date_picker = QDateEdit(calendarPopup=True)
        # 优先使用last_analysis_start_date，如果没有则默认今天
        if hasattr(self, 'last_analysis_start_date') and self.last_analysis_start_date:
            self.start_date_picker.setDate(QDate.fromString(self.last_analysis_start_date, "yyyy-MM-dd"))
            print(f"使用last_analysis_start_date: {self.last_analysis_start_date}")
        else:
            self.start_date_picker.setDate(QDate.currentDate())
            print("使用默认今天作为开始日期")
        self.end_date_label = QLabel("结束日期结束日:")
        self.end_date_picker = QDateEdit(calendarPopup=True)
        # 优先使用last_analysis_end_date，如果没有则默认今天
        if hasattr(self, 'last_analysis_end_date') and self.last_analysis_end_date:
            self.end_date_picker.setDate(QDate.fromString(self.last_analysis_end_date, "yyyy-MM-dd"))
            print(f"使用last_analysis_end_date: {self.last_analysis_end_date}")
        else:
            self.end_date_picker.setDate(QDate.currentDate())
            print("使用默认今天作为结束日期")
        # 绑定信号，变更时同步变量
        self.start_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
        self.end_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
        
        # 设置文件上传监听器
        self.setup_analysis_file_upload_listener()
        # 新增导出按钮
        self.export_excel_btn = QPushButton("导出Excel")
        self.export_excel_btn.clicked.connect(self.on_export_excel)
        self.export_csv_btn = QPushButton("导出CSV")
        self.export_csv_btn.clicked.connect(self.on_export_csv)
        # 新增导入按钮
        self.import_excel_btn = QPushButton("导入Excel")
        self.import_excel_btn.clicked.connect(self.on_import_excel)
        self.import_csv_btn = QPushButton("导入CSV")
        self.import_csv_btn.clicked.connect(self.on_import_csv)
        self.generate_btn = QPushButton("点击生成")
        self.generate_btn.clicked.connect(self.on_generate_analysis)
        row_layout.addWidget(self.start_date_label)
        row_layout.addWidget(self.start_date_picker)
        row_layout.addWidget(self.end_date_label)
        row_layout.addWidget(self.end_date_picker)
        row_layout.addWidget(self.generate_btn)
        row_layout.addWidget(self.export_excel_btn)
        row_layout.addWidget(self.export_csv_btn)
        row_layout.addWidget(self.import_excel_btn)
        row_layout.addWidget(self.import_csv_btn)
    
        row_layout.addStretch()
        layout.addLayout(row_layout)
        # 输出区
        self.analysis_result_area = QWidget()
        self.analysis_result_layout = QVBoxLayout(self.analysis_result_area)
        self.analysis_result_layout.setContentsMargins(0, 0, 0, 0)
        self.analysis_result_layout.setSpacing(0)
        self.analysis_result_text = QTextEdit()
        self.analysis_result_text.setReadOnly(True)
        self.analysis_result_text.setMinimumHeight(300)
        self.analysis_result_layout.addWidget(self.analysis_result_text)
        layout.addWidget(self.analysis_result_area)
        # 只把整个analysis_widget放进output_stack
        self.table_widget = self.analysis_widget
        self.output_stack.addWidget(self.analysis_widget)
        self.output_stack.setCurrentWidget(self.analysis_widget)
        # 切换到自动分析tab
        self.output_stack.setCurrentWidget(self.analysis_widget)
        # 清理内容区
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 展示缓存表格
        if hasattr(self, 'cached_table_data') and self.cached_table_data is not None:
            # 创建新表格
            data = self.cached_table_data["data"]
            formula = self.cached_table_data["formula"]
            table = QTableWidget(len(data), len(self.cached_table_data["headers"]), self.analysis_widget)
            table.setHorizontalHeaderLabels(self.cached_table_data["headers"])
            # 填充数据
            for i, row in enumerate(data):
                for j, cell in enumerate(row):
                    # 检查是否是止盈止损率统计行
                    if j == 0 and '总股票数' in cell and '持有率' in cell and '止盈率' in cell and '止损率' in cell:
                        item = QTableWidgetItem(cell)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        item.setToolTip(cell)
                        table.setItem(i, 0, item)
                        table.setSpan(i, 0, 1, table.columnCount())
                        table.setWordWrap(True)
                        table.resizeRowToContents(i)
                    # 检查是否是中位数统计行
                    elif j == 0 and '持有中位数' in cell and '止盈中位数' in cell and '止损中位数' in cell:
                        item = QTableWidgetItem(cell)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        item.setToolTip(cell)
                        table.setItem(i, 0, item)
                        table.setSpan(i, 0, 1, table.columnCount())
                        table.setWordWrap(True)
                        table.resizeRowToContents(i)
                    # 检查是否是公式行
                    elif j == 0 and cell.startswith("选股公式"):
                        item = QTableWidgetItem(f"选股公式:\n{formula}")
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                        item.setToolTip(item.text())
                        table.setItem(i, 0, item)
                        table.setSpan(i, 0, 1, table.columnCount())
                        table.setWordWrap(True)
                        table.resizeRowToContents(i)
                    else:
                        item = QTableWidgetItem(cell)
                        table.setItem(i, j, item)
            # 设置第一列宽度为固定150px，其他列自适应
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Fixed)
            table.setColumnWidth(0, 150)
            
            # 设置其他列自适应宽度，确保列名完全显示
            for i in range(1, table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
                
            self.analysis_result_layout.addWidget(table)
        else:
            self.analysis_result_layout.addWidget(self.analysis_result_text)

    def _on_analysis_date_changed_save(self):
        self.last_analysis_start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        self.last_analysis_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")

    def setup_analysis_file_upload_listener(self):
        
        #设置自动分析界面的文件上传成功监听器
        # 监听主窗口的文件上传成功事件
        if hasattr(self, 'init') and hasattr(self.init, 'on_file_loaded'):
            # 保存原始的文件加载完成方法
            original_on_file_loaded = self.init.on_file_loaded
            
            def new_on_file_loaded(df, price_data, diff_data, workdays_str, error_msg):
                # 调用原始方法
                original_on_file_loaded(df, price_data, diff_data, workdays_str, error_msg)
                
                # 如果没有错误，更新自动分析界面的日期
                if not error_msg and workdays_str and len(workdays_str) > 0:
                    # 更新主窗口的缓存
                    self.last_analysis_start_date = workdays_str[-1]
                    self.last_analysis_end_date = workdays_str[-1]
                    print(f"文件上传成功，更新自动分析日期: {workdays_str[-1]}")
                    
                    # 如果自动分析界面已经创建，则立即设置日期
                    if hasattr(self, 'start_date_picker') and self.start_date_picker is not None:
                        try:
                            self.start_date_picker.setDate(QDate.fromString(workdays_str[-1], "yyyy-MM-dd"))
                            print(f"立即设置自动分析开始日期为: {workdays_str[-1]}")
                        except Exception as e:
                            print(f"立即设置开始日期失败: {e}")
                    
                    if hasattr(self, 'end_date_picker') and self.end_date_picker is not None:
                        try:
                            self.end_date_picker.setDate(QDate.fromString(workdays_str[-1], "yyyy-MM-dd"))
                            print(f"立即设置自动分析结束日期为: {workdays_str[-1]}")
                        except Exception as e:
                            print(f"立即设置结束日期失败: {e}")
            
            # 替换方法
            self.init.on_file_loaded = new_on_file_loaded

    def on_op_stat_btn_clicked(self):
        self.clear_result_area()
        # 创建操作统计子界面整体widget
        self.op_stat_widget = QWidget()
        layout = QVBoxLayout(self.op_stat_widget)
        # 顶部控件区
        row_layout = QHBoxLayout()
        self.op_stat_export_excel_btn = QPushButton("导出Excel")
        self.op_stat_export_excel_btn.clicked.connect(self.on_op_stat_export_excel)
        self.op_stat_export_csv_btn = QPushButton("导出CSV")
        self.op_stat_export_csv_btn.clicked.connect(self.on_op_stat_export_csv)
        row_layout.addWidget(self.op_stat_export_excel_btn)
        row_layout.addWidget(self.op_stat_export_csv_btn)
        row_layout.addStretch()
        layout.addLayout(row_layout)
        # 输出区
        self.op_stat_result_area = QWidget()
        self.op_stat_result_layout = QVBoxLayout(self.op_stat_result_area)
        self.op_stat_result_layout.setContentsMargins(0, 0, 0, 0)
        self.op_stat_result_layout.setSpacing(0)
        # 生成表格
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
        result = getattr(self, 'last_auto_analysis_result', None)
        merged_results = result.get('dates', {}) if result else {}
        if not merged_results or not any(merged_results.values()):
            self.result_text.setText("请先进行自动分析")
            self.output_stack.setCurrentWidget(self.result_text)
            return
        
        # 过滤掉stock_idx为-1、-2、-3的结果
        filtered_merged_results = {}
        for end_date, stocks in merged_results.items():
            filtered_stocks = [stock for stock in stocks if stock.get('stock_idx') not in [-1, -2, -3]]
            if filtered_stocks:  # 只保留有有效股票数据的日期
                filtered_merged_results[end_date] = filtered_stocks
        
        merged_results = filtered_merged_results  # 使用过滤后的结果
        
        group_size = 19
        end_dates = [d for d, stocks in merged_results.items() if stocks]
        blocks = [end_dates[i:i+group_size] for i in range(0, len(end_dates), group_size)]
        block_max_counts = [max((len(merged_results[d]) for d in block), default=0) for block in blocks]
        # 每组多分配一行空行
        total_rows = sum([max_count + 2 for max_count in block_max_counts])  # +1表头，+1空行
        max_block_len = max(len(block) for block in blocks) if blocks else 0
        col_count = max_block_len * 3
        table = CopyableTableWidget(total_rows, col_count, self.op_stat_widget)
        row_offset = 0
        for block_idx, block in enumerate(blocks):
            max_count = block_max_counts[block_idx]
            # 表头
            for i, end_date in enumerate(block):
                col_base = i * 3
                table.setItem(row_offset, col_base, QTableWidgetItem(str(end_date)))
                table.setItem(row_offset, col_base+1, QTableWidgetItem("股票代码"))
                table.setItem(row_offset, col_base+2, QTableWidgetItem("股票名称"))
            # 股票数据
            for row in range(max_count):
                for i, end_date in enumerate(block):
                    stocks = merged_results[end_date]
                    col_base = i * 3
                    if row < len(stocks):
                        stock = stocks[row]
                        stock_idx = stock.get('stock_idx')
                        if stock_idx is not None and hasattr(self, 'init') and hasattr(self.init, 'price_data'):
                            code = str(self.init.price_data.iloc[int(stock_idx), 0])
                            name = str(self.init.price_data.iloc[int(stock_idx), 1])
                        else:
                            code = str(stock.get('code', stock.get('stock_idx', '')))
                            name = str(stock.get('name', ''))
                        table.setItem(row_offset+row+1, col_base+1, QTableWidgetItem(code))
                        table.setItem(row_offset+row+1, col_base+2, QTableWidgetItem(name))
                    else:
                        table.setItem(row_offset+row+1, col_base+1, QTableWidgetItem(""))
                        table.setItem(row_offset+row+1, col_base+2, QTableWidgetItem(""))
            # 添加一行空行
            for i in range(len(block)):
                col_base = i * 3
                table.setItem(row_offset+max_count+1, col_base, QTableWidgetItem(""))
                table.setItem(row_offset+max_count+1, col_base+1, QTableWidgetItem(""))
                table.setItem(row_offset+max_count+1, col_base+2, QTableWidgetItem(""))
            row_offset += max_count + 2  # 表头+数据行+空行
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")
        # 清理旧内容并显示新表格
        for i in reversed(range(self.op_stat_result_layout.count())):
            widget = self.op_stat_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        self.op_stat_result_layout.addWidget(table)
        layout.addWidget(self.op_stat_result_area)
        # 只把整个op_stat_widget放进output_stack
        self.table_widget = self.op_stat_widget
        self.output_stack.addWidget(self.op_stat_widget)
        self.output_stack.setCurrentWidget(self.op_stat_widget)

    def on_op_stat_export_excel(self):
        # 获取当前表格数据
        table = None
        for i in range(self.op_stat_result_layout.count()):
            widget = self.op_stat_result_layout.itemAt(i).widget()
            if hasattr(widget, 'rowCount') and hasattr(widget, 'columnCount'):
                table = widget
                break
        if table is None:
            QMessageBox.warning(self, "提示", "没有可导出的表格数据！")
            return
        # 读取表格内容
        data = []
        headers = []
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item else f"列{col+1}")
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        df = pd.DataFrame(data, columns=headers)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存为Excel文件", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            try:
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "导出成功", f"已成功导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出Excel失败：{e}")

    def on_op_stat_export_csv(self):
        # 获取当前表格数据
        table = None
        for i in range(self.op_stat_result_layout.count()):
            widget = self.op_stat_result_layout.itemAt(i).widget()
            if hasattr(widget, 'rowCount') and hasattr(widget, 'columnCount'):
                table = widget
                break
        if table is None:
            QMessageBox.warning(self, "提示", "没有可导出的表格数据！")
            return
        # 读取表格内容
        data = []
        headers = []
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item else f"列{col+1}")
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        df = pd.DataFrame(data, columns=headers)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存为CSV文件", "", "CSV Files (*.csv)")
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            try:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "导出成功", f"已成功导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出CSV失败：{e}")

    def on_component_analysis_btn_clicked(self):
        """组合分析按钮点击事件"""
        # 直接显示组合分析界面
        self.show_component_analysis_interface()

    def show_component_analysis_interface(self):
        """显示组合分析界面"""
        from ui.component_analysis_ui import ComponentAnalysisWidget
        
        self.clear_result_area()
        component_widget = ComponentAnalysisWidget(self)
        
        # 恢复之前保存的勾选框状态
        if hasattr(self, 'last_component_continuous_sum_logic'):
            component_widget.continuous_sum_logic_checkbox.setChecked(self.last_component_continuous_sum_logic)
        if hasattr(self, 'last_component_valid_sum_logic'):
            component_widget.valid_sum_logic_checkbox.setChecked(self.last_component_valid_sum_logic)
        
        component_widget.setMinimumSize(1200, 600)
        self.component_widget = component_widget  # 保存引用以便后续保存状态
        self.table_widget = component_widget
        self.output_stack.addWidget(component_widget)
        self.output_stack.setCurrentWidget(component_widget)
        # 恢复分析结果
        if hasattr(self, '_pending_component_analysis_results'):
            component_widget.set_cached_analysis_results(self._pending_component_analysis_results)
            del self._pending_component_analysis_results

    def on_export_excel(self):
        # 获取当前表格数据
        table = None
        for i in range(self.analysis_result_layout.count()):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if hasattr(widget, 'rowCount') and hasattr(widget, 'columnCount'):
                table = widget
                break
        if table is None:
            QMessageBox.warning(self, "提示", "没有可导出的表格数据！")
            return
        # 读取表格内容
        data = []
        headers = []
        for col in range(table.columnCount()):
            headers.append(table.horizontalHeaderItem(col).text())
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        df = pd.DataFrame(data, columns=headers)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存为Excel文件", "", "Excel Files (*.xlsx)")
        if file_path:
            if not file_path.endswith('.xlsx'):
                file_path += '.xlsx'
            try:
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "导出成功", f"已成功导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出Excel失败：{e}")

    def on_export_csv(self):
        # 获取当前表格数据
        table = None
        for i in range(self.analysis_result_layout.count()):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if hasattr(widget, 'rowCount') and hasattr(widget, 'columnCount'):
                table = widget
                break
        if table is None:
            QMessageBox.warning(self, "提示", "没有可导出的表格数据！")
            return
        # 读取表格内容
        data = []
        headers = []
        for col in range(table.columnCount()):
            headers.append(table.horizontalHeaderItem(col).text())
        for row in range(table.rowCount()):
            row_data = []
            for col in range(table.columnCount()):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        df = pd.DataFrame(data, columns=headers)
        file_path, _ = QFileDialog.getSaveFileName(self, "保存为CSV文件", "", "CSV Files (*.csv)")
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            try:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "导出成功", f"已成功导出到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出CSV失败：{e}")

    def on_import_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入Excel文件", "", "Excel Files (*.xlsx *.xls)")
        if not file_path:
            return
        df = pd.read_excel(file_path)
        self._show_imported_analysis(df)

    def on_import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入CSV文件", "", "CSV Files (*.csv)")
        if not file_path:
            return
        df = pd.read_csv(file_path)
        self._show_imported_analysis(df)

    def _show_imported_analysis(self, df):
        # 假设最后一行是公式行，且在第一列
        formula = ''
        params = {}
        stats_info = {}
        
        # 查找止盈止损率统计行
        for i in range(df.shape[0]):
            first_cell = str(df.iloc[i, 0])
            if '总股票数' in first_cell and '持有率' in first_cell and '止盈率' in first_cell and '止损率' in first_cell:
                # 解析统计信息
                stats_text = first_cell
                # 提取数值
                import re
                total_match = re.search(r'总股票数: (\d+)', stats_text)
                hold_match = re.search(r'持有率: ([\d.]+)%', stats_text)
                profit_match = re.search(r'止盈率: ([\d.]+)%', stats_text)
                loss_match = re.search(r'止损率: ([\d.]+)%', stats_text)
                
                if total_match:
                    stats_info['total_stocks'] = int(total_match.group(1))
                if hold_match:
                    stats_info['hold_rate'] = float(hold_match.group(1))
                if profit_match:
                    stats_info['profit_rate'] = float(profit_match.group(1))
                if loss_match:
                    stats_info['loss_rate'] = float(loss_match.group(1))
                break
        
        # 查找中位数统计行
        for i in range(df.shape[0]):
            first_cell = str(df.iloc[i, 0])
            if '持有中位数' in first_cell and '止盈中位数' in first_cell and '止损中位数' in first_cell:
                # 解析中位数信息
                median_text = first_cell
                # 提取数值
                import re
                hold_median_match = re.search(r'持有中位数: ([^%]+)%', median_text)
                profit_median_match = re.search(r'止盈中位数: ([^%]+)%', median_text)
                loss_median_match = re.search(r'止损中位数: ([^%]+)%', median_text)
                
                if hold_median_match:
                    hold_median_val = hold_median_match.group(1).strip()
                    if hold_median_val != 'N/A':
                        stats_info['hold_median'] = float(hold_median_val)
                if profit_median_match:
                    profit_median_val = profit_median_match.group(1).strip()
                    if profit_median_val != 'N/A':
                        stats_info['profit_median'] = float(profit_median_val)
                if loss_median_match:
                    loss_median_val = loss_median_match.group(1).strip()
                    if loss_median_val != 'N/A':
                        stats_info['loss_median'] = float(loss_median_val)
                break
        # 查找公式行
        formula_row_idx = None
        for i in range(df.shape[0]):
            first_cell = str(df.iloc[i, 0])
            if first_cell.startswith('选股公式'):
                formula = first_cell.replace('选股公式:', '').replace('选股公式', '').strip()
                formula_row_idx = i
                break
        # 查找参数行
        param_rows = []
        param_start_idx = None
        for i in range(df.shape[0]):
            first_cell = str(df.iloc[i, 0])
            if first_cell in [
                "日期宽度", "开始日期值选择", "前移天数", "操作天数", 
                "止盈递增率", "止盈后值大于结束值比例", "止盈后值大于前值比例", "止损递增率", "止损后值大于结束值比例", "止损大于前值比例", "操作涨幅"
            ]:
                param_start_idx = i
                break
        if param_start_idx is not None:
            param_rows = [df.iloc[j] for j in range(param_start_idx, df.shape[0])]
            for row in param_rows:
                if isinstance(row.iloc[0], str) and row.iloc[0] in [
                    "日期宽度", "开始日期值选择", "前移天数", "操作天数", 
                    "止盈递增率", "止盈后值大于结束值比例", "止盈后值大于前值比例", "止损递增率", "止损后值大于结束值比例", "止损大于前值比例", "操作涨幅"
                ]:
                    params[row.iloc[0]] = row.iloc[1]
        # 恢复参数到控件（用导入文件中的值）
        param_map = {
            "日期宽度": (self.width_spin, int),
            "开始日期值选择": (self.start_option_combo, str),
            "前移天数": (self.shift_spin, int),
            "操作天数": (self.op_days_edit, str),
            "止盈递增率": (self.inc_rate_edit, lambda v: v.replace('%','')),
            "止盈后值大于结束值比例": (self.after_gt_end_edit, lambda v: v.replace('%','')),
            "止盈后值大于前值比例": (self.after_gt_prev_edit, lambda v: v.replace('%','')),
            "止损递增率": (self.stop_loss_inc_rate_edit, lambda v: v.replace('%','')),
            "止损后值大于结束值比例": (self.stop_loss_after_gt_end_edit, lambda v: v.replace('%','')),
            "止损大于前值比例": (self.stop_loss_after_gt_start_edit, lambda v: v.replace('%','')),
            "操作涨幅": (self.ops_change_edit, lambda v: v.replace('%','')),
        }
        print("导入参数：", params)  # 调试用
        for key, (widget, val_func) in param_map.items():
            if key in params:
                val = str(params[key]).strip()
                try:
                    if hasattr(widget, 'setValue'):
                        widget.setValue(val_func(val))
                    elif hasattr(widget, 'setText'):
                        widget.setText(val_func(val))
                    elif hasattr(widget, 'findText') and hasattr(widget, 'setCurrentIndex'):
                        idx = widget.findText(val_func(val))
                        if idx >= 0:
                            widget.setCurrentIndex(idx)
                except Exception as e:
                    print(f"恢复控件 {key} 失败: {e}")
        # 恢复公式相关控件
        if formula:
            self._restore_formula_controls_from_formula(formula)
        # 清理旧内容
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 直接用导入的表格内容原样展示
        row_count = df.shape[0]
        col_count = df.shape[1]
        table = QTableWidget(row_count, col_count, self.analysis_widget)
        table.setHorizontalHeaderLabels([str(col) for col in df.columns])
        for i in range(row_count):
            first_cell = str(df.iat[i, 0])
            if '总股票数' in first_cell and '持有率' in first_cell and '止盈率' in first_cell and '止损率' in first_cell:
                item = QTableWidgetItem(first_cell)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setToolTip(first_cell)
                table.setItem(i, 0, item)
                table.setSpan(i, 0, 1, col_count)
                table.setWordWrap(True)
                table.resizeRowToContents(i)
            elif '持有中位数' in first_cell and '止盈中位数' in first_cell and '止损中位数' in first_cell:
                # 中位数统计行跨列展示
                item = QTableWidgetItem(first_cell)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item.setToolTip(first_cell)
                table.setItem(i, 0, item)
                table.setSpan(i, 0, 1, col_count)
                table.setWordWrap(True)
                table.resizeRowToContents(i)
            elif formula_row_idx is not None and i == formula_row_idx:
                # 公式行跨列展示
                item = QTableWidgetItem(f"选股公式:\n{formula}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                item.setToolTip(item.text())
                table.setItem(i, 0, item)
                table.setSpan(i, 0, 1, col_count)
                table.setWordWrap(True)
                table.resizeRowToContents(i)
            else:
                for j in range(col_count):
                    val = df.iat[i, j]
                    if pd.isna(val) or str(val).lower() == 'nan':
                        val = ''
                    table.setItem(i, j, QTableWidgetItem(str(val)))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 150)
        for i in range(1, table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.analysis_result_layout.addWidget(table)
        # 保存表格数据和跨列信息
        span_info = []
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                span = table.span(row, col)
                if span.rowCount() > 1 or span.columnCount() > 1:
                    span_info.append({
                        'row': row,
                        'col': col,
                        'row_span': span.rowCount(),
                        'col_span': span.columnCount()
                    })
        
        self.cached_table_data = {
            "headers": [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())],
            "data": [[table.item(i, j).text() if table.item(i, j) else "" for j in range(table.columnCount())] for i in range(table.rowCount())],
            "formula": formula,
            "span_info": span_info
        }

    def _restore_formula_controls_from_formula(self, formula):
        """
        解析公式字符串，自动勾选变量控件、设置上下限、比较控件、向前参数等。
        参考组合分析restore_formula_params方法，创建临时控件解析公式并保存状态。
        """
        import re
        try:
            print(f"开始恢复公式控件: {formula}")
            
            # 创建临时的公式选股控件
            from function.stock_functions import get_abbr_map, get_abbr_logic_map, get_abbr_round_map, FormulaSelectWidget
            abbr_map = get_abbr_map()
            logic_map = get_abbr_logic_map()
            round_map = get_abbr_round_map()
            
            temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self)
            
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
            if hasattr(self, 'forward_param_state') and self.forward_param_state:
                print(f"重置forward_param_state: {self.forward_param_state}")
                for var_name, var_state in self.forward_param_state.items():
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
                        self.forward_param_state[var_name] = False
                        print(f"重置向前参数布尔值: {var_name} = False")
            
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
            if hasattr(self, 'forward_param_state') and self.forward_param_state:
                forward_widgets = self.forward_param_state
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
                        if 'checkbox' in widgets:
                            widgets['checkbox'].setChecked(True)
                            print(f"勾选变量控件: {var}")
                        if 'lower' in widgets:
                            widgets['lower'].setText(str(lower))
                            print(f"设置下限值: {var} = {lower}")
                        processed_vars.add(var)  # 标记为已处理
                    # 再检查是否在forward_param_state中
                    elif var in forward_widgets:
                        print(f"找到forward_param_state中的下限条件: {var} >= {lower}")
                        var_state = forward_widgets[var]
                        if isinstance(var_state, dict):
                            # 对于条件变量，enable直接设为true
                            print(f"设置forward_param_state下限复选框为true: {var}")
                            # 实际设置需要在主窗口的forward_param_state中更新
                            if hasattr(self, 'forward_param_state') and var in self.forward_param_state:
                                if isinstance(self.forward_param_state[var], dict):
                                    self.forward_param_state[var]['enable'] = True
                                    self.forward_param_state[var]['lower'] = lower
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
                        if 'checkbox' in widgets:
                            widgets['checkbox'].setChecked(True)
                            print(f"勾选变量控件: {var}")
                        if 'upper' in widgets:
                            widgets['upper'].setText(str(upper))
                            print(f"设置上限值: {var} = {upper}")
                        processed_vars.add(var)  # 标记为已处理
                    # 再检查是否在forward_param_state中
                    elif var in forward_widgets:
                        print(f"找到forward_param_state中的上限条件: {var} <= {upper}")
                        var_state = forward_widgets[var]
                        if isinstance(var_state, dict):
                            # 对于条件变量，enable直接设为true
                            print(f"设置forward_param_state上限复选框为true: {var}")
                            # 实际设置需要在主窗口的forward_param_state中更新
                            if hasattr(self, 'forward_param_state') and var in self.forward_param_state:
                                if isinstance(self.forward_param_state[var], dict):
                                    self.forward_param_state[var]['enable'] = True
                                    self.forward_param_state[var]['upper'] = upper
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
                            if hasattr(self, 'forward_param_state') and var in self.forward_param_state:
                                if isinstance(self.forward_param_state[var], dict):
                                    self.forward_param_state[var]['enable'] = True
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
                            # 实际设置需要在主窗口的forward_param_state中更新
                            if hasattr(self, 'forward_param_state') and var in self.forward_param_state:
                                if isinstance(self.forward_param_state[var], dict):
                                    self.forward_param_state[var]['round'] = True
                                    print(f"已更新forward_param_state圆框: {var} = True")
                        elif isinstance(var_state, bool):
                            print(f"forward_param_state布尔值变量: {var} = {var_state}")
                    else:
                        print(f"result变量 {var} 不在控件列表中")
            
            # 5. 处理比较控件
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
            
            # 获取当前状态
            current_state = temp_formula_widget.get_state()
            
            # 如果有比较控件配置，添加到状态中
            if comparison_configs:
                current_state['comparison_widgets'] = comparison_configs
                print(f"添加比较控件配置到状态中")
            
            # 更新主窗口的last_formula_select_state
            self.last_formula_select_state = current_state
            print(f"已保存状态到主窗口: {len(current_state)} 个变量")
            
            # 清理临时控件
            temp_formula_widget.deleteLater()
            
            print("公式控件恢复完成")
            
        except Exception as e:
            print(f"恢复公式控件失败: {e}")
            import traceback
            traceback.print_exc()

    def save_config(self):
        config = {
            'width': self.width_spin.value(),
            'start_option': self.start_option_combo.currentIndex(),
            'shift': self.shift_spin.value(),
            'inc_rate': self.inc_rate_edit.text(),
            'op_days': self.op_days_edit.text(),
            'after_gt_end_ratio': self.after_gt_end_edit.text(),
            'after_gt_start_ratio': self.after_gt_prev_edit.text(),
            'stop_loss_inc_rate': self.stop_loss_inc_rate_edit.text(),
            'stop_loss_after_gt_end_ratio': self.stop_loss_after_gt_end_edit.text(),
            'stop_loss_after_gt_start_ratio': self.stop_loss_after_gt_start_edit.text(),
            'n_days': self.n_days_spin.value(),
            'n_days_max': self.n_days_max_spin.value(),
            'range_value': self.range_value_edit.text(),
            'continuous_abs_threshold': self.continuous_abs_threshold_edit.text(),
            'ops_change': self.ops_change_edit.text(),
            'expr': getattr(self, 'last_expr', ''),  # 新增：操作值表达式
            'last_formula_expr': getattr(self, 'last_formula_expr', ''),
            'last_select_count': getattr(self, 'last_select_count', 10),
            'last_sort_mode': getattr(self, 'last_sort_mode', '最大值排序'),
            'last_profit_type': getattr(self, 'last_profit_type', 'INC'),  # 新增：盈类型缓存
            'last_loss_type': getattr(self, 'last_loss_type', 'INC'),      # 新增：损类型缓存
            'direction': self.direction_checkbox.isChecked(),
            'component_analysis_start_date': getattr(self, 'last_component_analysis_start_date', ''),
            'component_analysis_end_date': getattr(self, 'last_component_analysis_end_date', ''),
            'cpu_cores': self.cpu_spin.value(),
            'last_formula_select_state': getattr(self, 'last_formula_select_state', {}),
            'analysis_table_cache_data': getattr(self, 'analysis_table_cache_data', None),
            'cached_table_data': getattr(self, 'cached_table_data', None),
            'trade_mode': self.trade_mode_combo.currentText(),
            # 新增：创新高/创新低相关SpinBox控件
            'new_before_high_start': self.new_before_high_start_spin.value(),
            'new_before_high_range': self.new_before_high_range_spin.value(),
            'new_before_high_span': self.new_before_high_span_spin.value(),
            'new_before_low_start': self.new_before_low_start_spin.value(),
            'new_before_low_range': self.new_before_low_range_spin.value(),
            'new_before_low_span': self.new_before_low_span_spin.value(),
            'valid_abs_sum_threshold': self.valid_abs_sum_threshold_edit.text(),
            'new_before_high_logic': self.new_before_high_logic_combo.currentText(),
            # 新增：创前新高2相关参数
            'new_before_high2_start': self.new_before_high2_start_spin.value(),
            'new_before_high2_range': self.new_before_high2_range_spin.value(),
            'new_before_high2_span': self.new_before_high2_span_spin.value(),
            'new_before_high2_logic': self.new_before_high2_logic_combo.currentText(),
            # 新增：创后新高1相关参数
            'new_after_high_start': self.new_after_high_start_spin.value(),
            'new_after_high_range': self.new_after_high_range_spin.value(),
            'new_after_high_span': self.new_after_high_span_spin.value(),
            'new_after_high_logic': self.new_after_high_logic_combo.currentText(),
            # 新增：创后新高2相关参数
            'new_after_high2_start': self.new_after_high2_start_spin.value(),
            'new_after_high2_range': self.new_after_high2_range_spin.value(),
            'new_after_high2_span': self.new_after_high2_span_spin.value(),
            'new_after_high2_logic': self.new_after_high2_logic_combo.currentText(),
            # 新增：创前新低1相关参数
            'new_before_low_start': self.new_before_low_start_spin.value(),
            'new_before_low_range': self.new_before_low_range_spin.value(),
            'new_before_low_span': self.new_before_low_span_spin.value(),
            'new_before_low_logic': self.new_before_low_logic_combo.currentText(),
            # 新增：创前新低2相关参数
            'new_before_low2_start': self.new_before_low2_start_spin.value(),
            'new_before_low2_range': self.new_before_low2_range_spin.value(),
            'new_before_low2_span': self.new_before_low2_span_spin.value(),
            'new_before_low2_logic': self.new_before_low2_logic_combo.currentText(),
            # 新增：创后新低1相关参数
            'new_after_low_start': self.new_after_low_start_spin.value(),
            'new_after_low_range': self.new_after_low_range_spin.value(),
            'new_after_low_span': self.new_after_low_span_spin.value(),
            'new_after_low_logic': self.new_after_low_logic_combo.currentText(),
            # 新增：创后新低2相关参数
            'new_after_low2_start': self.new_after_low2_start_spin.value(),
            'new_after_low2_range': self.new_after_low2_range_spin.value(),
            'new_after_low2_span': self.new_after_low2_span_spin.value(),
            'new_after_low2_logic': self.new_after_low2_logic_combo.currentText(),
            'new_before_high_flag': self.new_before_high_flag_checkbox.isChecked(),
            'new_before_high2_flag': self.new_before_high2_flag_checkbox.isChecked(),
            'new_after_high_flag': self.new_after_high_flag_checkbox.isChecked(),
            'new_after_high2_flag': self.new_after_high2_flag_checkbox.isChecked(),
            'new_before_low_flag': self.new_before_low_flag_checkbox.isChecked(),
            'new_before_low2_flag': self.new_before_low2_flag_checkbox.isChecked(),
            'new_after_low_flag': self.new_after_low_flag_checkbox.isChecked(),
            'new_after_low2_flag': self.new_after_low2_flag_checkbox.isChecked(),
            # 新增：组合分析界面勾选框状态
            'component_generate_trading_plan': getattr(self, 'last_component_generate_trading_plan', False),
            # 新增：组合分析次数
            'component_analysis_count': getattr(self, 'last_component_analysis_count', 1),
            # 新增：组合输出锁定状态
            'last_lock_output': getattr(self, 'last_lock_output', False),
            # 新增保存组合分析总耗时
            'last_component_total_elapsed_time': getattr(self, 'last_component_total_elapsed_time', None),
            # 新增保存组合分析组合次数
            'last_component_total_combinations': getattr(self, 'last_component_total_combinations', None),
            # 新增保存last_adjusted_value
            'last_adjusted_value': getattr(self, 'last_adjusted_value', None),
            # 新增：保存组合分析率值区间参数
            'component_hold_rate_min': getattr(self, 'last_component_hold_rate_min', 0),
            'component_hold_rate_max': getattr(self, 'last_component_hold_rate_max', 100),
            'component_profit_rate_min': getattr(self, 'last_component_profit_rate_min', 0),
            'component_profit_rate_max': getattr(self, 'last_component_profit_rate_max', 100),
            'component_loss_rate_min': getattr(self, 'last_component_loss_rate_min', 0),
            'component_loss_rate_max': getattr(self, 'last_component_loss_rate_max', 100),
            'component_only_better_trading_plan_percent': getattr(self, 'last_component_only_better_trading_plan_percent', 0.0),
            'component_comprehensive_daily_change_threshold': getattr(self, 'last_component_comprehensive_daily_change_threshold', 0.0),
            'component_comprehensive_stop_daily_change_threshold': getattr(self, 'last_component_comprehensive_stop_daily_change_threshold', 0.0),
            # 新增：保存组合分析总体结果
            'overall_stats': getattr(self, 'overall_stats', None),
        }
        # 保存公式选股控件状态
        if hasattr(self, 'formula_widget') and self.formula_widget is not None:
            try:
                config['formula_select_state'] = self.formula_widget.get_state()
            except Exception as e:
                print(f"保存公式选股控件状态失败: {e}")
        # 新增：保存forward_param_state
        config['forward_param_state'] = getattr(self, 'forward_param_state', {})
        # 保存组合分析结果
        if hasattr(self, 'component_widget') and hasattr(self.component_widget, 'get_cached_analysis_results'):
            import pickle, base64
            results = self.component_widget.get_cached_analysis_results()
            if results:
                config['component_analysis_results'] = base64.b64encode(pickle.dumps(results)).decode('utf-8')
        # 保存操盘方案列表
        if hasattr(self, 'trading_plan_list'):
            from ui.trading_plan_ui import TradingPlanWidget
            TradingPlanWidget.clean_plan_for_save(self.trading_plan_list)
            config['trading_plan_list'] = self.trading_plan_list
                    # 保存trading_plan_end_date
            if hasattr(self, 'last_trading_plan_end_date'):
                config['trading_plan_end_date'] = self.last_trading_plan_end_date
            elif hasattr(self, 'trading_plan_widget'):
                config['trading_plan_end_date'] = self.trading_plan_widget.end_date_picker.date().toString("yyyy-MM-dd")
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def load_config(self):
        if not os.path.exists('config.json'):
            return
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'width' in config:
                self.width_spin.setValue(config['width'])
            if 'start_option' in config:
                self.start_option_combo.setCurrentIndex(config['start_option'])
            if 'shift' in config:
                self.shift_spin.setValue(config['shift'])
            if 'inc_rate' in config:
                self.inc_rate_edit.setText(config['inc_rate'])
            if 'op_days' in config:
                self.op_days_edit.setText(config['op_days'])
            if 'after_gt_end_ratio' in config:
                self.after_gt_end_edit.setText(config['after_gt_end_ratio'])
            if 'after_gt_start_ratio' in config:
                self.after_gt_prev_edit.setText(config['after_gt_start_ratio'])
            if 'stop_loss_inc_rate' in config:
                self.stop_loss_inc_rate_edit.setText(config['stop_loss_inc_rate'])
            if 'stop_loss_after_gt_end_ratio' in config:
                self.stop_loss_after_gt_end_edit.setText(config['stop_loss_after_gt_end_ratio'])
            if 'stop_loss_after_gt_start_ratio' in config:
                self.stop_loss_after_gt_start_edit.setText(config['stop_loss_after_gt_start_ratio'])
            if 'n_days' in config:
                self.n_days_spin.setValue(config['n_days'])
            if 'n_days_max' in config:
                self.n_days_max_spin.setValue(config['n_days_max'])
            if 'range_value' in config:
                self.range_value_edit.setText(config['range_value'])
            if 'continuous_abs_threshold' in config:
                self.continuous_abs_threshold_edit.setText(config['continuous_abs_threshold'])
            if 'ops_change' in config:
                self.ops_change_edit.setText(config['ops_change'])
            if 'expr' in config:
                self.last_expr = config['expr']
            if 'last_formula_expr' in config:
                self.last_formula_expr = config['last_formula_expr']
            if 'last_select_count' in config:
                self.last_select_count = config['last_select_count']
            if 'last_sort_mode' in config:
                self.last_sort_mode = config['last_sort_mode']
            if 'last_profit_type' in config:
                self.last_profit_type = config['last_profit_type']
            if 'last_loss_type' in config:
                self.last_loss_type = config['last_loss_type']
            if 'direction' in config:
                self.direction_checkbox.setChecked(config['direction'])
            # 加载组合分析子界面的日期配置
            if 'component_analysis_start_date' in config:
                self.last_component_analysis_start_date = config['component_analysis_start_date']
            if 'component_analysis_end_date' in config:
                self.last_component_analysis_end_date = config['component_analysis_end_date']
            # 恢复CPU核心数
            if 'cpu_cores' in config:
                self.cpu_spin.setValue(config['cpu_cores'])
            # 恢复公式选股控件状态
            if 'formula_select_state' in config and hasattr(self, 'formula_widget') and self.formula_widget is not None:
                try:
                    self.formula_widget.set_state(config['formula_select_state'])
                except Exception as e:
                    print(f"恢复公式选股控件状态失败: {e}")
            # 恢复 last_formula_select_state
            if 'last_formula_select_state' in config:
                self.last_formula_select_state = config['last_formula_select_state']
            # 恢复自动分析缓存
            if 'analysis_table_cache_data' in config:
                self.analysis_table_cache_data = config['analysis_table_cache_data']
            # 恢复表格数据
            if 'cached_table_data' in config:
                self.cached_table_data = config['cached_table_data']
            # 恢复交易方式
            if 'trade_mode' in config:
                index = self.trade_mode_combo.findText(config['trade_mode'])
                if index >= 0:
                    self.trade_mode_combo.setCurrentIndex(index)
            # 新增：恢复创新高/创新低相关SpinBox控件
            if 'new_before_high_start' in config:
                self.new_before_high_start_spin.setValue(config['new_before_high_start'])
            if 'new_before_high_range' in config:
                self.new_before_high_range_spin.setValue(config['new_before_high_range'])
            if 'new_before_high_span' in config:
                self.new_before_high_span_spin.setValue(config['new_before_high_span'])
            if 'valid_abs_sum_threshold' in config:
                self.valid_abs_sum_threshold_edit.setText(config['valid_abs_sum_threshold'])
            if 'new_before_high_logic' in config:
                self.new_before_high_logic_combo.setCurrentText(config['new_before_high_logic'])
            # 新增：恢复创前新低1相关参数
            if 'new_before_low_start' in config:
                self.new_before_low_start_spin.setValue(config['new_before_low_start'])
            if 'new_before_low_range' in config:
                self.new_before_low_range_spin.setValue(config['new_before_low_range'])
            if 'new_before_low_span' in config:
                self.new_before_low_span_spin.setValue(config['new_before_low_span'])
            if 'new_before_low_logic' in config:
                self.new_before_low_logic_combo.setCurrentText(config['new_before_low_logic'])
            # 新增：恢复创前新高2相关参数
            if 'new_before_high2_start' in config:
                self.new_before_high2_start_spin.setValue(config['new_before_high2_start'])
            if 'new_before_high2_range' in config:
                self.new_before_high2_range_spin.setValue(config['new_before_high2_range'])
            if 'new_before_high2_span' in config:
                self.new_before_high2_span_spin.setValue(config['new_before_high2_span'])
            if 'new_before_high2_logic' in config:
                self.new_before_high2_logic_combo.setCurrentText(config['new_before_high2_logic'])
            # 新增：恢复创后新高1相关参数
            if 'new_after_high_start' in config:
                self.new_after_high_start_spin.setValue(config['new_after_high_start'])
            if 'new_after_high_range' in config:
                self.new_after_high_range_spin.setValue(config['new_after_high_range'])
            if 'new_after_high_span' in config:
                self.new_after_high_span_spin.setValue(config['new_after_high_span'])
            if 'new_after_high_logic' in config:
                self.new_after_high_logic_combo.setCurrentText(config['new_after_high_logic'])
            # 新增：恢复创后新高2相关参数
            if 'new_after_high2_start' in config:
                self.new_after_high2_start_spin.setValue(config['new_after_high2_start'])
            if 'new_after_high2_range' in config:
                self.new_after_high2_range_spin.setValue(config['new_after_high2_range'])
            if 'new_after_high2_span' in config:
                self.new_after_high2_span_spin.setValue(config['new_after_high2_span'])
            if 'new_after_high2_logic' in config:
                self.new_after_high2_logic_combo.setCurrentText(config['new_after_high2_logic'])
            # 新增：恢复创前新低2相关参数
            if 'new_before_low2_start' in config:
                self.new_before_low2_start_spin.setValue(config['new_before_low2_start'])
            if 'new_before_low2_range' in config:
                self.new_before_low2_range_spin.setValue(config['new_before_low2_range'])
            if 'new_before_low2_span' in config:
                self.new_before_low2_span_spin.setValue(config['new_before_low2_span'])
            if 'new_before_low2_logic' in config:
                self.new_before_low2_logic_combo.setCurrentText(config['new_before_low2_logic'])
            # 新增：恢复创后新低1相关参数
            if 'new_after_low_start' in config:
                self.new_after_low_start_spin.setValue(config['new_after_low_start'])
            if 'new_after_low_range' in config:
                self.new_after_low_range_spin.setValue(config['new_after_low_range'])
            if 'new_after_low_span' in config:
                self.new_after_low_span_spin.setValue(config['new_after_low_span'])
            if 'new_after_low_logic' in config:
                self.new_after_low_logic_combo.setCurrentText(config['new_after_low_logic'])
            # 新增：恢复创后新低2相关参数
            if 'new_after_low2_start' in config:
                self.new_after_low2_start_spin.setValue(config['new_after_low2_start'])
            if 'new_after_low2_range' in config:
                self.new_after_low2_range_spin.setValue(config['new_after_low2_range'])
            if 'new_after_low2_span' in config:
                self.new_after_low2_span_spin.setValue(config['new_after_low2_span'])
            if 'new_after_low2_logic' in config:
                self.new_after_low2_logic_combo.setCurrentText(config['new_after_low2_logic'])
            self.new_before_high_flag_checkbox.setChecked(config.get('new_before_high_flag', False))
            self.new_before_high2_flag_checkbox.setChecked(config.get('new_before_high2_flag', False))
            self.new_after_high_flag_checkbox.setChecked(config.get('new_after_high_flag', False))
            self.new_after_high2_flag_checkbox.setChecked(config.get('new_after_high2_flag', False))
            self.new_before_low_flag_checkbox.setChecked(config.get('new_before_low_flag', False))
            self.new_before_low2_flag_checkbox.setChecked(config.get('new_before_low2_flag', False))
            self.new_after_low_flag_checkbox.setChecked(config.get('new_after_low_flag', False))
            self.new_after_low2_flag_checkbox.setChecked(config.get('new_after_low2_flag', False))
            # 新增：恢复forward_param_state
            if 'forward_param_state' in config:
                self.forward_param_state = config['forward_param_state']
            else:
                self.forward_param_state = {}
            # 恢复组合分析结果
            if 'component_analysis_results' in config:
                import pickle, base64
                try:
                    results = pickle.loads(base64.b64decode(config['component_analysis_results']))
                    if hasattr(self, 'component_widget') and hasattr(self.component_widget, 'set_cached_analysis_results'):
                        self.component_widget.set_cached_analysis_results(results)
                    else:
                        self._pending_component_analysis_results = results
                except Exception as e:
                    print(f'恢复组合分析结果失败: {e}')
            # 恢复操盘方案列表
            if 'trading_plan_list' in config:
                self.trading_plan_list = config['trading_plan_list']
            if 'component_generate_trading_plan' in config:
                self.last_component_generate_trading_plan = config['component_generate_trading_plan']
            # 恢复trading_plan_end_date
            if 'trading_plan_end_date' in config:
                self.last_trading_plan_end_date = config['trading_plan_end_date']
            # 新增：恢复组合输出锁定状态
            if 'last_lock_output' in config:
                self.last_lock_output = config['last_lock_output']
            # 恢复组合分析总耗时
            if 'last_component_total_elapsed_time' in config:
                self.last_component_total_elapsed_time = config['last_component_total_elapsed_time']
            # 新增：恢复组合分析组合次数
            if 'last_component_total_combinations' in config:
                self.last_component_total_combinations = config['last_component_total_combinations']
            # 新增：恢复last_adjusted_value
            if 'last_adjusted_value' in config:
                self.last_adjusted_value = config['last_adjusted_value']
            # 恢复组合分析次数
            if 'component_analysis_count' in config:
                self.last_component_analysis_count = config['component_analysis_count']
            # 新增：恢复组合分析率值区间参数
            if 'component_hold_rate_min' in config:
                self.last_component_hold_rate_min = config['component_hold_rate_min']
            if 'component_hold_rate_max' in config:
                self.last_component_hold_rate_max = config['component_hold_rate_max']
            if 'component_profit_rate_min' in config:
                self.last_component_profit_rate_min = config['component_profit_rate_min']
            if 'component_profit_rate_max' in config:
                self.last_component_profit_rate_max = config['component_profit_rate_max']
            if 'component_loss_rate_min' in config:
                self.last_component_loss_rate_min = config['component_loss_rate_min']
            if 'component_loss_rate_max' in config:
                self.last_component_loss_rate_max = config['component_loss_rate_max']
            if 'component_only_better_trading_plan_percent' in config:
                self.last_component_only_better_trading_plan_percent = config['component_only_better_trading_plan_percent']
            # 新增：恢复综合止盈止损和停盈停损阈值
            if 'component_comprehensive_daily_change_threshold' in config:
                self.last_component_comprehensive_daily_change_threshold = config['component_comprehensive_daily_change_threshold']
            if 'component_comprehensive_stop_daily_change_threshold' in config:
                self.last_component_comprehensive_stop_daily_change_threshold = config['component_comprehensive_stop_daily_change_threshold']
            # 新增：恢复组合分析总体结果
            if 'overall_stats' in config:
                self.overall_stats = config['overall_stats']
        except Exception as e:
            print(f"加载配置失败: {e}")

    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)

    def _fix_date_range(self):
        # 自动修正日期到workdays范围
        if not hasattr(self.init, 'workdays_str') or not self.init.workdays_str:
            return
        min_date = QDate.fromString(self.init.workdays_str[0], "yyyy-MM-dd")
        max_date = QDate.fromString(self.init.workdays_str[-1], "yyyy-MM-dd")
        cur_date = self.date_picker.date()
        if cur_date < min_date:
            self.date_picker.setDate(min_date)
        elif cur_date > max_date:
            self.date_picker.setDate(max_date)

    def show_trading_plan_interface(self):
        """显示操盘方案界面"""
        from ui.trading_plan_ui import TradingPlanWidget
        trading_plan_widget = TradingPlanWidget(self)
        trading_plan_widget.setMinimumSize(1200, 600)
        self.trading_plan_widget = trading_plan_widget
        self.table_widget = trading_plan_widget
        self.output_stack.addWidget(trading_plan_widget)
        self.output_stack.setCurrentWidget(trading_plan_widget)

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
        if not hasattr(self, 'last_formula_select_state') or not self.last_formula_select_state:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
        # 获取当前选中的变量
        from function.stock_functions import get_abbr_round_only_map
        abbr_round_only_map = get_abbr_round_only_map()
        
        # 检查选中的变量属于哪个类别
        selected_vars = []
        for (zh, en), en_val in abbr_round_only_map.items():
            if en_val in self.last_formula_select_state:
                var_state = self.last_formula_select_state[en_val]
                if var_state.get('round_checked', False):  # 检查圆框是否勾选
                    selected_vars.append((zh, en_val))
        
        if not selected_vars:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
        # 根据选中的变量确定类别
        category = None
        for zh, en_val in selected_vars:
            if "停盈停损" in zh:
                category = "停盈停损"
                break
            elif "停盈止损" in zh:
                category = "停盈止损"
                break
            elif "止盈止损" in zh:
                category = "止盈止损"
                break
            elif "止盈停损" in zh:
                category = "止盈停损"
                break
        
        if not category:
            return default_profit_text, default_loss_text, default_profit_median_text, default_loss_median_text
        
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