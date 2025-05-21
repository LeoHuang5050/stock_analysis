import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QComboBox, QSpinBox, QTextEdit, QMessageBox, QDateEdit, QCheckBox, QLineEdit, QSizePolicy, QGridLayout, QHBoxLayout, QDialog, QVBoxLayout
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from datetime import datetime

# 导入function文件夹下的方法
import sys as _sys
import os as _os
_sys.path.append(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))
from function.stock_functions import unify_date_columns, calc_continuous_sum_np, get_workdays
import chinese_calendar

# 导入worker_threads文件夹下的方法
from worker_threads import FileLoaderThread, CalculateThread

# 导入init文件夹下的方法
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler

class StockAnalysisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analysis")
        self.resize(1700, 1050)
        # 不要在这里 setLayout

        # 先初始化业务逻辑
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        
        # 再初始化UI组件
        self.init_ui()
        
        # 最后连接信号
        self.connect_signals()

        self.max_value = None  # 用于存储基础参数最大值
        self.n_max_value = None  # 用于存储前N日最大值

    def init_ui(self):
        # 统一每一列的宽度（可根据实际内容调整）
        col_widths = [170, 170, 170, 170, 170, 170, 170, 170]
        grid = QGridLayout()
        self.setLayout(grid)

        # 第一行
        self.label = QLabel("请上传数据文件：")
        self.label.setMinimumWidth(col_widths[0])
        grid.addWidget(self.label, 0, 0)
        self.upload_btn = QPushButton("上传数据文件")
        self.upload_btn.setMinimumWidth(col_widths[1])
        grid.addWidget(self.upload_btn, 0, 1)
        self.date_label = QLabel("请选择结束日期：")
        self.date_label.setMinimumWidth(col_widths[2])
        grid.addWidget(self.date_label, 0, 2)
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setMinimumWidth(col_widths[3])
        grid.addWidget(self.date_picker, 0, 3)
        self.width_label = QLabel("请选择日期宽度：")
        self.width_label.setMinimumWidth(col_widths[4])
        grid.addWidget(self.width_label, 0, 4)
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(100)
        self.width_spin.setValue(5)
        self.width_spin.setMinimumWidth(col_widths[5])
        grid.addWidget(self.width_spin, 0, 5)
        # 第一行最右侧放确认区间按钮
        self.confirm_btn = QPushButton("1. 确认区间")
        self.confirm_btn.setMinimumWidth(col_widths[7])
        grid.addWidget(self.confirm_btn, 0, 7)

        # 第二行
        self.target_date_label = QLabel("选择日期(选择接近值使用)：")
        self.target_date_label.setMinimumWidth(col_widths[0])
        grid.addWidget(self.target_date_label, 1, 0)
        self.target_date_combo = QComboBox()
        self.target_date_combo.setMinimumWidth(col_widths[1])
        grid.addWidget(self.target_date_combo, 1, 1)
        self.start_option_label = QLabel("开始日期值选择：")
        self.start_option_label.setMinimumWidth(col_widths[2])
        grid.addWidget(self.start_option_label, 1, 2)
        self.start_option_combo = QComboBox()
        self.start_option_combo.addItems(["开始值", "最大值", "最小值", "接近值"])
        self.start_option_combo.setMinimumWidth(col_widths[3])
        grid.addWidget(self.start_option_combo, 1, 3)
        self.shift_label = QLabel("前移天数：")
        self.shift_label.setMinimumWidth(col_widths[4])
        grid.addWidget(self.shift_label, 1, 4)
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(-100)
        self.shift_spin.setMaximum(100)
        self.shift_spin.setValue(0)
        self.shift_spin.setMinimumWidth(col_widths[5])
        grid.addWidget(self.shift_spin, 1, 5)
        self.direction_checkbox = QCheckBox("是否计算向前向后")
        self.direction_checkbox.setMinimumWidth(col_widths[6])
        grid.addWidget(self.direction_checkbox, 1, 6)

        # 第三行（前1组结束地址前 + SpinBox + 日最大值 合并为一列）
        n_days_widget = QWidget()
        n_days_layout = QHBoxLayout()
        n_days_layout.setContentsMargins(0, 0, 0, 0)
        n_days_layout.setSpacing(5)
        self.n_days_label1 = QLabel("前1组结束地址前")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(0)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(0)
        self.n_days_label2 = QLabel("日最大值")
        n_days_layout.addWidget(self.n_days_label1)
        n_days_layout.addWidget(self.n_days_spin)
        n_days_layout.addWidget(self.n_days_label2)
        n_days_widget.setLayout(n_days_layout)
        grid.addWidget(n_days_widget, 2, 0, 1, 2)  # 跨2列

        # 其余控件顺次往后排
        self.range_label = QLabel("开始日到结束日之间最高价/最低价小于")
        self.range_label.setMinimumWidth(col_widths[2])
        grid.addWidget(self.range_label, 2, 2)
        self.range_value_edit = QLineEdit()
        self.range_value_edit.setMinimumWidth(col_widths[3])
        grid.addWidget(self.range_value_edit, 2, 3)
        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        self.abs_sum_label.setMinimumWidth(col_widths[4])
        grid.addWidget(self.abs_sum_label, 2, 4)
        self.continuous_abs_threshold_edit = QLineEdit()
        self.continuous_abs_threshold_edit.setMinimumWidth(col_widths[5])
        grid.addWidget(self.continuous_abs_threshold_edit, 2, 5)

        # 第四行：参数查询（合并为一组，放最右侧一列）
        query_widget = QWidget()
        query_layout = QHBoxLayout()
        query_layout.setContentsMargins(0, 0, 0, 0)
        query_layout.setSpacing(5)

        # 在第四行第一列添加操作参数标签
        self.op_param_label = QLabel("操作参数：")
        self.op_param_label.setMinimumWidth(col_widths[0])
        grid.addWidget(self.op_param_label, 3, 0)
        
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("根据代码/名称查询")
        self.query_input.setMinimumWidth(col_widths[1])
        self.query_btn = QPushButton("股票参数信息")
        self.query_btn.setMinimumWidth(col_widths[2])
        query_layout.addWidget(self.query_input)
        query_layout.addWidget(self.query_btn)
        query_widget.setLayout(query_layout)

        # 第四行：操作天数、递增率、后值大于结束值比例、后值大于前值比例
        op_days_layout = QHBoxLayout()
        op_days_layout.setContentsMargins(0, 0, 0, 0)
        op_days_layout.setSpacing(0)
        self.op_days_label = QLabel("操作天数")
        self.op_days_edit = QLineEdit()
        self.op_days_edit.setFixedWidth(40)
        self.op_days_edit.setAlignment(Qt.AlignLeft)
        self.op_days_placeholder = QLabel("")  # 占位，保证和其它组对齐
        op_days_layout.addWidget(self.op_days_label)
        op_days_layout.addWidget(self.op_days_edit)
        op_days_layout.addWidget(self.op_days_placeholder)
        op_days_widget = QWidget()
        op_days_widget.setLayout(op_days_layout)

        # 递增率组
        inc_rate_layout = QHBoxLayout()
        inc_rate_layout.setContentsMargins(0, 0, 0, 0)
        inc_rate_layout.setSpacing(0)
        self.inc_rate_label = QLabel("递增率")
        self.inc_rate_edit = QLineEdit()
        self.inc_rate_edit.setFixedWidth(40)
        self.inc_rate_edit.setAlignment(Qt.AlignLeft)
        self.inc_rate_percent = QLabel("%")
        inc_rate_layout.addWidget(self.inc_rate_label)
        inc_rate_layout.addWidget(self.inc_rate_edit)
        inc_rate_layout.addWidget(self.inc_rate_percent)
        inc_rate_widget = QWidget()
        inc_rate_widget.setLayout(inc_rate_layout)

        # 后值大于结束值比例组
        after_gt_end_layout = QHBoxLayout()
        after_gt_end_layout.setContentsMargins(0, 0, 0, 0)
        after_gt_end_layout.setSpacing(0)
        self.after_gt_end_label = QLabel("后值大于结束值比例")
        self.after_gt_end_edit = QLineEdit()
        self.after_gt_end_edit.setFixedWidth(40)
        self.after_gt_end_edit.setAlignment(Qt.AlignLeft)
        self.after_gt_end_percent = QLabel("%")
        after_gt_end_layout.addWidget(self.after_gt_end_label)
        after_gt_end_layout.addWidget(self.after_gt_end_edit)
        after_gt_end_layout.addWidget(self.after_gt_end_percent)
        after_gt_end_widget = QWidget()
        after_gt_end_widget.setLayout(after_gt_end_layout)

        # 后值大于前值比例组
        after_gt_start_layout = QHBoxLayout()
        after_gt_start_layout.setContentsMargins(0, 0, 0, 0)
        after_gt_start_layout.setSpacing(0)
        self.after_gt_start_label = QLabel("后值大于前值比例")
        self.after_gt_start_edit = QLineEdit()
        self.after_gt_start_edit.setFixedWidth(40)
        self.after_gt_start_edit.setAlignment(Qt.AlignLeft)
        self.after_gt_start_percent = QLabel("%")
        after_gt_start_layout.addWidget(self.after_gt_start_label)
        after_gt_start_layout.addWidget(self.after_gt_start_edit)
        after_gt_start_layout.addWidget(self.after_gt_start_percent)
        after_gt_start_widget = QWidget()
        after_gt_start_widget.setLayout(after_gt_start_layout)

        # 操作值+查询区组合
        expr_and_query_layout = QHBoxLayout()
        expr_and_query_layout.setContentsMargins(0, 0, 0, 0)
        expr_and_query_layout.setSpacing(10)
        self.expr_label = QLabel("操作值")
        self.expr_edit_brief = QLineEdit()
        self.expr_edit_brief.setPlaceholderText("点击输入/编辑组合表达式")
        self.expr_edit_brief.setReadOnly(True)
        self.expr_edit_brief.setFixedWidth(250)
        expr_and_query_layout.addWidget(self.expr_label)
        expr_and_query_layout.addWidget(self.expr_edit_brief)
        expr_and_query_layout.addStretch()
        expr_and_query_layout.addWidget(query_widget)
        expr_and_query_widget = QWidget()
        expr_and_query_widget.setLayout(expr_and_query_layout)

        # 总体横向布局
        op_row_layout = QHBoxLayout()
        op_row_layout.setContentsMargins(0, 0, 0, 0)
        op_row_layout.setSpacing(20)
        op_row_layout.addWidget(op_days_widget)
        op_row_layout.addWidget(inc_rate_widget)
        op_row_layout.addWidget(after_gt_end_widget)
        op_row_layout.addWidget(after_gt_start_widget)
        op_row_layout.addWidget(expr_and_query_widget)

        op_row_widget = QWidget()
        op_row_widget.setLayout(op_row_layout)
        grid.addWidget(op_row_widget, 4, 0, 1, 8)  # 跨8列

        # 结果文本框（跨8列）
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        grid.addWidget(self.result_text, 5, 0, 1, 8)

        # 第六行
        self.calc_btn = QPushButton("2. 生成参数")  # 先创建按钮
        self.calc_btn.setMinimumWidth(170)        # 你可以用col_widths[7]更美观
        calc_btn_row = QWidget()
        calc_btn_layout = QHBoxLayout()
        calc_btn_layout.addStretch()
        calc_btn_layout.addWidget(self.calc_btn)
        calc_btn_row.setLayout(calc_btn_layout)
        grid.addWidget(calc_btn_row, 5, 0, 1, 8)  # 跨8列

        # 设置标签左对齐
        self.op_days_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.inc_rate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.after_gt_end_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.after_gt_start_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.expr_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        self.start_option_combo.currentIndexChanged.connect(self.init.on_start_option_changed)
        self.confirm_btn.clicked.connect(self.base_param.update_shift_spin_range)
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)

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

    # def on_calculate_clicked(self):
    #     # 在计算时
    #     A = ... # 递增率
    #     B = ... # 后值大于结束值比例
    #     C = ... # 后值大于前值比例
    #     expr = self.expr_edit_brief.text()
    #     # 用simpleeval或自定义安全eval执行
    #     from simpleeval import simple_eval
    #     result = simple_eval(expr, names={'A': A, 'B': B, 'C': C})
    #     self.result_text.setText(str(result))

    def open_expr_dialog(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑组合表达式")
        layout = QVBoxLayout(dialog)
        # 固定提示
        tip_label = QLabel("A:递增率，B:后值大于结束值比例，C:后值大于前值比例")
        tip_label.setStyleSheet("color:gray;")  # 灰色字体
        layout.addWidget(tip_label)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.expr_edit_brief.text())
        layout.addWidget(text_edit)
        btn_ok = QPushButton("确定")
        layout.addWidget(btn_ok)
        def on_ok():
            self.expr_edit_brief.setText(text_edit.toPlainText())
            dialog.accept()
        btn_ok.clicked.connect(on_ok)
        dialog.exec_()