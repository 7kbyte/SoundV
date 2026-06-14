"""
系统托盘管理模块 — 图标、右键菜单、显示/隐藏/退出
"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush


class TrayManager:
    """管理右下角系统托盘图标及右键菜单"""

    def __init__(self, parent, app, get_hue, on_hue_changed,
                 show_color_picker, toggle_mode, get_mode_label,
                 toggle_auto_hue, get_auto_hue_label):
        """
        参数：
          parent              — 父级 QWidget
          app                 — QApplication
          get_hue             — () -> int
          on_hue_changed      — (int) -> None
          show_color_picker   — () -> None
          toggle_mode         — () -> None
          get_mode_label      — () -> str
          toggle_auto_hue     — () -> bool  返回切换后的状态
          get_auto_hue_label  — () -> str
        """
        self._parent = parent
        self._app = app
        self._get_hue = get_hue
        self._on_hue_changed = on_hue_changed
        self._show_color_picker = show_color_picker
        self._toggle_mode = toggle_mode
        self._get_mode_label = get_mode_label
        self._toggle_auto_hue = toggle_auto_hue
        self._get_auto_hue_label = get_auto_hue_label

        self._tray_icon = QSystemTrayIcon(parent)
        self._tray_menu = QMenu(parent)
        self._toggle_action = None
        self._mode_action = None
        self._auto_hue_action = None
        self._color_action = None
        self._exit_action = None

        self._setup()

    # ----------------------------------------------------------
    # 图标绘制
    # ----------------------------------------------------------
    def _create_icon(self) -> QIcon:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)

        bg = QColor.fromHsv(int(self._get_hue()) % 360, 200, 210)
        p.setBrush(QBrush(bg))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)

        pen = QPen(QColor(255, 255, 255), 2.5)
        p.setPen(pen)
        mid_y = 16
        for x, dy in [(7, -5), (13, -10), (19, 8), (25, -3)]:
            p.drawLine(x, mid_y, x, mid_y + dy)

        p.end()
        return QIcon(pixmap)

    def refresh_icon(self):
        """刷新托盘图标颜色"""
        if self._tray_icon is not None:
            self._tray_icon.setIcon(self._create_icon())

    # ----------------------------------------------------------
    # 菜单构建
    # ----------------------------------------------------------
    def _setup(self):
        self._tray_icon.setIcon(self._create_icon())
        self._tray_icon.setToolTip("音频波形可视化器")

        # 显示/隐藏
        self._toggle_action = QAction(
            "🔇 隐藏波形" if self._parent.isVisible() else "🔊 显示波形",
            self._parent,
        )
        self._toggle_action.triggered.connect(self._toggle_visibility)
        self._tray_menu.addAction(self._toggle_action)

        # 切换模式
        self._mode_action = QAction(self._get_mode_label(), self._parent)
        self._mode_action.triggered.connect(self._on_toggle_mode)
        self._tray_menu.addAction(self._mode_action)

        # 自动换色
        self._auto_hue_action = QAction(self._get_auto_hue_label(), self._parent)
        self._auto_hue_action.triggered.connect(self._on_toggle_auto_hue)
        self._tray_menu.addAction(self._auto_hue_action)

        self._tray_menu.addSeparator()

        # 波形颜色
        self._color_action = QAction("🎨 波形颜色...", self._parent)
        self._color_action.triggered.connect(self._show_color_picker)
        self._tray_menu.addAction(self._color_action)
        self._tray_menu.addSeparator()

        # 关闭插件
        self._exit_action = QAction("❌ 关闭插件", self._parent)
        self._exit_action.triggered.connect(self._quit)
        self._tray_menu.addAction(self._exit_action)

        self._tray_icon.setContextMenu(self._tray_menu)
        self._tray_icon.activated.connect(self._on_activated)
        self._tray_icon.show()

    # ----------------------------------------------------------
    # 交互
    # ----------------------------------------------------------
    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_visibility()

    def _toggle_visibility(self):
        if self._parent.isVisible():
            self._parent.hide()
            self._toggle_action.setText("🔊 显示波形")
        else:
            self._parent.show()
            self._toggle_action.setText("🔇 隐藏波形")

    def _on_toggle_mode(self):
        self._toggle_mode()
        self._mode_action.setText(self._get_mode_label())

    def _on_toggle_auto_hue(self):
        active = self._toggle_auto_hue()
        self._auto_hue_action.setText(self._get_auto_hue_label())

    def notify_hidden(self):
        """弹出"已最小化到托盘"提示"""
        self._toggle_action.setText("🔊 显示波形")
        self._tray_icon.showMessage(
            "音频可视化器",
            "已最小化到系统托盘，右键托盘图标可退出。",
            QSystemTrayIcon.Information,
            2000,
        )

    def _quit(self):
        """完全退出"""
        self._parent._save()
        self._parent._stop_audio_capture()
        self._tray_icon.hide()
        self._app.quit()
