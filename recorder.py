"""
業務モニター - 記録スクリプト（従業員PC用）
10分ごとにスクリーンショット + PCアクティビティログをGoogle Driveに保存

=== セットアップ ===
1. pip install Pillow pynput
2. 下の設定を従業員ごとに変更
3. pythonw.exe recorder.py で起動（完全バックグラウンド）

=== 自動起動の設定 ===
1. Win+R → shell:startup
2. ショートカットを作成:
   対象: pythonw.exe "C:\path\to\recorder.py"
"""

import os
import json
import time
import ctypes
import ctypes.wintypes
import threading
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 設定（従業員ごとに変更）
# ============================================================
EMPLOYEE_NAME = "田中美咲"          # 従業員名
INTERVAL_MINUTES = 10               # 記録間隔（分）
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")  # Google Driveのパス
# ============================================================

SAVE_DIR = GDRIVE_BASE / EMPLOYEE_NAME


def get_active_window_title() -> str:
    """アクティブウィンドウのタイトルを取得"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value if buf.value else "(不明)"
    except Exception:
        return "(取得失敗)"


def get_active_process_name() -> str:
    """アクティブウィンドウのプロセス名を取得"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if handle:
            buf = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size)
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            return Path(buf.value).name if buf.value else "(不明)"
    except Exception:
        pass
    return "(取得失敗)"


class ActivityTracker:
    """キーボード・マウスの操作有無を追跡"""

    def __init__(self):
        self.keyboard_count = 0
        self.mouse_count = 0
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        try:
            from pynput import keyboard, mouse

            def on_key(key):
                with self._lock:
                    self.keyboard_count += 1

            def on_move(x, y):
                with self._lock:
                    self.mouse_count += 1

            def on_click(x, y, button, pressed):
                with self._lock:
                    self.mouse_count += 1

            kl = keyboard.Listener(on_press=on_key)
            ml = mouse.Listener(on_move=on_move, on_click=on_click)
            kl.daemon = True
            ml.daemon = True
            kl.start()
            ml.start()
        except ImportError:
            pass  # pynputがなくても動作する（操作ログなしで）

    def get_and_reset(self) -> dict:
        with self._lock:
            result = {
                "keyboard_events": self.keyboard_count,
                "mouse_events": self.mouse_count,
            }
            self.keyboard_count = 0
            self.mouse_count = 0
        return result


def take_screenshot(save_path: str) -> bool:
    """スクリーンショットを撮影して保存"""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        # JPEG で保存（PNGより軽い→Google Drive同期が速い）
        img.save(save_path, "JPEG", quality=70, optimize=True)
        return True
    except Exception:
        return False


def record_snapshot(tracker: ActivityTracker):
    """1回分の記録を取得・保存"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    # 日付ごとのディレクトリ
    day_dir = SAVE_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    # スクリーンショット保存（JPEG）
    screenshot_filename = f"ss_{time_str}.jpg"
    screenshot_path = day_dir / screenshot_filename
    screenshot_ok = take_screenshot(str(screenshot_path))

    # ログデータ収集
    activity = tracker.get_and_reset()
    log_entry = {
        "timestamp": now.isoformat(),
        "employee": EMPLOYEE_NAME,
        "active_window": get_active_window_title(),
        "process_name": get_active_process_name(),
        "keyboard_events": activity["keyboard_events"],
        "mouse_events": activity["mouse_events"],
        "screenshot_file": screenshot_filename if screenshot_ok else None,
    }

    # ログファイルに追記（JSONLines形式）
    log_file = day_dir / "activity_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def write_error_log(msg: str):
    """エラーログ（トラブル対応用）"""
    try:
        err_file = SAVE_DIR / "error.log"
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(err_file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    tracker = ActivityTracker()
    tracker.start()

    while True:
        try:
            record_snapshot(tracker)
        except Exception as e:
            write_error_log(str(e))
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
