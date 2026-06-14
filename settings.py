"""
设置持久化模块 — JSON 文件存储于 %APPDATA%
"""
import json
import os

# 存储路径：%APPDATA%\AudioVisualizer\settings.json
APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AudioVisualizer")
os.makedirs(APP_DIR, exist_ok=True)
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

DEFAULTS = {
    "hue": 175,         # 色相 0-359
    "mode": "waveform", # "waveform" | "spectrum"
    "auto_hue": False,  # 自动色相旋转（默认关闭）
}


def load() -> dict:
    """从文件加载设置，缺失则返回默认值"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 类型强制转换，防止 JSON 类型偏差
            result = {}
            result["hue"] = int(data.get("hue", DEFAULTS["hue"])) % 360
            result["mode"] = str(data.get("mode", DEFAULTS["mode"]))
            result["auto_hue"] = bool(data.get("auto_hue", DEFAULTS["auto_hue"]))
            return result
    except (json.JSONDecodeError, IOError, ValueError):
        pass
    return DEFAULTS.copy()


def save(data: dict):
    """保存设置到文件"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[设置] 保存失败: {e}")
