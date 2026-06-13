"""
常量配置模块
"""
from PyQt5.QtGui import QColor

# ---- 音频参数 ----
SAMPLE_RATE = 44100          # 采样率
BLOCK_SIZE = 512             # 每次采集的采样块大小（越小延迟越低）
DISPLAY_DURATION = 0.15      # 显示时长（秒）— 越长变化越慢
DISPLAY_SAMPLES = int(SAMPLE_RATE * DISPLAY_DURATION)

# ---- 频谱参数 ----
FFT_SIZE = 2048              # FFT 窗口大小
NUM_BARS = 48                # 频谱柱子数量
BAR_SPACING = 2              # 柱子间距（像素）
BAR_MIN_HEIGHT = 2           # 最小高度（静音时微动）
SMOOTHING = 0.75             # 指数平滑系数（越大越平滑，0-1）

# ---- 窗口参数 ----
WINDOW_WIDTH = 360
WINDOW_HEIGHT = 100
WINDOW_MARGIN_LEFT = 12
WINDOW_MARGIN_BOTTOM = 50

# ---- 颜色 ----
DEFAULT_HUE = 175            # 默认色相：青色
CENTER_LINE_COLOR = QColor(255, 255, 255, 30)

# ---- 特效：自动色相旋转 ----
AUTO_HUE_SPEED = 0.04        # 自动旋转速度（度/帧 @60fps）
AUTO_HUE_DELAY = 5.0         # 手动选色后暂停秒数

# ---- 特效：光晕 ----
GLOW_RADIUS = 60             # 光晕半径（像素）
GLOW_BG_COUNT = 3            # 光晕数量（取波峰数）
GLOW_BG_ALPHA = 30           # 光晕背景透明度

# ---- 波形样式：振幅 ----
WAVE_AMPLITUDE_RATIO = 0.55  # 基础振幅（占窗口高度比例）
WAVE_SMOOTH_KERNEL = 9       # 滑动均值窗口大小（越大越平滑）
WAVE_GAIN_MIN = 0.05         # 自适应增益静音阈值
WAVE_GAIN_MAX = 4.0          # 自适应增益上限

# ---- 波形样式：线条 ----
WAVE_GLOW_WIDTHS = [(4.0, 50), (2.5, 70)]  # (线宽, 透明度) 发光层
WAVE_LINE_WIDTH = 2.8        # 主体线宽
WAVE_LINE_SAT = 220          # 主体线饱和度
WAVE_LINE_VAL = 245          # 主体线亮度
WAVE_LINE_ALPHA = 230        # 主体线透明度
WAVE_GRADIENT_HUE_SPAN = 150 # 左右色相跨度

# ---- 波形样式：填充 ----
WAVE_FILL_HUE_SPAN = 30      # 填充水平渐变色相跨度
WAVE_FILL_ALPHA = 10         # 填充水平渐变透明度

# ---- Catmull-Rom ----
CATMULL_SUBDIV = 3           # 曲线细分倍数


# ---- Qt 消息过滤 ----
def _qt_message_handler(mode, context, message):
    """过滤掉无影响的 OleInitialize 警告"""
    if "OleInitialize" not in message:
        print(f"[Qt] {message}")
