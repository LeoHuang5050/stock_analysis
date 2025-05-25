import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QSpinBox, QDateEdit, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QTextEdit, QLineEdit, QDialog, QMessageBox, QFrame, QStackedLayout
)
from PyQt5.QtCore import Qt
from function.init import StockAnalysisInit
from function.base_param import BaseParamHandler
from function.stock_functions import show_continuous_sum_table
import gc
import numpy as np

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
            "A:递增值，B:后值大于结束地址值，C:后值大于前值返回值\n"
            "支持Python条件表达式，例如：\n"
            "if (A > 10) and (B < 10):\n"
            "    result = C\n"
            "else:\n"
            "    result = A"
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
                dialog.accept()
            except SyntaxError as e:
                QMessageBox.warning(dialog, "语法错误", f"表达式存在语法错误，请检查！\n\n{e}")
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
        # 统一缓存变量
        self.last_end_date = None
        self.last_calculate_result = None
        self.last_formula_expr = None

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # 顶部参数输入区
        top_widget = QWidget()
        top_grid = QGridLayout(top_widget)
        top_widget.setLayout(top_grid)
        col_widths = [170, 170, 170, 170, 170, 170]

        # 第一行控件
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

        top_grid.addWidget(self.label, 0, 0)
        top_grid.addWidget(self.upload_btn, 0, 1)
        top_grid.addWidget(self.date_label, 0, 2)
        top_grid.addWidget(self.date_picker, 0, 3)
        top_grid.addWidget(self.width_label, 0, 4)
        top_grid.addWidget(self.width_spin, 0, 5)
        top_grid.addWidget(self.confirm_btn, 0, 8)

        # 第二行
        self.start_option_label = QLabel("开始日期值选择：")
        self.start_option_combo = QComboBox()
        self.start_option_combo.addItems(["开始值", "最大值", "最小值", "接近值"])
        self.shift_label = QLabel("前移天数：")
        self.shift_spin = QSpinBox()
        self.shift_spin.setMinimum(-1)
        self.shift_spin.setMaximum(1)
        self.shift_spin.setValue(0)
        self.direction_checkbox = QCheckBox("是否计算向前")
        self.calc_btn = QPushButton("2. 生成参数")
        self.calc_btn.setMinimumWidth(120)

        # 新增"前1组结束地址前N日最大值"
        self.n_days_label2 = QLabel("前1组结束地址前N日最大值")
        self.n_days_max_spin = QSpinBox()
        self.n_days_max_spin.setMinimum(0)
        self.n_days_max_spin.setMaximum(100)
        self.n_days_max_spin.setValue(0)

        top_grid.addWidget(self.start_option_label, 1, 0)
        top_grid.addWidget(self.start_option_combo, 1, 1)
        top_grid.addWidget(self.shift_label, 1, 2)
        top_grid.addWidget(self.shift_spin, 1, 3)
        top_grid.addWidget(self.direction_checkbox, 1, 4)
        # 新增控件放在第二行第五列
        top_grid.addWidget(self.n_days_label2, 1, 5)
        top_grid.addWidget(self.n_days_max_spin, 1, 6)
        top_grid.addWidget(self.calc_btn, 3, 8)

        # 第三行控件
        self.n_days_label1 = QLabel("前N日最大值")
        self.n_days_spin = QSpinBox()
        self.n_days_spin.setMinimum(0)
        self.n_days_spin.setMaximum(100)
        self.n_days_spin.setValue(0)
        self.range_label = QLabel("开始日到结束日之间最高价/最低价小于")
        self.range_value_edit = QLineEdit()
        self.abs_sum_label = QLabel("开始日到结束日之间连续累加值绝对值小于")
        self.continuous_abs_threshold_edit = QLineEdit()
        

        top_grid.addWidget(self.n_days_label1, 2, 0)
        top_grid.addWidget(self.n_days_spin, 2, 1)
        top_grid.addWidget(self.range_label, 2, 2)
        top_grid.addWidget(self.range_value_edit, 2, 3)
        top_grid.addWidget(self.abs_sum_label, 2, 4)
        top_grid.addWidget(self.continuous_abs_threshold_edit, 2, 5)
        

        # 第四行控件
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

        # 操作涨幅
        self.ops_change_label = QLabel("操作涨幅")
        self.ops_change_edit = QLineEdit()
        self.ops_change_edit.setFixedWidth(60)
        ops_change_widget = QWidget()
        ops_change_layout = QHBoxLayout()
        ops_change_layout.setContentsMargins(0, 0, 0, 0)
        ops_change_layout.setSpacing(0)
        ops_change_layout.setAlignment(Qt.AlignLeft)
        ops_change_layout.addWidget(self.ops_change_label)
        ops_change_layout.addWidget(self.ops_change_edit)
        ops_change_layout.addWidget(QLabel("%"))
        ops_change_widget.setLayout(ops_change_layout)

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
        # top_grid.addWidget(query_widget, 3, 8)

        # 添加到第四行
        top_grid.addWidget(op_days_widget, 3, 0)
        top_grid.addWidget(inc_rate_widget, 3, 1)
        top_grid.addWidget(after_gt_end_widget, 3, 2)
        top_grid.addWidget(after_gt_prev_widget, 3, 3)
        top_grid.addWidget(expr_widget, 3, 4)
        top_grid.addWidget(ops_change_widget, 3, 5)

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
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.continuous_sum_btn)
        btn_layout.addWidget(self.param_show_btn)
        btn_layout.addWidget(self.formula_select_btn)
        btn_layout.addStretch()  # 按钮靠左
        main_layout.addLayout(btn_layout)

        # 设置左表格所有参数列都不拉伸
        for i in range(7):  # 假设有7列（0~6），如有更多请调整
            top_grid.setColumnStretch(i, 0)
        # 让第8列（右侧空白）拉伸
        top_grid.setColumnStretch(7, 1)

    def connect_signals(self):
        self.upload_btn.clicked.connect(self.init.upload_file)
        self.date_picker.dateChanged.connect(self.init.on_date_changed)
        self.confirm_btn.clicked.connect(self.on_confirm_range)
        self.calc_btn.clicked.connect(self.on_calculate_clicked)
        # self.query_btn.clicked.connect(self.on_query_param)
        self.continuous_sum_btn.clicked.connect(self.on_continuous_sum_btn_clicked)
        self.param_show_btn.clicked.connect(self.on_param_show_btn_clicked)
        self.formula_select_btn.clicked.connect(self.on_formula_select_clicked)

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
        self.on_continuous_sum_clicked()

    def on_continuous_sum_clicked(self):
        result = self.get_or_calculate_result()
        if result is None:
            return
        merged_results = result.get('dates', {})
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
        self.on_param_show_clicked()

    def on_param_show_clicked(self):
        result = self.get_or_calculate_result()
        if result is None:
            return
        merged_results = result.get('dates', {})
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
        if table:
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

    def on_calculate_clicked(self, formula_expr=None):
        # 释放上一次的结果，防止内存累加
        self.all_results = None
        try:
            del self.all_results
        except Exception:
            pass
        # 2. 强制垃圾回收
        gc.collect()
        # 4. 触发numpy的内存释放
        np.empty(0)
        self.clear_result_area()
        self.result_text.setText("正在生成参数，请稍候...")
        self.output_stack.setCurrentWidget(self.result_text)
        # 传递 n_days_max
        params = {}
        params['n_days_max'] = self.n_days_max_spin.value()
        user_expr = self.expr_edit.text().strip()
        params['expr'] = user_expr
        # 其它参数收集（如有）
        # ... 你原有的参数收集逻辑 ...
        if formula_expr is not None:
            params['formula_expr'] = formula_expr
        self.base_param.on_calculate_clicked(params)

    def on_confirm_range(self):
        self.clear_result_area()
        self.result_text.setText("区间已确认，请继续设置参数...")
        self.output_stack.setCurrentWidget(self.result_text)
        self.init.on_confirm_range()

    def get_or_calculate_result(self, formula_expr=None, select_count=None, sort_mode=None, show_main_output=True, only_show_selected=None):
        end_date = self.date_picker.date().toString("yyyy-MM-dd")
        current_formula = formula_expr if formula_expr is not None else self.expr_edit.text()
        need_recalc = (
            self.last_end_date != end_date or
            self.last_calculate_result is None or
            self.last_formula_expr != current_formula
        )
        print(f'get_or_calculate_result only_show_selected: {only_show_selected}')
        if need_recalc:
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
            params['expr'] = current_formula
            params['select_count'] = select_count if select_count is not None else 10
            params['sort_mode'] = sort_mode if sort_mode is not None else "最大值排序"
            params['ops_change'] = self.ops_change_edit.text()
            # 选股计算公式
            params['formula_expr'] = formula_expr if formula_expr is not None else (self.formula_expr_edit.text() if hasattr(self, 'formula_expr_edit') else '')
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