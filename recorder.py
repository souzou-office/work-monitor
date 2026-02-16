"""
Work Monitor - Recorder (Employee PC)
- Screenshot every 10 min + activity log
- Window switch tracking (every 2 sec)
- Keystroke count + character count (content not recorded)
- Only records during work hours (9:00-23:00)

Setup:
1. pip install Pillow pynput
2. Edit settings below per employee
3. pythonw.exe recorder.py for background mode
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
# Settings (change per employee)
# ============================================================
EMPLOYEE_NAME = "池田龍太"
INTERVAL_MINUTES = 10
WINDOW_CHECK_SECONDS = 2
WORK_START_HOUR = 9
WORK_END_HOUR = 23
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
# ============================================================

SAVE_DIR = GDRIVE_BASE / EMPLOYEE_NAME


def is_work_hours() -> bool:
    now = datetime.now()
    return WORK_START_HOUR <= now.hour < WORK_END_HOUR


def get_active_window_title() -> str:
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value if buf.value else "(不明)"
    except Exception:
        return "(取得失敗)"


def get_active_process_name() -> str:
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
    def __init__(self):
        self.keyboard_count = 0
        self.mouse_count = 0
        self.char_count = 0      # printable character count
        self.delete_count = 0    # backspace/delete count
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True
        try:
            from pynput import keyboard, mouse
            from pynput.keyboard import Key

            def on_key(key):
                with self._lock:
                    self.keyboard_count += 1
                    try:
                        if hasattr(key, 'char') and key.char is not None:
                            self.char_count += 1
                        elif key == Key.backspace or key == Key.delete:
                            self.delete_count += 1
                    except Exception:
                        pass

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
            pass

    def get_and_reset(self) -> dict:
        with self._lock:
            result = {
                "keyboard_events": self.keyboard_count,
                "mouse_events": self.mouse_count,
                "char_count": self.char_count,
                "delete_count": self.delete_count,
            }
            self.keyboard_count = 0
            self.mouse_count = 0
            self.char_count = 0
            self.delete_count = 0
        return result


class WindowWatcher:
    def __init__(self):
        self._last_window = ""
        self._last_process = ""
        self._running = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._watch_loop, daemon=True)
        t.start()

    def _watch_loop(self):
        while self._running:
            try:
                if not is_work_hours():
                    time.sleep(WINDOW_CHECK_SECONDS)
                    continue

                current_window = get_active_window_title()
                current_process = get_active_process_name()

                if current_window != self._last_window or current_process != self._last_process:
                    if current_window and current_window != "(不明)" and current_window != "(取得失敗)":
                        self._log_switch(current_window, current_process)
                    self._last_window = current_window
                    self._last_process = current_process

            except Exception:
                pass

            time.sleep(WINDOW_CHECK_SECONDS)

    def _log_switch(self, window_title: str, process_name: str):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")

        day_dir = SAVE_DIR / date_str
        day_dir.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "type": "window_switch",
            "timestamp": now.isoformat(),
            "employee": EMPLOYEE_NAME,
            "active_window": window_title,
            "process_name": process_name,
        }

        log_file = day_dir / "window_log.jsonl"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


def take_screenshot(save_path: str) -> bool:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(save_path, "JPEG", quality=70, optimize=True)
        return True
    except Exception:
        return False


def record_snapshot(tracker: ActivityTracker):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")

    day_dir = SAVE_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    screenshot_filename = f"ss_{time_str}.jpg"
    screenshot_path = day_dir / screenshot_filename
    screenshot_ok = take_screenshot(str(screenshot_path))

    activity = tracker.get_and_reset()
    log_entry = {
        "type": "snapshot",
        "timestamp": now.isoformat(),
        "employee": EMPLOYEE_NAME,
        "active_window": get_active_window_title(),
        "process_name": get_active_process_name(),
        "keyboard_events": activity["keyboard_events"],
        "mouse_events": activity["mouse_events"],
        "char_count": activity["char_count"],
        "delete_count": activity["delete_count"],
        "screenshot_file": screenshot_filename if screenshot_ok else None,
    }

    log_file = day_dir / "activity_log.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def write_error_log(msg: str):
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

    watcher = WindowWatcher()
    watcher.start()

    while True:
        try:
            if is_work_hours():
                record_snapshot(tracker)
            else:
                tracker.get_and_reset()
        except Exception as e:
            write_error_log(str(e))
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
