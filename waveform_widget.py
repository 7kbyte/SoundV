"""
波形可视化窗口 — 全透明、鼠标穿透、常驻桌面左下角
支持两种模式：平滑波形 / 频谱柱状图
特效：Catmull-Rom曲线 · 自动色相 · 光晕背景
"""
import sys
import ctypes
import time as _time

import numpy as np

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient,
    QPen, QBrush, QRadialGradient,
)

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MARGIN_LEFT, WINDOW_MARGIN_BOTTOM,
    DEFAULT_HUE, CENTER_LINE_COLOR,
    FFT_SIZE, NUM_BARS, BAR_SPACING, BAR_MIN_HEIGHT, SMOOTHING,
    AUTO_HUE_SPEED, AUTO_HUE_DELAY,
    GLOW_RADIUS, GLOW_BG_COUNT, GLOW_BG_ALPHA,
    WAVE_AMPLITUDE_RATIO, WAVE_SMOOTH_KERNEL,
    WAVE_GAIN_MIN, WAVE_GAIN_MAX,
    WAVE_LINE_WIDTH,
    WAVE_LINE_SAT, WAVE_LINE_VAL, WAVE_LINE_ALPHA,
    WAVE_GRADIENT_HUE_SPAN,
    WAVE_FILL_HUE_SPAN, WAVE_FILL_ALPHA,
    CATMULL_SUBDIV,
    SAMPLE_RATE,
)
from audio_capture import AudioCapture
from tray_manager import TrayManager
from color_picker import ColorPickerPopup
from settings import load as load_settings, save as save_settings


