from PyQt5.QtWidgets import QDialog, QLineEdit, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class TableSearchDialog(QDialog):
    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table
        self.setWindowTitle('表格搜索')
        self.setWindowModality(Qt.NonModal)
        self.setFixedWidth(350)
        self.match_indices = []  # [(row, col), ...]
        self.current_match_idx = -1
        self.last_search_text = ''

        self.input = QLineEdit(self)
        self.input.setPlaceholderText('输入要查找的内容...')
        self.input.returnPressed.connect(self.do_search)

        self.label = QLabel('')
        self.btn_search = QPushButton('查找')
        self.btn_prev = QPushButton('上一个')
        self.btn_next = QPushButton('下一个')
        self.btn_search.clicked.connect(self.do_search)
        self.btn_prev.clicked.connect(self.goto_prev)
        self.btn_next.clicked.connect(self.goto_next)

        hbox = QHBoxLayout()
        hbox.addWidget(self.input)
        hbox.addWidget(self.btn_search)
        hbox.addWidget(self.btn_prev)
        hbox.addWidget(self.btn_next)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.label)
        self.setLayout(vbox)

    def do_search(self):
        text = self.input.text()
        self.clear_highlight()
        self.match_indices = []
        self.current_match_idx = -1
        if not text:
            self.label.setText('')
            return
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text():
                    self.match_indices.append((row, col))
        if self.match_indices:
            self.current_match_idx = 0
            self.goto_match(self.current_match_idx)
            self.update_label()
        else:
            self.label.setText('未找到相关内容。')

    def goto_match(self, idx):
        if not self.match_indices:
            return
        # 清除之前的高亮
        self.clear_highlight()
        # 高亮当前匹配项
        row, col = self.match_indices[idx]
        item = self.table.item(row, col)
        if item:
            item.setBackground(QColor(255, 255, 0))  # 黄色高亮
        self.table.setCurrentCell(row, col)
        self.table.scrollToItem(self.table.item(row, col), QAbstractItemView.PositionAtCenter)
        self.update_label()

    def goto_next(self):
        if not self.match_indices:
            return
        self.current_match_idx = (self.current_match_idx + 1) % len(self.match_indices)
        self.goto_match(self.current_match_idx)

    def goto_prev(self):
        if not self.match_indices:
            return
        self.current_match_idx = (self.current_match_idx - 1) % len(self.match_indices)
        self.goto_match(self.current_match_idx)

    def update_label(self):
        if not self.match_indices:
            self.label.setText('')
        else:
            self.label.setText(f'共 {len(self.match_indices)} 项，当前第 {self.current_match_idx + 1} 项')

    def highlight_matches(self):
        # 这个方法现在不再使用，因为我们在goto_match中直接处理高亮
        pass

    def clear_highlight(self):
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(Qt.white))

    def closeEvent(self, event):
        self.clear_highlight()
        event.accept() 