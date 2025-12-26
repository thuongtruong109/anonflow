import time
import threading
import sys
from typing import Any, Dict, List, Tuple, Optional

import requests
from openpyxl import load_workbook

GPM_API = "http://127.0.0.1:19995"
EXCEL_PATH = "proxies.xlsx"
START_ROW = 2

GROUP_NAME = "All"
BROWSER_CORE = "chromium"
BROWSER_NAME = "Chrome"

THREADS = 3
REQUEST_TIMEOUT = 30

SCREEN_W = 1920
SCREEN_H = 1080
TASKBAR_H = 40
GAP = 4

START_WIN_SCALE = None
START_WIN_SIZE = "640,520"

print_lock = threading.Lock()

def safe_print(*args):
    with print_lock:
        print(*args)


def menu_multi_select():
    import msvcrt
    import os

    options = ["Create profile", "Start profile", "Close profile", "Import cookie", "Exit"]
    selected = [False] * len(options)
    current = 0

    def draw():
        os.system("cls")
        print("Menu: ↑ ↓ move | SPACE select | ENTER run | ESC exit\n")
        for i, opt in enumerate(options):
            cursor = "➤" if i == current else " "
            mark = "[x]" if selected[i] else "[ ]"
            print(f"{cursor} {mark} {opt}")

    while True:
        draw()
        key = msvcrt.getch()
        if key == b"\x1b":  # ESC
            sys.exit(0)
        if key == b"\r":  # ENTER
            return selected
        if key == b" ":
            selected[current] = not selected[current]
        if key in (b"\xe0", b"\x00"):
            key2 = msvcrt.getch()
            if key2 == b"H":
                current = (current - 1) % len(options)
            elif key2 == b"P":
                current = (current + 1) % len(options)


def _json_or_throw(r: requests.Response, url: str) -> Dict[str, Any]:
    try:
        return r.json()
    except Exception:
        snippet = (r.text or "").strip().replace("\r", " ").replace("\n", " ")[:400]
        raise RuntimeError(f"API non-JSON (HTTP {r.status_code}) {url}: {snippet}")

def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{GPM_API}{path}"
    r = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
    return _json_or_throw(r, url)

def api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{GPM_API}{path}"
    r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    return _json_or_throw(r, url)

def normalize_proxy(raw: Any) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if not s:
        return ""

    if "://" in s:
        _, rest = s.split("://", 1)
    else:
        rest = s

    if "@" in rest:
        user_pass, host_port = rest.split("@", 1)
        if ":" in user_pass and ":" in host_port:
            user, password = user_pass.split(":", 1)
            host, port = host_port.split(":", 1)
            return f"socks5://{host}:{port}:{user}:{password}"

    parts = rest.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"socks5://{host}:{port}:{user}:{password}"

    if len(parts) == 2:
        return "socks5://" + rest

    return s


# ======= NEW: compute non-overlap window position =======
def _parse_win_size(win_size: str) -> Tuple[int, int]:
    w, h = win_size.split(",", 1)
    return int(w.strip()), int(h.strip())

