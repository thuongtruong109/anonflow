import sys, threading, os, requests
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openpyxl import load_workbook

GPM_API = "http://127.0.0.1:19995"
EXCEL_PATH = "proxies.xlsx"
COOKIES_DIR = "cookies"

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

print_lock = threading.Lock()
def safe_print(*args):
    with print_lock:
        print(*args)

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

def delete_profile(pid: str):
    r = api_get(f"/api/v3/profiles/delete/{pid}", {"mode": 2})

    if isinstance(r, dict) and (r.get("success") is False):
        raise RuntimeError(r.get("message") or f"Delete failed for {pid}")

    return r

# ================= COOKIES AND EXCEL =================
def list_cookie_filepaths(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Cookies folder not found: {folder}")

    files = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            files.append(os.path.abspath(full))

    files.sort(key=lambda p: os.path.basename(p).lower())
    return files

def update_excel_column_a_with_cookie_files(
    excel_path: str,
    cookies_folder: str,
    sheet_name: str | None = None,
    start_row: int = 2,
):
    cookie_paths = list_cookie_filepaths(cookies_folder)

    wb = load_workbook(excel_path)
    ws = wb[sheet_name] if sheet_name else wb.active

    row = start_row
    for fpath in cookie_paths:
        ws.cell(row=row, column=1).value = fpath
        row += 1

    wb.save(excel_path)
    return len(cookie_paths)

def count_proxy_rows(
    excel_path: str,
    sheet_name: str | None = None,
    start_row: int = 2,
    proxy_col: int = 2,
) -> int:
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active

    cnt = 0
    for r in range(start_row, ws.max_row + 1):
        v = ws.cell(r, proxy_col).value
        if v is None:
            continue
        if str(v).strip() == "":
            continue
        cnt += 1
    return cnt

def read_excel():
    wb = load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active
    rows = []

    for r in range(2, ws.max_row + 1):
        cookie_path = ws.cell(r, 1).value
        proxy = ws.cell(r, 2).value

        if proxy is None or str(proxy).strip() == "":
            continue

        cookie_path_str = str(cookie_path).strip() if cookie_path else ""
        profile_name = os.path.basename(cookie_path_str) if cookie_path_str else f"Profile {r-1}"

        rows.append((profile_name, cookie_path_str, proxy))

    return rows

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
            pass

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

def main():
    try:
        n = update_excel_column_a_with_cookie_files(EXCEL_PATH, COOKIES_DIR)
        safe_print(f"✅ Updated {n} cookie paths into column A")
    except Exception as e:
        safe_print(f"❌ Update cookies->excel failed: {e}")

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
