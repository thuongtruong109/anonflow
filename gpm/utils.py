from __future__ import annotations
import re, os, sys, shutil
from typing import List
from config import print_lock, setup_logger, START_WIN_SIZE, SCREEN_W, SCREEN_H, TASKBAR_H, GAP

log = setup_logger()

def safe_print(*args):
    with print_lock:
        log.info(" ".join(map(str, args)))

def compute_win_pos(index: int) -> str:
    w, h = map(int, START_WIN_SIZE.split(","))
    usable_h = SCREEN_H - TASKBAR_H
    cols = max(1, SCREEN_W // (w + GAP))
    x = (index % cols) * (w + GAP)
    y = (index // cols) * (h + GAP)
    return f"{x},{min(y, usable_h - h)}"

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
    username = re.search(r'\[([^\]]+)\]\.json$', text)
    return username.group(1) if username else "Unknown"

def copy_folder(source: str, destination: str):
    try:
        if os.path.exists(destination) and os.listdir(destination):
            return
        os.makedirs(destination, exist_ok=True)

        for item in os.listdir(source):
            src_path = os.path.join(source, item)
            dst_path = os.path.join(destination, item)

            if os.path.isdir(src_path):
                copy_folder(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
    except Exception as e:
        safe_print(f"⚠️ Skipped copying {source} to {destination} (file in use or error): {e}")