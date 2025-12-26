import sys
import time
import threading
from typing import Any, Dict, List, Tuple, Optional

import requests
from openpyxl import load_workbook

# ================== CONFIG ==================
GPM_API = "http://127.0.0.1:19995"
EXCEL_PATH = "proxies.xlsx"
START_ROW = 2

GROUP_NAME = "All"
BROWSER_CORE = "chromium"   # ✅ docs: chromium / firefox
BROWSER_NAME = "Chrome"

THREADS = 3
REQUEST_TIMEOUT = 30

# Start window options (optional)
START_WIN_SCALE = None   # e.g. 0.8
START_WIN_POS = None     # e.g. "300,300"
START_WIN_SIZE = None    # e.g. "1200,800"

print_lock = threading.Lock()


def safe_print(*args):
    with print_lock:
        print(*args)


def menu_multi_select():
    import msvcrt
    import os

    options = ["Create profile", "Start profile", "Import cookie", "Exit"]
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
        if key == b"\x1b":
            sys.exit(0)
        if key == b"\r":
            return selected
        if key == b" ":
            selected[current] = not selected[current]
        if key in (b"\xe0", b"\x00"):
            key2 = msvcrt.getch()
            if key2 == b"H":
                current = (current - 1) % len(options)
            elif key2 == b"P":
                current = (current + 1) % len(options)


# ================== API ==================
def _json_or_error(r: requests.Response, url: str) -> Dict[str, Any]:
    try:
        return r.json()
    except Exception:
        snippet = (r.text or "").strip().replace("\r", " ").replace("\n", " ")[:400]
        raise RuntimeError(f"API non-JSON (HTTP {r.status_code}) {url}: {snippet}")


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{GPM_API}{path}"
    r = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
    return _json_or_error(r, url)


def api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{GPM_API}{path}"
    r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    return _json_or_error(r, url)


def normalize_proxy(raw: Any) -> str:
    """
    Docs show Socks5 as: socks5://IP:Port:User:Pass
    Your input often: user:pass@host:port  -> convert to socks5://host:port:user:pass
    """
    if not raw:
        return ""
    s = str(raw).strip()
    if not s:
        return ""

    # strip scheme if present
    if "://" in s:
        _, rest = s.split("://", 1)
    else:
        rest = s

    # user:pass@host:port
    if "@" in rest:
        user_pass, host_port = rest.split("@", 1)
        if ":" in user_pass and ":" in host_port:
            user, password = user_pass.split(":", 1)
            host, port = host_port.split(":", 1)
            return f"socks5://{host}:{port}:{user}:{password}"

    # host:port:user:pass
    parts = rest.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"socks5://{host}:{port}:{user}:{password}"

    # host:port
    if len(parts) == 2:
        return "socks5://" + rest

    return s


# ================== GPM ==================
def create_profile(profile_name: str, raw_proxy: str) -> str:
    payload = {
        "profile_name": profile_name,
        "group_name": GROUP_NAME,
        "browser_core": BROWSER_CORE,
        "browser_name": BROWSER_NAME,
        "is_random_browser_version": True,  # ✅ let GPM auto
        "raw_proxy": raw_proxy or "",
        "startup_urls": "",
    }
    resp = api_post("/api/v3/profiles/create", payload)
    if not resp.get("success") or not resp.get("data"):
        raise RuntimeError(resp.get("message") or str(resp))
    return resp["data"]["id"]


def find_profile_id_by_name(profile_name: str, group_id: Optional[str] = None) -> str:
    """
    Use list profiles API:
      GET /api/v3/profiles?search=<keyword>&page=1&per_page=50
    Response items include id and name. :contentReference[oaicite:4]{index=4}
    """
    params: Dict[str, Any] = {"search": profile_name, "page": 1, "per_page": 50, "sort": 2}
    if group_id:
        params["group_id"] = group_id

    resp = api_get("/api/v3/profiles", params=params)
    if not resp.get("success"):
        raise RuntimeError(resp.get("message") or str(resp))

    items = resp.get("data") or []
    # Prefer exact name match first
    for it in items:
        if str(it.get("name", "")).strip() == profile_name:
            pid = it.get("id")
            if pid:
                return pid

    # fallback: first item if only 1
    if len(items) == 1 and items[0].get("id"):
        return items[0]["id"]

    raise RuntimeError(f"Cannot find unique profile id for name={profile_name!r} (found {len(items)} matches)")


def start_profile_by_id(profile_id: str) -> Dict[str, Any]:
    params = {}
    if START_WIN_SCALE is not None:
        params["win_scale"] = START_WIN_SCALE
    if START_WIN_POS:
        params["win_pos"] = START_WIN_POS
    if START_WIN_SIZE:
        params["win_size"] = START_WIN_SIZE

    resp = api_get(f"/api/v3/profiles/start/{profile_id}", params=params)  # :contentReference[oaicite:5]{index=5}
    if not resp.get("success"):
        raise RuntimeError(resp.get("message") or str(resp))
    return resp.get("data", {})


# ================== EXCEL ==================
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

    # Create (optional)
    if actions["create"]:
        try:
            pid = create_profile(profile_name, raw_proxy)
            safe_print(f"✅ Created {profile_name} (id={pid})")
        except Exception as e:
            safe_print(f"❌ Create failed {profile_name}: {e}")
            return

    # Start (optional)
    if actions["start"]:
        try:
            pid = find_profile_id_by_name(profile_name)  # name -> id via list profiles :contentReference[oaicite:6]{index=6}
            data = start_profile_by_id(pid)              # start/{id} :contentReference[oaicite:7]{index=7}
            safe_print(f"✅ Started {profile_name} (id={pid}) | remote={data.get('remote_debugging_address')}")
        except Exception as e:
            safe_print(f"❌ Start failed {profile_name}: {e}")


def main():
    rows = read_excel()
    selected = menu_multi_select()
    if selected[3]:
        return

    actions = {"create": selected[0], "start": selected[1], "import": selected[2]}
    safe_print("▶ ACTIONS:", actions)

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
