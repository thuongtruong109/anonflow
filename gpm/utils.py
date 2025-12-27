from __future__ import annotations
import os, sys
from typing import List

from config import print_lock, START_WIN_SIZE, SCREEN_W, SCREEN_H, TASKBAR_H, GAP

def safe_print(*args):
    with print_lock:
        print(*args)

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

def list_cookie_filepaths(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Cookies folder not found: {folder}")

    files = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            files.append(os.path.abspath(full))

    files.sort(key=lambda p: os.path.basename(p).lower())
    return files

def menu_multi_select():
    import msvcrt, os
    opts = [
        "Create profiles",
        "Start profiles",
        "Import cookies",
        "Close profiles",
        "Delete profiles",
        "Attach Playwright (CDP) & Run",
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
