import os
from config import EXCEL_PATH, COOKIES_DIR
import config

from utils import copy_folder, detect_username_from_cookie_filename, safe_print, normalize_proxy
from excel import update_excel_column_a_with_cookie_files, update_excel_column_c_with_profile_id
from services import (
    create_profile,
    get_profile_id,
    start_profile,
    close_profile,
    delete_profile,
    remember_debug_addr,
    get_debug_addr,
    update_profile,
)

def process_row(name, cookie, proxy_raw, index, actions, total_profiles=None):
    profile_name = detect_username_from_cookie_filename(name)
    addr = None
    try:
        proxy = normalize_proxy(proxy_raw)

        if actions["handle_cookies"]:
            # from convert import convert_cookies_format
            # convert_cookies_format()
            # safe_print(f"✅ Converted cookies format in {COOKIES_DIR}")

            for dir in os.listdir(config.EXTENSIONS_DIR):
                src = os.path.join(config.EXTENSIONS_DIR, dir)
                if not os.path.isdir(src):
                    continue
                dst = os.path.join(config.GPM_EXTENSION_LOCATE, dir)
                copy_folder(src, dst)

            safe_print(f"✅ Extensions copied to GPM location")
            try:
                n = update_excel_column_a_with_cookie_files(EXCEL_PATH, COOKIES_DIR)
                safe_print(f"✅ Updated {n} cookie paths into column A")
            except Exception as e:
                safe_print(f"❌ Update cookies->excel failed: {e}")

        if actions["create"]:
            pid = create_profile(profile_name, proxy)
            safe_print(f"✅ Created {profile_name}")
            # Update Excel column C with profile ID
            try:
                update_excel_column_c_with_profile_id(EXCEL_PATH, profile_name, pid)
                safe_print(f"📝 Updated Excel column C with ID {pid} for {profile_name}")
            except Exception as e:
                safe_print(f"❌ Failed to update Excel with ID for {profile_name}: {e}")
        else:
            pid = get_profile_id(profile_name)

        if actions.get("update"):
            pid = get_profile_id(profile_name)
            update_profile(pid, proxy)
            safe_print(f"🔄 Updated proxy for {profile_name}")

        if actions["start"] or actions["import"] or actions["pw"]:
            # Check if profile is already started
            existing_addr = get_debug_addr(profile_name)
            if existing_addr:
                addr = existing_addr
                safe_print(f"✅ Reusing existing connection for {profile_name} -> {addr}")
            else:
                addr = start_profile(pid, index, total_profiles)
                safe_print(f"✅ Started {profile_name} -> {addr}")
                remember_debug_addr(profile_name, addr)

        if actions["import"] or actions["pw"]:
            if addr:
                with config.pw_jobs_lock:
                    config.pw_jobs.append((profile_name, addr, cookie))

        if actions["close"]:
            close_profile(pid)
            safe_print(f"✅ Closed {profile_name}")

        if actions["delete"]:
            delete_profile(pid)
            safe_print(f"🗑️ Deleted {profile_name}")

    except Exception as e:
        safe_print(f"❌ {profile_name}: {e}")