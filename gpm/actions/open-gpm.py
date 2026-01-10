import subprocess, psutil, time, win32gui, win32con

APP_PATH = r"C:\Users\admin\AppData\Local\Programs\GPMLogin\GPMLogin.exe"
PROCESS_NAME = "GPMLogin.exe"

def is_app_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == PROCESS_NAME:
            return True
    return False

def focus_app_window():
    def enum_windows(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "GPM" in title:
                result.append(hwnd)

    windows = []
    win32gui.EnumWindows(enum_windows, windows)

    if windows:
        hwnd = windows[0]
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)


def open_gpm_app():
    if not is_app_running():
        subprocess.Popen(
            [APP_PATH],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True
        )
        time.sleep(2)
        focus_app_window()
    else:
        focus_app_window()