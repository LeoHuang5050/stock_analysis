import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDateEdit, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QLineEdit, QDialog, QMessageBox, QFrame, QStackedLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QDate, QItemSelectionModel
from PyQt5.QtGui import QKeySequence, QGuiApplication, QIntValidator, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler
from function.stock_functions import show_continuous_sum_table, EXPR_PLACEHOLDER_TEXT, calculate_analysis_result
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

class CopyableTableWidget(QTableWidget):
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copySelection()
        else:
            super().keyPressEvent(event)

    def copySelection(self):
        selection = self.selectedRanges()
        if not selection:
            return
        s = ""
        for r in selection:
            for row in range(r.topRow(), r.bottomRow() + 1):
                row_data = []
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.item(row, col)
                    row_data.append(item.text() if item else "")
                s += "\t".join(row_data) + "\n"
        QGuiApplication.clipboard().setText(s.strip())

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

        # 递增率
        self.inc_rate_label = QLabel("递增率")
        self.inc_rate_edit = QLineEdit()
        self.inc_rate_edit.setFixedWidth(30)
        self.inc_rate_unit = QLabel("%")
        inc_rate_widget = QWidget()
        inc_rate_layout = QHBoxLayout()
        inc_rate_layout.setContentsMargins(0, 0, 0, 0)
        inc_rate_layout.setSpacing(0)
        inc_rate_layout.setAlignment(Qt.AlignLeft)
        inc_rate_layout.addWidget(QLabel("递增率"))
        inc_rate_layout.addWidget(self.inc_rate_edit)
        inc_rate_layout.addWidget(QLabel("%"))
        inc_rate_widget.setLayout(inc_rate_layout)
        inc_rate_widget.setMaximumWidth(80)

        # 后值大于结束值比例
        self.after_gt_end_label = QLabel("后值大于结束值比例")
        self.after_gt_end_edit = QLineEdit()
        self.after_gt_end_edit.setFixedWidth(30)
        self.after_gt_end_unit = QLabel("%")
        after_gt_end_widget = QWidget()
        after_gt_end_layout = QHBoxLayout()
        after_gt_end_layout.setContentsMargins(0, 0, 0, 0)
        after_gt_end_layout.setSpacing(0)
        after_gt_end_layout.setAlignment(Qt.AlignLeft)
        after_gt_end_layout.addWidget(QLabel("后值大于结束值比例"))
        after_gt_end_layout.addWidget(self.after_gt_end_edit)
        after_gt_end_layout.addWidget(QLabel("%"))
        after_gt_end_widget.setLayout(after_gt_end_layout)
        after_gt_end_widget.setMaximumWidth(150)

        # 后值大于前值比例
        self.after_gt_start_label = QLabel("后值大于前值比例")
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
        after_gt_prev_widget.setMaximumWidth(130)

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

        # 操作值
        # expr_widget = QWidget()
        # expr_layout = QHBoxLayout()
        # expr_layout.setContentsMargins(0, 0, 0, 0)
        # expr_layout.setSpacing(0)
        # expr_layout.setAlignment(Qt.AlignLeft)
        # expr_layout.addWidget(QLabel("操作值"))
        # self.expr_edit = ValidatedExprEdit()
        # self.expr_edit.setPlainText(
        #     "if INC != 0:\n"
        #     "    result = INC\n"
        #     "else:\n"
        #     "    result = 0\n"
        # )
        # self.expr_edit.setMinimumHeight(25)
        # self.expr_edit.setMaximumHeight(120)
        # def adjust_expr_edit_height():
        #     doc = self.expr_edit.document()
        #     line_count = doc.blockCount()
        #     font_metrics = self.expr_edit.fontMetrics()
        #     height = font_metrics.lineSpacing() * line_count + 12
        #     height = max(25, min(height, 120))
        #     self.expr_edit.setFixedHeight(height)
        # self.expr_edit.textChanged.connect(adjust_expr_edit_height)
        # adjust_expr_edit_height()  # 初始化高度
        # expr_layout.addWidget(self.expr_edit)
        # expr_widget.setLayout(expr_layout)
        
        # 控件位置布局
        top_grid.addWidget(self.n_days_label1, 1, 0)
        top_grid.addWidget(self.n_days_spin, 1, 1)

        top_grid.addWidget(self.n_days_label2, 1, 2)
        top_grid.addWidget(self.n_days_max_spin, 1, 3)

        top_grid.addWidget(op_days_widget, 1, 4)
        top_grid.addWidget(inc_rate_widget, 1, 5)
        top_grid.addWidget(after_gt_end_widget, 1, 6)
        top_grid.addWidget(after_gt_prev_widget, 1, 7)
        # top_grid.addWidget(expr_widget, 1, 8)
        top_grid.addWidget(ops_change_widget, 1, 8)
        top_grid.addWidget(self.valid_abs_sum_label, 1, 9)
        top_grid.addWidget(self.valid_abs_sum_threshold_edit, 1, 10)
        top_grid.addWidget(cpu_widget, 1, 11)  # 添加CPU核心数控件

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

        # 第三行：创前新高1和创前新低相关控件
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
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.continuous_sum_btn)
        btn_layout.addWidget(self.param_show_btn)
        btn_layout.addWidget(self.formula_select_btn)
        btn_layout.addWidget(self.auto_analysis_btn)
        btn_layout.addWidget(self.op_stat_btn)
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

    def get_or_calculate_result(self, formula_expr=None, select_count=None, sort_mode=None, show_main_output=True, only_show_selected=None, is_auto_analysis=False, end_date_start=None, end_date_end=None):
        # 直接在此处校验创新高/创新低日期范围
        workdays = getattr(self.init, 'workdays_str', None)
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
        params['width'] = self.width_spin.value()
        params['start_option'] = self.start_option_combo.currentText()
        params['shift_days'] = self.shift_spin.value()
        params['is_forward'] = self.direction_checkbox.isChecked()
        params['n_days'] = self.n_days_spin.value()
        params['n_days_max'] = self.n_days_max_spin.value()
        params['range_value'] = self.range_value_edit.text()
        params['continuous_abs_threshold'] = self.continuous_abs_threshold_edit.text()
        params['op_days'] = self.op_days_edit.text()
        params['inc_rate'] = self.inc_rate_edit.text()
        params['after_gt_end_ratio'] = self.after_gt_end_edit.text()
        params['after_gt_start_ratio'] = self.after_gt_prev_edit.text()
        params['trade_mode'] = self.trade_mode_combo.currentText()
        # 选股公式、数量、排序方式参数
        params['expr'] = self.last_expr  # 新增：操作值表达式
        params['select_count'] = select_count if select_count is not None else 10
        params['sort_mode'] = sort_mode if sort_mode is not None else "最大值排序"
        params['ops_change'] = self.ops_change_edit.text()
        # 选股计算公式
        params['formula_expr'] = current_formula
        # 新增：创新高/创新低相关SpinBox参数
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
        result = self.base_param.on_calculate_clicked(params)
        if result is None:
            if show_main_output:
                self.result_text.setText("请先上传数据文件！")
                self.output_stack.setCurrentWidget(self.result_text)
            self.last_end_date = end_date
            self.last_formula_expr = current_formula
            self.last_calculate_result = None
            return None
        self.last_end_date = end_date
        self.last_formula_expr = current_formula
        self.last_calculate_result = result
        return self.last_calculate_result

    def create_analysis_table(self, valid_items, start_date, end_date):
        formula = getattr(self, 'last_formula_expr', '')
        if formula is None:
            formula = ''
        formula = formula.strip()
        row_count = len(valid_items)
        table = CopyableTableWidget(row_count + 2, 9, self.analysis_widget)  # 9列
        table.setHorizontalHeaderLabels([
            "结束日期", "操作天数", "持有涨跌幅", "日均涨跌幅", "从下往上非空均值", "从下往上含空均值", "含空值均值", "最大值", "最小值"
        ])
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 使用新的分析结果计算函数
        result = calculate_analysis_result(valid_items)
        
        # 设置第一行的均值数据
        summary = result['summary']
        table.setItem(0, 1, QTableWidgetItem(str(summary['mean_hold_days'])))
        table.setItem(0, 2, QTableWidgetItem(f"{summary['mean_ops_change']}%" if summary['mean_ops_change'] != '' else ''))
        table.setItem(0, 3, QTableWidgetItem(f"{summary['mean_daily_change']}%" if summary['mean_daily_change'] != '' else ''))
        table.setItem(0, 4, QTableWidgetItem(f"{summary['mean_non_nan']}%" if summary['mean_non_nan'] != '' else ''))
        table.setItem(0, 5, QTableWidgetItem(f"{summary['mean_with_nan']}%" if summary['mean_with_nan'] != '' else ''))
        table.setItem(0, 6, QTableWidgetItem(f"{summary['mean_daily_with_nan']}%" if summary['mean_daily_with_nan'] != '' else ''))
        table.setItem(0, 7, QTableWidgetItem(f"{summary['max_change']}%" if summary['max_change'] != '' else ''))
        table.setItem(0, 8, QTableWidgetItem(f"{summary['min_change']}%" if summary['min_change'] != '' else ''))

        # 设置每行的数据
        for row_idx, item in enumerate(result['items']):
            table.setItem(row_idx + 2, 0, QTableWidgetItem(item['date']))
            table.setItem(row_idx + 2, 1, QTableWidgetItem(str(item['hold_days'])))
            table.setItem(row_idx + 2, 2, QTableWidgetItem(f"{item['ops_change']}%" if item['ops_change'] != '' else ''))
            table.setItem(row_idx + 2, 3, QTableWidgetItem(f"{item['daily_change']}%" if item['daily_change'] != '' else ''))
            table.setItem(row_idx + 2, 4, QTableWidgetItem(f"{round(item['non_nan_mean'],2)}%" if not math.isnan(item['non_nan_mean']) else ''))
            table.setItem(row_idx + 2, 5, QTableWidgetItem(f"{round(item['with_nan_mean'],2)}%" if not math.isnan(item['with_nan_mean']) else ''))

        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")

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
            ("递增率", f"{self.inc_rate_edit.text()}%"),
            ("后值大于结束值比例", f"{self.after_gt_end_edit.text()}%"),
            ("后值大于前值比例", f"{self.after_gt_prev_edit.text()}%"),
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
        result = self.get_or_calculate_result(
            formula_expr=formula, 
            show_main_output=False, 
            only_show_selected=True, 
            is_auto_analysis=True,
            select_count=select_count,
            sort_mode=sort_mode,
            end_date_start=start_date,
            end_date_end=end_date
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
        # 保存表格数据
        self.cached_table_data = {
            "headers": [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())],
            "data": [[table.item(i, j).text() if table.item(i, j) else "" for j in range(table.columnCount())] for i in range(table.rowCount())],
            "formula": formula
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
        # 使用保存的日期值或默认值
        if hasattr(self, 'last_analysis_start_date'):
            self.start_date_picker.setDate(QDate.fromString(self.last_analysis_start_date, "yyyy-MM-dd"))
            print(f"获取到了 last_analysis_start_date: {self.last_analysis_start_date}")
        else:
            print("没有获取到 last_analysis_start_date")
            self.start_date_picker.setDate(self.date_picker.date())
        self.end_date_label = QLabel("结束日期结束日:")
        self.end_date_picker = QDateEdit(calendarPopup=True)
        # 使用保存的日期值或默认值
        if hasattr(self, 'last_analysis_end_date'):
            print(f"获取到了 last_analysis_end_date: {self.last_analysis_end_date}")
            self.end_date_picker.setDate(QDate.fromString(self.last_analysis_end_date, "yyyy-MM-dd"))
        else:
            print("没有获取到 last_analysis_end_date")
            self.end_date_picker.setDate(self.date_picker.date())
        # 绑定信号，变更时同步变量
        self.start_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
        self.end_date_picker.dateChanged.connect(self._on_analysis_date_changed_save)
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
                    if i == len(data) - 9 and j == 0 and cell.startswith("选股公式"):
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
            self.analysis_result_layout.addWidget(table)
        else:
            self.analysis_result_layout.addWidget(self.analysis_result_text)

    def _on_analysis_date_changed_save(self):
        self.last_analysis_start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        self.last_analysis_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")

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
        if '选股公式' in df.columns:
            formula = df['选股公式'].iloc[-1]
            df = df.iloc[:-1]
        elif df.shape[0] > 0 and str(df.iloc[-9, 0]).startswith('选股公式'):
            formula = str(df.iloc[-9, 0]).replace('选股公式:', '').strip()
            # 取倒数第8行到倒数第1行（参数信息）
            param_rows = df.iloc[-8:]
            for _, row in param_rows.iterrows():
                if isinstance(row[0], str) and row[0] in [
                    "日期宽度", "开始日期值选择", "前移天数", "操作天数", 
                    "递增率", "后值大于结束值比例", "后值大于前值比例", "操作涨幅"
                ]:
                    params[row[0]] = row[1]
            df = df.iloc[:-9]

        # 恢复参数到控件（用导入文件中的值）
        param_map = {
            "日期宽度": (self.width_spin, int),
            "开始日期值选择": (self.start_option_combo, str),
            "前移天数": (self.shift_spin, int),
            "操作天数": (self.op_days_edit, str),
            "递增率": (self.inc_rate_edit, lambda v: v.replace('%','')),
            "后值大于结束值比例": (self.after_gt_end_edit, lambda v: v.replace('%','')),
            "后值大于前值比例": (self.after_gt_prev_edit, lambda v: v.replace('%','')),
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

        # 只保留"结束日期"非NaN的有效数据行
        valid_items = []
        columns = [str(col) for col in df.columns]
        for i in range(df.shape[0]):
            date_key = str(df.iloc[i, 0])
            if pd.isna(df.iloc[i, 0]) or str(df.iloc[i, 0]).lower() == 'nan':
                continue
            stock = {}
            for j, col in enumerate(columns):
                stock[col] = df.iloc[i, j]
            valid_items.append((date_key, [stock]))
        # start_date和end_date取有效数据行
        dates = [k for k, v in valid_items]
        self.analysis_table_cache_data = {
            "valid_items": valid_items,
            "start_date": dates[0] if dates else '',
            "end_date": dates[-1] if dates else ''
        }
        # 更新公式和控件状态
        if formula:
            self.last_formula_expr = formula
            from function.stock_functions import parse_formula_to_config
            config = parse_formula_to_config(formula)
            self.last_formula_select_state = config
        # 刷新表格展示（直接打印df内容，nan值置空，公式跨行）
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        row_count = df.shape[0]
        col_count = df.shape[1]
        extra_row = 1 if formula else 0
        table = QTableWidget(row_count + extra_row, col_count, self.analysis_widget)
        table.setHorizontalHeaderLabels([str(col) for col in df.columns])
        for i in range(row_count):
            for j in range(col_count):
                val = df.iat[i, j]
                # nan值置空
                if pd.isna(val) or str(val).lower() == 'nan':
                    val = ''
                table.setItem(i, j, QTableWidgetItem(str(val)))

        # 在公式行后添加参数行
        params = [
            ("日期宽度", str(self.width_spin.value())),
            ("开始日期值选择", self.start_option_combo.currentText()),
            ("前移天数", str(self.shift_spin.value())),
            ("操作天数", self.op_days_edit.text()),
            ("递增率", f"{self.inc_rate_edit.text()}%"),
            ("后值大于结束值比例", f"{self.after_gt_end_edit.text()}%"),
            ("后值大于前值比例", f"{self.after_gt_prev_edit.text()}%"),
            ("操作涨幅", f"{self.ops_change_edit.text()}%")
        ]
        for i, (label, value) in enumerate(params):
            table.insertRow(row_count + 1 + i)
            table.setItem(row_count + 1 + i, 0, QTableWidgetItem(label))
            table.setItem(row_count + 1 + i, 1, QTableWidgetItem(value))        
        # 公式行
        if formula:
            from PyQt5.QtCore import Qt
            item = QTableWidgetItem(f"选股公式:\n{formula}")
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            item.setToolTip(item.text())
            table.setItem(row_count, 0, item)
            table.setSpan(row_count, 0, 1, col_count)
            table.setWordWrap(True)
            table.resizeRowToContents(row_count)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 150)
                
        self.analysis_result_layout.addWidget(table)
        # 保存表格数据
        self.cached_table_data = {
            "headers": [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())],
            "data": [[table.item(i, j).text() if table.item(i, j) else "" for j in range(table.columnCount())] for i in range(table.rowCount())],
            "formula": formula
        }

    def save_config(self):
        config = {
            'date': self.date_picker.date().toString("yyyy-MM-dd"),
            'width': self.width_spin.value(),
            'start_option': self.start_option_combo.currentIndex(),
            'shift': self.shift_spin.value(),
            'inc_rate': self.inc_rate_edit.text(),
            'op_days': self.op_days_edit.text(),
            'after_gt_end_ratio': self.after_gt_end_edit.text(),
            'after_gt_start_ratio': self.after_gt_prev_edit.text(),
            'n_days': self.n_days_spin.value(),
            'n_days_max': self.n_days_max_spin.value(),
            'range_value': self.range_value_edit.text(),
            'continuous_abs_threshold': self.continuous_abs_threshold_edit.text(),
            'ops_change': self.ops_change_edit.text(),
            'expr': getattr(self, 'last_expr', ''),  # 新增：操作值表达式
            'last_formula_expr': getattr(self, 'last_formula_expr', ''),
            'last_select_count': getattr(self, 'last_select_count', 10),
            'last_sort_mode': getattr(self, 'last_sort_mode', '最大值排序'),
            'direction': self.direction_checkbox.isChecked(),
            'analysis_start_date': getattr(self, 'last_analysis_start_date', ''),
            'analysis_end_date': getattr(self, 'last_analysis_end_date', ''),
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
        }
        # 保存公式选股控件状态
        if hasattr(self, 'formula_widget') and self.formula_widget is not None:
            try:
                config['formula_select_state'] = self.formula_widget.get_state()
            except Exception as e:
                print(f"保存公式选股控件状态失败: {e}")
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
            if 'date' in config:
                self.date_picker.blockSignals(True)
                self.date_picker.setDate(QDate.fromString(config['date'], "yyyy-MM-dd"))
                self.date_picker.blockSignals(False)
                self.pending_date = config['date']  # 依然保留，等workdays加载后再做一次校验
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
            if 'direction' in config:
                self.direction_checkbox.setChecked(config['direction'])
            # 加载自动分析子界面的日期配置
            if 'analysis_start_date' in config:
                self.last_analysis_start_date = config['analysis_start_date']
            if 'analysis_end_date' in config:
                self.last_analysis_end_date = config['analysis_end_date']
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