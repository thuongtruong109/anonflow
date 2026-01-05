from __future__ import annotations
import re, os, sys, shutil, math
from typing import List
from config import print_lock, setup_logger, START_WIN_SIZE, ROWS, COLS, SCREEN_H, SCREEN_W, TASKBAR_H

log = setup_logger("act")

def safe_print(*args):
    with print_lock:
        log.info(" ".join(map(str, args)))

def calculate_optimal_grid(total_profiles: int) -> tuple[int, int]:
    """
    Tính toán grid tối ưu dựa trên số lượng profile.
    Ví dụ:
    - 1-4 profiles: 2x2
    - 5-6 profiles: 3x2 hoặc 2x3
    - 7-9 profiles: 3x3
    - 10-12 profiles: 4x3 (mặc định)
    - >12 profiles: 4x(n)
    """
    if total_profiles <= 0:
        return COLS, ROWS

    if total_profiles <= 4:
        return 2, 2
    elif total_profiles <= 6:
        return 3, 2
    elif total_profiles <= 9:
        return 3, 3
    else:
        # Sử dụng grid mặc định 4x3 cho 10-12, hoặc tăng rows nếu cần
        return COLS, ROWS

def compute_win_pos(index: int, total_profiles: int = None) -> str:
    w, h = map(int, START_WIN_SIZE.split(","))

    # Nếu có total_profiles và < 12, tính grid tối ưu
    if total_profiles and total_profiles < 12:
        cols, rows = calculate_optimal_grid(total_profiles)

        # Tính lại kích thước cửa sổ để fill đầy màn hình (không có khoảng cách)
        usable_w = SCREEN_W
        usable_h = SCREEN_H - TASKBAR_H

        # Tính kích thước cửa sổ - ưu tiên lấp đầy width
        w = usable_w // cols
        h = usable_h // rows

        # Nếu có dư pixel, tăng width để lấp đầy
        remaining_w = usable_w % cols
        if remaining_w > 0:
            # Phân bổ đều remaining pixels cho các cột
            extra_per_col = remaining_w // cols
            w += extra_per_col

        # Đảm bảo height không vượt quá usable_h
        if h * rows > usable_h:
            h = usable_h // rows
    else:
        cols, rows = COLS, ROWS

    capacity = cols * rows
    i = index % capacity

    x = (i % cols) * w
    y = (i // cols) * h

    usable_h = SCREEN_H - TASKBAR_H
    if y > usable_h - h:
        y = usable_h - h

    return f"{x},{y},{w},{h}"

def normalize_proxy(raw) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if "://" in s:
        s = s.split("://", 1)[1]
    if "@" in s:
        up, hp = s.split("@", 1)
        u, p = up.split(":", 1)
        h, po = hp.split(":", 1)
        return f"socks5://{h}:{po}:{u}:{p}"
    parts = s.split(":")
    if len(parts) == 4:
        h, po, u, p = parts
        return f"socks5://{h}:{po}:{u}:{p}"
    if len(parts) == 2:
        return "socks5://" + s
    return s

def list_filepaths(folder: str, base: str = ".") -> List[str]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Cookies folder not found: {folder}")

    files = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            files.append(os.path.relpath(full, start=base))

    files.sort(key=lambda p: os.path.basename(p).lower())
    return files

def menu_multi_select():
    import msvcrt, os
    opts = [
        "Handle cookies",
        "Create profiles",
        "Start profiles",
        "Attach CDP",
        "Import cookies",
        "Close profiles",
        "Delete profiles",
        "Exit"
    ]
    sel = [False] * len(opts)
    cur = 0

    while True:
        os.system("cls")
        print("↑ ↓ move | SPACE select | ENTER run | ESC exit\n")
        for i, o in enumerate(opts):
            print(("➤" if i == cur else " "), "[x]" if sel[i] else "[ ]", o)

        k = msvcrt.getch()
        if k == b"\x1b":
            sys.exit(0)
        if k == b"\r":
            return sel
        if k == b" ":
            sel[cur] = not sel[cur]
        if k in (b"\xe0", b"\x00"):
            k2 = msvcrt.getch()
            if k2 == b"H":
                cur = (cur - 1) % len(opts)
            elif k2 == b"P":
                cur = (cur + 1) % len(opts)

def detect_username_from_cookie_filename(text: str) -> str:
    username = re.search(r'\[([^\]]+)\]\.txt$', text)
    return username.group(1) if username else "Unknown"

def copy_folder(source: str, destination: str):
    os.makedirs(destination, exist_ok=True)

    for item in os.listdir(source):
        src_path = os.path.join(source, item)
        dst_path = os.path.join(destination, item)

        if os.path.isdir(src_path):
            copy_folder(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
