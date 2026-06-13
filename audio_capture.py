"""
系统音频捕获模块 — WASAPI Loopback
"""
import threading
import time
from collections import deque

import numpy as np
import soundcard as sc

from config import SAMPLE_RATE, BLOCK_SIZE, DISPLAY_SAMPLES, FFT_SIZE


class AudioCapture:
    """在独立线程中通过 WASAPI Loopback 捕获系统播放的音频"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._mic = None
        self._recorder = None
        self._lock = threading.Lock()

        # 环形缓冲区 — 足够容纳波形和 FFT 所需的采样
        buf_size = max(DISPLAY_SAMPLES, FFT_SIZE) + BLOCK_SIZE
        self.buffer = deque([0.0] * buf_size, maxlen=buf_size)

    # ----------------------------------------------------------
    # 设备发现
    # ----------------------------------------------------------
    def _find_loopback_mic(self):
        """查找默认扬声器的 Loopback 设备"""
        try:
            default_sp = sc.default_speaker()
            print(f"[音频] 默认扬声器: {default_sp.name}")
            loopback_mic = sc.get_microphone(
                default_sp.id, include_loopback=True
            )
            print(f"[音频] Loopback 设备: {loopback_mic.name}")
            return loopback_mic
        except Exception as e:
            print(f"[音频] 未找到 Loopback 设备: {e}")

        try:
            for mic in sc.all_microphones(include_loopback=True):
                if mic.isloopback:
                    print(f"[音频] 使用 Loopback: {mic.name}")
                    return mic
        except Exception:
            pass
        return None

    # ----------------------------------------------------------
    # 采集循环
    # ----------------------------------------------------------
    def _capture_loop(self):
        try:
            with self._mic.recorder(
                samplerate=SAMPLE_RATE, channels=1
            ) as self._recorder:
                print("[音频] 系统音频捕获已启动（WASAPI Loopback）")
                while self._running:
                    try:
                        data = self._recorder.record(numframes=BLOCK_SIZE)
                        mono = data[:, 0] if data.ndim > 1 else data
                        with self._lock:
                            self.buffer.extend(mono.tolist())
                    except Exception as e:
                        if self._running:
                            print(f"[音频] 读取警告: {e}")
                        time.sleep(0.01)
        except Exception as e:
            print(f"[音频] 采集线程异常: {e}")
        finally:
            print("[音频] 采集线程已退出")

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------
    def start(self):
        """启动音频采集"""
        self._mic = self._find_loopback_mic()
        if self._mic is None:
            print("[错误] 无法找到系统音频 Loopback 设备！")
            try:
                all_mics = sc.all_microphones()
                if all_mics:
                    self._mic = all_mics[0]
                    print(f"[音频] 回退使用麦克风: {self._mic.name}")
            except Exception as e:
                print(f"[错误] 无法使用任何音频设备: {e}")
                return

        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True, name="AudioCapture",
        )
        self._thread.start()

    def stop(self):
        """停止音频采集"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        self._recorder = None
        self._mic = None

    def snapshot(self, count: int = None) -> list:
        """获取缓冲区内最近 count 个采样（线程安全）"""
        with self._lock:
            data = list(self.buffer)
        if count is not None and count < len(data):
            return data[-count:]
        return data

    def get_fft_chunk(self) -> np.ndarray:
        """获取最近 FFT_SIZE 个采样，作为 float32 numpy 数组"""
        with self._lock:
            data = list(self.buffer)
        chunk = data[-FFT_SIZE:] if len(data) >= FFT_SIZE else data
        # 补零对齐
        arr = np.zeros(FFT_SIZE, dtype=np.float32)
        arr[:len(chunk)] = chunk
        return arr
