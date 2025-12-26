import sys
import threading
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openpyxl import load_workbook

# ================= CONFIG =================
GPM_API = "http://127.0.0.1:19995"
EXCEL_PATH = "proxies.xlsx"

GROUP_NAME = "All"
BROWSER_CORE = "chromium"
BROWSER_NAME = "Chrome"

THREADS = 6
START_LIMIT = 3
REQUEST_TIMEOUT = 30

SCREEN_W = 1920
SCREEN_H = 1080
TASKBAR_H = 40
GAP = 4

START_WIN_SCALE = None
START_WIN_SIZE = "640,520"
# =========================================

print_lock = threading.Lock()
def safe_print(*args):
    with print_lock:
        print(*args)

# ================= HTTP =================
def build_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST")
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

thread_local = threading.local()
def get_session():
    if not hasattr(thread_local, "session"):
        thread_local.session = build_session()
    return thread_local.session

def api_get(path, params=None):
    r = get_session().get(f"{GPM_API}{path}", params=params or {}, timeout=REQUEST_TIMEOUT)
    return r.json()

def api_post(path, payload):
    r = get_session().post(f"{GPM_API}{path}", json=payload, timeout=REQUEST_TIMEOUT)
    return r.json()

# ================= WINDOW =================
def compute_win_pos(index):
    w, h = map(int, START_WIN_SIZE.split(","))
    usable_h = SCREEN_H - TASKBAR_H
    cols = max(1, SCREEN_W // (w + GAP))
    x = (index % cols) * (w + GAP)
    y = (index // cols) * (h + GAP)
    return f"{x},{min(y, usable_h - h)}"

# ================= PROXY =================
def normalize_proxy(raw):
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

# ================= PROFILE API =================
profile_cache = {}
cache_lock = threading.Lock()
start_sem = threading.Semaphore(START_LIMIT)

def create_profile(name, proxy):
    r = api_post("/api/v3/profiles/create", {
        "profile_name": name,
        "group_name": GROUP_NAME,
        "browser_core": BROWSER_CORE,
        "browser_name": BROWSER_NAME,
        "is_random_browser_version": True,
        "raw_proxy": proxy,
        "startup_urls": ""
    })
    return r["data"]["id"]

def get_profile_id(name):
    with cache_lock:
        if name in profile_cache:
            return profile_cache[name]

    r = api_get("/api/v3/profiles", {
        "search": name,
        "page": 1,
        "per_page": 50,
        "sort": 2
    })
    for it in r.get("data", []):
        if it.get("name") == name:
            pid = it["id"]
            with cache_lock:
                profile_cache[name] = pid
            return pid
    raise RuntimeError("Profile not found")

def start_profile(pid, index):
    with start_sem:
        params = {
            "win_size": START_WIN_SIZE,
            "win_pos": compute_win_pos(index)
        }
        if START_WIN_SCALE is not None:
            params["win_scale"] = START_WIN_SCALE
        api_get(f"/api/v3/profiles/start/{pid}", params)

def close_profile(pid):
    api_get(f"/api/v3/profiles/close/{pid}")

def delete_profile(pid):
    api_post("/api/v3/profiles/delete", {"ids": [pid]})

# ================= EXCEL =================
def read_excel():
    wb = load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    idx = 1
    for r in range(2, ws.max_row + 1):
        cookie = ws.cell(r, 1).value
        proxy = ws.cell(r, 2).value
        if cookie or proxy:
            rows.append((f"Profile {idx}", cookie, proxy))
            idx += 1
    return rows

# ================= WORKER =================
def process_row(name, cookie, proxy_raw, index, actions):
    try:
        proxy = normalize_proxy(proxy_raw)

        if actions["create"]:
            pid = create_profile(name, proxy)
            safe_print(f"✅ Created {name}")
        else:
            pid = get_profile_id(name)

        if actions["start"]:
            start_profile(pid, index)
            safe_print(f"✅ Started {name}")

        if actions["import"]:
            pass  # giữ chỗ cho import cookie sau

        if actions["close"]:
            close_profile(pid)
            safe_print(f"✅ Closed {name}")

        if actions["delete"]:
            delete_profile(pid)
            safe_print(f"🗑️ Deleted {name}")

    except Exception as e:
        safe_print(f"❌ {name}: {e}")

# ================= MENU =================
def menu_multi_select():
    import msvcrt, os
    opts = [
        "Create profiles",
        "Start profiles",
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

# ================= MAIN =================
def main():
    rows = read_excel()
    sel = menu_multi_select()
    if sel[5]:
        return

    actions = {
        "create": sel[0],
        "start": sel[1],
        "import": sel[2],
        "close": sel[3],
        "delete": sel[4]
    }

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = [
            ex.submit(process_row, *row, i, actions)
            for i, row in enumerate(rows)
        ]
        for _ in as_completed(futures):
            pass

    safe_print("✅ ALL DONE")

if __name__ == "__main__":
    main()
