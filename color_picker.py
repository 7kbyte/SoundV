"""
彩虹色选择弹窗 — 拖拽选色 + 确认按钮
"""
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QBrush, QFont,
)


class ColorPickerPopup(QWidget):
    """彩虹色条弹出选择器"""

    hueChanged = pyqtSignal(int)   # 色相变化 (0-359)
    confirmed = pyqtSignal()       # 用户点击确认

    def __init__(self, current_hue: int = 175, parent=None):
        super().__init__(parent)
        self._hue = int(current_hue) % 360
        self._dragging = False
        self._bar_height = 28
        self._bar_margin = 12
        self._confirm_height = 22

        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(300, 62)

    # ----------------------------------------------------------
    # 绘制
    # ----------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = self.width()
        bar_x = self._bar_margin
        bar_y = 10
        bar_w = w - self._bar_margin * 2
        bar_h = self._bar_height

        # 彩虹渐变条
        gradient = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
        for i in range(7):
            hue = int(i * 60)
            gradient.setColorAt(i / 6.0, QColor.fromHsv(hue, 255, 255))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 4, 4)

        # 当前选中指示器
        ratio = self._hue / 359.0
        cx = bar_x + int(bar_w * ratio)

        pen = QPen(QColor(255, 255, 255, 220), 2)
        painter.setPen(pen)
        painter.drawLine(cx, bar_y - 1, cx, bar_y + bar_h + 1)

        painter.setBrush(QBrush(QColor.fromHsv(self._hue, 255, 255)))
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1))
        tri = [QPoint(cx - 6, 0), QPoint(cx + 6, 0), QPoint(cx, bar_y - 2)]
        painter.drawPolygon(*tri)

        # 确认按钮
        btn_y = bar_y + bar_h + 4
        btn_h = self._confirm_height
        btn_w = w - self._bar_margin * 2

        btn_color = QColor.fromHsv(self._hue, 200, 210, 180)
        painter.setBrush(QBrush(btn_color))
        painter.setPen(QPen(QColor.fromHsv(self._hue, 200, 255, 100), 1))
        painter.drawRoundedRect(bar_x, btn_y, btn_w, btn_h, 4, 4)

        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 240))
        painter.drawText(
            bar_x, btn_y, btn_w, btn_h,
            Qt.AlignCenter, "✓  点 击 确 认",
        )

        painter.end()

    # ----------------------------------------------------------
    # 鼠标交互
    # ----------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.pos()
        bar_y = 10
        btn_y = bar_y + self._bar_height + 4
        if pos.y() >= btn_y:
            self.confirmed.emit()
            self.close()
            return
        self._dragging = True
        self._update_hue_from_pos(pos.x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_hue_from_pos(event.pos().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def focusOutEvent(self, event):
        self.close()

    def _update_hue_from_pos(self, x: int):
        bar_x = self._bar_margin
        bar_w = self.width() - self._bar_margin * 2
        ratio = max(0.0, min(1.0, (x - bar_x) / bar_w))
        new_hue = int(ratio * 359)
        if new_hue != self._hue:
            self._hue = new_hue
            self.hueChanged.emit(self._hue)
            self.update()
