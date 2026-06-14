"""
设置持久化模块 — JSON 文件存储
"""
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULTS = {
    "hue": 175,         # 色相 0-359
    "mode": "waveform", # "waveform" | "spectrum"
    "auto_hue": True,   # 自动色相旋转
}


def load() -> dict:
    """从文件加载设置，缺失则返回默认值"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 补全缺失的键
            for key, val in DEFAULTS.items():
                data.setdefault(key, val)
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return DEFAULTS.copy()


def save(data: dict):
    """保存设置到文件"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[设置] 保存失败: {e}")
