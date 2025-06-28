from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton, QFrame, QSizePolicy, QCheckBox, QMainWindow
)
from PyQt5.QtCore import Qt, QDate, QEvent
from function.attribute_mapping import get_chinese_alias
from function.base_param import CalculateThread
from function.stock_functions import show_formula_select_table_result

class TradingPlanWidget(QWidget):
    """操盘方案界面"""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.card_states = {}  # 记录每个卡片的最小化/最大化状态
        self.init_ui()
        self.installEventFilter(self)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)  # 关键：让所有内容顶部对齐
        # 顶部控件
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)
        top_layout.setContentsMargins(10, 10, 10, 2)
        top_layout.addWidget(QLabel("请选择结束日期："))
        self.end_date_picker = QDateEdit(calendarPopup=True)
        # 初始化时不设置日期，延迟设置
        # 添加日期变化监听事件
        self.end_date_picker.dateChanged.connect(self.save_end_date_to_main_window)
        top_layout.addWidget(self.end_date_picker)
        
        # 初始化结束日期：优先从主窗口恢复，否则延迟设置
        if hasattr(self.main_window, 'last_trading_plan_end_date') and self.main_window.last_trading_plan_end_date:
            try:
                self.end_date_picker.setDate(QDate.fromString(self.main_window.last_trading_plan_end_date, "yyyy-MM-dd"))
            except Exception as e:
                print(f"恢复操盘方案结束日期失败: {e}")
                # 恢复失败时使用延迟设置
                self.set_end_date_to_latest_workday()
        else:
            # 没有保存的日期时使用延迟设置
            self.set_end_date_to_latest_workday()
        self.select_btn = QPushButton("进行选股")
        top_layout.addWidget(self.select_btn)
        self.select_btn.clicked.connect(self.on_select_btn_clicked)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 下方方案卡片区
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(10, 0, 10, 0)
        self.cards_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        layout.addLayout(self.cards_layout)
        self.refresh_cards()
        layout.addStretch()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.refresh_cards()
        return super().eventFilter(obj, event)

    def refresh_cards(self):
        # 清空旧卡片
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # 获取方案列表
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        plan_list = sorted(plan_list, key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
        max_cards = 6
        total_width = self.width() if self.width() > 0 else 1200
        card_width = int(total_width / max_cards)
        for idx, plan in enumerate(plan_list[:max_cards]):
            # 检查是否参与实操，如果未勾选且用户未手动设置过状态则自动最小化
            is_min = self.card_states.get(idx, None)
            if is_min is None:  # 用户未手动设置过状态
                if not plan.get('real_trade', False):
                    is_min = True
                    self.card_states[idx] = True
                else:
                    is_min = False
                    self.card_states[idx] = False
            card = self.create_plan_card(idx, plan, card_width, is_min)
            # 关键：最小化卡片不被拉伸
            if is_min:
                card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
            else:
                card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # 外包一层垂直布局，保证顶部对齐
            wrapper = QWidget()
            vbox = QVBoxLayout(wrapper)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            vbox.setAlignment(Qt.AlignTop)
            vbox.addWidget(card)
            self.cards_layout.addWidget(wrapper)
        # 补空白
        for _ in range(max_cards - len(plan_list)):
            spacer = QWidget()
            spacer.setFixedWidth(card_width)
            spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.cards_layout.addWidget(spacer)
        # 关键：让所有卡片都靠上
        self.cards_layout.addStretch()

    def create_plan_card(self, idx, plan, card_width, is_minimized):
        card = QFrame()
        card.setFrameShape(QFrame.Box)
        card.setLineWidth(1)
        card.setFixedWidth(card_width)
        if is_minimized:
            card.setFixedHeight(32)
            card.setStyleSheet("background:#fff;")
            hbox = QHBoxLayout(card)
            hbox.setContentsMargins(6, 0, 6, 0)
            hbox.setSpacing(4)
            label_title = QLabel(f"操盘方案 {idx+1}")
            label_title.setStyleSheet("font-size:14px;font-weight:bold;")
            hbox.addWidget(label_title)
            hbox.addStretch()
            btn_max = QPushButton("□")
            btn_max.setFixedSize(20, 20)
            btn_max.setStyleSheet("font-weight:bold;border:none;background:transparent;")
            btn_max.clicked.connect(lambda _, i=idx: self.set_card_minimized(i, False))
            del_btn = QPushButton("×")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("color:red;font-weight:bold;border:none;background:transparent;")
            del_btn.clicked.connect(lambda _, i=idx: self.delete_plan(i))
            hbox.addWidget(btn_max)
            hbox.addWidget(del_btn)
            return card
        # 最大化内容（原有内容）
        card.setMinimumHeight(350)
        card.setMaximumHeight(350)
        card.setStyleSheet("background:#fff;")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(6)
        vbox.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 右上角按钮区
        btn_min = QPushButton("-")
        btn_min.setFixedSize(20, 20)
        btn_min.setStyleSheet("font-weight:bold;border:none;background:transparent;")
        btn_min.clicked.connect(lambda _, i=idx: self.set_card_minimized(i, True))
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("color:red;font-weight:bold;border:none;background:transparent;")
        del_btn.clicked.connect(lambda _, i=idx: self.delete_plan(i))
        hbox_btn = QHBoxLayout()
        hbox_btn.addStretch()
        hbox_btn.addWidget(btn_min)
        hbox_btn.addWidget(del_btn)
        vbox.addLayout(hbox_btn)
        # 标题
        label_title = QLabel(f"操盘方案 {idx+1}")
        label_title.setStyleSheet("font-weight:bold;font-size:15px;")
        label_title.setAlignment(Qt.AlignLeft)
        vbox.addWidget(label_title)
        # 第二行：组合分析排序输出值
        adjusted_value = plan.get('adjusted_value', '')
        try:
            adjusted_value_str = f"{float(adjusted_value):.2f}"
        except Exception:
            adjusted_value_str = str(adjusted_value)
        label_adj = QLabel(f"组合分析排序输出值: {adjusted_value_str}")
        label_adj.setAlignment(Qt.AlignLeft)
        vbox.addWidget(label_adj)
        # 全局变量
        params = plan.get('params', {})
        for key in ['width', 'op_days', 'increment_rate']:
            label = QLabel(f"{get_chinese_alias(key)}: {params.get(key, '')}")
            label.setStyleSheet("font-size:13px;")
            label.setAlignment(Qt.AlignLeft)
            vbox.addWidget(label)
        # 分割线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("color:#ccc;")
        vbox.addWidget(line1)
        # 第三行：公式
        formula = plan.get('formula', '')
        label_formula = QLabel(f"公式:\n {formula}")
        label_formula.setWordWrap(True)
        label_formula.setStyleSheet("font-size:13px;")
        label_formula.setAlignment(Qt.AlignLeft)
        vbox.addWidget(label_formula)
        # 分割线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("color:#ccc;")
        vbox.addWidget(line2)
        # 第四行：是否参与实操（勾选框）
        real_trade_widget = QWidget()
        real_trade_layout = QHBoxLayout(real_trade_widget)
        real_trade_layout.setContentsMargins(0, 0, 0, 0)
        real_trade_layout.setSpacing(5)
        real_trade_checkbox = QCheckBox("是否参与实操")
        real_trade_checkbox.setChecked(plan.get('real_trade', False))
        # 绑定勾选框状态变化事件
        def on_real_trade_changed(state):
            plan['real_trade'] = (state == Qt.Checked)
        real_trade_checkbox.stateChanged.connect(on_real_trade_changed)
        real_trade_layout.addWidget(real_trade_checkbox)
        real_trade_layout.addStretch()
        vbox.addWidget(real_trade_widget)
        
        # 第五行：选股结果按钮
        result_btn = QPushButton("选股结果")
        result_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2D6DA3;
                padding-top: 6px;
                padding-left: 10px;
            }
        """)
        result_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # 绑定按钮点击事件
        def on_result_btn_clicked():
            result = plan.get('result', None)
            if result and isinstance(result, dict):
                try:
                    # 为每个卡片创建独立的窗口实例
                    if 'result_window' not in plan or plan['result_window'] is None:
                        result_window = QMainWindow()
                        result_window.setWindowTitle(f"操盘方案 {idx+1} 选股结果")
                        flags = result_window.windowFlags()
                        flags &= ~Qt.WindowStaysOnTopHint  # 移除置顶标志
                        flags &= ~Qt.WindowContextHelpButtonHint  # 移除问号按钮
                        result_window.setWindowFlags(flags)
                        
                        # 添加窗口关闭事件处理
                        def on_window_closed():
                            plan['result_window'] = None
                            plan['result_table'] = None
                        result_window.destroyed.connect(on_window_closed)
                        
                        plan['result_window'] = result_window
                    else:
                        result_window = plan['result_window']
                        # 如果窗口最小化，则恢复显示
                        if result_window.isMinimized():
                            result_window.showNormal()
                        # 确保窗口在最前面
                        result_window.raise_()
                        result_window.activateWindow()
                    
                    result_table = show_formula_select_table_result(
                        parent=result_window,
                        result=result,
                        price_data=getattr(self.main_window.init, 'price_data', None),
                        is_select_action=False
                    )
                    if result_table:
                        # 替换内容
                        central_widget = QWidget()
                        layout = QVBoxLayout(central_widget)
                        layout.addWidget(result_table)
                        result_window.setCentralWidget(central_widget)
                        result_window.resize(580, 450)
                        result_window.show()
                        plan['result_window'] = result_window
                        plan['result_table'] = result_table
                except Exception as e:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "错误", f"选股结果加载失败: {e}")
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "提示", "暂无选股结果")
        
        result_btn.clicked.connect(on_result_btn_clicked)
        
        vbox.addWidget(result_btn)
        
        vbox.addStretch()
        return card

    def set_card_minimized(self, idx, minimized):
        self.card_states[idx] = minimized
        self.refresh_cards()

    def delete_plan(self, idx):
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        if 0 <= idx < len(plan_list):
            plan_list.pop(idx)
            self.clean_plan_for_save(plan_list)
            self.main_window.trading_plan_list = plan_list
            self.refresh_cards()

    def on_select_btn_clicked(self):
        self.calculate_all_trading_plans()
        self.refresh_cards()

    def calculate_all_trading_plans(self):
        """
        遍历trading_plan_list，对每个方案用params创建CalculateThread并计算，将结果写回plan['result']。
        """
        # 检查是否有数据文件
        price_data = getattr(self.main_window.init, 'price_data', None)
        if price_data is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "提示", "请先上传数据文件！")
            return
            
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        for plan in plan_list:
            # 检查是否参与实操，如果为False则跳过
            if not plan.get('real_trade', False):
                continue
                
            params = plan.get('params', {})
            # 将公式添加到params中
            formula = plan.get('formula', '')
            params['formula_expr'] = formula
            
            # 将结束日期添加到params中
            end_date = self.end_date_picker.date().toString("yyyy-MM-dd")
            params['end_date_start'] = end_date
            params['end_date_end'] = end_date
            params['max_cores'] = 1
            
            # 参数名称映射和类型转换，确保与stock_analysis_ui_v2.py一致
            if 'after_gt_end_edit' in params:
                params['after_gt_end_ratio'] = float(params.pop('after_gt_end_edit'))
            if 'after_gt_prev_edit' in params:
                params['after_gt_start_ratio'] = float(params.pop('after_gt_prev_edit'))
            if 'increment_rate' in params:
                params['inc_rate'] = float(params.pop('increment_rate'))
            if 'shift' in params:
                params['shift_days'] = params.pop('shift')
            if 'direction' in params:
                params['is_forward'] = params.pop('direction')
            
            # 确保其他数值参数为正确的类型
            if 'inc_rate' in params and isinstance(params['inc_rate'], str):
                params['inc_rate'] = float(params['inc_rate'])
            if 'ops_change' in params and isinstance(params['ops_change'], str):
                params['ops_change'] = float(params['ops_change'])
            if 'range_value' in params and isinstance(params['range_value'], str):
                params['range_value'] = float(params['range_value'])
            if 'continuous_abs_threshold' in params and isinstance(params['continuous_abs_threshold'], str):
                params['continuous_abs_threshold'] = float(params['continuous_abs_threshold'])
            if 'valid_abs_sum_threshold' in params and isinstance(params['valid_abs_sum_threshold'], str):
                params['valid_abs_sum_threshold'] = float(params['valid_abs_sum_threshold'])
            
            # 添加一些必要的默认参数
            if 'select_count' not in params:
                params['select_count'] = params.get('last_select_count', 10)
            if 'sort_mode' not in params:
                params['sort_mode'] = '最大值排序'
            if 'only_show_selected' not in params:
                params['only_show_selected'] = True
            
            # 直接用CalculateThread计算
            calc = CalculateThread(
                self.main_window.init.price_data,
                self.main_window.init.diff_data,
                self.main_window.init.workdays_str,
                params
            )
            result = calc.calculate_batch_16_cores(params)
            # 新增：将股票名称写入result
            price_data = getattr(self.main_window.init, 'price_data', None)
            if result and isinstance(result, dict) and price_data is not None:
                merged_results = result.get('dates', {})
                for stocks in merged_results.values():
                    for stock in stocks:
                        stock_idx = stock.get('stock_idx', None)
                        if stock_idx is not None and 'name' not in stock:
                            stock['name'] = price_data.iloc[stock_idx, 1]
            plan['result'] = result
        self.clean_plan_for_save(plan_list)

    @staticmethod
    def clean_plan_for_save(plan_list):
        """
        清理每个plan中的不可序列化字段，防止保存配置时报错。
        """
        for plan in plan_list:
            plan.pop('result_window', None)
            plan.pop('result_table', None)

    def set_end_date_to_latest_workday(self):
        """
        延迟设置结束日期为workdays_str最后一天。
        """
        workdays_str = getattr(self.main_window.init, 'workdays_str', None)
        if workdays_str and len(workdays_str) > 0:
            self.end_date_picker.setDate(QDate.fromString(workdays_str[-1], "yyyy-MM-dd"))
        else:
            self.end_date_picker.setDate(QDate.currentDate())

    def save_end_date_to_main_window(self):
        """
        将当前结束日期保存到主窗口属性。
        """
        if hasattr(self, 'end_date_picker'):
            self.main_window.last_trading_plan_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")

# 用法示例：
# TradingPlanWidget.clean_plan_for_save(trading_plan_list)  # 在save_config等保存前调用