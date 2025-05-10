import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QComboBox, QSpinBox, QTextEdit, QMessageBox, QDateEdit, QHBoxLayout, QCheckBox
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
        self.resize(600, 500)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # 先初始化业务逻辑
        self.init = StockAnalysisInit(self)
        self.base_param = BaseParamHandler(self)
        
        # 再初始化UI组件
        self.init_ui()
        
        # 最后连接信号
        self.connect_signals()

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
        self.confirm_btn = QPushButton("确认区间")
        self.confirm_btn.clicked.connect(self.init.on_confirm_range)
        top_layout.addWidget(self.confirm_btn, alignment=Qt.AlignLeft)
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

        self.calc_btn = QPushButton("生成基础参数")
        self.calc_btn.clicked.connect(self.base_param.on_calculate_clicked)
        second_layout.addWidget(self.calc_btn, alignment=Qt.AlignLeft)

        self.layout.addLayout(second_layout)

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