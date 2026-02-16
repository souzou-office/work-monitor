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
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# Default settings (overridden by config.json if present)
# ============================================================
EMPLOYEE_NAME = "池田龍太"
INTERVAL_MINUTES = 10
WINDOW_CHECK_SECONDS = 2
WORK_START_HOUR = 9
WORK_END_HOUR = 23
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
SCREENSHOT_MAX_WIDTH = 960         # resize width (None = no resize)
SCREENSHOT_RETENTION_DAYS = 30     # auto-delete screenshots older than N days
# ============================================================

# Load config.json next to EXE (or next to .py) if it exists
_config_path = (
    Path(sys.executable).parent / "config.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).parent / "config.json"
)
if _config_path.exists():
    with open(_config_path, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
        EMPLOYEE_NAME = _cfg.get("employee_name", EMPLOYEE_NAME)
        INTERVAL_MINUTES = _cfg.get("interval_minutes", INTERVAL_MINUTES)
        GDRIVE_BASE = Path(_cfg.get("gdrive_base", str(GDRIVE_BASE)))
        SCREENSHOT_MAX_WIDTH = _cfg.get("screenshot_max_width", SCREENSHOT_MAX_WIDTH)
        SCREENSHOT_RETENTION_DAYS = _cfg.get("screenshot_retention_days", SCREENSHOT_RETENTION_DAYS)

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
        if SCREENSHOT_MAX_WIDTH and img.width > SCREENSHOT_MAX_WIDTH:
            ratio = SCREENSHOT_MAX_WIDTH / img.width
            new_size = (SCREENSHOT_MAX_WIDTH, int(img.height * ratio))
            img = img.resize(new_size, getattr(__import__('PIL.Image', fromlist=['Image']), 'LANCZOS', 1))
        img.save(save_path, "JPEG", quality=60, optimize=True)
        return True
    except Exception:
        return False


def cleanup_old_screenshots():
    """Delete screenshot files older than SCREENSHOT_RETENTION_DAYS.
    Skips dates with a .keep file (protected via dashboard save button).
    Logs and window_log files are kept (tiny size).
    """
    if not SAVE_DIR.exists() or not SCREENSHOT_RETENTION_DAYS:
        return
    cutoff = (datetime.now() - timedelta(days=SCREENSHOT_RETENTION_DAYS)).strftime("%Y-%m-%d")
    deleted = 0
    for day_dir in SAVE_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        name = day_dir.name
        if len(name) != 10 or name[4] != '-' or name[7] != '-':
            continue
        if name >= cutoff:
            continue
        if (day_dir / ".keep").exists():
            continue
        for f in day_dir.glob("ss_*.jpg"):
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
    if deleted:
        write_error_log(f"Cleanup: deleted {deleted} old screenshot(s) before {cutoff}")


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

    # Clean up old screenshots on startup
    try:
        cleanup_old_screenshots()
    except Exception as e:
        write_error_log(f"Cleanup error: {e}")

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
