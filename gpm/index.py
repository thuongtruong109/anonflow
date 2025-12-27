import threading, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import started_debug_addrs, started_lock, EXCEL_PATH, COOKIES_DIR, THREADS, START_LIMIT
import config

from utils import copy_folder, detect_username_from_cookie_filename, safe_print, normalize_proxy, menu_multi_select
from excel import update_excel_column_a_with_cookie_files, read_excel
from services import (
    create_profile,
    get_profile_id,
    start_profile,
    close_profile,
    delete_profile,
    remember_debug_addr,
)
from runner import run_all_playwright

def process_row(name, cookie, proxy_raw, index, actions):
    profile_name = detect_username_from_cookie_filename(name)
    try:
        proxy = normalize_proxy(proxy_raw)

        if actions["handle_cookies"]:
            from cookie import convert_cookies_format
            convert_cookies_format()
            safe_print(f"✅ Converted cookies format in {COOKIES_DIR}")

            try:
                n = update_excel_column_a_with_cookie_files(EXCEL_PATH, COOKIES_DIR)
                safe_print(f"✅ Updated {n} cookie paths into column A")
            except Exception as e:
                safe_print(f"❌ Update cookies->excel failed: {e}")

        if actions["create"]:
            pid = create_profile(profile_name, proxy)
            safe_print(f"✅ Created {profile_name}")
        else:
            pid = get_profile_id(profile_name)

        if actions["start"]:
            addr = start_profile(pid, index)
            safe_print(f"✅ Started {profile_name} -> {addr}")
            remember_debug_addr(profile_name, addr)

        if actions["import"]:
            copy_folder(config.EXTENSIONS_DIR, config.GPM_EXTENSION_LOCATE)

        if actions["close"]:
            close_profile(pid)
            safe_print(f"✅ Closed {profile_name}")

        if actions["delete"]:
            delete_profile(pid)
            safe_print(f"🗑️ Deleted {profile_name}")

    except Exception as e:
        safe_print(f"❌ {profile_name}: {e}")

def main():
    config.start_sem = threading.Semaphore(START_LIMIT)

    rows = read_excel()
    sel = menu_multi_select()
    if sel[7]:
        return

    actions = {
        "handle_cookies": sel[0],
        "create": sel[1],
        "start": sel[2],
        "pw": sel[3],
        "import": sel[4],
        "close": sel[5],
        "delete": sel[6],
    }

    with started_lock:
        started_debug_addrs.clear()

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = [
            ex.submit(process_row, *row, i, actions)
            for i, row in enumerate(rows)
        ]
        for _ in as_completed(futures):
            pass

    if actions["pw"]:
        with started_lock:
            pairs = started_debug_addrs.copy()

        if not pairs:
            safe_print("⚠️ No remote_debugging_address collected. Select 'Start profiles' before Playwright.")
        else:
            asyncio.run(run_all_playwright(pairs))

    safe_print("✅ ALL DONE")

if __name__ == "__main__":
    main()
