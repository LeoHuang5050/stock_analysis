import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDateEdit, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QLineEdit, QDialog, QMessageBox, QFrame, QStackedLayout, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QDate, QItemSelectionModel
from PyQt5.QtGui import QKeySequence, QGuiApplication, QIntValidator
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler
from function.stock_functions import show_continuous_sum_table, EXPR_PLACEHOLDER_TEXT
import gc
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
import math
import json
import os

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

class StockAnalysisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        self.init_ui()
        self.connect_signals()
        # 默认最大化显示
        self.showMaximized()
        # 统一缓存变量
        self.last_end_date = None
        self.last_calculate_result = None
        self.last_formula_expr = None
        # 加载参数
        self.load_config()

    def init_ui(self):
        # 设置窗口标题
        self.setWindowTitle("股票分析工具")
        # 移除固定大小设置
        # self.setFixedSize(1200, 800)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # 顶部参数输入区
        top_widget = QWidget()
        top_grid = QGridLayout(top_widget)
        top_grid.setHorizontalSpacing(20)
        top_widget.setLayout(top_grid)
        col_widths = [170, 170, 170, 170, 170, 170]

        # 第一行控件
        self.label = QLabel("请上传数据文件：")
        self.upload_btn = QPushButton("上传数据文件")
        self.date_label = QLabel("请选择结束日期：")
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setDisplayFormat("yyyy/M/d")

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
        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        self.continuous_abs_threshold_edit = QLineEdit()

        # 第一行全部控件
        top_grid.addWidget(self.label, 0, 0)
        top_grid.addWidget(self.upload_btn, 0, 1)
        top_grid.addWidget(self.date_label, 0, 2)
        top_grid.addWidget(self.date_picker, 0, 3)
        top_grid.addWidget(width_widget, 0, 4)
        top_grid.addWidget(start_option_widget, 0, 5)
        top_grid.addWidget(shift_widget, 0, 6)
        top_grid.addWidget(self.direction_checkbox, 0, 7)
        top_grid.addWidget(self.range_label, 0, 8)
        top_grid.addWidget(self.range_value_edit, 0, 9)
        top_grid.addWidget(self.abs_sum_label, 0, 10)
        top_grid.addWidget(self.continuous_abs_threshold_edit, 0, 11)

        # 第二行
        # 新增"前1组结束地址前N日最大值"
        self.n_days_label1 = QLabel("前N日最大值")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(0)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(0)

        self.n_days_label2 = QLabel("前1组结束地址前N日最大值")
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
        expr_widget = QWidget()
        expr_layout = QHBoxLayout()
        expr_layout.setContentsMargins(0, 0, 0, 0)
        expr_layout.setSpacing(0)
        expr_layout.setAlignment(Qt.AlignLeft)
        expr_layout.addWidget(QLabel("操作值"))
        self.expr_edit = QTextEdit()
        self.expr_edit.setPlainText(
            "if INC != 0:\n"
            "    result = INC\n"
            "else:\n"
            "    result = 0\n"
        )
        self.expr_edit.setMinimumHeight(25)
        self.expr_edit.setMaximumHeight(120)
        def adjust_expr_edit_height():
            doc = self.expr_edit.document()
            line_count = doc.blockCount()
            font_metrics = self.expr_edit.fontMetrics()
            height = font_metrics.lineSpacing() * line_count + 12
            height = max(25, min(height, 120))
            self.expr_edit.setFixedHeight(height)
        self.expr_edit.textChanged.connect(adjust_expr_edit_height)
        adjust_expr_edit_height()  # 初始化高度
        expr_layout.addWidget(self.expr_edit)
        expr_widget.setLayout(expr_layout)
        
        # 控件位置布局
        top_grid.addWidget(self.n_days_label1, 1, 0)
        top_grid.addWidget(self.n_days_spin, 1, 1)

        top_grid.addWidget(self.n_days_label2, 1, 2)
        top_grid.addWidget(self.n_days_max_spin, 1, 3)

        top_grid.addWidget(op_days_widget, 1, 4)
        top_grid.addWidget(inc_rate_widget, 1, 5)
        top_grid.addWidget(after_gt_end_widget, 1, 6)
        top_grid.addWidget(after_gt_prev_widget, 1, 7)
        top_grid.addWidget(expr_widget, 1, 8)
        top_grid.addWidget(ops_change_widget, 1, 9)

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
            self.expr_edit, self.n_days_spin, self.n_days_max_spin, self.width_spin, self.shift_spin, self.start_option_combo
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
            formula_input = None
            for child in table.findChildren((QWidget,)):
                if child.__class__.__name__ == 'FormulaExprEdit':
                    formula_input = child
                    break
            if formula_input and hasattr(self, 'last_formula_expr') and self.last_formula_expr:
                formula_input.setText(self.last_formula_expr)
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

    def get_or_calculate_result(self, formula_expr=None, select_count=None, sort_mode=None, show_main_output=True, only_show_selected=None, is_auto_analysis=False):
        end_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_formula = formula_expr if formula_expr is not None else (
            self.formula_expr_edit.toPlainText() if hasattr(self, 'formula_expr_edit') else ''
        )
        # 每次都强制重新计算
        # 收集所有参数
        params = {}
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
        # 选股公式、数量、排序方式参数
        params['expr'] = self.expr_edit.toPlainText()
        params['select_count'] = select_count if select_count is not None else 10
        params['sort_mode'] = sort_mode if sort_mode is not None else "最大值排序"
        params['ops_change'] = self.ops_change_edit.text()
        # 选股计算公式
        params['formula_expr'] = current_formula
        # 获取end_date_start和end_date_end
        if is_auto_analysis and hasattr(self, 'start_date_picker') and hasattr(self, 'end_date_picker'):
            params['end_date_start'] = self.start_date_picker.date().toString("yyyy-MM-dd")
            params['end_date_end'] = self.end_date_picker.date().toString("yyyy-MM-dd")
        else:
            params['end_date_start'] = end_date
            params['end_date_end'] = end_date
        if only_show_selected is not None:
            params['only_show_selected'] = only_show_selected
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
        row_count = len(valid_items)
        table = CopyableTableWidget(row_count, 6, self.analysis_widget)
        table.setHorizontalHeaderLabels([
            "结束日期开始日", "结束日期结束日", "结束日期", "操作天数", "持有涨跌幅", "日均涨跌幅"
        ])
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        def safe_val(val):
            if val is None:
                return ''
            if isinstance(val, float) and math.isnan(val):
                return ''
            if isinstance(val, str) and val.strip().lower().startswith('nan'):
                return ''
            return val
        mean_hold_days_list = []
        mean_ops_change_list = []
        mean_incre_rate_list = []
        for row_idx, (date_key, stocks) in enumerate(valid_items):
            if row_idx == 0:
                table.setItem(row_idx, 0, QTableWidgetItem(start_date))
                table.setItem(row_idx, 1, QTableWidgetItem(end_date))
            else:
                table.setItem(row_idx, 0, QTableWidgetItem(""))
                table.setItem(row_idx, 1, QTableWidgetItem(""))
            table.setItem(row_idx, 2, QTableWidgetItem(date_key))
            hold_days_list = []
            ops_change_list = []
            ops_incre_rate_list = []
            for stock in stocks:
                try:
                    v = safe_val(stock.get('hold_days', ''))
                    if v != '':
                        v = float(v)
                        if not math.isnan(v):
                            hold_days_list.append(v)
                except Exception:
                    pass
                try:
                    v = safe_val(stock.get('ops_change', ''))
                    if v != '':
                        v = float(v)
                        if not math.isnan(v):
                            ops_change_list.append(v)
                except Exception:
                    pass
                try:
                    v = safe_val(stock.get('ops_incre_rate', ''))
                    if v != '':
                        v = float(v)
                        if not math.isnan(v):
                            ops_incre_rate_list.append(v)
                except Exception:
                    pass
            def safe_mean(lst):
                return round(sum(lst) / len(lst), 2) if lst else ''
            mean_hold_days = safe_mean(hold_days_list)
            mean_ops_change = safe_mean(ops_change_list)
            mean_ops_incre_rate = safe_mean(ops_incre_rate_list)
            min_incre_rate = ''
            if mean_hold_days and mean_hold_days != 0 and mean_ops_change != '':
                calc1 = mean_ops_incre_rate if mean_ops_incre_rate != '' else float('inf')
                calc2 = mean_ops_change / mean_hold_days if mean_hold_days != 0 else float('inf')
                min_incre_rate = round(min(calc1, calc2), 2)
            table.setItem(row_idx, 3, QTableWidgetItem(str(mean_hold_days)))
            table.setItem(row_idx, 4, QTableWidgetItem(f"{mean_ops_change}%" if mean_ops_change != '' else ''))
            table.setItem(row_idx, 5, QTableWidgetItem(f"{min_incre_rate}%" if min_incre_rate != '' else ''))
            if mean_hold_days != '':
                mean_hold_days_list.append(mean_hold_days)
            if mean_ops_change != '':
                mean_ops_change_list.append(mean_ops_change)
            if min_incre_rate != '':
                mean_incre_rate_list.append(min_incre_rate)
        def safe_mean2(lst):
            return round(sum(lst) / len(lst), 2) if lst else ''
        mean_of_mean_hold_days = safe_mean2(mean_hold_days_list)
        mean_of_mean_ops_change = safe_mean2(mean_ops_change_list)
        mean_of_mean_incre_rate = safe_mean2(mean_incre_rate_list)
        last_row = table.rowCount()
        table.insertRow(last_row)
        table.insertRow(last_row+1)
        table.setItem(last_row+1, 3, QTableWidgetItem(str(mean_of_mean_hold_days)))
        table.setItem(last_row+1, 4, QTableWidgetItem(f"{mean_of_mean_ops_change}%" if mean_of_mean_ops_change != '' else ''))
        table.setItem(last_row+1, 5, QTableWidgetItem(f"{mean_of_mean_incre_rate}%" if mean_of_mean_incre_rate != '' else ''))
        table.resizeColumnsToContents()
        table.horizontalHeader().setFixedHeight(40)
        table.horizontalHeader().setStyleSheet("font-size: 12px;")
        return table

    def on_generate_analysis(self):
        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
        formula = getattr(self, 'last_formula_expr', '')
        if formula is None:
            formula = ''
        formula = formula.strip()
        if not formula:
            self.analysis_result_text.setText("请先设置选股公式")
            return
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
        # 获取选股数量和排序方式
        select_count = getattr(self, 'last_select_count', 10)
        sort_mode = getattr(self, 'last_sort_mode', '最大值排序')
        print(f"select_count: {select_count}, sort_mode: {sort_mode}")
        result = self.get_or_calculate_result(
            formula_expr=formula, 
            show_main_output=False, 
            only_show_selected=True, 
            is_auto_analysis=True,
            select_count=select_count,
            sort_mode=sort_mode
        )
        merged_results = result.get('dates', {}) if result else {}
        valid_items = [(date_key, stocks) for date_key, stocks in merged_results.items() if stocks]
        # 缓存数据
        self.analysis_table_cache_data = {
            "valid_items": valid_items,
            "start_date": start_date,
            "end_date": end_date
        }
        # 清理旧内容并显示新表格
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        table = self.create_analysis_table(valid_items, start_date, end_date)
        self.analysis_result_layout.addWidget(table)

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
        self.generate_btn = QPushButton("点击生成")
        self.generate_btn.clicked.connect(self.on_generate_analysis)
        row_layout.addWidget(self.start_date_label)
        row_layout.addWidget(self.start_date_picker)
        row_layout.addWidget(self.end_date_label)
        row_layout.addWidget(self.end_date_picker)
        row_layout.addWidget(self.generate_btn)
        row_layout.addWidget(self.export_excel_btn)
        row_layout.addWidget(self.export_csv_btn)
    
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
        # 绑定信号，双向限制日期选择
        self.width_spin.valueChanged.connect(self.on_analysis_date_changed)
        self.on_analysis_date_changed()
        # 切换到自动分析tab
        self.output_stack.setCurrentWidget(self.analysis_widget)
        # 清理内容区
        for i in reversed(range(self.analysis_result_layout.count())):
            widget = self.analysis_result_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
        # 展示缓存表格
        if hasattr(self, 'analysis_table_cache_data') and self.analysis_table_cache_data is not None:
            data = self.analysis_table_cache_data
            table = self.create_analysis_table(data["valid_items"], data["start_date"], data["end_date"])
            self.analysis_result_layout.addWidget(table)
        else:
            self.analysis_result_layout.addWidget(self.analysis_result_text)

    def _on_analysis_date_changed_save(self):
        self.last_analysis_start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        self.last_analysis_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")

    def on_analysis_date_changed(self):
        if not hasattr(self, 'end_date_picker') or self.end_date_picker is None:
            return
        if not hasattr(self, 'start_date_picker') or self.start_date_picker is None:
            return
        workdays = getattr(self.init, 'workdays_str', None)
        if not workdays:
            return
        width = self.width_spin.value()
        start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        # 1. 结束日结束日的可选范围：start_date ~ workdays[-1]
        if start_date in workdays:
            min_end_idx = workdays.index(start_date)
        else:
            min_end_idx = 0
        max_end_idx = len(workdays) - 1
        min_end_date = QDate.fromString(workdays[min_end_idx], "yyyy-MM-dd")
        max_end_date = QDate.fromString(workdays[max_end_idx], "yyyy-MM-dd")
        self.end_date_picker.setMinimumDate(min_end_date)
        self.end_date_picker.setMaximumDate(max_end_date)
        
        # 2. 结束日开始日的可选范围：max(0, end_idx-width) ~ end_idx
        min_start_idx = max(0, width)
        max_start_idx = max_end_idx
        min_start_date = QDate.fromString(workdays[min_start_idx], "yyyy-MM-dd")
        max_start_date = QDate.fromString(workdays[max_start_idx], "yyyy-MM-dd")
        self.start_date_picker.setMinimumDate(min_start_date)
        self.start_date_picker.setMaximumDate(max_start_date)

    def on_op_stat_btn_clicked(self):
        self.clear_result_area()
        try:
            end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
            start_date = self.start_date_picker.date().toString("yyyy-MM-dd")
        except (AttributeError, RuntimeError):
            self.result_text.setText("请先在自动分析子界面设置结束日期开始日和结束日期结束日")
            self.output_stack.setCurrentWidget(self.result_text)
            return
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
        # 获取自动分析的result
        result = self.last_calculate_result
        merged_results = result.get('dates', {}) if result else {}
        group_size = 19
        end_dates = [d for d, stocks in merged_results.items() if stocks]
        blocks = [end_dates[i:i+group_size] for i in range(0, len(end_dates), group_size)]
        block_max_counts = [max((len(merged_results[d]) for d in block), default=0) for block in blocks]
        # 修正：多分配一块的最大行数，彻底避免最后一块丢行
        total_rows = sum([n+1 for n in block_max_counts]) + (max(block_max_counts) if block_max_counts else 0)
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
            row_offset += max_count + 2
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
            'expr': self.expr_edit.toPlainText(),
            'last_formula_expr': getattr(self, 'last_formula_expr', ''),
            'last_select_count': getattr(self, 'last_select_count', 10),
            'last_sort_mode': getattr(self, 'last_sort_mode', '最大值排序'),
            'direction': self.direction_checkbox.isChecked(),
            # 添加自动分析子界面的日期配置
            'analysis_start_date': getattr(self, 'start_date_picker', self.date_picker).date().toString("yyyy-MM-dd"),
            'analysis_end_date': getattr(self, 'end_date_picker', self.date_picker).date().toString("yyyy-MM-dd"),
        }
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
                self.expr_edit.setText(config['expr'])
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
        except Exception as e:
            print(f"加载配置失败: {e}")

    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)