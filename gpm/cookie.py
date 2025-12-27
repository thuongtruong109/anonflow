import os, json
from concurrent.futures import ThreadPoolExecutor
from utils import safe_print
from config import COOKIES_DIR

ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

def read_lines_with_fallback(path):
    last_err = None
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.readlines(), enc
        except UnicodeDecodeError as e:
            last_err = e
            continue

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines(), "utf-8(ignore)"

def convert_file(filename):
    txt_path = os.path.join(COOKIES_DIR, filename)
    processing_path = txt_path + ".processing"
    json_path = txt_path.replace(".txt", ".json")

    if os.path.exists(json_path):
        return

    try:
        os.rename(txt_path, processing_path)

        cookies = []

        lines, used_enc = read_lines_with_fallback(processing_path)

        for line in lines:
            if not line.strip() or line.startswith("#") and not line.startswith("#HttpOnly_"):
                continue

            http_only = False
            raw = line.strip()

            if raw.startswith("#HttpOnly_"):
                http_only = True
                raw = raw[len("#HttpOnly_"):]

            parts = raw.split("\t")
            if len(parts) != 7:
                continue

            domain, flag, path, secure, expiry, name, value = parts

            try:
                exp_int = int(expiry)
            except ValueError:
                continue

            cookies.append({
                "domain": domain,
                "path": path,
                "secure": secure.upper() == "TRUE",
                "httpOnly": http_only,
                "name": name,
                "value": value,
                "expirationDate": exp_int
            })

        if not cookies:
            raise ValueError(f"Không có cookie hợp lệ (encoding dùng: {used_enc})")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        os.remove(processing_path)
        safe_print(f"✅ {filename} → {os.path.basename(json_path)} (read: {used_enc})")

    except Exception as e:
        print(f"❌ Lỗi {filename}: {e}")
        if os.path.exists(processing_path):
            os.rename(processing_path, txt_path)

def convert_cookies_format():
    files = [f for f in os.listdir(COOKIES_DIR) if f.endswith(".txt")]

    if not files:
        print("⚠️ Không có file cần convert")
        return

    workers = min(8, len(files))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(convert_file, files))