class WaveformWidget(QWidget):
    """主窗口：集成音频捕获 + 双模式可视化 + 托盘管理"""

    MODE_WAVEFORM = "waveform"
    MODE_SPECTRUM = "spectrum"
    MODE_LABELS = {MODE_WAVEFORM: "📈 波形", MODE_SPECTRUM: "📊 频谱"}

    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._color_picker = None

        # 加载持久化设置
        saved = load_settings()
        self._mode = saved.get("mode", self.MODE_WAVEFORM)
        self._current_hue = saved.get("hue", DEFAULT_HUE)
        self._auto_hue = saved.get("auto_hue", True)
        self._update_colors()
        self._save()  # 确保配置文件存在

        # 音频采集
        self._audio = AudioCapture()

        # 频谱平滑状态
        self._spectrum_smooth = np.zeros(NUM_BARS)

        # ---- 特效状态 ----
        # 自动色相旋转
        self._auto_hue = True
        self._last_manual_hue = _time.time()
        # 波形平滑滚动（消除亚像素抖动）
        self._scroll_phase = 0.0

        # 窗口
        self._setup_window()

        # 托盘
        self._tray = TrayManager(
            parent=self,
            app=app,
            get_hue=lambda: self._current_hue,
            on_hue_changed=self._on_hue_changed,
            show_color_picker=self._show_color_picker,
            toggle_mode=self.toggle_mode,
            get_mode_label=lambda: self.MODE_LABELS[self._mode],
            toggle_auto_hue=self.toggle_auto_hue,
            get_auto_hue_label=lambda: "🔄 自动换色 ✓" if self._auto_hue else "🔄 自动换色 ✗",
        )

        # 启动音频
        self._audio.start()

        # 垂直同步：匹配屏幕刷新率
        screen = QApplication.primaryScreen()
        refresh = screen.refreshRate()
        interval = int(1000 / refresh) if refresh > 0 else 16
        self._frame_interval = interval / 1000.0  # 秒
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(interval)

    # ----------------------------------------------------------
    # 模式 & 特效控制
    # ----------------------------------------------------------
    def _save(self):
        save_settings({
            "hue": int(self._current_hue) % 360,
            "mode": self._mode,
            "auto_hue": self._auto_hue,
        })

    def toggle_mode(self):
        """切换 波形 ↔ 频谱"""
        self._mode = (
            self.MODE_SPECTRUM if self._mode == self.MODE_WAVEFORM
            else self.MODE_WAVEFORM
        )
        self._spectrum_smooth = np.zeros(NUM_BARS)
        self._save()

    def toggle_auto_hue(self):
        """切换自动色相旋转"""
        self._auto_hue = not self._auto_hue
        self._last_manual_hue = _time.time()
        self._save()
        return self._auto_hue

    def _update_auto_hue(self):
        """自动色相旋转"""
        if self._auto_hue and _time.time() - self._last_manual_hue > AUTO_HUE_DELAY:
            self._current_hue = (self._current_hue + AUTO_HUE_SPEED) % 360
            self._update_colors()
            self._tray.refresh_icon()

    # ----------------------------------------------------------
    # 窗口设置
    # ----------------------------------------------------------
    def _setup_window(self):
        self.setWindowTitle("Audio Visualizer")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.left() + WINDOW_MARGIN_LEFT
        y = screen.bottom() - WINDOW_HEIGHT - WINDOW_MARGIN_BOTTOM
        self.setGeometry(x, y, WINDOW_WIDTH, WINDOW_HEIGHT)

        self._make_click_through()

    def _make_click_through(self):
        if sys.platform != "win32":
            return
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOPMOST = 0x00000008
        WS_EX_NOACTIVATE = 0x08000000

        ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = ex_style | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

        HWND_TOPMOST = -1
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        ctypes.windll.user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        )

    # ----------------------------------------------------------
    # 颜色管理
    # ----------------------------------------------------------
    def _update_colors(self):
        h = int(self._current_hue) % 360
        self._waveform_color = QColor.fromHsv(h, 200, 230, 220)
        self._waveform_glow  = QColor.fromHsv(h, 180, 220, 80)
        self._gradient_top   = QColor.fromHsv(h, 150, 200, 0)    # 边缘全透明
        self._gradient_mid   = QColor.fromHsv(h, 200, 210, 100)  # 中间可见
        # 频谱柱颜色
        self._bar_color     = QColor.fromHsv(h, 200, 230, 210)
        self._bar_glow      = QColor.fromHsv(h, 180, 220, 50)
        self._bar_grad_top  = QColor.fromHsv(h, 150, 200, 40)
        self._bar_grad_bot  = QColor.fromHsv(h, 200, 210, 120)

    def _on_hue_changed(self, hue: int):
        self._current_hue = int(hue)
        self._last_manual_hue = _time.time()
        self._update_colors()
        self._tray.refresh_icon()
        self._save()

    def _show_color_picker(self):
        if self._color_picker is not None:
            self._color_picker.close()
            self._color_picker = None
        QTimer.singleShot(150, self._do_show_color_picker)

    def _do_show_color_picker(self):
        self._color_picker = ColorPickerPopup(self._current_hue)
        self._color_picker.hueChanged.connect(self._on_hue_changed)
        self._color_picker.destroyed.connect(
            lambda: setattr(self, '_color_picker', None)
        )
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self._color_picker.width() - 20
        y = screen.bottom() - self._color_picker.height() - 60
        self._color_picker.move(x, y)
        self._color_picker.show()

    # ----------------------------------------------------------
    # 绘制调度
    # ----------------------------------------------------------
    def paintEvent(self, event):
        # 特效更新
        self._update_auto_hue()

        if self._mode == self.MODE_WAVEFORM:
            self._paint_waveform()
        else:
            self._paint_spectrum()

    # ==========================================================
    # 模式 A：平滑波形 + Catmull-Rom + 光晕 + 闪光
    # ==========================================================
    def _paint_waveform(self):
        samples = self._audio.snapshot()
        if len(samples) < 2:
            return

        w, h = self.width(), self.height()
        if w <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        mid_y = h / 2.0
        amplitude = h * WAVE_AMPLITUDE_RATIO

        # 双重平滑：先均值滤波，再高斯加权滤波
        kernel = np.ones(WAVE_SMOOTH_KERNEL) / WAVE_SMOOTH_KERNEL
        smoothed = np.convolve(samples, kernel, mode='same')
        # 二次平滑：用更宽的窗口去除残留高频
        kernel2 = np.ones(WAVE_SMOOTH_KERNEL * 2) / (WAVE_SMOOTH_KERNEL * 2)
        smoothed = np.convolve(smoothed, kernel2, mode='same')

        # 自适应增益：追踪近 0.5 秒峰值，动态放大
        chunk = samples[-22050:] if len(samples) > 22050 else samples
        chunk_max = max((abs(s) for s in chunk), default=0.01)
        gain = 1.0 / max(chunk_max, WAVE_GAIN_MIN)
        gain = min(gain, WAVE_GAIN_MAX)

        step = max(1.0, len(smoothed) / w)
        # 亚像素滚动对齐：基于帧间隔估算每帧推进的像素数
        samples_per_frame = SAMPLE_RATE * self._frame_interval
        self._scroll_phase = (self._scroll_phase + samples_per_frame / step) % 1.0
        phase_offset = self._scroll_phase * step

        raw_pts = []
        for px in range(w + 1):
            idx = min(int(px * step + phase_offset), len(smoothed) - 1)
            y_off = smoothed[idx] * amplitude * gain
            # 裁剪避免溢出
            y_off = max(-mid_y + 1, min(mid_y - 1, y_off))
            raw_pts.append((float(px), float(mid_y - y_off)))

        # ---- 光晕背景 ----
        self._paint_glow_bg(painter, raw_pts, w, h, mid_y)

        # ---- Catmull-Rom 平滑曲线 ----
        curve_pts = self._catmull_rom_curve(raw_pts)

        # 中线
        painter.setPen(QPen(CENTER_LINE_COLOR, 1.0))
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        # 主体线 — 从左到右色相渐变
        self._draw_gradient_polyline(painter, curve_pts, w)

        painter.end()

    def _paint_glow_bg(self, painter, pts, w, h, mid_y):
        """在波形峰值处绘制径向光晕"""
        if len(pts) < 10:
            return
        # 取最高波峰
        indexed = sorted(enumerate(pts), key=lambda x: -x[1][1])[:GLOW_BG_COUNT]
        for _, (gx, gy) in indexed:
            r = GLOW_RADIUS
            radial = QRadialGradient(gx, gy, r)
            glow_col = QColor(
                self._waveform_glow.red(),
                self._waveform_glow.green(),
                self._waveform_glow.blue(),
                GLOW_BG_ALPHA,
            )
            radial.setColorAt(0.0, glow_col)
            radial.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(radial))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(gx - r), int(gy - r), int(r * 2), int(r * 2))

    # ==========================================================
    # Catmull-Rom 样条插值
    # ==========================================================
    @staticmethod
    def _catmull_rom(p0, p1, p2, p3, t):
        """四点 Catmull-Rom 插值，t ∈ [0, 1]"""
        t2, t3 = t * t, t * t * t
        x = 0.5 * ((2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
        y = 0.5 * ((2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
        return (x, y)

    def _catmull_rom_curve(self, pts, subdiv=CATMULL_SUBDIV):
        """对点列表做 Catmull-Rom 平滑，返回细分后的曲线点"""
        if len(pts) < 4:
            return pts
        result = [pts[0]]
        for i in range(len(pts) - 3):
            p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
            for j in range(1, subdiv + 1):
                t = j / (subdiv + 1)
                result.append(self._catmull_rom(p0, p1, p2, p3, t))
        result.append(pts[-1])
        return result

    # ==========================================================
    # 模式 B：频谱柱状图 + 彩虹渐变 + 闪光
    # ==========================================================
    def _paint_spectrum(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # ---- 1. FFT ----
        chunk = self._audio.get_fft_chunk()
        window = np.hanning(FFT_SIZE)
        spectrum = np.abs(np.fft.rfft(chunk * window))
        freqs = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)

        # ---- 2. 对数频率分组 ----
        bar_values = np.zeros(NUM_BARS)
        min_freq, max_freq = 30.0, 18000.0
        log_min, log_max = np.log10(min_freq), np.log10(max_freq)
        bin_edges = np.logspace(log_min, log_max, NUM_BARS + 1)

        for i in range(NUM_BARS):
            mask = (freqs >= bin_edges[i]) & (freqs < bin_edges[i + 1])
            if np.any(mask):
                bar_values[i] = np.mean(spectrum[mask])

        # ---- 3. 归一化 + 压缩 + 平滑 ----
        max_val = np.max(bar_values)
        if max_val > 1e-6:
            bar_values = bar_values / max_val
        bar_values = np.power(bar_values, 0.5)

        self._spectrum_smooth = (
            self._spectrum_smooth * SMOOTHING
            + bar_values * (1.0 - SMOOTHING)
        )

        # ---- 4. 绘制柱子（彩虹渐变） ----
        w, h = self.width(), self.height()
        total_spacing = BAR_SPACING * (NUM_BARS - 1)
        bar_w = max((w - 20 - total_spacing) / NUM_BARS, 2)
        base_y = h - 2

        for i, val in enumerate(self._spectrum_smooth):
            val = max(val, 0.001)
            bar_h_px = max(int(val * (h - 8)), BAR_MIN_HEIGHT)
            x = 10 + i * (bar_w + BAR_SPACING)
            y = base_y - bar_h_px

            # 彩虹色：低频红 → 高频紫
            hue = (self._current_hue + i * 360 / NUM_BARS) % 360
            bar_col = QColor.fromHsv(int(hue), 220, 240, 200)
            bar_glow_col = QColor.fromHsv(int(hue), 200, 240, 50)

            # 发光底层
            painter.setPen(Qt.NoPen)
            painter.setBrush(bar_glow_col)
            painter.drawRoundedRect(
                int(x - 1), int(y - 1),
                int(bar_w + 2), int(bar_h_px + 2), 2, 2,
            )

            # 渐变主体
            grad = QLinearGradient(0, y, 0, base_y)
            grad.setColorAt(0.0, bar_col)
            grad.setColorAt(1.0, QColor.fromHsv(int(hue), 180, 200, 100))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(
                int(x), int(y), int(bar_w), int(bar_h_px), 2, 2,
            )

        # 底部基线
        painter.setPen(QPen(CENTER_LINE_COLOR, 1.0))
        painter.drawLine(0, base_y, w, base_y)

        painter.end()

    # ----------------------------------------------------------
    # 共用工具
    # ----------------------------------------------------------
    @staticmethod
    def _draw_polyline(painter, points):
        for i in range(len(points) - 1):
            painter.drawLine(
                int(points[i][0]), int(points[i][1]),
                int(points[i + 1][0]), int(points[i + 1][1]),
            )

    def _draw_gradient_polyline(self, painter, points, total_w):
        """绘制从左到右色相渐变的折线"""
        h_base = int(self._current_hue) % 360
        hue_span = WAVE_GRADIENT_HUE_SPAN
        for i in range(len(points) - 1):
            x = (points[i][0] + points[i + 1][0]) / 2.0
            ratio = x / max(total_w, 1)
            hue = (h_base - hue_span // 2 + int(ratio * hue_span)) % 360
            seg_color = QColor.fromHsv(hue, WAVE_LINE_SAT, WAVE_LINE_VAL, WAVE_LINE_ALPHA)
            painter.setPen(QPen(seg_color, WAVE_LINE_WIDTH))
            painter.drawLine(
                int(points[i][0]), int(points[i][1]),
                int(points[i + 1][0]), int(points[i + 1][1]),
            )

    # ----------------------------------------------------------
    # 生命周期
    # ----------------------------------------------------------
    def _stop_audio_capture(self):
        self._audio.stop()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._tray.notify_hidden()
