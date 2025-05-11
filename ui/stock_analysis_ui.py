import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QComboBox, QSpinBox, QTextEdit, QMessageBox, QDateEdit, QHBoxLayout, QCheckBox, QLineEdit, QSizePolicy
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
from function.extend_param import ExtendParamHandler

class StockAnalysisApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analysis")
        self.resize(600, 500)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 先初始化业务逻辑
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        self.extend_param = ExtendParamHandler(self)
        
        # 再初始化UI组件
        self.init_ui()
        
        # 最后连接信号
        self.connect_signals()

        self.max_value = None  # 用于存储基础参数最大值
        self.n_max_value = None  # 用于存储前N日最大值

    def init_ui(self):
        # 第一行：文件上传、结束日期、日期宽度
        top_layout = QHBoxLayout()
        self.label = QLabel("请上传数据文件：")
        top_layout.addWidget(self.label, alignment=Qt.AlignLeft)
        self.upload_btn = QPushButton("上传数据文件")
        top_layout.addWidget(self.upload_btn, alignment=Qt.AlignLeft)
        self.date_label = QLabel("请选择结束日期：")
        top_layout.addWidget(self.date_label, alignment=Qt.AlignLeft)
        self.date_picker = QDateEdit(calendarPopup=True)
        self.date_picker.setDisplayFormat("yyyy-MM-dd")
        self.date_picker.setMinimumWidth(120)
        top_layout.addWidget(self.date_picker, alignment=Qt.AlignLeft)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.width_label = QLabel("请选择日期宽度：")
        top_layout.addWidget(self.width_label, alignment=Qt.AlignLeft)
        self.width_spin = QSpinBox()
        self.width_spin.setMinimum(1)
        self.width_spin.setMaximum(100)
        self.width_spin.setValue(5)
        self.width_spin.setMinimumWidth(60)
        top_layout.addWidget(self.width_spin, alignment=Qt.AlignLeft)
        # 添加弹性空间，让按钮靠右
        top_layout.addStretch()
        self.confirm_btn = QPushButton("1. 确认区间")
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        top_layout.addWidget(self.confirm_btn, alignment=Qt.AlignRight)
        self.layout.addLayout(top_layout)

        # 第二行：选择日期、开始日期值选择、前移天数、是否计算向前向后
        second_layout = QHBoxLayout()

        self.target_date_label = QLabel("选择日期：")
        self.target_date_combo = QComboBox()
        self.target_date_combo.setMinimumWidth(150)
        second_layout.addWidget(self.target_date_label, alignment=Qt.AlignLeft)
        second_layout.addWidget(self.target_date_combo, alignment=Qt.AlignLeft)

        self.start_option_label = QLabel("开始日期值选择：")
        second_layout.addWidget(self.start_option_label, alignment=Qt.AlignLeft)
        self.start_option_combo = QComboBox()
        self.start_option_combo.addItems(["最大值", "最小值", "接近值", "开始值"])
        self.start_option_combo.setMinimumWidth(80)
        second_layout.addWidget(self.start_option_combo, alignment=Qt.AlignLeft)

        self.shift_label = QLabel("前移天数：")
        second_layout.addWidget(self.shift_label, alignment=Qt.AlignLeft)
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(-100)
        self.shift_spin.setMaximum(100)
        self.shift_spin.setValue(0)
        self.shift_spin.setMinimumWidth(60)
        second_layout.addWidget(self.shift_spin, alignment=Qt.AlignLeft)

        self.direction_checkbox = QCheckBox("是否计算向前向后")
        second_layout.addWidget(self.direction_checkbox, alignment=Qt.AlignLeft)
        # 添加弹性空间，让按钮靠右
        second_layout.addStretch()
        self.calc_btn = QPushButton("2. 生成基础参数")
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)
        second_layout.addWidget(self.calc_btn, alignment=Qt.AlignRight)
        self.layout.addLayout(second_layout)

        # 添加第三行：前N日最大值设置和扩展参数按钮
        third_layout = QHBoxLayout()
        third_layout.setContentsMargins(0, 0, 0, 0)
        third_layout.setSpacing(10)

        # 左侧控件布局
        left_layout = QHBoxLayout()
        left_layout.setSpacing(10)

        self.n_days_label1 = QLabel("前1组结束地址前")
        left_layout.addWidget(self.n_days_label1)

        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(1)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(5)
        self.n_days_spin.setMinimumWidth(40)
        self.n_days_spin.setMaximumWidth(80)
        self.n_days_spin.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        left_layout.addWidget(self.n_days_spin)

        self.n_days_label2 = QLabel("日最大值：")
        left_layout.addWidget(self.n_days_label2)

        left_layout.addSpacing(20)

        self.range_label = QLabel("开始日到结束日之间最高价/最低价小于")
        left_layout.addWidget(self.range_label)

        self.range_value_edit = QLineEdit()
        self.range_value_edit.setMinimumWidth(60)
        self.range_value_edit.setMaximumWidth(100)
        self.range_value_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        left_layout.addWidget(self.range_value_edit)

        left_layout.addSpacing(20)

        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        left_layout.addWidget(self.abs_sum_label)

        self.abs_sum_value_edit = QLineEdit()
        self.abs_sum_value_edit.setMinimumWidth(60)
        self.abs_sum_value_edit.setMaximumWidth(100)
        self.abs_sum_value_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        left_layout.addWidget(self.abs_sum_value_edit)

        # 左侧布局加入第三行主布局
        third_layout.addLayout(left_layout)
        third_layout.addStretch()  # 推动右侧按钮到最右

        # 右侧按钮
        self.extend_btn = QPushButton("3. 生成扩展参数")
        self.extend_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        third_layout.addWidget(self.extend_btn)

        self.layout.addLayout(third_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        self.start_option_combo.currentIndexChanged.connect(self.init.on_start_option_changed)
        self.confirm_btn.clicked.connect(self.base_param.update_shift_spin_range)
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)
        self.extend_btn.clicked.connect(self.extend_param.on_extend_clicked)