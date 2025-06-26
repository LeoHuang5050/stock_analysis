"""
通用UI组件模块
包含可复用的UI组件
"""

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QGuiApplication


class CopyableTableWidget(QTableWidget):
    """可复制的表格组件"""
    
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copySelection()
        else:
            super().keyPressEvent(event)

    def copySelection(self):
        """复制选中的内容到剪贴板"""
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