def compute_win_pos(index: int) -> str:
    win_w, win_h = _parse_win_size(START_WIN_SIZE)

    usable_w = SCREEN_W
    usable_h = SCREEN_H - TASKBAR_H

    cols = max(1, (usable_w + GAP) // (win_w + GAP))
    rows = max(1, (usable_h + GAP) // (win_h + GAP))
    per_page = cols * rows

    slot = index % per_page
    col = slot % cols
    row = slot // cols

    x = col * (win_w + GAP)
    y = row * (win_h + GAP)

    # đảm bảo không vượt biên
    x = min(x, max(0, usable_w - win_w))
    y = min(y, max(0, usable_h - win_h))

    return f"{x},{y}"


# ================== GPM Actions ==================
def create_profile(profile_name: str, raw_proxy: str) -> str:
    payload = {
        "profile_name": profile_name,
        "group_name": GROUP_NAME,
        "browser_core": BROWSER_CORE,
        "browser_name": BROWSER_NAME,
        "is_random_browser_version": True,
        "raw_proxy": raw_proxy or "",
        "startup_urls": "",
    }
    resp = api_post("/api/v3/profiles/create", payload)
    if not resp.get("success") or not resp.get("data"):
        raise RuntimeError(resp.get("message") or str(resp))
    return resp["data"]["id"]

def find_profile_id_by_name(profile_name: str, group_id: Optional[str] = None) -> str:
    params: Dict[str, Any] = {"search": profile_name, "page": 1, "per_page": 50, "sort": 2}
    if group_id:
        params["group_id"] = group_id

    resp = api_get("/api/v3/profiles", params=params)
    if not resp.get("success"):
        raise RuntimeError(resp.get("message") or str(resp))

    items = resp.get("data") or []

    for it in items:
        if str(it.get("name", "")).strip() == profile_name:
            pid = it.get("id")
            if pid:
                return pid

    if len(items) == 1 and items[0].get("id"):
        return items[0]["id"]

    raise RuntimeError(f"Cannot find unique profile id for name={profile_name!r} (matches={len(items)})")

def start_profile_by_id(profile_id: str, index: int) -> Dict[str, Any]:
    params = {}

    if START_WIN_SCALE is not None:
        params["win_scale"] = START_WIN_SCALE

    params["win_size"] = START_WIN_SIZE
    params["win_pos"] = compute_win_pos(index)  # <<<<<< key point

    resp = api_get(f"/api/v3/profiles/start/{profile_id}", params=params)
    if not resp.get("success"):
        raise RuntimeError(resp.get("message") or str(resp))
    return resp.get("data", {})

def close_profile_by_id(profile_id: str) -> None:
    resp = api_get(f"/api/v3/profiles/close/{profile_id}")
    if not resp.get("success"):
        raise RuntimeError(resp.get("message") or str(resp))

def read_excel() -> List[Tuple[str, Any, Any]]:
    wb = load_workbook(EXCEL_PATH)
    ws = wb.active
    rows = []
    idx = 1
    for r in range(START_ROW, ws.max_row + 1):
        cookie = ws.cell(r, 1).value
        proxy = ws.cell(r, 2).value
        if cookie or proxy:
            rows.append((f"Profile {idx}", cookie, proxy))
            idx += 1
    return rows

# ================== WORKER ==================
def process_row(profile_name, cookie_cell, proxy_cell, index, actions):
    raw_proxy = normalize_proxy(proxy_cell)

    if actions["create"]:
        try:
            pid = create_profile(profile_name, raw_proxy)
            safe_print(f"✅ Created {profile_name} (id={pid})")
        except Exception as e:
            safe_print(f"❌ Create failed {profile_name}: {e}")
            return

    if actions["start"]:
        try:
            pid = find_profile_id_by_name(profile_name)
            data = start_profile_by_id(pid, index)  # << pass index
            safe_print(f"✅ Started {profile_name} (id={pid}) | pos={compute_win_pos(index)} | remote={data.get('remote_debugging_address')}")
        except Exception as e:
            safe_print(f"❌ Start failed {profile_name}: {e}")

    if actions["close"]:
        try:
            pid = find_profile_id_by_name(profile_name)
            close_profile_by_id(pid)
            safe_print(f"✅ Closed {profile_name} (id={pid})")
        except Exception as e:
            safe_print(f"❌ Close failed {profile_name}: {e}")

def main():
    rows = read_excel()
    selected = menu_multi_select()
    if selected[4]:
        return

    actions = {
        "create": selected[0],
        "start": selected[1],
        "close": selected[2],
        "import": selected[3],
    }

    threads = []
    for i, row in enumerate(rows):
        t = threading.Thread(target=process_row, args=(*row, i, actions), daemon=True)
        t.start()
        threads.append(t)

        while threading.active_count() > THREADS:
            time.sleep(0.2)

    for t in threads:
        t.join()

    safe_print("✅ ALL DONE")

if __name__ == "__main__":
    main()
