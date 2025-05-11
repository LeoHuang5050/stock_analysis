import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QComboBox, QSpinBox, QTextEdit, QMessageBox, QDateEdit, QCheckBox, QLineEdit, QSizePolicy, QGridLayout, QHBoxLayout
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
        # self.confirm_btn = QPushButton("1. 确认区间")
        # self.confirm_btn.setMinimumWidth(col_widths[6])
        # grid.addWidget(self.confirm_btn, 0, 6)

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
        self.start_option_combo.addItems(["最大值", "最小值", "接近值", "开始值"])
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
        self.calc_btn = QPushButton("2. 生成基础参数")
        self.calc_btn.setMinimumWidth(col_widths[7])
        grid.addWidget(self.calc_btn, 1, 7)

        # 第三行（前1组结束地址前 + SpinBox + 日最大值 合并为一列）
        n_days_widget = QWidget()
        n_days_layout = QHBoxLayout()
        n_days_layout.setContentsMargins(0, 0, 0, 0)
        n_days_layout.setSpacing(5)
        self.n_days_label1 = QLabel("前1组结束地址前")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(1)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(5)
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
        self.abs_sum_value_edit = QLineEdit()
        self.abs_sum_value_edit.setMinimumWidth(col_widths[5])
        grid.addWidget(self.abs_sum_value_edit, 2, 5)
        # self.extend_btn = QPushButton("3. 生成扩展参数")
        # self.extend_btn.setMinimumWidth(col_widths[6])
        # grid.addWidget(self.extend_btn, 2, 6)

        # 第三行最右侧放生成扩展参数按钮
        self.extend_btn = QPushButton("3. 生成扩展参数")
        self.extend_btn.setMinimumWidth(col_widths[7])
        grid.addWidget(self.extend_btn, 2, 7)

        # 结果文本框（跨8列）
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(300)
        grid.addWidget(self.result_text, 3, 0, 1, 8)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        self.start_option_combo.currentIndexChanged.connect(self.init.on_start_option_changed)
        self.confirm_btn.clicked.connect(self.base_param.update_shift_spin_range)
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)