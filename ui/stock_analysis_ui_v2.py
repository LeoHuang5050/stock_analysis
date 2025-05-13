import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDateEdit, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QLineEdit, QDialog
)
from PyQt5.QtCore import Qt
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler

class ExprLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑组合表达式")
        layout = QVBoxLayout(dialog)
        tip_label = QLabel("A:递增率，B:后值大于结束值比例，C:后值大于前值比例")
        tip_label.setStyleSheet("color:gray;")
        layout.addWidget(tip_label)
        text_edit = QTextEdit()
        text_edit.setPlainText(self.text())
        layout.addWidget(text_edit)
        btn_ok = QPushButton("确定")
        layout.addWidget(btn_ok)
        def on_ok():
            self.setText(text_edit.toPlainText())
            dialog.accept()
        btn_ok.clicked.connect(on_ok)
        dialog.exec_()

class StockAnalysisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analysis")
        self.resize(1700, 1050)
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # 顶部参数输入区
        top_widget = QWidget()
        top_grid = QGridLayout(top_widget)
        top_widget.setLayout(top_grid)
        col_widths = [170, 170, 170, 170, 170, 170]

        # 第一行控件（先创建，再addWidget）
        self.label = QLabel("请上传数据文件：")
        self.upload_btn = QPushButton("上传数据文件")
        self.date_label = QLabel("请选择结束日期：")
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.width_label = QLabel("请选择日期宽度：")
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(100)
        self.width_spin.setValue(0)
        self.confirm_btn = QPushButton("1. 确认区间")
        self.confirm_btn.setMinimumWidth(120)

        # 然后再addWidget
        top_grid.addWidget(self.label, 0, 0)
        top_grid.addWidget(self.upload_btn, 0, 1)
        top_grid.addWidget(self.date_label, 0, 2)
        top_grid.addWidget(self.date_picker, 0, 3)
        top_grid.addWidget(self.width_label, 0, 4)
        top_grid.addWidget(self.width_spin, 0, 5)
        top_grid.addWidget(self.confirm_btn, 0, 8)

        # 第二行（左侧参数）
        self.target_date_label = QLabel("选择日期(选择接近值使用)：")
        self.target_date_combo = QComboBox()
        self.start_option_label = QLabel("开始日期值选择：")
        self.start_option_combo = QComboBox()
        self.start_option_combo.addItems(["开始值", "最大值", "最小值", "接近值"])
        self.shift_label = QLabel("前移天数：")
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(-100)
        self.shift_spin.setMaximum(100)
        self.shift_spin.setValue(0)

        # 第二行（右侧按钮）
        self.calc_btn = QPushButton("2. 生成参数")
        self.calc_btn.setMinimumWidth(120)

        # 添加到顶部表格
        top_grid.addWidget(self.target_date_label, 1, 0)
        top_grid.addWidget(self.target_date_combo, 1, 1)
        top_grid.addWidget(self.start_option_label, 1, 2)
        top_grid.addWidget(self.start_option_combo, 1, 3)
        top_grid.addWidget(self.shift_label, 1, 4)
        top_grid.addWidget(self.shift_spin, 1, 5)
        top_grid.addWidget(self.calc_btn, 1, 8)

        # 第三行控件
        self.n_days_label1 = QLabel("前1组结束地址前N日最大值")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(0)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(0)
        self.range_label = QLabel("开始日到结束日之间最高价/最低价小于")
        self.range_value_edit = QLineEdit()
        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        self.abs_sum_value_edit = QLineEdit()

        # 添加到顶部表格
        top_grid.addWidget(self.n_days_label1, 2, 0)
        top_grid.addWidget(self.n_days_spin, 2, 1)
        top_grid.addWidget(self.range_label, 2, 2)
        top_grid.addWidget(self.range_value_edit, 2, 3)
        top_grid.addWidget(self.abs_sum_label, 2, 4)
        top_grid.addWidget(self.abs_sum_value_edit, 2, 5)

        # 第四行控件
        self.direction_checkbox = QCheckBox("是否计算向前向后")
        op_days_widget = QWidget()
        op_days_layout = QHBoxLayout()
        op_days_layout.setContentsMargins(0, 0, 0, 0)
        op_days_layout.setSpacing(5)
        op_days_layout.setAlignment(Qt.AlignLeft)
        self.op_days_label = QLabel("操作天数")
        self.op_days_edit = QLineEdit()
        self.op_days_edit.setFixedWidth(30)
        op_days_layout.addWidget(self.op_days_label)
        op_days_layout.addWidget(self.op_days_edit)
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

        # 操作值
        expr_widget = QWidget()
        expr_layout = QHBoxLayout()
        expr_layout.setContentsMargins(0, 0, 0, 0)
        expr_layout.setSpacing(0)
        expr_layout.setAlignment(Qt.AlignLeft)
        expr_layout.addWidget(QLabel("操作值"))
        self.expr_edit = ExprLineEdit()
        self.expr_edit.setPlaceholderText("点击输入/编辑组合表达式")
        expr_layout.addWidget(self.expr_edit)
        expr_widget.setLayout(expr_layout)

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
        # 添加到第四行右侧
        top_grid.addWidget(query_widget, 3, 8)

        # 添加到第四行
        top_grid.addWidget(self.direction_checkbox, 3, 0)
        top_grid.addWidget(op_days_widget, 3, 1)
        top_grid.addWidget(inc_rate_widget, 3, 2)
        top_grid.addWidget(after_gt_end_widget, 3, 3)
        top_grid.addWidget(after_gt_prev_widget, 3, 4)
        top_grid.addWidget(expr_widget, 3, 5)

        # 输出框
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 添加到主布局
        main_layout.addWidget(top_widget)
        main_layout.addWidget(self.result_text, stretch=1)

        # 设置左表格所有参数列都不拉伸
        for i in range(7):  # 假设有7列（0~6），如有更多请调整
            top_grid.setColumnStretch(i, 0)
        # 让第8列（右侧空白）拉伸
        top_grid.setColumnStretch(7, 1)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        self.confirm_btn.clicked.connect(self.base_param.update_shift_spin_range)
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)
        self.query_btn.clicked.connect(self.on_query_param)

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