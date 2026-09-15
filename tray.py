# filename: tray.py
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

if os.name != "nt":
    raise SystemExit("The system-tray launcher is currently supported on Windows only.")

import pystray
from PIL import Image, ImageDraw
import winreg

APP_NAME = "GoFile ABDM Helper"
RUN_VALUE_NAME = "GoFileABDMHelper"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
HEALTH_URL = "http://127.0.0.1:8765/health"
HEALTH_SERVICE_NAME = "gofile-abdm-helper"
BASE_DIR = Path(__file__).resolve().parent
APP_PATH = BASE_DIR / "app.py"
LOG_PATH = BASE_DIR / "helper.log"
LOG_OLD_PATH = BASE_DIR / "helper.log.1"
MAX_LOG_BYTES = 2 * 1024 * 1024
CHECK_INTERVAL_SECONDS = 3
HEALTH_FAILURE_RESTART_THRESHOLD = 4
MUTEX_NAME = "Local\\GoFileABDMHelperTray"
ERROR_ALREADY_EXISTS = 183

_helper_process: Optional[subprocess.Popen] = None
_stopping = threading.Event()
_icon: Optional[pystray.Icon] = None
_mutex_handle = None
_status_lock = threading.Lock()
_status_text = "Starting"


def _pythonw_executable() -> str:
    current = Path(sys.executable)
    if current.name.lower() == "pythonw.exe":
        return str(current)
    sibling = current.with_name("pythonw.exe")
    if sibling.exists():
        return str(sibling)
    return str(current)


def _startup_command() -> str:
    return f'"{_pythonw_executable()}" "{Path(__file__).resolve()}"'


def _is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return value == _startup_command()
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _set_startup_enabled(enabled: bool) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_VALUE_NAME)
            except FileNotFoundError:
                pass


def _toggle_startup(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    try:
        new_value = not _is_startup_enabled()
        _set_startup_enabled(new_value)
        _icon.update_menu()
        _icon.notify(
            "Windows startup enabled." if new_value else "Windows startup disabled.",
            APP_NAME,
        )
    except OSError as exc:
        _icon.notify(f"Could not change startup setting: {exc}", APP_NAME)


def _health_ok(timeout: float = 0.7) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.load(response)
            return (
                isinstance(payload, dict)
                and payload.get("ok") is True
                and payload.get("service") == HEALTH_SERVICE_NAME
            )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return False


def _rotate_log() -> None:
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > MAX_LOG_BYTES:
            if LOG_OLD_PATH.exists():
                LOG_OLD_PATH.unlink()
            LOG_PATH.replace(LOG_OLD_PATH)
    except OSError:
        pass


def _set_status(text: str) -> None:
    global _status_text
    with _status_lock:
        changed = text != _status_text
        _status_text = text
    if changed and _icon is not None:
        try:
            _icon.update_menu()
        except Exception:
            pass


def _get_status() -> str:
    with _status_lock:
        return _status_text


def _status_label(_item: pystray.MenuItem) -> str:
    return f"Helper: {_get_status()}"


def _start_helper() -> None:
    global _helper_process

    if _health_ok():
        if _helper_process is not None and _helper_process.poll() is None:
            _set_status("Running")
        else:
            _set_status("Running (external)")
        return

    if _helper_process is not None and _helper_process.poll() is None:
        return

    _rotate_log()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        log_handle = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
        _helper_process = subprocess.Popen(
            [_pythonw_executable(), str(APP_PATH)],
            cwd=str(BASE_DIR),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            env=env,
        )
        log_handle.close()
        _set_status("Starting")
    except Exception as exc:
        _helper_process = None
        _set_status("Failed")
        if _icon is not None:
            _icon.notify(f"Failed to start helper: {exc}", APP_NAME)


def _stop_owned_helper() -> None:
    global _helper_process
    proc = _helper_process
    _helper_process = None
    if proc is None or proc.poll() is not None:
        return

    try:
        proc.terminate()
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
    except OSError:
        pass


def _restart_helper(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    if _helper_process is None and _health_ok():
        icon.notify(
            "A helper started outside the tray is already using port 8765. Close it first; the tray will start its own helper automatically.",
            APP_NAME,
        )
        return

    _set_status("Restarting")
    _stop_owned_helper()
    time.sleep(0.4)
    _start_helper()


def _open_folder(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    os.startfile(str(BASE_DIR))


def _open_log(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    try:
        LOG_PATH.touch(exist_ok=True)
        os.startfile(str(LOG_PATH))
    except OSError as exc:
        icon.notify(f"Could not open log: {exc}", APP_NAME)


def _exit(icon: pystray.Icon, _item: pystray.MenuItem) -> None:
    _stopping.set()
    _set_status("Stopping")
    _stop_owned_helper()
    icon.stop()


def _monitor() -> None:
    consecutive_owned_health_failures = 0
    while not _stopping.wait(CHECK_INTERVAL_SECONDS):
        alive = _health_ok()
        proc_alive = _helper_process is not None and _helper_process.poll() is None

        if alive:
            consecutive_owned_health_failures = 0
            _set_status("Running" if proc_alive else "Running (external)")
            continue

        if proc_alive:
            consecutive_owned_health_failures += 1
            if consecutive_owned_health_failures < HEALTH_FAILURE_RESTART_THRESHOLD:
                _set_status("Starting")
                continue

            # A process can stay alive while Flask is permanently unresponsive.
            # Restart only after several failed probes so normal startup or a
            # short busy period does not cause a premature restart loop.
            consecutive_owned_health_failures = 0
            _set_status("Restarting")
            _stop_owned_helper()
            time.sleep(0.4)
            _start_helper()
            continue

        consecutive_owned_health_failures = 0
        _set_status("Stopped")
        _start_helper()


def _create_icon_image() -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(37, 99, 235, 255))
    draw.line((32, 16, 32, 41), fill=(255, 255, 255, 255), width=7)
    draw.polygon([(20, 34), (44, 34), (32, 48)], fill=(255, 255, 255, 255))
    return image


def _acquire_single_instance() -> bool:
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not _mutex_handle:
        return False
    return kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def _release_mutex() -> None:
    global _mutex_handle
    if _mutex_handle:
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None


def main() -> None:
    global _icon

    if not _acquire_single_instance():
        return

    menu = pystray.Menu(
        pystray.MenuItem(_status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart Helper", _restart_helper),
        pystray.MenuItem("Open Folder", _open_folder),
        pystray.MenuItem("View Log", _open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start with Windows", _toggle_startup, checked=lambda _item: _is_startup_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", _exit),
    )

    _icon = pystray.Icon("gofile-abdm-helper", _create_icon_image(), APP_NAME, menu)

    _start_helper()
    monitor = threading.Thread(target=_monitor, name="helper-monitor", daemon=True)
    monitor.start()

    try:
        _icon.run()
    finally:
        _stopping.set()
        _stop_owned_helper()
        _release_mutex()


if __name__ == "__main__":
    main()
