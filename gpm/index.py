import threading, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import started_debug_addrs, started_lock, EXCEL_PATH, COOKIES_DIR, THREADS, START_LIMIT
import config

from utils import safe_print, normalize_proxy, menu_multi_select
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
    try:
        proxy = normalize_proxy(proxy_raw)

        if actions["create"]:
            pid = create_profile(name, proxy)
            safe_print(f"✅ Created {name}")
        else:
            pid = get_profile_id(name)

        if actions["start"]:
            addr = start_profile(pid, index)
            safe_print(f"✅ Started {name} -> {addr}")
            remember_debug_addr(name, addr)

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


def main():
    config.start_sem = threading.Semaphore(START_LIMIT)

    try:
        n = update_excel_column_a_with_cookie_files(EXCEL_PATH, COOKIES_DIR)
        safe_print(f"✅ Updated {n} cookie paths into column A")
    except Exception as e:
        safe_print(f"❌ Update cookies->excel failed: {e}")

    rows = read_excel()
    sel = menu_multi_select()
    if sel[6]:
        return

    actions = {
        "create": sel[0],
        "start": sel[1],
        "import": sel[2],
        "close": sel[3],
        "delete": sel[4],
        "pw": sel[5],
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
