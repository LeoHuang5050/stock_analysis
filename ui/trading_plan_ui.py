from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton, QFrame, QSizePolicy, QCheckBox, QMainWindow,
    QDialog, QLineEdit, QMessageBox, QHeaderView, QScrollArea, QDesktopWidget, QTabWidget, QApplication
)
from PyQt5.QtCore import Qt, QDate, QEvent, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QKeyEvent

from function.base_param import CalculateThread
from function.stock_functions import show_formula_select_table_result

def clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                clear_layout(child_layout)

class TradingPlanWidget(QWidget):
    """操盘方案界面"""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_page = 0  # 当前页面索引
        self.cards_per_page = 3  # 每页显示的卡片数量
        self.tab_enabled = True  # Tab切换功能是否启用
        self.init_ui()
        self.installEventFilter(self)
        
        # 确保初始化时Tab切换功能启用
        QTimer.singleShot(300, lambda: setattr(self, 'tab_enabled', True))
        
        # 设置焦点策略，使widget能够接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 延迟设置焦点和安装事件过滤器
        QTimer.singleShot(100, lambda: (self.setFocus(), setattr(self, 'tab_enabled', True)))
        QTimer.singleShot(200, self.install_event_filters)
        
        # 监听文件上传成功事件
        self.setup_file_upload_listener()

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
        # 添加日期变化监听事件（暂时保留，以备将来需要）
        # self.end_date_picker.dateChanged.connect(self.save_end_date_to_main_window)
        top_layout.addWidget(self.end_date_picker)
        
        # 初始化结束日期：设置为workdays_str最后一天或当前日期
        self.init_end_date()
        self.select_btn = QPushButton("进行选股")
        top_layout.addWidget(self.select_btn)
        self.select_btn.clicked.connect(self.on_select_btn_clicked)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 书签式标签栏
        self.tab_bar = QHBoxLayout()
        self.tab_bar.setSpacing(5)
        self.tab_bar.setContentsMargins(10, 5, 10, 5)
        self.tab_buttons = []  # 存储标签按钮
        layout.addLayout(self.tab_bar)

        # 卡片区用QWidget+QVBoxLayout
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(10, 0, 10, 0)
        self.cards_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.cards_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # 用QScrollArea包裹卡片区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, 1)  # 让scroll占据剩余空间

        self.refresh_cards()

    def install_event_filters(self):
        """为主要控件安装事件过滤器"""
        # 只为主要的输入控件安装事件过滤器
        if hasattr(self, 'end_date_picker'):
            self.end_date_picker.installEventFilter(self)
        if hasattr(self, 'select_btn'):
            self.select_btn.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.refresh_cards()
        elif event.type() == QEvent.KeyPress:
            # 只在Tab切换功能启用时拦截键盘事件
            if self.tab_enabled:
                if event.key() == Qt.Key_Tab:
                    self.next_page()
                    return True
                elif event.key() == Qt.Key_Backtab:
                    self.prev_page()
                    return True

        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        if self.tab_enabled:
            if event.key() == Qt.Key_Tab:
                # Tab键切换页面
                self.next_page()
                event.accept()
            elif event.key() == Qt.Key_Backtab:
                # Shift+Tab键切换到上一页
                self.prev_page()
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def on_focus_out(self, event):
        """当焦点离开widget时禁用Tab切换功能"""
        super().focusOutEvent(event)
        self.tab_enabled = False

    def next_page(self):
        """切换到下一页"""
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        total_pages = (len(plan_list) + self.cards_per_page - 1) // self.cards_per_page
        if total_pages > 0:
            self.current_page = (self.current_page + 1) % total_pages
            self.refresh_cards()
            self.update_tab_buttons()
            # 键盘切换时设置焦点并启用Tab切换
            self.setFocus()
            self.tab_enabled = True

    def prev_page(self):
        """切换到上一页"""
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        total_pages = (len(plan_list) + self.cards_per_page - 1) // self.cards_per_page
        if total_pages > 0:
            self.current_page = (self.current_page - 1) % total_pages
            self.refresh_cards()
            self.update_tab_buttons()
            # 键盘切换时设置焦点并启用Tab切换
            self.setFocus()
            self.tab_enabled = True

    def create_tab_buttons(self):
        """创建书签式标签按钮"""
        # 清除现有按钮
        for btn in self.tab_buttons:
            btn.setParent(None)
            btn.deleteLater()
        self.tab_buttons.clear()
        
        # 清除布局
        while self.tab_bar.count():
            item = self.tab_bar.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        total_pages = (len(plan_list) + self.cards_per_page - 1) // self.cards_per_page
        
        if total_pages == 0:
            return

        # 创建标签按钮
        for i in range(total_pages):
            start_idx = i * self.cards_per_page
            end_idx = min(start_idx + self.cards_per_page, len(plan_list))
            
            # 创建书签式按钮
            tab_btn = QPushButton(f"第{start_idx+1}-{end_idx}个方案")
            tab_btn.setFixedSize(120, 30)
            tab_btn.setCheckable(True)
            tab_btn.setChecked(i == self.current_page)
            
            # 设置书签样式
            if i == self.current_page:
                tab_btn.setStyleSheet("""
                    QPushButton {
                        background: #4A90E2;
                        color: white;
                        border: 2px solid #4A90E2;
                        border-radius: 15px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #357ABD;
                    }
                """)
            else:
                tab_btn.setStyleSheet("""
                    QPushButton {
                        background: #f0f0f0;
                        color: #333;
                        border: 2px solid #ddd;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border-color: #4A90E2;
                    }
                """)
            
            # 绑定点击事件
            tab_btn.clicked.connect(lambda checked, page=i: self.switch_to_page_with_focus(page))
            
            self.tab_buttons.append(tab_btn)
            self.tab_bar.addWidget(tab_btn)
        
        # 添加提示信息
        tip_label = QLabel("(按Tab键切换页面)")
        tip_label.setStyleSheet("color: #666; font-size: 12px; margin-left: 10px;")
        self.tab_bar.addWidget(tip_label)
        
        self.tab_bar.addStretch()

    def update_tab_buttons(self):
        """更新标签按钮状态"""
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == self.current_page)
            if i == self.current_page:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #4A90E2;
                        color: white;
                        border: 2px solid #4A90E2;
                        border-radius: 15px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #357ABD;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #f0f0f0;
                        color: #333;
                        border: 2px solid #ddd;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background: #e0e0e0;
                        border-color: #4A90E2;
                    }
                """)

    def switch_to_page(self, page):
        """切换到指定页面"""
        self.current_page = page
        self.refresh_cards()
        self.update_tab_buttons()

    def switch_to_page_with_focus(self, page):
        """切换到指定页面并设置焦点"""
        self.switch_to_page(page)
        # 设置焦点到当前widget并启用Tab切换
        self.setFocus()
        self.tab_enabled = True

    def refresh_cards(self):
        # 递归清理所有旧内容和嵌套布局，防止重影
        clear_layout(self.cards_layout)
        
        # 创建标签按钮
        self.create_tab_buttons()
        
        # 获取方案列表
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        
        # 保存排序后的列表到主窗口，确保索引一致
        sorted_plan_list = sorted(plan_list, key=lambda x: float(x.get('adjusted_value', 0)), reverse=True)
        self.main_window.sorted_trading_plan_list = sorted_plan_list
        
        # 计算当前页面显示的方案
        start_idx = self.current_page * self.cards_per_page
        end_idx = min(start_idx + self.cards_per_page, len(sorted_plan_list))
        current_page_plans = sorted_plan_list[start_idx:end_idx]
        
        # 固定每行3个卡片，宽度600
        cards_per_row = 3
        card_width = 780
        
        # 按行分组显示卡片
        for row_start in range(0, len(current_page_plans), cards_per_row):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            
            for col in range(cards_per_row):
                idx = row_start + col
                if idx < len(current_page_plans):
                    plan = current_page_plans[idx]
                    # 计算在原始列表中的索引
                    original_idx = start_idx + idx
                    # 只根据用户操作记录的card_states决定最大/最小化，默认最大化
                    is_min = plan.get('card_minimized', False)
                    card = self.create_plan_card(original_idx, plan, card_width, is_min)
                    if is_min:
                        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
                    else:
                        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                    
                    wrapper = QWidget()
                    wrapper.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
                    vbox = QVBoxLayout(wrapper)
                    vbox.setContentsMargins(0, 0, 0, 0)
                    vbox.setSpacing(0)
                    vbox.setAlignment(Qt.AlignTop)
                    vbox.addWidget(card)
                    row_layout.addWidget(wrapper)
                else:
                    spacer = QWidget()
                    spacer.setFixedWidth(card_width)
                    spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    row_layout.addWidget(spacer)
            
            self.cards_layout.addLayout(row_layout)
        
        self.cards_layout.addStretch()
        # 强制重绘，防止重影
        self.cards_layout.update()
        self.update()
        self.cards_container.adjustSize()
        
        # 刷新后重新设置焦点
        if self.tab_enabled:
            self.setFocus()

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
            label_title = QLabel(plan.get('plan_name', "操盘方案"))
            label_title.setStyleSheet("font-size:14px;font-weight:bold;")
            hbox.addWidget(label_title)
            hbox.addStretch()
            edit_btn = QPushButton("✎")
            edit_btn.setFixedSize(20, 20)
            edit_btn.setStyleSheet("font-weight:bold;border:none;background:transparent;color:blue;")
            edit_btn.clicked.connect(lambda _, i=idx: self.edit_plan_name(i))
            btn_max = QPushButton("□")
            btn_max.setFixedSize(20, 20)
            btn_max.setStyleSheet("font-weight:bold;border:none;background:transparent;")
            btn_max.clicked.connect(lambda _, i=idx: self.set_card_minimized(i, False))
            del_btn = QPushButton("×")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet("color:red;font-weight:bold;border:none;background:transparent;")
            del_btn.clicked.connect(lambda _, i=idx: self.delete_plan(i))
            hbox.addWidget(edit_btn)
            hbox.addWidget(btn_max)
            hbox.addWidget(del_btn)
            return card
        # 最大化内容（原有内容）
        card.setFixedHeight(840)
        card.setStyleSheet("background:#fff;")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(3)
        vbox.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 右上角按钮区
        btn_min = QPushButton("-")
        btn_min.setFixedSize(20, 20)
        btn_min.setStyleSheet("font-weight:bold;border:none;background:transparent;")
        btn_min.clicked.connect(lambda _, i=idx: self.set_card_minimized(i, True))
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(20, 20)
        edit_btn.setStyleSheet("font-weight:bold;border:none;background:transparent;color:blue;")
        edit_btn.clicked.connect(lambda _, i=idx: self.edit_plan_name(i))
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("color:red;font-weight:bold;border:none;background:transparent;")
        del_btn.clicked.connect(lambda _, i=idx: self.delete_plan(i))
        hbox_btn = QHBoxLayout()
        hbox_btn.addStretch()
        hbox_btn.addWidget(edit_btn)
        hbox_btn.addWidget(btn_min)
        hbox_btn.addWidget(del_btn)
        vbox.addLayout(hbox_btn)
        # 标题
        label_title = QLabel(plan.get('plan_name', "操盘方案"))
        label_title.setStyleSheet("font-weight:bold;font-size:14px;")
        label_title.setAlignment(Qt.AlignLeft)
        vbox.addWidget(label_title)
        
        # 显示选股公式
        formula = plan.get('formula', '')
        if formula:
            label_formula = QLabel(f"选股公式：\n{formula}")
            label_formula.setStyleSheet("font-size:12px;")
            label_formula.setAlignment(Qt.AlignLeft)
            vbox.addWidget(label_formula)
        
        # 显示选股参数（按指定顺序分行输出）
        params = plan.get('params', {})
        params_text = []
        params_text.append(f"选股数量: {params.get('last_select_count', 10)}")
        params_text.append(f"排序方式: {params.get('last_sort_mode', '')}")
        params_text.append(f"开始日期值选择: {params.get('start_option', '')}")
        params_text.append(f"交易方式: {params.get('trade_mode', '')}")
        params_text.append(f"操作值: {params.get('expr', '')}")
        params_text.append(f"日期宽度: {params.get('width', '')}")
        params_text.append(f"操作天数: {params.get('op_days', '')}")
        params_text.append(f"止盈递增率: {params.get('increment_rate', '')}")
        params_text.append(f"止盈后值大于结束值比例: {params.get('after_gt_end_ratio', '')}")
        params_text.append(f"止盈后值大于前值比例: {params.get('after_gt_start_ratio', '')}")
        params_text.append(f"止损递增率: {params.get('stop_loss_inc_rate', '')}")
        params_text.append(f"止损后值大于结束值比例: {params.get('stop_loss_after_gt_end_ratio', '')}")
        params_text.append(f"止损后值大于前值比例: {params.get('stop_loss_after_gt_start_ratio', '')}")
        
        if params_text:
            label_params = QLabel("选股参数：\n" + "\n".join(params_text))
            label_params.setStyleSheet("font-size:12px;")
            label_params.setAlignment(Qt.AlignLeft)
            vbox.addWidget(label_params)
        
        # 添加空行
        empty_label = QLabel("")
        empty_label.setFixedHeight(10)
        vbox.addWidget(empty_label)
        
        # 显示参加组合排序的参数名
        params = plan.get('params', {})
        selected_vars = params.get('selected_vars_with_values', [])
        if selected_vars:
            # 构建参数显示文本
            param_lines = ["参加组合排序参数："]
            
            for var_name, value in selected_vars:  # 解包元组
                param_lines.append(f"{var_name}: {value:.2f}")  # 直接使用中文名称
            
            # 添加组合排序输出值
            adjusted_value = plan.get('adjusted_value', 0)
            if adjusted_value:
                try:
                    adjusted_value = float(adjusted_value)
                    param_lines.append(f"组合排序输出值: {adjusted_value:.2f}")
                except (ValueError, TypeError):
                    param_lines.append("组合排序输出值: 0.00")
            
            label_vars = QLabel("\n".join(param_lines))
            label_vars.setStyleSheet("font-size:12px;")
            label_vars.setAlignment(Qt.AlignLeft)
            vbox.addWidget(label_vars)
        
        # 分割线
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("color:#ccc;")
        vbox.addWidget(line1)
        
        # 第四行：是否参与实操（勾选框）和恢复参数按钮
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
        
        # 添加恢复参数按钮
        restore_btn = QPushButton("恢复参数")
        restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        # 绑定恢复参数事件
        def on_restore_params_clicked():
            self.restore_plan_params(plan)
        restore_btn.clicked.connect(on_restore_params_clicked)
        real_trade_layout.addWidget(restore_btn)
        
        real_trade_layout.addStretch()
        vbox.addWidget(real_trade_widget)
        
        # 选股结果分割线
        result_line = QFrame()
        result_line.setFrameShape(QFrame.HLine)
        result_line.setStyleSheet("color:#4A90E2;border-width:2px;")
        vbox.addWidget(result_line)
        
        # 选股结果标题
        result_title = QLabel("====选股结果====")
        result_title.setStyleSheet("font-weight:bold;font-size:12px;color:#4A90E2;text-align:center;")
        result_title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(result_title)
        
        # 选股结果表格区域
        result_area = QWidget()
        result_area.setStyleSheet("border:1px solid #ddd;background:#f9f9f9;")
        result_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 设置选股结果区域占用更多空间
        vbox.addWidget(result_area, 1)  # 添加拉伸因子1，让它占用更多空间
        
        # 如果有选股结果，显示表格
        result = plan.get('result', None)
        if result and isinstance(result, dict):
            try:
                result_table = show_formula_select_table_result(
                    parent=result_area,
                    result=result,
                    price_data=getattr(self.main_window.init, 'price_data', None),
                    is_select_action=False
                )
                if result_table:
                    # 设置表格完全展示，不限制高度
                    result_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    # 恢复正常字体大小
                    result_table.setStyleSheet("font-size:12px;")
                    # 列宽自适应内容
                    result_table.resizeColumnsToContents()
                    # 设置"选股公式输出值"列根据列名自适应宽度，不拉伸
                    result_table.horizontalHeader().setStretchLastSection(False)
                    # 手动设置最后一列的宽度，让它只根据列名自适应
                    last_col_width = result_table.horizontalHeader().sectionSizeHint(6)  # 第7列（索引6）是"选股公式输出值"
                    result_table.setColumnWidth(6, last_col_width)
                    # 设置合适的行高
                    result_table.verticalHeader().setDefaultSectionSize(25)
                    result_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
                    
                    # 将表格添加到结果区域
                    result_layout = QVBoxLayout(result_area)
                    result_layout.setContentsMargins(1, 1, 1, 1)
                    result_layout.addWidget(result_table)
                    # 设置表格大小策略，让它能够根据内容自动调整
                    result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            except Exception as e:
                error_label = QLabel(f"选股结果加载失败: {e}")
                error_label.setStyleSheet("color:red;font-size:10px;")
                error_label.setAlignment(Qt.AlignCenter)
                result_layout = QVBoxLayout(result_area)
                result_layout.addWidget(error_label)
        else:
            no_result_label = QLabel("暂无选股结果")
            no_result_label.setStyleSheet("color:#999;font-size:12px;")
            no_result_label.setAlignment(Qt.AlignCenter)
            result_layout = QVBoxLayout(result_area)
            result_layout.addWidget(no_result_label)
        
        return card

    def set_card_minimized(self, idx, minimized):
        # 使用排序后的列表来获取正确的plan
        sorted_plan_list = getattr(self.main_window, 'sorted_trading_plan_list', [])
        if 0 <= idx < len(sorted_plan_list):
            plan_to_update = sorted_plan_list[idx]
            plan_id = plan_to_update.get('plan_id')
            
            # 在原始列表中找到对应的plan并更新
            plan_list = getattr(self.main_window, 'trading_plan_list', [])
            for plan in plan_list:
                if plan.get('plan_id') == plan_id:
                    plan['card_minimized'] = minimized
                    break
        self.refresh_cards()

    def delete_plan(self, idx):
        # 使用排序后的列表来获取正确的plan
        sorted_plan_list = getattr(self.main_window, 'sorted_trading_plan_list', [])
        if 0 <= idx < len(sorted_plan_list):
            plan_to_delete = sorted_plan_list[idx]
            plan_id = plan_to_delete.get('plan_id')
            
            # 从原始列表中删除对应的plan
            plan_list = getattr(self.main_window, 'trading_plan_list', [])
            plan_list = [plan for plan in plan_list if plan.get('plan_id') != plan_id]
            
            self.clean_plan_for_save(plan_list)
            self.main_window.trading_plan_list = plan_list
            self.refresh_cards()

    def on_select_btn_clicked(self):
        self.calculate_all_trading_plans()
        self.refresh_cards()
        
        # 统计参与实操的方案数量
        plan_list = getattr(self.main_window, 'trading_plan_list', [])
        real_trade_count = sum(1 for plan in plan_list if plan.get('real_trade', False))
        if real_trade_count > 0:
            QMessageBox.warning(self, "选股完成", "操盘方案选股已完成！")
            

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
            
            # 检查结束日期是否为交易日
            if hasattr(self.main_window.init, 'workdays_str'):
                if not self.main_window.init.workdays_str:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "提示", "请先上传数据文件！")
                    return
                if end_date not in self.main_window.init.workdays_str:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "提示", "只能选择交易日！")
                    return
            
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

    def init_end_date(self):
        """
        初始化结束日期：设置为workdays_str最后一天或当前日期
        """
        self.set_end_date_to_latest_workday()

    def restore_end_date_from_cache(self):
        """
        从缓存恢复结束日期：优先使用缓存，否则设置为workdays_str最后一天或当前日期
        """
        try:
            # 优先从缓存恢复
            cached_date = getattr(self.main_window, 'last_trading_plan_end_date', None)
            if cached_date:
                if hasattr(self, 'end_date_picker') and self.end_date_picker is not None:
                    self.end_date_picker.setDate(QDate.fromString(cached_date, "yyyy-MM-dd"))
                    print(f"从缓存恢复操盘方案结束日期: {cached_date}")
                    return
                else:
                    print("end_date_picker控件不存在，无法从缓存恢复")
            
            # 如果没有缓存，使用原来的逻辑
            self.set_end_date_to_latest_workday()
        except Exception as e:
            print(f"从缓存恢复结束日期失败: {e}")
            # 如果恢复失败，使用原来的逻辑
            self.set_end_date_to_latest_workday()

    def set_end_date_to_latest_workday(self):
        """
        设置结束日期：如果上传了文件就设置为workdays_str最后一天，否则默认为今天
        """
        try:
            workdays_str = getattr(self.main_window.init, 'workdays_str', None)
            if workdays_str and len(workdays_str) > 0:
                # 检查控件是否仍然有效
                if hasattr(self, 'end_date_picker') and self.end_date_picker is not None:
                    self.end_date_picker.setDate(QDate.fromString(workdays_str[-1], "yyyy-MM-dd"))
                    print(f"设置操盘方案结束日期为: {workdays_str[-1]}")
                else:
                    print("end_date_picker控件不存在，跳过设置")
            else:
                if hasattr(self, 'end_date_picker') and self.end_date_picker is not None:
                    self.end_date_picker.setDate(QDate.currentDate())
                    print("设置操盘方案结束日期为当前日期")
                else:
                    print("end_date_picker控件不存在，跳过设置")
        except Exception as e:
            print(f"设置结束日期失败: {e}")

    def setup_file_upload_listener(self):
        """
        设置文件上传成功监听器
        """
        # 监听主窗口的文件上传成功事件
        if hasattr(self.main_window, 'init') and hasattr(self.main_window.init, 'on_file_loaded'):
            # 保存原始的文件加载完成方法
            original_on_file_loaded = self.main_window.init.on_file_loaded
            
            def new_on_file_loaded(df, price_data, diff_data, workdays_str, error_msg):
                # 调用原始方法
                original_on_file_loaded(df, price_data, diff_data, workdays_str, error_msg)
                
                # 如果没有错误，将结束日期保存到缓存中
                if not error_msg and workdays_str and len(workdays_str) > 0:
                    # 保存到主窗口缓存
                    self.main_window.last_trading_plan_end_date = workdays_str[-1]
                    print(f"文件上传成功，缓存操盘方案结束日期: {workdays_str[-1]}")
                    
                    # 如果操盘方案界面已经创建，则立即设置日期
                    if hasattr(self, 'end_date_picker') and self.end_date_picker is not None:
                        try:
                            self.end_date_picker.setDate(QDate.fromString(workdays_str[-1], "yyyy-MM-dd"))
                            print(f"立即设置操盘方案结束日期为: {workdays_str[-1]}")
                        except Exception as e:
                            print(f"立即设置结束日期失败: {e}")
            
            # 替换方法
            self.main_window.init.on_file_loaded = new_on_file_loaded

    def save_end_date_to_main_window(self):
        """
        将当前结束日期保存到主窗口属性。
        """
        if hasattr(self, 'end_date_picker'):
            self.main_window.last_trading_plan_end_date = self.end_date_picker.date().toString("yyyy-MM-dd")

    def restore_plan_params(self, plan):
        """恢复操盘方案参数到主窗口控件"""
        try:
            # 获取操盘方案的参数
            params = plan.get('params', {})
            formula = plan.get('formula', '')
            
            # 恢复基本参数
            if 'width' in params and hasattr(self.main_window, 'width_spin'):
                try:
                    width_val = int(float(params['width']))
                    self.main_window.width_spin.setValue(width_val)
                    print(f"恢复日期宽度: {width_val}")
                except:
                    pass
            
            if 'start_option' in params and hasattr(self.main_window, 'start_option_combo'):
                try:
                    start_option = params['start_option']
                    idx = self.main_window.start_option_combo.findText(start_option)
                    if idx >= 0:
                        self.main_window.start_option_combo.setCurrentIndex(idx)
                        print(f"恢复开始日期值选择: {start_option}")
                except:
                    pass
            
            if 'shift' in params and hasattr(self.main_window, 'shift_spin'):
                try:
                    shift_val = int(float(params['shift']))
                    self.main_window.shift_spin.setValue(shift_val)
                    print(f"恢复前移天数: {shift_val}")
                except:
                    pass
            
            if 'direction' in params and hasattr(self.main_window, 'direction_checkbox'):
                try:
                    is_forward = bool(params['direction'])
                    self.main_window.direction_checkbox.setChecked(is_forward)
                    print(f"恢复是否计算向前: {is_forward}")
                except:
                    pass
            
            if 'trade_mode' in params and hasattr(self.main_window, 'trade_mode_combo'):
                try:
                    trade_mode = params['trade_mode']
                    idx = self.main_window.trade_mode_combo.findText(trade_mode)
                    if idx >= 0:
                        self.main_window.trade_mode_combo.setCurrentIndex(idx)
                        print(f"恢复交易方式: {trade_mode}")
                except:
                    pass
            
            # 恢复组合分析次数
            if 'component_analysis_count' in params:
                try:
                    component_analysis_count = params['component_analysis_count']
                    if component_analysis_count:
                        count_val = int(float(component_analysis_count))
                        self.main_window.last_component_analysis_count = count_val
                        print(f"恢复组合分析次数: {count_val}")
                except Exception as e:
                    print(f"恢复组合分析次数失败: {e}")
            
            # 恢复操作相关参数
            if 'op_days' in params and hasattr(self.main_window, 'op_days_edit'):
                try:
                    self.main_window.op_days_edit.setText(str(params['op_days']))
                    print(f"恢复操作天数: {params['op_days']}")
                except:
                    pass
            
            if 'increment_rate' in params and hasattr(self.main_window, 'inc_rate_edit'):
                try:
                    self.main_window.inc_rate_edit.setText(str(params['increment_rate']))
                    print(f"恢复止盈递增率: {params['increment_rate']}")
                except:
                    pass
            
            if 'after_gt_end_ratio' in params and hasattr(self.main_window, 'after_gt_end_edit'):
                try:
                    self.main_window.after_gt_end_edit.setText(str(params['after_gt_end_ratio']))
                    print(f"恢复止盈后值大于结束值比例: {params['after_gt_end_ratio']}")
                except:
                    pass
            
            if 'after_gt_start_ratio' in params and hasattr(self.main_window, 'after_gt_prev_edit'):
                try:
                    self.main_window.after_gt_prev_edit.setText(str(params['after_gt_start_ratio']))
                    print(f"恢复止盈后值大于前值比例: {params['after_gt_start_ratio']}")
                except:
                    pass
            
            # 恢复止损参数
            if 'stop_loss_inc_rate' in params and hasattr(self.main_window, 'stop_loss_inc_rate_edit'):
                try:
                    self.main_window.stop_loss_inc_rate_edit.setText(str(params['stop_loss_inc_rate']))
                    print(f"恢复止损递增率: {params['stop_loss_inc_rate']}")
                except:
                    pass
            
            if 'stop_loss_after_gt_end_ratio' in params and hasattr(self.main_window, 'stop_loss_after_gt_end_edit'):
                try:
                    self.main_window.stop_loss_after_gt_end_edit.setText(str(params['stop_loss_after_gt_end_ratio']))
                    print(f"恢复止损后值大于结束值比例: {params['stop_loss_after_gt_end_ratio']}")
                except:
                    pass
            
            if 'stop_loss_after_gt_start_ratio' in params and hasattr(self.main_window, 'stop_loss_after_gt_start_edit'):
                try:
                    self.main_window.stop_loss_after_gt_start_edit.setText(str(params['stop_loss_after_gt_start_ratio']))
                    print(f"恢复止损后值大于前值比例: {params['stop_loss_after_gt_start_ratio']}")
                except:
                    pass
            
            # 恢复其他参数
            if 'n_days' in params and hasattr(self.main_window, 'n_days_spin'):
                try:
                    n_days_val = int(float(params['n_days']))
                    self.main_window.n_days_spin.setValue(n_days_val)
                    print(f"恢复第1组后N最大值逻辑: {n_days_val}")
                except:
                    pass
            
            if 'n_days_max' in params and hasattr(self.main_window, 'n_days_max_spin'):
                try:
                    n_days_max_val = int(float(params['n_days_max']))
                    self.main_window.n_days_max_spin.setValue(n_days_max_val)
                    print(f"恢复前1组结束地址后N日的最大值: {n_days_max_val}")
                except:
                    pass
            
            if 'range_value' in params and hasattr(self.main_window, 'range_value_edit'):
                try:
                    self.main_window.range_value_edit.setText(str(params['range_value']))
                    print(f"恢复开始日到结束日之间最高价/最低价小于: {params['range_value']}")
                except:
                    pass
            
            if 'continuous_abs_threshold' in params and hasattr(self.main_window, 'continuous_abs_threshold_edit'):
                try:
                    self.main_window.continuous_abs_threshold_edit.setText(str(params['continuous_abs_threshold']))
                    print(f"恢复开始日到结束日之间连续累加值绝对值小于: {params['continuous_abs_threshold']}")
                except:
                    pass
            
            if 'valid_abs_sum_threshold' in params and hasattr(self.main_window, 'valid_abs_sum_threshold_edit'):
                try:
                    self.main_window.valid_abs_sum_threshold_edit.setText(str(params['valid_abs_sum_threshold']))
                    print(f"恢复开始日到结束日之间有效累加值绝对值小于: {params['valid_abs_sum_threshold']}")
                except:
                    pass
            
            if 'ops_change' in params and hasattr(self.main_window, 'ops_change_edit'):
                try:
                    self.main_window.ops_change_edit.setText(str(params['ops_change']))
                    print(f"恢复操作涨幅: {params['ops_change']}")
                except:
                    pass
            
            # 恢复操作值表达式
            if 'expr' in params:
                try:
                    self.main_window.last_expr = params['expr']
                    print(f"恢复操作值表达式: {params['expr']}")
                except:
                    pass
            
            # 恢复选股数量和排序方式
            if 'last_select_count' in params:
                try:
                    self.main_window.last_select_count = int(params['last_select_count'])
                    print(f"恢复选股数量: {params['last_select_count']}")
                except:
                    pass
            
            if 'last_sort_mode' in params:
                try:
                    self.main_window.last_sort_mode = params['last_sort_mode']
                    print(f"恢复排序方式: {params['last_sort_mode']}")
                except:
                    pass
            
            # 恢复创新高/创新低相关参数
            new_high_low_params = [
                'new_before_high_start', 'new_before_high_range', 'new_before_high_span',
                'new_before_high2_start', 'new_before_high2_range', 'new_before_high2_span',
                'new_after_high_start', 'new_after_high_range', 'new_after_high_span',
                'new_after_high2_start', 'new_after_high2_range', 'new_after_high2_span',
                'new_before_low_start', 'new_before_low_range', 'new_before_low_span',
                'new_before_low2_start', 'new_before_low2_range', 'new_before_low2_span',
                'new_after_low_start', 'new_after_low_range', 'new_after_low_span',
                'new_after_low2_start', 'new_after_low2_range', 'new_after_low2_span'
            ]
            
            for param_name in new_high_low_params:
                if param_name in params and hasattr(self.main_window, param_name + '_spin'):
                    try:
                        spin_val = int(float(params[param_name]))
                        getattr(self.main_window, param_name + '_spin').setValue(spin_val)
                        print(f"恢复{param_name}: {spin_val}")
                    except:
                        pass
            
            # 恢复创新高/创新低逻辑参数
            logic_params = [
                'new_before_high_logic', 'new_before_high2_logic', 'new_after_high_logic', 'new_after_high2_logic',
                'new_before_low_logic', 'new_before_low2_logic', 'new_after_low_logic', 'new_after_low2_logic'
            ]
            
            for param_name in logic_params:
                if param_name in params and hasattr(self.main_window, param_name + '_combo'):
                    try:
                        logic_val = params[param_name]
                        combo = getattr(self.main_window, param_name + '_combo')
                        idx = combo.findText(logic_val)
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                            print(f"恢复{param_name}: {logic_val}")
                    except:
                        pass
            
            # 恢复创新高/创新低标志参数
            flag_params = [
                'new_before_high_flag', 'new_before_high2_flag', 'new_after_high_flag', 'new_after_high2_flag',
                'new_before_low_flag', 'new_before_low2_flag', 'new_after_low_flag', 'new_after_low2_flag'
            ]
            
            for param_name in flag_params:
                if param_name in params and hasattr(self.main_window, param_name + '_checkbox'):
                    try:
                        flag_val = bool(params[param_name])
                        getattr(self.main_window, param_name + '_checkbox').setChecked(flag_val)
                        print(f"恢复{param_name}: {flag_val}")
                    except:
                        pass
            
            # 恢复公式相关状态
            if 'last_formula_select_state' in params:
                try:
                    self.main_window.last_formula_select_state = params['last_formula_select_state']
                    print(f"恢复公式选择状态")
                except:
                    pass
            
            if 'forward_param_state' in params:
                try:
                    self.main_window.forward_param_state = params['forward_param_state']
                    print(f"恢复向前参数状态")
                except:
                    pass
            
            # 恢复公式表达式
            if formula:
                try:
                    self.main_window.last_formula_expr = formula
                    print(f"恢复公式表达式: {formula}")
                except:
                    pass
            
            # 设置组合输出锁定勾选框为勾选状态
            try:
                self.main_window.last_lock_output = True
                print("设置组合输出锁定状态为: True")
                
                # 直接设置组合输出锁定勾选框控件状态
                if hasattr(self.main_window, 'formula_widget') and self.main_window.formula_widget is not None:
                    if hasattr(self.main_window.formula_widget, 'lock_output_checkbox'):
                        self.main_window.formula_widget.lock_output_checkbox.setChecked(True)
                        print("设置组合输出锁定勾选框为: True")
            except:
                pass
            
            # 恢复选股控件值上下限和勾选状态（参考组合分析的restore_formula_params方法）
            try:
                # 创建临时的公式选股控件来恢复选股参数
                from function.stock_functions import get_abbr_map, get_abbr_logic_map, get_abbr_round_map, FormulaSelectWidget
                import re
                
                abbr_map = get_abbr_map()
                logic_map = get_abbr_logic_map()
                round_map = get_abbr_round_map()
                
                temp_formula_widget = FormulaSelectWidget(abbr_map, logic_map, round_map, self.main_window)
                
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
                    
                    # 清空含逻辑选项
                    if 'logic_check' in widgets:
                        widgets['logic_check'].setChecked(False)
                        print(f"  重置含逻辑选项: {var_name}")
                    
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
                        print(f"  重置比较控件含逻辑选项")
                    print(f"  已重置比较控件")
                
                # 重置forward_param_state中的向前参数控件状态
                if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                    for var_name, var_state in self.main_window.forward_param_state.items():
                        if isinstance(var_state, dict):
                            # 重置enable复选框状态
                            var_state['enable'] = False
                            # 重置round圆框状态
                            var_state['round'] = False
                            # 重置含逻辑选项
                            if 'logic' in var_state:
                                var_state['logic'] = False
                            # 清空上下限值和步长
                            var_state['lower'] = ''
                            var_state['upper'] = ''
                            if 'step' in var_state:
                                var_state['step'] = ''
                            print(f"重置向前参数: {var_name}")
                        elif isinstance(var_state, bool):
                            # 如果只是布尔值，重置为False
                            self.main_window.forward_param_state[var_name] = False
                            print(f"重置向前参数布尔值: {var_name} = False")
                
                # 解析公式并设置控件状态
                if formula:
                    print(f"开始解析公式: {formula}")
                    
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
                    if hasattr(self.main_window, 'forward_param_state') and self.main_window.forward_param_state:
                        forward_widgets = self.main_window.forward_param_state
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
                                # 直接设置控件状态，但需要检查键是否存在
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
                                    if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                        if isinstance(self.main_window.forward_param_state[var], dict):
                                            self.main_window.forward_param_state[var]['enable'] = True
                                            self.main_window.forward_param_state[var]['lower'] = lower
                                            print(f"已更新forward_param_state下限: {var} enable=True, lower={lower}")
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
                                # 直接设置控件状态，但需要检查键是否存在
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
                                    if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                        if isinstance(self.main_window.forward_param_state[var], dict):
                                            self.main_window.forward_param_state[var]['enable'] = True
                                            self.main_window.forward_param_state[var]['upper'] = upper
                                            print(f"已更新forward_param_state上限: {var} enable=True, upper={upper}")
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
                                # 直接设置控件状态，但需要检查键是否存在
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
                                    if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                        if isinstance(self.main_window.forward_param_state[var], dict):
                                            self.main_window.forward_param_state[var]['enable'] = True
                                            print(f"已更新forward_param_state逻辑变量: {var} enable=True")
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
                                # 直接设置圆框控件状态，但需要检查键是否存在
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
                                    if hasattr(self.main_window, 'forward_param_state') and var in self.main_window.forward_param_state:
                                        if isinstance(self.main_window.forward_param_state[var], dict):
                                            self.main_window.forward_param_state[var]['round'] = True
                                            print(f"已更新forward_param_state圆框: {var} = True")
                            else:
                                print(f"result变量 {var} 不在控件列表中")
                    
                    # 5. 处理比较控件
                    from function.stock_functions import get_abbr_map
                    abbr_map = get_abbr_map()  # {中文: 英文}
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
                        
                        # 保存比较控件配置到状态中
                        comparison_state = {
                            'comparison_widgets': comparison_configs
                        }
                        print(f"保存比较控件配置到状态: {comparison_state}")
                        
                        # 获取当前状态并添加比较控件配置
                        current_state = temp_formula_widget.get_state()
                        if comparison_configs:
                            current_state['comparison_widgets'] = comparison_configs
                            print(f"添加比较控件配置到状态中")
                        
                        # 更新主窗口的last_formula_select_state
                        self.main_window.last_formula_select_state = current_state
                        print(f"已保存状态到主窗口: {len(current_state)} 个变量")
                
                # 恢复get_abbr_round_only_map的圆框勾选状态
                selected_vars_with_values = plan.get('params', {}).get('selected_vars_with_values', [])
                print(f"selected_vars_with_values: {selected_vars_with_values}")
                if selected_vars_with_values:
                    from function.stock_functions import get_abbr_round_only_map
                    abbr_round_only_map = get_abbr_round_only_map()
                    # 只处理英文名
                    selected_en_vars = set(var_name for var_name, _ in selected_vars_with_values)
                    for (zh, en), en_val in abbr_round_only_map.items():
                        if en_val in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[en_val]
                            if 'round_checkbox' in widgets:
                                widgets['round_checkbox'].setChecked(en_val in selected_en_vars)
                                print(f"恢复圆框变量 {en_val} 勾选状态: {en_val in selected_en_vars}")
                
                # 恢复n_values输入值（只恢复被勾选的变量）
                n_values = plan.get('params', {}).get('n_values', {})
                if n_values and selected_vars_with_values:
                    print(f"恢复n_values: {n_values}")
                    selected_var_names = set(var_name for var_name, _ in selected_vars_with_values)
                    for var_name, n_value in n_values.items():
                        # 只恢复在selected_vars_with_values中被勾选的变量
                        if var_name in selected_var_names and var_name in temp_formula_widget.var_widgets:
                            widgets = temp_formula_widget.var_widgets[var_name]
                            if 'n_input' in widgets:
                                widgets['n_input'].setText(str(n_value))
                                print(f"恢复n_input变量 {var_name} 输入值: {n_value}")
                
                print("选股控件状态恢复完成")
                
            except Exception as e:
                print(f"恢复选股控件状态失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 显示成功消息
            QMessageBox.information(self, "恢复成功", f"已成功恢复操盘方案参数！\n公式: {formula}\n排序方式: {params.get('last_sort_mode', '')}\n选股数量: {params.get('last_select_count', '')}\n开始日期值选择: {params.get('start_option', '')}\n前移天数: {params.get('shift', '')}\n是否计算向前: {params.get('direction', False)}\n交易方式: {params.get('trade_mode', '')}\n操作值: {params.get('expr', '')}\n开始日到结束日之间最高价/最低价小于: {params.get('range_value', '')}\n开始日到结束日之间连续累加值绝对值小于: {params.get('continuous_abs_threshold', '')}\n开始日到结束日之间有效累加值绝对值小于: {params.get('valid_abs_sum_threshold', '')}\n第1组后N最大值逻辑: {params.get('n_days', '')}\n前1组结束地址后N日的最大值: {params.get('n_days_max', '')}\n操作涨幅: {params.get('ops_change', '')}\n日期宽度: {params.get('width', '')}\n操作天数: {params.get('op_days', '')}\n止盈递增率: {params.get('inc_rate', '')}\n止盈后值大于结束值比例: {params.get('after_gt_end_edit', '')}\n止盈后值大于前值比例: {params.get('after_gt_prev_edit', '')}\n止损递增率: {params.get('stop_loss_inc_rate', '')}\n止损后值大于结束值比例: {params.get('stop_loss_after_gt_end_edit', '')}\n止损后值大于前值比例: {params.get('stop_loss_after_gt_start_edit', '')}")
            
        except Exception as e:
            QMessageBox.critical(self, "恢复失败", f"恢复操盘方案参数失败：{e}")
            print(f"恢复失败详细错误: {e}")
            import traceback
            traceback.print_exc()

    def edit_plan_name(self, idx):
        """编辑操盘方案名称"""
        # 使用排序后的列表来获取正确的plan
        sorted_plan_list = getattr(self.main_window, 'sorted_trading_plan_list', [])
        if 0 <= idx < len(sorted_plan_list):
            plan = sorted_plan_list[idx]
            dialog = PlanNameEditDialog(plan, self)
            if dialog.exec_() == QDialog.Accepted:
                # 更新方案名称
                new_name = dialog.get_plan_name()
                plan['plan_name'] = new_name
                
                # 更新对应的选股结果窗口标题
                if 'result_window' in plan and plan['result_window'] is not None:
                    plan['result_window'].setWindowTitle(f"{new_name} 选股结果")
                
                # 更新原始列表中的plan
                plan_list = getattr(self.main_window, 'trading_plan_list', [])
                # 找到对应的plan并更新
                for original_plan in plan_list:
                    if original_plan.get('plan_id') == plan.get('plan_id'):
                        original_plan['plan_name'] = new_name
                        break
                
                self.main_window.trading_plan_list = plan_list
                self.refresh_cards()
                QMessageBox.information(self, "成功", "方案名称已更新！")

class PlanNameEditDialog(QDialog):
    """操盘方案名称编辑对话框"""
    def __init__(self, plan, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("编辑方案名称")
        self.setFixedSize(300, 120)
        
        layout = QVBoxLayout(self)
        
        # 当前方案信息
        current_name = self.plan.get('plan_name', "操盘方案")
        info_label = QLabel(f"当前方案: {current_name}")
        layout.addWidget(info_label)
        
        # 名称输入
        layout.addWidget(QLabel("新方案名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(current_name)
        self.name_edit.selectAll()  # 自动选中文本
        layout.addWidget(self.name_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
    def get_plan_name(self):
        """获取编辑后的方案名称"""
        return self.name_edit.text().strip()

# 用法示例：
# TradingPlanWidget.clean_plan_for_save(trading_plan_list)  # 在save_config等保存前调用