"""
程序入口 — 桌面音频波形可视化器
"""
import sys
import warnings
import os

# 强力抑制所有警告
warnings.simplefilter("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, qInstallMessageHandler

from config import _qt_message_handler
from waveform_widget import WaveformWidget


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    widget = WaveformWidget(app)
    widget.show()

    print("=" * 50)
    print("  桌面音频波形可视化器 已启动")
    print("  波形显示在桌面左下角 — 全透明 + 鼠标穿透")
    print("  右键点击右下角托盘图标可隐藏/退出")
    print("=" * 50)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
