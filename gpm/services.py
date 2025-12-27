from config import profile_cache, cache_lock, started_debug_addrs, started_lock, GROUP_NAME, BROWSER_CORE, BROWSER_NAME, START_WIN_SCALE, START_WIN_SIZE
import config
from client import api_get, api_post
from utils import compute_win_pos

def create_profile(name: str, proxy: str) -> str:
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

def get_profile_id(name: str) -> str:
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

def start_profile(pid: str, index: int) -> str:
    with config.start_sem:
        params = {
            "win_size": START_WIN_SIZE,
            "win_pos": compute_win_pos(index)
        }
        if START_WIN_SCALE is not None:
            params["win_scale"] = START_WIN_SCALE

        r = api_get(f"/api/v3/profiles/start/{pid}", params)

        data = r.get("data") or {}
        addr = data.get("remote_debugging_address")

        if not addr:
            raise RuntimeError(f"Start profile ok but missing remote_debugging_address (pid={pid})")

        addr = str(addr).strip()
        if addr.startswith("http://") or addr.startswith("https://") or addr.startswith("ws://"):
            return addr
        return "http://" + addr


def close_profile(pid: str):
    api_get(f"/api/v3/profiles/close/{pid}")

def delete_profile(pid: str):
    r = api_get(f"/api/v3/profiles/delete/{pid}", {"mode": 2})
    if isinstance(r, dict) and (r.get("success") is False):
        raise RuntimeError(r.get("message") or f"Delete failed for {pid}")
    return r

def remember_debug_addr(name: str, addr: str):
    with started_lock:
        started_debug_addrs.append((name, addr))
